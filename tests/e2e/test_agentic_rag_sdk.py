#!/usr/bin/env python3
"""Agentic RAG 自动化测试 v5 — 多数据集支持

数据源: redis-docs + awesome-llm-apps + local docs/ + RAGBench techqa + CRAG finance
评估: eval_module (Gate 门禁 + RAGAS faithfulness/relevancy)

环境变量:
  EVAL_DATASET=v5|ragbench|crag|all  选择数据集（默认 v5）
  EVAL_CONCURRENCY=N                 并发数（默认 1，建议 3-5）
"""

import asyncio
import json
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from claude_agent_sdk import query, ClaudeAgentOptions

PROJECT_ROOT = Path(__file__).parent.parent.parent

# 导入评测模块
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from eval_module import extract_contexts, gate_check, get_tools_used, get_retrieved_doc_paths, get_kb_commit, llm_judge, extract_turn_timings

# 导入测试用例
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "fixtures"))
from v5_test_queries import TEST_CASES_V5, GOLDEN_CASES

# 数据集选择
EVAL_DATASET = os.environ.get("EVAL_DATASET", "v5")

if EVAL_DATASET == "ragbench":
    from ragbench_techqa_cases import RAGBENCH_TECHQA_CASES
    TEST_CASES = RAGBENCH_TECHQA_CASES
elif EVAL_DATASET == "crag":
    from crag_finance_cases import CRAG_FINANCE_CASES
    TEST_CASES = CRAG_FINANCE_CASES
elif EVAL_DATASET == "all":
    from ragbench_techqa_cases import RAGBENCH_TECHQA_CASES
    from crag_finance_cases import CRAG_FINANCE_CASES
    TEST_CASES = TEST_CASES_V5 + RAGBENCH_TECHQA_CASES + CRAG_FINANCE_CASES
elif EVAL_DATASET == "golden":
    TEST_CASES = GOLDEN_CASES
    print(f"🌟 Golden dataset: {len(TEST_CASES)} cases")
else:
    TEST_CASES = TEST_CASES_V5

# Smoke test 过滤：只跑指定 ID 的用例
_SMOKE_IDS = os.environ.get("EVAL_SMOKE_IDS", "")
if _SMOKE_IDS:
    _ids = set(_SMOKE_IDS.split(","))
    TEST_CASES = [tc for tc in TEST_CASES if tc["id"] in _ids]
    print(f"🔥 Smoke test: {len(TEST_CASES)} cases ({_SMOKE_IDS})")

# 从 v5 用例的 expected_keywords 动态构建 KEYWORD_CHECKS
KEYWORD_CHECKS = {}
for _tc in TEST_CASES:
    cat = _tc["category"]
    kws = _tc.get("expected_keywords", [])
    if cat not in KEYWORD_CHECKS:
        KEYWORD_CHECKS[cat] = list(kws)
    else:
        for kw in kws:
            if kw not in KEYWORD_CHECKS[cat]:
                KEYWORD_CHECKS[cat].append(kw)

# 是否启用 MCP（模型加载需要 15-20 分钟，可选关闭）
USE_MCP = os.environ.get("USE_MCP", "0") == "1"
# 是否启用 LLM-as-Judge（对 Gate 通过的用例做质量打分）
USE_JUDGE = os.environ.get("USE_JUDGE", "0") == "1"
# 并发数（默认 1 = 串行，建议 3-5）
EVAL_CONCURRENCY = int(os.environ.get("EVAL_CONCURRENCY", "1"))
# Router 模式：通过 claude-code-router 代理到其他模型（如 GLM-5）
# 用法: USE_ROUTER=1 ROUTER_MODEL=glm-5 （需要先 ccr start 启动 router）
# 支持模型: glm-5, qwen3.5-plus, deepseek-chat
USE_ROUTER = os.environ.get("USE_ROUTER", "0") == "1"
ROUTER_URL = os.environ.get("ROUTER_URL", "http://127.0.0.1:3456")
ROUTER_MODEL = os.environ.get("ROUTER_MODEL", "")  # 空=使用 router 默认配置
# 直连模式：Anthropic 兼容 API（如 MiniMax M2.5）
# 用法: ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic ANTHROPIC_API_KEY=sk-xxx MODEL_NAME=MiniMax-M2.5
# 无需 router，直接设置 base_url + api_key，Agent SDK 原生支持
DIRECT_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "")
DIRECT_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL_NAME = os.environ.get("MODEL_NAME", "")
USE_DIRECT = bool(DIRECT_BASE_URL and DIRECT_API_KEY)


def _switch_router_model(model_name: str):
    """动态切换 router 默认模型（修改 config.json + restart）。"""
    import json as _json
    config_path = os.path.expanduser("~/.claude-code-router/config.json")
    try:
        with open(config_path) as f:
            config = _json.load(f)
        # 找到包含该模型的 provider
        provider_name = None
        for p in config.get("Providers", []):
            if model_name in p.get("models", []):
                provider_name = p["name"]
                break
        if not provider_name:
            print(f"⚠️ 模型 {model_name} 未在 router config 中找到，跳过切换")
            return
        route = f"{provider_name},{model_name}"
        config["Router"]["default"] = route
        config["Router"]["think"] = route
        with open(config_path, "w") as f:
            _json.dump(config, f, indent=2)
        # Restart router
        os.system("ccr restart > /dev/null 2>&1")
        import time; time.sleep(3)
        print(f"✅ Router 已切换到 {route}")
    except Exception as e:
        print(f"⚠️ Router 切换失败: {e}")


if USE_DIRECT:
    # 直连模式：Anthropic 兼容 API（MiniMax 等）
    # Claude CLI 用 ANTHROPIC_AUTH_TOKEN 做 Authorization header
    os.environ["ANTHROPIC_AUTH_TOKEN"] = DIRECT_API_KEY
    os.environ.setdefault("DISABLE_COST_WARNINGS", "true")
    print(f"🔗 直连模式: {DIRECT_BASE_URL} | model={MODEL_NAME or 'default'}")
elif USE_ROUTER:
    # 设置环境变量让 Agent SDK 走 router 代理
    os.environ["ANTHROPIC_BASE_URL"] = ROUTER_URL
    os.environ["ANTHROPIC_AUTH_TOKEN"] = os.environ.get("ANTHROPIC_AUTH_TOKEN", "test")
    os.environ.setdefault("DISABLE_COST_WARNINGS", "true")
    # 如果指定了模型，动态更新 router config
    if ROUTER_MODEL:
        _switch_router_model(ROUTER_MODEL)

if USE_MCP:
    # 不使用 setting_sources=["project"]，因为它会加载 .mcp.json 并覆盖 allowed_tools
    # 改用 system_prompt 注入关键指令 + 手动配置 MCP server
    SEARCH_SYSTEM_PROMPT = """你是知识库检索助手。收到问题后，用工具检索文档，基于文档内容回答。

## 知识库目录（所有文档都在这里）

1. Redis 官方文档（294 docs，在 Qdrant 索引中）：
   - develop/: data-types/, programmability/, reference/, pubsub/, get-started/
   - operate/: management/(sentinel, security, optimization), install/, reference/
   路径示例: kb/kb-redis-docs/docs/redis-docs/develop/data-types/streams.md

2. awesome-llm-apps（207 docs，在 Qdrant 索引中）：
   - rag_tutorials/, advanced_ai_agents/, starter_ai_agents/, ai_agent_framework_crash_course/
   路径示例: kb/kb-awesome-llm-apps/docs/awesome-llm-apps/rag_tutorials/xxx/README.md

3. 本地文档（Grep 可搜索）：
   - docs/runbook/    — 运维 runbook（Redis 故障恢复、K8s 排障）
   - docs/api/        — API 设计文档（认证、授权）

4. RAGBench techqa（245 docs）、CRAG finance（119 docs）— 在 Qdrant 索引中

## 本地文件搜索范围（Grep/Glob/Read）

知识库文件只在以下目录：
- docs/runbook/    — 运维 runbook（Redis 故障恢复、K8s 排障）
- docs/api/        — API 设计文档（认证、授权）
- kb/kb-redis-docs/docs/  — Qdrant 索引的完整文档（hybrid_search 返回的 path）

正确: Grep(pattern="sentinel", path="docs/runbook/")
正确: Grep(pattern="OAuth", path="docs/api/")
正确: Read(file_path="kb/kb-redis-docs/docs/redis-docs/operate/...")  ← 来自 hybrid_search 返回的 path
错误: Grep(pattern="sentinel", path="docs/")  ← 会搜到 ragbench/crag 噪声
错误: Grep(pattern="sentinel", path=".")  ← 会搜到 tests/eval/scripts
错误: Read(file_path="docs/ragbench-techqa/...")  ← 评测数据，不是知识库
错误: Read(file_path="tests/fixtures/...")  ← 测试代码，不是知识库

## 检索方法（第一步，必须执行）

每次收到问题，立即并行调用这两个工具：

  mcp__knowledge-base__hybrid_search(query="<问题关键词>", top_k=5)
  Grep(pattern="<关键词>", path="docs/runbook/")

hybrid_search 搜索 Qdrant 索引（Redis 文档、LLM 文档等全部在这里）。
Grep 搜索本地 docs/ 子目录（仅 runbook/api 两个目录）。

Grep path 选择：
- Redis/K8s → path="docs/runbook/"
- API/OAuth → path="docs/api/"

## 扩展阅读（第二步，按需执行）

hybrid_search 返回的 path 字段是文档的实际路径，用 Read(file_path=path) 读取完整内容。
如果 chunk 只有概述缺少细节，必须 Read 完整文档。

## 检索效率

1. **见好就收**：hybrid_search 的 top-1 title/path 与问题直接相关 → Read 后，如果能引用到回答问题的关键句（定义/步骤/命令/配置）→ 直接回答。如果 Read 后只有概念没有细节，且问题是"怎么做/配置/排障" → 再搜一次补证据，或声明"文档未提供具体步骤"
2. **快速放弃**：第一次 hybrid_search 无相关结果（top-5 的 title/path 都不含问题核心词）→ 改写 query 再搜一次（换语言/提取核心名词）。第二次 top-5 title/path 仍不含核心词 → 回答"❌ 未找到"
3. **禁止循环**：连续 Grep/Glob 2 次未命中 → 必须换到 hybrid_search/keyword_search，或直接回答/notfound。禁止继续换 pattern 堆叠

## 回答规则

- 100% 基于检索到的文档内容，附引用 [来源: path]
- 严禁用训练知识补充命令/配置/代码
- 文档无相关信息 → 回答"❌ 未找到相关文档"
- 回答语言跟随查询语言

## 禁止

- 禁止 Grep(path="docs/") — 会命中 ragbench/crag 噪声文件
- 禁止 Grep(path=".") 或 Grep 不带 path — 会搜到 tests/eval/scripts
- 禁止 Grep 扫描 docs/ragbench-techqa/、docs/crag-finance/、eval/、tests/、scripts/
- 禁止 Read tests/fixtures/kb-sources/ 下的文件 — 那是测试 fixtures，不是知识库
- 禁止猜测文件路径 — Read 的路径必须来自工具返回值
- 禁止只用 Grep 不用 hybrid_search — Redis 文档不在本地 docs/ 下，只有 hybrid_search 能找到
"""
    BASE_OPTIONS = dict(
        allowed_tools=[
            "Read", "Grep", "Glob",
            "mcp__knowledge-base__hybrid_search",
            "mcp__knowledge-base__keyword_search",
            "mcp__knowledge-base__index_status",
        ],
        disallowed_tools=["Bash", "Write", "Edit", "NotebookEdit", "Task"],
        mcp_servers={
            "knowledge-base": {
                "command": sys.executable,
                "args": [str(PROJECT_ROOT / "scripts" / "mcp_server.py")],
                "env": {
                    "QDRANT_URL": os.environ.get("QDRANT_URL", "http://localhost:6333"),
                    "COLLECTION_NAME": os.environ.get("COLLECTION_NAME", "knowledge-base"),
                },
            }
        },
        system_prompt=SEARCH_SYSTEM_PROMPT,
        permission_mode="bypassPermissions",
        cwd=str(PROJECT_ROOT),
        max_turns=10,
        **({"model": MODEL_NAME} if MODEL_NAME else {}),
    )
else:
    # 无 MCP 模式：仅使用 Grep/Glob/Read（Agentic Layer 1）
    # 注意：不能用 setting_sources=["project"]，否则会加载 .mcp.json 启动 MCP server
    # 改用 system_prompt 注入 CLAUDE.md 和 search skill 的关键指令
    BASE_OPTIONS = dict(
        allowed_tools=["Read", "Grep", "Glob"],
        disallowed_tools=["Bash", "Write", "Edit", "NotebookEdit", "Task"],
        permission_mode="bypassPermissions",
        cwd=str(PROJECT_ROOT),
        max_turns=10,
        system_prompt="""你是一个知识库检索助手。用户会用 /search 命令查询知识库。

知识库文档在 docs/ 目录下，格式为 Markdown，包含 Redis、LLM/AI 应用开发等技术文档。
Qdrant 向量索引包含 redis-docs（234 docs）和 awesome-llm-apps（207 docs）。

核心流程：搜索 → 评估 → 扩展 → 回答

1. 初始检索：使用 Grep 搜索关键词 + hybrid_search 语义检索（可并行）
2. 评估 chunk 充分性：chunk 是否包含具体步骤/命令/配置/代码？还是只有概述？
3. 扩展上下文：如果 chunk 不充分，用 Read(path) 读取 hybrid_search 返回的 path 字段指向的完整文件
4. 基于证据回答，必须带引用 [来源: docs/xxx.md]

⚠️ Hard Grounding（最重要的规则）：
- 你的回答必须 100% 基于检索到的文档内容，逐字逐句有据可查
- 严禁用你自己的训练知识补充命令、配置、代码示例、参数说明、最佳实践
- 如果 chunk 只有概述级别内容，必须 Read(path) 获取完整文档再回答
- 如果 Read 后文档仍然只有概念描述没有具体命令/配置/代码，你必须：
  1. 回答文档中实际包含的内容
  2. 明确声明："⚠️ 文档中提到了 [概念]，但未提供具体的 [命令/配置/代码示例]。如需详细信息，请参考官方文档。"
  3. 绝对不要自己补充缺失的命令/配置/代码
- 如果文档中完全没有相关信息，只回答"❌ 未找到相关文档"
- 宁可回答不完整，也不要编造任何细节
- 回答语言跟随查询语言（中文问中文答，英文问英文答）
- 引用具体文档路径
""",
    )


def log(msg: str, log_file=None):
    """同时输出到 stdout 和日志文件"""
    print(msg, flush=True)
    if log_file:
        log_file.write(msg + "\n")
        log_file.flush()


async def run_query(prompt: str, session_id: Optional[str], log_file) -> Dict[str, Any]:
    """执行单个查询，完整记录中间过程"""
    start = time.time()
    answer = ""
    new_session_id = session_id
    cost = 0.0
    num_turns = 0
    tools_used = []
    messages_log = []  # 完整消息日志

    try:
        if session_id:
            opts = ClaudeAgentOptions(
                resume=session_id,
                permission_mode="bypassPermissions",
                max_turns=10,
            )
        else:
            opts = ClaudeAgentOptions(**BASE_OPTIONS)

        async for msg in query(prompt=prompt, options=opts):
            # 记录每条消息的完整信息
            msg_dict = {}
            for attr in ["type", "subtype", "role", "result", "session_id",
                         "cost_usd", "num_turns", "tool_name", "tool_input",
                         "tool_result", "content", "text", "data",
                         "stop_reason", "duration_ms", "total_cost_usd",
                         "usage", "modelUsage", "permission_denials"]:
                val = getattr(msg, attr, None)
                if val is not None:
                    try:
                        json.dumps(val)  # 确保可序列化
                        msg_dict[attr] = val
                    except (TypeError, ValueError):
                        msg_dict[attr] = str(val)

            messages_log.append(msg_dict)

            # 详细日志输出 - 解析 SDK 消息结构
            subtype = getattr(msg, "subtype", None)
            content = getattr(msg, "content", None)

            if subtype == "init":
                data = getattr(msg, "data", {}) or {}
                if isinstance(data, dict):
                    new_session_id = data.get("session_id", new_session_id)
                    model = data.get("model", "unknown")
                    log(f"    [INIT] session={new_session_id} model={model}", log_file)
                if hasattr(msg, "session_id"):
                    new_session_id = msg.session_id

            elif subtype == "success":
                # 最终结果
                if hasattr(msg, "result"):
                    answer = msg.result if isinstance(msg.result, str) else str(msg.result)
                num_turns = getattr(msg, "num_turns", num_turns)
                cost = getattr(msg, "total_cost_usd", cost) or cost
                duration = getattr(msg, "duration_ms", 0)
                log(f"    [RESULT] {len(answer)} chars | {num_turns} turns | {duration}ms", log_file)

            elif content:
                # 解析 content blocks（TextBlock, ToolUseBlock, ToolResultBlock）
                if isinstance(content, list):
                    for block in content:
                        block_type = getattr(block, "type", None)
                        if block_type is None and isinstance(block, dict):
                            block_type = block.get("type", "")

                        if block_type == "text" or (hasattr(block, "text") and not hasattr(block, "name") and not hasattr(block, "tool_use_id")):
                            # TextBlock - Claude 的推理/回复
                            text = getattr(block, "text", "") if hasattr(block, "text") else block.get("text", "")
                            if text:
                                # 多行文本截断显示
                                lines = text.strip().split("\n")
                                preview = lines[0][:200]
                                if len(lines) > 1:
                                    preview += f" (+{len(lines)-1} lines)"
                                log(f"    [THINK] {preview}", log_file)

                        elif block_type == "tool_use" or hasattr(block, "name"):
                            # ToolUseBlock - 工具调用
                            tool_name = getattr(block, "name", "unknown")
                            tool_input = getattr(block, "input", {})
                            if isinstance(tool_input, dict):
                                input_str = json.dumps(tool_input, ensure_ascii=False)
                            else:
                                input_str = str(tool_input)
                            if len(input_str) > 300:
                                input_str = input_str[:300] + "..."
                            log(f"    [TOOL] {tool_name}({input_str})", log_file)
                            tools_used.append(tool_name)

                        elif block_type == "tool_result" or hasattr(block, "tool_use_id"):
                            # ToolResultBlock - 工具返回
                            result_content = getattr(block, "content", "")
                            if isinstance(result_content, str):
                                # 截断长结果，保留关键信息
                                lines = result_content.strip().split("\n")
                                if len(lines) > 5:
                                    preview = "\n".join(lines[:3]) + f"\n    ... ({len(lines)} lines total)"
                                else:
                                    preview = result_content[:400]
                                log(f"    [TOOL_OUT] {preview}", log_file)
                            elif isinstance(result_content, list):
                                for rc in result_content:
                                    rc_text = getattr(rc, "text", str(rc)) if hasattr(rc, "text") else str(rc)
                                    log(f"    [TOOL_OUT] {rc_text[:300]}", log_file)

            # 提取元数据
            if hasattr(msg, "cost_usd") and msg.cost_usd:
                cost = msg.cost_usd
            if hasattr(msg, "total_cost_usd") and msg.total_cost_usd:
                cost = msg.total_cost_usd
            if hasattr(msg, "num_turns") and msg.num_turns:
                num_turns = msg.num_turns

            # 检查 permission denials
            denials = getattr(msg, "permission_denials", None)
            if denials:
                for d in denials:
                    tool = d.get("tool_name", "unknown") if isinstance(d, dict) else str(d)
                    log(f"    [DENIED] {tool}", log_file)

        elapsed = time.time() - start
        return {
            "status": "success",
            "answer": answer,
            "session_id": new_session_id,
            "elapsed": elapsed,
            "cost_usd": cost,
            "num_turns": num_turns,
            "tools_used": tools_used,
            "messages_log": messages_log,
        }
    except Exception as e:
        elapsed = time.time() - start
        log(f"    [ERROR] {e}", log_file)
        return {
            "status": "error",
            "error": str(e),
            "session_id": new_session_id,
            "elapsed": elapsed,
            "messages_log": messages_log,
        }


def evaluate(tc: Dict, result: Dict) -> Dict:
    """两阶段评估: Gate 门禁 (确定性) → 关键词质量检查 (辅助)。"""
    ev = {"passed": False, "reasons": [], "quality": {}, "gate": {}}

    if result["status"] != "success":
        ev["reasons"].append(f"执行失败: {result.get('error', '')[:80]}")
        return ev

    answer = result.get("answer", "")
    messages_log = result.get("messages_log", [])

    # ── Stage 1: 结构化 context 提取 ──
    contexts = extract_contexts(messages_log)
    ev["quality"]["contexts_count"] = len(contexts)
    ev["quality"]["tools_used"] = get_tools_used(contexts)
    ev["quality"]["retrieved_paths"] = get_retrieved_doc_paths(contexts)

    # ── Stage 1.5: Per-turn timing ──
    turn_timings = extract_turn_timings(messages_log)
    ev["quality"]["turn_timings"] = turn_timings

    # ── Stage 2: Gate 门禁 ──
    gate = gate_check(tc, answer, contexts)
    ev["gate"] = gate

    if not gate["passed"]:
        ev["passed"] = False
        ev["reasons"] = gate["reasons"]
        return ev

    # ── Stage 3: 质量检查 (Gate 通过后的辅助指标) ──
    if len(answer) < 50:
        ev["reasons"].append(f"答案过短 ({len(answer)})")
        return ev

    # 引用质量 (从 gate 获取)
    ev["quality"]["has_citation"] = gate["checks"].get("has_citation", False)

    # 关键词匹配 (辅助信号，不作为 pass/fail 判据)
    expected = KEYWORD_CHECKS.get(tc["category"], [])
    matched = [k for k in expected if k.lower() in answer.lower()]
    ev["quality"]["keywords"] = matched

    # 正确文档引用 (从 gate 的 expected_doc_hit 获取)
    ev["quality"]["correct_doc"] = gate["checks"].get("expected_doc_hit", None)

    # Gate 通过 + 答案足够长 → 通过
    if len(answer) >= 50:
        ev["passed"] = True
    else:
        ev["reasons"].append(f"答案过短 ({len(answer)})")
        return ev

    # ── Stage 4: LLM-as-Judge (可选，Gate 通过后) ──
    if USE_JUDGE and ev["passed"] and not tc.get("source") == "notfound":
        gold_answer = tc.get("reference_answer")
        judge = llm_judge(tc["query"], answer, contexts, gold_answer=gold_answer)
        ev["quality"]["judge"] = judge
        # Judge score < 2 视为质量不合格（但不改变 pass/fail）
        if judge.get("score", -1) >= 0:
            ev["quality"]["judge_score"] = judge["score"]
            ev["quality"]["faithfulness"] = judge.get("faithfulness", -1)
            ev["quality"]["relevancy"] = judge.get("relevancy", -1)
            ev["quality"]["context_precision"] = judge.get("context_precision", -1)
            ev["quality"]["context_recall"] = judge.get("context_recall", -1)
            ev["quality"]["answer_correctness"] = judge.get("answer_correctness", -1)

    return ev


async def run_single_case(i: int, tc: Dict, sem: asyncio.Semaphore,
                          results_slot: list, log_lock: threading.Lock,
                          lf, df) -> None:
    """执行单个测试用例（并发安全）。"""
    async with sem:
        case_log = []  # 缓冲日志，完成后一次性写入

        def clog(msg):
            case_log.append(msg)

        clog(f"\n{'='*60}")
        clog(f"[{i}/{len(TEST_CASES)}] {tc['id']} ({tc['category']}) [{tc.get('type', '?')}]")
        clog(f"  Q: {tc['query']}")
        if tc.get("note"):
            clog(f"  💡 {tc['note']}")
        clog(f"  开始: {datetime.now().strftime('%H:%M:%S')}")

        # 每个用例独立 session，不复用
        prompt = f"请检索知识库并回答: {tc['query']}"

        # run_query 内部的实时日志用 None（不写文件），靠 case_log 缓冲
        import io
        buf = io.StringIO()

        class BufWriter:
            def write(self, s): buf.write(s)
            def flush(self): pass

        # 单次 call 超时保护（防止 API hang 住，如 Kimi K2.5 case 16）
        QUERY_TIMEOUT = int(os.environ.get("EVAL_QUERY_TIMEOUT", "300"))  # 默认 5 分钟
        try:
            result = await asyncio.wait_for(
                run_query(prompt, None, BufWriter()),
                timeout=QUERY_TIMEOUT,
            )
        except asyncio.TimeoutError:
            result = {
                "status": "error",
                "error": f"TimeoutError: query exceeded {QUERY_TIMEOUT}s",
                "answer": "",
                "session_id": None,
                "cost_usd": 0,
                "num_turns": 0,
                "elapsed": QUERY_TIMEOUT,
                "messages": [],
            }
            clog(f"  ⏰ 超时: query 超过 {QUERY_TIMEOUT}s，跳过")

        # 追加 run_query 的详细日志
        detail_lines = buf.getvalue()
        if detail_lines:
            case_log.append(detail_lines.rstrip())

        elapsed = result.get("elapsed", 0)
        ev = evaluate(tc, result)

        if result["status"] == "error":
            clog(f"  ❌ 错误: {result.get('error', '')[:80]}")
            status = "error"
        elif ev["passed"]:
            ans_len = len(result.get("answer", ""))
            quality = ev.get("quality", {})
            tools = quality.get("tools_used", [])
            cite = "引用✅" if quality.get("has_citation") else "引用❌"
            correct_doc = quality.get("correct_doc")
            doc_tag = "文档✅" if correct_doc else ("文档❌" if correct_doc is False else "")
            ctx_count = quality.get("contexts_count", 0)
            kw = quality.get("keywords", [])
            clog(f"  ✅ 通过 | {ans_len}字符 | {elapsed:.1f}s | ${result.get('cost_usd', 0):.4f} | {cite} {doc_tag} | ctx:{ctx_count}")
            if tools:
                clog(f"  🔧 工具: {', '.join(tools)}")
            if quality.get("retrieved_paths"):
                clog(f"  📄 检索: {', '.join(quality['retrieved_paths'][:5])}")
            if kw:
                clog(f"  🔑 关键词: {', '.join(kw)}")
            if quality.get("judge_score") is not None:
                js = quality["judge_score"]
                ff = quality.get("faithfulness", "?")
                rr = quality.get("relevancy", "?")
                clog(f"  🧑‍⚖️ Judge: score={js} faith={ff} rel={rr}")
            status = "passed"
        else:
            clog(f"  ❌ 失败: {'; '.join(ev['reasons'])}")
            status = "failed"

        ans_preview = result.get("answer", "")[:500]
        if ans_preview:
            clog(f"  📝 答案: {ans_preview}{'...' if len(result.get('answer',''))>500 else ''}")
        clog(f"  结束: {datetime.now().strftime('%H:%M:%S')} | 耗时: {elapsed:.1f}s")
        clog("-" * 80)

        # 构建结果
        gate = ev.get("gate", {})
        quality = ev.get("quality", {})
        detail_record = {
            "test_id": tc["id"],
            "category": tc["category"],
            "type": tc.get("type", "unknown"),
            "source": tc.get("source", "unknown"),
            "query": tc["query"],
            "status": status,
            "elapsed_seconds": elapsed,
            "cost_usd": result.get("cost_usd", 0),
            "num_turns": result.get("num_turns", 0),
            "answer_length": len(result.get("answer", "")),
            "answer": result.get("answer", ""),
            "tools_used": quality.get("tools_used", []),
            "retrieved_paths": quality.get("retrieved_paths", []),
            "contexts_count": quality.get("contexts_count", 0),
            "has_citation": quality.get("has_citation", False),
            "correct_doc": quality.get("correct_doc"),
            "matched_keywords": quality.get("keywords", []),
            "gate_passed": gate.get("passed"),
            "gate_checks": gate.get("checks", {}),
            "failure_reasons": ev.get("reasons", []),
            "judge_score": quality.get("judge_score"),
            "faithfulness": quality.get("faithfulness"),
            "relevancy": quality.get("relevancy"),
            "context_precision": quality.get("context_precision"),
            "context_recall": quality.get("context_recall"),
            "answer_correctness": quality.get("answer_correctness"),
            "judge": quality.get("judge"),
            "turn_timings": quality.get("turn_timings", []),
            "messages": result.get("messages_log", []),
        }

        summary_record = {
            "test_id": tc["id"], "category": tc["category"],
            "type": tc.get("type", "unknown"),
            "source": tc.get("source", "unknown"),
            "query": tc["query"],
            "status": status, "elapsed_seconds": elapsed,
            "cost_usd": result.get("cost_usd", 0),
            "num_turns": result.get("num_turns", 0),
            "answer_length": len(result.get("answer", "")),
            "tools_used": quality.get("tools_used", []),
            "retrieved_paths": quality.get("retrieved_paths", []),
            "contexts_count": quality.get("contexts_count", 0),
            "has_citation": quality.get("has_citation", False),
            "correct_doc": quality.get("correct_doc"),
            "matched_keywords": quality.get("keywords", []),
            "gate_passed": gate.get("passed"),
            "failure_reasons": ev.get("reasons", []),
            "answer_preview": result.get("answer", "")[:300],
            "judge_score": quality.get("judge_score"),
            "faithfulness": quality.get("faithfulness"),
            "relevancy": quality.get("relevancy"),
            "context_precision": quality.get("context_precision"),
            "context_recall": quality.get("context_recall"),
            "answer_correctness": quality.get("answer_correctness"),
            "turn_timings": quality.get("turn_timings", []),
        }

        # 线程安全写入日志和结果
        with log_lock:
            for line in case_log:
                log(line, lf)
            df.write(json.dumps(detail_record, ensure_ascii=False) + "\n")
            df.flush()

        # 存入对应 slot（保持顺序）
        results_slot[i - 1] = summary_record


async def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = PROJECT_ROOT / "eval" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"agentic_rag_{timestamp}.log"
    detail_path = log_dir / f"agentic_rag_{timestamp}_detail.jsonl"

    with open(log_path, "w", encoding="utf-8") as lf, \
         open(detail_path, "w", encoding="utf-8") as df:

        mode = "MCP + Grep/Glob/Read" if USE_MCP else "Grep/Glob/Read (无 MCP)"
        model_info = f"direct → {MODEL_NAME or 'default'} ({DIRECT_BASE_URL})" if USE_DIRECT else (f"via router → {ROUTER_MODEL or 'default'} ({ROUTER_URL})" if USE_ROUTER else "Claude (direct)")
        kb_commit_header = get_kb_commit()
        log("=" * 80, lf)
        log(f"🤖 Agentic RAG 测试 (Agent SDK)", lf)
        log("=" * 80, lf)
        log(f"用例: {len(TEST_CASES)} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", lf)
        log(f"模式: {mode}", lf)
        log(f"模型: {model_info}", lf)
        log(f"并发: {EVAL_CONCURRENCY}", lf)
        log(f"KB commit: {kb_commit_header}", lf)
        log(f"评估: eval_module (Gate 门禁 + 质量检查)", lf)
        log(f"策略: Claude 自主选择检索策略 (Grep/Glob/Read{' + MCP hybrid_search' if USE_MCP else ''})", lf)
        log(f"日志: {log_path}", lf)
        log(f"详细: {detail_path}", lf)
        log("", lf)

        # 预分配结果 slot（保持顺序）
        results_slot = [None] * len(TEST_CASES)
        sem = asyncio.Semaphore(EVAL_CONCURRENCY)
        log_lock = threading.Lock()

        # 并发执行所有用例
        tasks = [
            run_single_case(i, tc, sem, results_slot, log_lock, lf, df)
            for i, tc in enumerate(TEST_CASES, 1)
        ]
        await asyncio.gather(*tasks)

        # 收集结果
        results = [r for r in results_slot if r is not None]
        passed = sum(1 for r in results if r["status"] == "passed")
        failed = sum(1 for r in results if r["status"] == "failed")
        errors = sum(1 for r in results if r["status"] == "error")
        total_time = sum(r["elapsed_seconds"] for r in results)
        total_cost = sum(r["cost_usd"] for r in results)

        # 总结
        total = len(TEST_CASES)
        log(f"\n{'=' * 80}", lf)
        log(f"📊 总结: ✅{passed} ❌{failed} ⚠️{errors} / {total} ({passed/total*100:.1f}%)", lf)
        log(f"⏱️  总耗时: {total_time:.1f}s | 平均: {total_time/max(passed+failed,1):.1f}s", lf)
        log(f"💰 总费用: ${total_cost:.4f}", lf)

        # 速度统计: avg/p50/p95 latency
        elapsed_list = sorted([r["elapsed_seconds"] for r in results if r["elapsed_seconds"] > 0])
        if elapsed_list:
            avg_latency = sum(elapsed_list) / len(elapsed_list)
            p50_idx = max(0, int(len(elapsed_list) * 0.5) - 1)
            p95_idx = max(0, int(len(elapsed_list) * 0.95) - 1)
            p50_latency = elapsed_list[p50_idx]
            p95_latency = elapsed_list[p95_idx]
            min_latency = elapsed_list[0]
            max_latency = elapsed_list[-1]
            log(f"⏱️  延迟: avg={avg_latency:.1f}s | p50={p50_latency:.1f}s | p95={p95_latency:.1f}s | min={min_latency:.1f}s | max={max_latency:.1f}s", lf)

        # 按查询类型统计
        type_stats = {}
        for r in results:
            qtype = r.get("type", "unknown")
            type_stats.setdefault(qtype, {"t": 0, "p": 0})
            type_stats[qtype]["t"] += 1
            if r["status"] == "passed": type_stats[qtype]["p"] += 1

        log("", lf)
        log("📈 按查询类型:", lf)
        type_labels = {
            "exact": "精确匹配(Grep擅长)",
            "scenario": "SO场景/症状描述",
            "cross-lang": "跨语言",
            "howto": "实操问答",
            "multi-doc": "多文档综合",
            "concept": "概念型(需Qdrant)",
            "notfound": "未收录",
        }
        for t, s in sorted(type_stats.items()):
            r2 = s["p"]/s["t"]*100
            label = type_labels.get(t, t)
            log(f"  {'✅' if r2==100 else '⚠️' if r2>0 else '❌'} {label}: {s['p']}/{s['t']} ({r2:.0f}%)", lf)

        log("", lf)
        log("📋 按 category:", lf)
        cats = {}
        for r in results:
            c = r["category"]
            cats.setdefault(c, {"t": 0, "p": 0})
            cats[c]["t"] += 1
            if r["status"] == "passed": cats[c]["p"] += 1
        for c, s in sorted(cats.items()):
            r2 = s["p"]/s["t"]*100
            log(f"  {'✅' if r2==100 else '⚠️' if r2>0 else '❌'} {c}: {s['p']}/{s['t']} ({r2:.0f}%)", lf)

        # 按数据源统计
        source_stats = {}
        for r in results:
            src = r.get("source", "unknown")
            source_stats.setdefault(src, {"t": 0, "p": 0})
            source_stats[src]["t"] += 1
            if r["status"] == "passed": source_stats[src]["p"] += 1

        log("", lf)
        log("📈 按数据源:", lf)
        source_labels = {
            "local": "本地 docs/ (Grep/Glob/Read)",
            "qdrant": "Qdrant 索引 (MCP hybrid_search)",
            "notfound": "未收录 (应拒答)",
        }
        for src, s in sorted(source_stats.items()):
            r2 = s["p"]/s["t"]*100
            label = source_labels.get(src, src)
            icon = "✅" if r2 == 100 else ("⚠️" if r2 > 0 else "❌")
            log(f"  {icon} {label}: {s['p']}/{s['t']} ({r2:.0f}%)", lf)

        if not USE_MCP and source_stats.get("qdrant", {}).get("t", 0) > 0:
            qdrant_total = source_stats["qdrant"]["t"]
            qdrant_pass = source_stats["qdrant"]["p"]
            log(f"\n  ⚠️  注意: {qdrant_total} 个 Qdrant 用例在无 MCP 模式下运行", lf)
            log(f"     通过 {qdrant_pass}/{qdrant_total} — 可能是 Claude 用通用知识回答（非检索）", lf)
            log(f"     设置 USE_MCP=1 启用 hybrid_search 以测试真正的向量检索", lf)

        # ── Early Stopping 观测指标（纯后处理，不影响 Agent 行为）──
        def _compute_early_stop_metrics(r):
            """从 turn_timings 统计检索效率指标。"""
            timings = r.get("turn_timings", [])
            tools = r.get("tools_used", [])

            # search_calls: hybrid_search 调用次数
            search_calls = sum(1 for t in tools if "hybrid_search" in t)

            # max_consecutive_same_tool: 最大连续同工具次数（Read 不同文件豁免）
            max_consec = 1
            cur_consec = 1
            for j in range(1, len(tools)):
                t_cur = tools[j]
                t_prev = tools[j - 1]
                if t_cur == t_prev:
                    # Read 不同文件豁免：检查 turn_timings 中的 tool_input
                    if t_cur == "Read" and j < len(timings) and j - 1 < len(timings):
                        path_cur = timings[j].get("tool_input", {}).get("file_path", "") if isinstance(timings[j].get("tool_input"), dict) else ""
                        path_prev = timings[j-1].get("tool_input", {}).get("file_path", "") if isinstance(timings[j-1].get("tool_input"), dict) else ""
                        if path_cur != path_prev:
                            cur_consec = 1
                            continue
                    cur_consec += 1
                    max_consec = max(max_consec, cur_consec)
                else:
                    cur_consec = 1

            # stop_reason: 从结果推断
            num_turns = r.get("num_turns", 0)
            status = r.get("status", "")
            answer = r.get("answer_preview", "") or ""
            if num_turns >= 10:
                stop_reason = "max_turns_reached"
            elif "❌" in answer and ("未找到" in answer or "not found" in answer.lower()):
                stop_reason = "notfound_quick" if num_turns <= 4 else "notfound_slow"
            elif search_calls <= 1 and num_turns <= 4:
                stop_reason = "hit_first_search"
            elif max_consec >= 3:
                stop_reason = "loop_detected"
            else:
                stop_reason = "normal"

            return {
                "search_calls": search_calls,
                "max_consecutive_same_tool": max_consec,
                "stop_reason": stop_reason,
            }

        # 计算每个 case 的 early stop 指标
        for r in results:
            r["early_stop"] = _compute_early_stop_metrics(r)

        # 汇总 early stop 统计
        stop_reasons = {}
        all_search_calls = []
        all_max_consec = []
        for r in results:
            es = r.get("early_stop", {})
            reason = es.get("stop_reason", "unknown")
            stop_reasons[reason] = stop_reasons.get(reason, 0) + 1
            all_search_calls.append(es.get("search_calls", 0))
            all_max_consec.append(es.get("max_consecutive_same_tool", 0))

        avg_search = sum(all_search_calls) / max(len(all_search_calls), 1)
        avg_consec = sum(all_max_consec) / max(len(all_max_consec), 1)

        # Turns 统计
        all_turns = [r.get("num_turns", 0) for r in results if r.get("num_turns", 0) > 0]
        avg_turns = sum(all_turns) / max(len(all_turns), 1)
        high_turn_cases = [r for r in results if r.get("num_turns", 0) >= 7]

        log("", lf)
        log("🔍 检索效率 (Early Stopping):", lf)
        log(f"  avg turns: {avg_turns:.1f} | avg search_calls: {avg_search:.1f} | avg max_consec_same_tool: {avg_consec:.1f}", lf)
        log(f"  stop_reasons: {json.dumps(stop_reasons, ensure_ascii=False)}", lf)
        if high_turn_cases:
            log(f"  ⚠️ 高 turn cases (≥7): {len(high_turn_cases)}", lf)
            for r in sorted(high_turn_cases, key=lambda x: -x.get("num_turns", 0))[:5]:
                log(f"    - {r['test_id']}: {r.get('num_turns', 0)} turns | {r.get('elapsed_seconds', 0):.0f}s | {r.get('early_stop', {}).get('stop_reason', '?')}", lf)

        # LLM Judge 统计
        if USE_JUDGE:
            judge_scores = [r.get("judge_score") for r in results
                           if r.get("judge_score") is not None]
            if judge_scores:
                avg_score = sum(judge_scores) / len(judge_scores)
                faith_vals = [r.get("faithfulness", 0) for r in results
                              if r.get("faithfulness") is not None and r.get("faithfulness", -1) >= 0]
                rel_vals = [r.get("relevancy", 0) for r in results
                            if r.get("relevancy") is not None and r.get("relevancy", -1) >= 0]
                ctx_prec_vals = [r.get("context_precision", 0) for r in results
                                 if r.get("context_precision") is not None and r.get("context_precision", -1) >= 0]
                ctx_rec_vals = [r.get("context_recall", 0) for r in results
                                if r.get("context_recall") is not None and r.get("context_recall", -1) >= 0]
                correct_vals = [r.get("answer_correctness", 0) for r in results
                                if r.get("answer_correctness") is not None and r.get("answer_correctness", -1) >= 0]
                avg_faith = sum(faith_vals) / max(len(faith_vals), 1)
                avg_rel = sum(rel_vals) / max(len(rel_vals), 1)
                low_quality = [r for r in results if r.get("judge_score") is not None and r["judge_score"] < 3]
                log("", lf)
                log(f"🧑‍⚖️ LLM Judge ({len(judge_scores)} cases):", lf)
                log(f"  平均 score: {avg_score:.2f}/5 | faithfulness: {avg_faith:.3f} | relevancy: {avg_rel:.3f}", lf)
                if ctx_prec_vals:
                    avg_ctx_prec = sum(ctx_prec_vals) / len(ctx_prec_vals)
                    log(f"  context_precision: {avg_ctx_prec:.3f} ({len(ctx_prec_vals)} cases with reference_answer)", lf)
                if ctx_rec_vals:
                    avg_ctx_rec = sum(ctx_rec_vals) / len(ctx_rec_vals)
                    log(f"  context_recall: {avg_ctx_rec:.3f} ({len(ctx_rec_vals)} cases with reference_answer)", lf)
                if correct_vals:
                    avg_correct = sum(correct_vals) / len(correct_vals)
                    log(f"  answer_correctness: {avg_correct:.3f} ({len(correct_vals)} cases with reference_answer)", lf)
                if low_quality:
                    log(f"  ⚠️ 低质量 (score<3): {len(low_quality)} 个", lf)
                    for r in low_quality[:5]:
                        log(f"    - {r['test_id']}: score={r['judge_score']} {r.get('query', '')[:40]}", lf)

        # ── 质量指标（独立于 gate，衡量回答质量）──
        # 只统计 gate_passed=True 且有 judge 分数的 case
        judged_results = [r for r in results if r.get("gate_passed") and r.get("faithfulness") is not None]
        if judged_results:
            faith_ge_05 = sum(1 for r in judged_results if (r.get("faithfulness") or 0) >= 0.5)
            judge_ge_3 = sum(1 for r in judged_results if (r.get("judge_score") or 0) >= 3.0)
            pct_faith = faith_ge_05 / len(judged_results) * 100
            pct_judge = judge_ge_3 / len(judged_results) * 100
            log("", lf)
            log(f"📊 质量指标 ({len(judged_results)} judged cases):", lf)
            log(f"  pct_faith_ge_05: {faith_ge_05}/{len(judged_results)} ({pct_faith:.1f}%)", lf)
            log(f"  pct_judge_ge_3:  {judge_ge_3}/{len(judged_results)} ({pct_judge:.1f}%)", lf)
        else:
            pct_faith = None
            pct_judge = None

        # ── 越界检测（boundary violation）──
        BOUNDARY_PREFIXES = [
            "tests/", "eval/", "scripts/",
            "docs/ragbench-techqa/", "docs/crag-finance/", "docs/archive/",
        ]
        BOUNDARY_PATTERNS = [
            "docs/design", "docs/dual-", "docs/e2e-", "docs/eval-", "docs/progress-",
        ]
        boundary_violations = []
        for r in results:
            paths = r.get("retrieved_paths", [])
            violated_paths = []
            for p in paths:
                for prefix in BOUNDARY_PREFIXES:
                    if p.startswith(prefix) or f"/{prefix}" in p:
                        violated_paths.append(p)
                        break
                else:
                    for pat in BOUNDARY_PATTERNS:
                        if pat in p:
                            violated_paths.append(p)
                            break
            if violated_paths:
                r["boundary_violation"] = True
                r["violated_paths"] = violated_paths
                boundary_violations.append(r)
            else:
                r["boundary_violation"] = False

        if boundary_violations:
            log("", lf)
            log(f"⚠️  越界检测: {len(boundary_violations)} cases 访问了非知识库路径:", lf)
            for r in boundary_violations:
                log(f"  - {r['test_id']}: {r.get('violated_paths', [])[:3]}", lf)

        # 保存汇总 JSON
        kb_commit = get_kb_commit()
        out_dir = PROJECT_ROOT / "eval"
        out_file = out_dir / f"agentic_rag_v5_{timestamp}.json"

        # Judge 汇总
        judge_summary = {}
        if USE_JUDGE:
            judge_scores = [r.get("judge_score") for r in results
                           if r.get("judge_score") is not None]
            if judge_scores:
                faith_vals = [r.get("faithfulness") for r in results
                              if r.get("faithfulness") is not None and r.get("faithfulness", -1) >= 0]
                rel_vals = [r.get("relevancy") for r in results
                            if r.get("relevancy") is not None and r.get("relevancy", -1) >= 0]
                ctx_prec_vals = [r.get("context_precision") for r in results
                                 if r.get("context_precision") is not None and r.get("context_precision", -1) >= 0]
                ctx_rec_vals = [r.get("context_recall") for r in results
                                if r.get("context_recall") is not None and r.get("context_recall", -1) >= 0]
                correct_vals = [r.get("answer_correctness") for r in results
                                if r.get("answer_correctness") is not None and r.get("answer_correctness", -1) >= 0]
                judge_summary = {
                    "count": len(judge_scores),
                    "avg_score": round(sum(judge_scores) / len(judge_scores), 2),
                    "avg_faithfulness": round(sum(faith_vals) / max(len(faith_vals), 1), 3) if faith_vals else None,
                    "avg_relevancy": round(sum(rel_vals) / max(len(rel_vals), 1), 3) if rel_vals else None,
                    "avg_context_precision": round(sum(ctx_prec_vals) / len(ctx_prec_vals), 3) if ctx_prec_vals else None,
                    "avg_context_recall": round(sum(ctx_rec_vals) / len(ctx_rec_vals), 3) if ctx_rec_vals else None,
                    "avg_answer_correctness": round(sum(correct_vals) / len(correct_vals), 3) if correct_vals else None,
                    "low_quality_count": sum(1 for s in judge_scores if s < 3),
                }

        # 速度汇总
        speed_summary = {}
        if elapsed_list:
            speed_summary = {
                "avg_seconds": round(avg_latency, 1),
                "p50_seconds": round(p50_latency, 1),
                "p95_seconds": round(p95_latency, 1),
                "min_seconds": round(min_latency, 1),
                "max_seconds": round(max_latency, 1),
            }

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(), "test_type": "agentic_rag_v5",
                "method": "claude_agent_sdk", "total": total,
                "passed": passed, "failed": failed, "errors": errors,
                "total_time": total_time, "total_cost": total_cost,
                "kb_commit": kb_commit,
                "eval_module": "eval_module.py (gate + quality + judge)",
                "model": MODEL_NAME if USE_DIRECT and MODEL_NAME else (ROUTER_MODEL if USE_ROUTER and ROUTER_MODEL else ("router:default" if USE_ROUTER else "claude-sonnet")),
                "dataset": EVAL_DATASET,
                "category_stats": {c: {"total": s["t"], "passed": s["p"]} for c, s in cats.items()},
                "source_stats": {s: {"total": v["t"], "passed": v["p"]} for s, v in source_stats.items()},
                "judge_summary": judge_summary,
                "quality_metrics": {
                    "pct_faith_ge_05": round(pct_faith, 1) if pct_faith is not None else None,
                    "pct_judge_ge_3": round(pct_judge, 1) if pct_judge is not None else None,
                    "judged_count": len(judged_results) if judged_results else 0,
                },
                "boundary_violations": {
                    "count": len(boundary_violations),
                    "cases": [{"test_id": r["test_id"], "violated_paths": r.get("violated_paths", [])} for r in boundary_violations],
                },
                "speed_summary": speed_summary,
                "early_stop_summary": {
                    "avg_turns": round(avg_turns, 1),
                    "avg_search_calls": round(avg_search, 1),
                    "avg_max_consec_same_tool": round(avg_consec, 1),
                    "stop_reasons": stop_reasons,
                    "high_turn_count": len(high_turn_cases),
                },
                "use_mcp": USE_MCP,
                "use_judge": USE_JUDGE,
                "use_router": USE_ROUTER,
                "use_direct": USE_DIRECT,
                "direct_base_url": DIRECT_BASE_URL if USE_DIRECT else None,
                "concurrency": EVAL_CONCURRENCY,
                "results": results,
            }, f, indent=2, ensure_ascii=False)

        log(f"\n📁 汇总: {out_file}", lf)
        log(f"📋 日志: {log_path}", lf)
        log(f"📝 详细: {detail_path}", lf)

    return results


if __name__ == "__main__":
    asyncio.run(main())
