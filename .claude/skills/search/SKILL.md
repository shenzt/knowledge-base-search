---
name: search
description: 从知识库检索文档并生成带引用的回答。当用户提到"搜索文档"、"查找知识库"、"查一下 runbook"、"有没有相关的 ADR"、"search docs" 时自动触发。
argument-hint: [查询内容] [--scope runbook|adr|api|postmortem|meeting-notes]
allowed-tools: Read, Grep, Glob
---

# 知识库检索

## 输入
- $0: 用户查询（必填）
- --scope: 检索范围，可选值 runbook | adr | api | postmortem | meeting-notes

## 执行流程

1. 调用 MCP 工具 `hybrid_search`，传入查询和 scope
   - top_k=5, min_score=0.3
2. 如果 hybrid_search 返回空或得分均 < 0.3，降级调用 `keyword_search`
3. 对每个命中结果，调用 `get_document` 拉取完整段落上下文
4. 检查每篇文档的 front-matter：
   - confidence 为 low/deprecated → 标注警告
   - last_reviewed 超过 6 个月 → 提示可能过时
5. 归纳回答，附带引用

## 输出格式

```
[回答内容]

---
引用:
- [来源: docs/runbook/xxx.md, chunk #2, score: 0.85]
- [来源: docs/adr/yyy.md, chunk #1, score: 0.72]

⚠️ 文档提醒:
- docs/runbook/xxx.md 最后审核于 2024-01-15，可能需要更新
```

## 注意事项
- 不要在没有检索的情况下凭记忆回答
- 不要一次性读取整个目录
- 如果检索结果不足以回答问题，明确告知用户并建议补充文档
