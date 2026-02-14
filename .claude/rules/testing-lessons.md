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

### Qdrant 索引（全量，heading-based chunking）

**K8s 英文文档 (~144 个)** — from kubernetes/website concepts:
- Workloads, Networking, Storage, Configuration, Architecture, Policy, Scheduling, Security, Overview

**Redis 英文文档 (~62 个)** — from redis/docs official:
- Data Types, Management (Sentinel, Replication, Persistence, Scaling), Security, Optimization, Develop

来源: git submodules in `tests/fixtures/kb-sources/`

### 本地 docs/（3 个技术文档）
- `runbook/redis-failover.md` — Redis Sentinel 主从切换故障恢复
- `runbook/kubernetes-pod-crashloop.md` — K8s CrashLoopBackOff 排查
- `api/authentication.md` — OAuth 2.0 + JWT API 认证设计

### 评测用例（v4, 64 个）
- Local: 17 (exact/scenario/cross-lang/howto/multi-doc)
- Qdrant: 41 (Redis 20 + K8s 21, 含 HPA)
- Notfound: 6 (MongoDB/Kafka/Prometheus/Nginx/MySQL/Docker Compose)

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
