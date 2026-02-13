#!/usr/bin/env python3
"""简化的 E2E 测试 - 使用 Simple RAG Worker"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

from simple_rag_worker import search_with_rag

# 测试用例
TEST_CASES = [
    {
        "id": "test-001",
        "query": "What is a Pod in Kubernetes?",
        "language": "en",
        "category": "k8s-basic",
    },
    {
        "id": "test-002",
        "query": "Redis 管道技术如何工作？",
        "language": "zh",
        "category": "redis-pipeline",
    },
    {
        "id": "test-003",
        "query": "Kubernetes Service 是什么？",
        "language": "zh",
        "category": "k8s-service",
    },
    {
        "id": "test-004",
        "query": "What are Init Containers?",
        "language": "en",
        "category": "k8s-init",
    },
]


async def run_test():
    """运行测试"""
    print("="*80)
    print("Simple E2E 测试 - 使用 Anthropic SDK")
    print("="*80)

    results = []
    passed = 0
    failed = 0
    errors = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] 测试: {test_case['id']}")
        print(f"查询: {test_case['query']}")

        try:
            result = await search_with_rag(test_case['query'], top_k=3)

            if result['status'] == 'success':
                num_results = len(result.get('search_results', []))
                has_answer = len(result.get('answer', '')) > 0

                if num_results > 0 and has_answer:
                    print(f"状态: ✅ 通过")
                    print(f"检索结果: {num_results} 个")
                    print(f"答案长度: {len(result['answer'])} 字符")
                    passed += 1
                    status = "passed"
                else:
                    print(f"状态: ❌ 失败 (无结果或无答案)")
                    failed += 1
                    status = "failed"

                results.append({
                    "test_id": test_case['id'],
                    "query": test_case['query'],
                    "status": status,
                    "num_results": num_results,
                    "answer_length": len(result['answer']),
                    "sources": result.get('sources', []),
                    "usage": result.get('usage', {})
                })

            elif result['status'] == 'partial':
                print(f"状态: ⚠️ 部分成功 (检索成功但生成答案失败)")
                failed += 1
                results.append({
                    "test_id": test_case['id'],
                    "query": test_case['query'],
                    "status": "partial",
                    "error": result.get('error', 'Unknown'),
                    "num_results": len(result.get('search_results', []))
                })

            else:
                print(f"状态: ❌ 错误")
                print(f"错误: {result.get('error', 'Unknown')}")
                errors += 1
                results.append({
                    "test_id": test_case['id'],
                    "query": test_case['query'],
                    "status": "error",
                    "error": result.get('error', 'Unknown')
                })

        except Exception as e:
            print(f"状态: ❌ 异常")
            print(f"异常: {e}")
            errors += 1
            results.append({
                "test_id": test_case['id'],
                "query": test_case['query'],
                "status": "error",
                "error": str(e)
            })

        print("-"*80)

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    total = len(TEST_CASES)
    print(f"\n总用例: {total}")
    print(f"通过: {passed} ({passed/total*100:.1f}%)")
    print(f"失败: {failed} ({failed/total*100:.1f}%)")
    print(f"错误: {errors} ({errors/total*100:.1f}%)")

    # 保存结果
    output_file = f"eval/simple_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {output_file}")

    # 显示详细结果
    if passed > 0:
        print(f"\n✅ 通过的测试:")
        for r in results:
            if r['status'] == 'passed':
                print(f"  - {r['test_id']}: {r['query'][:50]}...")
                print(f"    检索: {r['num_results']} 个结果, 答案: {r['answer_length']} 字符")
                if r.get('usage'):
                    print(f"    Token: {r['usage'].get('total_tokens', 0)}")

    if failed > 0 or errors > 0:
        print(f"\n❌ 失败/错误的测试:")
        for r in results:
            if r['status'] in ['failed', 'error', 'partial']:
                print(f"  - {r['test_id']}: {r['query'][:50]}...")
                if 'error' in r:
                    print(f"    错误: {r['error']}")

    print("\n" + "="*80)

    return results


if __name__ == "__main__":
    asyncio.run(run_test())
