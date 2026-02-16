#!/usr/bin/env python3
"""Agentic RAG 自动化测试 v5 — 100 个真实问题

数据源: redis-docs (234 docs) + awesome-llm-apps (207 docs) + local docs/ (3 docs)
评估: eval_module (Gate 门禁 + 质量检查 + LLM-as-Judge)
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from claude_agent_sdk import query, ClaudeAgentOptions

PROJECT_ROOT = Path(__file__).parent.parent.parent

# 导入评测模块
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from eval_module import extract_contexts, gate_check, get_tools_used, get_retrieved_doc_paths, get_kb_commit, llm_judge

# 导入 v5 测试用例
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "fixtures"))
from v5_test_queries import TEST_CASES_V5

TEST_CASES = TEST_CASES_V5

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

if USE_MCP:
    BASE_OPTIONS = dict(
        allowed_tools=[
            "Read", "Grep", "Glob", "Bash",
            "mcp__knowledge-base__hybrid_search",
            "mcp__knowledge-base__keyword_search",
            "mcp__knowledge-base__index_status",
        ],
        mcp_servers={
            "knowledge-base": {
                "command": str(PROJECT_ROOT / ".venv" / "bin" / "python"),
                "args": [str(PROJECT_ROOT / "scripts" / "mcp_server.py")],
                "env": {
                    "QDRANT_URL": os.environ.get("QDRANT_URL", "http://localhost:6333"),
                    "COLLECTION_NAME": os.environ.get("COLLECTION_NAME", "knowledge-base"),
                },
            }
        },
        setting_sources=["project"],
        permission_mode="bypassPermissions",
        cwd=str(PROJECT_ROOT),
        max_turns=15,
    )
else:
    # 无 MCP 模式：仅使用 Grep/Glob/Read（Agentic Layer 1）
    # 注意：不能用 setting_sources=["project"]，否则会加载 .mcp.json 启动 MCP server
    # 改用 system_prompt 注入 CLAUDE.md 和 search skill 的关键指令
    BASE_OPTIONS = dict(
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        permission_mode="bypassPermissions",
        cwd=str(PROJECT_ROOT),
        max_turns=15,
        system_prompt="""你是一个知识库检索助手。用户会用 /search 命令查询知识库。

知识库文档在 docs/ 目录下，格式为 Markdown，包含 Redis、LLM/AI 应用开发等技术文档。

检索策略：
1. 使用 Grep 搜索关键词
2. 使用 Glob 查找相关文件（如 docs/**/*.md）
3. 使用 Read 读取命中文件的相关段落
4. 综合分析并回答，必须带引用 [来源: docs/xxx.md]

回答要求：
- 必须且只能基于检索到的文档内容回答
- 如果文档中没有相关信息，只回答"未找到相关文档"，不要提供任何建议、替代方案或通用知识
- 严禁用你自己的训练知识补充回答。如果 docs/ 中没有，就是没有
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
                max_turns=15,
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
        judge = llm_judge(tc["query"], answer, contexts)
        ev["quality"]["judge"] = judge
        # Judge score < 2 视为质量不合格（但不改变 pass/fail）
        if judge.get("score", -1) >= 0:
            ev["quality"]["judge_score"] = judge["score"]
            ev["quality"]["faithfulness"] = judge.get("faithfulness", -1)
            ev["quality"]["relevancy"] = judge.get("relevancy", -1)

    return ev


async def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = PROJECT_ROOT / "eval" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"agentic_rag_{timestamp}.log"
    detail_path = log_dir / f"agentic_rag_{timestamp}_detail.jsonl"

    with open(log_path, "w", encoding="utf-8") as lf, \
         open(detail_path, "w", encoding="utf-8") as df:

        mode = "MCP + Grep/Glob/Read" if USE_MCP else "Grep/Glob/Read (无 MCP)"
        kb_commit_header = get_kb_commit()
        log("=" * 80, lf)
        log(f"🤖 Agentic RAG 测试 (Agent SDK)", lf)
        log("=" * 80, lf)
        log(f"用例: {len(TEST_CASES)} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", lf)
        log(f"模式: {mode}", lf)
        log(f"KB commit: {kb_commit_header}", lf)
        log(f"评估: eval_module (Gate 门禁 + 质量检查)", lf)
        log(f"策略: Claude 自主选择检索策略 (Grep/Glob/Read{' + MCP hybrid_search' if USE_MCP else ''})", lf)
        log(f"日志: {log_path}", lf)
        log(f"详细: {detail_path}", lf)
        log("", lf)

        results = []
        passed = failed = errors = 0
        total_time = total_cost = 0.0
        # 不复用 session — 每个用例独立 session，确保 Agent 每次都执行工具调用
        # 复用 session 会导致 Claude 从上下文记忆回答，跳过检索，extract_contexts() 为空

        for i, tc in enumerate(TEST_CASES, 1):
            log(f"\n{'='*60}", lf)
            log(f"[{i}/{len(TEST_CASES)}] {tc['id']} ({tc['category']}) [{tc.get('type', '?')}]", lf)
            log(f"  Q: {tc['query']}", lf)
            if tc.get("note"):
                log(f"  💡 {tc['note']}", lf)
            if i == 1 and USE_MCP:
                log(f"  ⏳ 首次查询，加载 MCP server (BGE-M3)...", lf)
            log(f"  开始: {datetime.now().strftime('%H:%M:%S')}", lf)

            # 如果有 MCP + skills，用 /search；否则直接提问
            prompt = f"/search {tc['query']}" if USE_MCP else f"请在 docs/ 目录中检索并回答: {tc['query']}"
            result = await run_query(prompt, None, lf)  # None = 每次新 session

            elapsed = result.get("elapsed", 0)
            total_time += elapsed
            total_cost += result.get("cost_usd", 0)

            ev = evaluate(tc, result)

            if result["status"] == "error":
                log(f"  ❌ 错误: {result.get('error', '')[:80]}", lf)
                errors += 1
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
                log(f"  ✅ 通过 | {ans_len}字符 | {elapsed:.1f}s | ${result.get('cost_usd', 0):.4f} | {cite} {doc_tag} | ctx:{ctx_count}", lf)
                if tools:
                    log(f"  🔧 工具: {', '.join(tools)}", lf)
                if quality.get("retrieved_paths"):
                    log(f"  📄 检索: {', '.join(quality['retrieved_paths'][:5])}", lf)
                if kw:
                    log(f"  🔑 关键词: {', '.join(kw)}", lf)
                if quality.get("judge_score") is not None:
                    js = quality["judge_score"]
                    ff = quality.get("faithfulness", "?")
                    rr = quality.get("relevancy", "?")
                    log(f"  🧑‍⚖️ Judge: score={js} faith={ff} rel={rr}", lf)
                passed += 1
                status = "passed"
            else:
                log(f"  ❌ 失败: {'; '.join(ev['reasons'])}", lf)
                failed += 1
                status = "failed"

            # 输出答案预览（通过和失败都输出）
            ans_preview = result.get("answer", "")[:500]
            if ans_preview:
                log(f"  📝 答案: {ans_preview}{'...' if len(result.get('answer',''))>500 else ''}", lf)

            log(f"  结束: {datetime.now().strftime('%H:%M:%S')} | 耗时: {elapsed:.1f}s", lf)

            # 写入详细 JSONL（每个 query 一行，包含完整消息日志）
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
                "judge": quality.get("judge"),
                "messages": result.get("messages_log", []),
            }
            df.write(json.dumps(detail_record, ensure_ascii=False) + "\n")
            df.flush()

            results.append({
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
            })
            log("-" * 80, lf)

        # 总结
        total = len(TEST_CASES)
        log(f"\n{'=' * 80}", lf)
        log(f"📊 总结: ✅{passed} ❌{failed} ⚠️{errors} / {total} ({passed/total*100:.1f}%)", lf)
        log(f"⏱️  总耗时: {total_time:.1f}s | 平均: {total_time/max(passed+failed,1):.1f}s", lf)
        log(f"💰 总费用: ${total_cost:.4f}", lf)

        # 按查询类型统计
        type_stats = {}
        for i2, r in enumerate(results):
            qtype = TEST_CASES[i2].get("type", "unknown")
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
        for i2, r in enumerate(results):
            src = TEST_CASES[i2].get("source", "unknown")
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

        # LLM Judge 统计
        if USE_JUDGE:
            judge_scores = [r.get("judge_score") for r in results
                           if r.get("judge_score") is not None]
            if judge_scores:
                avg_score = sum(judge_scores) / len(judge_scores)
                avg_faith = sum(r.get("faithfulness", 0) for r in results
                               if r.get("faithfulness") is not None and r.get("faithfulness", -1) >= 0) / max(len(judge_scores), 1)
                avg_rel = sum(r.get("relevancy", 0) for r in results
                             if r.get("relevancy") is not None and r.get("relevancy", -1) >= 0) / max(len(judge_scores), 1)
                low_quality = [r for r in results if r.get("judge_score") is not None and r["judge_score"] < 3]
                log("", lf)
                log(f"🧑‍⚖️ LLM Judge ({len(judge_scores)} cases):", lf)
                log(f"  平均 score: {avg_score:.2f}/5 | faithfulness: {avg_faith:.2f}/5 | relevancy: {avg_rel:.2f}/5", lf)
                if low_quality:
                    log(f"  ⚠️ 低质量 (score<3): {len(low_quality)} 个", lf)
                    for r in low_quality[:5]:
                        log(f"    - {r['test_id']}: score={r['judge_score']} {r.get('query', '')[:40]}", lf)

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
                judge_summary = {
                    "count": len(judge_scores),
                    "avg_score": round(sum(judge_scores) / len(judge_scores), 2),
                    "low_quality_count": sum(1 for s in judge_scores if s < 3),
                }

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(), "test_type": "agentic_rag_v5",
                "method": "claude_agent_sdk", "total": total,
                "passed": passed, "failed": failed, "errors": errors,
                "total_time": total_time, "total_cost": total_cost,
                "kb_commit": kb_commit,
                "eval_module": "eval_module.py (gate + quality + judge)",
                "category_stats": {c: {"total": s["t"], "passed": s["p"]} for c, s in cats.items()},
                "source_stats": {s: {"total": v["t"], "passed": v["p"]} for s, v in source_stats.items()},
                "judge_summary": judge_summary,
                "use_mcp": USE_MCP,
                "use_judge": USE_JUDGE,
                "results": results,
            }, f, indent=2, ensure_ascii=False)

        log(f"\n📁 汇总: {out_file}", lf)
        log(f"📋 日志: {log_path}", lf)
        log(f"📝 详细: {detail_path}", lf)

    return results


if __name__ == "__main__":
    asyncio.run(main())
