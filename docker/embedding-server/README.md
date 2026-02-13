# Embedding MCP Server

独立的 Embedding 服务，提供常驻的向量编码和重排序能力。

## 为什么需要独立服务？

**问题**:
- BGE-M3 模型加载需要 2-3 分钟
- 每次查询都重新加载模型，效率低下
- 无法复用模型实例

**解决方案**:
- 将 embedding 服务独立为常驻 MCP Server
- 模型加载一次，持续服务
- 支持批量编码，提升效率
- 可部署到远程 GPU 服务器

## 架构

```
┌─────────────────┐
│  Claude Code    │
│  (Agentic RAG)  │
└────────┬────────┘
         │
         ├──────────────────┬──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Qdrant MCP      │  │ Embedding    │  │ Other MCP        │
│ (search)        │  │ MCP Server   │  │ Servers          │
└────────┬────────┘  └──────┬───────┘  └──────────────────┘
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌──────────────────┐
│   Qdrant DB     │  │   BGE-M3 Model   │
│   (vectors)     │  │   (常驻内存)      │
└─────────────────┘  └──────────────────┘
```

## 提供的工具

### 1. encode_query
编码查询文本为 dense + sparse 向量

```python
{
    "text": "What is a Pod in Kubernetes?"
}
→
{
    "dense": [0.123, -0.456, ...],  # 1024d
    "sparse": {"123": 0.89, "456": 0.67, ...}
}
```

### 2. encode_documents
批量编码文档

```python
{
    "texts": ["doc1", "doc2", ...],
    "batch_size": 32
}
→
[
    {"dense": [...], "sparse": {...}},
    {"dense": [...], "sparse": {...}},
    ...
]
```

### 3. rerank
重排序文档

```python
{
    "query": "What is a Pod?",
    "documents": [
        {"text": "doc1", ...},
        {"text": "doc2", ...}
    ],
    "top_k": 10
}
→
[
    {"text": "doc2", "rerank_score": 0.95, ...},
    {"text": "doc1", "rerank_score": 0.87, ...}
]
```

## 快速开始

### 1. 构建并启动服务

```bash
# 启动所有服务（Qdrant + Embedding Server）
docker compose up -d

# 查看日志
docker compose logs -f embedding-server

# 等待模型加载完成（约 2-3 分钟）
# 看到 "✅ 服务就绪，等待请求..." 表示启动成功
```

### 2. 配置 MCP

更新 `.mcp.json`:

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "python",
      "args": ["scripts/mcp_server.py"]
    },
    "embedding": {
      "command": "python",
      "args": ["docker/embedding-server/embedding_mcp_server.py"]
    }
  }
}
```

### 3. 使用服务

在 Claude Code 中：

```python
# 编码查询
result = await mcp.call_tool("embedding", "encode_query", {
    "text": "What is a Pod?"
})

# 批量编码文档
result = await mcp.call_tool("embedding", "encode_documents", {
    "texts": ["doc1", "doc2", "doc3"],
    "batch_size": 32
})

# 重排序
result = await mcp.call_tool("embedding", "rerank", {
    "query": "What is a Pod?",
    "documents": search_results,
    "top_k": 10
})
```

## 性能对比

| 场景 | 之前 | 现在 | 提升 |
|------|------|------|------|
| 首次查询 | 2-3 分钟 | 2-3 分钟 | - |
| 后续查询 | 2-3 分钟 | < 1 秒 | **180x** |
| 批量编码 100 文档 | 不支持 | ~5 秒 | **新功能** |

## 部署选项

### 本地 CPU
```bash
docker compose up -d
```

### 本地 GPU
```yaml
# docker-compose.yml
embedding-server:
  environment:
    - CUDA_VISIBLE_DEVICES=0
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### 远程 GPU 服务器
```bash
# 在远程服务器上启动
docker compose up -d embedding-server

# 本地配置指向远程服务
# .mcp.json
{
  "embedding": {
    "command": "python",
    "args": ["scripts/remote_embedding_client.py"],
    "env": {
      "EMBEDDING_SERVER_URL": "http://gpu-server:8000"
    }
  }
}
```

## 监控

### 健康检查
```bash
curl http://localhost:8000/health
```

### 查看日志
```bash
docker compose logs -f embedding-server
```

### 资源使用
```bash
docker stats embedding-server
```

## 故障排查

### 服务启动慢
- 首次启动需要下载模型（~2GB）
- 模型加载需要 2-3 分钟
- 查看日志确认进度

### 内存不足
- BGE-M3 需要约 4GB 内存
- 如果内存不足，考虑使用 GPU
- 或者使用更小的模型

### GPU 不可用
- 检查 CUDA 安装
- 检查 nvidia-docker 配置
- 查看 docker compose 日志

## 下一步

1. ✅ 启动 Embedding Server
2. 更新 `scripts/index.py` 使用 embedding MCP
3. 更新 `scripts/mcp_server.py` 使用 embedding MCP
4. 测试性能提升
5. 部署到远程 GPU 服务器（可选）
