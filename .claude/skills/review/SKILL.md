---
name: review
description: 检查知识库文档的健康度。当用户提到"检查文档"、"知识库健康度"、"文档审查"、"review docs" 时触发。
argument-hint: [--scope runbook|adr|api|postmortem|meeting-notes] [--fix]
allowed-tools: Read, Grep, Glob, Bash
context: fork
agent: general-purpose
---

# 知识库健康度审查

## 检查项

### 严重（必须修复）
- front-matter 缺少 `id` 字段（索引主键缺失）
- docs/ 中存在文档但 Qdrant 中无对应 chunks（索引不一致）
- Qdrant 中存在已删除文档的残留 chunks

### 警告
- front-matter 缺少 title/owner/tags/created/last_reviewed/confidence
- `last_reviewed` 超过 6 个月
- `confidence` 为 deprecated 但仍被其他文档引用
- 同一主题存在多份近似文档（标题相似度 > 0.8）

### 建议
- 空章节、TODO 标记、占位符内容
- 长期从未被检索命中的文档（孤儿文档）
- front-matter tags 为空

## 执行流程

1. 扫描 docs/ 下所有 .md 文件
2. 解析每篇文档的 front-matter
3. 调用 knowledge-base MCP 的 `index_status` 获取索引状态
4. 逐项检查，按严重程度分类
5. 计算健康度评分（0-100）

## 输出格式

```
知识库健康度: 78/100

🔴 严重 (2)
- docs/api/old-spec.md: 缺少 id 字段
- Qdrant 残留: doc_id=a1b2c3d4 对应文件已删除

🟡 警告 (5)
- docs/runbook/redis.md: last_reviewed 2024-06-01，已超过 6 个月
- docs/runbook/redis-v2.md: 与 redis.md 内容高度相似，建议合并
...

🔵 建议 (3)
- docs/adr/001-db-choice.md: tags 为空
...
```

## --fix 模式
如果用户传入 --fix，对可自动修复的问题执行修复：
- 为缺少 id 的文档生成 id
- 删除 Qdrant 中的残留 chunks
- 更新 last_reviewed 为今天（需用户确认）
