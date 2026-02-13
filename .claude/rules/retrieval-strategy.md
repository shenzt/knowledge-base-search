---
paths:
  - "docs/**/*.md"
---

# 检索策略

## 检索通道优先级

默认走 dense + sparse 混合检索（主力），full-text 仅作 fallback/过滤/高亮：

1. 优先使用 MCP 工具 `hybrid_search`（dense + sparse + RRF + rerank）
2. 不要用 Read/Glob/Grep 扫描全仓库来回答知识库问题
3. 默认 top_k=5, min_score=0.3
4. 可通过 scope 参数限定目录：runbook / adr / api / postmortem / meeting-notes
5. 如果 hybrid_search 无结果，降级为 `keyword_search`（Qdrant full-text）扩大召回
6. 用 `get_document` 拉取完整文档上下文

## 引用要求

回答必须带完整引用链：
- 路径 + section_path（定位到章节）
- source_line_range（定位到行号）
- score（rerank 后得分）
- kb_commit（可追溯到索引构建时的文档版本）

格式：`[docs/runbook/xxx.md > 章节名, L42-78, score: 0.89, commit: ff41edc]`

## 文档质量提醒

- confidence 为 low/deprecated → 标注警告
- last_reviewed 超过 6 个月 → 提示"此文档可能需要更新"

## 得分解读

- 0.8–1.0: 高度相关，可直接引用
- 0.5–0.8: 中度相关，需结合上下文判断
- 0.3–0.5: 弱相关，仅作参考
- < 0.3: 已被过滤

## 禁止行为

- 不要在没有检索的情况下凭记忆回答知识库相关问题
- 不要一次性读取整个目录的所有文件
- 不要自动执行索引更新命令
