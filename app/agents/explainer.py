"""
app/agents/explainer.py
=======================
Micro-Task 2.3 — Multimodal Explainer Agent Node
--------------------------------------------------
Synthesises image caption + retrieved textbook context + user query
into a cited, educational explanation using Google Gemini (free tier).

Prompt enforces:
  - Strictly educational & student-oriented tone
  - Inline bracket citations  [Source, Page N]
  - Non-diagnostic disclaimer

Verification:
    python -c "
    from app.agents.explainer import explainer_node
    print(explainer_node({
        'user_query': 'How does blood flow through the heart?',
        'retrieved_chunks': [{'content': 'Blood enters the right atrium...', 'source': 'OpenStax_AP.pdf', 'page': 45}],
        'image_caption': None,
    }))
    "
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM Configuration — Google Gemini free tier
# ---------------------------------------------------------------------------
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

SYSTEM_PROMPT = """You are MedLearn — an expert medical/anatomy study assistant for students.
Your job is to produce clear, accurate, educational explanations grounded in the provided source material.

RULES:
1. Use ONLY the retrieved textbook passages below to construct your answer.
2. Cite every factual claim with an inline citation in brackets: [Source, Page N].
3. If the retrieved context does not contain enough information to answer, say so explicitly — never fabricate.
4. Write at an undergraduate level — clear, structured, and easy to follow.
5. NEVER provide medical diagnoses, treatment plans, or clinical advice.
6. End your explanation with a brief "Key Takeaways" section (2-3 bullet points).

DISCLAIMER: You are an educational study tool, NOT a medical professional. Your explanations are for learning purposes only."""


def _build_user_prompt(
    user_query: str,
    retrieved_chunks: list,
    image_caption: str | None = None,
) -> str:
    """Assemble the user-facing prompt with context and query."""
    parts: list[str] = []

    # Include image caption if available
    if image_caption:
        parts.append(f"**Image Description:** {image_caption}\n")

    # Include retrieved textbook context
    if retrieved_chunks:
        parts.append("**Retrieved Textbook Context:**")
        for i, chunk in enumerate(retrieved_chunks, start=1):
            source = chunk.get("source", "unknown")
            page = chunk.get("page", "?")
            content = chunk.get("content", "")
            parts.append(f"\n[{i}] {source}, Page {page}:\n{content}")
        parts.append("")
    else:
        parts.append("**Retrieved Context:** No relevant textbook passages found.\n")

    # User question
    parts.append(f"**Student's Question:** {user_query}")
    parts.append("\nPlease provide a thorough, cited explanation.")

    return "\n".join(parts)


def explainer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: generate a cited educational explanation.

    Reads:
        state["user_query"]        — the student's question
        state["retrieved_chunks"]  — top-k retriever results
        state["image_caption"]     — optional BLIP caption

    Writes:
        state["draft_explanation"] — the generated explanation text
        state["current_step"]      — "Explainer"
    """
    user_query = state.get("user_query", "")
    retrieved_chunks = state.get("retrieved_chunks", [])
    image_caption = state.get("image_caption")

    # If no query, build one from the caption
    if not user_query.strip() and image_caption:
        user_query = f"Explain what is shown in this image: {image_caption}"

    user_prompt = _build_user_prompt(user_query, retrieved_chunks, image_caption)

    candidate_models = list(dict.fromkeys([
        GEMINI_MODEL,
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-flash-latest",
    ]))

    explanation = ""
    last_error = None

    for model_name in candidate_models:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.3,
                max_output_tokens=2048,
            )

            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            response = llm.invoke(messages)
            if isinstance(response.content, str):
                explanation = response.content.strip()
            elif isinstance(response.content, list):
                explanation = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in response.content).strip()
            else:
                explanation = str(response.content).strip()

            if explanation:
                logger.info("Explainer generated %d-char explanation using model %s.", len(explanation), model_name)
                break
        except Exception as exc:
            logger.warning("Explainer LLM call with %s failed: %s", model_name, exc)
            last_error = exc

    if not explanation:
        logger.error("All explainer candidate models failed. Last error: %s", last_error)
        explanation = (
            "I was unable to generate an explanation at this time. "
            "Please try again or rephrase your question.\n\n"
            f"Error: {last_error}"
        )

    return {
        "draft_explanation": explanation,
        "current_step": "Explainer",
    }
