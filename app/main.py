"""
app/main.py
===========
Micro-Task 4.1 — FastAPI REST API Implementation
-------------------------------------------------
Exposes the MedLearn LangGraph pipeline via HTTP endpoints:

  POST /api/v1/ask    — Image + text query → explanation + grounding
  POST /api/v1/quiz   — Topic → MCQ quiz questions
  GET  /health        — System health check

Usage
-----
    # Start the server
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

    # Health check
    curl http://localhost:8000/health

    # Text query
    curl -X POST http://localhost:8000/api/v1/ask \
         -F "query=What are the four chambers of the heart?"

    # Image + text query
    curl -X POST http://localhost:8000/api/v1/ask \
         -F "query=Explain this diagram" \
         -F "image=@/path/to/image.png"

Verification
------------
    python -c "from app.main import app; print(app.title)"
    → MedLearn Agent API
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Ensure repo root on sys.path
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MedLearn Agent API",
    description=(
        "Multimodal Medical Education Agent — LangGraph-powered RAG pipeline "
        "for anatomy & physiology learning. Educational use only."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow Streamlit frontend (and any local origin during development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str


class CitationModel(BaseModel):
    source: str
    page: int
    content_preview: str


class EvaluationModel(BaseModel):
    grounded_score: float
    is_faithful: bool
    reasoning: str


class AskResponse(BaseModel):
    question: str
    answer: str
    input_type: str
    image_caption: Optional[str]
    citations: List[CitationModel]
    evaluation: Optional[EvaluationModel]
    warning: Optional[str]
    thread_id: str


class QuizOption(BaseModel):
    label: str
    text: str


class QuizQuestion(BaseModel):
    question: str
    options: List[QuizOption]
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    topic: str
    questions: List[QuizQuestion]
    thread_id: str


class ErrorResponse(BaseModel):
    error: str
    detail: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE_MB = 10


def _parse_citations(retrieved_chunks: List[Dict[str, Any]]) -> List[CitationModel]:
    """Convert raw retrieved chunks into CitationModel objects."""
    citations = []
    for chunk in retrieved_chunks:
        content = chunk.get("content", "")
        citations.append(
            CitationModel(
                source=chunk.get("source", "Unknown"),
                page=int(chunk.get("page", 0)),
                content_preview=content[:300] + ("..." if len(content) > 300 else ""),
            )
        )
    return citations


def _parse_evaluation(eval_result: Dict[str, Any]) -> Optional[EvaluationModel]:
    """Convert raw evaluation result dict into EvaluationModel."""
    if not eval_result:
        return None
    return EvaluationModel(
        grounded_score=float(eval_result.get("grounded_score", 0.0)),
        is_faithful=bool(eval_result.get("is_faithful", False)),
        reasoning=str(eval_result.get("reasoning", "")),
    )


def _parse_quiz_questions(raw_questions: List[Dict[str, Any]]) -> List[QuizQuestion]:
    """Convert raw quiz question dicts into QuizQuestion models."""
    questions = []
    for q in raw_questions:
        raw_options = q.get("options", [])
        labels = ["A", "B", "C", "D", "E"]
        options = []
        for i, opt in enumerate(raw_options):
            label = labels[i] if i < len(labels) else str(i + 1)
            # Options may already be prefixed like "A. text" or just "text"
            text = opt.lstrip("ABCDE. ") if opt and opt[0] in "ABCDE" and len(opt) > 2 else opt
            options.append(QuizOption(label=label, text=text))

        questions.append(
            QuizQuestion(
                question=q.get("question", ""),
                options=options,
                correct_answer=str(q.get("correct_answer", "")),
                explanation=str(q.get("explanation", "")),
            )
        )
    return questions


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    System health check endpoint.
    Returns service status and version information.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        service="MedLearn Agent API",
    )


@app.post(
    "/api/v1/ask",
    response_model=AskResponse,
    tags=["Agent"],
    summary="Submit a medical education query (with optional image)",
)
async def ask(
    query: str = Form(..., description="The medical/anatomy question to ask"),
    image: Optional[UploadFile] = File(
        None, description="Optional medical diagram or anatomy image"
    ),
) -> AskResponse:
    """
    Submit an educational query to the MedLearn multi-agent pipeline.

    Accepts text-only or image+text queries. Runs the full LangGraph pipeline:
    Router → [Captioner] → Retriever → Explainer → Evaluator

    Returns the explanation with source citations and grounding evaluation.

    > **Note:** This is an educational tool only — not medical advice.
    """
    from app.graph import run_graph

    if not query.strip():
        raise HTTPException(status_code=422, detail="'query' field cannot be empty.")

    thread_id = f"api-{uuid.uuid4().hex[:8]}"
    image_path = ""
    tmp_file = None

    # Handle image upload
    if image is not None:
        content_type = image.content_type or ""
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported image type '{content_type}'. "
                       f"Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
            )

        image_bytes = await image.read()

        if len(image_bytes) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"Image exceeds maximum size of {MAX_IMAGE_SIZE_MB} MB.",
            )

        # Save to temp file (graph expects a file path)
        suffix = Path(image.filename or "upload.png").suffix or ".png"
        tmp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, dir=tempfile.gettempdir()
        )
        tmp_file.write(image_bytes)
        tmp_file.close()
        image_path = tmp_file.name
        logger.info("Saved uploaded image to temp: %s (%d bytes)", image_path, len(image_bytes))

    try:
        logger.info(
            "Running graph — query='%s...', image=%s, thread=%s",
            query[:60],
            bool(image_path),
            thread_id,
        )

        result = run_graph(
            user_query=query,
            image_path=image_path,
            generate_quiz=False,
            thread_id=thread_id,
        )

    except Exception as exc:
        logger.error("Graph execution failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent pipeline error: {exc}",
        )
    finally:
        # Clean up temp image file
        if tmp_file is not None:
            try:
                os.unlink(tmp_file.name)
            except Exception:
                pass

    # Build response
    answer = result.get("final_response") or result.get("draft_explanation") or ""
    citations = _parse_citations(result.get("retrieved_chunks", []))
    evaluation = _parse_evaluation(result.get("evaluation_result", {}))

    # Warning if low confidence
    warning: Optional[str] = None
    if evaluation and not evaluation.is_faithful:
        warning = (
            "⚠️ Low grounding score — this answer may not be fully supported by "
            "the source material. Consider verifying with your textbook."
        )

    return AskResponse(
        question=query,
        answer=answer,
        input_type=result.get("input_type", "text"),
        image_caption=result.get("image_caption"),
        citations=citations,
        evaluation=evaluation,
        warning=warning,
        thread_id=thread_id,
    )


@app.post(
    "/api/v1/quiz",
    response_model=QuizResponse,
    tags=["Agent"],
    summary="Generate MCQ quiz questions on a medical topic",
)
async def quiz(
    topic: str = Form(..., description="The medical/anatomy topic to generate quiz questions for"),
) -> QuizResponse:
    """
    Generate multiple-choice quiz questions on the given topic.

    Runs the full pipeline with `generate_quiz=True`, returning 3–5 MCQs
    with answer choices, correct answer, and explanation.
    """
    from app.graph import run_graph

    if not topic.strip():
        raise HTTPException(status_code=422, detail="'topic' field cannot be empty.")

    thread_id = f"quiz-{uuid.uuid4().hex[:8]}"

    try:
        logger.info("Generating quiz — topic='%s...', thread=%s", topic[:60], thread_id)

        result = run_graph(
            user_query=f"Explain the key concepts of: {topic}",
            image_path="",
            generate_quiz=True,
            thread_id=thread_id,
        )

    except Exception as exc:
        logger.error("Quiz generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Quiz generation error: {exc}",
        )

    raw_questions = result.get("quiz_questions", [])
    questions = _parse_quiz_questions(raw_questions)

    if not questions:
        raise HTTPException(
            status_code=500,
            detail="Quiz generation returned no questions. Try a different topic.",
        )

    return QuizResponse(
        topic=topic,
        questions=questions,
        thread_id=thread_id,
    )


# ---------------------------------------------------------------------------
# Main entry point (for direct execution)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
