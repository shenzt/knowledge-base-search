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

## 测试与验证

**重要**: 代码变更后必须验证功能正常

### 快速验证
```bash
make verify          # 检查环境配置
make status          # 检查索引状态
make test-e2e        # 运行端到端测试
```

### 完整测试
```bash
make test            # 运行所有测试
make test-unit       # 单元测试
make test-integration # 集成测试
make test-e2e        # E2E 测试
```

### 手动验证
```bash
# 1. 确认 Qdrant 运行
docker compose ps

# 2. 检查索引状态
.venv/bin/python scripts/index.py --status

# 3. 测试检索
.venv/bin/python scripts/workers/simple_rag_worker.py "What is a Pod?"
```

## 常用命令

```bash
make help            # 显示所有可用命令
make setup           # 初始化环境
make start           # 启动 Qdrant
make stop            # 停止 Qdrant
make status          # 查看索引状态
make index           # 索引示例文档
make test            # 运行测试
make clean           # 清理缓存
```

## 关键约定

- 每篇文档 front-matter 必须有 `id` 字段（稳定索引主键，不可修改）
- 不要自动执行索引命令，必须由用户触发
- 回答知识库问题必须先检索，不要凭记忆回答
- 文档语言：中英文均支持，回答跟随文档语言
- **代码变更后必须运行测试验证**
- **编写测试用例前，必须先确认知识库中实际有哪些文档**（见 .claude/rules/testing-lessons.md）
- **区分数据源**：本地 docs/ 只有 3 个技术文档，Qdrant 索引有 21 个文档（K8s + Redis）

## 知识库数据源

### Qdrant 索引（SSOT，152 chunks）
- K8s 英文文档 (11 个): Pod, Service, Ingress, Deployment, ReplicationController, Init Containers, Sidecar Containers, Ephemeral Containers, Pod Lifecycle, Pod QoS, Volumes
- Redis 中文文档 (10 个): pipelining, benchmarks, clients, commands, community, documentation, download, index, support, buzz
- 来源: `~/ws/kb-test-k8s-en/` + `~/ws/kb-test-redis-cn/`
- 查看: `.venv/bin/python scripts/index.py --status`

### 本地 docs/（项目文档 + 示例 runbook）
- `runbook/redis-failover.md` — Redis Sentinel 主从切换故障恢复
- `runbook/kubernetes-pod-crashloop.md` — K8s CrashLoopBackOff 排查
- `api/authentication.md` — OAuth 2.0 + JWT API 认证设计
- 其余为项目自身的设计/进展文档，不是知识库内容

## 项目结构

```
knowledge-base-search/
├── .claude/
│   ├── skills/              # 所有 Skills（用户 + Meta）
│   └── rules/               # 路径规则
├── docs/                    # 知识库文档
│   ├── design.md
│   ├── guides/              # 用户指南
│   ├── api/
│   └── runbook/
├── specs/                   # 规格说明（spec-kit 风格）
│   ├── 001-hybrid-search/
│   ├── 002-rag-worker/
│   └── 003-agentic-improvements/
├── scripts/
│   ├── mcp_server.py        # MCP Server
│   ├── index.py             # 索引工具
│   ├── workers/             # Worker 脚本
│   └── requirements.txt
├── tests/
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   ├── e2e/                 # 端到端测试
│   └── conftest.py          # Pytest 配置
├── eval/                    # 评测结果
├── raw/                     # 原始文档
├── .env                     # 本地配置（不提交）
├── .env.example             # 配置模板
├── CLAUDE.md                # 本文件
├── README.md                # 项目说明
├── Makefile                 # 快捷命令
└── pyproject.toml           # Python 项目元数据
```

## 常见问题

### Qdrant 未运行
```bash
make start
# 或
docker compose up -d
```

### 索引为空
```bash
make index  # 索引示例文档
# 或
.venv/bin/python scripts/index.py --file docs/path/to/file.md
```

### 测试失败
1. 检查 Qdrant 是否运行: `docker compose ps`
2. 检查 .env 文件是否存在: `ls -la .env`
3. 检查索引状态: `make status`
4. 重新索引: `make index`

### 首次运行慢
首次运行会下载 BGE-M3 模型（~2-3 分钟），后续运行会使用缓存。

## 设计文档

详见 @docs/design.md
