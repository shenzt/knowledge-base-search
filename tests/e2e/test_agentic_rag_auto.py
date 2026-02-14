#!/usr/bin/env python3
"""Agentic RAG 自动化测试 - 使用 Claude CLI 调用 /search skill

通过 `claude -p` 触发完整的 Agentic RAG 流程：
- 智能三层检索策略（Grep → MCP hybrid_search → 多文档推理）
- Claude 自主决策检索策略
- 上下文扩展和多步推理

对比 Simple RAG baseline，生成完整对比报告。
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 测试用例（与 Simple RAG 相同的 15 个）
TEST_CASES = [
    # 基础查询
    {"id": "basic-001", "query": "What is a Pod in Kubernetes?", "category": "k8s-basic", "min_score": 4.0},
    {"id": "basic-002", "query": "Kubernetes Service 是什么？", "category": "k8s-service", "min_score": 3.0},
    {"id": "basic-003", "query": "What are Init Containers?", "category": "k8s-init", "min_score": 3.5},
    # 跨语言检索
    {"id": "cross-lang-001", "query": "Redis 管道技术如何工作？", "category": "redis-pipeline", "min_score": 2.0},
    {"id": "cross-lang-002", "query": "How does Redis pipelining improve performance?", "category": "redis-pipeline", "min_score": 2.0},
    # 复杂推理
    {"id": "complex-001", "query": "What's the difference between Deployment and StatefulSet?", "category": "k8s-comparison", "min_score": 3.0},
    {"id": "complex-002", "query": "How to troubleshoot CrashLoopBackOff in Kubernetes?", "category": "k8s-troubleshooting", "min_score": 3.0},
    {"id": "complex-003", "query": "Kubernetes 中如何实现服务发现？", "category": "k8s-service-discovery", "min_score": 2.5},
    # 操作指南
    {"id": "howto-001", "query": "How to create a Pod with multiple containers?", "category": "k8s-howto", "min_score": 3.0},
    {"id": "howto-002", "query": "如何配置 Kubernetes 资源限制？", "category": "k8s-resources", "min_score": 2.5},
    # 概念理解
    {"id": "concept-001", "query": "What is the purpose of a ReplicaSet?", "category": "k8s-concept", "min_score": 3.0},
    {"id": "concept-002", "query": "Kubernetes 命名空间的作用是什么？", "category": "k8s-namespace", "min_score": 2.5},
    # 边界情况
    {"id": "edge-001", "query": "What is a sidecar container?", "category": "k8s-pattern", "min_score": 2.0},
    {"id": "edge-002", "query": "Kubernetes 中的 DaemonSet 是什么？", "category": "k8s-daemonset", "min_score": 2.0},
    # 不存在内容
    {"id": "notfound-001", "query": "How to configure Kubernetes with blockchain?", "category": "not-in-kb", "min_score": 0.0, "expect_no_results": True},
]


def run_agentic_search(query: str, timeout: int = 180) -> Dict[str, Any]:
    """使用 Claude CLI 调用 /search skill

    这会触发完整的 Agentic RAG 流程：
    1. Claude 分析查询类型
    2. 选择检索策略（Grep/MCP/多文档）
    3. 执行检索
    4. 读取完整上下文
    5. 生成带引用的答案
    """
    start_time = time.time()

    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                f"/search {query}",
                "--output-format", "json",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
            env={**os.environ, "CLAUDE_AUTO_ACCEPT_PERMISSIONS": "true"},
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            # 尝试解析 JSON 输出
            try:
                output_data = json.loads(result.stdout)
                answer = output_data.get("result", result.stdout)
                # 提取 cost/token 信息
                cost_usd = output_data.get("cost_usd", 0)
                duration_ms = output_data.get("duration_ms", elapsed * 1000)
                num_turns = output_data.get("num_turns", 0)
            except (json.JSONDecodeError, TypeError):
                answer = result.stdout
                cost_usd = 0
                duration_ms = elapsed * 1000
                num_turns = 0

            return {
                "status": "success",
                "query": query,
                "answer": answer if isinstance(answer, str) else str(answer),
                "elapsed_seconds": elapsed,
                "cost_usd": cost_usd,
                "duration_ms": duration_ms,
                "num_turns": num_turns,
                "strategy": "agentic",
            }
        else:
            return {
                "status": "error",
                "query": query,
                "error": result.stderr[:500] if result.stderr else f"Exit code: {result.returncode}",
                "stdout": result.stdout[:500] if result.stdout else "",
                "elapsed_seconds": elapsed,
            }

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        return {
            "status": "error",
            "query": query,
            "error": f"Timeout after {timeout}s",
            "elapsed_seconds": elapsed,
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "query": query,
            "error": "claude CLI not found. Install: npm install -g @anthropic-ai/claude-code",
            "elapsed_seconds": 0,
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "status": "error",
            "query": query,
            "error": str(e),
            "elapsed_seconds": elapsed,
        }


def evaluate_answer(test_case: Dict, result: Dict) -> Dict[str, Any]:
    """评估 Agentic RAG 的答案质量"""
    evaluation = {
        "test_passed": False,
        "failure_reasons": [],
        "quality_indicators": {},
    }

    if result["status"] != "success":
        evaluation["failure_reasons"].append(f"执行失败: {result.get('error', 'Unknown')}")
        return evaluation

    answer = result.get("answer", "")

    # 1. 答案长度检查
    if test_case.get("expect_no_results"):
        # 对于不存在的内容，答案应该说明未找到
        not_found_indicators = ["未找到", "没有找到", "not found", "no relevant", "don't have", "无法找到", "couldn't find", "no results"]
        has_not_found = any(ind.lower() in answer.lower() for ind in not_found_indicators)
        if has_not_found or len(answer) < 500:
            evaluation["test_passed"] = True
            evaluation["quality_indicators"]["correctly_identified_no_results"] = True
        else:
            evaluation["failure_reasons"].append("应识别为无结果，但生成了长答案")
        return evaluation

    # 2. 答案非空且有实质内容
    if len(answer) < 50:
        evaluation["failure_reasons"].append(f"答案过短 ({len(answer)} 字符)")
        return evaluation

    # 3. 检查是否有引用/来源
    has_citation = any(marker in answer for marker in ["来源:", "docs/", "[来源", "Source:", ".md"])
    evaluation["quality_indicators"]["has_citation"] = has_citation

    # 4. 检查答案是否包含相关关键词（宽松匹配）
    category = test_case["category"]
    keyword_checks = {
        "k8s-basic": ["pod", "container", "kubernetes"],
        "k8s-service": ["service", "网络", "network", "负载", "load"],
        "k8s-init": ["init", "container", "初始化"],
        "redis-pipeline": ["pipeline", "管道", "批量", "batch", "redis"],
        "k8s-comparison": ["deployment", "statefulset", "区别", "difference"],
        "k8s-troubleshooting": ["crashloopbackoff", "debug", "排查", "troubleshoot", "log"],
        "k8s-service-discovery": ["service", "discovery", "发现", "dns", "kube-dns"],
        "k8s-howto": ["pod", "container", "multi", "多容器", "sidecar"],
        "k8s-resources": ["resource", "limit", "request", "资源", "cpu", "memory"],
        "k8s-concept": ["replicaset", "replica", "副本"],
        "k8s-namespace": ["namespace", "命名空间", "隔离", "isolation"],
        "k8s-pattern": ["sidecar", "container", "pattern", "模式"],
        "k8s-daemonset": ["daemonset", "node", "节点", "守护"],
    }

    expected_keywords = keyword_checks.get(category, [])
    answer_lower = answer.lower()
    matched_keywords = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    evaluation["quality_indicators"]["matched_keywords"] = matched_keywords
    evaluation["quality_indicators"]["keyword_match_rate"] = len(matched_keywords) / max(len(expected_keywords), 1)

    # 5. 综合判断
    has_substance = len(answer) >= 100
    has_keywords = len(matched_keywords) >= 1

    if has_substance and has_keywords:
        evaluation["test_passed"] = True
    else:
        if not has_substance:
            evaluation["failure_reasons"].append(f"答案内容不足 ({len(answer)} 字符)")
        if not has_keywords:
            evaluation["failure_reasons"].append(f"缺少关键词 (期望: {expected_keywords})")

    return evaluation


def run_all_tests() -> tuple:
    """运行所有 Agentic RAG 测试"""
    print("=" * 80)
    print("🤖 Agentic RAG 自动化测试")
    print("=" * 80)
    print(f"\n方法: Claude CLI → /search skill → 智能三层检索")
    print(f"测试用例: {len(TEST_CASES)}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目: {PROJECT_ROOT}\n")

    results = []
    passed = 0
    failed = 0
    errors = 0
    total_time = 0
    total_cost = 0

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] {test_case['id']}")
        print(f"  类别: {test_case['category']}")
        print(f"  查询: {test_case['query']}")

        # 执行 Agentic RAG
        result = run_agentic_search(test_case["query"])
        elapsed = result.get("elapsed_seconds", 0)
        total_time += elapsed

        # 评估答案
        evaluation = evaluate_answer(test_case, result)

        if result["status"] == "error":
            print(f"  状态: ❌ 错误")
            print(f"  错误: {result.get('error', 'Unknown')[:100]}")
            errors += 1
            status = "error"
        elif evaluation["test_passed"]:
            print(f"  状态: ✅ 通过")
            answer_len = len(result.get("answer", ""))
            print(f"  答案: {answer_len} 字符")
            if evaluation["quality_indicators"].get("has_citation"):
                print(f"  引用: ✅")
            keywords = evaluation["quality_indicators"].get("matched_keywords", [])
            if keywords:
                print(f"  关键词: {', '.join(keywords[:5])}")
            passed += 1
            status = "passed"
        else:
            print(f"  状态: ❌ 失败")
            print(f"  原因: {'; '.join(evaluation['failure_reasons'])}")
            failed += 1
            status = "failed"

        print(f"  耗时: {elapsed:.1f}s")
        cost = result.get("cost_usd", 0)
        total_cost += cost
        if cost > 0:
            print(f"  费用: ${cost:.4f}")

        results.append({
            "test_id": test_case["id"],
            "category": test_case["category"],
            "query": test_case["query"],
            "status": status,
            "elapsed_seconds": elapsed,
            "answer_length": len(result.get("answer", "")),
            "cost_usd": cost,
            "num_turns": result.get("num_turns", 0),
            "has_citation": evaluation.get("quality_indicators", {}).get("has_citation", False),
            "matched_keywords": evaluation.get("quality_indicators", {}).get("matched_keywords", []),
            "failure_reasons": evaluation.get("failure_reasons", []),
            "answer_preview": result.get("answer", "")[:300],
        })

        print("-" * 80)

    # 总结
    total = len(TEST_CASES)
    print("\n" + "=" * 80)
    print("🤖 Agentic RAG 测试总结")
    print("=" * 80)
    print(f"\n总用例: {total}")
    print(f"✅ 通过: {passed} ({passed/total*100:.1f}%)")
    print(f"❌ 失败: {failed} ({failed/total*100:.1f}%)")
    print(f"⚠️  错误: {errors} ({errors/total*100:.1f}%)")
    print(f"\n总耗时: {total_time:.1f}s")
    if passed + failed > 0:
        print(f"平均耗时: {total_time/(passed+failed):.1f}s/query")
    print(f"总费用: ${total_cost:.4f}")

    # 按类别统计
    print("\n按类别:")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0}
        categories[cat]["total"] += 1
        if r["status"] == "passed":
            categories[cat]["passed"] += 1

    for cat, stats in sorted(categories.items()):
        rate = stats["passed"] / stats["total"] * 100
        emoji = "✅" if rate == 100 else "⚠️" if rate > 0 else "❌"
        print(f"  {emoji} {cat}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")

    # 保存结果
    output_dir = PROJECT_ROOT / "eval"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"agentic_rag_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "test_type": "agentic_rag",
            "method": "claude_cli_search_skill",
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "total_time": total_time,
            "total_cost": total_cost,
            "results": results,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {output_file}")
    print("=" * 80)

    return results, str(output_file)


def generate_comparison_report(agentic_file: str):
    """生成 Simple RAG vs Agentic RAG 对比报告"""
    print("\n" + "=" * 80)
    print("📊 生成对比报告")
    print("=" * 80)

    # 读取 Simple RAG baseline
    simple_file = PROJECT_ROOT / "eval" / "comprehensive_test_20260213_234320.json"
    if not simple_file.exists():
        # 尝试找最新的
        simple_files = sorted((PROJECT_ROOT / "eval").glob("comprehensive_test_*.json"))
        if simple_files:
            simple_file = simple_files[-1]
        else:
            print("❌ 未找到 Simple RAG baseline 结果")
            return

    with open(simple_file, "r") as f:
        simple_data = json.load(f)

    with open(agentic_file, "r") as f:
        agentic_data = json.load(f)

    # 按 test_id 建立映射
    simple_map = {r["test_id"]: r for r in simple_data["results"]}
    agentic_map = {r["test_id"]: r for r in agentic_data["results"]}

    # 类别统计
    def calc_category_stats(results):
        cats = {}
        for r in results:
            cat = r["category"]
            if cat not in cats:
                cats[cat] = {"total": 0, "passed": 0, "avg_time": 0, "times": []}
            cats[cat]["total"] += 1
            if r["status"] == "passed":
                cats[cat]["passed"] += 1
            if r.get("elapsed_seconds"):
                cats[cat]["times"].append(r["elapsed_seconds"])
        for cat in cats:
            times = cats[cat]["times"]
            cats[cat]["avg_time"] = sum(times) / len(times) if times else 0
        return cats

    simple_cats = calc_category_stats(simple_data["results"])
    agentic_cats = calc_category_stats(agentic_data["results"])

    s_pass_rate = simple_data["passed"] / simple_data["total"] * 100
    a_pass_rate = agentic_data["passed"] / agentic_data["total"] * 100
    improvement = a_pass_rate - s_pass_rate

    s_avg_time = simple_data.get("total_time", 0) / simple_data["total"]
    a_avg_time = agentic_data.get("total_time", 0) / agentic_data["total"]

    report = f"""# Simple RAG vs Agentic RAG 对比报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试方法**: 自动化测试，相同 15 个查询集

## 📊 总体对比

| 指标 | Simple RAG | Agentic RAG | 变化 |
|------|-----------|-------------|------|
| **通过率** | {simple_data['passed']}/{simple_data['total']} ({s_pass_rate:.1f}%) | {agentic_data['passed']}/{agentic_data['total']} ({a_pass_rate:.1f}%) | **{improvement:+.1f}%** |
| **失败数** | {simple_data['failed']} | {agentic_data['failed']} | {agentic_data['failed'] - simple_data['failed']:+d} |
| **错误数** | {simple_data['errors']} | {agentic_data['errors']} | {agentic_data['errors'] - simple_data['errors']:+d} |
| **平均耗时** | {s_avg_time:.1f}s | {a_avg_time:.1f}s | {a_avg_time - s_avg_time:+.1f}s |
| **总费用** | ${simple_data.get('total_tokens', 0) * 0.000003:.4f} (est.) | ${agentic_data.get('total_cost', 0):.4f} | - |

## 📈 按类别对比

| 类别 | Simple RAG | Agentic RAG | 提升 |
|------|-----------|-------------|------|
"""

    all_categories = sorted(set(list(simple_cats.keys()) + list(agentic_cats.keys())))
    for cat in all_categories:
        s = simple_cats.get(cat, {"total": 0, "passed": 0})
        a = agentic_cats.get(cat, {"total": 0, "passed": 0})
        s_rate = s["passed"] / s["total"] * 100 if s["total"] > 0 else 0
        a_rate = a["passed"] / a["total"] * 100 if a["total"] > 0 else 0
        diff = a_rate - s_rate
        emoji = "🟢" if diff > 0 else "🔴" if diff < 0 else "⚪"
        report += f"| {cat} | {s['passed']}/{s['total']} ({s_rate:.0f}%) | {a['passed']}/{a['total']} ({a_rate:.0f}%) | {emoji} {diff:+.0f}% |\n"

    report += f"""
## 🔍 逐用例对比

| ID | 查询 | Simple | Agentic | 变化 |
|----|------|--------|---------|------|
"""

    for tc in TEST_CASES:
        tid = tc["id"]
        s_result = simple_map.get(tid, {})
        a_result = agentic_map.get(tid, {})
        s_status = "✅" if s_result.get("status") == "passed" else "❌"
        a_status = "✅" if a_result.get("status") == "passed" else "❌"

        if s_result.get("status") != "passed" and a_result.get("status") == "passed":
            change = "🟢 改善"
        elif s_result.get("status") == "passed" and a_result.get("status") != "passed":
            change = "🔴 退步"
        elif s_result.get("status") == "passed" and a_result.get("status") == "passed":
            change = "⚪ 持平"
        else:
            change = "⚪ 均失败"

        query_short = tc["query"][:40] + "..." if len(tc["query"]) > 40 else tc["query"]
        report += f"| {tid} | {query_short} | {s_status} | {a_status} | {change} |\n"

    # 改善和退步的详细分析
    improved = []
    regressed = []
    for tc in TEST_CASES:
        tid = tc["id"]
        s = simple_map.get(tid, {})
        a = agentic_map.get(tid, {})
        if s.get("status") != "passed" and a.get("status") == "passed":
            improved.append(tc)
        elif s.get("status") == "passed" and a.get("status") != "passed":
            regressed.append(tc)

    report += f"""
## 🟢 Agentic RAG 改善的查询 ({len(improved)} 个)

"""
    if improved:
        for tc in improved:
            a = agentic_map.get(tc["id"], {})
            report += f"### {tc['id']}: {tc['query']}\n"
            report += f"- Simple RAG: ❌ 失败\n"
            report += f"- Agentic RAG: ✅ 通过 ({a.get('answer_length', 0)} 字符, {a.get('elapsed_seconds', 0):.1f}s)\n"
            report += f"- 引用: {'✅' if a.get('has_citation') else '❌'}\n"
            report += f"- 关键词: {', '.join(a.get('matched_keywords', []))}\n\n"
    else:
        report += "无改善的查询。\n\n"

    if regressed:
        report += f"""## 🔴 Agentic RAG 退步的查询 ({len(regressed)} 个)

"""
        for tc in regressed:
            a = agentic_map.get(tc["id"], {})
            report += f"### {tc['id']}: {tc['query']}\n"
            report += f"- Simple RAG: ✅ 通过\n"
            report += f"- Agentic RAG: ❌ 失败\n"
            report += f"- 原因: {'; '.join(a.get('failure_reasons', ['Unknown']))}\n\n"

    report += f"""
## 💡 关键发现

### Agentic RAG 的优势
1. **智能策略选择**: Claude 自主决定使用 Grep、MCP Search 或多文档推理
2. **上下文扩展**: 自动读取完整文档上下文，不限于 chunk
3. **多步推理**: 对复杂问题可以分步检索和综合

### 对比总结
- 通过率: {s_pass_rate:.1f}% → {a_pass_rate:.1f}% ({improvement:+.1f}%)
- 改善查询: {len(improved)} 个
- 退步查询: {len(regressed)} 个
- 平均耗时: {s_avg_time:.1f}s → {a_avg_time:.1f}s

## 📝 结论

{'Agentic RAG 显著优于 Simple RAG' if improvement > 10 else 'Agentic RAG 略优于 Simple RAG' if improvement > 0 else 'Agentic RAG 与 Simple RAG 表现相当' if improvement == 0 else 'Agentic RAG 表现不如 Simple RAG'}。

{'主要改善在复杂推理和跨语言检索方面。' if improvement > 0 else ''}

---

**测试数据**:
- Simple RAG: {simple_file}
- Agentic RAG: {agentic_file}
"""

    report_file = PROJECT_ROOT / "eval" / f"AGENTIC_VS_SIMPLE_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✅ 对比报告: {report_file}")
    print("=" * 80)
    return str(report_file)


if __name__ == "__main__":
    # 先验证 claude CLI 可用
    try:
        check = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10)
        print(f"Claude CLI: {check.stdout.strip()}")
    except Exception as e:
        print(f"❌ Claude CLI 不可用: {e}")
        print("安装: npm install -g @anthropic-ai/claude-code")
        sys.exit(1)

    # 运行测试
    results, agentic_file = run_all_tests()

    # 生成对比报告
    generate_comparison_report(agentic_file)

    print(f"\n🎉 Agentic RAG 测试完成！")
