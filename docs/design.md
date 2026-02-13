# 基于 Git + Qdrant + MCP + Claude Code 的中文知识库检索系统 — 设计文档

> 版本: v0.4 | 日期: 2026-01
> 状态: 架构设计（整合多方反馈）
> 部署模式: 纯本地（支持算力解耦到局域网服务器）

---

## 1. 背景与动机

团队工程文档（Runbook、ADR、API 文档、事后复盘、会议纪要等）散落各处，缺乏统一检索入口。目标：

- Git 仓库作为文档单一事实源（SSOT）：版本化、PR 审核、可追溯、可回滚
- Qdrant 作为可再生索引层：本地混合检索，对中文有一流支持
- MCP + Skills 做编排：文档预处理、检索、审查全部通过 Claude Code agentic 流程完成
- 可复现、可追溯、可回归测试

---

## 2. 技术选型

### 2.1 向量数据库：Qdrant

选择 Qdrant 而非 ChromaDB：原生 dense + sparse 混合检索 + RRF 融合，multilingual 全文索引（charabia/jieba），生产级成熟度。

### 2.2 Embedding：BAAI/bge-m3

8K 上下文、单模型输出 dense + sparse（learned lexical weights）+ ColBERT，C-MTEB ~62-63。sparse 向量替代传统 jieba + BM25，无需额外分词管线。

### 2.3 Reranker：BAAI/bge-reranker-v2-m3

同系列，中文 rerank 效果好。

### 2.4 文档预处理工具

| 场景 | 推荐工具 | MCP Server | 说明 |
|------|---------|-----------|------|
| 中文 PDF | MinerU | ❌ (CLI) | 上海 AI Lab，中文 PDF 解析最强 |
| 通用文档 (PDF/DOCX/PPTX/XLSX) | Docling (IBM) | ✅ docling-mcp | 格式最广，有 MCP |
| 高精度表格/公式 PDF | Marker | ❌ (CLI) | LLM 模式下表格/公式最佳 |
| 网页抓取 | Firecrawl / Crawl4AI | ✅ 均有 MCP | Firecrawl 全站爬取，Crawl4AI 开源本地 |

### 2.5 检索策略定位

| 检索通道 | 角色 | 说明 |
|---------|------|------|
| BGE-M3 dense | 主力：语义召回 | cosine similarity |
| BGE-M3 sparse | 主力：词项召回 | learned lexical weights，对中文比 naive full-text 更稳 |
| RRF 融合 | 主力：结果合并 | Reciprocal Rank Fusion |
| BGE-Reranker | 主力：精排 | 最终排序 |
| Qdrant full-text | 补充：fallback/过滤/高亮 | multilingual tokenizer，不作为主要召回通道 |

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户 / Claude Code IDE                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   /search skill  /ingest skill  /review skill
          │            │            │
          ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server 层                             │
│                                                             │
│  knowledge-base MCP     docling-mcp      firecrawl-mcp     │
│  (自建检索+索引服务)     (文档解析)        (网页抓取)         │
│  - hybrid_search        - convert_pdf    - scrape           │
│  - keyword_search       - to_markdown    - crawl            │
│  - get_document                                             │
│  - index_file                                               │
│  - delete_document                                          │
│  - index_status                                             │
└──────────┬──────────────────┬───────────────────────────────┘
           │                  │
           ▼                  ▼
┌──────────────────┐  ┌──────────────────────────────────────┐
│  Qdrant (本地)    │  │  Git 知识库仓库                       │
│  dense + sparse   │  │  docs/ ← 预处理后的 Markdown          │
│  + full-text      │  │  raw/  ← 原始文件 (PDF/HTML/...)     │
│                   │  │  .index_manifest.jsonl ← 索引清单     │
└──────────────────┘  └──────────────────────────────────────┘
```

---

## 4. 核心设计

### 4.1 doc_id 稳定性设计

路径会变（重命名/移动），所以 doc_id 不能依赖路径。

每篇文档 front-matter 必须包含稳定 `id`：

```yaml
---
id: "d7f3a2b1"              # 稳定主键，首次创建时生成（短 UUID/hash）
title: "Service A 故障处理手册"
owner: "@zhangsan"
tags: [runbook, service-a]
created: 2025-01-15
last_reviewed: 2025-06-01
confidence: high
---
```

规则：
- `id` 是 Qdrant 中所有 chunks 的 `doc_id` 字段，作为稳定主键
- `path` 只是可变属性，写入 payload 但不作为主键
- 重命名/移动文件时 `id` 不变，索引自动关联
- `index_file` 时：先按 `doc_id` 批量 delete 旧 chunks，再 upsert 新 chunks（幂等）

### 4.2 语义分块策略（Semantic Chunking）

两层切分，避免切烂表格/代码块/章节：

**第一层：结构切分（Header-based）**

按 Markdown heading 层级分 section，每个 section 保留完整的标题路径（`h1 > h2 > h3`）。

**第二层：长度切分**

- 单个 section 超过 3200 字符（~800 token）时，按段落/句子边界再切
- 切分时保留 15% 重叠（480 字符）
- 切分优先级：`\n\n` → `\n` → `。` → `；` → 空格
- 表格和代码块视为原子单元，不在中间切断

每个 chunk 的 payload：

```json
{
  "doc_id": "d7f3a2b1",
  "chunk_id": "d7f3a2b1-003",
  "path": "docs/runbook/service-a.md",
  "section_path": "Service A 故障处理手册 > 常见故障 > 连接超时",
  "source_line_range": [42, 78],
  "chunk_index": 3,
  "doc_hash": "sha256:abc123...",
  "kb_commit": "ff41edc",
  "title": "Service A 故障处理手册",
  "confidence": "high",
  "tags": ["runbook", "service-a"],
  "text": "..."
}
```

### 4.3 Index Manifest（可复现、可追溯）

每次索引构建追加一条记录到 `.index_manifest.jsonl`（进 Git）：

```jsonl
{"timestamp":"2026-01-15T10:30:00Z","kb_commit":"ff41edc","action":"full_rebuild","chunking_version":"v1","chunk_size":3200,"chunk_overlap":480,"embedding_model":"BAAI/bge-m3","reranker_model":"BAAI/bge-reranker-v2-m3","total_docs":48,"total_chunks":342,"docs_added":48,"docs_updated":0,"docs_deleted":0}
```

用途：
- 回答结果可追溯到"某个 commit + 某个 chunk + 某次索引构建"
- 出现"同一问题今天和昨天答案不一样"时，快速定位是文档变了还是切块/模型/策略变了

### 4.4 增量索引（doc_hash 驱动）

不全量重建，以 `doc_hash = sha256(normalized_markdown)` 为驱动：

```
git diff --name-status HEAD~1 HEAD -- docs/
  │
  ├── A (新增) → 解析 front-matter → 切块 → 编码 → upsert
  ├── M (修改) → 计算 doc_hash
  │     ├── hash 未变 → 跳过
  │     └── hash 变了 → 按 doc_id delete 旧 chunks → 重新切块 → upsert
  └── D (删除) → 按 doc_id delete 所有 chunks
```

### 4.5 /ingest Skill — 文档导入（带审计日志）

导入流程输出结构化结果：

```json
{
  "raw_artifact_path": "raw/performance-report-2025.pdf",
  "converter_used": "mineru",
  "converter_version": "1.3.0",
  "markdown_path": "docs/api/performance-report-2025.md",
  "doc_id": "e8f4b2c1",
  "doc_hash": "sha256:def456...",
  "index_points": 12,
  "warnings": ["第 15 页表格 OCR 置信度低 (0.62)", "第 23 页公式可能不完整"]
}
```

转换日志落盘到 `docs/.ingest_logs/`。

### 4.6 /search Skill — 引用作为一等公民

`hybrid_search` 返回完整追溯信息：

```json
{
  "doc_id": "d7f3a2b1",
  "chunk_id": "d7f3a2b1-003",
  "section_path": "Service A 故障处理手册 > 常见故障 > 连接超时",
  "source_path": "docs/runbook/service-a.md",
  "source_line_range": [42, 78],
  "kb_commit": "ff41edc",
  "score_dense": 0.82,
  "score_sparse": 0.71,
  "score_rrf": 0.76,
  "score_rerank": 0.89,
  "confidence": "high",
  "text": "..."
}
```

### 4.7 /review Skill — 健康度仪表盘

| 检查项 | 说明 |
|--------|------|
| front-matter 完整性 | id/title/owner/tags/created/last_reviewed/confidence |
| 时效性 | last_reviewed 超过 6 个月 |
| deprecated 引用 | confidence=deprecated 的文档是否仍被引用 |
| 孤儿文档 | 长期从未被检索命中的文档 |
| 近重复文档 | 同一主题多份版本，需合并或标注 deprecated |
| 索引一致性 | docs/ 与 Qdrant 中的文档是否一致 |
| 内容质量 | 空章节、TODO 标记、占位符内容 |

输出健康度评分（0-100）+ 按严重程度分类的问题列表。

### 4.8 Eval 回归框架

```
eval/
├── questions.jsonl        # 测试问题集
├── eval.py                # 评测脚本
└── results/               # 历史评测结果
```

questions.jsonl 格式：
```jsonl
{"question":"Redis 主从切换后客户端如何自动重连？","expected_doc_ids":["d7f3a2b1"],"expected_keywords":["sentinel","重连","failover"],"scope":"runbook"}
```

评测指标：Retrieval@K、Chunk Hit Rate、答案一致性（LLM-as-judge）。

---

## 5. 算力解耦

| 组件 | 部署位置 | 说明 |
|------|---------|------|
| Claude Code + 轻量 MCP | 本地开发机 | 编排层，低算力 |
| Qdrant + 检索 MCP | 本地或局域网服务器 | 检索层，中等算力 |
| 预处理 MCP (Docling/MinerU) | GPU 服务器 / NAS | 重算力，按需调用 |

MCP HTTP transport 天然支持远程调用：
```json
{"mcpServers": {"knowledge-base": {"type": "http", "url": "http://gpu-server:8181/mcp"}}}
```

---

## 6. 示例仓库

### 6.1 kb-example-sre-runbook（推荐首选）

最贴近实际痛点，可直接迁移到团队内部。

内容：3-5 篇 runbook + 2 篇 postmortem + 1-2 份公开 PDF

配套：docker-compose.yml、Makefile（bootstrap/ingest/index/search/review/eval）、eval 问题集

### 6.2 kb-example-ai-agent-docs（动态知识库）

用 Crawl4AI 定期爬取 Agent 框架文档，解决"框架更新快、训练数据跟不上"的痛点。

### 6.3 kb-example-quant-research（高难度预处理）

展示 MinerU 在复杂金融 PDF（公式、密集表格）上的解析能力。

---

## 7. 项目目录结构

```
knowledge-base-search/
├── CLAUDE.md
├── .mcp.json
├── Makefile
├── docker-compose.yml
├── .claude/
│   ├── rules/
│   │   ├── retrieval-strategy.md
│   │   ├── doc-frontmatter.md
│   │   └── python-style.md
│   ├── skills/
│   │   ├── search/SKILL.md
│   │   ├── ingest/SKILL.md
│   │   ├── index-docs/SKILL.md
│   │   └── review/SKILL.md
│   └── agents/
│       └── doc-reviewer.md
├── scripts/
│   ├── mcp_server.py
│   ├── index.py
│   ├── chunker.py
│   └── requirements.txt
├── docs/
│   ├── design.md
│   ├── .ingest_logs/
│   ├── runbook/
│   ├── adr/
│   ├── api/
│   ├── postmortem/
│   └── meeting-notes/
├── raw/
├── eval/
│   ├── questions.jsonl
│   ├── eval.py
│   └── results/
├── .index_manifest.jsonl
└── .gitignore
```

---

## 8. 实施路线

### Phase 1: 核心脚本（3-5 天）
- [ ] chunker.py — Header-based + 长度切分
- [ ] index.py — doc_hash 驱动增量索引 + manifest
- [ ] mcp_server.py — Qdrant 混合检索 + Reranker

### Phase 2: Skills 和配置（2-3 天）
- [ ] /ingest、/search、/review skills
- [ ] Makefile + docker-compose.yml

### Phase 3: 示例仓库（3-5 天）
- [ ] kb-example-sre-runbook + eval 回归

### Phase 4: 迭代优化（持续）
- [ ] 中文 benchmark + 参数调优
- [ ] 更多示例仓库
- [ ] CI 集成检索回归

---

## 9. 依赖清单

```
# 核心
FlagEmbedding>=1.2.0       # BGE-M3 + Reranker
qdrant-client>=1.9.0       # Qdrant Python SDK
mcp>=1.0.0                 # MCP Server SDK
python-frontmatter>=1.1.0  # front-matter 解析
torch>=2.0.0               # PyTorch
numpy>=1.24.0              # 向量计算

# 预处理（按需）
magic-pdf                  # MinerU
docling                    # Docling
marker-pdf                 # Marker
```
