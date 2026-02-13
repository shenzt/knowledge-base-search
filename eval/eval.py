#!/usr/bin/env python3
"""知识库检索回归测试脚本。

用法: python eval/eval.py [--top-k 5] [--min-score 0.3]
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def load_questions(path: str = "eval/questions.jsonl") -> list[dict]:
    """加载测试问题集。"""
    questions = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))
    return questions


def evaluate_retrieval(question: dict, results: list[dict], top_k: int = 5) -> dict:
    """评估单个问题的检索质量。

    指标:
    - doc_hit: expected_doc_ids 中的文档是否出现在 top-k
    - keyword_hit_rate: expected_keywords 在 top-k 结果文本中的命中率
    """
    result_texts = " ".join(r.get("text", "") for r in results[:top_k])
    result_doc_ids = [r.get("doc_id", "") for r in results[:top_k]]

    # Doc hit
    expected_ids = question.get("expected_doc_ids", [])
    doc_hit = any(did in result_doc_ids for did in expected_ids) if expected_ids else None

    # Keyword hit rate
    expected_kw = question.get("expected_keywords", [])
    kw_hits = sum(1 for kw in expected_kw if kw in result_texts)
    kw_hit_rate = kw_hits / len(expected_kw) if expected_kw else None

    return {
        "question": question["question"],
        "scope": question.get("scope", ""),
        "doc_hit": doc_hit,
        "keyword_hit_rate": kw_hit_rate,
        "top_k_count": len(results[:top_k]),
    }


def main():
    questions = load_questions()
    print(f"加载 {len(questions)} 个测试问题")
    print("=" * 60)

    # TODO: 接入实际的 MCP 检索调用
    # 目前输出骨架，等 mcp_server.py 实现后补齐
    print("⚠️  eval.py 当前为骨架模式，需要 mcp_server.py 实现后接入实际检索")
    print()

    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['question']}")
        print(f"  scope: {q.get('scope', 'all')}")
        print(f"  expected_keywords: {q.get('expected_keywords', [])}")
        print()

    # 保存结果模板
    result_path = Path("eval/results") / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "total_questions": len(questions),
        "status": "skeleton_mode",
        "note": "等待 mcp_server.py 实现后接入实际检索",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"结果已保存到 {result_path}")


if __name__ == "__main__":
    main()
