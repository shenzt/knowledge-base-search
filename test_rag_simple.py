#!/usr/bin/env python3
"""简单的 RAG Worker 测试 - 使用 Claude Sonnet 4

直接测试 RAG Worker 是否能正常工作。
"""

import asyncio
import json
import logging
from datetime import datetime

from rag_worker import search_knowledge_base

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


async def test_single_query(query: str, query_id: str):
    """测试单个查询"""
    print(f"\n{'='*80}")
    print(f"测试查询: {query}")
    print(f"查询 ID: {query_id}")
    print(f"{'='*80}")

    start_time = datetime.now()

    try:
        result = await search_knowledge_base(query, top_k=3)

        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"\n✅ 查询完成 (耗时: {elapsed:.2f}s)")
        print(f"\n状态: {result.get('status')}")
        print(f"Session ID: {result.get('session_id', 'N/A')}")

        if result.get('status') == 'success':
            print(f"\n结果:\n{result.get('result', 'N/A')[:500]}...")

            if result.get('tool_calls'):
                print(f"\n工具调用 ({len(result['tool_calls'])} 次):")
                for i, call in enumerate(result['tool_calls'][:5], 1):
                    print(f"  {i}. {call.get('tool', 'unknown')}")

            if result.get('usage'):
                usage = result['usage']
                print(f"\nToken 使用:")
                print(f"  输入: {usage.get('input_tokens', 0)}")
                print(f"  输出: {usage.get('output_tokens', 0)}")
                print(f"  总计: {usage.get('total_tokens', 0)}")
        else:
            print(f"\n❌ 错误: {result.get('error', 'Unknown')}")

        return result

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n❌ 异常 (耗时: {elapsed:.2f}s): {e}")
        return {
            "status": "error",
            "error": str(e),
            "elapsed_time": elapsed
        }


async def main():
    """运行测试"""
    print("\n" + "="*80)
    print("RAG Worker 简单测试")
    print("模型: claude-sonnet-4-20250514")
    print("="*80)

    # 测试用例
    test_cases = [
        {
            "id": "test-001",
            "query": "What is a Pod in Kubernetes?",
            "description": "英文查询 - Kubernetes 基础概念"
        },
        {
            "id": "test-002",
            "query": "Redis 管道技术如何工作？",
            "description": "中文查询 - Redis 技术细节"
        }
    ]

    results = []

    for test_case in test_cases:
        result = await test_single_query(
            query=test_case["query"],
            query_id=test_case["id"]
        )
        results.append({
            "test_id": test_case["id"],
            "query": test_case["query"],
            "result": result
        })

        # 延迟避免过载
        await asyncio.sleep(2)

    # 总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")

    success_count = sum(1 for r in results if r['result'].get('status') == 'success')
    total_count = len(results)

    print(f"\n成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")

    for r in results:
        status_icon = "✅" if r['result'].get('status') == 'success' else "❌"
        print(f"{status_icon} {r['test_id']}: {r['query']}")

    # 保存结果
    output_file = f"test_rag_simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到: {output_file}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
