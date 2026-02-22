---
name: eval
description: RAG 评测。运行评测用例，分析结果，生成报告。当用户提到"评测"、"eval"、"跑测试" 时触发。
argument-hint: [--mcp] [--quick] [--analyze <file>] [--re-eval] [--status]
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
---

# /eval — RAG 评测

触发: `/eval [选项]`

## 选项

- `/eval` — 默认: USE_MCP=0 跑本地 docs/ 用例
- `/eval --mcp` — USE_MCP=1 跑全量用例（含 Qdrant，约 1.5h）
- `/eval --quick` — 只跑 5 个核心用例快速验证
- `/eval --analyze <json_file>` — 分析已有评测结果，输出改进建议
- `/eval --re-eval <detail.jsonl>` — 用修复后的 eval_module 重新评分（不重跑 Agent）
- `/eval --status` — 查看索引状态 + 上次评测结果摘要

## 评测流程

```
1. 预检查
   - Qdrant 是否运行？索引是否非空？
   - 如果 --mcp: MCP server 是否可用？
   - 显示 KB commit hash

2. 运行测试
   - 执行: .venv/bin/python tests/e2e/test_agentic_rag_sdk.py
   - 环境变量: USE_MCP=0|1
   - 每个用例独立 session（禁止 session 复用）

3. 分析结果
   - 读取 eval/ 下最新的 JSON 结果文件
   - 按 source (local/qdrant/none) 分组统计
   - 按 type (exact/scenario/cross-lang/howto/concept/notfound) 分组统计
   - 识别失败模式: gate 失败原因分布

4. 输出改进建议
   - 哪些 gate check 失败最多？
   - 哪些文档检索不到？是索引问题还是检索策略问题？
   - 是否有幻觉（notfound 用例未拒答）？
   - 引用质量如何？
```

## 评估架构（两阶段）

```
Agent 回答 + messages_log
        │
        ▼
  extract_contexts()  ← 从 ToolUseBlock/ToolResultBlock 提取结构化 contexts
  ├─ 支持 MCP 工具名（含连字符: mcp__knowledge-base__hybrid_search）
  ├─ 按 tool_use_id 精确匹配 ToolUse ↔ ToolResult
  └─ 多轮反转义处理 SDK 序列化的 JSON
        │
        ▼
  Gate 门禁（确定性规则，一票否决）
  ├─ has_contexts: found 用例必须有检索结果
  ├─ expected_doc_hit: contexts 的 doc_paths 包含期望文档
  ├─ must_use: 强制使用特定工具
  ├─ has_citation: answer 中有机器可读引用
  ├─ admits_not_found: notfound 用例明确拒答（含"没有包含"等短语）
  ├─ has_factual_claims: notfound 用例不输出事实断言
  └─ hybrid_search_used: Qdrant 用例在无 MCP 时必须失败
        │
        ▼
  质量检查（Gate 通过后）
  ├─ 答案长度 >= 50
  ├─ 关键词匹配（辅助信号）
  └─ 正确文档引用
```

## 用例分布（v4, 64 个）

- Local: 17 (exact 5 / scenario 6 / cross-lang 2 / howto 3 / multi-doc 1)
- Qdrant: 41 (Redis 20 + K8s 21, 含 HPA)
- Notfound: 6 (MongoDB/Kafka/Prometheus/Nginx/MySQL/Docker Compose)

## 基准结果

- USE_MCP=0: Local 17/17 (100%), Notfound 6/6 (100%), Qdrant 0/41 (0%) = 23/64 (35.9%)
- USE_MCP=1: Local 17/17 (100%), Notfound 6/6 (100%), Qdrant 37/41 (90%) ≈ 60/64 (93.8%)

## 关键文件

- `scripts/eval_module.py` — 评估核心: extract_contexts + gate_check + llm_judge
- `tests/e2e/test_agentic_rag_sdk.py` — E2E 测试脚本 (v4, 64 用例)
- `tests/unit/test_eval_module.py` — 评估模块单元测试 (17 tests)
- `eval/` — 评测结果目录（JSON + logs + detail.jsonl + 对比报告）

## 分析结果时的关注点

1. Gate 失败分布: 哪个 check 失败最多？
   - `未检索到期望文档` → 检索策略或索引问题
   - `无检索结果` → Agent 没调工具（可能 session 复用）
   - `未调用必需工具` → 路由策略问题
   - `notfound 用例输出了具体事实断言` → 幻觉问题

2. Source 维度:
   - local 通过率应 = 100%（Grep 直接命中）
   - qdrant 通过率取决于 USE_MCP（无 MCP 应为 0%）
   - notfound 通过率应 = 100%

3. Type 维度:
   - exact > scenario > cross-lang（难度递增）
   - concept 类需要 Qdrant 支持

4. 常见陷阱:
   - MCP 路径提取失败 → 检查 _extract_doc_paths 的转义处理
   - session 复用导致 ctx:0 → 确认每个用例独立 session
   - notfound 短语不全 → 检查 nf_phrases 列表

## 禁止行为

- 不要手动修改 eval/ 下的结果文件
- 不要在评测中使用 LLM Judge（当前阶段只用 Gate + 质量检查）
- 不要把评测结果当作绝对指标，关注趋势和失败模式
- 不要复用 session — 每个用例必须独立 session
