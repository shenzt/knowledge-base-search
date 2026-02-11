# 知识库检索规约

## 可用 MCP 工具
- hybrid_search: 混合检索（语义 + 关键词 + 重排序），首选
- keyword_search: 纯关键词检索，适合精确术语匹配
- get_document: 按路径取完整文档
- list_collections: 列出可用知识库
- index_status: 查看索引状态

## 检索策略
当用户问题涉及 docs/ 下的文档时：
1. 优先使用 hybrid_search，不要先用 Read/Glob/Grep 扫描全仓库
2. 默认 top_k=5, min_score=0.3
3. 可通过 scope 参数限定目录：runbook / adr / api / postmortem / meeting-notes
4. 如果 hybrid_search 无结果，降级为 keyword_search 扩大召回
5. 用 get_document 拉取完整文档上下文

## 输出要求
- 回答必须带引用：[来源: docs/runbook/xxx.md, chunk #2]
- 如果文档 confidence 为 low 或 deprecated，必须提醒用户
- 如果 last_reviewed 超过 6 个月，提示"此文档可能需要更新"

## 得分解读
- 0.8–1.0: 高度相关，可直接引用
- 0.5–0.8: 中度相关，需结合上下文判断
- 0.3–0.5: 弱相关，仅作参考
- < 0.3: 已被过滤

## 禁止行为
- 不要在没有检索的情况下凭记忆回答知识库相关问题
- 不要一次性读取整个目录的所有文件
- 不要自动执行索引更新命令（update / embed）
