"""
app/agents/retriever.py
=======================
Micro-Task 1.4 — Vector Store & Retriever Module
-------------------------------------------------
Wraps the populated Chroma vector store with a clean retrieval interface.

Public API
----------
    retrieve_context(query: str, top_k: int = 4) -> List[Dict[str, Any]]

Each returned dict contains:
    content  : str   — the chunk text
    source   : str   — PDF filename
    page     : int   — 1-based page number
    subject  : str   — subject label (e.g. "Anatomy & Physiology")
    chapter  : str   — best-effort chapter heading (may be empty)
    score    : float — cosine similarity score (higher = more relevant)

Optional filter support
-----------------------
    retrieve_context(query, top_k=4, subject="Surgery")
    retrieve_context(query, top_k=4, source="anatomy-and-physiology-2e_-_WEB.pdf")

Verification
------------
    python -c "
    from app.agents.retriever import retrieve_context
    results = retrieve_context('cardiovascular system heart ventricles', top_k=2)
    for r in results:
        print(r['source'], 'p.', r['page'], '| score:', round(r['score'], 3))
        print(r['content'][:120])
        print()
    "
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Ensure repo root on sys.path when running directly
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — must match ingest.py
# ---------------------------------------------------------------------------
CHROMA_DIR: Path = REPO_ROOT / "app" / "vectorstore" / "chroma_db"
COLLECTION_NAME: str = "medlearn_textbooks"
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# Singleton vectorstore — loaded once, reused across calls
# ---------------------------------------------------------------------------
_vectorstore: Optional[Chroma] = None


def _get_vectorstore() -> Chroma:
    """
    Lazy-load and cache the Chroma vector store.
    Raises RuntimeError if the store has not been populated yet.
    """
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    if not CHROMA_DIR.exists():
        raise RuntimeError(
            f"Chroma DB not found at '{CHROMA_DIR}'. "
            "Please run `python app/ingest.py` first to populate the vector store."
        )

    logger.info("Loading Chroma vector store from '%s' …", CHROMA_DIR)
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    _vectorstore = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
    )
    doc_count = _vectorstore._collection.count()
    logger.info("Vector store loaded — %s chunks available.", f"{doc_count:,}")
    return _vectorstore


def retrieve_context(
    query: str,
    top_k: int = 4,
    subject: Optional[str] = None,
    source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the top-k most relevant chunks for *query* from the Chroma DB.

    Parameters
    ----------
    query   : Natural language question or search string.
    top_k   : Number of chunks to return (default 4).
    subject : Optional metadata filter — e.g. "Surgery" or "Anatomy & Physiology".
    source  : Optional metadata filter — exact PDF filename.

    Returns
    -------
    List of dicts, each containing:
        {
            "content" : str,
            "source"  : str,
            "page"    : int,
            "subject" : str,
            "chapter" : str,
            "score"   : float,
        }
    Results are sorted by descending similarity score.
    """
    if not query or not query.strip():
        logger.warning("retrieve_context called with empty query — returning [].")
        return []

    store = _get_vectorstore()

    # Build optional metadata filter for Chroma's `where` clause
    where: Optional[Dict[str, Any]] = None
    if subject and source:
        where = {"$and": [{"subject": subject}, {"source": source}]}
    elif subject:
        where = {"subject": subject}
    elif source:
        where = {"source": source}

    try:
        results = store.similarity_search_with_relevance_scores(
            query=query,
            k=top_k,
            filter=where,  # langchain-chroma 1.x uses 'filter' not 'where'
        )
    except Exception as exc:
        logger.error("Chroma similarity search failed: %s", exc)
        return []

    chunks: List[Dict[str, Any]] = []
    for doc, score in results:
        meta = doc.metadata or {}
        chunks.append(
            {
                "content": doc.page_content,
                "source": meta.get("source", "unknown"),
                "page": meta.get("page", 0),
                "subject": meta.get("subject", ""),
                "chapter": meta.get("chapter", ""),
                "score": round(float(score), 4),
            }
        )

    # Sort by score descending (should already be, but enforce)
    chunks.sort(key=lambda c: c["score"], reverse=True)

    logger.debug(
        "retrieve_context('%s', top_k=%d) → %d chunks returned.",
        query[:60],
        top_k,
        len(chunks),
    )
    return chunks


def format_citations(chunks: List[Dict[str, Any]]) -> str:
    """
    Convenience helper: convert retrieved chunks into a formatted citation
    string for injection into LLM prompts.

    Example output:
        [1] anatomy-and-physiology-2e_-_WEB.pdf, Page 312
            The left ventricle pumps oxygenated blood into the aorta...

        [2] Manipal Manual of Surgery Vol. 1, 2- 6th edition.pdf, Page 88
            Surgical anatomy of the heart includes...
    """
    if not chunks:
        return "No relevant context found."

    lines: List[str] = []
    for i, chunk in enumerate(chunks, start=1):
        chapter = f" — {chunk['chapter']}" if chunk.get("chapter") else ""
        header = f"[{i}] {chunk['source']}, Page {chunk['page']}{chapter}"
        preview = chunk["content"][:300].replace("\n", " ").strip()
        lines.append(f"{header}\n    {preview}…")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Quick sanity check when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[retriever] %(message)s")
    test_query = "cardiovascular system heart ventricles blood flow"
    print(f"\nQuery: '{test_query}'\n" + "=" * 60)
    results = retrieve_context(test_query, top_k=2)
    if not results:
        print("No results — run `python app/ingest.py` first.")
        sys.exit(1)
    for r in results:
        print(f"\nSource : {r['source']}")
        print(f"Page   : {r['page']}  |  Subject: {r['subject']}")
        print(f"Chapter: {r['chapter'] or '(not detected)'}")
        print(f"Score  : {r['score']}")
        print(f"Content: {r['content'][:200]}…")
    print("\n" + "=" * 60)
    print(f"\nCitation block:\n{format_citations(results)}")
