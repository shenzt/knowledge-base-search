# knowledge-base-search

基于 Git + Qdrant + BGE-M3 + Claude Code 的中文知识库检索系统。

## 项目结构

- `docs/` — 知识库文档（Markdown），按 runbook/adr/api/postmortem/meeting-notes 分类
- `scripts/` — 索引构建、MCP Server 等 Python 脚本
- `.claude/` — Claude Code 配置（rules、skills、agents）

## 技术栈

- Qdrant（本地 Docker 或嵌入式）
- BGE-M3 embedding + learned sparse vectors
- BGE-Reranker-v2-M3
- MCP 协议接入 Claude Code

## 常用命令

```bash
# 启动 Qdrant
docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# 构建索引
python scripts/index.py

# 增量更新（仅变更文件）
python scripts/index.py --incremental

# 启动 MCP Server（通常由 Claude Code 自动管理）
python scripts/mcp_server.py
```

## 文档

详细设计文档见 [docs/design.md](docs/design.md)。
