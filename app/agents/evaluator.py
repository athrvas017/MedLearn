"""
app/agents/evaluator.py
=======================
Micro-Task 2.5 — Evaluator / Groundedness Critic Agent Node
-------------------------------------------------------------
Analyses the draft_explanation against the retrieved_chunks to
score faithfulness (groundedness). Flags hallucinations and produces
a confidence assessment using Google Gemini free tier.

Output in state["evaluation_result"]:
    {
        "grounded_score": float (0.0 – 1.0),
        "is_faithful": bool,
        "reasoning": str
    }

If is_faithful is False or score < 0.7, the final_response gets
a low-confidence warning prefix.

Verification:
    python -c "
    from app.agents.evaluator import evaluator_node
    print(evaluator_node({
        'draft_explanation': 'The atrium pumps blood.',
        'retrieved_chunks': [{'content': 'The atrium receives blood.'}]
    }))
    "
"""

from __future__ import annotations

import json
import logging
import os
import re
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

FAITHFULNESS_THRESHOLD = 0.7

SYSTEM_PROMPT = """You are a Groundedness Evaluator for an educational medical study tool.

Your task: compare an AI-generated explanation against the source textbook passages and judge how FAITHFUL the explanation is to those sources.

EVALUATION CRITERIA:
1. Every factual claim in the explanation should be supported by the retrieved source passages.
2. If the explanation introduces facts NOT present in the sources, that reduces faithfulness.
3. Opinions stated as facts without source backing are unfaithful.
4. Correct paraphrasing of source material is faithful.
5. Reasonable inferences directly from source material are acceptable.

IMPORTANT: Return ONLY a valid JSON object with these exact keys:
{
  "grounded_score": <float between 0.0 and 1.0>,
  "is_faithful": <true if score >= 0.7, false otherwise>,
  "reasoning": "<2-3 sentence explanation of your assessment>"
}

No markdown fencing, no extra text — just the JSON object."""


def _parse_eval_json(raw_text: str) -> Dict[str, Any]:
    """Robustly extract the evaluation JSON from the LLM response."""
    # Try direct parse
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

    # Try to find a JSON object within the text
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse evaluator JSON — returning default low-confidence.")
    return {
        "grounded_score": 0.5,
        "is_faithful": False,
        "reasoning": "Unable to parse evaluation result from the LLM. Defaulting to low confidence.",
    }


def evaluator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: evaluate groundedness of the draft explanation.

    Reads:
        state["draft_explanation"] — the explainer's output
        state["retrieved_chunks"]  — source passages for comparison

    Writes:
        state["evaluation_result"] — {grounded_score, is_faithful, reasoning}
        state["final_response"]    — explanation with optional warning prefix
        state["current_step"]      — "Evaluator"
    """
    explanation = state.get("draft_explanation", "")
    retrieved_chunks = state.get("retrieved_chunks", [])

    # Build comparison prompt
    source_text_parts: list[str] = []
    for i, chunk in enumerate(retrieved_chunks[:6], start=1):
        source = chunk.get("source", "unknown")
        page = chunk.get("page", "?")
        content = chunk.get("content", "")
        source_text_parts.append(f"[{i}] {source}, Page {page}:\n{content}")

    source_context = "\n\n".join(source_text_parts) if source_text_parts else "No source passages available."

    user_prompt = (
        f"**AI-Generated Explanation:**\n{explanation}\n\n"
        f"**Retrieved Source Passages:**\n{source_context}\n\n"
        "Evaluate the faithfulness of the explanation against the source passages. "
        "Return ONLY a JSON object."
    )

    candidate_models = list(dict.fromkeys([
        GEMINI_MODEL,
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-flash-latest",
    ]))

    evaluation_result = None
    last_error = None

    for model_name in candidate_models:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.1,  # Low temperature for consistent evaluation
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

            evaluation_result = _parse_eval_json(raw_text)
            if evaluation_result and "grounded_score" in evaluation_result:
                logger.info("Evaluator completed using model %s.", model_name)
                break
        except Exception as exc:
            logger.warning("Evaluator LLM call with %s failed: %s", model_name, exc)
            last_error = exc

    if not evaluation_result:
        logger.error("All evaluator candidate models failed. Last error: %s", last_error)
        evaluation_result = {
            "grounded_score": 0.5,
            "is_faithful": False,
            "reasoning": f"Evaluation failed due to an error: {last_error}",
        }

    # Ensure required keys exist with proper types
    grounded_score = float(evaluation_result.get("grounded_score", 0.5))
    is_faithful = bool(evaluation_result.get("is_faithful", grounded_score >= FAITHFULNESS_THRESHOLD))
    reasoning = str(evaluation_result.get("reasoning", ""))

    # Clamp score to [0.0, 1.0]
    grounded_score = max(0.0, min(1.0, grounded_score))
    # Override is_faithful based on threshold
    is_faithful = grounded_score >= FAITHFULNESS_THRESHOLD

    evaluation_result = {
        "grounded_score": grounded_score,
        "is_faithful": is_faithful,
        "reasoning": reasoning,
    }

    # Build final response
    if is_faithful:
        final_response = explanation
    else:
        final_response = (
            "⚠️ **Low Confidence Warning**: This explanation may contain claims not fully "
            "supported by the source material. Please verify with your textbook.\n\n"
            f"{explanation}\n\n"
            f"---\n*Groundedness Score: {grounded_score:.2f}/1.00 — "
            f"Evaluator note: {reasoning}*"
        )

    logger.info(
        "Evaluator: score=%.2f, faithful=%s",
        grounded_score,
        is_faithful,
    )

    return {
        "evaluation_result": evaluation_result,
        "final_response": final_response,
        "current_step": "Evaluator",
    }
