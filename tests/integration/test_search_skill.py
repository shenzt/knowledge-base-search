#!/usr/bin/env python3
"""测试 Search Skill - 直接调用 MCP Server

不使用 Claude Agent SDK，直接测试混合检索功能。
"""

import json
import sys
import os

# 添加 scripts 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from mcp_server import hybrid_search


def test_search_skill():
    """测试搜索技能"""

    test_cases = [
        {
            "id": "test-001",
            "query": "What is a Pod in Kubernetes?",
            "expected_topics": ["pod", "container", "kubernetes"]
        },
        {
            "id": "test-002",
            "query": "Redis 管道技术如何工作？",
            "expected_topics": ["redis", "pipeline", "管道"]
        },
        {
            "id": "test-003",
            "query": "Kubernetes Service 是什么？",
            "expected_topics": ["service", "kubernetes", "网络"]
        },
        {
            "id": "test-004",
            "query": "What are Init Containers?",
            "expected_topics": ["init", "container", "initialization"]
        }
    ]

    print("=" * 80)
    print("Search Skill 测试 - 混合检索验证")
    print("=" * 80)

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试 {i}/{len(test_cases)}: {test_case['query']}")
        print(f"{'='*80}")

        try:
            # 调用混合检索
            search_results_json = hybrid_search(
                query=test_case["query"],
                top_k=3,
                min_score=0.3
            )

            # 解析结果
            search_results = json.loads(search_results_json)

            if not search_results:
                print("\n⚠️ 没有找到结果")
                results.append({
                    "test_id": test_case["id"],
                    "query": test_case["query"],
                    "status": "no_results",
                    "passed": False
                })
                continue

            # 显示结果
            print(f"\n✅ 找到 {len(search_results)} 个结果\n")

            for j, result in enumerate(search_results, 1):
                print(f"结果 {j}:")
                print(f"  标题: {result.get('title', 'N/A')}")
                print(f"  文档: {result.get('doc_id', 'N/A')}")
                print(f"  得分: {result.get('score', 0):.4f}")
                print(f"  路径: {result.get('path', 'N/A')}")

                # 显示内容片段
                text = result.get('text', '')
                if len(text) > 200:
                    text = text[:200] + "..."
                print(f"  内容: {text}")
                print()

            # 评估质量
            top_score = search_results[0].get('score', 0)

            # 生成回答
            answer = generate_answer(test_case["query"], search_results)
            print(f"生成的回答:\n{answer}\n")

            # 判断是否通过
            passed = top_score > 0.5 and len(search_results) > 0

            results.append({
                "test_id": test_case["id"],
                "query": test_case["query"],
                "status": "success",
                "top_score": top_score,
                "num_results": len(search_results),
                "answer": answer,
                "passed": passed
            })

            if passed:
                print(f"✅ 测试通过 (得分: {top_score:.4f})")
            else:
                print(f"⚠️ 测试未通过 (得分: {top_score:.4f})")

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            results.append({
                "test_id": test_case["id"],
                "query": test_case["query"],
                "status": "error",
                "error": str(e),
                "passed": False
            })

    # 总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}\n")

    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"通过率: {passed}/{total} ({pass_rate:.1f}%)\n")

    for result in results:
        status_icon = "✅" if result.get("passed") else "❌"
        print(f"{status_icon} {result['test_id']}: {result['query']}")
        if result.get("status") == "success":
            print(f"   得分: {result.get('top_score', 0):.4f}, 结果数: {result.get('num_results', 0)}")
        else:
            print(f"   状态: {result.get('status', 'unknown')}")

    # 保存结果
    output_file = "eval/search_skill_test_results.json"
    os.makedirs("eval", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {output_file}")
    print(f"\n{'='*80}\n")

    return results


def generate_answer(query: str, search_results: list) -> str:
    """基于检索结果生成回答"""

    if not search_results:
        return "抱歉，没有找到相关信息。"

    # 获取最相关的结果
    top_result = search_results[0]

    answer = f"根据检索结果，{query}\n\n"
    answer += f"【来源】{top_result.get('title', 'N/A')}\n"
    answer += f"【得分】{top_result.get('score', 0):.4f}\n"
    answer += f"【路径】{top_result.get('path', 'N/A')}\n\n"

    # 提取关键内容
    text = top_result.get('text', '')
    if len(text) > 500:
        text = text[:500] + "..."

    answer += f"【内容摘要】\n{text}\n"

    # 如果有多个结果，列出其他来源
    if len(search_results) > 1:
        answer += f"\n【其他相关文档】\n"
        for i, result in enumerate(search_results[1:], 2):
            answer += f"{i}. {result.get('title', 'N/A')} (得分: {result.get('score', 0):.4f})\n"

    return answer


if __name__ == "__main__":
    test_search_skill()
