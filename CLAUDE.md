# knowledge-base-search

基于 Git + Qdrant + Claude Code 的 Agentic RAG 本地知识库检索系统。

## 核心理念

Claude Code 就是 agent。能用 agent 做的事情就让它做，不写多余代码。

- Skills 定义行为，Claude Code 用内置工具（Read/Grep/Glob/Bash/Write）执行
- 唯一的自建代码：MCP Server（向量检索需要常驻 BGE-M3 模型）+ index.py（向量编码写入）
- Git 管理文档版本，Qdrant 存可再生索引（不进 Git）
- 中英文并重，支持跨语言检索

## 环境

- Python 3.10+，venv 在 `.venv/`，依赖见 @scripts/requirements.txt
- Qdrant: `docker compose up -d`（端口 6333）
- 纯本地方案，仅 Claude Code 调用 Anthropic API 需联网

## 工作流

- `/search <问题>` — 检索（先 Grep 快速查，不够再走向量检索 MCP）
- `/ingest <文件或URL>` — 导入文档（Claude Code 调 CLI 转换 + 整理 + git commit）
- `/index-docs [--status|--file|--full]` — 索引管理（调 index.py）
- `/review [--scope xxx] [--fix]` — 文档审查（Claude Code 用 Read/Grep 直接检查）

## 关键约定

- 每篇文档 front-matter 必须有 `id` 字段（稳定索引主键，不可修改）
- 不要自动执行索引命令，必须由用户触发
- 回答知识库问题必须先检索，不要凭记忆回答
- 文档语言：中英文均支持，回答跟随文档语言

## 常用命令

```bash
docker compose up -d                              # 启动 Qdrant
.venv/bin/python scripts/index.py --status        # 查看索引状态
.venv/bin/python scripts/index.py --file <path>   # 索引单个文件
.venv/bin/python scripts/mcp_server.py            # 启动 MCP Server
```

## 设计文档

详见 @docs/design.md
