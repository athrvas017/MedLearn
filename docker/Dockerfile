# ============================================================
# MedLearn Agent — Dockerfile
# ============================================================
# Multi-stage build supporting both API (FastAPI) and
# Frontend (Streamlit) services.
#
# Build args:
#   SERVICE = api | frontend (default: api)
#
# Usage:
#   docker build --build-arg SERVICE=api     -t medlearn-api .
#   docker build --build-arg SERVICE=frontend -t medlearn-frontend .
# ============================================================

# ── Base image ──────────────────────────────────────────────
FROM python:3.11-slim AS base

LABEL maintainer="MedLearn Agent"
LABEL description="Multimodal Medical Education Agent (LangGraph + RAG)"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# ── Dependencies ─────────────────────────────────────────────
FROM base AS deps

COPY requirements.txt .

# Install Python deps (no cache to keep image slim)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Application ──────────────────────────────────────────────
FROM deps AS app

# Copy project files
COPY app/          ./app/
COPY frontend/     ./frontend/
COPY evals/        ./evals/
COPY data/         ./data/
COPY .env.example  ./.env.example

# Create vectorstore directory (populated at runtime via ingest)
RUN mkdir -p ./app/vectorstore/chroma_db

# Non-root user for security
RUN adduser --disabled-password --gecos "" medlearn
USER medlearn

# ── API Service ──────────────────────────────────────────────
FROM app AS api

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]

# ── Frontend Service ─────────────────────────────────────────
FROM app AS frontend

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "frontend/streamlit_app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
