"""
app/agents/router.py
====================
Micro-Task 2.2 — Input Router Agent Node
-----------------------------------------
Inspects the incoming state (image_path, user_query) and classifies
the request into one of three routing paths:

    "image"       — image provided, no text query
    "text"        — text query only, no image
    "image+text"  — both image and text query

This is a pure-logic node — no LLM call, so it's instant and free.

Verification:
    python -c "from app.agents.router import router_node; print(router_node({'image_path': 'img.png', 'user_query': ''}))"
    # → {'input_type': 'image', 'current_step': 'Router'}
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def router_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: classify input type based on what the user provided.

    Reads:
        state["image_path"]  — file path string or None/empty
        state["user_query"]  — question string or None/empty

    Writes:
        state["input_type"]   — "image" | "text" | "image+text"
        state["current_step"] — "Router"
    """
    image_path = state.get("image_path") or ""
    user_query = state.get("user_query") or ""

    has_image = bool(image_path.strip())
    has_query = bool(user_query.strip())

    if has_image and has_query:
        input_type = "image+text"
    elif has_image:
        input_type = "image"
    elif has_query:
        input_type = "text"
    else:
        # Edge case: nothing provided — default to text so graph doesn't crash
        input_type = "text"
        logger.warning("Router received empty input (no image, no query).")

    logger.info("Router classified input as '%s'.", input_type)

    return {
        "input_type": input_type,
        "current_step": "Router",
    }


def route_after_router(state: Dict[str, Any]) -> str:
    """
    Conditional edge function: decides which node to run after the Router.

    Returns:
        "captioner"  — if input contains an image (needs captioning first)
        "retriever"  — if text-only (skip captioning, go straight to retrieval)
    """
    input_type = state.get("input_type", "text")

    if input_type in ("image", "image+text"):
        return "captioner"
    return "retriever"
