# knowledge-base-search

## 环境
- Python 3.10+, 依赖见 @scripts/requirements.txt
- Qdrant: `make bootstrap` 一键启动，或 `docker compose up -d`
- 所有检索组件纯本地，仅 Claude Code 调用 Anthropic API 需联网
- 重算力组件（MinerU/Reranker）可部署到局域网 GPU 服务器，通过 MCP HTTP transport 调用

## 工作流
- 导入文档: `/ingest <文件路径或URL>`
- 检索问答: `/search <问题>`
- 文档审查: `/review`
- 索引管理: `/index-docs --incremental` 或 `/index-docs --status`
- 不要自动执行索引命令，必须由用户手动触发或通过 skill 编排

## 文档语言
- 知识库文档以中文为主，部分 API 文档为英文
- 回答和交互使用中文

## 关键约定
- 每篇文档 front-matter 必须有稳定 `id` 字段，作为索引主键
- 索引变更记录在 .index_manifest.jsonl（进 Git）
- 回答必须带完整引用链（path + section + line + score + commit）
