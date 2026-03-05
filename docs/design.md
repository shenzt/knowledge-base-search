# knowledge-base-search — 设计文档

> 版本: v2.0 | 日期: 2026-03
> 状态: 核心功能完成，评测体系成熟，仓库导入验证通过，CI/CD 就绪
> 部署模式: 纯本地

---

## 1. 核心理念

**Claude Code 就是 agent。** 能用 agent 做的事情就让它做，不写多余代码。

这是一套 Agentic RAG 的本地化落地方案：
- Git 仓库作为文档单一事实源（SSOT）：版本化、可追溯、可回滚
- Claude Code 作为核心 agent：文档导入、检索、审查全部通过 Skills 编排
- Qdrant 作为可再生索引层：本地混合检索，中英文均有一流支持
- MCP Server 提供向量检索（hybrid_search + keyword_search + index_status），常驻 BGE-M3 模型
- Embedding 抽象层（`embedding_provider.py`）支持本地 BGE-M3 和 OpenAI-compatible API 切换

### 设计原则

1. **极简代码** — 只写 agent 做不了的（向量编码/检索需要常驻模型）
2. **Skills 定义行为** — Claude Code 用内置工具（Read/Grep/Glob/Bash/Write）执行
3. **Git 管理一切** — 文档、配置、Skills 全部版本化，索引可再生不进 Git
4. **中英文并重** — BGE-M3 天然支持多语言，包括跨语言检索

### 架构分层规范

| 层 | 角色 | 判断标准 |
|---|---|---|
| Skill (SKILL.md) | 工作流编排 | 每步都能用 Claude Code 内置工具完成 |
| Python 脚本 | 确定性重活 | 需要常驻模型、向量计算、持久连接 |
| Subagent | 隔离的智能任务 | 需要 LLM 做决策 + 隔离 context |

详见 `.claude/rules/agent-architecture.md`。

---

## 2. 技术选型

### 向量数据库：Qdrant

原生 dense + sparse 混合检索 + RRF 融合，multilingual 全文索引（charabia/jieba），生产级成熟度。Docker 一键启动。

### Embedding：BAAI/bge-m3

8K 上下文、单模型输出 dense（1024d）+ sparse（learned lexical weights）+ ColBERT。sparse 向量替代传统 jieba + BM25，无需额外分词管线。C-MTEB ~62-63。

### Reranker：BAAI/bge-reranker-v2-m3

同系列，中英文 rerank 效果好。

### 文档预处理

不内置预处理代码。Claude Code 通过 Bash 调用本地已安装的 CLI 工具：

| 场景 | 推荐工具 | 安装方式 |
|------|---------|---------|
| 中文 PDF | MinerU | `pip install magic-pdf` |
| 通用文档 | Docling / Marker | `pip install docling` / `pip install marker-pdf` |
| 网页 | curl + pandoc | 系统自带 |
| DOCX/PPTX | pandoc | `apt install pandoc` |

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────┐
│              用户 / Claude Code IDE               │
└──────────────────┬──────────────────────────────┘
                   │
      ┌────────────┼────────────┬──────────┐
      ▼            ▼            ▼          ▼
  /search      /ingest     /index-docs  /review
      │            │            │          │
      │  ┌─────────┘            │          │
      │  │  Claude Code 内置工具              │
      │  │  Read/Grep/Glob/Bash/Write       │
      │  └─────────┐            │          │
      ▼            ▼            ▼          ▼
┌──────────────────────────────────────────────┐
│  knowledge-base MCP Server（唯一的自建代码）    │
│  - hybrid_search (dense+sparse+RRF+rerank)   │
│  - keyword_search (full-text fallback)       │
│  - index_status                              │
└──────────┬───────────────────────────────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌──────────┐ ┌──────────────────────┐
│  Qdrant  │ │  Git 知识库仓库        │
│  (本地)   │ │  docs/ ← Markdown    │
│          │ │  raw/  ← 原始文件     │
└──────────┘ └──────────────────────┘
```

### 检索策略（两层）

| 层 | 方式 | 适用场景 | 成本 |
|----|------|---------|------|
| 第一层 | Grep/Glob（Claude Code 内置） | 关键词明确、术语、错误码 | 零（无需模型） |
| 第二层 | MCP hybrid_search | 语义/模糊/跨语言查询 | 需要 BGE-M3 模型 |

选择逻辑：关键词明确 → 先第一层；模糊/概念性 → 直接第二层；第一层不够 → 补充第二层。

---

## 4. Skills 设计（11 个）

### /search — 知识库检索（自动触发）

Agent 自主路由：Grep（精确关键词）/ hybrid_search（语义模糊）/ Read（完整上下文）。可并行调用。回答必须带引用 `[来源: docs/xxx.md > section_path]`。

### /ingest — 单文档导入（手动触发）

Claude Code 判断输入类型 → 调 CLI 转换 → 整理 Markdown + front-matter → 保存到 docs/ → git commit → 索引。

### /ingest-repo — Git 仓库导入（手动触发）

核心能力。将任意 Git 仓库的 Markdown 文档导入知识库：
1. Shallow clone 仓库到临时目录
2. 扫描 .md 文件（格式路由预留 PDF/DOCX/HTML 桩）
3. 注入溯源 front-matter（source_repo, source_path, source_commit）
4. 输出到外部独立 Git 目录（`--target-dir`），保留原始目录结构
5. LLM 预处理（contextual_summary + gap_flags + evidence_flags）
6. Drop 旧索引 + 全量重建（按 source_repo 过滤删除）
7. 在外部目录 git commit 保留历史版本

设计要点：
- 存储隔离：生成的文档不放在代码仓库中，输出到外部 Git 目录
- 溯源完整：每个 chunk 的 Qdrant payload 包含 source_repo/source_path/source_commit
- 每次重建：初期 repo 不大，drop + full rebuild 保证一致性
- 格式扩展：未来 PDF 用 MinerU，可能需要 Subagent 做智能清洗

### /preprocess — LLM 文档预处理（手动触发）

调用 `doc_preprocess.py`，为每个文档生成 sidecar JSON（contextual_summary + gap_flags + evidence_flags + doc_type + quality_score + key_concepts）。支持 DeepSeek V3 / GLM-4.5 等模型。

### /index-docs — 索引管理（手动触发）

纯 Bash 调用 index.py，支持 --status / --file / --full / --incremental / --delete-by-repo / --snapshot-export / --snapshot-import。

### /review — 文档审查（自动触发）

Claude Code 用 Read/Grep/Glob 直接检查 front-matter 完整性、时效性、TODO 标记等，输出健康度评分。

### /build-index — 分层目录索引（自动触发）

构建/增量更新文档目录的分层索引结构。

### /generate-index — KB 导航指南生成（手动触发）

探索 KB 仓库目录结构和版本策略，生成 INDEX.md 导航指南。

### /eval — RAG 评测（手动触发）

100+ 测试用例（v5: Local 15 + Qdrant 75 + Notfound 10），两阶段评估：Gate 门禁（确定性规则）→ RAGAS faithfulness/relevancy（默认启用）。支持多模型评测（Sonnet / Qwen / GLM-5 / DeepSeek）。

### /convert-html — HTML → Markdown 转换（手动触发）

批量将 HTML 文件转换为 Markdown 格式。

### /sync-from-raw — 双仓同步（手动触发）

原始文档仓库与知识库仓库之间的同步工作流。

---

## 5. 文档规范

### Front-matter（必须）

```yaml
---
id: "d7f3a2b1"           # 稳定主键，首次创建时生成，不可修改
title: "文档标题"
owner: "@负责人"
tags: [分类标签]
created: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
confidence: high | medium | low | deprecated
---
```

- `id` 是 Qdrant 索引的稳定主键，重命名/移动文件时不变
- 新导入文档默认 `confidence: medium`
- `last_reviewed` 超过 6 个月应提醒更新

### 目录结构

```
docs/
├── runbook/          # 运维手册
├── adr/              # 架构决策记录
├── api/              # API 文档
├── postmortem/       # 事后复盘
└── meeting-notes/    # 会议纪要
```

---

## 6. 项目结构

```
knowledge-base-search/
├── CLAUDE.md                    # Agent 上下文
├── .mcp.json                    # MCP Server 配置
├── Makefile                     # 快捷命令
├── pyproject.toml               # Python 项目元数据
├── docker-compose.yml           # Qdrant
├── .claude/
│   ├── rules/                   # 约束规则
│   │   ├── agent-architecture.md  # Skill vs Python vs Subagent 规范
│   │   ├── retrieval-strategy.md
│   │   ├── doc-frontmatter.md
│   │   ├── python-style.md
│   │   ├── security.md
│   │   └── testing-lessons.md   # 26 条经验教训
│   └── skills/                  # Agent 技能（11 个）
│       ├── search/SKILL.md       # 自动触发
│       ├── review/SKILL.md       # 自动触发
│       ├── build-index/SKILL.md  # 自动触发
│       ├── ingest/SKILL.md       # 手动触发
│       ├── ingest-repo/SKILL.md  # 手动触发
│       ├── preprocess/SKILL.md   # 手动触发
│       ├── index-docs/SKILL.md   # 手动触发
│       ├── eval/SKILL.md         # 手动触发
│       ├── generate-index/SKILL.md # 手动触发
│       ├── convert-html/SKILL.md # 手动触发
│       └── sync-from-raw/SKILL.md # 手动触发
├── scripts/
│   ├── mcp_server.py            # 向量检索 MCP Server（hybrid_search + keyword_search + index_status）
│   ├── index.py                 # 索引构建工具（heading-based chunking + section_path + sidecar 注入）
│   ├── doc_preprocess.py        # LLM 文档预处理（contextual_summary + gap_flags）
│   ├── embedding_provider.py    # Embedding 抽象层（Local BGE-M3 / OpenAI-compatible API）
│   ├── llm_client.py            # 统一 LLM 调用接口（Anthropic + OpenAI-compatible）
│   ├── eval_module.py           # 评估模块（extract_contexts + gate_check + llm_judge）
│   ├── eval_skill.py            # Skill 评测脚本（Agent SDK，支持多模型）
│   ├── ragas_judge.py           # RAGAS faithfulness/relevancy 评分
│   ├── generate_eval_report.py  # 评测报告生成
│   ├── workers/                 # Worker 脚本
│   └── requirements.txt
├── docs/                        # 知识库文档（Git 管理）
├── kb/                          # 知识库仓库（Git submodules）
├── tests/
│   ├── unit/                    # 单元测试
│   ├── integration/             # 集成测试
│   └── e2e/                     # E2E 测试 (Agent SDK)
├── eval/                        # 评测结果
└── .github/workflows/
    ├── kb-update.yml            # CI: sync → preprocess → generate INDEX.md → index → snapshot
    ├── kb-eval.yml              # CI: Skill 评测（DeepSeek v3.2 via claude-code-router）
    └── ci.yml                   # CI: Retrieval 评测（Qwen via claude-code-router）
```

---

## 7. 已验证

- [x] Qdrant Docker 启动 + collection 创建
- [x] BGE-M3 模型加载 + dense/sparse 编码
- [x] BGE-Reranker-v2-M3 重排序
- [x] index.py 索引单文件 + 状态查询
- [x] MCP Server hybrid_search + keyword_search
- [x] 中文语义检索（"Redis 主从切换后应用如何重连？" → score 4.89）
- [x] 英文语义检索（"How to fix pod CrashLoopBackOff?" → score 4.11）
- [x] 跨语言检索（中文 query → 英文文档，score 0.37）
- [x] 关键词检索（"JWT" → API 认证文档）
- [x] /search skill 端到端（Grep 快速检索 → 读取文档 → 回答）

---

## 8. 进展

### Phase 1: 核心功能 ✅
- [x] index.py 增量索引（基于 git diff）
- [x] index.py 全量重建（--full）
- [x] 语义分块：Heading-based 切分 + section_path 保留
- [x] Agentic Router：Agent 自主路由，非串行 fallback
- [x] 防幻觉约束：必须基于检索结果回答
- [x] delete_by_source_repo：按仓库批量删除索引

### Phase 2: 评测体系 ✅
- [x] 100 个测试用例 v5（Local 15 + Qdrant 75 + Notfound 10），另有 RAGBench 50 + CRAG 50
- [x] Gate 门禁 + RAGAS faithfulness/relevancy 两阶段评估（RAGAS 默认启用）
- [x] extract_contexts 从 Agent SDK messages_log 提取结构化 contexts
- [x] 多模型评测：Sonnet 89% gate / Qwen 3.5 Plus 98% / GLM-5 95% / DeepSeek V3 52%（partial）
- [x] Skill 评测脚本（eval_skill.py）：独立 session + 600s 超时 + MODEL_NAME 环境变量

### Phase 3: 仓库导入 + 预处理 ✅
- [x] /ingest-repo skill 定义 + 实际运行验证
- [x] 架构规范（Skill vs Python vs Subagent）
- [x] LLM 文档预处理管线（doc_preprocess.py + sidecar JSON）
- [x] Redis 官方文档导入（3,329 docs, ~12K+ chunks）
- [x] awesome-llm-apps 导入（207 docs, ~979 chunks）
- [x] RAGBench + CRAG benchmark 数据导入
- [x] CI/CD 管线（kb-update + kb-eval + ci）
- [ ] 格式扩展：PDF (MinerU) / DOCX (Pandoc)

### Phase 4: 生态扩展
- [x] CI 集成检索回归（kb-eval.yml + ci.yml，使用 DeepSeek/Qwen via claude-code-router）
- [ ] 算力解耦：远程 GPU Embedding（通过 OpenAICompatibleProvider 指向自建 API）
- [ ] 示例仓库：kb-example-sre-runbook

---

## 9. 依赖

```
# 核心（必须）
FlagEmbedding>=1.2.0
qdrant-client>=1.9.0
mcp[cli]>=1.0.0
python-frontmatter>=1.1.0
torch>=2.0.0
numpy>=1.24.0
transformers>=4.38.0,<5.0.0

# 预处理（按需安装）
# magic-pdf          # MinerU（中文 PDF）
# docling            # Docling（通用文档）
# marker-pdf         # Marker（高精度 PDF）
```
