# knowledge-base-search — 设计文档

> 版本: v0.5 | 日期: 2025-02
> 状态: 核心功能已验证
> 部署模式: 纯本地

---

## 1. 核心理念

**Claude Code 就是 agent。** 能用 agent 做的事情就让它做，不写多余代码。

这是一套 Agentic RAG 的本地化落地方案：
- Git 仓库作为文档单一事实源（SSOT）：版本化、可追溯、可回滚
- Claude Code 作为核心 agent：文档预处理、分块、检索、审查全部通过 Skills 编排
- Qdrant 作为可再生索引层：本地混合检索，中英文均有一流支持
- MCP Server 只做一件事：向量检索（因为需要常驻 BGE-M3 模型）

### 设计原则

1. **极简代码** — 只写 agent 做不了的（向量编码/检索需要常驻模型）
2. **Skills 定义行为** — Claude Code 用内置工具（Read/Grep/Glob/Bash/Write）执行
3. **Git 管理一切** — 文档、配置、Skills 全部版本化，索引可再生不进 Git
4. **中英文并重** — BGE-M3 天然支持多语言，包括跨语言检索

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

## 4. Skills 设计

### /search — 知识库检索

两层检索策略，回答必须带引用 `[来源: docs/xxx.md:行号]`。

### /ingest — 文档导入

Claude Code 判断输入类型 → 调 CLI 转换 → 整理 Markdown + front-matter → 保存到 docs/ → git commit → 索引。

### /index-docs — 索引管理

纯 Bash 调用 index.py，支持 --status / --file / --incremental。

### /review — 文档审查

Claude Code 用 Read/Grep/Glob 直接检查 front-matter 完整性、时效性、TODO 标记等，输出健康度评分。

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
├── docker-compose.yml           # Qdrant
├── .claude/
│   ├── rules/                   # 路径条件规则
│   │   ├── retrieval-strategy.md
│   │   ├── doc-frontmatter.md
│   │   └── python-style.md
│   └── skills/                  # Agent 技能
│       ├── search/SKILL.md
│       ├── ingest/SKILL.md
│       ├── index-docs/SKILL.md
│       └── review/SKILL.md
├── scripts/
│   ├── mcp_server.py            # 向量检索 MCP Server
│   ├── index.py                 # 索引构建工具
│   └── requirements.txt
├── docs/                        # 知识库文档（Git 管理）
└── raw/                         # 原始文件（PDF/DOCX 等）
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

## 8. TODO

### Phase 1: 完善核心功能
- [ ] index.py 增量索引（基于 git diff + doc_hash）
- [ ] index.py 全量重建（--full）
- [ ] mcp_server.py 添加 get_document 工具（拉取完整文档上下文）
- [ ] 语义分块优化：Header-based 切分 + section_path 保留
- [ ] .mcp.json 中 python 路径改为相对 venv 路径

### Phase 2: 测试知识库
- [ ] 英文测试库：redis-doc（Redis 官方文档，结构化技术文档）
- [ ] 中文测试库：CS-Base 网络篇（小林 coding，中文技术教程）
- [ ] 端到端测试：ingest → index → search → 回答质量验证

### Phase 3: 增强功能
- [ ] /review skill 实际运行验证
- [ ] 目录索引生成（SUMMARY.md / index.json，给 agent 建"目录册"）
- [ ] Eval 回归框架（questions.jsonl + 评测脚本）
- [ ] 算力解耦：MCP HTTP transport 支持远程 GPU 服务器

### Phase 4: 生态扩展
- [ ] 示例仓库：kb-example-sre-runbook
- [ ] 示例仓库：kb-example-redis-docs
- [ ] 文档预处理工具集成测试（MinerU / Docling / Marker）
- [ ] CI 集成检索回归

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
