#!/usr/bin/env python3
"""Generate markdown eval report from result JSON files.

Reads eval result files and generates a unified markdown report with:
- Summary table (pass rate, faithfulness, elapsed time)
- Per-case detail table (id, status, tools, retrieved paths, time)
- Comparison between retrieval eval and skill eval
- Timestamp and git commit

Usage:
  python scripts/generate_eval_report.py                    # auto-detect result files
  python scripts/generate_eval_report.py --output report.md # custom output path
  python scripts/generate_eval_report.py --stdout           # print to stdout (for CI summary)
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).parent.parent
EVAL_DIR = PROJECT_ROOT / "eval"


def get_git_info() -> dict:
    """获取当前 git commit 信息。"""
    info = {"commit": "unknown", "branch": "unknown", "date": "unknown"}
    try:
        info["commit"] = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, cwd=PROJECT_ROOT,
        ).stdout.strip()
        info["branch"] = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True, cwd=PROJECT_ROOT,
        ).stdout.strip()
    except Exception:
        pass
    return info


def load_results(path: Path) -> dict | None:
    """加载 eval 结果 JSON 文件。"""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log.warning(f"Failed to load {path}: {e}")
        return None


def format_status(status: str) -> str:
    """格式化状态为 emoji。"""
    return {"PASS": "✅", "FAIL": "❌", "ERROR": "⚠️"}.get(status, "❓")


def generate_summary_section(retrieval: dict | None, skill: dict | None) -> str:
    """生成总结表格。"""
    lines = ["## Summary\n"]
    lines.append("| Eval | Cases | Passed | Rate | Faithfulness | Time |")
    lines.append("|------|-------|--------|------|-------------|------|")

    for label, data in [("Retrieval", retrieval), ("Skill (E2E)", skill)]:
        if not data:
            continue
        s = data.get("summary", {})
        total = s.get("total", 0)
        passed = s.get("passed", 0)
        rate = s.get("pass_rate", 0)
        faith = s.get("avg_faithfulness")
        faith_str = f"{faith:.3f}" if faith is not None else "—"
        elapsed = s.get("elapsed_sec", 0)
        elapsed_str = f"{elapsed:.0f}s" if elapsed < 300 else f"{elapsed/60:.1f}m"
        lines.append(f"| {label} | {total} | {passed} | {rate}% | {faith_str} | {elapsed_str} |")

    lines.append("")
    return "\n".join(lines)


def generate_detail_section(label: str, data: dict) -> str:
    """生成单个 eval 的详细结果表格。"""
    results = data.get("results", [])
    if not results:
        return ""

    lines = [f"## {label} — Detail\n"]
    lines.append("| ID | Topic | Status | Tools | Retrieved Paths | Answer | Time |")
    lines.append("|----|-------|--------|-------|-----------------|--------|------|")

    for r in results:
        status = format_status(r.get("status", "?"))
        case_id = r.get("id", "?")
        topic = r.get("topic", "?")

        # Tools — from skill eval or empty for retrieval eval
        tools = r.get("tools_used", [])
        tools_short = ", ".join(t.replace("mcp__knowledge-base__", "") for t in tools) if tools else "—"

        # Paths — from skill eval (retrieved_paths) or retrieval eval (hits)
        paths = r.get("retrieved_paths", [])
        hits = r.get("hits", [])
        if not paths and hits:
            paths = [h.get("path", "") for h in hits]

        path_str = "—"
        if paths:
            short_paths = sorted(paths, key=len)[:2]
            path_str = ", ".join(
                p.split("/")[-1] if "/" in p else p
                for p in short_paths
            )
            if len(path_str) > 50:
                path_str = path_str[:47] + "..."

        # Answer / score info
        answer_len = r.get("answer_length", 0)
        elapsed = r.get("elapsed_sec", 0)
        error = r.get("error")
        time_str = f"{elapsed:.0f}s" if elapsed else "—"

        if answer_len:
            answer_str = f"{answer_len}c"
        elif hits:
            top_score = max((h.get("score", 0) for h in hits), default=0)
            answer_str = f"top={top_score:.2f}"
        else:
            answer_str = "—"

        if error:
            answer_str = f"⚠️ {error[:30]}"

        # Faithfulness if available
        faith = r.get("ragas", {}).get("faithfulness", -1)
        if isinstance(faith, (int, float)) and faith >= 0:
            answer_str += f" (f={faith:.2f})"

        lines.append(f"| {case_id} | {topic} | {status} | {tools_short} | {path_str} | {answer_str} | {time_str} |")

    # Failed cases detail
    failed = [r for r in results if r.get("status") != "PASS"]
    if failed:
        lines.append(f"\n### Failed Cases ({len(failed)})\n")
        for r in failed:
            case_id = r.get("id", "?")
            error = r.get("error", "")
            reasons = r.get("gate_reasons", [])
            lines.append(f"- **{case_id}**: {error or ', '.join(reasons) or 'unknown'}")

    lines.append("")
    return "\n".join(lines)


def generate_report(
    retrieval_path: Path | None = None,
    skill_path: Path | None = None,
    output_path: Path | None = None,
    to_stdout: bool = False,
) -> str:
    """生成完整的 eval 报告。"""
    # Auto-detect result files
    if retrieval_path is None:
        retrieval_path = EVAL_DIR / "so-redis-eval-results.json"
    if skill_path is None:
        skill_path = EVAL_DIR / "skill-eval-results.json"

    retrieval = load_results(retrieval_path)
    skill = load_results(skill_path)

    if not retrieval and not skill:
        return "No eval results found.\n"

    git = get_git_info()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Build report
    sections = []
    sections.append(f"# Eval Results\n")
    sections.append(f"> Generated: {now} | Commit: `{git['commit']}` | Branch: `{git['branch']}`\n")

    # Summary
    sections.append(generate_summary_section(retrieval, skill))

    # Detail tables
    if retrieval:
        sections.append(generate_detail_section("Retrieval Eval", retrieval))
    if skill:
        sections.append(generate_detail_section("Skill Eval (E2E Agent)", skill))

    report = "\n".join(sections)

    # Output
    if to_stdout:
        print(report)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)
        log.info(f"Report saved to {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Generate eval report")
    parser.add_argument("--retrieval", type=Path, help="Retrieval eval results JSON")
    parser.add_argument("--skill", type=Path, help="Skill eval results JSON")
    parser.add_argument("--output", type=Path, default=EVAL_DIR / "EVAL_RESULTS.md",
                        help="Output markdown file")
    parser.add_argument("--stdout", action="store_true", help="Also print to stdout")
    args = parser.parse_args()

    generate_report(
        retrieval_path=args.retrieval,
        skill_path=args.skill,
        output_path=args.output,
        to_stdout=args.stdout,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
