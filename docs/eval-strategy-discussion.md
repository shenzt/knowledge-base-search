---
id: "eval-disc"
title: "评测体系升级讨论稿：RAGAS + 公开数据集"
created: 2025-02-18
confidence: medium
---

# 评测体系升级讨论稿：RAGAS + 公开数据集

## 背景

我们在构建一个通用的 Agentic RAG 平台（Git + Qdrant + Claude Code）。当前评测体系基于自建 100 case + 自研 LLM Judge，存在以下问题：

1. **指标不标准** — 自研 1-5 分 faithfulness/relevancy，无法与业界横向对比
2. **数据集单一** — 仅覆盖 Redis + LLM Apps 两个领域，无法验证平台通用性
3. **评测波动大** — Agent 行为随机（temperature 不可控）+ Judge 打分粒度粗，R8-R10 faithfulness 在 3.88-4.27 间波动
4. **缺少检索质量指标** — 只评端到端回答质量，不单独评 retriever 的 precision/recall

### 当前评测结果（R10）

| 指标 | 值 |
|------|-----|
| Gate 通过率 | 100/100 |
| Faithfulness | 3.94/5（自研 Judge） |
| Relevancy | 4.76/5 |
| 评测成本 | $8.72/轮 |
| 数据集 | 100 case（Redis 40 + LLM Apps 35 + Local 15 + Notfound 10） |

---

## 议题一：是否引入 RAGAS 替代自研 Judge？

### RAGAS 核心指标

| 指标 | 测什么 | 需要 ground truth？ | 方法论 |
|------|--------|-------------------|--------|
| **Faithfulness** | 回答是否忠于检索到的 context | ❌ 不需要 | 拆解 response 为 claims → 逐条验证是否有 context 支撑 → supported/total = 0-1 分 |
| **Context Precision** | 检索结果中相关 chunk 的排名质量 | ⚠️ 需要 reference answer 或 reference contexts | Mean Precision@K，rank-aware |
| **Context Recall** | 检索结果是否覆盖了所有必要信息 | ✅ 需要 ground truth answer | 检查 ground truth 中的每个 claim 是否能在 contexts 中找到 |
| **Response Relevancy** | 回答是否切题 | ❌ 不需要 | 生成多个问题反推，计算与原始问题的语义相似度 |

参考：[RAGAS 论文](https://arxiv.org/html/2309.15217v2) | [RAGAS 文档](https://docs.ragas.io/en/stable/)

### 对比分析

| 维度 | 自研 Judge | RAGAS |
|------|-----------|-------|
| Faithfulness 粒度 | 1-5 整数分 | 0-1 连续分（claim-level） |
| 检索质量评估 | ❌ 无 | ✅ Context Precision + Recall |
| 可复现性 | 中（LLM 打分有随机性） | 高（claim 拆解 + 逐条验证，更确定性） |
| 业界可比性 | ❌ 自研指标 | ✅ 标准指标，论文/博客通用 |
| 集成成本 | 已有 | `pip install ragas`，适配数据格式即可 |
| Judge LLM | Claude Sonnet 4.5 | 支持 Claude / DeepSeek / GPT 等任意模型 |
| 成本 | ~$0.09/case | 类似（取决于 Judge LLM 选择） |

### 讨论点

1. 是否完全替换自研 Judge，还是两套并行跑一段时间做对比？
2. RAGAS 的 Faithfulness 是 claim-level 验证（更严格），可能导致分数普遍偏低 — 这是否可接受？
3. Context Precision/Recall 需要 ground truth，是否值得为 100 case 补充标注？
4. RAGAS 默认用 OpenAI，我们用 Claude/DeepSeek 作为 Judge LLM，是否需要验证一致性？

---

## 议题二：引入哪些公开数据集？

### 目标

作为通用 Agentic RAG 平台，需要验证：
- 不同领域的检索质量（不只是 Redis/LLM Apps）
- 不同问题类型的处理能力（单跳、多跳、事实核查、对比分析）
- 不同文档格式的适应性（长文档、表格、代码）

### 候选数据集

#### Tier 1：强烈推荐（有 ground truth contexts + answers，可直接用于端到端评测）

| 数据集 | 规模 | 领域 | 特点 | 链接 |
|--------|------|------|------|------|
| **RAGBench** | 100K examples, 12 子集 | 金融、医疗、法律、技术、通用 | sentence-level grounding 标注，已含 RAGAS 分数，12 个领域子集 | [HuggingFace](https://huggingface.co/datasets/rungalileo/ragbench) |
| **HotpotQA** | 113K QA pairs | Wikipedia 多跳推理 | 需要跨文档推理，测试 Agent 多轮检索能力 | [hotpotqa.github.io](https://hotpotqa.github.io/) |
| **Natural Questions** | 307K QA pairs | Google 真实搜索 | 真实用户查询，长/短答案标注 | [ai.google.com/research/NaturalQuestions](https://ai.google.com/research/NaturalQuestions) |

#### Tier 2：值得考虑（特定能力测试）

| 数据集 | 规模 | 领域 | 特点 | 链接 |
|--------|------|------|------|------|
| **CRAG** | 4,409 QA pairs | 5 领域 × 8 问题类型 | Meta 出品，覆盖时效性、实体流行度、复杂度维度 | [GitHub](https://github.com/facebookresearch/CRAG) |
| **MultiHop-RAG** | - | 多跳推理 | 专测多跳检索 + 推理，适合验证 Agent 多轮工具调用 | [GitHub](https://github.com/yixuantt/MultiHop-RAG) |
| **GaRAGe** | 2,366 Q + 35K passages | 通用 | ACL 2025，grounding annotations，测 faithfulness/attribution | [ACL](https://aclanthology.org/2025.findings-acl.875/) |
| **RAGTruth** | 18K responses | 通用 | 专测幻觉检测，区分 evident/subtle conflicts | [论文](https://arxiv.org/abs/2407.11005) |

#### Tier 3：参考（经典但可能不直接适用）

| 数据集 | 说明 |
|--------|------|
| **MS MARCO** | 大规模 passage ranking，更适合测 retriever 而非端到端 RAG |
| **BeIR** | 18 个零样本检索任务，测 embedding 泛化能力 |
| **FEVER** | 事实核查，185K claims，测 evidence retrieval + verification |

### 讨论点

1. **RAGBench 优先级最高？** — 12 个领域子集（techqa、finqa、pubmedqa 等），已含 sentence-level grounding 标注和 RAGAS 分数，可以直接对比我们的系统 vs baseline。但需要将其文档导入我们的 Qdrant 索引。
2. **HotpotQA 测多跳能力** — 我们的 Agent 支持多轮工具调用，HotpotQA 的多跳推理正好测试这个能力。但需要先将 Wikipedia 文档子集导入 KB。
3. **数据集导入成本** — 公开数据集的文档需要导入我们的 Qdrant 索引才能测试。这意味着：
   - 需要将数据集的 corpus 转为 Markdown → 导入 KB → 建索引
   - 或者修改评测脚本，直接将 ground truth contexts 注入 Agent 的检索结果（跳过检索，只测生成质量）
4. **两种评测模式？**
   - **Component-level**：直接用公开数据集的 contexts，只评 generation 质量（faithfulness、relevancy）
   - **End-to-end**：将文档导入 KB，从检索到生成全链路评测（+ context precision/recall）

---

## 议题三：评测架构升级方案

### 方案 A：最小改动 — RAGAS 替换 Judge

```
现有 100 case 评测流程不变
  → Agent SDK 跑完后，从 messages_log 提取 (question, contexts, response)
  → 喂给 RAGAS evaluate() 替代自研 llm_judge()
  → 输出标准 RAGAS 指标（faithfulness 0-1, context_precision, response_relevancy）
```

工作量：~1 天，改 eval_module.py 的 judge 部分
收益：指标标准化，可与业界对比

### 方案 B：中等改动 — RAGAS + RAGBench 子集

```
方案 A 基础上：
  → 选 RAGBench 的 2-3 个子集（techqa、finqa、emanual）
  → 将其 corpus 导入 Qdrant（通过 /ingest 流程）
  → 用其 QA pairs 作为评测 case
  → 端到端评测：检索 + 生成 + RAGAS 全指标
```

工作量：~3-5 天（数据导入 + 评测脚本适配 + 跑评测）
收益：验证平台通用性，多领域评测

### 方案 C：完整升级 — 标准化评测框架

```
方案 B 基础上：
  → 支持 component-level 评测（跳过检索，直接注入 contexts）
  → 支持多数据集切换（RAGBench / HotpotQA / 自建）
  → CI/CD 集成（每次代码变更自动跑评测子集）
  → 评测结果 dashboard（历史趋势、跨数据集对比）
```

工作量：~1-2 周
收益：完整的评测基础设施，支持持续迭代

### 讨论点

1. 当前阶段选哪个方案？A 最快见效，C 最完整但投入大
2. 评测 LLM 选什么？Claude Sonnet（质量高但贵）vs DeepSeek V3（便宜但需验证一致性）
3. 是否需要 component-level 评测？还是只做端到端就够了？

---

## 附录：技术细节

### RAGAS 集成代码示例

```python
from ragas import evaluate
from ragas.metrics import faithfulness, context_precision, answer_relevancy
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample

# 从 Agent SDK messages_log 提取数据
samples = []
for case in eval_results:
    samples.append(SingleTurnSample(
        user_input=case["query"],
        retrieved_contexts=case["contexts"],  # 从 messages_log 提取
        response=case["answer"],
        reference=case.get("ground_truth", None),  # 可选
    ))

dataset = EvaluationDataset(samples=samples)
results = evaluate(
    dataset=dataset,
    metrics=[faithfulness, context_precision, answer_relevancy],
    llm=ragas_llm,  # Claude / DeepSeek / GPT
)
print(results)  # {'faithfulness': 0.82, 'context_precision': 0.75, ...}
```

### RAGBench 数据格式

```json
{
  "question": "What is the maximum number of devices supported?",
  "documents": ["The system supports up to 256 devices...", "..."],
  "response": "The maximum number of devices supported is 256.",
  "documents_sentences": [["The system supports up to 256 devices.", "..."]],
  "response_sentences": [["The maximum number of devices supported is 256."]],
  "sentence_support_information": [{
    "response_sentence_key": "response_0_0",
    "supporting_sentence_keys": ["documents_0_0"],
    "fully_supported": true,
    "explanation": "Directly stated in document 0, sentence 0"
  }],
  "ragas_faithfulness": 1.0,
  "ragas_context_relevance": 0.85
}
```

### 当前评测数据格式

```json
{
  "test_id": "redis-dt-001",
  "query": "What is the difference between Redis Sorted Sets and regular Sets?",
  "answer": "Based on the search results...",
  "retrieved_paths": ["../my-agent-kb/docs/redis-docs/.../sorted-sets.md"],
  "contexts_count": 1,
  "judge_score": 5,
  "faithfulness": 5,
  "relevancy": 5
}
```

---

## 期望讨论输出

1. 确定评测升级方案（A/B/C）
2. 确定优先引入的公开数据集（1-2 个）
3. 确定 RAGAS Judge LLM 选型
4. 确定是否需要为现有 100 case 补充 ground truth 标注
