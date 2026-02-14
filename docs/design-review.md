---
id: "design-review-002"
title: "RAG 系统设计 Review v2"
created: 2025-02-14
confidence: high
---

# RAG 系统设计 Review v2

## 核心理念

Claude Code 就是 Agent。不写框架代码，不引入 LangChain/LlamaIndex。
Skills 定义行为约束，MCP 提供工具，Agent 自主决策调用什么、怎么调用。

## 当前架构

```
用户查询 → Claude Code (Agent)
               │
               ├─ Layer 1: Grep/Glob/Read  → 本地 docs/
               ├─ Layer 2: MCP hybrid_search → Qdrant (BGE-M3 + RRF + Rerank)
               └─ Layer 3: 多文档推理
               │
               ↓
          生成答案 + 引用
```

三层是串行 fallback：先试 Grep，不够再走 Qdrant，复杂查询才做多文档推理。

### 实际代码现状

| 组件 | 文件 | 行数 | 状态 |
|------|------|------|------|
| MCP Server | `scripts/mcp_server.py` | 198 | ✅ hybrid_search + keyword_search + index_status |
| 索引工具 | `scripts/index.py` | 216 | ⚠️ 基础可用，分块粗糙 |
| 检索 Skill | `.claude/skills/search/` | 267 | ✅ 三层策略定义完整 |
| Simple Worker | `scripts/workers/simple_rag_worker.py` | 195 | ✅ 直接调 Anthropic API |
| Agentic Worker | `scripts/workers/rag_worker.py` | 321 | ❌ 未集成，引用不存在的目录 |

### 已验证的数据

| 指标 | 结果 |
|------|------|
| Hybrid vs Dense-only | +36% 准确率 |
| Layer 1 本地文档 (Grep) | 17/17 (100%) |
| Claude "语义 Grep" | 能将模糊症状分解为多关键词 OR 模式 |
| 跨语言 | 英文问→中文文档 ✅，中文问→英文文档 ✅ |
| Qdrant 用例 (无 MCP) | 6/12 通过，但全是通用知识非检索（假阳性）|

## 架构问题分析

### 问题 1: 串行 fallback 是低效的

当前 `/search` skill 指示 Agent 先 Grep，不够再 Qdrant。这是开发者硬编码的流程。

实际上 Claude 本身就能判断查询意图：
- "READONLY You can't write against a read only replica" → 明显是精确关键词，Grep 最快
- "容器跑着跑着就被 kill 了" → 模糊症状，需要语义检索
- "对比 Deployment 和 ReplicationController" → 需要多文档

**应该做的**: 把决策权交给 Agent。Layer 1/2/3 不是上下游，是平级工具箱。Agent 根据查询特征自主选择，甚至并行调用。

这就是 Adaptive-RAG / Self-RAG 论文的核心思路：**Intent-driven Routing**，不是 Pipeline。

### 问题 2: 分块丢失结构（P0）

当前 `index.py` 的分块逻辑：

```python
# 实际代码
paragraphs = post.content.split("\n\n")
# 合并到 3200 字符
```

Qdrant payload 中存了 `path`, `title`, `doc_id`, `chunk_id`, `confidence`, `tags`。
但没有 `section_path`。MCP server 返回时有这个字段，永远是空字符串。

Agent 拿到一个 chunk，不知道它属于文档的哪个章节。引用只能到文件级，不能到章节级。

**极简解法**: 按 Markdown 标题 (`##`, `###`) 切分，把标题路径注入 payload。不需要 NLP 模型，一个正则就够。

```python
# 极简：按标题切分，保留层级路径
chunk_payload = {
    "text": "配置步骤...",
    "path": "docs/runbook/redis-failover.md",
    "section_path": "故障恢复 > 手动恢复 > 确认新 Master",  # 关键
    "chunk_id": "redis-failover-003"
}
```

### 问题 3: 增量索引缺失（P0）

当前只有 `--file` 单文件索引。Git 已经帮你算好了所有 hash 和 diff。

**极简解法**: 不需要在 Python 里维护状态。

```bash
# --full: 全量
git ls-files '*.md' | xargs -I{} python index.py --file {}

# --incremental: 增量（上次索引到现在的变更）
git diff --name-only HEAD@{1} HEAD -- '*.md' | xargs -I{} python index.py --file {}
```

删除旧 chunk：按 `doc_id` 在 Qdrant 中 delete，再 upsert 新的。`index.py` 已有 `delete_doc()` 函数。

### 问题 4: `get_document` 不需要新 MCP 工具

Claude Code 本身就有 Read 工具。chunk payload 里有 `path` 字段。
Agent 看到 chunk 觉得不够，直接 `Read(path)` 读全文即可。

只需要在 `/search` skill 里加一句引导：
> "如果 chunk 上下文不足，用 Read 工具读取 source_file 的完整内容。"

不需要写新代码。

### 问题 5: 评测假阳性

Qdrant 用例在 USE_MCP=0 下"通过"，实际是 Claude 用通用知识回答。

**极简解法**: 测试 prompt 加防幻觉约束：
> "只能使用检索工具返回的内容回答。如果搜索结果不包含答案，回答'未找到相关文档'。"

评估时检查答案是否包含正确的 `chunk_id` 或 `section_path`，没有就判 Failed。

## 目标架构: Agentic Router

```
用户查询 → Claude Code (Agent / Router)
               │
               │  Agent 自主判断意图，选择工具（或并行）
               │
               ├─ Tool A: grep_search     → 精确关键词、报错代码、文件路径
               ├─ Tool B: hybrid_search   → 模糊语义、跨语言、概念理解
               ├─ Tool C: read_file       → 读取完整文档上下文
               └─ Tool D: list_docs       → 小规模 KB 直接全量读取
               │
               ↓
          融合多源结果 → 生成答案 + 引用 (chunk_id + section_path)
```

关键变化：
1. **不是 Layer 1→2→3 串行**，是 Agent 自主路由到最合适的工具
2. **可以并行**: Agent 同时调 grep + hybrid_search，Late Fusion 在 context window 里完成
3. **规模感知**: 如果 KB 只有几个文件（< 50KB），Agent 应直接全量读取，跳过所有检索
4. **控制流在 Agent 手里**，不在 Python 代码里

### 实现方式: 改 Skill，不改代码

这个架构变更的核心不是写新的 Python 代码，而是重写 `/search` skill 的指令。

当前 skill 说："先 Grep，不够再 Qdrant"（硬编码流程）。
新 skill 应该说："这里有 4 个工具，根据查询特征自己选"（Agent 决策）。

工具本身（Grep、MCP hybrid_search、Read）已经全部就绪。
唯一需要写代码的是 `index.py` 的分块改进（加 section_path）。

## 改进计划（极简优先）

### Phase 1: 数据质量（改 index.py，~50 行）

- [ ] 按 Markdown 标题切分，注入 `section_path` 到 payload
- [ ] `--full` 全量重建（遍历 git ls-files）
- [ ] `--incremental` 增量更新（git diff + delete + upsert）
- [ ] 重新索引现有 21 个文档

### Phase 2: Agentic Router（改 skill，0 行代码）

- [ ] 重写 `/search` skill：从串行 fallback 改为 Agent 自主路由
- [ ] 加入规模感知：小 KB 直接全量读取
- [ ] 加入并行提示：允许 Agent 同时调多个工具
- [ ] 加入防幻觉约束：必须基于检索结果回答

### Phase 3: 评测修正

- [ ] USE_MCP=1 完整测试（等限流重置）
- [ ] 评估标准：必须包含 chunk_id 或 section_path 才算通过
- [ ] 对比 Phase 1/2 前后的检索质量

### 不做的事情

- ❌ 不引入 LangChain / LlamaIndex / Unstructured
- ❌ 不写 Python 路由逻辑（Agent 自己路由）
- ❌ 不写 `get_document` MCP 工具（Agent 用 Read 即可）
- ❌ 不训练意图分类模型（Claude 本身就能判断）
- ❌ 不在 Python 里维护索引状态（Git 已经有）

## 代码量预估

| 改动 | 文件 | 预估行数 |
|------|------|----------|
| 标题分块 + section_path | `scripts/index.py` | +40 行 |
| --full / --incremental | `scripts/index.py` | +20 行 |
| Agentic Router skill | `.claude/skills/search/` | 重写 ~200 行 |
| 评测收紧 | `tests/e2e/test_agentic_rag_sdk.py` | +30 行 |

总计: ~90 行新代码 + 1 个 skill 重写。符合极简原则。
