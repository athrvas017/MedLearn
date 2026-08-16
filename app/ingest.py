"""
app/ingest.py
=============
Micro-Task 1.3 — Textbook PDF Chunking & Ingestion Pipeline
------------------------------------------------------------
Loads every PDF found under ``data/source_pdfs/`` (recursively),
splits them into overlapping text chunks, enriches each chunk with
rich metadata for easy retrieval, and persists the result into a
persistent Chroma vector store at ``app/vectorstore/chroma_db``.

Metadata attached to every chunk
---------------------------------
  source        : PDF filename (basename)
  source_path   : Relative path from repo root
  subject       : High-level subject inferred from folder name
                  ("anatomy" → "Anatomy & Physiology",
                   "surgery"  → "Surgery")
  page          : 1-based page number inside the PDF
  chapter       : Best-effort chapter heading detected in chunk text
  chunk_index   : Sequential chunk index within the document
  total_chunks  : Total number of chunks produced from this PDF
  chunk_size    : Approximate character length of this chunk
  ingestion_ts  : ISO-8601 UTC timestamp of ingestion run

Run
---
    python app/ingest.py

Expected output (example)
--------------------------
    [ingest] Scanning: data/source_pdfs
    [ingest] Found 2 PDF file(s).
    [ingest] Processing: anatomy-and-physiology-2e_-_WEB.pdf  (476 MB)
    [ingest]   Pages loaded : 1,342
    [ingest]   Chunks created: 4,891
    [ingest] Processing: Manipal Manual of Surgery Vol. 1, 2- 6th edition.pdf  (189 MB)
    [ingest]   Pages loaded : 2,201
    [ingest]   Chunks created: 7,102
    [ingest] Embedding & storing all 11,993 chunks into Chroma ...
    [ingest] Successfully ingested 11,993 documents from PDF into Chroma vector store at ./app/vectorstore/chroma_db
"""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Ensure the repo root is on sys.path when running this file directly
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[ingest] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — tweak here if needed
# ---------------------------------------------------------------------------
SOURCE_DIR: Path = REPO_ROOT / "data" / "source_pdfs"
CHROMA_DIR: Path = REPO_ROOT / "app" / "vectorstore" / "chroma_db"
COLLECTION_NAME: str = "medlearn_textbooks"

# Chunk parameters (per micro_task.md spec)
CHUNK_SIZE: int = 800
CHUNK_OVERLAP: int = 150

# Embedding model — runs locally with sentence-transformers, no API key needed
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

# Batch size for Chroma upsert (avoids memory spikes on large PDFs)
UPSERT_BATCH_SIZE: int = 500

# ---------------------------------------------------------------------------
# Subject mapping: folder name (lower-cased) → human-readable subject label
# ---------------------------------------------------------------------------
SUBJECT_MAP: dict = {
    "anatomy": "Anatomy & Physiology",
    "surgery": "Surgery",
    "pathology": "Pathology",
    "pharmacology": "Pharmacology",
    "physiology": "Physiology",
    "biochemistry": "Biochemistry",
    "microbiology": "Microbiology",
}


def _infer_subject(pdf_path: Path) -> str:
    """
    Walk up the directory tree relative to SOURCE_DIR and return the
    human-readable subject label for the first matching folder name.
    Falls back to the immediate parent folder name if nothing matches.
    """
    parts = pdf_path.relative_to(SOURCE_DIR).parts  # e.g. ("anatomy", "file.pdf")
    for part in parts[:-1]:  # skip the filename itself
        label = SUBJECT_MAP.get(part.lower())
        if label:
            return label
    # Fallback: use immediate parent folder with title-case
    if len(parts) > 1:
        return parts[-2].replace("_", " ").title()
    return "General Medicine"


def _infer_chapter(text: str) -> str:
    """
    Lightweight heuristic: look for a 'Chapter N' or 'CHAPTER N'
    header in the first 400 characters of the chunk text.
    Returns the matched heading string or an empty string.
    """
    match = re.search(
        r"(chapter\s+\d+[:\s\-\u2013\u2014]*[A-Za-z\s,\-\u2013\u2014]{0,60})",
        text[:400],
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def discover_pdfs(source_dir: Path) -> List[Path]:
    """Return all *.pdf files found recursively under *source_dir*."""
    pdfs = sorted(source_dir.rglob("*.pdf"))
    logger.info("Found %d PDF file(s).", len(pdfs))
    return pdfs


def load_and_chunk(pdf_path: Path, ingestion_ts: str) -> list:
    """
    Load a single PDF and split into chunks.

    Returns a list of LangChain ``Document`` objects with enriched metadata.
    """
    logger.info(
        "Processing: %s  (%.0f MB)",
        pdf_path.name,
        pdf_path.stat().st_size / 1_048_576,
    )

    loader = PyPDFLoader(str(pdf_path))
    raw_pages = loader.load()  # one Document per page, metadata["page"] is 0-based

    logger.info("  Pages loaded : %s", f"{len(raw_pages):,}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    chunks = splitter.split_documents(raw_pages)
    total_chunks = len(chunks)
    subject = _infer_subject(pdf_path)
    rel_path = str(pdf_path.relative_to(REPO_ROOT)).replace("\\", "/")

    for idx, chunk in enumerate(chunks):
        # PyPDFLoader stores page as 0-based int
        page_0based: int = chunk.metadata.get("page", 0)
        chapter_hint: str = _infer_chapter(chunk.page_content)

        # ----------------------------------------------------------------
        # Rich metadata — every field here is filterable in Chroma queries
        # ----------------------------------------------------------------
        chunk.metadata = {
            # --- Provenance ---
            "source": pdf_path.name,           # e.g. "anatomy-and-physiology-2e_-_WEB.pdf"
            "source_path": rel_path,           # e.g. "data/source_pdfs/anatomy/..."
            "subject": subject,                # e.g. "Anatomy & Physiology"
            # --- Location in source ---
            "page": page_0based + 1,           # 1-based for human-readable citations
            "chapter": chapter_hint,           # best-effort heading (may be empty)
            # --- Chunk bookkeeping ---
            "chunk_index": idx,                # 0-based chunk index within this PDF
            "total_chunks": total_chunks,      # total chunks from this PDF
            "chunk_size": len(chunk.page_content),  # actual char length
            # --- Ingestion audit ---
            "ingestion_ts": ingestion_ts,      # ISO-8601 UTC
        }

    logger.info("  Chunks created: %s", f"{total_chunks:,}")
    return chunks


def embed_and_store(all_chunks: list, chroma_dir: Path) -> int:
    """
    Embed *all_chunks* and upsert into a persistent Chroma collection.
    Uses batch upserts to avoid OOM on large corpora.
    Returns the total number of documents stored.
    """
    logger.info(
        "Embedding & storing all %s chunks into Chroma ...",
        f"{len(all_chunks):,}",
    )

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    chroma_dir.mkdir(parents=True, exist_ok=True)

    vectorstore = None
    for batch_start in range(0, len(all_chunks), UPSERT_BATCH_SIZE):
        batch = all_chunks[batch_start : batch_start + UPSERT_BATCH_SIZE]

        if vectorstore is None:
            # First batch — create the collection
            vectorstore = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                persist_directory=str(chroma_dir),
                collection_name=COLLECTION_NAME,
            )
        else:
            vectorstore.add_documents(batch)

        logger.info(
            "  Stored batch %d\u2013%d ...",
            batch_start + 1,
            min(batch_start + UPSERT_BATCH_SIZE, len(all_chunks)),
        )

    # langchain-chroma 1.x auto-persists on every write — no explicit call needed.
    if vectorstore:
        logger.info("All chunks persisted to '%s'.", chroma_dir)

    return len(all_chunks)


def run_ingestion() -> int:
    """
    Full ingestion pipeline:
      1. Discover PDFs
      2. Load & chunk each PDF with metadata
      3. Embed & store in Chroma
    Returns total document count (0 on failure).
    """
    logger.info("Scanning: %s", SOURCE_DIR)

    pdf_files = discover_pdfs(SOURCE_DIR)
    if not pdf_files:
        logger.warning(
            "No PDF files found under '%s'. "
            "Please place your source PDFs in subfolders of that directory.",
            SOURCE_DIR,
        )
        return 0

    ingestion_ts = datetime.now(timezone.utc).isoformat()
    all_chunks: list = []

    for pdf_path in pdf_files:
        try:
            chunks = load_and_chunk(pdf_path, ingestion_ts)
            all_chunks.extend(chunks)
        except Exception as exc:  # noqa: BLE001
            logger.error("  FAILED to process '%s': %s", pdf_path.name, exc)
            continue

    if not all_chunks:
        logger.error("No chunks produced — aborting.")
        return 0

    total_stored = embed_and_store(all_chunks, CHROMA_DIR)

    logger.info(
        "Successfully ingested %s documents from PDF into Chroma vector store at ./%s",
        f"{total_stored:,}",
        CHROMA_DIR.relative_to(REPO_ROOT),
    )
    return total_stored


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    count = run_ingestion()
    sys.exit(0 if count > 0 else 1)
