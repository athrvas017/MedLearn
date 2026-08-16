"""
evals/ragas_eval.py
===================
Micro-Task 3.2 — RAGAS Integration & Benchmark Runner Script
--------------------------------------------------------------
Evaluates the MedLearn agent pipeline against the benchmark test cases
in ``evals/test_cases.json`` using RAGAS metrics:

  - **Faithfulness**: Are the generated facts supported by retrieved context?
  - **Answer Relevancy**: Does the answer address the question?
  - **Context Precision**: Are the most relevant contexts ranked highest?

Two operating modes
-------------------
1. **Full pipeline mode** (default): Runs every test case through the
   live LangGraph pipeline (``app.graph.run_graph``) to get real
   answers + real retrieved context, then evaluates with RAGAS.

2. **Ground-truth mode** (``--ground-truth``): Evaluates using the
   pre-written ground-truth answers and reference contexts from the
   test-cases file — useful for validating the evaluation harness
   itself without burning LLM quota.

Usage
-----
    # Run on 2 sample cases (quick smoke test)
    python evals/ragas_eval.py --sample 2

    # Full benchmark (all test cases)
    python evals/ragas_eval.py

    # Ground-truth mode (no LLM calls, validates eval harness)
    python evals/ragas_eval.py --ground-truth

    # Export results to JSON
    python evals/ragas_eval.py --output evals/results.json

Verification
------------
    python evals/ragas_eval.py --sample 2
    → Console metrics table: Faithfulness: 0.XX, Answer Relevancy: 0.XX
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Ensure repo root on sys.path
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Fix Windows console encoding for emoji/Unicode output
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_CASES_PATH = REPO_ROOT / "evals" / "test_cases.json"
RESULTS_DIR = REPO_ROOT / "evals" / "results"
FAITHFULNESS_TARGET = 0.80  # PRD success metric


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_test_cases(path: Path = TEST_CASES_PATH) -> List[Dict[str, Any]]:
    """Load benchmark test cases from JSON file."""
    if not path.exists():
        raise FileNotFoundError(
            f"Test cases not found at '{path}'. "
            "Please create evals/test_cases.json first (Micro-Task 3.1)."
        )
    with open(path, "r", encoding="utf-8") as f:
        cases = json.load(f)
    logger.info("Loaded %d test cases from '%s'.", len(cases), path.name)
    return cases


# ---------------------------------------------------------------------------
# Pipeline Execution — Run each test case through the MedLearn graph
# ---------------------------------------------------------------------------

def run_pipeline_on_cases(
    test_cases: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Execute each test case through the live LangGraph pipeline and collect
    the results needed for RAGAS evaluation.

    Returns a list of dicts with keys:
        question, answer, contexts, ground_truth
    """
    # Late import to avoid loading heavy modules unless needed
    from app.graph import run_graph

    eval_samples: List[Dict[str, Any]] = []

    for i, tc in enumerate(test_cases, start=1):
        question = tc["question"]
        ground_truth = tc["ground_truth"]
        tc_id = tc.get("id", f"tc-{i:03d}")

        logger.info("[%d/%d] Running pipeline for: %s", i, len(test_cases), tc_id)
        start = time.time()

        try:
            result = run_graph(
                user_query=question,
                image_path="",
                generate_quiz=False,
                thread_id=f"eval-{tc_id}",
            )
            elapsed = time.time() - start

            # Extract answer and contexts from pipeline result
            answer = result.get("final_response", result.get("draft_explanation", ""))
            retrieved_chunks = result.get("retrieved_chunks", [])
            contexts = [c.get("content", "") for c in retrieved_chunks if c.get("content")]

            # Also capture internal evaluation result for comparison
            eval_result = result.get("evaluation_result", {})

            logger.info(
                "  [%s] Done in %.1fs | chunks=%d | internal_score=%.2f",
                tc_id, elapsed, len(contexts),
                eval_result.get("grounded_score", -1),
            )

        except Exception as exc:
            logger.error("  [%s] Pipeline failed: %s", tc_id, exc)
            answer = f"Error: {exc}"
            contexts = []
            eval_result = {}
            elapsed = -1

        eval_samples.append({
            "question": question,
            "answer": answer,
            "contexts": contexts if contexts else ["No context retrieved."],
            "ground_truth": ground_truth,
            "metadata": {
                "id": tc_id,
                "topic": tc.get("topic", ""),
                "difficulty": tc.get("difficulty", ""),
                "elapsed_seconds": round(elapsed, 2),
                "internal_eval": eval_result,
            },
        })

    return eval_samples


def build_ground_truth_samples(
    test_cases: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Build evaluation samples from the ground-truth data in test_cases.json
    (no LLM calls needed). Useful for validating the RAGAS harness.
    """
    eval_samples: List[Dict[str, Any]] = []
    for i, tc in enumerate(test_cases, start=1):
        tc_id = tc.get("id", f"tc-{i:03d}")
        eval_samples.append({
            "question": tc["question"],
            "answer": tc["ground_truth"],  # Use ground truth as the answer
            "contexts": tc.get("reference_contexts", ["No reference context."]),
            "ground_truth": tc["ground_truth"],
            "metadata": {
                "id": tc_id,
                "topic": tc.get("topic", ""),
                "difficulty": tc.get("difficulty", ""),
                "elapsed_seconds": 0,
                "internal_eval": {},
            },
        })
    return eval_samples


# ---------------------------------------------------------------------------
# RAGAS Evaluation
# ---------------------------------------------------------------------------

def run_ragas_evaluation(
    eval_samples: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Run RAGAS metrics (faithfulness, answer_relevancy, context_precision)
    on the collected evaluation samples.

    Falls back to the project's own Gemini-based evaluator if RAGAS
    is not available or has broken dependencies.

    Returns a dict with per-metric scores and per-sample details.
    """
    ragas_available = False

    # Fast pre-check: RAGAS depends on langchain_community.chat_models.vertexai
    # which is often missing. Test for this BEFORE the slow RAGAS import.
    try:
        import importlib
        importlib.import_module("langchain_community.chat_models.vertexai")
    except Exception:
        logger.warning(
            "RAGAS dependency 'langchain_community.chat_models.vertexai' missing. "
            "Skipping RAGAS — using Gemini-based evaluation."
        )
        return _run_llm_based_evaluation(eval_samples)

    try:
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            faithfulness,
        )
        from datasets import Dataset

        ragas_available = True
    except Exception as exc:
        logger.warning(
            "RAGAS not available (%s: %s). "
            "Using Gemini-based evaluation instead.",
            type(exc).__name__, exc,
        )

    if ragas_available:
        try:
            return _run_ragas_native(eval_samples)
        except Exception as exc:
            logger.warning(
                "RAGAS native evaluation failed (%s). "
                "Falling back to Gemini-based evaluation.",
                exc,
            )

    return _run_llm_based_evaluation(eval_samples)


def _run_ragas_native(
    eval_samples: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Run evaluation using the RAGAS library."""
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        faithfulness,
    )
    from datasets import Dataset

    # Build a HuggingFace Dataset in the format RAGAS expects
    ragas_data = {
        "question": [s["question"] for s in eval_samples],
        "answer": [s["answer"] for s in eval_samples],
        "contexts": [s["contexts"] for s in eval_samples],
        "ground_truth": [s["ground_truth"] for s in eval_samples],
    }

    dataset = Dataset.from_dict(ragas_data)

    logger.info("Running RAGAS evaluation on %d samples…", len(eval_samples))
    start = time.time()

    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision],
    )

    elapsed = time.time() - start
    logger.info("RAGAS evaluation completed in %.1fs.", elapsed)

    # Extract aggregate scores
    scores = {
        "faithfulness": round(result["faithfulness"], 4),
        "answer_relevancy": round(result["answer_relevancy"], 4),
        "context_precision": round(result["context_precision"], 4),
    }

    # Per-sample scores from the result dataframe
    per_sample = []
    if hasattr(result, "to_pandas"):
        df = result.to_pandas()
        for idx, row in df.iterrows():
            per_sample.append({
                "question": row.get("question", eval_samples[idx]["question"]),
                "faithfulness": round(float(row.get("faithfulness", 0)), 4),
                "answer_relevancy": round(float(row.get("answer_relevancy", 0)), 4),
                "context_precision": round(float(row.get("context_precision", 0)), 4),
                "metadata": eval_samples[idx].get("metadata", {}),
            })

    return {
        "aggregate": scores,
        "per_sample": per_sample,
        "num_samples": len(eval_samples),
        "evaluation_time_seconds": round(elapsed, 2),
        "method": "ragas_native",
    }


def _run_llm_based_evaluation(
    eval_samples: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluation using the project's own Gemini-based evaluator when RAGAS
    is unavailable. Computes three metrics via LLM:

      - Faithfulness:       reuses app/agents/evaluator.py (grounded_score)
      - Answer Relevancy:   Gemini LLM judges how well the answer addresses the question
      - Context Precision:  Gemini LLM judges how relevant the retrieved contexts are
    """
    from app.agents.evaluator import evaluator_node

    logger.info(
        "Running Gemini-based evaluation on %d samples...",
        len(eval_samples),
    )
    start = time.time()

    faithfulness_scores: List[float] = []
    relevancy_scores: List[float] = []
    precision_scores: List[float] = []
    per_sample: List[Dict[str, Any]] = []

    for i, sample in enumerate(eval_samples, start=1):
        tc_id = sample["metadata"].get("id", "?")
        logger.info("  [%d/%d] Evaluating: %s", i, len(eval_samples), tc_id)

        # --- 1. Faithfulness (via existing evaluator) ---
        eval_state = {
            "draft_explanation": sample["answer"],
            "retrieved_chunks": [
                {"content": ctx, "source": "benchmark", "page": 0}
                for ctx in sample["contexts"]
            ],
        }

        try:
            eval_result = evaluator_node(eval_state)
            eval_data = eval_result.get("evaluation_result", {})
            faith_score = float(eval_data.get("grounded_score", 0.5))
        except Exception as exc:
            logger.error("  Faithfulness eval failed: %s", exc)
            faith_score = 0.5

        # --- 2. Answer Relevancy (Gemini LLM) ---
        relevancy = _gemini_answer_relevancy(
            sample["question"], sample["answer"]
        )

        # --- 3. Context Precision (keyword-based, fast) ---
        precision = _compute_context_precision(
            sample["question"], sample["ground_truth"], sample["contexts"]
        )

        faithfulness_scores.append(faith_score)
        relevancy_scores.append(relevancy)
        precision_scores.append(precision)

        per_sample.append({
            "question": sample["question"],
            "faithfulness": round(faith_score, 4),
            "answer_relevancy": round(relevancy, 4),
            "context_precision": round(precision, 4),
            "metadata": sample.get("metadata", {}),
        })

        logger.info(
            "  [%s] faith=%.2f  relev=%.2f  prec=%.2f",
            tc_id, faith_score, relevancy, precision,
        )

    elapsed = time.time() - start

    avg_faith = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0
    avg_relevancy = sum(relevancy_scores) / len(relevancy_scores) if relevancy_scores else 0
    avg_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0

    return {
        "aggregate": {
            "faithfulness": round(avg_faith, 4),
            "answer_relevancy": round(avg_relevancy, 4),
            "context_precision": round(avg_precision, 4),
        },
        "per_sample": per_sample,
        "num_samples": len(eval_samples),
        "evaluation_time_seconds": round(elapsed, 2),
        "method": "gemini_based",
    }


def _gemini_answer_relevancy(question: str, answer: str) -> float:
    """
    Use Gemini to score how well the answer addresses the question (0.0-1.0).
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            temperature=0.1,
            max_output_tokens=64,
        )

        prompt = (
            f"Question: {question}\n\n"
            f"Answer: {answer[:1500]}\n\n"
            "Rate how well the answer addresses the question on a scale of 0.0 to 1.0. "
            "Return ONLY a single decimal number, nothing else."
        )

        response = llm.invoke([
            SystemMessage(content="You are a strict answer-relevancy scorer. Return only a float."),
            HumanMessage(content=prompt),
        ])

        score = float(response.content.strip())
        return max(0.0, min(1.0, score))

    except Exception as exc:
        logger.error("  Answer relevancy LLM call failed: %s", exc)
        # Fall back to keyword overlap
        return _compute_keyword_relevancy(question, answer)


def _compute_context_precision(
    question: str,
    ground_truth: str,
    contexts: List[str],
) -> float:
    """
    Compute context precision: what fraction of retrieved contexts are
    actually relevant to answering the question correctly.

    Uses keyword overlap between each context and the ground truth answer
    as a proxy for relevance. A context is considered relevant if it shares
    significant terminology with the ground truth.
    """
    if not contexts:
        return 0.0

    gt_words = {
        w.lower().strip(".,;:!?\"'()")
        for w in ground_truth.split()
        if len(w) > 3
    }

    if not gt_words:
        return 0.5

    relevant_count = 0
    for ctx in contexts:
        ctx_lower = ctx.lower()
        overlap = sum(1 for w in gt_words if w in ctx_lower)
        # Consider context relevant if it overlaps with >= 15% of ground truth terms
        if overlap / len(gt_words) >= 0.15:
            relevant_count += 1

    return relevant_count / len(contexts)


def _compute_keyword_relevancy(question: str, answer: str) -> float:
    """
    Simple keyword-overlap relevancy score (0.0–1.0).
    Counts how many significant words from the question appear in the answer.
    """
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "what", "how", "why",
        "when", "where", "which", "who", "do", "does", "did", "and", "or",
        "but", "in", "on", "at", "to", "for", "of", "with", "by", "from",
        "that", "this", "it", "its", "be", "been", "being", "have", "has",
        "had", "can", "could", "will", "would", "shall", "should", "may",
        "might", "must", "not", "no", "so", "if", "than", "then", "also",
        "about", "up", "out", "just", "into", "over", "after", "between",
    }

    q_words = {
        w.lower().strip("?.!,;:")
        for w in question.split()
        if w.lower().strip("?.!,;:") not in stop_words and len(w) > 2
    }

    if not q_words:
        return 0.5

    answer_lower = answer.lower()
    matches = sum(1 for w in q_words if w in answer_lower)

    return min(1.0, matches / len(q_words))


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_results(results: Dict[str, Any]) -> None:
    """Pretty-print evaluation results to the console."""
    agg = results["aggregate"]
    method = results.get("method", "unknown")
    n = results["num_samples"]
    elapsed = results["evaluation_time_seconds"]

    print("\n" + "=" * 64)
    print("  MedLearn Agent — RAGAS Benchmark Results")
    print("=" * 64)
    print(f"  Method          : {method}")
    print(f"  Samples         : {n}")
    print(f"  Evaluation Time : {elapsed:.1f}s")
    print("-" * 64)

    # Aggregate metrics
    print("\n  📊 Aggregate Metrics:")
    print(f"     Faithfulness      : {agg['faithfulness']:.4f}")
    print(f"     Answer Relevancy  : {agg['answer_relevancy']:.4f}")
    if agg.get("context_precision") is not None:
        print(f"     Context Precision : {agg['context_precision']:.4f}")
    else:
        print(f"     Context Precision : N/A (fallback mode)")

    # Faithfulness target check
    faith = agg["faithfulness"]
    target_met = faith >= FAITHFULNESS_TARGET
    status = "✅ PASS" if target_met else "❌ FAIL"
    print(f"\n  🎯 Faithfulness Target (≥ {FAITHFULNESS_TARGET}): {status}")

    # Per-sample breakdown
    per_sample = results.get("per_sample", [])
    if per_sample:
        print("\n" + "-" * 64)
        print("  Per-Sample Breakdown:")
        print(f"  {'ID':<10} {'Faith':>8} {'Relev':>8} {'CtxPr':>8} {'Topic':<14} {'Diff':<10}")
        print("  " + "-" * 60)
        for s in per_sample:
            meta = s.get("metadata", {})
            tc_id = meta.get("id", "?")
            topic = meta.get("topic", "?")
            diff = meta.get("difficulty", "?")
            faith_s = f"{s['faithfulness']:.4f}" if s.get("faithfulness") is not None else "N/A"
            relev_s = f"{s['answer_relevancy']:.4f}" if s.get("answer_relevancy") is not None else "N/A"
            prec_s = f"{s['context_precision']:.4f}" if s.get("context_precision") is not None else "N/A"
            print(f"  {tc_id:<10} {faith_s:>8} {relev_s:>8} {prec_s:>8} {topic:<14} {diff:<10}")

    print("\n" + "=" * 64 + "\n")


def save_results(
    results: Dict[str, Any],
    output_path: Optional[str] = None,
) -> str:
    """Save evaluation results to a JSON file."""
    if output_path is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(RESULTS_DIR / f"eval_{timestamp}.json")

    # Add metadata
    results["timestamp"] = datetime.now().isoformat()
    results["faithfulness_target"] = FAITHFULNESS_TARGET
    results["target_met"] = (
        results["aggregate"]["faithfulness"] >= FAITHFULNESS_TARGET
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    logger.info("Results saved to '%s'.", output)
    return str(output)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MedLearn RAGAS Benchmark Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python evals/ragas_eval.py --sample 2          # Quick smoke test
  python evals/ragas_eval.py                     # Full benchmark
  python evals/ragas_eval.py --ground-truth      # Validate eval harness
  python evals/ragas_eval.py --output results.json
        """,
    )
    parser.add_argument(
        "--sample", "-s",
        type=int,
        default=None,
        help="Number of test cases to sample (default: all)",
    )
    parser.add_argument(
        "--ground-truth", "-g",
        action="store_true",
        help="Use ground-truth answers instead of running the pipeline",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Path to save results JSON (default: evals/results/eval_<timestamp>.json)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(name)s] %(levelname)s: %(message)s",
    )

    # Load test cases
    test_cases = load_test_cases()

    # Sample if requested
    if args.sample is not None:
        test_cases = test_cases[: args.sample]
        logger.info("Sampled %d test cases.", len(test_cases))

    # Build evaluation samples
    if args.ground_truth:
        print("\n🔬 Ground-Truth Mode — using reference answers (no LLM calls)\n")
        eval_samples = build_ground_truth_samples(test_cases)
    else:
        print("\n🚀 Pipeline Mode — running live MedLearn graph\n")
        eval_samples = run_pipeline_on_cases(test_cases)

    # Run RAGAS evaluation
    results = run_ragas_evaluation(eval_samples)

    # Display results
    print_results(results)

    # Save results
    output_path = save_results(results, args.output)
    print(f"📁 Results saved to: {output_path}\n")

    # Exit code based on faithfulness target
    if results["aggregate"]["faithfulness"] >= FAITHFULNESS_TARGET:
        print("✅ Faithfulness target met! Pipeline is performing well.\n")
        sys.exit(0)
    else:
        print(
            f"⚠️  Faithfulness ({results['aggregate']['faithfulness']:.4f}) "
            f"below target ({FAITHFULNESS_TARGET}). Consider iterating on prompts.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
