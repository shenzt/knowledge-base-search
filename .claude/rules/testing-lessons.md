# 测试经验教训（重要）

## 教训 1：测试必须基于实际知识库内容

**问题**：编写了 34 个测试用例，但大量 case 问的是知识库中根本不存在的内容（如 Namespace、DaemonSet、ReplicaSet）。Claude 回答"未找到相关文档"就算通过了 — 这不是在测检索能力，是在测"能不能说不知道"。

**规则**：
- 编写测试用例前，**必须先确认知识库中实际有哪些文档**
- 运行 `.venv/bin/python scripts/index.py --status` 查看索引状态
- 查看 Qdrant 中实际索引了哪些文档和 chunks
- 测试用例的 expected_doc 必须是知识库中真实存在的文档
- "未找到"类测试不超过总用例的 10%

## 教训 2：区分知识库来源 — 本地 docs/ vs Qdrant 索引

**问题**：Qdrant 中索引了 21 个文档（来自 kb-test-k8s-en/ 和 kb-test-redis-cn/），但 Agentic RAG 测试用 Grep/Glob/Read 只搜索本地 docs/（3 个示例文档），完全绕过了真正的知识库。

**规则**：
- 本地 `docs/` 目录：项目自身文档 + 少量示例 runbook
- Qdrant 索引：真正的知识库内容（K8s 英文文档 + Redis 中文文档）
- 测试 Agentic RAG 时必须明确测试的是哪个数据源
- Layer 1 (Grep/Glob/Read) 只能搜索本地文件
- Layer 2 (MCP hybrid_search) 搜索 Qdrant 索引
- 如果测试 Layer 1，用例必须基于本地 docs/ 的实际内容
- 如果测试 Layer 2，必须启用 MCP 并基于 Qdrant 索引内容

## 教训 3：不要用"通过率 100%"自欺欺人

**问题**：测试显示 100% 通过率，但实际上是因为评估标准太宽松 — 只要答案超过 100 字符且包含 1 个关键词就算通过。对于知识库中不存在的内容，Claude 用通用知识回答也能通过。

**规则**：
- 评估必须检查是否引用了**正确的文档**（expected_doc）
- 区分"基于文档回答"和"基于模型通用知识回答"
- 对于知识库中有的内容，必须验证答案来源于具体文档
- 通过率 100% 时要反思：是测试太简单，还是真的都对了？

## 教训 4：先验证基础设施，再跑测试

**规则**：
- 跑测试前先确认：Qdrant 运行中？索引非空？MCP Server 能连接？
- 测试脚本开头应有 preflight check
- 如果依赖 MCP hybrid_search，确认 BGE-M3 模型已加载

## 教训 5：保留所有历史测试结果

**规则**：
- 所有测试用例（包括有问题的）都要保留，不要删除
- 日志中必须输出完整的 answer/result，方便事后分析
- 每次测试的 JSON 结果文件保留在 eval/ 目录
- 用 git commit 记录每次测试的变更和发现

## 当前知识库实际内容

### Qdrant 索引（2662 chunks，heading-based chunking + 预处理元数据）

**Redis 官方文档 (234 docs, ~1120 chunks)** — from redis/docs:
- Data Types, Management (Sentinel, Replication, Persistence, Scaling), Security, Optimization, Develop, Install

**awesome-llm-apps (207 docs, ~979 chunks)** — from Shubhamsaboo/awesome-llm-apps:
- RAG Tutorials, AI Agents, Chat with X, Multi-Agent, LLM Frameworks, Advanced Apps

**本地 docs/ (21 docs, ~168 chunks)**

**RAGBench techqa (245 docs, ~249 chunks)** — from rungalileo/ragbench:
- IBM 技术文档 QA，涵盖 IBM 产品技术支持文档

**CRAG finance (121 docs, ~146 chunks)** — from facebookresearch/CRAG:
- 金融领域 QA，8 种问题类型（simple, comparison, multi-hop, set, aggregation 等）

来源: 通过 /ingest-repo 或导入脚本导入，存储在 `../my-agent-kb/` 和 `docs/`
预处理: 462 docs 已完成 LLM 预处理（DeepSeek V3），sidecar 存储在 `.preprocess/` 目录

### 本地 docs/（3 个技术文档）
- `runbook/redis-failover.md` — Redis Sentinel 主从切换故障恢复
- `runbook/kubernetes-pod-crashloop.md` — K8s CrashLoopBackOff 排查
- `api/authentication.md` — OAuth 2.0 + JWT API 认证设计

### 评测用例
- v5 (100 个): Local 15 + Qdrant 75 (Redis 40 + LLM Apps 35) + Notfound 10
- RAGBench techqa (50 个): IBM 技术文档 QA，EVAL_DATASET=ragbench
- CRAG finance (50 个): 金融领域 QA，EVAL_DATASET=crag
- 全量 (200 个): EVAL_DATASET=all

### 评测结果历史

| Run | Gate | Faithfulness | Relevancy | Cost | 备注 |
|-----|------|-------------|-----------|------|------|
| R8 | 100/100 | 3.88/5 | - | - | Hard Grounding Guardrail |
| R9 | 100/100 | 4.27/5 | 4.83/5 | $11.88 | baseline |
| R10 | 100/100 | 3.94/5 | 4.76/5 | $8.72 | +预处理管线，faithfulness 在历史方差内 |

#### RAGAS + DeepSeek V3 Judge 评测（2026-02-19）

| Dataset | Run | Gate | Faithfulness | Errors | Cost | Bash | 备注 |
|---------|-----|------|-------------|--------|------|------|------|
| RAGBench | R1 (serial) | 27/50 (54%) | 0.54 | 9 | $13.50 | 21 | Agent 用 Bash pkill MCP server |
| RAGBench | R2 (concurrent) | 33/50 (66%) | 0.54 | 10 | $10.10 | 28 | setting_sources 覆盖 allowed_tools |
| RAGBench | R3 (Bash blocked) | 48/50 (96%) | 0.47 | 0 | $4.80 | 0 | ✅ 最终修复版 |
| CRAG | R1 (concurrent) | 25/50 (50%) | 0.74 | 10 | $10.55 | 27 | Bash 未封禁 |
| v5 | R11 (old) | 53/100 (53%) | 0.35 | 39 | $13.67 | 22 | Bash 未封禁 |
| CRAG | R2 | - | - | 429 | - | - | 周费用限额 $280 |
| v5 | R12 | - | - | 429 | - | - | 周费用限额 $280 |

#### GLM-5 via claude-code-router 评测（2026-02-19）

| Dataset | Model | Gate | Faithfulness | Errors | Avg Turns | Avg Time | 备注 |
|---------|-------|------|-------------|--------|-----------|----------|------|
| RAGBench | Claude Sonnet | 48/50 (96%) | 0.47 | 0 | 5.1 | 440s | baseline |
| RAGBench | GLM-5 | 50/50 (100%) | 0.54 | 0 | 8.2 | 610s | ✅ 更高 gate + faithfulness |
| CRAG | GLM-5 | 48/50 (96%) | 0.62 | 0 | 7.7 | 504s | 2 failures: 空答案 |
| v5 | GLM-5 (partial) | 43/43 (100%) | 0.44 | 57 | 5.4 | - | 57 cases hit 429 余额不足 |
| v5 | GLM-5 R13 | 88/99 (89%) | 0.49 | 2 | - | - | 1 case stuck, 9 fail (llm-fw 50%, redis-failover 50%) |
| v5 | GLM-5 R14 | 93/98 (95%) | 0.49 | 2 | - | - | llm-fw 100%, notfound 100%, 2 stuck |

GLM-5 vs Claude Sonnet 关键差异：
- Gate: GLM-5 100% vs Claude 96% — GLM-5 更严格遵循 grounding 规则
- Faithfulness: GLM-5 0.54 vs Claude 0.47 — GLM-5 回答更忠实于文档
- Turns: GLM-5 8.2 vs Claude 5.1 — GLM-5 做更多轮检索，更彻底
- Speed: GLM-5 610s vs Claude 440s — GLM-5 慢 ~40%（更多轮次 + API 延迟）
- Answer: GLM-5 1533 chars vs Claude 1020 chars — GLM-5 回答更详细
- Cost: GLM-5 ~$7.19 vs Claude $4.80（GLM-5 单价低但 token 用量多 ~1.6x）

### 评测经验教训

## 教训 6：eval_module 必须正确解析 MCP 工具结果

**问题**：MCP hybrid_search 返回的 JSON 路径经过多层转义（SDK 序列化），`_extract_doc_paths()` 无法提取，导致 gate 的 `expected_doc_hit` 全部判 False。21 个 qdrant 用例被误判为失败。

**规则**：
- MCP 工具名含连字符（如 `mcp__knowledge-base__hybrid_search`），regex 必须支持 `[\w-]+`
- ToolResultBlock 的 content 经过多层 JSON 转义，需要多轮 `replace('\\"', '"')` 反转义
- 并行工具调用（Grep + hybrid_search）必须按 `tool_use_id` 精确匹配，不能用"最近未匹配"
- 每次修改 eval_module 后，用已有 detail.jsonl 重新评分验证

## 教训 7：测试用例的 expected_doc 必须基于实际索引内容

**问题**：notfound-001 (HPA) 实际在 K8s 文档中存在（`horizontal-pod-autoscale.md`），但被标记为 notfound。

**规则**：
- 编写 notfound 用例前，先用 `hybrid_search` 确认 KB 中确实没有
- K8s concepts 文档覆盖面很广，不要想当然地认为某个概念不在 KB 中

## 教训 8：禁用 session 复用

**问题**：session 复用导致 Claude 从上下文记忆回答，跳过工具调用，`extract_contexts()` 返回空。

**规则**：
- 评测时每个用例必须独立 session（`session_id=None`）
- 确保每次查询都触发完整的工具调用链

## 教训 9：CLAUDE.md 的 KB 描述决定 Agent 是否搜索

**问题**：v5 评测中 5 个 LLM Apps 用例（chat_with_youtube, ai_travel_planner, resume_job_matcher 等）Agent 直接回答"未找到"，完全没调用任何工具。原因是 CLAUDE.md 中只列了 K8s + Redis，Agent 读到后认为 KB 没有 LLM/AI 内容，跳过了检索。

**规则**：
- CLAUDE.md 的"知识库数据源"部分必须准确反映当前 Qdrant 索引内容
- 每次 /ingest-repo 导入新数据源后，必须更新 CLAUDE.md
- Agent 会根据 CLAUDE.md 的描述决定是否值得搜索，描述不准 = 跳过检索 = 假阴性

## 教训 10：expected_doc 要用宽松匹配

**问题**：v5 评测中 5 个用例 Agent 找到了正确主题的文档，但文件名不是 expected_doc 指定的那个（如 compare-data-types.md vs hashes.md）。这是 test fixture 问题，不是检索问题。

**规则**：
- expected_doc 应该用关键路径片段而非完整文件名（如 `compare-data-types` 或 `hashes`）
- 对于"比较类"问题，expected_doc 应包含多个可能的文档
- 编写 expected_doc 前，先用 hybrid_search 确认实际会返回哪些文档

## 教训 11：RRF top-N 保护 — reranker 不可靠时的防御策略

**问题**：code-reviewer (llm-fw-004) 在 dense search 排名第 1、RRF 排名第 2，但 reranker 将其从 rank 2 降到 rank 8（score -2.68），超出 top_k=5 被截断。

**规则**：
- BGE-reranker-v2-m3 对短文档/标题匹配型查询评分不可靠
- 实现 RRF top-N 保护：RRF 排名前 3 的结果必定保留在最终输出中
- reranker 只对 RRF rank 4+ 的结果做排序，不能覆盖向量检索的强信号
- 这是 `mcp_server.py` hybrid_search 的核心防御机制

## 教训 12：LLM Judge 的 faithfulness 问题 — Agent 过度补充知识

**问题**：v5 100/100 gate 通过，但 LLM Judge 平均 score 3.83/5，20 个 case score<3。根因：Agent 检索到相关文档后，用自己的训练知识大量补充细节（命令、配置、代码示例），judge 判定为 unsupported claims。

**分布**：redis-so (9), redis-ops (5), llm-agent (2), redis-failover (2), redis-data-types (1), llm-framework (1)

**规则**：
- system prompt 必须强调"逐字逐句有据可查"，不能只说"基于文档回答"
- 如果文档只覆盖部分问题，Agent 应明确说"文档中未涉及其余内容"
- 不要编造命令/配置/代码——除非直接出现在检索到的文档中
- faithfulness 和 helpfulness 是 trade-off：严格忠实 = 更短但更可靠的回答

## 教训 13：setting_sources=["project"] 会覆盖 allowed_tools / disallowed_tools

**问题**：评测中设置了 `allowed_tools` 排除 Bash，但 Agent 仍然使用 Bash 执行 `pkill -f mcp_server.py`，导致 MCP server 被杀死，所有并发 session 全部失败。根因：`setting_sources=["project"]` 会加载 `.mcp.json` 和项目设置，完全覆盖 SDK 传入的工具限制。

**影响**：RAGBench R1/R2 各 9-10 个 error，CRAG R1 10 个 error，v5 R11 39 个 error。Agent 用 Bash 做了各种意外操作（pkill、循环搜索、写文件）。

**修复**：
- 移除 `setting_sources=["project"]`
- 改用 `system_prompt` 注入知识库描述和 Hard Grounding 规则
- 手动配置 `mcp_servers` 字典（只启动 knowledge-base MCP）
- 设置 `disallowed_tools=["Bash", "Write", "Edit", "NotebookEdit", "Task"]`

**规则**：
- 评测场景下绝对不要用 `setting_sources=["project"]`
- 用 `system_prompt` + `mcp_servers` 替代，精确控制 Agent 能力边界
- `disallowed_tools` 只在没有 `setting_sources` 时才生效
- Agent 会用 Task 工具 spawn subagent 绕过限制，Task 也要禁

**效果**：RAGBench R3 gate 从 54% → 96%，errors 从 9 → 0，cost 从 $13.50 → $4.80

## 教训 14：Benchmark 数据集的 expected_doc 不适合做硬性 gate

**问题**：RAGBench/CRAG 的 expected_doc 来自原始数据集标注，但我们的 chunking 策略（heading-based）和文档路径与原始数据集不同，导致 expected_doc 匹配率偏低。这不代表检索失败——Agent 可能找到了正确内容但路径不匹配。

**修复**：
- `eval_module.py` 中对 ragbench/crag 类别的 expected_doc miss 改为 soft signal（记录但不 fail gate）
- v5 数据集保持严格 gate（expected_doc 是我们自己标注的）

**规则**：
- 自建数据集（v5）：expected_doc 严格匹配
- 公开 benchmark（ragbench/crag）：expected_doc 仅作参考，gate 主要看 answer 质量
- 不同数据集的评估标准应该不同，不能一刀切

## 教训 15：RAGAS faithfulness 与 DeepSeek 模型兼容性

**问题**：
1. `deepseek-reasoner`（R1）不兼容 RAGAS structured output，faithfulness 返回 NaN
2. `OPENAI_API_KEY` 环境变量实际是 Claude key（`cr_*`），导致 embedding 401 错误
3. RAGAS answer_relevancy 需要 OpenAI embedding，没有真正的 OpenAI key 时应跳过

**修复**：
- Judge 模型从 `deepseek-reasoner` 改为 `deepseek-chat`（V3）
- embedding key 检测：拒绝 `cr_*` 和 `sk-ant-*` 前缀
- 无有效 OpenAI key 时 answer_relevancy 返回 None 而非报错

**规则**：
- RAGAS 的 LLM 必须支持 structured output（function calling），reasoning 模型不行
- embedding 和 LLM judge 用不同的 API key，要分别验证
- 评测脚本启动时应做 preflight check：验证所有 API key 有效

## 教训 16：并发评测的资源冲突

**问题**：两个评测进程同时启动（v5 + CRAG），共享同一个时间戳的日志文件，结果互相覆盖。

**规则**：
- 不要同时启动多个评测进程（不同 dataset），它们会竞争日志文件和 MCP server
- 同一个评测内的并发（EVAL_CONCURRENCY=5）是安全的，因为共享同一个 MCP server 进程
- 如果需要跑多个 dataset，串行执行或确保日志文件名包含 dataset 标识
- 注意 API 费用累积：5 并发 × 2 个 dataset = 10 个并发 session，容易触发费用限额

## 教训 17：claude-code-router 模型替换 — GLM-5 vs Claude Sonnet Agent 能力对比

**背景**：通过 claude-code-router 将 Agent SDK 的 Claude API 调用代理到 GLM-5（智谱 744B MoE），评测 RAGBench techqa 50 cases。

**配置**：
- Router: `ccr start`（本地代理 http://127.0.0.1:3456）
- Provider: zhipu, api_base_url=https://open.bigmodel.cn/api/paas/v4/chat/completions
- Transformer: `deepseek`（处理 reasoning_content）+ `tooluse`（优化 tool_choice）
- 评测脚本: `USE_ROUTER=1` 设置 `ANTHROPIC_BASE_URL` 走 router

**结果**：
- GLM-5: 50/50 (100%) gate, faithfulness 0.54, 0 errors
- Claude: 48/50 (96%) gate, faithfulness 0.47, 0 errors
- GLM-5 在 gate pass 和 faithfulness 上都优于 Claude Sonnet

**关键差异**：
1. **工具调用策略**：GLM-5 平均 8.2 turns vs Claude 5.1 turns — GLM-5 更倾向于多轮检索确认
2. **Grounding 遵循度**：GLM-5 更严格遵循 Hard Grounding 规则，不补充训练知识
3. **速度**：GLM-5 610s/case vs Claude 440s/case — 慢 40%（更多轮次 + API 延迟）
4. **回答详细度**：GLM-5 1533 chars vs Claude 1020 chars — 更详细但更忠实
5. **路径幻觉**：GLM-5 偶尔在 Grep 中使用文档内容里的路径（如 `/Users/kenneth/...`），但能自我纠正
6. **成本**：GLM-5 单价低（$1/$3.2 per 1M tokens vs Claude $3/$15），但 token 用量多 ~1.6x

**规则**：
- claude-code-router 可以无缝替换 Agent 模型，只需设置 `ANTHROPIC_BASE_URL`
- GLM-5 适合需要高 faithfulness 的 RAG 场景（严格 grounding）
- Claude Sonnet 适合需要快速响应的场景（更少 turns，更快）
- 评测时 `USE_ROUTER=1` 不影响当前 Claude Code session（环境变量隔离）
- Router config 在 `~/.claude-code-router/config.json`，不要提交到 git

## 教训 18：Grep 搜索污染 — eval 日志被当作知识库内容

**问题**：Agent 用 Grep 搜索关键词时，把 `eval/logs/` 下的评测日志也搜出来了（Found 137 files）。日志文件极大，Agent 尝试 Read 这些文件导致 context 爆炸和耗时暴增（单 case 1027s/17min）。Agent 甚至在回答中说"仅在 eval 日志中提及，非文档内容"。

**修复**：在 search SKILL.md 中明确限制 Grep/Glob 搜索范围为 `docs/` 和 `tests/fixtures/kb-sources/`，严禁扫描 `eval/`、`.claude/`、`.git/`、`.preprocess/`、`scripts/`。

**规则**：
- Grep 必须指定 `path` 参数，不要全仓库扫描
- 评测日志、脚本代码、git 历史不是知识库内容
- 如果 Grep 返回 >50 个文件，说明 scope 太大，需要缩小

## 教训 19：路径幻觉 — Agent 编造不存在的绝对路径

**问题**：Agent 频繁编造绝对路径调用 Read（如 `/Users/junwei/...`、`/Users/huangmpaa/...`、`/mnt/data/...`），这些路径来自预训练数据中其他开发者的机器。每次失败浪费一个 tool call turn + ~$0.5。

**修复**：在 search SKILL.md 中增加硬约束：Read 的 file_path 必须来自工具返回值（hybrid_search 的 path、Grep/Glob 的匹配路径），严禁猜测。Read 失败时用 Glob 搜索文件名。

**规则**：
- Read 路径只能来自：hybrid_search 返回的 path、Grep 命中的路径、Glob 匹配的路径
- 严禁从文档内容中提取路径去 Read（文档里的路径是示例，不是本机路径）
- Read 失败 → Glob 搜索文件名 → 再 Read，不要猜测其他路径

## 教训 20：Read 失败后强行作答 — evidence gate 缺失

**问题**：Agent 在 Read 失败、Glob 也找不到文件的情况下，仍然用 hybrid_search 返回的 chunk 片段拼凑答案并声称"Based on the retrieved documents..."。这导致 faithfulness 丢分。

**修复**：在 search SKILL.md 中增加 evidence gate：如果核心 Read 操作全部失败，必须声明证据不足，不能假装读到了完整文档。

**规则**：
- 至少成功 Read 到 1 个相关文件，才能声称"基于文档回答"
- 如果只有 chunk 片段（未 Read 完整文档），回答中必须声明"基于检索片段，可能不完整"
- Read 全部失败 → 要么重试（换路径/换查询），要么明确声明证据不足
