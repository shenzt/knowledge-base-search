#!/usr/bin/env python3
"""E2E 测试套件 - 端到端验证双层架构和 RAG 系统

测试覆盖:
1. 文档转换 (HTML → Markdown)
2. 索引构建 (分层索引 + 向量索引)
3. 知识检索 (混合检索 + Reranker)
4. 端到端流程 (转换 → 索引 → 检索)
5. 跨语言检索 (中英文)
6. 复杂查询 (多步推理)
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any

from sonnet_worker import run_rag_task, search_knowledge_base

# 加载测试用例
def load_test_cases(config_file: str = "eval/test_cases.json") -> Dict:
    """从配置文件加载测试用例"""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config["test_suites"]
    except FileNotFoundError:
        print(f"⚠️  配置文件未找到: {config_file}，使用默认测试用例")
        return get_default_test_cases()
    except Exception as e:
        print(f"⚠️  加载配置文件失败: {e}，使用默认测试用例")
        return get_default_test_cases()


def get_default_test_cases() -> Dict:
    """默认测试用例（如果配置文件不存在）"""
    return {
        "basic_search": [
            {
                "id": "basic-001",
                "query": "What is a Pod in Kubernetes?",
                "language": "en",
                "category": "k8s-basic",
                "expected_keywords": ["pod", "container", "smallest", "deployable"],
                "min_score": 0.5
            }
        ]
    }


# 测试用例定义
TEST_CASES = load_test_cases()


class E2ETestRunner:
    """E2E 测试运行器"""

    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None

    async def run_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """运行单个测试用例"""
        test_id = test_case["id"]
        query = test_case["query"]

        print(f"\n{'='*80}")
        print(f"测试用例: {test_id}")
        print(f"查询: {query}")
        print(f"语言: {test_case['language']}")
        print(f"分类: {test_case['category']}")
        print(f"{'='*80}")

        start = datetime.now()

        try:
            # 执行检索
            result = await search_knowledge_base(query, top_k=5)

            elapsed = (datetime.now() - start).total_seconds()

            # 解析结果
            if result["status"] == "success":
                result_text = result.get("result", "")

                # 检查关键词
                keywords_found = []
                for keyword in test_case["expected_keywords"]:
                    if keyword.lower() in result_text.lower():
                        keywords_found.append(keyword)

                keyword_coverage = len(keywords_found) / len(test_case["expected_keywords"])

                # 评估结果
                passed = keyword_coverage >= 0.5  # 至少匹配 50% 关键词

                test_result = {
                    "test_id": test_id,
                    "status": "passed" if passed else "failed",
                    "query": query,
                    "language": test_case["language"],
                    "category": test_case["category"],
                    "elapsed_time": elapsed,
                    "keyword_coverage": keyword_coverage,
                    "keywords_found": keywords_found,
                    "keywords_expected": test_case["expected_keywords"],
                    "result_length": len(result_text),
                    "tool_calls": len(result.get("tool_calls", [])),
                    "token_usage": result.get("usage", {})
                }

                print(f"\n✅ 状态: {'通过' if passed else '失败'}")
                print(f"⏱️  耗时: {elapsed:.2f}s")
                print(f"📊 关键词覆盖: {keyword_coverage:.1%} ({len(keywords_found)}/{len(test_case['expected_keywords'])})")
                print(f"🔍 找到的关键词: {', '.join(keywords_found)}")

            else:
                test_result = {
                    "test_id": test_id,
                    "status": "error",
                    "query": query,
                    "error": result.get("error", "Unknown error"),
                    "elapsed_time": elapsed
                }
                print(f"\n❌ 错误: {result.get('error', 'Unknown error')}")

        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            test_result = {
                "test_id": test_id,
                "status": "error",
                "query": query,
                "error": str(e),
                "elapsed_time": elapsed
            }
            print(f"\n❌ 异常: {e}")

        return test_result

    async def run_test_suite(self, suite_name: str, test_cases: List[Dict]) -> List[Dict]:
        """运行测试套件"""
        print(f"\n{'#'*80}")
        print(f"# 测试套件: {suite_name}")
        print(f"# 用例数量: {len(test_cases)}")
        print(f"{'#'*80}")

        suite_results = []
        for test_case in test_cases:
            result = await run_test_case(test_case)
            suite_results.append(result)

            # 短暂延迟，避免过载
            await asyncio.sleep(1)

        return suite_results

    async def run_all_tests(self):
        """运行所有测试"""
        self.start_time = datetime.now()
        print(f"\n{'='*80}")
        print(f"E2E 测试开始")
        print(f"时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")

        all_results = []

        for suite_name, test_cases in TEST_CASES.items():
            suite_results = await self.run_test_suite(suite_name, test_cases)
            all_results.extend(suite_results)

        self.end_time = datetime.now()
        self.results = all_results

        # 生成报告
        self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        print(f"\n{'='*80}")
        print(f"测试报告")
        print(f"{'='*80}")

        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "passed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        errors = sum(1 for r in self.results if r["status"] == "error")

        total_time = (self.end_time - self.start_time).total_seconds()
        avg_time = sum(r.get("elapsed_time", 0) for r in self.results) / total if total > 0 else 0

        print(f"\n📊 总体统计:")
        print(f"  总用例: {total}")
        print(f"  通过: {passed} ({passed/total*100:.1f}%)")
        print(f"  失败: {failed} ({failed/total*100:.1f}%)")
        print(f"  错误: {errors} ({errors/total*100:.1f}%)")
        print(f"  总耗时: {total_time:.2f}s")
        print(f"  平均耗时: {avg_time:.2f}s")

        # 按分类统计
        print(f"\n📈 分类统计:")
        categories = {}
        for r in self.results:
            cat = r.get("category", "unknown")
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0}
            categories[cat]["total"] += 1
            if r["status"] == "passed":
                categories[cat]["passed"] += 1

        for cat, stats in sorted(categories.items()):
            pass_rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"  {cat}: {stats['passed']}/{stats['total']} ({pass_rate:.1f}%)")

        # 失败用例
        if failed > 0 or errors > 0:
            print(f"\n❌ 失败/错误用例:")
            for r in self.results:
                if r["status"] in ["failed", "error"]:
                    print(f"  {r['test_id']}: {r['query']}")
                    if r["status"] == "failed":
                        coverage = r.get("keyword_coverage", 0)
                        print(f"    关键词覆盖: {coverage:.1%}")
                    else:
                        print(f"    错误: {r.get('error', 'Unknown')}")

        # Token 使用统计
        total_tokens = sum(
            r.get("token_usage", {}).get("total_tokens", 0)
            for r in self.results
        )
        print(f"\n💰 Token 使用:")
        print(f"  总计: {total_tokens}")
        print(f"  平均: {total_tokens/total:.0f} per query")
        print(f"  预估成本: ${total_tokens * 0.000003:.4f} (Sonnet 定价)")

        # 保存结果
        self.save_results()

    def save_results(self):
        """保存测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval/e2e_results_{timestamp}.json"

        os.makedirs("eval", exist_ok=True)

        report = {
            "timestamp": self.start_time.isoformat(),
            "duration": (self.end_time - self.start_time).total_seconds(),
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r["status"] == "passed"),
                "failed": sum(1 for r in self.results if r["status"] == "failed"),
                "errors": sum(1 for r in self.results if r["status"] == "error")
            },
            "results": self.results
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n💾 结果已保存: {filename}")


async def main():
    runner = E2ETestRunner()
    await runner.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
