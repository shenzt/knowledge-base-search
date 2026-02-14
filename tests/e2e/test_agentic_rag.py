#!/usr/bin/env python3
"""Agentic RAG 自动化测试 - 使用 Claude Agent SDK 调用 /search skill

对比 Simple RAG 和 Agentic RAG 的性能差异。
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
load_dotenv()

# 测试用例（与 Simple RAG 相同）
TEST_CASES = [
    # 基础查询
    {
        "id": "basic-001",
        "query": "What is a Pod in Kubernetes?",
        "category": "k8s-basic",
        "expected_keywords": ["pod", "container", "smallest unit"],
        "min_score": 4.0,
    },
    {
        "id": "basic-002",
        "query": "Kubernetes Service 是什么？",
        "category": "k8s-service",
        "expected_keywords": ["service", "网络", "负载均衡"],
        "min_score": 3.0,
    },
    {
        "id": "basic-003",
        "query": "What are Init Containers?",
        "category": "k8s-init",
        "expected_keywords": ["init", "container", "startup"],
        "min_score": 3.5,
    },

    # 跨语言检索
    {
        "id": "cross-lang-001",
        "query": "Redis 管道技术如何工作？",
        "category": "redis-pipeline",
        "expected_keywords": ["pipeline", "批量"],
        "min_score": 2.0,
    },
    {
        "id": "cross-lang-002",
        "query": "How does Redis pipelining improve performance?",
        "category": "redis-pipeline",
        "expected_keywords": ["pipeline", "performance"],
        "min_score": 2.0,
    },

    # 复杂推理
    {
        "id": "complex-001",
        "query": "What's the difference between Deployment and StatefulSet?",
        "category": "k8s-comparison",
        "expected_keywords": ["deployment", "statefulset", "difference"],
        "min_score": 3.0,
    },
    {
        "id": "complex-002",
        "query": "How to troubleshoot CrashLoopBackOff in Kubernetes?",
        "category": "k8s-troubleshooting",
        "expected_keywords": ["crashloopbackoff", "debug"],
        "min_score": 3.0,
    },
    {
        "id": "complex-003",
        "query": "Kubernetes 中如何实现服务发现？",
        "category": "k8s-service-discovery",
        "expected_keywords": ["service", "discovery"],
        "min_score": 2.5,
    },

    # 操作指南
    {
        "id": "howto-001",
        "query": "How to create a Pod with multiple containers?",
        "category": "k8s-howto",
        "expected_keywords": ["pod", "container", "multi"],
        "min_score": 3.0,
    },
    {
        "id": "howto-002",
        "query": "如何配置 Kubernetes 资源限制？",
        "category": "k8s-resources",
        "expected_keywords": ["resource", "limit"],
        "min_score": 2.5,
    },

    # 概念理解
    {
        "id": "concept-001",
        "query": "What is the purpose of a ReplicaSet?",
        "category": "k8s-concept",
        "expected_keywords": ["replicaset", "replica"],
        "min_score": 3.0,
    },
    {
        "id": "concept-002",
        "query": "Kubernetes 命名空间的作用是什么？",
        "category": "k8s-namespace",
        "expected_keywords": ["namespace", "隔离"],
        "min_score": 2.5,
    },

    # 边界情况
    {
        "id": "edge-001",
        "query": "What is a sidecar container?",
        "category": "k8s-pattern",
        "expected_keywords": ["sidecar", "container"],
        "min_score": 2.0,
    },
    {
        "id": "edge-002",
        "query": "Kubernetes 中的 DaemonSet 是什么？",
        "category": "k8s-daemonset",
        "expected_keywords": ["daemonset", "node"],
        "min_score": 2.0,
    },

    # 不存在内容
    {
        "id": "notfound-001",
        "query": "How to configure Kubernetes with blockchain?",
        "category": "not-in-kb",
        "expected_keywords": [],
        "min_score": 0.0,
        "expect_no_results": True,
    },
]


async def run_agentic_search(query: str) -> Dict[str, Any]:
    """使用 Claude Agent SDK 调用 /search skill

    这会触发 Agentic RAG 的智能三层检索策略。
    """
    try:
        # 方法 1: 使用 Bash 调用 claude CLI
        # 这是最接近真实使用场景的方式
        import subprocess

        start_time = time.time()

        # 调用 claude CLI 执行 /search skill
        result = subprocess.run(
            ["claude", "-p", f"/search {query}"],
            capture_output=True,
            text=True,
            timeout=120,
            env=os.environ.copy()
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            # 解析输出
            output = result.stdout

            # 提取答案（简化版，实际需要更复杂的解析）
            answer = output

            return {
                "status": "success",
                "query": query,
                "answer": answer,
                "elapsed_seconds": elapsed,
                "strategy": "agentic",  # 由 Claude 自主决策
                "output": output
            }
        else:
            return {
                "status": "error",
                "query": query,
                "error": result.stderr,
                "elapsed_seconds": elapsed
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "query": query,
            "error": "Timeout after 120s"
        }
    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "error": str(e)
        }


async def run_agentic_test():
    """运行 Agentic RAG 测试"""
    print("=" * 80)
    print("Agentic RAG 自动化测试")
    print("=" * 80)
    print(f"\n测试用例总数: {len(TEST_CASES)}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = []
    passed = 0
    failed = 0
    errors = 0
    total_time = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] 测试: {test_case['id']}")
        print(f"类别: {test_case['category']}")
        print(f"查询: {test_case['query']}")

        try:
            result = await run_agentic_search(test_case['query'])

            if result['status'] == 'success':
                elapsed = result['elapsed_seconds']
                total_time += elapsed

                # 简化的评估逻辑
                has_answer = len(result.get('answer', '')) > 100

                if has_answer:
                    print(f"状态: ✅ 通过")
                    print(f"耗时: {elapsed:.2f}s")
                    passed += 1
                    status = "passed"
                else:
                    print(f"状态: ❌ 失败 (答案过短)")
                    failed += 1
                    status = "failed"

                results.append({
                    "test_id": test_case['id'],
                    "category": test_case['category'],
                    "query": test_case['query'],
                    "status": status,
                    "elapsed_seconds": elapsed,
                    "answer_length": len(result.get('answer', '')),
                    "strategy": result.get('strategy', 'unknown')
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
    print("Agentic RAG 测试总结")
    print("=" * 80)

    total = len(TEST_CASES)
    print(f"\n总用例: {total}")
    print(f"✅ 通过: {passed} ({passed/total*100:.1f}%)")
    print(f"❌ 失败: {failed} ({failed/total*100:.1f}%)")
    print(f"⚠️  错误: {errors} ({errors/total*100:.1f}%)")
    print(f"\n总耗时: {total_time:.2f}s")
    if passed + failed > 0:
        print(f"平均耗时: {total_time/(passed+failed):.2f}s/query")

    # 保存结果
    output_file = f"eval/agentic_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "test_type": "agentic_rag",
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "total_time": total_time,
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {output_file}")
    print("=" * 80)

    return results


async def generate_comparison_report():
    """生成 Simple RAG vs Agentic RAG 对比报告"""
    print("\n" + "=" * 80)
    print("生成对比报告")
    print("=" * 80)

    # 读取 Simple RAG 结果
    simple_file = "eval/comprehensive_test_20260213_234320.json"
    with open(simple_file, 'r') as f:
        simple_data = json.load(f)

    # 读取最新的 Agentic RAG 结果
    agentic_files = sorted(Path("eval").glob("agentic_test_*.json"))
    if not agentic_files:
        print("❌ 未找到 Agentic RAG 测试结果")
        return

    with open(agentic_files[-1], 'r') as f:
        agentic_data = json.load(f)

    # 生成对比报告
    report = f"""# Simple RAG vs Agentic RAG 对比报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📊 总体对比

| 指标 | Simple RAG | Agentic RAG | 提升 |
|------|-----------|-------------|------|
| 通过率 | {simple_data['passed']}/{simple_data['total']} ({simple_data['passed']/simple_data['total']*100:.1f}%) | {agentic_data['passed']}/{agentic_data['total']} ({agentic_data['passed']/agentic_data['total']*100:.1f}%) | {(agentic_data['passed']/agentic_data['total'] - simple_data['passed']/simple_data['total'])*100:+.1f}% |
| 失败率 | {simple_data['failed']}/{simple_data['total']} ({simple_data['failed']/simple_data['total']*100:.1f}%) | {agentic_data['failed']}/{agentic_data['total']} ({agentic_data['failed']/agentic_data['total']*100:.1f}%) | {(agentic_data['failed']/agentic_data['total'] - simple_data['failed']/simple_data['total'])*100:+.1f}% |
| 错误率 | {simple_data['errors']}/{simple_data['total']} ({simple_data['errors']/simple_data['total']*100:.1f}%) | {agentic_data['errors']}/{agentic_data['total']} ({agentic_data['errors']/agentic_data['total']*100:.1f}%) | {(agentic_data['errors']/agentic_data['total'] - simple_data['errors']/simple_data['total'])*100:+.1f}% |
| 平均耗时 | {simple_data['total_time']/simple_data['total']:.2f}s | {agentic_data['total_time']/agentic_data['total']:.2f}s | {(simple_data['total_time']/simple_data['total'])/(agentic_data['total_time']/agentic_data['total']):.1f}x |
| 总 Token | {simple_data.get('total_tokens', 'N/A')} | {agentic_data.get('total_tokens', 'N/A')} | - |

## 📈 按类别对比

### 基础查询 (k8s-basic, k8s-init)
- Simple RAG: 3/3 (100%)
- Agentic RAG: ?/3 (?%)

### 跨语言检索 (redis-pipeline)
- Simple RAG: 1/2 (50%)
- Agentic RAG: ?/2 (?%)

### 复杂推理 (k8s-comparison, k8s-troubleshooting, k8s-service-discovery)
- Simple RAG: 1/3 (33.3%)
- Agentic RAG: ?/3 (?%)

### 概念理解 (k8s-concept, k8s-namespace)
- Simple RAG: 0/2 (0%)
- Agentic RAG: ?/2 (?%)

## 🎯 关键发现

### Agentic RAG 的优势
1.
2.
3.

### Agentic RAG 的劣势
1.
2.

### 改进建议
1.
2.
3.

## 📝 结论

Agentic RAG 相比 Simple RAG：
- 通过率提升: ?%
- 响应时间: ?x
- 最大改善: ?
- 仍需改进: ?

---

**测试数据**:
- Simple RAG: {simple_file}
- Agentic RAG: {agentic_files[-1]}
"""

    # 保存报告
    report_file = f"eval/COMPARISON_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ 对比报告已生成: {report_file}")
    print("=" * 80)


if __name__ == "__main__":
    print("⚠️  注意: 此脚本需要 claude CLI 可用")
    print("⚠️  如果 claude CLI 不可用，请使用手动测试方式\n")

    # 运行测试
    asyncio.run(run_agentic_test())

    # 生成对比报告
    asyncio.run(generate_comparison_report())
