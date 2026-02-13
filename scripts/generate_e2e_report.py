#!/usr/bin/env python3
"""评测报告生成器 - 分析 E2E 测试结果并生成详细报告"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any


def load_latest_result(results_dir: str = "eval") -> Dict:
    """加载最新的测试结果"""
    files = [f for f in os.listdir(results_dir) if f.startswith("e2e_results_") and f.endswith(".json")]

    if not files:
        raise FileNotFoundError("未找到测试结果文件")

    latest_file = sorted(files)[-1]
    filepath = os.path.join(results_dir, latest_file)

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_markdown_report(result: Dict) -> str:
    """生成 Markdown 格式的报告"""

    report = []
    report.append("# E2E 测试报告\n")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**测试时间**: {result['timestamp']}\n")
    report.append(f"**测试时长**: {result['duration']:.2f} 秒\n")
    report.append("\n---\n")

    # 总体统计
    summary = result['summary']
    total = summary['total']
    passed = summary['passed']
    failed = summary['failed']
    errors = summary['errors']

    report.append("\n## 📊 总体统计\n")
    report.append(f"- **总用例数**: {total}\n")
    report.append(f"- **通过**: {passed} ({passed/total*100:.1f}%)\n")
    report.append(f"- **失败**: {failed} ({failed/total*100:.1f}%)\n")
    report.append(f"- **错误**: {errors} ({errors/total*100:.1f}%)\n")
    report.append(f"- **通过率**: {passed/total*100:.1f}%\n")

    # 性能统计
    results_list = result['results']
    avg_time = sum(r.get('elapsed_time', 0) for r in results_list) / len(results_list)
    total_tokens = sum(r.get('token_usage', {}).get('total_tokens', 0) for r in results_list)

    report.append("\n## ⏱️ 性能统计\n")
    report.append(f"- **平均响应时间**: {avg_time:.2f} 秒\n")
    report.append(f"- **总 Token 使用**: {total_tokens:,}\n")
    report.append(f"- **平均 Token/查询**: {total_tokens/total:.0f}\n")
    report.append(f"- **预估成本**: ${total_tokens * 0.000003:.4f} (Sonnet 定价)\n")

    # 按分类统计
    report.append("\n## 📈 分类统计\n")
    categories = {}
    for r in results_list:
        cat = r.get('category', 'unknown')
        if cat not in categories:
            categories[cat] = {'total': 0, 'passed': 0, 'avg_time': 0, 'times': []}
        categories[cat]['total'] += 1
        if r['status'] == 'passed':
            categories[cat]['passed'] += 1
        categories[cat]['times'].append(r.get('elapsed_time', 0))

    report.append("\n| 分类 | 通过/总数 | 通过率 | 平均耗时 |\n")
    report.append("|------|----------|--------|----------|\n")

    for cat, stats in sorted(categories.items()):
        pass_rate = stats['passed'] / stats['total'] * 100
        avg_time = sum(stats['times']) / len(stats['times'])
        report.append(f"| {cat} | {stats['passed']}/{stats['total']} | {pass_rate:.1f}% | {avg_time:.2f}s |\n")

    # 按语言统计
    report.append("\n## 🌍 语言统计\n")
    languages = {}
    for r in results_list:
        lang = r.get('language', 'unknown')
        if lang not in languages:
            languages[lang] = {'total': 0, 'passed': 0}
        languages[lang]['total'] += 1
        if r['status'] == 'passed':
            languages[lang]['passed'] += 1

    report.append("\n| 语言 | 通过/总数 | 通过率 |\n")
    report.append("|------|----------|--------|\n")

    for lang, stats in sorted(languages.items()):
        pass_rate = stats['passed'] / stats['total'] * 100
        report.append(f"| {lang} | {stats['passed']}/{stats['total']} | {pass_rate:.1f}% |\n")

    # 关键词覆盖率分析
    report.append("\n## 🔍 关键词覆盖率分析\n")

    coverage_ranges = {
        '优秀 (80%+)': [],
        '良好 (60-80%)': [],
        '一般 (40-60%)': [],
        '较差 (<40%)': []
    }

    for r in results_list:
        if r['status'] == 'passed' or r['status'] == 'failed':
            coverage = r.get('keyword_coverage', 0)
            test_id = r['test_id']

            if coverage >= 0.8:
                coverage_ranges['优秀 (80%+)'].append((test_id, coverage))
            elif coverage >= 0.6:
                coverage_ranges['良好 (60-80%)'].append((test_id, coverage))
            elif coverage >= 0.4:
                coverage_ranges['一般 (40-60%)'].append((test_id, coverage))
            else:
                coverage_ranges['较差 (<40%)'].append((test_id, coverage))

    for range_name, cases in coverage_ranges.items():
        if cases:
            report.append(f"\n### {range_name}\n")
            for test_id, coverage in cases:
                report.append(f"- {test_id}: {coverage:.1%}\n")

    # 失败用例详情
    failed_cases = [r for r in results_list if r['status'] in ['failed', 'error']]

    if failed_cases:
        report.append("\n## ❌ 失败/错误用例详情\n")

        for r in failed_cases:
            report.append(f"\n### {r['test_id']}\n")
            report.append(f"- **查询**: {r['query']}\n")
            report.append(f"- **状态**: {r['status']}\n")

            if r['status'] == 'failed':
                coverage = r.get('keyword_coverage', 0)
                keywords_found = r.get('keywords_found', [])
                keywords_expected = r.get('keywords_expected', [])

                report.append(f"- **关键词覆盖**: {coverage:.1%}\n")
                report.append(f"- **找到的关键词**: {', '.join(keywords_found) if keywords_found else '无'}\n")
                report.append(f"- **期望的关键词**: {', '.join(keywords_expected)}\n")
            else:
                report.append(f"- **错误**: {r.get('error', 'Unknown error')}\n")

    # 优秀用例
    excellent_cases = [r for r in results_list if r['status'] == 'passed' and r.get('keyword_coverage', 0) >= 0.8]

    if excellent_cases:
        report.append("\n## ✅ 优秀用例 (关键词覆盖 80%+)\n")

        for r in excellent_cases:
            report.append(f"\n### {r['test_id']}\n")
            report.append(f"- **查询**: {r['query']}\n")
            report.append(f"- **关键词覆盖**: {r.get('keyword_coverage', 0):.1%}\n")
            report.append(f"- **响应时间**: {r.get('elapsed_time', 0):.2f}s\n")
            report.append(f"- **找到的关键词**: {', '.join(r.get('keywords_found', []))}\n")

    # 改进建议
    report.append("\n## 💡 改进建议\n")

    # 分析失败原因
    if failed > 0:
        report.append("\n### 失败用例分析\n")

        low_coverage_cases = [r for r in results_list if r['status'] == 'failed' and r.get('keyword_coverage', 0) < 0.4]
        if low_coverage_cases:
            report.append(f"- **关键词覆盖率低** ({len(low_coverage_cases)} 个用例):\n")
            report.append("  - 建议: 优化文档分块策略，保留更多上下文\n")
            report.append("  - 建议: 调整 min_score 阈值\n")

    # 性能优化建议
    slow_cases = [r for r in results_list if r.get('elapsed_time', 0) > 3.0]
    if slow_cases:
        report.append(f"\n### 性能优化\n")
        report.append(f"- **响应时间过长** ({len(slow_cases)} 个用例 > 3秒):\n")
        report.append("  - 建议: 优化检索策略，先用快速关键词检索\n")
        report.append("  - 建议: 减少 top_k 参数\n")

    # 跨语言检索建议
    cross_lang_cases = [r for r in results_list if r.get('target_doc_lang')]
    if cross_lang_cases:
        cross_lang_passed = sum(1 for r in cross_lang_cases if r['status'] == 'passed')
        cross_lang_rate = cross_lang_passed / len(cross_lang_cases) * 100

        report.append(f"\n### 跨语言检索\n")
        report.append(f"- **通过率**: {cross_lang_rate:.1f}% ({cross_lang_passed}/{len(cross_lang_cases)})\n")

        if cross_lang_rate < 70:
            report.append("  - 建议: 增强跨语言检索能力\n")
            report.append("  - 建议: 调整 sparse 向量权重\n")

    report.append("\n---\n")
    report.append(f"\n**报告生成完成** - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    return "".join(report)


def main():
    try:
        # 加载最新结果
        result = load_latest_result()

        # 生成报告
        report = generate_markdown_report(result)

        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"eval/e2e_report_{timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"✅ 报告已生成: {report_file}")

        # 同时输出到控制台
        print("\n" + "="*80)
        print(report)

    except Exception as e:
        print(f"❌ 生成报告失败: {e}")


if __name__ == "__main__":
    main()
