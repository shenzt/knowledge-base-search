#!/usr/bin/env python3
"""Retrieval quality eval — runs SO test cases against Qdrant index.

Two modes:
  1. Retrieval-only (default): checks if expected docs appear in top-k results
  2. RAGAS mode (--ragas): also generates answers via LLM and scores faithfulness

Usage:
  python scripts/eval_retrieval.py                    # retrieval-only
  python scripts/eval_retrieval.py --ragas             # + LLM answer + RAGAS judge
  python scripts/eval_retrieval.py --ragas --top-k 10  # custom top-k

Environment variables (RAGAS mode):
  JUDGE_API_KEY / DEEPSEEK_API_KEY  — API key for DeepSeek (answer gen + RAGAS judge)
  JUDGE_MODEL                       — judge model (default: deepseek-chat)
  JUDGE_BASE_URL                    — API base URL (default: https://api.deepseek.com)
  EMBEDDING_PROVIDER                — embedding provider for search
  QDRANT_URL                        — Qdrant endpoint (default: http://localhost:6333)
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


def load_test_cases() -> list[dict]:
    """Load SO test cases from tests/so_redis_test.py."""
    test_dir = Path(__file__).parent.parent / "tests"
    sys.path.insert(0, str(test_dir))
    from so_redis_test import SO_TEST_CASES
    return SO_TEST_CASES


def search(query: str, top_k: int = 5) -> list[dict]:
    """Dense vector search against Qdrant."""
    from embedding_provider import get_embedding_provider
    from qdrant_client import QdrantClient

    provider = get_embedding_provider()
    client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))

    q = provider.encode_query(query)
    results = client.query_points(
        collection_name="knowledge-base",
        query=q["dense_vec"],
        using="dense",
        limit=top_k,
        with_payload=True,
    )

    hits = []
    for pt in results.points:
        hits.append({
            "path": pt.payload.get("path", ""),
            "title": pt.payload.get("title", ""),
            "text": pt.payload.get("text", ""),
            "section_path": pt.payload.get("section_path", ""),
            "score": pt.score,
        })
    return hits


def check_hit(hits: list[dict], expected_paths: list[str]) -> bool:
    """Check if any hit matches any expected path fragment."""
    for hit in hits:
        path = hit.get("path", "").lower()
        for expected in expected_paths:
            if expected.lower() in path:
                return True
    return False


def generate_answer(query: str, contexts: list[str]) -> str:
    """Generate an answer from retrieved contexts using DeepSeek."""
    from openai import OpenAI

    api_key = (os.environ.get("JUDGE_API_KEY")
               or os.environ.get("DEEPSEEK_API_KEY")
               or os.environ.get("DOC_PROCESS_API_KEY", ""))
    base_url = os.environ.get("JUDGE_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("ANSWER_MODEL", os.environ.get("JUDGE_MODEL", "deepseek-chat"))

    client = OpenAI(api_key=api_key, base_url=base_url)

    context_block = "\n\n---\n\n".join(contexts[:5])
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": (
                "You are a Redis documentation assistant. Answer the question based ONLY "
                "on the provided documentation excerpts. If the docs don't contain enough "
                "information, say so. Cite the source document path when possible. "
                "Be concise and technical."
            )},
            {"role": "user", "content": (
                f"## Question\n{query}\n\n"
                f"## Retrieved Documentation\n{context_block}"
            )},
        ],
    )
    return resp.choices[0].message.content or ""


def ragas_score(query: str, answer: str, contexts: list[str]) -> dict:
    """Score answer faithfulness using RAGAS."""
    try:
        from ragas import evaluate
        from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
        from ragas.metrics import Faithfulness
        from ragas.llms import LangchainLLMWrapper
        from langchain_openai import ChatOpenAI

        api_key = (os.environ.get("JUDGE_API_KEY")
                   or os.environ.get("DEEPSEEK_API_KEY")
                   or os.environ.get("DOC_PROCESS_API_KEY", ""))
        base_url = os.environ.get("JUDGE_BASE_URL", "https://api.deepseek.com")
        model = os.environ.get("JUDGE_MODEL", "deepseek-chat")

        llm = LangchainLLMWrapper(ChatOpenAI(
            model=model, base_url=base_url, api_key=api_key or "dummy",
            temperature=0, max_tokens=4096,
        ))

        sample = SingleTurnSample(
            user_input=query,
            response=answer[:4000],
            retrieved_contexts=contexts[:5],
        )
        dataset = EvaluationDataset(samples=[sample])
        result = evaluate(dataset=dataset, metrics=[Faithfulness(llm=llm)])
        df = result.to_pandas()
        faith = float(df["faithfulness"].iloc[0])
        return {"faithfulness": round(faith, 3)}
    except Exception as e:
        log.warning(f"  RAGAS error: {e}")
        return {"faithfulness": -1, "error": str(e)[:100]}


def run_eval(top_k: int = 5, use_ragas: bool = False) -> dict:
    """Run the full evaluation."""
    cases = load_test_cases()
    log.info(f"Running {len(cases)} test cases (top_k={top_k}, ragas={use_ragas})\n")

    passed = 0
    failed = 0
    results = []
    faith_scores = []
    t0 = time.time()

    for i, tc in enumerate(cases):
        hits = search(tc["question"], top_k=top_k)
        hit = check_hit(hits, tc["expected_paths"])

        status = "PASS" if hit else "FAIL"
        passed += hit
        failed += not hit

        top_path = hits[0]["path"] if hits else "N/A"
        top_score = f"{hits[0]['score']:.3f}" if hits else "N/A"

        log.info(f"[{status}] {tc['id']} ({tc['topic']}): {tc['question'][:70]}...")
        if not hit:
            log.info(f"       Expected: {tc['expected_paths']}")
            log.info(f"       Got top-5: {[h['path'].split('/')[-1] for h in hits[:5]]}")
        else:
            log.info(f"       Top hit: {top_path} (score: {top_score})")

        entry = {
            "id": tc["id"],
            "topic": tc["topic"],
            "question": tc["question"][:200],
            "status": status,
            "hits": [{"path": h["path"], "title": h["title"], "score": h["score"]}
                     for h in hits[:5]],
        }

        # RAGAS mode: generate answer + score faithfulness
        if use_ragas and hit:
            contexts = [h["text"] for h in hits if h.get("text")]
            if not contexts:
                contexts = [f"[{h['title']}] {h['path']}" for h in hits]

            answer = generate_answer(tc["question"], contexts)
            entry["answer"] = answer[:500]
            entry["answer_length"] = len(answer)

            scores = ragas_score(tc["question"], answer, contexts)
            entry["ragas"] = scores
            if scores.get("faithfulness", -1) >= 0:
                faith_scores.append(scores["faithfulness"])
                log.info(f"       Faith: {scores['faithfulness']:.3f} | Answer: {len(answer)} chars")

        results.append(entry)

    elapsed = time.time() - t0

    # Summary
    summary = {
        "total": len(cases),
        "passed": passed,
        "failed": failed,
        "pass_rate": round(100 * passed / len(cases), 1),
        "top_k": top_k,
        "elapsed_sec": round(elapsed, 1),
    }
    if faith_scores:
        summary["avg_faithfulness"] = round(sum(faith_scores) / len(faith_scores), 3)
        summary["min_faithfulness"] = round(min(faith_scores), 3)
        summary["ragas_scored"] = len(faith_scores)

    log.info(f"\n{'='*60}")
    log.info(f"Retrieval: {passed}/{len(cases)} passed ({summary['pass_rate']}%)")
    if faith_scores:
        log.info(f"Faithfulness: avg={summary['avg_faithfulness']:.3f} "
                 f"min={summary['min_faithfulness']:.3f} (n={len(faith_scores)})")
    log.info(f"Time: {elapsed:.1f}s")

    # Save results
    output_dir = Path(__file__).parent.parent / "eval"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "so-redis-eval-results.json"
    with open(output_file, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2, ensure_ascii=False)
    log.info(f"\nResults saved to {output_file}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Redis docs KB retrieval eval")
    parser.add_argument("--ragas", action="store_true", help="Enable RAGAS faithfulness scoring")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to retrieve")
    args = parser.parse_args()

    summary = run_eval(top_k=args.top_k, use_ragas=args.ragas)

    # Exit with error if pass rate < 90%
    if summary["pass_rate"] < 90:
        log.error(f"\nFAILED: pass rate {summary['pass_rate']}% < 90% threshold")
        sys.exit(1)


if __name__ == "__main__":
    main()
