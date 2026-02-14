# knowledge-base-search

基于 Git + Qdrant + Claude Code 的 Agentic RAG 本地知识库检索系统。

## 核心理念

**Claude Code 就是 agent。** 能用 agent 做的事情就让它做，不写多余代码。

- Git 仓库 = 文档单一事实源（SSOT）
- Claude Code = 核心 agent（导入、检索、审查全部通过 Skills 编排）
- Qdrant = 可再生向量索引（不进 Git）
- MCP Server = 唯一的自建代码（向量检索需要常驻模型）

## 架构分层

```
人类 → Claude Code (Agent)
          │
          ├─ Skills (SKILL.md)     工作流编排，Agent 用内置工具执行
          ├─ Python 脚本            只做 Agent 做不了的事（向量编码、常驻模型）
          └─ Subagent (未来)        需要 LLM 决策的隔离任务（如 PDF 智能转换）
```

判断标准：
- 每一步都能用 Claude Code 内置工具完成 → **Skill**
- 需要常驻模型、向量计算 → **Python 脚本**
- 需要 LLM 做决策 + 隔离 context → **Subagent**

详见 `.claude/rules/agent-architecture.md`。

## 前置条件

- Python 3.10+
- Docker（用于运行 Qdrant）
- 约 3GB 磁盘空间（BGE-M3 模型首次运行时自动下载）

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url> && cd knowledge-base-search

# 2. 创建 venv 并安装依赖
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt

# 3. 启动 Qdrant
docker compose up -d

# 4. 索引示例文档（首次运行会下载 BGE-M3 模型，约 2-3 分钟）
.venv/bin/python scripts/index.py --full docs/

# 5. 确认索引状态
.venv/bin/python scripts/index.py --status
```

> CPU-only PyTorch 即可运行（约 190MB），无需 GPU。安装时可用：
> `pip install torch --index-url https://download.pytorch.org/whl/cpu`

## Skills（在 Claude Code 中使用）

```
/search Redis 主从切换后如何重连？
/search How to fix pod CrashLoopBackOff?
/ingest raw/report.pdf runbook
/ingest-repo https://github.com/redis/docs --target-dir ../my-kb --md-root content/
/index-docs --status
/review
```

| Skill | 用途 | 实现方式 |
|-------|------|---------|
| `/search` | 知识库检索 | Agent 自主路由 Grep / hybrid_search / Read |
| `/ingest` | 导入单个文档 | Agent 调 CLI 转换 + 整理 + git commit |
| `/ingest-repo` | 导入 Git 仓库 | Agent clone → 提取 md → 注入溯源 front-matter → 索引 → git commit 到外部 KB 目录 |
| `/index-docs` | 索引管理 | 调 index.py（--status / --file / --full / --incremental） |
| `/review` | 文档审查 | Agent 用 Read/Grep 检查 front-matter、时效性等 |
| `/eval` | RAG 评测 | 64 个用例，Gate 门禁 + 质量检查 |

## 导入 Git 仓库

`/ingest-repo` 是核心能力 — 将任意 Git 仓库的 Markdown 文档导入知识库：

```
/ingest-repo https://github.com/redis/docs --target-dir ../my-agent-kb --md-root content/
```

流程：
1. Shallow clone 仓库到临时目录
2. 扫描 .md 文件（未来支持 PDF/DOCX 格式路由）
3. 注入溯源 front-matter（source_repo, source_path, source_commit）
4. 输出到外部独立 Git 目录，保留原始目录结构
5. Drop 旧索引 + 全量重建（按 source_repo 过滤删除）
6. 在外部目录 git commit 保留历史版本

每个 chunk 的 Qdrant payload 包含完整溯源信息，可回溯到原始 repo 的具体文件和 commit。

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 向量数据库 | Qdrant | dense + sparse 混合检索 + RRF |
| Embedding | BAAI/bge-m3 | 1024d，中英文，dense + sparse |
| Reranker | BAAI/bge-reranker-v2-m3 | 中英文重排序 |
| Agent | Claude Code | Skills 编排，内置工具执行 |
| 版本管理 | Git | 文档 SSOT |
| 分块策略 | Heading-based | 按 Markdown 标题切分，保留 section_path 层级 |

## 检索架构

```
用户查询 → Agent (Router) 自主判断意图，选择工具（可并行）
              │
              ├─ Grep/Glob/Read  → 精确关键词、报错代码、文件路径（零成本）
              ├─ MCP hybrid_search → 模糊语义、跨语言、概念理解（Qdrant）
              ├─ Read             → 读取完整文档上下文（chunk 不够时）
              └─ Glob + Read     → 小规模 KB 直接全量读取（< 50KB 时跳过检索）
```

不是串行 fallback，是 Agent 根据查询特征自主路由，可并行调多个工具。

## 常用命令

```bash
make setup                                        # 初始化环境
make start                                        # 启动 Qdrant
make status                                       # 查看索引状态
make test                                         # 运行测试
.venv/bin/python scripts/index.py --full docs/    # 全量索引
.venv/bin/python scripts/index.py --incremental   # 增量索引（基于 git diff）
.venv/bin/python scripts/index.py --delete-by-repo <url>  # 按仓库删除索引
```

## 评测

64 个测试用例，两阶段评估（Gate 门禁 + 质量检查）：

| 模式 | Local | Qdrant | Notfound | 总计 |
|------|-------|--------|----------|------|
| USE_MCP=0 | 17/17 (100%) | 0/41 (0%) | 6/6 (100%) | 23/64 (35.9%) |
| USE_MCP=1 | 17/17 (100%) | 37/41 (90%) | 6/6 (100%) | 60/64 (93.8%) |

详见 `.claude/skills/eval/SKILL.md`。

## 项目结构

```
knowledge-base-search/
├── .claude/
│   ├── skills/                  # Agent Skills
│   │   ├── search/              # 知识库检索
│   │   ├── ingest/              # 单文档导入
│   │   ├── ingest-repo/         # Git 仓库导入
│   │   ├── index-docs/          # 索引管理
│   │   ├── review/              # 文档审查
│   │   └── eval/                # RAG 评测
│   └── rules/                   # 约束规则
│       ├── agent-architecture.md  # Skill vs Python vs Subagent 规范
│       ├── retrieval-strategy.md
│       ├── doc-frontmatter.md
│       ├── python-style.md
│       └── testing-lessons.md
├── scripts/
│   ├── mcp_server.py            # MCP Server (hybrid_search + keyword_search)
│   ├── index.py                 # 索引工具 (heading-based chunking + section_path)
│   ├── eval_module.py           # 评估模块 (extract_contexts + gate_check)
│   └── requirements.txt
├── docs/                        # 本地知识库文档
├── tests/
│   ├── unit/                    # 单元测试 (40 tests)
│   ├── integration/             # 集成测试
│   └── e2e/                     # E2E 测试 (Agent SDK)
├── eval/                        # 评测结果
├── CLAUDE.md                    # Agent 上下文
├── Makefile                     # 快捷命令
└── docker-compose.yml           # Qdrant
```

## 文档

- [设计文档](docs/design.md) — 系统架构、技术选型、Skills 设计
- [设计 Review](docs/design-review.md) — 架构分析、改进方案、实施进展
