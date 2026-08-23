"""
app/agents/quiz_gen.py
======================
Micro-Task 2.4 — Quiz Generator Agent Node
--------------------------------------------
Produces 3–5 multiple-choice questions (MCQs) based on the
current topic's explanation and retrieved context using Google
Gemini free tier.

Output Schema per question:
    {
        "question": str,
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "correct_answer": "A",
        "explanation": str
    }

Verification:
    python -c "
    from app.agents.quiz_gen import quiz_gen_node
    print(quiz_gen_node({'draft_explanation': 'The heart has four chambers...', 'retrieved_chunks': []}))
    "
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM Configuration — Google Gemini free tier
# ---------------------------------------------------------------------------
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

SYSTEM_PROMPT = """You are MedLearn Quiz Generator — an educational quiz creator for medical/anatomy students.

RULES:
1. Generate exactly 3 to 5 multiple-choice questions based on the provided explanation and source material.
2. Each question must have exactly 4 options labeled A, B, C, D.
3. Only ONE option is correct per question.
4. Include a brief explanation for why the correct answer is right.
5. Questions should test understanding, not just memorization.
6. Keep questions at an undergraduate anatomy/physiology level.

IMPORTANT: Return ONLY a valid JSON array. No markdown fencing, no extra text.

Example format:
[
  {
    "question": "What is the primary function of the left ventricle?",
    "options": ["A) Receives deoxygenated blood from the body", "B) Pumps oxygenated blood to the body through the aorta", "C) Pumps blood to the lungs for oxygenation", "D) Filters blood before it enters the heart"],
    "correct_answer": "B",
    "explanation": "The left ventricle is the most muscular chamber and is responsible for pumping oxygenated blood through the aorta to the systemic circulation."
  }
]"""


def _parse_quiz_json(raw_text: str) -> List[Dict[str, Any]]:
    """
    Robustly extract the JSON array from the LLM response.
    Handles markdown code fences, leading text, etc.
    """
    # Try direct parse first
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw_text)
    cleaned = cleaned.strip().rstrip("`")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON array within the text
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse quiz JSON from LLM response.")
    return []


def quiz_gen_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: generate MCQ quiz questions.

    Reads:
        state["draft_explanation"] — the explainer's output
        state["retrieved_chunks"]  — source context for grounding

    Writes:
        state["quiz_questions"]  — list of MCQ dicts
        state["current_step"]    — "QuizGen"
    """
    explanation = state.get("draft_explanation", "")
    retrieved_chunks = state.get("retrieved_chunks", [])

    # Build context for quiz generation
    context_parts: list[str] = []
    if explanation:
        context_parts.append(f"**Explanation to quiz on:**\n{explanation}")
    if retrieved_chunks:
        context_parts.append("\n**Source material:**")
        for i, chunk in enumerate(retrieved_chunks[:4], start=1):
            context_parts.append(
                f"[{i}] {chunk.get('source', 'unknown')}, Page {chunk.get('page', '?')}:\n"
                f"{chunk.get('content', '')[:500]}"
            )

    user_prompt = "\n\n".join(context_parts)
    user_prompt += "\n\nGenerate 3-5 multiple choice questions based on the above content. Return ONLY a JSON array."

    candidate_models = list(dict.fromkeys([
        GEMINI_MODEL,
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-flash-latest",
    ]))

    quiz_questions = []
    last_error = None

    for model_name in candidate_models:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.5,
                max_output_tokens=2048,
            )

            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            response = llm.invoke(messages)
            if isinstance(response.content, str):
                raw_text = response.content.strip()
            elif isinstance(response.content, list):
                raw_text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in response.content).strip()
            else:
                raw_text = str(response.content).strip()

            parsed = _parse_quiz_json(raw_text)
            if parsed:
                quiz_questions = parsed
                logger.info("QuizGen produced %d question(s) using model %s.", len(quiz_questions), model_name)
                break
        except Exception as exc:
            logger.warning("QuizGen LLM call with %s failed: %s", model_name, exc)
            last_error = exc

    if not quiz_questions:
        logger.warning("All QuizGen candidate models failed or returned empty. Last error: %s", last_error)
        quiz_questions = []

    return {
        "quiz_questions": quiz_questions,
        "current_step": "QuizGen",
    }
