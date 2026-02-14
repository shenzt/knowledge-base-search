---
id: "design-review-001"
title: "RAG 系统设计 Review"
created: 2025-02-14
confidence: high
---

# RAG 系统设计 Review

## 当前架构

```
用户查询
  ↓
Claude Code (Agent)
  ├─ Layer 1: Grep/Glob/Read → 本地 docs/ (零成本, 关键词)
  ├─ Layer 2: MCP hybrid_search → Qdrant (语义, 跨语言)
  │    ├─ BGE-M3 编码 (dense 1024d + sparse)
  │    ├─ Qdrant prefetch (dense top20 + sparse top20)
  │    ├─ RRF 融合
  │    └─ BGE-Reranker-v2-M3 重排
  └─ Layer 3: 多文档推理 (复杂查询)
       ↓
  生成答案 + 引用
```

### 数据流: Ingest → Index → Search → Answer

| 阶段 | 实现 | 状态 |
|------|------|------|
| Ingest | `/ingest` skill → pandoc/docling → docs/ → git commit | ✅ 可用 |
| Index | `index.py` → BGE-M3 编码 → Qdrant upsert | ⚠️ 基础可用 |
| Search | `/search` skill → Grep + MCP hybrid_search | ✅ 核心功能 |
| Answer | Claude 读取上下文 → 生成带引用的回答 | ✅ 可用 |

### 数据源

| 数据源 | 内容 | 检索方式 | 文档数 |
|--------|------|----------|--------|
| 本地 docs/ | runbook + API 文档 | Grep/Glob/Read (Layer 1) | 3 |
| Qdrant 索引 | K8s EN + Redis CN | MCP hybrid_search (Layer 2) | 21 (152 chunks) |

## 已验证的能力

- Hybrid search (dense + sparse + RRF + rerank): 比纯 dense 提升 36%
- Layer 1 Grep 对本地文档: 100% 通过率 (17/17)
- Claude "语义 Grep": 能将模糊描述分解为多关键词 OR 模式
- 跨语言检索: 英文问→中文文档, 中文问→英文文档
- Session 复用: Agent SDK session resume 避免重复加载模型

## 关键问题

### P0: 分块策略过于简单

当前: 按 `\n\n` 分割, 合并到 3200 字符。

问题:
- 丢失文档结构 (标题层级、section_path)
- 无法定位到具体章节
- 影响检索精度和引用质量

建议: 基于 Markdown 标题的语义分块, 保留 section_path 到 payload。

### P0: 缺少增量索引

当前: 只能单文件索引 (`--file`), 无 `--full` 重建, 无变更检测。

建议:
- payload 中记录 doc_hash
- `git diff` 检测变更文件
- `--full` 全量重建 + `--incremental` 增量更新

### P1: 评测体系不完善

已发现的问题 (详见 `.claude/rules/testing-lessons.md`):
- 测试用例与实际 KB 内容不匹配
- 评估标准过于宽松 (100字符 + 1关键词 = 通过)
- 未区分"基于文档回答" vs "基于通用知识回答"
- Qdrant 用例在无 MCP 模式下的通过是假阳性

当前测试结果 (USE_MCP=0):

| 数据源 | 通过率 | 说明 |
|--------|--------|------|
| 本地 docs/ | 17/17 (100%) | Grep 完全有效 |
| Qdrant 索引 | 6/12 (50%) | 6个429限流, 通过的是通用知识非检索 |

需要 USE_MCP=1 测试才能验证 Layer 2 的真正检索能力。

### P1: MCP Server 缺少 `get_document` 工具

设计文档提到但未实现。当前 hybrid_search 返回 chunk, 无法拉取完整文档上下文。

### P2: rag_worker.py 未集成

- 依赖 `claude_agent_sdk` 未在 requirements.txt
- 引用不存在的 `kb_skills` 目录
- 代码库中无实际调用

### P2: 无单元测试

核心函数 (分块、编码、front-matter 解析) 无测试覆盖。

## 架构优势

1. **"Claude Code 就是 agent"** — 最小化自建代码, Skills 定义行为
2. **三层检索策略** — Grep(零成本) → Hybrid(语义) → 多文档推理
3. **Hybrid Search** — dense + sparse + RRF + rerank, 效果显著
4. **双语支持** — BGE-M3 原生支持中英文跨语言检索
5. **Git 管理文档** — 版本可追溯, 索引可再生

## 建议优先级

| 优先级 | 项目 | 预期收益 |
|--------|------|----------|
| P0 | 语义分块 (保留标题/section_path) | 检索精度 + 引用质量 |
| P0 | 增量索引 (doc_hash + git diff) | 运维效率 |
| P1 | USE_MCP=1 完整测试 | 验证 Layer 2 真实能力 |
| P1 | 实现 get_document MCP 工具 | 完整上下文检索 |
| P1 | 收紧评测标准 (correct_doc 必须匹配) | 评测可信度 |
| P2 | 单元测试 (分块/编码/解析) | 代码质量 |
| P2 | 清理 rag_worker.py | 代码整洁 |
| P2 | scope 过滤修复 (MatchText → prefix) | 检索准确性 |
