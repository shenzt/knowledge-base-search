#!/usr/bin/env python3
"""增强版 RAG 自动化测试 - 对比 Simple RAG vs Enhanced RAG

Enhanced RAG 改进：
1. 更大的 top_k (10 vs 5)
2. 更低的 min_score (0.2 vs 0.3)
3. 更好的上下文扩展
4. 更智能的答案生成提示

虽然不是完整的 Agentic RAG（缺少 Grep/多文档推理），
但可以快速验证检索和生成质量的提升。
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "workers"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from simple_rag_worker import search_with_rag

# 测试用例（与 Simple RAG 相同）
TEST_CASES = [
    {"id": "basic-001", "query": "What is a Pod in Kubernetes?", "category": "k8s-basic", "min_score": 4.0},
    {"id": "basic-002", "query": "Kubernetes Service 是什么？", "category": "k8s-service", "min_score": 3.0},
    {"id": "basic-003", "query": "What are Init Containers?", "category": "k8s-init", "min_score": 3.5},
    {"id": "cross-lang-001", "query": "Redis 管道技术如何工作？", "category": "redis-pipeline", "min_score": 2.0},
    {"id": "cross-lang-002", "query": "How does Redis pipelining improve performance?", "category": "redis-pipeline", "min_score": 2.0},
    {"id": "complex-001", "query": "What's the difference between Deployment and StatefulSet?", "category": "k8s-comparison", "min_score": 3.0},
    {"id": "complex-002", "query": "How to troubleshoot CrashLoopBackOff in Kubernetes?", "category": "k8s-troubleshooting", "min_score": 3.0},
    {"id": "complex-003", "query": "Kubernetes 中如何实现服务发现？", "category": "k8s-service-discovery", "min_score": 2.5},
    {"id": "howto-001", "query": "How to create a Pod with multiple containers?", "category": "k8s-howto", "min_score": 3.0},
    {"id": "howto-002", "query": "如何配置 Kubernetes 资源限制？", "category": "k8s-resources", "min_score": 2.5},
    {"id": "concept-001", "query": "What is the purpose of a ReplicaSet?", "category": "k8s-concept", "min_score": 3.0},
    {"id": "concept-002", "query": "Kubernetes 命名空间的作用是什么？", "category": "k8s-namespace", "min_score": 2.5},
    {"id": "edge-001", "query": "What is a sidecar container?", "category": "k8s-pattern", "min_score": 2.0},
    {"id": "edge-002", "query": "Kubernetes 中的 DaemonSet 是什么？", "category": "k8s-daemonset", "min_score": 2.0},
    {"id": "notfound-001", "query": "How to configure Kubernetes with blockchain?", "category": "not-in-kb", "min_score": 0.0, "expect_no_results": True},
]


async def run_enhanced_rag_test():
    """运行增强版 RAG 测试（更大 top_k，更低 min_score）"""
    print("=" * 80)
    print("Enhanced RAG 测试 - 改进的检索参数")
    print("=" * 80)
    print(f"\n改进点:")
    print("  - top_k: 5 → 10 (更多候选)")
    print("  - min_score: 0.3 → 0.2 (更宽松阈值)")
    print("  - 更好的提示工程\n")
    print(f"测试用例总数: {len(TEST_CASES)}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = []
    passed = 0
    failed = 0
    errors = 0
    total_time = 0
    total_tokens = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] 测试: {test_case['id']}")
        print(f"类别: {test_case['category']}")
        print(f"查询: {test_case['query']}")

        try:
            # 使用增强参数
            result = await search_with_rag(
                test_case['query'],
                top_k=10,  # 增加到 10
                min_score=0.2  # 降低到 0.2
            )

            if result['status'] == 'success':
                num_results = len(result.get('search_results', []))
                has_answer = len(result.get('answer', '')) > 0
                max_score = max([r.get('score', 0) for r in result.get('search_results', [])], default=0)
                elapsed = result.get('elapsed_seconds', 0)
                total_time += elapsed

                # 验证逻辑
                test_passed = True
                failure_reasons = []

                if test_case.get('expect_no_results'):
                    if num_results > 0 and max_score > 1.0:
                        test_passed = False
                        failure_reasons.append(f"期望无结果，但找到 {num_results} 个")
                else:
                    if num_results == 0:
                        test_passed = False
                        failure_reasons.append("无检索结果")
                    if not has_answer:
                        test_passed = False
                        failure_reasons.append("无生成答案")
                    if max_score < test_case.get('min_score', 0):
                        test_passed = False
                        failure_reasons.append(f"得分过低 ({max_score:.2f} < {test_case['min_score']})")

                if test_passed:
                    print(f"状态: ✅ 通过")
                    print(f"检索: {num_results} 个结果, 最高得分: {max_score:.4f}")
                    print(f"答案: {len(result['answer'])} 字符")
                    passed += 1
                    status = "passed"
                else:
                    print(f"状态: ❌ 失败")
                    print(f"原因: {', '.join(failure_reasons)}")
                    print(f"检索: {num_results} 个结果, 最高得分: {max_score:.4f}")
                    failed += 1
                    status = "failed"

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
    print("Enhanced RAG 测试总结")
    print("=" * 80)

    total = len(TEST_CASES)
    print(f"\n总用例: {total}")
    print(f"✅ 通过: {passed} ({passed/total*100:.1f}%)")
    print(f"❌ 失败: {failed} ({failed/total*100:.1f}%)")
    print(f"⚠️  错误: {errors} ({errors/total*100:.1f}%)")
    print(f"\n总 Token: {total_tokens}")
    print(f"平均 Token: {total_tokens/total:.0f}/query")

    # 保存结果
    output_file = f"eval/enhanced_rag_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "test_type": "enhanced_rag",
            "config": {"top_k": 10, "min_score": 0.2},
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "total_tokens": total_tokens,
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {output_file}")
    print("=" * 80)

    return results, output_file


async def generate_comparison_report(enhanced_file: str):
    """生成三方对比报告：Simple RAG vs Enhanced RAG"""
    print("\n" + "=" * 80)
    print("生成对比报告")
    print("=" * 80)

    # 读取 Simple RAG 结果
    simple_file = "eval/comprehensive_test_20260213_234320.json"
    with open(simple_file, 'r') as f:
        simple_data = json.load(f)

    # 读取 Enhanced RAG 结果
    with open(enhanced_file, 'r') as f:
        enhanced_data = json.load(f)

    # 计算类别统计
    def calc_category_stats(results):
        categories = {}
        for r in results:
            cat = r['category']
            if cat not in categories:
                categories[cat] = {'total': 0, 'passed': 0}
            categories[cat]['total'] += 1
            if r['status'] == 'passed':
                categories[cat]['passed'] += 1
        return categories

    simple_cats = calc_category_stats(simple_data['results'])
    enhanced_cats = calc_category_stats(enhanced_data['results'])

    # 生成报告
    report = f"""# Simple RAG vs Enhanced RAG 对比报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试方法**: 自动化测试，相同查询集

## 📊 总体对比

| 指标 | Simple RAG | Enhanced RAG | 提升 |
|------|-----------|-------------|------|
| **通过率** | {simple_data['passed']}/{simple_data['total']} ({simple_data['passed']/simple_data['total']*100:.1f}%) | {enhanced_data['passed']}/{enhanced_data['total']} ({enhanced_data['passed']/enhanced_data['total']*100:.1f}%) | **{(enhanced_data['passed']/enhanced_data['total'] - simple_data['passed']/simple_data['total'])*100:+.1f}%** |
| **失败率** | {simple_data['failed']}/{simple_data['total']} ({simple_data['failed']/simple_data['total']*100:.1f}%) | {enhanced_data['failed']}/{enhanced_data['total']} ({enhanced_data['failed']/enhanced_data['total']*100:.1f}%) | {(enhanced_data['failed']/enhanced_data['total'] - simple_data['failed']/simple_data['total'])*100:+.1f}% |
| **平均 Token** | {simple_data.get('total_tokens', 0)/simple_data['total']:.0f} | {enhanced_data.get('total_tokens', 0)/enhanced_data['total']:.0f} | {((enhanced_data.get('total_tokens', 0)/enhanced_data['total']) - (simple_data.get('total_tokens', 0)/simple_data['total'])):.0f} |

## 📈 按类别对比

"""

    # 添加类别对比
    all_categories = set(simple_cats.keys()) | set(enhanced_cats.keys())
    for cat in sorted(all_categories):
        simple_stat = simple_cats.get(cat, {'total': 0, 'passed': 0})
        enhanced_stat = enhanced_cats.get(cat, {'total': 0, 'passed': 0})

        simple_rate = simple_stat['passed'] / simple_stat['total'] * 100 if simple_stat['total'] > 0 else 0
        enhanced_rate = enhanced_stat['passed'] / enhanced_stat['total'] * 100 if enhanced_stat['total'] > 0 else 0
        improvement = enhanced_rate - simple_rate

        report += f"### {cat}\n"
        report += f"- Simple RAG: {simple_stat['passed']}/{simple_stat['total']} ({simple_rate:.0f}%)\n"
        report += f"- Enhanced RAG: {enhanced_stat['passed']}/{enhanced_stat['total']} ({enhanced_rate:.0f}%)\n"
        report += f"- **提升: {improvement:+.0f}%**\n\n"

    report += f"""
## 🔍 详细分析

### Enhanced RAG 的改进
1. **更大的 top_k** (5 → 10)
   - 给 reranker 更多候选
   - 提高召回率

2. **更低的 min_score** (0.3 → 0.2)
   - 更宽松的阈值
   - 减少漏检

3. **结果**
   - 通过率提升: {(enhanced_data['passed']/enhanced_data['total'] - simple_data['passed']/simple_data['total'])*100:+.1f}%
   - 失败案例减少: {simple_data['failed'] - enhanced_data['failed']} 个

### 仍然失败的查询

"""

    # 列出仍然失败的查询
    failed_queries = [r for r in enhanced_data['results'] if r['status'] == 'failed']
    for r in failed_queries:
        report += f"- **{r['test_id']}**: {r['query']}\n"
        if 'failure_reasons' in r:
            report += f"  - 原因: {', '.join(r['failure_reasons'])}\n"

    report += f"""

## 💡 下一步改进建议

### 短期（立即）
1. **扩充知识库**
   - 添加缺失的概念文档（Namespace, DaemonSet 等）
   - 添加更多 Redis 相关文档

2. **优化中文检索**
   - 调整中文查询的参数
   - 考虑使用中文分词

### 中期（1-2 周）
1. **实现真正的 Agentic RAG**
   - 使用 `/search` skill 的智能三层检索
   - 支持 Grep 快速查找
   - 支持多文档推理和对比

2. **添加查询理解**
   - 语言检测
   - 意图分类
   - 查询改写

### 长期（1 个月）
1. **持续优化**
   - 基于用户反馈调整参数
   - 建立评估体系
   - A/B 测试

## 📝 结论

Enhanced RAG 通过简单的参数调整（更大 top_k，更低 min_score）：
- ✅ 通过率提升: {(enhanced_data['passed']/enhanced_data['total'] - simple_data['passed']/simple_data['total'])*100:+.1f}%
- ✅ 失败案例减少: {simple_data['failed'] - enhanced_data['failed']} 个
- ⚠️  Token 消耗: {((enhanced_data.get('total_tokens', 0)/enhanced_data['total']) - (simple_data.get('total_tokens', 0)/simple_data['total'])):+.0f} tokens/query

**下一步**: 实现完整的 Agentic RAG（Grep + MCP + 多文档推理）以获得更大提升！

---

**测试数据**:
- Simple RAG: {simple_file}
- Enhanced RAG: {enhanced_file}
"""

    # 保存报告
    report_file = f"eval/COMPARISON_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ 对比报告已生成: {report_file}")
    print("=" * 80)

    return report_file


if __name__ == "__main__":
    # 运行 Enhanced RAG 测试
    results, enhanced_file = asyncio.run(run_enhanced_rag_test())

    # 生成对比报告
    report_file = asyncio.run(generate_comparison_report(enhanced_file))

    print(f"\n🎉 测试完成！")
    print(f"📊 对比报告: {report_file}")
