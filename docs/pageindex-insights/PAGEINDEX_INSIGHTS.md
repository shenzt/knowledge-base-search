# PageIndex 调研与落地方案

**日期**: 2025-07-18
**来源**: [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex)
**参与分析**: Kiro, Gemini, ChatGPT
**状态**: 待评审

---

## 一、PageIndex 核心思想

PageIndex 是一个 **Vectorless, Reasoning-based RAG** 系统。一句话概括：

> 放弃向量检索的"语义相似度"，回归人类专家阅读的"目录树推理"。

### 1.1 三个核心机制

| 机制 | 说明 |
|------|------|
| 结构化目录树 | 把文档解析成层级语义树（类似 Table of Contents），每个节点带 title / page_range / summary，而非扁平 chunk |
| LLM 主动寻路 | 检索时不算余弦相似度，而是把目录大纲丢给 LLM 做逻辑推理："这个问题属于哪个章节？" 自上而下遍历树定位目标段落 |
| 自然上下文对齐 | 没有暴力 chunking，提取内容遵循原始章节边界，天生自带完整上下文 |

### 1.2 混合树搜索（Value-based）

PageIndex 文档中给出了一个可落地的混合思路：

- 用 embedding 对节点内部的子 chunk 做向量检索，把命中的 chunk 归到父节点
- 用聚合公式算 NodeScore（`sum(chunk_scores) / sqrt(N+1)`，奖励多命中但递减）
- 与 LLM tree search 并行产出候选节点

### 1.3 Tree Thinning

节点太小就并到父节点；节点太长才做 summary，否则直接用原文当 summary。与我们"极简 + 低成本预处理"的理念高度契合。

---

## 二、PageIndex 的局限性

### 扩展性瓶颈（致命）

- 当知识库达到数百上千个文档时，让 LLM 每次遍历成百上千棵树的目录极度缓慢且昂贵
- 多文档检索场景下，速度和成本远不如 Hybrid Vector Search
- 核心优势场景：**单/少量长文档深度理解**（如财务报表、合规文件），FinanceBench 98.7% 准确率

### 不适合我们的部分

| 不建议引入 | 原因 |
|-----------|------|
| 去掉向量搜索改纯 LLM 推理 | 我们有 462 文档 2267 chunks，纯推理遍历成本太高、延迟太大 |
| 把整棵树塞进 context | 对单文档可行，对多文档知识库会爆 context |
| 依赖 OpenAI 做索引构建 | 我们用 BGE-M3 本地模型在成本和隐私上更优 |

---

## 三、核心结论

PageIndex 证明了"结构化推理"在解决复杂查询时碾压"向量相似度"。但我们不需要也不应该抛弃 Qdrant。正确的做法是：

> **海量筛选用向量（毫秒级），精准定位用树推理（Agent 级）。**

### 进一步抽象：树是图的特例，但我们需要的不是数据结构

树/图只是"地图"的形态。PageIndex 的本质是：**给 Agent 一张地图，让它先看地图再决定去哪里找东西。** 关键不是树遍历算法，而是"导航 → 定位 → 精读"这个行为模式。

我们已经有了所有的"地图原料"：

| 已有的东西 | 本质上是什么 |
|-----------|------------|
| `section_path` (heading 层级) | 文档内部的导航路径 |
| `contextual_summary` | 节点的摘要描述 |
| `evidence_flags` / `gap_flags` | 节点的质量标注 |
| front-matter `tags` / `doc_type` | 文档间的分类关系 |

PageIndex 花了大量代码去建树、遍历树。但我们的 Agent 本身就是推理引擎 — 不需要写代码实现树遍历，Agent 看到结构化信息自己就会推理。

---

## 四、落地方案：一个 INDEX.md 搞定

### 核心思路

不建树，不建图，不写新 Python 代码。只给 Agent 一份足够好的"索引摘要" — 一个人类可读的 Markdown 文件。

对每个 repo（数据源）生成一个 `INDEX.md`，Agent 用 `Read` 读它，自己推理该去看哪个文档的哪个章节，然后 `Read` 或 `Grep` 精确定位。

### INDEX.md 格式示例

```markdown
# Redis Docs 索引

## sentinel.md — Redis Sentinel 高可用方案
- 概述: Sentinel 架构、自动故障转移、配置指南
- 章节: 工作原理 / 部署配置 / 故障转移流程 / 客户端配置 / 常见问题
- 标记: has_command, has_config

## replication.md — Redis 主从复制
- 概述: 主从复制机制、配置、故障处理
- 章节: 复制原理 / 配置步骤 / 部分重同步 / 无盘复制
- 标记: has_command, has_config, missing_example

## persistence.md — Redis 持久化
- 概述: RDB 快照与 AOF 日志两种持久化方式
- 章节: RDB 配置 / AOF 配置 / 混合持久化 / 备份策略
- 标记: has_command, has_config, has_code_block
```

每个条目包含：
- 文件名 + 一句话概述（来自现有 `contextual_summary`）
- 章节列表（来自现有 `section_path`，即 heading 结构）
- evidence 标记（来自现有 `evidence_flags`）

### 为什么这样做

| 对比 | PageIndex 方式 | INDEX.md 方式 |
|------|---------------|--------------|
| 数据结构 | JSON 树 + node_id + page_range | 纯 Markdown，无新格式 |
| 遍历逻辑 | 代码实现 tree search | Agent 自己推理 |
| 生成方式 | Python 脚本解析 + LLM summary | `/preprocess` Skill 里 Agent 自己生成，或简单脚本聚合已有 sidecar |
| 新增代码 | 需要 tree builder + tree searcher | 零新代码，或极少量聚合脚本 |
| 维护成本 | 树结构变更需同步 | Markdown 文件，git 管理 |

### 实现路径

1. 在 `/preprocess` Skill 中新增一步：聚合该 repo 下所有 sidecar JSON，生成 `INDEX.md`
   - 数据全部来自已有的 sidecar（`contextual_summary` + `evidence_flags`）和 `index.py` 的 heading 解析
   - 可以用 Agent 直接生成（Read sidecar → Write INDEX.md），也可以写一个 20 行的聚合脚本
2. 在 `/search` Skill 中新增指引：当 hybrid_search 结果不充分时，Agent 先 `Read` 对应 repo 的 `INDEX.md`，推理定位目标文档和章节，再精确检索

### 与现有架构的融合

```
用户查询
  │
  ├─ Layer 1: Grep/Glob/Read（精确关键词，零成本）
  ├─ Layer 2: hybrid_search（语义检��，毫秒级）
  │
  │  ── 如果 chunk 充分 → 直接回答
  │
  └─ Layer 3: Read INDEX.md → 推理定位 → Read 目标 section（导航精读）
       └─ 仅在 Layer 1+2 不充分时触发
```

这完全符合"Claude Code IS the Agent"的哲学 — 导航逻辑在 Agent 脑子里，不在代码里。

### 预期收益

| 指标 | 当前 | 预期改善 |
|------|------|---------|
| 精确运维指令检索 | 依赖 Grep 命中关键词 | INDEX.md 导航让 Agent 知道该去哪个文件找 |
| Agent Read 效率 | 盲目 Read 全文 | 先看索引再定向 Read，减少无效读取 |
| 新增代码量 | — | 0 行（Agent 生成）或 ~20 行（聚合脚本） |
| 新增成本 | — | 零（纯聚合已有数据） |

### 后续可选增强（不急）

如果 INDEX.md 方案验证有效，后续可以按需叠加：
- section 级 summary（大章节用 LLM 生成一句话摘要，小章节用标题）
- NodeScore 聚合（hybrid_search 结果按 section_path 归组打分，在 `mcp_server.py` 中实现）
- agent_hint 子章节提示（chunk 有子章节时提示 Agent 深入）

但这些都是锦上添花，INDEX.md 是最小可行方案。

---

## 五、参考资料

- [PageIndex GitHub](https://github.com/VectifyAI/PageIndex)
- [PageIndex Documentation - Hybrid Tree Search](https://docs.pageindex.ai/tutorials/tree-search/hybrid)
- [PageIndex Documentation - LLM Tree Search](https://docs.pageindex.ai/tutorials/tree-search/llm)
- [PageIndex: Document Index for Reasoning-based RAG (YouTube)](https://www.youtube.com/watch?v=M3Dq6WXEoNY)
- Anthropic Contextual Retrieval: section-level summary 的理论基础
