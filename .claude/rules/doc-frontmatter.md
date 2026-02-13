---
paths:
  - "docs/**/*.md"
---

# 文档规范

所有 docs/ 下的 Markdown 文档必须包含 YAML front-matter：

```yaml
---
title: "文档标题"
owner: "@负责人"
tags: [分类标签]
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
confidence: high | medium | low | deprecated
---
```

- confidence 字段必填，防止过时内容被当作权威答案
- last_reviewed 超过 6 个月的文档应提醒作者更新
- deprecated 文档不应作为主要引用来源
