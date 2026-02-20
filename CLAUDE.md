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
- `/ingest-repo <repo-url> [--target-dir <path>]` — 导入 Git 仓库（clone → 提取 md → 注入 front-matter → 预处理 → 索引 → git commit）
- `/preprocess [--dir|--file|--status]` — LLM 文档预处理（生成 contextual_summary + evidence_flags + gap_flags）
- `/index-docs [--status|--file|--full|--incremental]` — 索引管理（调 index.py）
- `/review [--scope xxx] [--fix]` — 文档审查（Claude Code 用 Read/Grep 直接检查）

## 数据导入链路

```
Git Repo / 文件 / URL
  → /ingest-repo 或 /ingest（clone + 提取 .md + 注入 front-matter）
  → /preprocess（LLM 生成 sidecar JSON: contextual_summary + gap_flags + evidence_flags）
  → /index-docs --full（BGE-M3 编码，contextual_summary 注入 embedding，元数据写入 Qdrant payload）
  → hybrid_search 返回 agent_hint + evidence_flags，Agent 据此判断 chunk 充分性
```

关键组件：
- `scripts/doc_preprocess.py` — LLM 预处理（DeepSeek/GLM/Claude），生成 `.preprocess/*.json` sidecar
- `scripts/llm_client.py` — 统一 LLM 调用接口（Anthropic + OpenAI-compatible）
- `scripts/index.py` — 向量编码 + Qdrant 写入，自动读取 sidecar 注入 embedding 和 metadata
- `scripts/mcp_server.py` — MCP Server，hybrid_search 输出包含 agent_hint / evidence_flags

## 架构规范

详见 `.claude/rules/agent-architecture.md`。核心原则：
- Agent 是唯一入口，不写面向人类的 CLI 工具
- Skill = 工作流编排（Agent 用内置工具执行）
- Python 脚本 = 只做 Agent 做不了的事（向量编码、常驻模型、LLM 预处理）
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

# 预处理相关
.venv/bin/python scripts/doc_preprocess.py --dir <path>     # 批量 LLM 预处理
.venv/bin/python scripts/doc_preprocess.py --status <path>  # 查看预处理状态
.venv/bin/python scripts/index.py --full <path>             # 预处理后重建索引
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
- 区分数据源：本地 docs/ 只有 3 个技术文档，Qdrant 索引有 2662 chunks（Redis + LLM Apps + 本地 + RAGBench + CRAG）
- 导入新数据源后，必须运行预处理 + 重建索引才能生效

## 知识库数据源

### Qdrant 索引（2675 chunks，heading-based chunking + section_path + 预处理元数据）
- Redis 官方文档 (234 docs, ~1120 chunks): redis/docs
  - Data Types: Strings, Lists, Sets, Sorted Sets, Hashes, Streams, JSON, Probabilistic, TimeSeries, Vector Sets
  - Management: Sentinel, Replication, Persistence, Scaling (Cluster), Config, Admin, Debugging, Troubleshooting
  - Security: ACL, Encryption
  - Optimization: Benchmarks, Latency, Memory, CPU Profiling
  - Develop: Pipelining, Transactions, Pub/Sub, Keyspace, Lua Scripting
  - Install: Linux, macOS, Docker, Build from source
- awesome-llm-apps (207 docs, ~979 chunks): Shubhamsaboo/awesome-llm-apps
  - RAG Tutorials: hybrid search, agentic RAG, database routing, local RAG, Cohere RAG
  - AI Agents: research agent, data analysis, travel planner, sales intelligence, VC due diligence
  - Chat with X: YouTube videos, PDF, GitHub, Gmail, research papers
  - Multi-Agent: agent teams, code reviewer, multimodal agents
  - LLM Frameworks: LangChain, CrewAI, Phidata, OpenAI SDK
  - Advanced: resume matcher, content generator, voice AI
- 本地 docs/ (21 docs, ~168 chunks): 项目 runbook + API 文档 + 设计文档
- RAGBench techqa (245 docs, ~249 chunks): IBM 技术文档 QA，来自 rungalileo/ragbench
- CRAG finance (119 docs, ~153 chunks): 金融领域 QA，来自 facebookresearch/CRAG（已清洗 JS/CSS 垃圾）
- 来源: 通过 /ingest-repo 或导入脚本导入
- 预处理: 462 docs 已完成 LLM 预处理（DeepSeek V3），sidecar 存储在 `.preprocess/` 目录
- 查看: `.venv/bin/python scripts/index.py --status`

### 本地 docs/（项目文档 + 示例 runbook）
- `runbook/redis-failover.md` — Redis Sentinel 主从切换故障恢复
- `runbook/kubernetes-pod-crashloop.md` — K8s CrashLoopBackOff 排查
- `api/authentication.md` — OAuth 2.0 + JWT API 认证设计
- 其余为项目自身的设计/进展文档，不是知识库内容

### 预处理元数据（sidecar JSON）

每个文档经 LLM 预处理后生成 `.preprocess/<filename>.json`，包含：
- `contextual_summary` — 1 句话文档摘要，注入 embedding 提升检索召回
- `doc_type` — tutorial / reference / guide / troubleshooting / overview / example
- `quality_score` — 0-10，基于 actionability + specificity + structure
- `key_concepts` — 3-5 个关键术语
- `gap_flags` — missing_command / missing_config / missing_example / incomplete_steps
- `evidence_flags` — has_command / has_config / has_code_block / has_steps（正则计算，零 LLM 成本）

hybrid_search 返回结果中包含 `agent_hint`（压缩的 doc_type + quality + gaps）和 `evidence_flags`，Agent 据此判断 chunk 充分性。

## 项目结构

```
knowledge-base-search/
├── .claude/
│   ├── skills/              # Skills（Agent 行为约束）
│   │   ├── search/          # 知识库检索（含预处理元数据使用指南）
│   │   ├── preprocess/      # LLM 文档预处理
│   │   ├── ingest-repo/     # Git 仓库导入
│   │   └── ...
│   └── rules/               # 路径规则 + 经验教训
├── docs/                    # 知识库文档
│   ├── design.md            # 系统设计
│   ├── design-review.md     # 架构 Review
│   ├── api/
│   └── runbook/
├── scripts/
│   ├── mcp_server.py        # MCP Server (hybrid_search + keyword_search + agent_hint)
│   ├── index.py             # 索引工具 (标题分块 + section_path + sidecar 注入)
│   ├── doc_preprocess.py    # LLM 文档预处理 (contextual_summary + gap_flags)
│   ├── llm_client.py        # 统一 LLM 调用接口 (Anthropic + OpenAI-compatible)
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
