# 评测体系升级实施计划

## 执行顺序

### Part 1: RAGAS 集成（替换自研 Judge）— ~1 天

1. 安装依赖：ragas, datasets, langchain-anthropic, langchain-openai
2. 创建 `scripts/ragas_judge.py` — RAGAS 评测封装
   - faithfulness (0-1, claim-level) + answer_relevancy (0-1, embedding-based)
   - Judge LLM: Claude Sonnet 4.5, temperature=0
   - answer_relevancy embedding: OpenAI text-embedding-3-small（先用，后续可切 BGE-M3）
   - 向后兼容：映射到 0-5 scale
3. 修改 `scripts/eval_module.py` — llm_judge() 委托给 ragas_judge()，保留 _legacy_llm_judge()
4. 修改 `tests/e2e/test_agentic_rag_sdk.py` — 适配 0-1 分制显示，detail.jsonl 保存 contexts
5. 5-case smoke test 验证
6. 全量 100-case 跑新 baseline

### Part 2: RAGBench techqa 导入 — ~0.5 天

1. 下载 rungalileo/ragbench techqa 子集
2. 选取 50-100 QA pairs + 对应文档
3. 文档转 Markdown + front-matter → docs/ragbench-techqa/
4. 预处理 + 索引
5. 创建 tests/fixtures/ragbench_techqa_cases.py
6. Smoke test

### Part 3: CRAG 子集导入 — ~0.5 天

1. 下载 CRAG，选 1 个领域（finance）~50 QA pairs
2. HTML → Markdown 转换（markdownify）
3. 文档导入 + 索引
4. 创建 test fixtures
5. 合并评测

## 新增/修改文件

| 操作 | 文件 | 说明 |
|------|------|------|
| CREATE | scripts/ragas_judge.py | RAGAS 评测封装 |
| MODIFY | scripts/eval_module.py | llm_judge() → ragas_judge() |
| MODIFY | tests/e2e/test_agentic_rag_sdk.py | 0-1 分制 + EVAL_DATASET 切换 |
| MODIFY | scripts/requirements.txt | 新增依赖 |
| CREATE | scripts/import_ragbench.py | RAGBench 下载转换 |
| CREATE | scripts/import_crag.py | CRAG 下载转换 |
| CREATE | tests/fixtures/ragbench_techqa_cases.py | RAGBench 测试用例 |
| CREATE | tests/fixtures/crag_finance_cases.py | CRAG 测试用例 |
