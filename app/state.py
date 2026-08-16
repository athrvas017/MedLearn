"""
app/state.py
============
Micro-Task 2.1 — LangGraph Shared State Definition
----------------------------------------------------
Central TypedDict schema shared across all agent nodes in the
LangGraph StateGraph. Every node reads from and writes to this state.

Verification:
    python -c "from app.state import AgentState; print(AgentState.__annotations__.keys())"
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    """
    Shared state flowing through the MedLearn LangGraph pipeline.

    Fields are populated progressively as the graph executes:
      Router → Captioner (optional) → Retriever → Explainer → Evaluator → QuizGen (optional)
    """

    # --- Input classification ---
    input_type: str                          # "image" | "text" | "image+text"

    # --- User inputs ---
    image_path: Optional[str]                # filesystem path to uploaded image
    user_query: str                          # user's text question

    # --- Captioner output ---
    image_caption: Optional[str]             # vision-model description of the image

    # --- Retriever output ---
    retrieved_chunks: List[Dict[str, Any]]   # top-k chunks from Chroma vector store

    # --- Explainer output ---
    draft_explanation: Optional[str]         # cited educational explanation

    # --- Quiz generator output ---
    quiz_questions: Optional[List[Dict[str, Any]]]  # list of MCQ dicts

    # --- Evaluator output ---
    evaluation_result: Optional[Dict[str, Any]]     # {grounded_score, is_faithful, reasoning}

    # --- Final output ---
    final_response: Optional[str]            # post-evaluation answer for the user

    # --- Graph bookkeeping ---
    current_step: str                        # name of the currently executing node
    generate_quiz: bool                      # whether the user requested quiz generation
