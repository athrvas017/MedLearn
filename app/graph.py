"""
app/graph.py
============
Micro-Task 2.6 — LangGraph StateGraph Assembly & Conditional Edges
-------------------------------------------------------------------
Assembles all agent nodes into a unified executable LangGraph workflow:

    START → router → (conditional) → captioner / retriever →
    explainer → evaluator → (conditional) → quiz_gen / END

Features:
  - Conditional edges for image vs text-only routing
  - Optional quiz generation branch
  - MemorySaver checkpointer for state persistence & conversation memory

Graph Flow:
    START → router_node
         ↓ (conditional)
    [image/image+text] → captioner_node → retriever_node
    [text]             → retriever_node
         ↓
    explainer_node → evaluator_node
         ↓ (conditional)
    [generate_quiz=True]  → quiz_gen_node → END
    [generate_quiz=False] → END

Verification:
    python -c "from app.graph import app_graph; print(list(app_graph.get_graph().nodes.keys()))"
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Ensure repo root on sys.path
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.state import AgentState
from app.agents.router import router_node, route_after_router
from app.agents.captioner import generate_caption
from app.agents.retriever import retrieve_context
from app.agents.explainer import explainer_node
from app.agents.quiz_gen import quiz_gen_node
from app.agents.evaluator import evaluator_node

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LangGraph-compatible wrapper nodes for Phase 1 modules
# ---------------------------------------------------------------------------

def captioner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node wrapper around the Phase 1 captioner.

    Reads:  state["image_path"]
    Writes: state["image_caption"], state["current_step"]
    """
    image_path = state.get("image_path", "")
    logger.info("Captioner processing image: %s", image_path)

    caption = generate_caption(image_path)

    logger.info("Captioner output: '%s'", caption[:80])
    return {
        "image_caption": caption,
        "current_step": "Captioner",
    }


def retriever_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node wrapper around the Phase 1 retriever.

    Builds a composite query from user_query + image_caption,
    then retrieves top-k chunks from the Chroma vector store.

    Reads:  state["user_query"], state["image_caption"]
    Writes: state["retrieved_chunks"], state["current_step"]
    """
    user_query = state.get("user_query", "")
    image_caption = state.get("image_caption", "")

    # Build composite query: combine user question with caption for better retrieval
    query_parts: list[str] = []
    if user_query.strip():
        query_parts.append(user_query.strip())
    if image_caption:
        query_parts.append(image_caption)

    composite_query = " ".join(query_parts) if query_parts else "anatomy physiology"

    logger.info("Retriever query: '%s'", composite_query[:100])

    chunks = retrieve_context(query=composite_query, top_k=4)

    logger.info("Retriever returned %d chunk(s).", len(chunks))
    return {
        "retrieved_chunks": chunks,
        "current_step": "Retriever",
    }


def route_after_evaluator(state: Dict[str, Any]) -> str:
    """
    Conditional edge after the evaluator: go to quiz_gen or END.
    """
    if state.get("generate_quiz", False):
        return "quiz_gen"
    return END


# ---------------------------------------------------------------------------
# Build the StateGraph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """
    Construct and compile the MedLearn multi-agent StateGraph.

    Returns a compiled LangGraph runnable with MemorySaver checkpointing.
    """
    workflow = StateGraph(AgentState)

    # --- Add nodes ---
    workflow.add_node("router", router_node)
    workflow.add_node("captioner", captioner_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("explainer", explainer_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("quiz_gen", quiz_gen_node)

    # --- Define edges ---

    # START → Router
    workflow.add_edge(START, "router")

    # Router → (conditional) → Captioner or Retriever
    workflow.add_conditional_edges(
        "router",
        route_after_router,
        {
            "captioner": "captioner",
            "retriever": "retriever",
        },
    )

    # Captioner → Retriever (always)
    workflow.add_edge("captioner", "retriever")

    # Retriever → Explainer (always)
    workflow.add_edge("retriever", "explainer")

    # Explainer → Evaluator (always)
    workflow.add_edge("explainer", "evaluator")

    # Evaluator → (conditional) → QuizGen or END
    workflow.add_conditional_edges(
        "evaluator",
        route_after_evaluator,
        {
            "quiz_gen": "quiz_gen",
            END: END,
        },
    )

    # QuizGen → END (always)
    workflow.add_edge("quiz_gen", END)

    # --- Compile with checkpointer ---
    memory = MemorySaver()
    compiled = workflow.compile(checkpointer=memory)

    logger.info("MedLearn StateGraph compiled successfully.")
    return compiled


# ---------------------------------------------------------------------------
# Module-level compiled graph instance
# ---------------------------------------------------------------------------
app_graph = build_graph()


# ---------------------------------------------------------------------------
# Convenience wrapper for running the graph
# ---------------------------------------------------------------------------

def run_graph(
    user_query: str = "",
    image_path: str = "",
    generate_quiz: bool = False,
    thread_id: str = "default",
) -> Dict[str, Any]:
    """
    Execute the full MedLearn agent pipeline.

    Args:
        user_query:    Text question from the user.
        image_path:    Optional path to an uploaded image.
        generate_quiz: Whether to generate MCQ quiz questions.
        thread_id:     Conversation thread ID for checkpointing.

    Returns:
        The final state dict after the graph completes.
    """
    initial_state: Dict[str, Any] = {
        "user_query": user_query,
        "image_path": image_path,
        "generate_quiz": generate_quiz,
    }

    config = {"configurable": {"thread_id": thread_id}}

    logger.info(
        "Running graph — query='%s', image='%s', quiz=%s, thread='%s'",
        user_query[:60],
        image_path or "(none)",
        generate_quiz,
        thread_id,
    )

    result = app_graph.invoke(initial_state, config=config)

    logger.info("Graph completed. Final step: %s", result.get("current_step", "?"))
    return result


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[graph] %(message)s")

    # Print graph topology
    nodes = list(app_graph.get_graph().nodes.keys())
    print(f"Graph nodes: {nodes}")

    # Dry run with text-only query
    print("\n--- Text-only test ---")
    result = run_graph(
        user_query="What are the four chambers of the human heart?",
        generate_quiz=False,
        thread_id="test-text-only",
    )
    print(f"Input type: {result.get('input_type')}")
    print(f"Retrieved chunks: {len(result.get('retrieved_chunks', []))}")
    print(f"Evaluation: {result.get('evaluation_result', {})}")
    print(f"Final response (first 200 chars): {result.get('final_response', '')[:200]}...")
