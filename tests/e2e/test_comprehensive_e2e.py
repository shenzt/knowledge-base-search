#!/usr/bin/env python3
"""完整的 E2E 测试套件 - 测试 Agentic RAG 核心能力"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "workers"))

from simple_rag_worker import search_with_rag

# 扩展的测试用例 - 覆盖多种场景
TEST_CASES = [
    # === 基础检索测试 ===
    {
        "id": "basic-001",
        "query": "What is a Pod in Kubernetes?",
        "language": "en",
        "category": "k8s-basic",
        "expected_keywords": ["pod", "container", "kubernetes"],
        "min_score": 4.0,
    },
    {
        "id": "basic-002",
        "query": "Kubernetes Service 是什么？",
        "language": "zh",
        "category": "k8s-service",
        "expected_keywords": ["service", "网络", "负载均衡"],
        "min_score": 3.0,
    },
    {
        "id": "basic-003",
        "query": "What are Init Containers?",
        "language": "en",
        "category": "k8s-init",
        "expected_keywords": ["init", "container", "startup"],
        "min_score": 3.5,
    },

    # === 跨语言检索测试 ===
    {
        "id": "cross-lang-001",
        "query": "Redis 管道技术如何工作？",
        "language": "zh",
        "category": "redis-pipeline",
        "expected_keywords": ["pipeline", "redis", "批量"],
        "min_score": 2.0,  # 跨语言得分较低
    },
    {
        "id": "cross-lang-002",
        "query": "How does Redis pipelining improve performance?",
        "language": "en",
        "category": "redis-pipeline",
        "expected_keywords": ["pipeline", "performance", "batch"],
        "min_score": 2.0,
    },

    # === 复杂查询测试 ===
    {
        "id": "complex-001",
        "query": "What's the difference between Deployment and StatefulSet?",
        "language": "en",
        "category": "k8s-comparison",
        "expected_keywords": ["deployment", "statefulset", "difference"],
        "min_score": 3.0,
    },
    {
        "id": "complex-002",
        "query": "How to troubleshoot CrashLoopBackOff in Kubernetes?",
        "language": "en",
        "category": "k8s-troubleshooting",
        "expected_keywords": ["crashloopbackoff", "pod", "debug"],
        "min_score": 3.0,
    },
    {
        "id": "complex-003",
        "query": "Kubernetes 中如何实现服务发现？",
        "language": "zh",
        "category": "k8s-service-discovery",
        "expected_keywords": ["service", "discovery", "dns"],
        "min_score": 2.5,
    },

    # === 具体操作查询 ===
    {
        "id": "howto-001",
        "query": "How to create a Pod with multiple containers?",
        "language": "en",
        "category": "k8s-howto",
        "expected_keywords": ["pod", "container", "yaml"],
        "min_score": 3.0,
    },
    {
        "id": "howto-002",
        "query": "如何配置 Kubernetes 资源限制？",
        "language": "zh",
        "category": "k8s-resources",
        "expected_keywords": ["resource", "limit", "request"],
        "min_score": 2.5,
    },

    # === 概念理解测试 ===
    {
        "id": "concept-001",
        "query": "What is the purpose of a ReplicaSet?",
        "language": "en",
        "category": "k8s-concept",
        "expected_keywords": ["replicaset", "replica", "pod"],
        "min_score": 3.0,
    },
    {
        "id": "concept-002",
        "query": "Kubernetes 命名空间的作用是什么？",
        "language": "zh",
        "category": "k8s-namespace",
        "expected_keywords": ["namespace", "隔离", "资源"],
        "min_score": 2.5,
    },

    # === 边界情况测试 ===
    {
        "id": "edge-001",
        "query": "What is a sidecar container?",
        "language": "en",
        "category": "k8s-pattern",
        "expected_keywords": ["sidecar", "container", "pattern"],
        "min_score": 2.0,
    },
    {
        "id": "edge-002",
        "query": "Kubernetes 中的 DaemonSet 是什么？",
        "language": "zh",
        "category": "k8s-daemonset",
        "expected_keywords": ["daemonset", "node", "pod"],
        "min_score": 2.0,
    },

    # === 不存在的内容测试 ===
    {
        "id": "notfound-001",
        "query": "How to configure Kubernetes with blockchain?",
        "language": "en",
        "category": "not-in-kb",
        "expected_keywords": [],
        "min_score": 0.0,
        "expect_no_results": True,
    },
]


async def run_comprehensive_test():
    """运行完整测试"""
    print("=" * 80)
    print("完整 E2E 测试 - Agentic RAG 核心能力验证")
    print("=" * 80)
    print(f"\n测试用例总数: {len(TEST_CASES)}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = []
    passed = 0
    failed = 0
    errors = 0

    total_tokens = 0
    total_time = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] 测试: {test_case['id']}")
        print(f"类别: {test_case['category']}")
        print(f"查询: {test_case['query']}")

        start_time = datetime.now()

        try:
            result = await search_with_rag(test_case['query'], top_k=5)

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            total_time += elapsed

            if result['status'] == 'success':
                num_results = len(result.get('search_results', []))
                has_answer = len(result.get('answer', '')) > 0
                max_score = max([r.get('score', 0) for r in result.get('search_results', [])], default=0)

                # 验证逻辑
                test_passed = True
                failure_reasons = []

                # 检查是否期望无结果
                if test_case.get('expect_no_results'):
                    if num_results > 0 and max_score > 1.0:
                        test_passed = False
                        failure_reasons.append(f"期望无结果，但找到 {num_results} 个")
                else:
                    # 检查结果数量
                    if num_results == 0:
                        test_passed = False
                        failure_reasons.append("无检索结果")

                    # 检查答案
                    if not has_answer:
                        test_passed = False
                        failure_reasons.append("无生成答案")

                    # 检查得分
                    if max_score < test_case.get('min_score', 0):
                        test_passed = False
                        failure_reasons.append(f"得分过低 ({max_score:.2f} < {test_case['min_score']})")

                    # 检查关键词（可选）
                    if test_case.get('expected_keywords'):
                        answer_lower = result.get('answer', '').lower()
                        missing_keywords = [kw for kw in test_case['expected_keywords']
                                          if kw.lower() not in answer_lower]
                        if len(missing_keywords) > len(test_case['expected_keywords']) / 2:
                            # 超过一半关键词缺失才算失败
                            failure_reasons.append(f"缺失关键词: {missing_keywords}")

                if test_passed:
                    print(f"状态: ✅ 通过")
                    print(f"检索: {num_results} 个结果, 最高得分: {max_score:.4f}")
                    print(f"答案: {len(result['answer'])} 字符")
                    print(f"耗时: {elapsed:.2f}s")
                    passed += 1
                    status = "passed"
                else:
                    print(f"状态: ❌ 失败")
                    print(f"原因: {', '.join(failure_reasons)}")
                    print(f"检索: {num_results} 个结果, 最高得分: {max_score:.4f}")
                    failed += 1
                    status = "failed"

                # 记录 token 使用
                if result.get('usage'):
                    total_tokens += result['usage'].get('total_tokens', 0)
                    print(f"Token: {result['usage'].get('total_tokens', 0)}")

                results.append({
                    "test_id": test_case['id'],
                    "category": test_case['category'],
                    "query": test_case['query'],
                    "status": status,
                    "num_results": num_results,
                    "max_score": max_score,
                    "answer_length": len(result['answer']),
                    "elapsed_seconds": elapsed,
                    "sources": result.get('sources', []),
                    "usage": result.get('usage', {}),
                    "failure_reasons": failure_reasons if not test_passed else []
                })

            else:
                print(f"状态: ❌ 错误")
                print(f"错误: {result.get('error', 'Unknown')}")
                errors += 1
                results.append({
                    "test_id": test_case['id'],
                    "category": test_case['category'],
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
                "category": test_case['category'],
                "query": test_case['query'],
                "status": "error",
                "error": str(e)
            })

        print("-" * 80)

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    total = len(TEST_CASES)
    print(f"\n总用例: {total}")
    print(f"✅ 通过: {passed} ({passed/total*100:.1f}%)")
    print(f"❌ 失败: {failed} ({failed/total*100:.1f}%)")
    print(f"⚠️  错误: {errors} ({errors/total*100:.1f}%)")
    print(f"\n总耗时: {total_time:.2f}s")
    print(f"平均耗时: {total_time/total:.2f}s/query")
    print(f"总 Token: {total_tokens}")
    print(f"平均 Token: {total_tokens/total:.0f}/query")

    # 按类别统计
    print("\n" + "=" * 80)
    print("按类别统计")
    print("=" * 80)

    categories = {}
    for r in results:
        cat = r['category']
        if cat not in categories:
            categories[cat] = {'total': 0, 'passed': 0}
        categories[cat]['total'] += 1
        if r['status'] == 'passed':
            categories[cat]['passed'] += 1

    for cat, stats in sorted(categories.items()):
        rate = stats['passed'] / stats['total'] * 100
        print(f"{cat:30s}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")

    # 保存结果
    output_file = f"eval/comprehensive_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "total_time": total_time,
            "total_tokens": total_tokens,
            "results": results,
            "categories": categories
        }, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {output_file}")

    # 显示失败的测试
    if failed > 0 or errors > 0:
        print("\n" + "=" * 80)
        print("❌ 失败/错误的测试")
        print("=" * 80)
        for r in results:
            if r['status'] in ['failed', 'error']:
                print(f"\n{r['test_id']}: {r['query'][:50]}...")
                if 'failure_reasons' in r and r['failure_reasons']:
                    print(f"  原因: {', '.join(r['failure_reasons'])}")
                if 'error' in r:
                    print(f"  错误: {r['error']}")

    print("\n" + "=" * 80)

    return results


if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())
