---
name: review
description: 检查知识库文档健康度。当用户提到"检查文档"、"文档审查"、"review" 时触发。
argument-hint: [--scope runbook|adr|api|postmortem|meeting-notes] [--fix]
allowed-tools: Read, Grep, Glob, Bash, Write
context: fork
agent: general-purpose
---

# 知识库文档审查

扫描 docs/ 下所有 Markdown 文档，检查质量和时效性。

## 检查项

1. 用 Glob 找到 docs/**/*.md 所有文档
2. 用 Read 逐个读取 front-matter，检查：
   - 缺少 id 字段 → 🔴 严重
   - 缺少 title/owner/confidence → 🟡 警告
   - last_reviewed 超过 6 个月 → 🟡 警告
   - confidence 为 deprecated → 🔵 提示
   - tags 为空 → 🔵 建议
3. 用 Grep 检查内容质量：
   - 搜索 `TODO`、`FIXME`、`TBD` → 🟡 警告
   - 空章节（标题后无内容） → 🔵 建议

## 输出格式

```
知识库健康度: XX/100

🔴 严重 (N)
- docs/xxx.md: 缺少 id 字段

🟡 警告 (N)
- docs/yyy.md: last_reviewed 2024-06-01，已超 6 个月
- docs/zzz.md: 包含 TODO 标记 (L23)

🔵 建议 (N)
- docs/aaa.md: tags 为空
```

## --fix 模式
如果用户传入 --fix：
- 为缺少 id 的文档生成 id（用 python -c 生成 8 位 hash）
- 用 Write 工具写入修复后的 front-matter
- 修复后 git commit
