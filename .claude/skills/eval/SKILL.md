# /eval — RAG 评测

触发: `/eval [选项]`

## 选项

- `/eval` — 默认: USE_MCP=0 跑本地 docs/ 用例
- `/eval --mcp` — USE_MCP=1 跑全量用例（含 Qdrant）
- `/eval --quick` — 只跑 5 个核心用例快速验证
- `/eval --analyze <json_file>` — 分析已有评测结果，输出改进建议
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
        │
        ▼
  Gate 门禁（确定性规则，一票否决）
  ├─ has_contexts: found 用例必须有检索结果
  ├─ expected_doc_hit: contexts 的 doc_paths 包含期望文档
  ├─ must_use: 强制使用特定工具
  ├─ has_citation: answer 中有机器可读引用
  ├─ admits_not_found: notfound 用例明确拒答
  ├─ has_factual_claims: notfound 用例不输出事实断言
  └─ hybrid_search_used: Qdrant 用例在无 MCP 时必须失败
        │
        ▼
  质量检查（Gate 通过后）
  ├─ 答案长度 >= 50
  ├─ 关键词匹配（辅助信号）
  └─ 正确文档引用
```

## 关键文件

- `scripts/eval_module.py` — 评估核心: extract_contexts + gate_check + llm_judge
- `tests/e2e/test_agentic_rag_sdk.py` — E2E 测试脚本
- `tests/unit/test_eval_module.py` — 评估模块单元测试
- `eval/` — 评测结果目录（JSON + logs + 对比报告）
- `docs/eval-review.md` — 评测方案设计文档

## 分析结果时的关注点

1. Gate 失败分布: 哪个 check 失败最多？
   - `未检索到期望文档` → 检索策略或索引问题
   - `无检索结果` → Agent 没调工具
   - `未调用必需工具` → 路由策略问题
   - `notfound 用例输出了具体事实断言` → 幻觉问题

2. Source 维度:
   - local 通过率应 > 90%（Grep 直接命中）
   - qdrant 通过率取决于 USE_MCP（无 MCP 应为 0%）
   - notfound 通过率应 = 100%

3. Type 维度:
   - exact > scenario > cross-lang（难度递增）
   - concept 类需要 Qdrant 支持

## 禁止行为

- 不要手动修改 eval/ 下的结果文件
- 不要在评测中使用 LLM Judge（当前阶段只用 Gate + 质量检查）
- 不要把评测结果当作绝对指标，关注趋势和失败模式
