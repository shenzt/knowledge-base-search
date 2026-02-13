---
name: search
description: 从知识库检索文档并回答问题。当用户提到"搜索"、"查找"、"查一下"、"有没有相关文档" 时触发。
argument-hint: <查询内容> [--scope runbook|adr|api|postmortem|meeting-notes]
allowed-tools: Read, Grep, Glob, Bash
---

# 知识库检索

## 输入
- $0: 用户查询
- --scope: 限定目录范围（可选）

## 检索策略（两层）

### 第一层：Grep/Glob 快速检索（轻量，无需模型）

适合关键词明确的查询，直接用 Claude Code 内置工具：

1. 用 Grep 在 docs/ 下搜索关键词
2. 用 Glob 按目录/文件名模式匹配
3. 用 Read 读取命中文件的相关段落

如果第一层已经找到高质量答案，直接回答。

### 第二层：向量检索（语义，需要 MCP）

适合模糊/语义化的查询，调用 knowledge-base MCP：

1. 调用 `hybrid_search`，top_k=5, min_score=0.3
2. 对命中结果用 Read 读取完整上下文
3. 归纳回答

### 选择逻辑

- 查询包含明确关键词/术语/错误码 → 先走第一层
- 查询是模糊问题/概念性问题 → 直接走第二层
- 第一层结果不够 → 补充第二层

## 回答要求

- 必须带引用：`[来源: docs/runbook/xxx.md:42]`
- 如果文档 confidence 为 deprecated，标注警告
- 如果 last_reviewed 超过 6 个月，提示可能过时
- 检索不到相关内容时，明确告知用户

## 注意事项
- 不要在没有检索的情况下凭记忆回答知识库问题
- 不要一次性 Read 整个目录的所有文件
