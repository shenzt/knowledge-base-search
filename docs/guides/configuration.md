# API 配置说明

## 设置方法

### 方法 1: 使用 .env 文件 (推荐)

1. 复制示例文件:
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的实际凭证:
```bash
ANTHROPIC_BASE_URL=https://claude-code.club/api
ANTHROPIC_AUTH_TOKEN=your_token_here
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
WORKER_MODEL=claude-sonnet-4-20250514
```

3. `.env` 文件已加入 `.gitignore`，不会被提交到 Git

### 方法 2: 使用环境变量

```bash
export ANTHROPIC_BASE_URL="https://claude-code.club/api"
export ANTHROPIC_AUTH_TOKEN="your_token_here"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export WORKER_MODEL="claude-sonnet-4-20250514"
```

## 运行测试

所有测试脚本会自动从 `.env` 文件加载配置:

```bash
# Simple E2E 测试 (推荐)
python test_simple_e2e.py

# 快速 E2E 测试
python test_quick_e2e.py

# 完整 E2E 测试
python test_e2e.py

# 直接 MCP Server 测试 (不需要 API Key)
python test_direct_mcp.py
```

## 安全提示

- ⚠️ **永远不要**将 `.env` 文件提交到 Git
- ⚠️ **永远不要**在代码中硬编码 API Key
- ⚠️ **永远不要**在公开的文档或日志中暴露 API Key
- ✅ 使用 `.env.example` 作为模板，不包含实际凭证
- ✅ `.env` 已加入 `.gitignore`

## 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| ANTHROPIC_BASE_URL | API 基础 URL | https://api.anthropic.com |
| ANTHROPIC_AUTH_TOKEN | API 认证 Token | 必填 |
| CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC | 禁用非必要流量 | 1 |
| WORKER_MODEL | Worker 使用的模型 | claude-sonnet-4-20250514 |
| QDRANT_URL | Qdrant 服务地址 | http://localhost:6333 |
| COLLECTION_NAME | Qdrant Collection 名称 | knowledge-base |
| BGE_M3_MODEL | BGE-M3 模型路径 | BAAI/bge-m3 |
| RERANKER_MODEL | Reranker 模型路径 | BAAI/bge-reranker-v2-m3 |
