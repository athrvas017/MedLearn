"""
frontend/streamlit_app.py
=========================
Micro-Tasks 4.2 / 4.3 / 4.4 — Streamlit UI: Clinical Teal Design System,
Agent Stepper, Citation Display, Interactive Quiz
---------------------------------------------------------------------------
Design tokens match design.md exactly:
  Primary:        Deep Teal  #0F766E
  Primary Hover:  #0B5D57
  Accent (Quiz):  Soft Amber #F59E0B
  Bg light:       #F8FAF9   |  Bg dark: #0F1817
  Surface light:  #FFFFFF   |  Surface dark: #16211F
  Text primary:   #111827
  Text secondary: #6B7280
  Success:        #22C55E   |  Warning: #DC2626
  Border:         #E5E7EB
  Fonts:          Inter (body) / IBM Plex Mono (citations)

Two execution modes:
  STANDALONE_MODE=1  → calls run_graph() directly (no backend)
  default            → calls FastAPI at BACKEND_URL (default: http://localhost:8000)

Run:
    streamlit run frontend/streamlit_app.py
"""

from __future__ import annotations

import base64
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Repo root on sys.path
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv()

STANDALONE_MODE = os.getenv("STANDALONE_MODE", "0") == "1"
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="MedLearn Agent",
    page_icon="🩺",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Design system CSS
# ---------------------------------------------------------------------------
GOOGLE_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
    '&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">'
)

CSS = """
<style>
/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
  color: var(--text-primary) !important;
  font-family: 'Inter', sans-serif !important;
}

/* ── CSS Variables (light mode default) ── */
:root {
  --primary:        #0F766E;
  --primary-hover:  #0B5D57;
  --accent:         #F59E0B;
  --accent-hover:   #D97706;
  --bg:             #F8FAF9;
  --surface:        #FFFFFF;
  --text-primary:   #111827;
  --text-secondary: #6B7280;
  --success:        #22C55E;
  --danger:         #DC2626;
  --border:         #E5E7EB;
  --shadow:         0 2px 8px rgba(0,0,0,0.08);
  --mono:           'IBM Plex Mono', monospace;
}

/* ── Dark mode ── */
[data-theme="dark"] {
  --bg:           #0F1817;
  --surface:      #16211F;
  --text-primary: #F9FAFB;
  --text-secondary:#9CA3AF;
  --border:       #2D3F3D;
  --shadow:       0 2px 8px rgba(0,0,0,0.3);
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stSidebar"] { display: none; }
.block-container {
  padding-top: 0 !important;
  padding-bottom: 2rem !important;
  max-width: 760px !important;
}

/* ── Top bar ── */
.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0.75rem 1.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: var(--shadow);
}
.topbar-logo {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--primary);
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.topbar-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}
.topbar-link {
  font-size: 0.82rem;
  color: var(--text-secondary);
  cursor: pointer;
  text-decoration: none;
  transition: color 0.15s;
}
.topbar-link:hover { color: var(--primary); }

/* ── Disclaimer strip ── */
.disclaimer {
  background: #FFF7ED;
  border-left: 3px solid var(--accent);
  border-bottom: 1px solid var(--border);
  padding: 0.45rem 1.25rem;
  font-size: 0.78rem;
  color: #92400E;
  font-weight: 500;
}
[data-theme="dark"] .disclaimer {
  background: #1C1400;
  color: #FCD34D;
}

/* ── Card ── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  margin: 1rem 0;
  box-shadow: var(--shadow);
}

/* ── Agent Stepper ── */
.stepper {
  display: flex;
  align-items: center;
  gap: 0;
  margin: 1.25rem 0 0.5rem;
  overflow-x: auto;
}
.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  min-width: 72px;
  cursor: pointer;
}
.step-node {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2.5px solid var(--border);
  background: var(--surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--text-secondary);
  transition: all 0.25s ease-out;
  position: relative;
  z-index: 1;
}
.step-node.active {
  border-color: var(--primary);
  background: var(--primary);
  color: #fff;
  box-shadow: 0 0 0 4px rgba(15,118,110,0.15);
}
.step-node.done {
  border-color: var(--primary);
  background: var(--primary);
  color: #fff;
}
.step-node.eval-pass { border-color: var(--success); background: var(--success); }
.step-node.eval-fail { border-color: var(--danger); background: var(--danger); }
.step-label {
  font-size: 0.65rem;
  margin-top: 0.35rem;
  color: var(--text-secondary);
  text-align: center;
  white-space: nowrap;
  font-weight: 500;
}
.step-label.active { color: var(--primary); font-weight: 600; }
.step-connector {
  flex: 1;
  height: 2px;
  background: var(--border);
  margin-bottom: 18px;
  transition: background 0.25s;
}
.step-connector.done { background: var(--primary); }

/* ── Badge ── */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-success { background: #DCFCE7; color: #15803D; }
.badge-warning { background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; }
.badge-danger  { background: #FEE2E2; color: #991B1B; }
[data-theme="dark"] .badge-success { background: #14532D; color: #86EFAC; }
[data-theme="dark"] .badge-warning { background: #451A03; color: #FCD34D; }
[data-theme="dark"] .badge-danger  { background: #450A0A; color: #FCA5A5; }

/* ── Citation pill ── */
.citation-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.55rem;
  border: 1px solid var(--primary);
  border-radius: 6px;
  font-size: 0.72rem;
  color: var(--primary);
  font-family: var(--mono);
  background: rgba(15,118,110,0.06);
  margin: 0.15rem 0.15rem 0 0;
  transition: transform 0.15s, background 0.15s;
  cursor: pointer;
}
.citation-pill:hover {
  transform: scale(1.03);
  background: rgba(15,118,110,0.12);
}

/* ── Citation excerpt ── */
.citation-excerpt {
  font-family: var(--mono);
  font-size: 0.75rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-left: 3px solid var(--primary);
  border-radius: 6px;
  padding: 0.65rem 0.85rem;
  margin: 0.35rem 0;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* ── Message bubbles ── */
.user-bubble {
  display: flex;
  justify-content: flex-end;
  margin: 0.6rem 0;
  animation: fadeUp 0.2s ease-out;
}
.user-bubble-inner {
  background: rgba(15,118,110,0.12);
  border: 1px solid rgba(15,118,110,0.2);
  border-radius: 16px 16px 4px 16px;
  padding: 0.7rem 1rem;
  max-width: 85%;
  font-size: 0.92rem;
  color: var(--text-primary);
}
.agent-bubble {
  margin: 0.6rem 0;
  animation: fadeUp 0.2s ease-out;
}

/* ── Buttons ── */
.btn-primary {
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.55rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
  font-family: 'Inter', sans-serif;
}
.btn-primary:hover { background: var(--primary-hover); transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-accent {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.55rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
  font-family: 'Inter', sans-serif;
}
.btn-accent:hover { background: var(--accent-hover); transform: translateY(-1px); }

.btn-ghost {
  background: transparent;
  color: var(--primary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.4rem 0.9rem;
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  font-family: 'Inter', sans-serif;
}
.btn-ghost:hover { border-color: var(--primary); background: rgba(15,118,110,0.06); }

/* ── Quiz card ── */
.quiz-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.1rem 1.3rem;
  margin: 0.75rem 0;
  box-shadow: var(--shadow);
}
.quiz-question-text {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
}
.quiz-option {
  padding: 0.5rem 0.8rem;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  margin: 0.3rem 0;
  font-size: 0.88rem;
  cursor: pointer;
  transition: all 0.15s;
}
.quiz-option:hover { border-color: var(--primary); background: rgba(15,118,110,0.05); }
.quiz-option.correct {
  border-color: var(--success);
  background: #DCFCE7;
  color: #14532D;
  font-weight: 600;
}
.quiz-option.incorrect {
  border-color: var(--danger);
  background: #FEE2E2;
  color: #991B1B;
}
.quiz-explanation {
  margin-top: 0.75rem;
  padding: 0.6rem 0.85rem;
  background: var(--bg);
  border-left: 3px solid var(--primary);
  border-radius: 6px;
  font-size: 0.83rem;
  color: var(--text-secondary);
  line-height: 1.55;
}

/* ── Upload zone ── */
.upload-zone {
  border: 2px dashed var(--border);
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.88rem;
  margin: 0.75rem 0;
  transition: border-color 0.2s;
  background: var(--bg);
}
.upload-zone:hover { border-color: var(--primary); }

/* ── Loading dots ── */
@keyframes pulse-dot {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.5; }
  40%           { transform: scale(1.0); opacity: 1.0; }
}
.loading-dots span {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
  margin: 0 3px;
  animation: pulse-dot 1.2s infinite;
}
.loading-dots span:nth-child(2) { animation-delay: 0.15s; }
.loading-dots span:nth-child(3) { animation-delay: 0.30s; }

/* ── Animations ── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}

/* ── Streamlit widget overrides ── */
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stTextArea"] textarea {
  border-radius: 8px !important;
  border: 1.5px solid var(--border) !important;
  font-family: 'Inter', sans-serif !important;
}
div[data-testid="stTextInput"] > div > div > input:focus,
div[data-testid="stTextArea"] textarea:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px rgba(15,118,110,0.15) !important;
}
button[kind="primary"] {
  background: var(--primary) !important;
  border: none !important;
  border-radius: 8px !important;
  font-family: 'Inter', sans-serif !important;
}
button[kind="secondary"] {
  border-radius: 8px !important;
  font-family: 'Inter', sans-serif !important;
}
div[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}
</style>
"""

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def init_session():
    defaults = {
        "messages": [],          # list of {role, content, data}
        "dark_mode": False,
        "show_about": False,
        "image_data": None,      # bytes
        "image_name": None,      # str
        "running": False,
        "quiz_data": None,       # QuizResponse dict
        "quiz_answers": {},      # {q_idx: selected_option_label}
        "quiz_submitted": set(), # set of q_idx already submitted
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ---------------------------------------------------------------------------
# Theme token
# ---------------------------------------------------------------------------
THEME_ATTR = 'data-theme="dark"' if st.session_state.dark_mode else ""

# ---------------------------------------------------------------------------
# API / Standalone helpers
# ---------------------------------------------------------------------------

def call_ask_api(query: str, image_bytes: Optional[bytes], image_name: Optional[str]) -> Dict[str, Any]:
    """Call the FastAPI /ask endpoint (or run_graph directly in standalone mode)."""
    if STANDALONE_MODE:
        from app.graph import run_graph
        import tempfile, os as _os
        image_path = ""
        tmp = None
        if image_bytes:
            suffix = Path(image_name or "img.png").suffix or ".png"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(image_bytes)
            tmp.close()
            image_path = tmp.name
        try:
            result = run_graph(user_query=query, image_path=image_path, generate_quiz=False)
        finally:
            if tmp:
                try: _os.unlink(tmp.name)
                except Exception: pass
        return _normalize_standalone_ask(result, query)
    else:
        import requests
        files = {}
        data = {"query": query}
        if image_bytes:
            files["image"] = (image_name or "upload.png", image_bytes)
        try:
            resp = requests.post(f"{BACKEND_URL}/api/v1/ask", data=data, files=files or None, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            # Fallback to standalone
            st.warning("⚠️ Backend not reachable — running in standalone mode.")
            from app.graph import run_graph
            result = run_graph(user_query=query, generate_quiz=False)
            return _normalize_standalone_ask(result, query)
        except Exception as e:
            raise RuntimeError(str(e))


def call_quiz_api(topic: str) -> Dict[str, Any]:
    """Call the FastAPI /quiz endpoint (or run_graph directly in standalone mode)."""
    if STANDALONE_MODE:
        from app.graph import run_graph
        result = run_graph(user_query=f"Explain: {topic}", generate_quiz=True)
        return _normalize_standalone_quiz(result, topic)
    else:
        import requests
        try:
            resp = requests.post(f"{BACKEND_URL}/api/v1/quiz", data={"topic": topic}, timeout=120)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            st.warning("⚠️ Backend not reachable — running in standalone mode.")
            from app.graph import run_graph
            result = run_graph(user_query=f"Explain: {topic}", generate_quiz=True)
            return _normalize_standalone_quiz(result, topic)
        except Exception as e:
            raise RuntimeError(str(e))


def _normalize_standalone_ask(result: Dict, query: str) -> Dict:
    """Normalise run_graph() result to match FastAPI AskResponse format."""
    chunks = result.get("retrieved_chunks", [])
    eval_r = result.get("evaluation_result", {})
    return {
        "question": query,
        "answer": result.get("final_response") or result.get("draft_explanation") or "",
        "input_type": result.get("input_type", "text"),
        "image_caption": result.get("image_caption"),
        "citations": [
            {
                "source": c.get("source", "Unknown"),
                "page": int(c.get("page", 0)),
                "content_preview": c.get("content", "")[:300],
            }
            for c in chunks
        ],
        "evaluation": {
            "grounded_score": float(eval_r.get("grounded_score", 0)),
            "is_faithful": bool(eval_r.get("is_faithful", False)),
            "reasoning": str(eval_r.get("reasoning", "")),
        } if eval_r else None,
        "warning": None,
        "thread_id": "standalone",
    }


def _normalize_standalone_quiz(result: Dict, topic: str) -> Dict:
    """Normalise run_graph() result to match FastAPI QuizResponse format."""
    raw_qs = result.get("quiz_questions", [])
    labels = ["A", "B", "C", "D", "E"]
    questions = []
    for q in raw_qs:
        opts = q.get("options", [])
        questions.append({
            "question": q.get("question", ""),
            "options": [
                {"label": labels[i], "text": opt.lstrip("ABCDE. ")}
                for i, opt in enumerate(opts) if i < len(labels)
            ],
            "correct_answer": str(q.get("correct_answer", "")),
            "explanation": str(q.get("explanation", "")),
        })
    return {"topic": topic, "questions": questions, "thread_id": "standalone"}


# ---------------------------------------------------------------------------
# Stepper renderer
# ---------------------------------------------------------------------------

STEP_LABELS = ["Router", "Caption", "Retrieve", "Explain", "Evaluate"]
STEP_ICONS  = ["🔀", "📷", "🔍", "💡", "✅"]

def render_stepper(completed_steps: int, eval_pass: Optional[bool] = None):
    """Render the horizontal agent stepper. completed_steps: how many steps done (0–5)."""
    nodes_html = []
    for i, (label, icon) in enumerate(zip(STEP_LABELS, STEP_ICONS)):
        step_num = i + 1
        is_done = step_num < completed_steps
        is_active = step_num == completed_steps

        # Connector
        if i > 0:
            conn_class = "done" if is_done or is_active else ""
            nodes_html.append(f'<div class="step-connector {conn_class}"></div>')

        # Node class
        if i == 4 and is_done:  # Evaluator (last)
            if eval_pass is True:
                node_class = "eval-pass"
                icon = "✅"
            elif eval_pass is False:
                node_class = "eval-fail"
                icon = "⚠️"
            else:
                node_class = "done"
        elif is_done:
            node_class = "done"
        elif is_active:
            node_class = "active"
        else:
            node_class = ""

        label_class = "active" if is_active else ""
        nodes_html.append(
            f'<div class="step">'
            f'  <div class="step-node {node_class}">{icon}</div>'
            f'  <div class="step-label {label_class}">{label}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="stepper">{"".join(nodes_html)}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Chat message renderers
# ---------------------------------------------------------------------------

def render_user_message(content: str, image_name: Optional[str] = None):
    img_html = f'<div style="font-size:0.75rem;color:var(--text-secondary);margin-bottom:0.25rem">📎 {image_name}</div>' if image_name else ""
    st.markdown(
        f'<div class="user-bubble">'
        f'  <div class="user-bubble-inner">'
        f'    {img_html}'
        f'    {content}'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_agent_response(data: Dict[str, Any], msg_idx: int):
    """Render a full agent response card with stepper, badges, citations, answer."""
    answer = data.get("answer", "")
    input_type = data.get("input_type", "text")
    image_caption = data.get("image_caption")
    citations = data.get("citations", [])
    evaluation = data.get("evaluation")
    warning = data.get("warning")

    # Determine eval pass/fail
    eval_pass = None
    if evaluation:
        eval_pass = bool(evaluation.get("is_faithful", False))

    # Stepper — all 5 done for a complete response
    # Caption step only applies for image inputs
    steps_done = 5
    if input_type == "text":
        steps_done = 5  # router+retrieve+explain+eval (caption skipped but we still show 5)

    with st.container():
        st.markdown('<div class="agent-bubble">', unsafe_allow_html=True)

        # Stepper
        render_stepper(steps_done + 1, eval_pass=eval_pass)

        # Grounding badge
        badge_col, _ = st.columns([3, 1])
        with badge_col:
            if evaluation:
                score = evaluation.get("grounded_score", 0)
                if eval_pass:
                    st.markdown(
                        f'<span class="badge badge-success">✅ Grounded ({score:.0%})</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<span class="badge badge-warning">⚠️ Low Confidence ({score:.0%})</span>',
                        unsafe_allow_html=True,
                    )

        # Warning strip
        if warning:
            st.warning(warning)

        # Image caption (if image was used)
        if image_caption:
            with st.expander("📷 Image Caption", expanded=False):
                st.markdown(
                    f'<div class="citation-excerpt">{image_caption}</div>',
                    unsafe_allow_html=True,
                )

        # Main answer card
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(answer, unsafe_allow_html=False)
        st.markdown('</div>', unsafe_allow_html=True)

        # Action row: Copy + Regenerate
        copy_col, regen_col, _ = st.columns([1, 1, 4])
        with copy_col:
            if st.button("📋 Copy", key=f"copy_{msg_idx}", help="Copy answer to clipboard"):
                # JS clipboard copy workaround
                js = f"""<script>
                navigator.clipboard.writeText({json.dumps(answer)}).then(
                    () => console.log('Copied'),
                    () => console.error('Copy failed')
                );
                </script>"""
                st.markdown(js, unsafe_allow_html=True)
                st.toast("Answer copied!", icon="📋")
        with regen_col:
            if evaluation and not eval_pass:
                if st.button("🔄 Regenerate", key=f"regen_{msg_idx}", help="Re-run with more context"):
                    st.session_state["regen_request"] = data.get("question", "")
                    st.rerun()

        # Citations
        if citations:
            with st.expander(f"📚 View Sources ({len(citations)})", expanded=False):
                for i, cit in enumerate(citations):
                    src = cit.get("source", "Unknown")
                    page = cit.get("page", 0)
                    preview = cit.get("content_preview", "")
                    st.markdown(
                        f'<span class="citation-pill">📄 {src} · p.{page}</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="citation-excerpt">{preview}</div>',
                        unsafe_allow_html=True,
                    )

        # Agent trace (collapsible)
        if evaluation:
            with st.expander("🔍 Agent Trace — Evaluator Output", expanded=False):
                st.markdown(
                    f'<div class="citation-excerpt">'
                    f'<strong>Grounded Score:</strong> {evaluation.get("grounded_score", 0):.2f}<br>'
                    f'<strong>Faithful:</strong> {evaluation.get("is_faithful", False)}<br>'
                    f'<strong>Reasoning:</strong> {evaluation.get("reasoning", "")}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Quiz renderer
# ---------------------------------------------------------------------------

def render_quiz(quiz_data: Dict[str, Any]):
    """Render the interactive MCQ quiz with immediate feedback."""
    topic = quiz_data.get("topic", "")
    questions = quiz_data.get("questions", [])

    st.markdown(
        f'<div class="card"><h3 style="color:var(--accent);margin:0 0 0.25rem">🧠 Quiz: {topic}</h3>'
        f'<p style="color:var(--text-secondary);font-size:0.82rem;margin:0">'
        f'Select the best answer for each question.</p></div>',
        unsafe_allow_html=True,
    )

    for i, q in enumerate(questions):
        qtext = q.get("question", "")
        options = q.get("options", [])
        correct = q.get("correct_answer", "")
        explanation = q.get("explanation", "")

        already_submitted = i in st.session_state.quiz_submitted

        st.markdown(f'<div class="quiz-card">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="quiz-question-text">Q{i+1}. {qtext}</div>',
            unsafe_allow_html=True,
        )

        if not already_submitted:
            # Show radio choices
            opt_labels = [f"{o['label']}. {o['text']}" for o in options]
            selected = st.radio(
                "Choose your answer:",
                opt_labels,
                key=f"quiz_q{i}",
                label_visibility="collapsed",
            )
            if st.button("Submit Answer", key=f"quiz_submit_{i}"):
                selected_label = selected[0] if selected else ""
                st.session_state.quiz_answers[i] = selected_label
                st.session_state.quiz_submitted.add(i)
                st.rerun()
        else:
            # Show feedback
            selected_label = st.session_state.quiz_answers.get(i, "")
            # Normalise correct answer label (may be "A" or "A. text" or full text)
            correct_label = correct.strip()[0].upper() if correct else ""

            for o in options:
                lbl = o["label"]
                txt = o["text"]
                is_correct = (lbl == correct_label)
                is_selected = (lbl == selected_label)

                if is_correct:
                    opt_class = "quiz-option correct"
                    prefix = "✅ "
                elif is_selected and not is_correct:
                    opt_class = "quiz-option incorrect"
                    prefix = "❌ "
                else:
                    opt_class = "quiz-option"
                    prefix = ""

                st.markdown(
                    f'<div class="{opt_class}">{prefix}<strong>{lbl}.</strong> {txt}</div>',
                    unsafe_allow_html=True,
                )

            if explanation:
                st.markdown(
                    f'<div class="quiz-explanation">💡 <strong>Explanation:</strong> {explanation}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# About modal
# ---------------------------------------------------------------------------

def render_about_modal():
    with st.expander("ℹ️ About MedLearn Agent", expanded=True):
        st.markdown("""
**MedLearn Agent** is a multimodal, RAG-powered educational assistant for anatomy & physiology.

**How it works:**
1. 🔀 **Router** — Detects if input is text, image, or both
2. 📷 **Captioner** — Generates anatomical description from medical images (BLIP-2)
3. 🔍 **Retriever** — Finds relevant passages from OpenStax Anatomy & Physiology
4. 💡 **Explainer** — Synthesises a cited educational explanation (Gemini)
5. ✅ **Evaluator** — Checks groundedness against retrieved sources

**Data Sources:**
- [OpenStax Anatomy and Physiology](https://openstax.org/details/books/anatomy-and-physiology-2e) — CC BY 4.0

**Disclaimer:** This tool is for educational purposes only.
It does **not** provide medical diagnosis, treatment advice, or clinical guidance.
Always consult a qualified healthcare professional for medical concerns.
        """)


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

# Inject fonts + CSS
st.markdown(GOOGLE_FONTS, unsafe_allow_html=True)
st.markdown(CSS, unsafe_allow_html=True)

# Theme wrapper (applied via CSS class on root — workaround via st.markdown)
if st.session_state.dark_mode:
    st.markdown(
        '<script>document.documentElement.setAttribute("data-theme","dark")</script>',
        unsafe_allow_html=True,
    )

# ── Top bar ────────────────────────────────────────────────────────────────
col_logo, col_actions = st.columns([3, 2])
with col_logo:
    st.markdown(
        '<div class="topbar-logo">🩺 MedLearn Agent</div>',
        unsafe_allow_html=True,
    )
with col_actions:
    tc1, tc2, tc3 = st.columns([1, 1, 1])
    with tc1:
        dark_label = "☀️ Light" if st.session_state.dark_mode else "🌙 Dark"
        if st.button(dark_label, key="toggle_dark", help="Toggle dark/light mode"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    with tc2:
        if st.button("ℹ️ About", key="about_btn"):
            st.session_state.show_about = not st.session_state.show_about
            st.rerun()
    with tc3:
        if st.button("🔄 New", key="new_session", help="Clear chat and start a new session"):
            for k in ["messages", "image_data", "image_name", "quiz_data",
                      "quiz_answers", "quiz_submitted", "running"]:
                st.session_state[k] = [] if isinstance(st.session_state.get(k), list) else (
                    {} if isinstance(st.session_state.get(k), dict) else (
                    set() if isinstance(st.session_state.get(k), set) else None
                ))
            st.session_state["messages"] = []
            st.rerun()

# ── Disclaimer strip ──────────────────────────────────────────────────────
st.markdown(
    '<div class="disclaimer">⚕️ Educational tool only — not medical advice. '
    'Always consult a qualified healthcare professional for clinical guidance.</div>',
    unsafe_allow_html=True,
)

# ── About modal ────────────────────────────────────────────────────────────
if st.session_state.show_about:
    render_about_modal()

st.markdown("<br>", unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────────────────
for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        render_user_message(msg["content"], msg.get("image_name"))
    else:
        render_agent_response(msg["data"], idx)

# ── Quiz display ───────────────────────────────────────────────────────────
if st.session_state.quiz_data:
    st.markdown("---")
    render_quiz(st.session_state.quiz_data)
    if st.button("🗑️ Clear Quiz", key="clear_quiz"):
        st.session_state.quiz_data = None
        st.session_state.quiz_answers = {}
        st.session_state.quiz_submitted = set()
        st.rerun()

# ── Input section ──────────────────────────────────────────────────────────
st.markdown("---")

# Image upload
with st.expander("📎 Attach Image (optional)", expanded=bool(st.session_state.image_data)):
    uploaded = st.file_uploader(
        "Upload a medical diagram or anatomy image",
        type=["png", "jpg", "jpeg", "webp"],
        key="image_uploader",
        label_visibility="collapsed",
    )
    if uploaded is not None:
        st.session_state.image_data = uploaded.read()
        st.session_state.image_name = uploaded.name
        st.image(st.session_state.image_data, caption=uploaded.name, width=220)
    elif st.session_state.image_data:
        col_img, col_clear = st.columns([3, 1])
        with col_img:
            st.image(st.session_state.image_data, caption=st.session_state.image_name, width=180)
        with col_clear:
            if st.button("✕ Clear", key="clear_image"):
                st.session_state.image_data = None
                st.session_state.image_name = None
                st.rerun()

# Text input
query = st.text_area(
    "Ask a medical or anatomy question…",
    placeholder="e.g. What are the four chambers of the heart and what does each do?",
    height=100,
    key="query_input",
    label_visibility="collapsed",
)

# Action buttons
btn_col1, btn_col2, _ = st.columns([2, 2, 3])
with btn_col1:
    send_clicked = st.button(
        "🔬 Ask MedLearn",
        key="send_btn",
        type="primary",
        disabled=st.session_state.running,
        use_container_width=True,
    )
with btn_col2:
    quiz_clicked = st.button(
        "🧠 Generate Quiz",
        key="quiz_btn",
        disabled=st.session_state.running or not query.strip(),
        use_container_width=True,
    )

# Handle regen request
if "regen_request" in st.session_state and st.session_state.regen_request:
    query = st.session_state.regen_request
    del st.session_state["regen_request"]
    send_clicked = True

# ── Send / Ask flow ────────────────────────────────────────────────────────
if send_clicked and query.strip():
    # Add user message to history
    st.session_state.messages.append({
        "role": "user",
        "content": query,
        "image_name": st.session_state.image_name,
    })
    st.session_state.running = True

    with st.spinner(""):
        # Animated stepper during loading
        stepper_placeholder = st.empty()
        step_labels = ["Router", "Caption", "Retrieve", "Explain", "Evaluate"]

        # Animate steps during loading
        for step_num in range(1, 6):
            if step_num == 2 and not st.session_state.image_data:
                continue  # Skip caption step for text-only
            stepper_placeholder.markdown(
                f"**Step {step_num}/5:** Running {step_labels[step_num-1]}…",
                unsafe_allow_html=True,
            )
            time.sleep(0.3)

        stepper_placeholder.empty()

        try:
            result = call_ask_api(
                query=query,
                image_bytes=st.session_state.image_data,
                image_name=st.session_state.image_name,
            )
            st.session_state.messages.append({
                "role": "agent",
                "content": result.get("answer", ""),
                "data": result,
            })
        except Exception as e:
            st.error(f"❌ Error: {e}")

    st.session_state.running = False
    # Clear image after sending
    st.session_state.image_data = None
    st.session_state.image_name = None
    st.rerun()

# ── Quiz generation flow ───────────────────────────────────────────────────
if quiz_clicked and query.strip():
    st.session_state.running = True
    st.session_state.quiz_answers = {}
    st.session_state.quiz_submitted = set()

    with st.spinner("Generating quiz questions…"):
        try:
            quiz_result = call_quiz_api(topic=query)
            st.session_state.quiz_data = quiz_result
        except Exception as e:
            st.error(f"❌ Quiz error: {e}")

    st.session_state.running = False
    st.rerun()
