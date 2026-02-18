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

把 PageIndex 的思想作为轻量增强层叠加到现有架构上，而非替换。

---

## 四、落地 Action Items

### Action 1: 章节级 TOC 树 Sidecar（P0 — 最高优先级）

**问题**: 向量检索找不到具体运维指令/配置参数时，Agent 缺乏"目录导航"能力。

**方案**: 在现有 `.preprocess/` 目录中，为每个文档额外生成 `_toc_tree` 字段（或独立 sidecar），内容为 heading 层级树。

**数据结构**:
```json
{
  "doc_id": "abc123",
  "title": "Redis Sentinel 故障恢复",
  "toc_tree": [
    {
      "node_id": "001",
      "title": "故障恢复",
      "section_path": "故障恢复",
      "level": 2,
      "children": [
        {
          "node_id": "001-1",
          "title": "自动故障转移",
          "section_path": "故障恢复 > 自动故障转移",
          "level": 3,
          "summary": "Sentinel 自动检测 master 下线并选举新 master 的流程",
          "has_command": true,
          "children": []
        },
        {
          "node_id": "001-2",
          "title": "手动恢复",
          "section_path": "故障恢复 > 手动恢复",
          "level": 3,
          "summary": "手动介入恢复主从关系的步骤",
          "has_command": true,
          "children": []
        }
      ]
    }
  ]
}
```

**生成方式**: 复用 `index.py` 中已有的 `split_by_headings()` 建树，只差一步。小节点直接用标题当 summary，大节点（>500 tokens）用 DeepSeek 生成一句话 summary。

**Agent 使用方式**: 在 `/search` Skill 中新增指引 —— 当混合检索效果不佳时，Agent 先 `Read` 该领域的 TOC 树，通过阅读目录推理出目标章节，再精确 `Read` 或 `Grep` 那个文件的对应 section。

**成本**: 树结构生成零 LLM 成本（纯解析）；section summary 用 DeepSeek V3 约 ¥0.5/1000 节点。

**实现路径**:
1. `scripts/doc_preprocess.py` 新增 `generate_toc_tree()` 函数
2. 输出到现有 sidecar JSON 的 `toc_tree` 字段
3. `/search` Skill 新增 TOC 导航指引

---

### Action 2: Section 级 Summary 替代 Doc 级 Summary（P0）

**问题**: 当前 `contextual_summary` 是文档级别的，注入 embedding 时"把整篇的主题噪声注入每个 chunk"。

**方案**: 对每个 heading section 生成一句话 summary，替代（或补充）doc-level summary。

**改动点**:
- `scripts/doc_preprocess.py`: 生成 `section_summaries: { "section_path": "一句话summary" }`
- `scripts/index.py`: embedding 输入从 `title + section_path + text + DOC_SUMMARY` 改为 `section_summary + title + text`
- 小节点（<200 tokens）直接用标题当 summary，不调 LLM（PageIndex 的 thinning 思路）

**收益**:
- embedding 更精准，减少文档级噪声
- Agent 拿到搜索结果后可快速判断要不要 `Read` 全文
- 与 Action 1 的 TOC 树共享 summary 数据，一次生成两处使用

---

### Action 3: NodeScore 聚合排序（P1）

**问题**: hybrid_search 返回的 top-K chunks 是扁平的，Agent 不知道哪个章节/文档命中最多。

**方案**: 在 MCP Server 的 hybrid_search 返回结果中，增加按 section_path 的聚合信息。

**算法**（来自 PageIndex 的 Value-based 思路）:
```python
# 把 top-K chunks 按 section_path 归组
groups = defaultdict(list)
for chunk, score in results:
    parent = chunk.payload["section_path"].split(" > ")[0]  # 取顶级 section
    groups[parent].append(score)

# 计算 NodeScore
node_scores = {}
for section, scores in groups.items():
    node_scores[section] = sum(scores) / math.sqrt(len(scores) + 1)

# 在返回结果中附加 node_score 信息
```

**Agent 使用方式**: 优先消费 NodeScore 高的章节，减少无效 Read。

**实现路径**: 仅改 `mcp_server.py` 的返回格式，零侵入，不改索引结构。

---

### Action 4: agent_hint 增加子章节提示（P1）

**问题**: Agent 拿到一个父级标题的 chunk（如 `## Sentinel 故障转移`）但里面没有具体命令，不知道该深入还是放弃。

**方案**: 在 `agent_hint` 中增加子章节信息。

**改动**: 当 chunk 对应的 section 在 TOC 树中有子节点时，agent_hint 追加：
```
[有 3 个子章节: 自动故障转移 / 手动恢复 / 确认新 Master，建议 Read 深入]
```

**依赖**: Action 1 的 TOC 树数据。

---

### Action 5: Evidence/Gap Flags 下沉到章节级（P2）

**问题**: 当前 evidence_flags 和 gap_flags 是文档级别的。一个文档可能某些章节有命令、某些没有，文档级标记粒度太粗。

**方案**: 在 Action 1 的 TOC 树节点上标记 evidence_flags。

**实现**: `generate_toc_tree()` 时对每个 section 的文本跑现有的 regex evidence 检测（零 LLM 成本），写入节点的 `has_command` / `has_config` / `has_code_block` 字段。

**收益**: Agent 在"选章节"阶段就能看到风险信号，不用等到读完 chunk 才发现缺命令。

---

### Action 6: 两段式路由架构确认（P2 — 架构方向）

PageIndex 的启示确认了我们的演进路径：

```
用户查询
  │
  ├─ 第一段：海量筛选（毫秒级）
  │   └─ BGE-M3 + Qdrant hybrid_search → Top 5 相关文档/章节
  │
  └─ 第二段：推理精读（Agent 级）
      ├─ 如果 chunk 充分 → 直接回答
      ├─ 如果 chunk 不足 → 读 TOC 树 → 推理定位 → Read 目标 section
      └─ gap_flags / quality_score 阻断幻觉
```

这不需要引入 PageIndex 的第三方依赖，只要把"让模型看目录再做决定"这个逻辑加进 `/search` Skill 的工作流里。

---

## 五、优先级与依赖关系

```
Action 1 (TOC 树 Sidecar)  ←── Action 4 (子章节提示) 依赖此
    │                            Action 5 (章节级 Flags) 依赖此
    │
Action 2 (Section Summary)  ←── 与 Action 1 共享 summary 数据
    │
Action 3 (NodeScore 聚合)   ←── 独立，可并行开发
    │
Action 6 (两段式路由)       ←── 架构方向，贯穿所有 Action
```

**建议执行顺序**: Action 1 + 2（一起做，共享 summary）→ Action 3（独立）→ Action 4 + 5（依赖 Action 1）

---

## 六、预期收益

| 指标 | 当前 | 预期改善 |
|------|------|---------|
| 精确运维指令检索 | 依赖 Grep 命中关键词 | TOC 导航 + 章节级 evidence 让 Agent 精准定位 |
| Faithfulness | 3.94/5 | 章节级 summary 减少噪声注入，Agent 更精准引用 |
| Agent Read 效率 | 盲目 Read 全文 | NodeScore + TOC 导航减少无效 Read |
| 新增成本 | — | TOC 树生成零成本；section summary ≈ ¥0.5/1000 节点 |

---

## 七、参考资料

- [PageIndex GitHub](https://github.com/VectifyAI/PageIndex)
- [PageIndex Documentation - Hybrid Tree Search](https://docs.pageindex.ai/tutorials/tree-search/hybrid)
- [PageIndex Documentation - LLM Tree Search](https://docs.pageindex.ai/tutorials/tree-search/llm)
- [PageIndex: Document Index for Reasoning-based RAG (YouTube)](https://www.youtube.com/watch?v=M3Dq6WXEoNY)
- Anthropic Contextual Retrieval: section-level summary 的理论基础
