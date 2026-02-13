# knowledge-base-search

## 环境
- Python 3.10+, 依赖见 @scripts/requirements.txt
- Qdrant: `make bootstrap` 或 `docker compose up -d`
- 纯本地方案，仅 Claude Code 调用 Anthropic API 需联网

## 核心理念
- Claude Code 就是 agent，能做的事情就让它做，不写多余代码
- Skills 定义行为，Claude Code 用内置工具（Read/Grep/Glob/Bash/Write）执行
- 唯一的代码是 MCP Server（向量检索需要常驻模型）和 index.py（向量编码写入）
- Git 管理文档版本，Qdrant 存可再生索引

## 工作流
- `/ingest <文件或URL>` — 导入文档（Claude Code 调 CLI 转换 + 整理 + git commit）
- `/search <问题>` — 检索（先 Grep 快速查，不够再走向量检索 MCP）
- `/index-docs` — 索引管理（调 index.py）
- `/review` — 文档审查（Claude Code 用 Read/Grep 直接检查）

## 文档语言
- 知识库以中文为主，回答使用中文

## 关键约定
- 每篇文档 front-matter 必须有 `id` 字段（稳定索引主键）
- 不要自动执行索引命令，必须由用户触发
