#!/usr/bin/env python3
"""E2E /search skill eval — tests the full Agent pipeline via Claude Agent SDK.

Tests: query → Agent reads INDEX.md → hybrid_search/Grep → Read docs → grounded answer
Unlike eval_retrieval.py (Layer 2 only), this tests the complete Agentic RAG pipeline.

Usage:
  python scripts/eval_skill.py                     # golden subset (6 cases)
  python scripts/eval_skill.py --full              # all 35 cases
  python scripts/eval_skill.py --ragas             # + RAGAS faithfulness scoring
  python scripts/eval_skill.py --concurrency 3     # parallel sessions

Environment variables:
  QDRANT_URL          — Qdrant endpoint (default: http://localhost:6333)
  JUDGE_API_KEY       — API key for RAGAS judge (DeepSeek)
  JUDGE_MODEL         — judge model (default: deepseek-chat)
  JUDGE_BASE_URL      — judge API base URL
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

PROJECT_ROOT = Path(__file__).parent.parent
GOLDEN_IDS = {"so-001", "so-003", "so-008", "so-015", "so-019", "cn-003"}


def load_test_cases(golden_only: bool = True) -> list[dict]:
    """Load SO test cases."""
    test_dir = PROJECT_ROOT / "tests"
    sys.path.insert(0, str(test_dir))
    from so_redis_test import SO_TEST_CASES
    if golden_only:
        return [tc for tc in SO_TEST_CASES if tc["id"] in GOLDEN_IDS]
    return SO_TEST_CASES


def build_system_prompt() -> str:
    """Build the Agent system prompt from /search skill."""
    skill_path = PROJECT_ROOT / ".claude" / "skills" / "search" / "SKILL.md"
    skill_content = skill_path.read_text() if skill_path.exists() else ""

    # Strip YAML front-matter
    if skill_content.startswith("---"):
        end = skill_content.find("---", 3)
        if end > 0:
            skill_content = skill_content[end + 3:].strip()

    return f"""{skill_content}

## Hard Grounding Rules

- Answer ONLY based on retrieved documents. Never supplement with training knowledge.
- Include citations [来源: path] for every factual claim.
- If documents don't contain the answer, say "未找到相关文档" or "not found in docs".
- Do NOT fabricate commands, configurations, or code examples not in the retrieved docs.
- Answer language follows query language (Chinese query → Chinese answer).
"""


def get_mcp_server_config() -> dict:
    """Build MCP server config for the Agent session."""
    mcp_script = str(PROJECT_ROOT / "scripts" / "mcp_server.py")
    return {
        "knowledge-base": {
            "command": str(PROJECT_ROOT / ".venv" / "bin" / "python"),
            "args": [mcp_script],
            "env": {
                "QDRANT_URL": os.environ.get("QDRANT_URL", "http://localhost:6333"),
            },
        }
    }


async def run_single_case(
    tc: dict,
    system_prompt: str,
    max_turns: int = 10,
    timeout_sec: int = 300,
) -> dict:
    """Run a single test case through the Agent pipeline."""
    from claude_agent_sdk import query, ClaudeAgentOptions

    case_id = tc["id"]
    t0 = time.time()
    messages_log = []
    answer = ""
    error = None

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        mcp_servers=get_mcp_server_config(),
        allowed_tools=[
            "Read", "Grep", "Glob",
            "mcp__knowledge-base__hybrid_search",
            "mcp__knowledge-base__keyword_search",
        ],
        disallowed_tools=["Bash", "Write", "Edit", "NotebookEdit", "Task"],
        permission_mode="bypassPermissions",
        max_turns=max_turns,
        cwd=str(PROJECT_ROOT),
    )

    try:
        async def _run():
            nonlocal answer, messages_log
            async for msg in query(prompt=tc["question"], options=options):
                content = getattr(msg, "content", None)

                # Convert SDK block objects to dicts for eval_module compatibility
                if isinstance(content, list):
                    converted = []
                    for block in content:
                        block_type = type(block).__name__
                        if block_type == "ToolUseBlock":
                            converted.append({
                                "type": "tool_use",
                                "id": getattr(block, "id", ""),
                                "name": getattr(block, "name", ""),
                                "input": getattr(block, "input", {}),
                            })
                        elif block_type == "ToolResultBlock":
                            converted.append({
                                "type": "tool_result",
                                "tool_use_id": getattr(block, "tool_use_id", ""),
                                "content": getattr(block, "content", ""),
                                "is_error": getattr(block, "is_error", None),
                            })
                        elif block_type == "TextBlock":
                            text = getattr(block, "text", "")
                            converted.append({"type": "text", "text": text})
                            # Capture answer from text blocks
                            if text and len(text) > 50:
                                answer = text
                        else:
                            converted.append({"type": block_type, "raw": str(block)[:500]})
                    messages_log.append({"content": converted})
                else:
                    # Capture final answer from ResultMessage
                    if hasattr(msg, "result") and msg.result:
                        answer = str(msg.result)

        await asyncio.wait_for(_run(), timeout=timeout_sec)
    except asyncio.TimeoutError:
        error = f"timeout ({timeout_sec}s)"
        log.warning(f"  [{case_id}] TIMEOUT after {timeout_sec}s")
    except Exception as e:
        error = str(e)[:200]
        log.warning(f"  [{case_id}] ERROR: {error}")

    elapsed = time.time() - t0
    return {
        "id": case_id,
        "topic": tc["topic"],
        "question": tc["question"][:200],
        "answer": answer[:1000] if answer else "",
        "answer_length": len(answer),
        "messages_log": messages_log,
        "elapsed_sec": round(elapsed, 1),
        "error": error,
    }


def evaluate_result(tc: dict, result: dict, use_ragas: bool = False) -> dict:
    """Evaluate a single result: gate check + optional RAGAS."""
    from eval_module import extract_contexts, gate_check, get_tools_used, get_retrieved_doc_paths

    contexts = extract_contexts(result["messages_log"])
    tools_used = get_tools_used(contexts)
    retrieved_paths = get_retrieved_doc_paths(contexts)

    # Check if expected docs were retrieved
    expected_paths = tc.get("expected_paths", [])
    doc_hit = any(
        any(exp.lower() in path.lower() for path in retrieved_paths)
        for exp in expected_paths
    ) if expected_paths else True

    # Gate check
    gate_tc = {
        "expected_doc": ",".join(expected_paths),
        "source": "qdrant",
    }
    gate = gate_check(gate_tc, result["answer"], contexts)

    entry = {
        "id": result["id"],
        "topic": result["topic"],
        "question": result["question"],
        "status": "PASS" if doc_hit and not result["error"] else "FAIL",
        "doc_hit": doc_hit,
        "gate_passed": gate["passed"],
        "gate_reasons": gate.get("reasons", []),
        "tools_used": tools_used,
        "retrieved_paths": retrieved_paths[:10],
        "answer_length": result["answer_length"],
        "elapsed_sec": result["elapsed_sec"],
        "error": result["error"],
    }

    if use_ragas and result["answer"] and not result["error"]:
        try:
            from ragas_judge import ragas_judge
            scores = ragas_judge(
                tc["question"], result["answer"], contexts,
            )
            entry["ragas"] = {
                "faithfulness": scores.get("faithfulness", -1),
                "relevancy": scores.get("relevancy", -1),
            }
        except Exception as e:
            log.warning(f"  RAGAS error for {result['id']}: {e}")
            entry["ragas"] = {"faithfulness": -1, "error": str(e)[:100]}

    return entry


async def run_eval(
    golden_only: bool = True,
    use_ragas: bool = False,
    concurrency: int = 1,
    max_turns: int = 10,
    timeout_sec: int = 300,
) -> dict:
    """Run the full E2E skill evaluation."""
    cases = load_test_cases(golden_only=golden_only)
    system_prompt = build_system_prompt()

    log.info(f"Running {len(cases)} E2E skill eval cases "
             f"(concurrency={concurrency}, max_turns={max_turns}, ragas={use_ragas})\n")

    results = []
    passed = 0
    failed = 0
    faith_scores = []
    t0 = time.time()

    sem = asyncio.Semaphore(concurrency)

    async def _run_with_sem(tc):
        async with sem:
            return await run_single_case(tc, system_prompt, max_turns, timeout_sec)

    # Run cases (concurrent or sequential)
    if concurrency > 1:
        tasks = [_run_with_sem(tc) for tc in cases]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    else:
        raw_results = []
        for tc in cases:
            r = await run_single_case(tc, system_prompt, max_turns, timeout_sec)
            raw_results.append(r)

    # Evaluate results
    for tc, raw in zip(cases, raw_results):
        if isinstance(raw, Exception):
            entry = {
                "id": tc["id"], "topic": tc["topic"],
                "status": "ERROR", "error": str(raw)[:200],
            }
        else:
            entry = evaluate_result(tc, raw, use_ragas=use_ragas)

        status = entry.get("status", "ERROR")
        if status == "PASS":
            passed += 1
        else:
            failed += 1

        # Log
        log.info(f"[{status}] {entry['id']} ({entry.get('topic', '?')}): "
                 f"{entry.get('answer_length', 0)} chars, "
                 f"{entry.get('elapsed_sec', 0)}s, "
                 f"tools={entry.get('tools_used', [])}")
        if status != "PASS":
            reasons = entry.get("gate_reasons", [])
            if reasons:
                log.info(f"       Reasons: {reasons}")
            if entry.get("error"):
                log.info(f"       Error: {entry['error']}")

        # Track faithfulness
        faith = entry.get("ragas", {}).get("faithfulness", -1)
        if isinstance(faith, (int, float)) and faith >= 0:
            faith_scores.append(faith)
            log.info(f"       Faith: {faith:.3f}")

        # Strip messages_log from saved results (too large)
        entry.pop("messages_log", None)
        results.append(entry)

    elapsed = time.time() - t0

    # Summary
    total = len(cases)
    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(100 * passed / total, 1) if total else 0,
        "max_turns": max_turns,
        "concurrency": concurrency,
        "elapsed_sec": round(elapsed, 1),
    }
    if faith_scores:
        summary["avg_faithfulness"] = round(sum(faith_scores) / len(faith_scores), 3)
        summary["min_faithfulness"] = round(min(faith_scores), 3)
        summary["ragas_scored"] = len(faith_scores)

    log.info(f"\n{'='*60}")
    log.info(f"E2E Skill Eval: {passed}/{total} passed ({summary['pass_rate']}%)")
    if faith_scores:
        log.info(f"Faithfulness: avg={summary['avg_faithfulness']:.3f} "
                 f"min={summary['min_faithfulness']:.3f} (n={len(faith_scores)})")
    log.info(f"Time: {elapsed:.1f}s")

    # Save results
    output_dir = PROJECT_ROOT / "eval"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "skill-eval-results.json"
    with open(output_file, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2, ensure_ascii=False)
    log.info(f"\nResults saved to {output_file}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="E2E /search skill eval")
    parser.add_argument("--full", action="store_true", help="Run all 35 cases (default: golden 6)")
    parser.add_argument("--ragas", action="store_true", help="Enable RAGAS faithfulness scoring")
    parser.add_argument("--concurrency", type=int, default=1, help="Parallel sessions")
    parser.add_argument("--max-turns", type=int, default=10, help="Max Agent turns per case")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per case (seconds)")
    args = parser.parse_args()

    summary = asyncio.run(run_eval(
        golden_only=not args.full,
        use_ragas=args.ragas,
        concurrency=args.concurrency,
        max_turns=args.max_turns,
        timeout_sec=args.timeout,
    ))

    if summary["pass_rate"] < 80:
        log.error(f"\nFAILED: pass rate {summary['pass_rate']}% < 80% threshold")
        sys.exit(1)


if __name__ == "__main__":
    main()
