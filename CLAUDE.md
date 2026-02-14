# knowledge-base-search

基于 Git + Qdrant + Claude Code 的 Agentic RAG 本地知识库检索系统。

## 设计理念

**Claude Code 就是 Agent。** 不写框架代码，不引入 LangChain/LlamaIndex。

- Skills 定义行为约束，MCP 提供工具，Agent 自主决策调用什么、怎么调用
- 唯一的自建代码：MCP Server（向量检索需常驻 BGE-M3）+ index.py（向量编码写入）
- Git 管理文档版本，Qdrant 存可再生索引（不进 Git）
- 控制流在 Agent 手里，不在 Python 代码里

### Agentic Router 架构

```
用户查询 → Agent (Router) 自主判断意图，选择工具（可并行）
              │
              ├─ Grep/Glob/Read  → 精确关键词、报错代码、文件路径（零成本）
              ├─ MCP hybrid_search → 模糊语义、跨语言、概念理解（Qdrant）
              ├─ Read             → 读取完整文档上下文（chunk 不够时）
              └─ Glob + Read     → 小规模 KB 直接全量读取（< 50KB 时跳过检索）
              │
              ↓
         融合多源结果 → 生成答案 + 引用 (section_path + 行号)
```

关键：这不是串行 fallback，是 Agent 根据查询特征自主路由。可以并行调多个工具，Late Fusion 在 context window 里完成。

### 防幻觉约束

- 必须基于检索结果回答，不能凭通用知识
- 答案必须包含引用（文件路径 + section_path 或行号）
- 如果检索结果不包含答案，明确回答"未找到相关文档"
- 区分"基于文档回答"和"基于通用知识回答"

## 环境

- Python 3.10+，venv 在 `.venv/`，依赖见 `scripts/requirements.txt`
- Qdrant: `docker compose up -d`（端口 6333）
- 纯本地方案，仅 Claude Code 调用 Anthropic API 需联网

## 工作流

- `/search <问题>` — 检索（Agent 自主选择 Grep / hybrid_search / 全量读取）
- `/ingest <文件或URL>` — 导入单个文档（Claude Code 调 CLI 转换 + 整理 + git commit）
- `/ingest-repo <repo-url> [--target-dir <path>]` — 导入 Git 仓库（clone → 提取 md → 注入 front-matter → 索引 → git commit 到外部 KB 目录）
- `/index-docs [--status|--file|--full|--incremental]` — 索引管理（调 index.py）
- `/review [--scope xxx] [--fix]` — 文档审查（Claude Code 用 Read/Grep 直接检查）

## 架构规范

详见 `.claude/rules/agent-architecture.md`。核心原则：
- Agent 是唯一入口，不写面向人类的 CLI 工具
- Skill = 工作流编排（Agent 用内置工具执行）
- Python 脚本 = 只做 Agent 做不了的事（向量编码、常驻模型）
- Subagent = 需要隔离 context 的智能任务（如未来 PDF 转换）

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

## 测试与验证

代码变更后必须验证功能正常。

```bash
make verify          # 检查环境配置
make test-e2e        # E2E 测试
make test            # 全部测试
```

## 关键约定

- 每篇文档 front-matter 必须有 `id` 字段（稳定索引主键，不可修改）
- 不要自动执行索引命令，必须由用户触发
- 回答知识库问题必须先检索，不要凭记忆回答
- 文档语言：中英文均支持，回答跟随文档语言
- 代码变更后必须运行测试验证
- 编写测试用例前，必须先确认知识库中实际有哪些文档
- 区分数据源：本地 docs/ 只有 3 个技术文档，Qdrant 索引有 ~206 个文档（K8s + Redis）

## 知识库数据源

### Qdrant 索引（全量，heading-based chunking + section_path）
- K8s 英文文档 (~144 个): kubernetes/website concepts section
  - Workloads: Pod, Deployment, ReplicationController, Init/Sidecar/Ephemeral Containers
  - Networking: Service, Ingress
  - Storage: Volumes
  - Configuration: ConfigMap, Secret, Probes, Resource Management
  - Architecture: Nodes, Controllers, GC, Leases
  - Policy: LimitRange, ResourceQuota
  - Scheduling: Taints/Tolerations, Node Affinity, Pod Priority
  - Security: RBAC, Pod Security, Service Accounts
  - Overview: Components, API, Labels, Annotations, Namespaces, Finalizers
- Redis 英文文档 (~62 个): redis/docs official
  - Data Types: Strings, Lists, Sets, Sorted Sets, Hashes, Streams, JSON, Probabilistic, TimeSeries, Vector Sets
  - Management: Sentinel, Replication, Persistence, Scaling (Cluster), Config, Admin, Debugging, Troubleshooting
  - Security: ACL, Encryption
  - Optimization: Benchmarks, Latency, Memory, CPU Profiling
  - Develop: Pipelining, Transactions, Pub/Sub, Keyspace, Lua Scripting
- 来源: git submodules in `tests/fixtures/kb-sources/`
  - `k8s-website/` → kubernetes/website
  - `redis-docs/` → redis/docs
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
│   ├── skills/              # Skills（Agent 行为约束）
│   └── rules/               # 路径规则 + 经验教训
├── docs/                    # 知识库文档
│   ├── design.md            # 系统设计
│   ├── design-review.md     # 架构 Review
│   ├── api/
│   └── runbook/
├── scripts/
│   ├── mcp_server.py        # MCP Server (hybrid_search + keyword_search)
│   ├── index.py             # 索引工具 (标题分块 + section_path)
│   ├── workers/             # Worker 脚本
│   └── requirements.txt
├── tests/
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── e2e/                 # 端到端测试
├── eval/                    # 评测结果
├── CLAUDE.md                # 本文件
├── Makefile                 # 快捷命令
└── pyproject.toml           # Python 项目元数据
```

## 设计文档

详见 `docs/design-review.md`（架构分析 + 改进方案）
