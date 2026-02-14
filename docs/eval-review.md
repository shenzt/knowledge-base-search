---
id: "eval-review-001"
title: "RAG 评测方案 Review"
created: 2025-02-14
confidence: high
---

# RAG 评测方案 Review

## 当前评测现状

### 我们在测什么

```
用户查询 → Agent (Grep/hybrid_search/Read) → 生成答案
                                                  ↓
                                            evaluate(tc, result)
                                                  ↓
                                            passed / failed
```

### 当前评估维度

| 维度 | 实现方式 | 问题 |
|------|----------|------|
| 答案长度 | `len(answer) >= 100` | 太粗糙，长不等于好 |
| 关键词匹配 | 答案包含 1+ 预设关键词 | 通用知识也能命中 |
| 引用检查 | 答案包含 `docs/` 或 `.md` | 只检查格式，不验证正确性 |
| 正确文档 | 答案包含 expected_doc 文件名 | 文件名匹配太宽松 |
| 防幻觉 | Qdrant 用例检查 "未找到" 短语 | 仅在 USE_MCP=0 时有效 |

### 当前测试结果

| 版本 | 本地 docs/ | Qdrant | notfound | 总计 |
|------|-----------|--------|----------|------|
| v2 (宽松) | 17/17 (100%) | 6/12 (50%) | 0/3 (0%) | 23/32 (71.9%) |
| v3 (收紧) | 17/17 (100%) | 1/12 (8%) | 3/3 (100%) | 21/32 (65.6%) |

v2→v3 的差异完全来自 Qdrant 假阳性被过滤。说明评估标准本身就是最大变量。

### 核心问题

1. **没有 ground truth**: 没有标准答案，无法计算 faithfulness / correctness
2. **不测检索质量**: 只测最终答案，不测中间的 retrieved_contexts
3. **关键词 ≠ 质量**: "包含 pod 这个词" 不等于 "正确解释了 Pod 的概念"
4. **无法区分来源**: 答案对了，但不知道是从文档检索的还是模型通用知识

## Ragas 能解决什么

[Ragas](https://docs.ragas.io/) 是 RAG 评测框架，核心指标：

| 指标 | 测什么 | 输入 | 我们需要吗 |
|------|--------|------|-----------|
| Faithfulness | 答案是否基于 context（非幻觉） | query + response + contexts | ✅ 核心需求 |
| Response Relevancy | 答案是否回答了问题 | query + response | ✅ 替代关键词匹配 |
| Context Precision | 检索结果排序质量（相关的排前面） | query + contexts + reference | ⚠️ 需要 reference |
| Context Recall | 检索是否召回了必要信息 | query + contexts + reference | ⚠️ 需要 reference |
| Factual Correctness | 答案事实是否正确 | response + reference | ⚠️ 需要 reference |

### Ragas 的代价

1. **需要 ground truth (reference)**: Context Precision/Recall/Factual Correctness 都需要标准答案
2. **需要 retrieved_contexts**: 必须拿到中间检索结果，不只是最终答案
3. **LLM-as-Judge**: Faithfulness/Relevancy 用 LLM 评分，有成本和一致性问题
4. **额外依赖**: ragas + datasets + 评估用 LLM API

## 评测方案对比

### 方案 A: 继续自建（改进当前方案）

```
优点: 零依赖，完全可控，贴合我们的极简理念
缺点: 指标不够科学，难以和业界对比
```

改进方向:
- 用 LLM-as-Judge 替代关键词匹配（调 Claude API 评分）
- 从 Agent SDK 消息日志中提取 retrieved_contexts
- 为每个 test case 写 reference answer
- 加入 latency / cost / tool_calls 效率指标

### 方案 B: 引入 Ragas

```
优点: 业界标准指标，科学可对比，社区活跃
缺点: 重依赖，需要准备 ground truth dataset，LLM 评估成本
```

集成方式:
- 从 Agent SDK 日志提取 (query, contexts, response) 三元组
- 喂给 Ragas 计算 Faithfulness + Response Relevancy（不需要 reference）
- 可选: 为核心用例写 reference，启用 Context Precision/Recall

### 方案 C: 混合方案（推荐）

```
自建快速检查 + Ragas 深度评估
```

分两层:

**Layer 1: 自建快速检查（每次 CI 跑）**
- 引用完整性: 答案是否包含 section_path 或 chunk_id
- 来源验证: 引用的文档是否是 expected_doc
- 防幻觉: Qdrant 用例是否真正调用了 hybrid_search
- 拒答能力: notfound 用例是否正确拒答
- 效率: latency, cost, tool_calls 数量

**Layer 2: Ragas 深度评估（定期跑）**
- Faithfulness: 答案是否基于检索结果（核心！）
- Response Relevancy: 答案是否切题
- 可选: Context Precision/Recall（需要 reference）

## 推荐方案: 方案 C 的极简实现

### 不需要 Ragas 也能做的（优先）

#### 1. 从 Agent 日志提取 retrieved_contexts

当前 `test_agentic_rag_sdk.py` 已经记录了完整的 `messages_log`，包含每次 tool call 的输入输出。可以从中提取:

```python
# 从 messages_log 中提取检索到的文档
def extract_contexts(messages_log):
    contexts = []
    for msg in messages_log:
        if msg.get("tool_name") == "Grep":
            contexts.append({"tool": "Grep", "result": msg.get("tool_result", "")})
        elif msg.get("tool_name") == "Read":
            contexts.append({"tool": "Read", "result": msg.get("tool_result", "")})
        elif msg.get("tool_name") == "mcp__knowledge-base__hybrid_search":
            contexts.append({"tool": "hybrid_search", "result": msg.get("tool_result", "")})
    return contexts
```

#### 2. LLM-as-Judge 替代关键词匹配

用 Claude API 做 0-5 分评估，替代 "包含 1 个关键词就通过":

```python
judge_prompt = """评估以下 RAG 回答的质量 (0-5 分):

问题: {query}
检索到的文档: {contexts}
回答: {answer}

评分标准:
- 5: 完全基于文档，准确全面，引用正确
- 4: 基于文档，基本准确，有引用
- 3: 部分基于文档，有遗漏
- 2: 主要靠通用知识，文档引用不准确
- 1: 与文档无关，纯通用知识
- 0: 错误或幻觉

返回 JSON: {"score": N, "reason": "..."}
"""
```

#### 3. 检索质量指标（不需要 Ragas）

```python
# 检索效率
retrieval_metrics = {
    "tools_called": ["Grep", "Read"],           # 调了哪些工具
    "hybrid_search_used": False,                  # 是否用了向量检索
    "contexts_count": 3,                          # 检索到几个 context
    "correct_doc_retrieved": True,                # 是否检索到正确文档
    "first_relevant_rank": 1,                     # 第一个相关结果的排名
}
```

### 需要 Ragas 的场景

只有当你需要以下能力时才引入 Ragas:

1. **和业界 benchmark 对比**: 用标准指标发论文或做产品对比
2. **大规模评测**: 100+ test cases，需要自动化 ground truth 生成
3. **多维度雷达图**: Faithfulness × Relevancy × Precision × Recall 的综合视图
4. **持续监控**: 每次部署后自动跑评测，追踪指标趋势

### 当前阶段不需要 Ragas 的理由

1. 知识库只有 21+3 个文档，手写 reference 完全可行
2. 评测用例 32 个，规模不大
3. 核心问题是"检索到没有"而不是"检索排序好不好"
4. LLM-as-Judge 可以用 Claude API 直接做，不需要框架
5. 极简原则：能不引入依赖就不引入

## 改进计划

### Phase 1: 自建改进（0 依赖）

- [ ] 从 messages_log 提取 retrieved_contexts
- [ ] 加入 `correct_doc_retrieved` 指标（检查 tool_result 中是否包含 expected_doc）
- [ ] 加入 `hybrid_search_used` 指标（检查是否调用了 MCP 工具）
- [ ] 为每个 test case 写 `reference_answer`（简短标准答案）
- [ ] LLM-as-Judge: 用 Claude API 做 0-5 分评估

### Phase 2: 可选引入 Ragas

- [ ] 如果 Phase 1 的 LLM-as-Judge 不够稳定，引入 Ragas Faithfulness
- [ ] 如果需要和业界对比，引入 Ragas 全套指标
- [ ] 如果评测规模扩大到 100+，用 Ragas 的 dataset 管理

### 不做的事情

- ❌ 不为了引入 Ragas 而引入 Ragas
- ❌ 不在没有 ground truth 的情况下跑 Context Precision/Recall
- ❌ 不用 Ragas 替代我们的快速检查（两层互补，不是替代）

## 数据格式设计

无论是否引入 Ragas，统一数据格式（兼容 Ragas 的 SingleTurnSample）:

```python
test_case = {
    # 输入
    "user_input": "READONLY You can't write against a read only replica 怎么解决",

    # 检索结果（从 Agent 日志提取）
    "retrieved_contexts": [
        "Redis Sentinel 触发主从切换后...",  # chunk text
    ],

    # Agent 输出
    "response": "根据文档，这个错误是 Redis Sentinel 主从切换导致的...",

    # Ground truth（手写）
    "reference": "READONLY 错误是 Redis Sentinel failover 后，应用仍连接旧 master（已降为 replica）导致。解决方案：使用 Sentinel 客户端自动切换。",

    # 元数据
    "expected_doc": "redis-failover.md",
    "source": "local",
    "type": "exact",
}
```

这个格式可以直接喂给:
- 我们的自建评估函数
- Ragas 的 `SingleTurnSample`
- 任何其他评测框架
