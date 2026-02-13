#!/usr/bin/env python3
"""直接测试 MCP Server 的混合检索功能

绕过 Claude Agent SDK，直接调用 MCP Server 验证混合检索是否正常工作。
"""

import sys
import os
import json

# 添加 scripts 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from mcp_server import hybrid_search, keyword_search, index_status


def test_hybrid_search():
    """测试混合检索功能"""

    print("=" * 80)
    print("直接测试 MCP Server - 混合检索验证")
    print("=" * 80)

    # 测试用例
    test_cases = [
        {
            "id": "test-001",
            "query": "What is a Pod in Kubernetes?",
            "language": "en",
            "expected_keywords": ["pod", "kubernetes", "container"]
        },
        {
            "id": "test-002",
            "query": "Redis 管道技术如何工作？",
            "language": "zh",
            "expected_keywords": ["redis", "管道", "pipeline"]
        },
        {
            "id": "test-003",
            "query": "Kubernetes Service 是什么？",
            "language": "zh",
            "expected_keywords": ["service", "kubernetes"]
        },
        {
            "id": "test-004",
            "query": "What are Init Containers?",
            "language": "en",
            "expected_keywords": ["init", "container"]
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试 {i}/{len(test_cases)}: {test_case['query']}")
        print(f"{'='*80}")

        try:
            # 调用混合检索 (返回 JSON 字符串)
            search_results_json = hybrid_search(
                query=test_case["query"],
                top_k=3,
                min_score=0.3
            )

            # 解析 JSON
            search_results = json.loads(search_results_json)

            print(f"\n✅ 检索成功，返回 {len(search_results)} 个结果")

            # 显示结果
            for j, result in enumerate(search_results, 1):
                print(f"\n结果 {j}:")
                print(f"  文档: {result.get('doc_id', 'N/A')}")
                print(f"  标题: {result.get('title', 'N/A')}")
                print(f"  得分: {result.get('score', 0):.4f}")
                print(f"  内容片段: {result.get('text', '')[:200]}...")

            # 评估结果质量
            has_results = len(search_results) > 0
            top_score = search_results[0].get('score', 0) if search_results else 0

            result = {
                "test_id": test_case["id"],
                "query": test_case["query"],
                "status": "success",
                "num_results": len(search_results),
                "top_score": top_score,
                "passed": has_results and top_score > 0.5
            }

            results.append(result)

            if result["passed"]:
                print(f"\n✅ 测试通过 (得分: {top_score:.4f})")
            else:
                print(f"\n⚠️ 测试未通过 (得分: {top_score:.4f})")

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
    print(f"{'='*80}")

    passed = sum(1 for r in results if r.get("passed", False))
    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"\n通过率: {passed}/{total} ({pass_rate:.1f}%)")

    for result in results:
        status_icon = "✅" if result.get("passed") else "❌"
        print(f"{status_icon} {result['test_id']}: {result['query'][:50]}...")
        if result.get("status") == "success":
            print(f"   得分: {result.get('top_score', 0):.4f}, 结果数: {result.get('num_results', 0)}")
        else:
            print(f"   错误: {result.get('error', 'Unknown')}")

    # 检查索引状态
    print(f"\n{'='*80}")
    print("索引状态")
    print(f"{'='*80}")

    try:
        status_json = index_status()
        status = json.loads(status_json)
        print(f"\nCollection: {status.get('collection', 'N/A')}")
        print(f"文档数: {status.get('points_count', 0)}")
        print(f"状态: {status.get('status', 'N/A')}")
    except Exception as e:
        print(f"\n⚠️ 无法获取索引状态: {e}")

    print(f"\n{'='*80}")

    return results


if __name__ == "__main__":
    test_hybrid_search()
