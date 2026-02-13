---
paths:
  - "docs/**/*.md"
---

# 文档 Front-matter 规范

所有 docs/ 下的 Markdown 文档必须包含 YAML front-matter：

```yaml
---
id: "d7f3a2b1"           # 稳定主键（8位短hash/UUID），首次创建时生成，重命名/移动不变
title: "文档标题"
owner: "@负责人"
tags: [分类标签]
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
confidence: high | medium | low | deprecated
---
```

关键规则：
- `id` 是 Qdrant 索引的稳定主键，绝对不能修改或重复
- `confidence` 必填，防止过时内容被当作权威答案
- `last_reviewed` 超过 6 个月的文档应提醒作者更新
- `deprecated` 文档不应作为主要引用来源
- 新导入的文档默认 confidence: medium，经人工审核后调整
