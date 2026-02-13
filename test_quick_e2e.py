#!/usr/bin/env python3
"""简化的 E2E 测试 - 快速验证核心功能"""

import asyncio
import json
from datetime import datetime
from sonnet_worker import search_knowledge_base

# 精选测试用例
QUICK_TEST_CASES = [
    {
        "id": "quick-001",
        "query": "What is a Pod in Kubernetes?",
        "language": "en",
        "category": "k8s-basic",
        "expected_keywords": ["pod", "container", "smallest"],
    },
    {
        "id": "quick-002",
        "query": "Redis 管道技术如何工作？",
        "language": "zh",
        "category": "redis-pipeline",
        "expected_keywords": ["pipeline", "管道", "批量"],
    },
    {
        "id": "quick-003",
        "query": "Kubernetes Service 是什么？",
        "language": "zh",
        "category": "k8s-service",
        "expected_keywords": ["service", "网络"],
    },
    {
        "id": "quick-004",
        "query": "What are Init Containers?",
        "language": "en",
        "category": "k8s-init",
        "expected_keywords": ["init", "container"],
    },
]


async def run_quick_test():
    """运行快速测试"""
    print("="*80)
    print("快速 E2E 测试")
    print("="*80)

    results = []

    for i, test_case in enumerate(QUICK_TEST_CASES, 1):
        test_id = test_case["id"]
        query = test_case["query"]

        print(f"\n[{i}/{len(QUICK_TEST_CASES)}] 测试: {test_id}")
        print(f"查询: {query}")

        try:
            # 执行检索
            result = await search_knowledge_base(query, top_k=3)

            if result["status"] == "success":
                result_text = result.get("result", "")

                # 检查关键词
                keywords_found = []
                for keyword in test_case["expected_keywords"]:
                    if keyword.lower() in result_text.lower():
                        keywords_found.append(keyword)

                coverage = len(keywords_found) / len(test_case["expected_keywords"])
                passed = coverage >= 0.5

                print(f"状态: {'✅ 通过' if passed else '❌ 失败'}")
                print(f"关键词覆盖: {coverage:.1%} ({len(keywords_found)}/{len(test_case['expected_keywords'])})")
                print(f"找到: {', '.join(keywords_found) if keywords_found else '无'}")

                # 显示部分结果
                if result_text:
                    print(f"回答预览: {result_text[:200]}...")

                results.append({
                    "test_id": test_id,
                    "status": "passed" if passed else "failed",
                    "coverage": coverage,
                    "keywords_found": keywords_found,
                    "result_preview": result_text[:500]
                })
            else:
                print(f"状态: ❌ 错误")
                print(f"错误: {result.get('error', 'Unknown')}")
                results.append({
                    "test_id": test_id,
                    "status": "error",
                    "error": result.get("error")
                })

        except Exception as e:
            print(f"状态: ❌ 异常")
            print(f"异常: {e}")
            results.append({
                "test_id": test_id,
                "status": "error",
                "error": str(e)
            })

        print("-"*80)
        await asyncio.sleep(2)  # 短暂延迟

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    errors = sum(1 for r in results if r["status"] == "error")

    print(f"\n总用例: {total}")
    print(f"通过: {passed} ({passed/total*100:.1f}%)")
    print(f"失败: {failed} ({failed/total*100:.1f}%)")
    print(f"错误: {errors} ({errors/total*100:.1f}%)")

    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"eval/quick_test_{timestamp}.json"

    import os
    os.makedirs("eval", exist_ok=True)

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {result_file}")

    # Bad cases 分析
    bad_cases = [r for r in results if r["status"] in ["failed", "error"]]
    if bad_cases:
        print("\n" + "="*80)
        print("Bad Cases 分析")
        print("="*80)

        for r in bad_cases:
            print(f"\n测试: {r['test_id']}")
            print(f"状态: {r['status']}")

            if r["status"] == "failed":
                print(f"关键词覆盖: {r.get('coverage', 0):.1%}")
                print(f"找到的关键词: {', '.join(r.get('keywords_found', []))}")
                print(f"回答预览: {r.get('result_preview', 'N/A')[:200]}...")
            else:
                print(f"错误: {r.get('error', 'Unknown')}")

    return results


if __name__ == "__main__":
    asyncio.run(run_quick_test())
