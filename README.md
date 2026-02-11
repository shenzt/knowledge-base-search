# knowledge-base-search

基于 Git + Qdrant + BGE-M3 + Claude Code Agent 的中文知识库检索系统。

## 架构

- **数据层**: Git 仓库管理 Markdown 文档
- **存储层**: Qdrant 向量数据库（本地 Docker 或嵌入式）
- **检索层**: 自建 MCP Server（BGE-M3 混合检索 + BGE-Reranker 重排序）
- **编排层**: Claude Code Agent 通过 MCP 协议调用检索工具

## 快速开始

```bash
# 1. 安装 Python 依赖
pip install -r scripts/requirements.txt

# 2. 启动 Qdrant
docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# 3. 构建索引
python scripts/index.py

# 4. 启动 MCP Server（由 Claude Code 自动管理，或手动测试）
python scripts/mcp_server.py
```

## 文档

详细设计文档见 [docs/design.md](docs/design.md)。

## 纯本地方案

所有检索组件（Qdrant、BGE-M3、Reranker）均在本地运行。仅首次需联网下载模型和 Docker 镜像，之后检索管线完全离线。Claude Code 调用 Anthropic API 是唯一持续联网的部分。
