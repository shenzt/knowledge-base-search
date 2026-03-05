---
id: "design-review-002"
title: "RAG 系统设计 Review v2"
created: 2025-02-14
last_reviewed: 2025-02-15
confidence: high
---

# RAG 系统设计 Review v2

## 核心理念

Claude Code 就是 Agent。不写框架代码，不引入 LangChain/LlamaIndex。
Skills 定义行为约束，MCP 提供工具，Agent 自主决策调用什么、怎么调用。

## 架构分层

```
人类 → Claude Code (Agent)
          │
          ├─ Skills (SKILL.md)     工作流编排，Agent 用内置工具执行
          ├─ Python 脚本            只做 Agent 做不了的事（向量编码、常驻模型）
          └─ Subagent (未来)        需要 LLM 决策的隔离任务（如 PDF 智能转换）
```

判断标准详见 `.claude/rules/agent-architecture.md`。

## 当前架构

```
用户查询 → Agent (Router) 自主判断意图，选择工具（可并行）
              │
              ├─ Grep/Glob/Read  → 精确关键词、报错代码、文件路径（零成本）
              ├─ MCP hybrid_search → 模糊语义、跨语言、概念理解（Qdrant）
              ├─ Read             → 读取完整文档上下文（chunk 不够时）
              └─ Glob + Read     → 小规模 KB 直接全量读取（< 50KB 时跳过检索）
```

不是串行 fallback，是 Agent 根据查询特征自主路由（Agentic Router）。

### 实际代码现状（已更新至 2026-03）

| 组件 | 文件 | 状态 |
|------|------|------|
| MCP Server | `scripts/mcp_server.py` | ✅ hybrid_search + keyword_search + index_status |
| 索引工具 | `scripts/index.py` | ✅ heading-based chunking + section_path + sidecar 注入 + incremental |
| 评估模块 | `scripts/eval_module.py` | ✅ extract_contexts + gate_check + llm_judge |
| Skill 评测 | `scripts/eval_skill.py` | ✅ Agent SDK, 600s timeout, RAGAS 默认, MODEL_NAME |
| RAGAS Judge | `scripts/ragas_judge.py` | ✅ faithfulness + relevancy 评分 |
| LLM 预处理 | `scripts/doc_preprocess.py` | ✅ contextual_summary + gap_flags + evidence_flags |
| Embedding 抽象层 | `scripts/embedding_provider.py` | ✅ Local BGE-M3 / OpenAI-compatible API |
| LLM 客户端 | `scripts/llm_client.py` | ✅ Anthropic + OpenAI-compatible 统一接口 |
| 检索 Skill | `.claude/skills/search/` | ✅ Agentic Router 策略 |
| 仓库导入 Skill | `.claude/skills/ingest-repo/` | ✅ clone → 提取 → 溯源 front-matter → 预处理 → 索引 |
| CI/CD | `.github/workflows/` | ✅ kb-update + kb-eval (DeepSeek) + ci (Qwen) |

### 已验证的数据（v4 baseline，历史基准）

> **注**：以下为 v4 (64 用例) 的初始基准数据。当前 v5 (100+ 用例) 和多模型评测结果见 CLAUDE.md 和 testing-lessons.md。

| 指标 | 结果 |
|------|------|
| Hybrid vs Dense-only | +36% 准确率 |
| Layer 1 本地文档 (Grep) | 17/17 (100%) |
| Layer 2 Qdrant (USE_MCP=1) | 37/41 (90%) |
| Notfound 防幻觉 | 6/6 (100%) |
| 总体 (USE_MCP=1) | 60/64 (93.8%) |
| 跨语言 | 英文问→中文文档 ✅，中文问→英文文档 ✅ |

## 已解决的架构问题

### ✅ 问题 1: 串行 fallback → Agentic Router

已改为 Agent 自主路由。`/search` skill 提供工具箱，Agent 根据查询特征选择，可并行调用。

### ✅ 问题 2: 分块丢失结构 → Heading-based chunking

`index.py` 按 Markdown 标题切分，注入 `section_path` 到 payload。引用可精确到章节级。

### ✅ 问题 3: 增量索引缺失 → git diff + delete + upsert

`--incremental` 基于 git diff，`--full` 全量重建，`--delete-by-repo` 按仓库批量删除。

### ✅ 问题 4: 评测假阳性 → Gate 门禁

两阶段评估：Gate（确定性规则，一票否决）→ 质量检查。extract_contexts 从 Agent SDK messages_log 提取结构化 contexts，按 tool_use_id 精确匹配。

### ✅ 问题 5: 仓库导入能力 → /ingest-repo skill

支持 clone 任意 Git 仓库 → 提取 md → 注入溯源 front-matter → 输出到外部 KB 目录 → drop + rebuild 索引。

## 当前待解决

### 问题 6: 检索质量长尾问题

v4 时的 3 个具体失败已在 v5 数据集调整中重新评估。当前主要关注：
- awesome-llm-apps 类别检索命中率偏低（Sonnet: llm-agent 62%）
- 非 Sonnet 模型的 Grep 搜索污染（返回 ragbench/crag 噪声文件）
- 详见 CLAUDE.md 中的多模型评测对比

### 问题 7: 格式扩展

当前只处理 .md。未来需要：
- PDF → MinerU (`magic-pdf`)，可能需要 Subagent 做智能清洗
- DOCX → Pandoc
- HTML → Pandoc + html2text

## 不做的事情

- ❌ 不引入 LangChain / LlamaIndex / Unstructured
- ❌ 不写 Python 路由逻辑（Agent 自己路由）
- ❌ 不写面向人类的 CLI 工具（所有能力封装为 Skill）
- ❌ 不训练意图分类模型（Claude 本身就能判断）
- ❌ 不在 Python 里维护索引状态（Git 已经有）
