#!/usr/bin/env python3
"""Agentic RAG 自动化测试 - 使用 Claude Agent SDK + Session 复用

关键优化：使用 session resume 保持 MCP server 活跃，避免每次重新加载模型。
完整记录中间过程到日志文件，方便排查和调优。
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

TEST_CASES = [
    # ── 基础关键词查询（Grep 擅长）── type: keyword
    {"id": "basic-001", "query": "What is a Pod in Kubernetes?", "category": "k8s-basic", "type": "keyword"},
    {"id": "basic-002", "query": "Kubernetes Service 是什么？", "category": "k8s-service", "type": "keyword"},
    {"id": "basic-003", "query": "What are Init Containers?", "category": "k8s-init", "type": "keyword"},

    # ── 精确关键词/错误码（Grep 最强）── type: exact
    {"id": "grep-001", "query": "READONLY You can't write against a read only replica", "category": "redis-error",
     "type": "exact", "note": "精确错误信息，Grep 直接命中 redis-failover.md"},
    {"id": "grep-002", "query": "OOMKilled", "category": "k8s-oom",
     "type": "exact", "note": "精确错误码，Grep 直接命中 k8s-crashloop.md"},
    {"id": "grep-003", "query": "TOKEN_EXPIRED 错误码是什么意思？", "category": "api-errorcode",
     "type": "exact", "note": "精确错误码，Grep 命中 authentication.md"},
    {"id": "grep-004", "query": "JWT token 的结构是什么？", "category": "api-jwt",
     "type": "exact", "note": "精确关键词 JWT，Grep 命中 authentication.md"},
    {"id": "grep-005", "query": "SENTINEL failover 命令怎么用？", "category": "redis-sentinel",
     "type": "exact", "note": "精确命令名，Grep 命中 redis-failover.md"},

    # ── 症状描述型（Hybrid Search 擅长）── type: semantic
    {"id": "semantic-001", "query": "应用突然无法写入缓存，日志报只读错误", "category": "redis-symptom",
     "type": "semantic", "note": "症状描述→redis-failover.md，无直接关键词匹配"},
    {"id": "semantic-002", "query": "容器一直重启，无法正常运行", "category": "k8s-symptom",
     "type": "semantic", "note": "症状描述→k8s-crashloop.md，不含 CrashLoopBackOff 关键词"},
    {"id": "semantic-003", "query": "内存不足导致进程被杀", "category": "k8s-oom-semantic",
     "type": "semantic", "note": "语义描述 OOMKilled，不含英文关键词"},
    {"id": "semantic-004", "query": "用户登录后如何保持会话状态？", "category": "api-session",
     "type": "semantic", "note": "语义→authentication.md 的 token 机制，不含 JWT/OAuth 关键词"},

    # ── 跨语言查询（Hybrid Search 擅长）── type: cross-lang
    {"id": "cross-lang-001", "query": "Redis 管道技术如何工作？", "category": "redis-pipeline", "type": "cross-lang"},
    {"id": "cross-lang-002", "query": "How does Redis pipelining improve performance?", "category": "redis-pipeline", "type": "cross-lang"},
    {"id": "cross-lang-003", "query": "How to recover from Redis master-slave failover?", "category": "redis-cross",
     "type": "cross-lang", "note": "英文查询→中文文档 redis-failover.md"},
    {"id": "cross-lang-004", "query": "Kubernetes pod keeps crashing, how to debug?", "category": "k8s-cross",
     "type": "cross-lang", "note": "英文口语化查询→英文文档，但不含精确关键词 CrashLoopBackOff"},

    # ── 同义词改写型（Hybrid Search 擅长）── type: paraphrase
    {"id": "paraphrase-001", "query": "如何检查 Redis 高可用集群的健康状态？", "category": "redis-ha",
     "type": "paraphrase", "note": "高可用→Sentinel，健康状态→排查步骤，改写后无直接关键词"},
    {"id": "paraphrase-002", "query": "API 接口的权限控制是怎么设计的？", "category": "api-rbac",
     "type": "paraphrase", "note": "权限控制→RBAC，改写后需语义理解"},
    {"id": "paraphrase-003", "query": "应用连接数据库缓存的最佳实践", "category": "redis-connpool",
     "type": "paraphrase", "note": "数据库缓存→Redis，连接→连接池，需语义关联"},

    # ── 复杂推理/多文档（Skills 第三层擅长）── type: complex
    {"id": "complex-001", "query": "What's the difference between Deployment and StatefulSet?", "category": "k8s-comparison", "type": "complex"},
    {"id": "complex-002", "query": "How to troubleshoot CrashLoopBackOff in Kubernetes?", "category": "k8s-troubleshooting", "type": "complex"},
    {"id": "complex-003", "query": "Kubernetes 中如何实现服务发现？", "category": "k8s-service-discovery", "type": "complex"},
    {"id": "complex-004", "query": "Pod 崩溃后 Redis 连接会怎样？需要怎么处理？", "category": "multi-doc",
     "type": "complex", "note": "需要综合 k8s-crashloop + redis-failover 两个文档"},
    {"id": "complex-005", "query": "系统的安全机制有哪些？从认证到部署都说说", "category": "multi-doc-security",
     "type": "complex", "note": "需要综合 authentication.md + configuration.md"},

    # ── How-to 实操型 ── type: howto
    {"id": "howto-001", "query": "How to create a Pod with multiple containers?", "category": "k8s-howto", "type": "howto"},
    {"id": "howto-002", "query": "如何配置 Kubernetes 资源限制？", "category": "k8s-resources", "type": "howto"},
    {"id": "howto-003", "query": "refresh_token 过期了怎么办？", "category": "api-refresh",
     "type": "howto", "note": "实操问题→authentication.md 的 token 刷新流程"},
    {"id": "howto-004", "query": "怎么配置 Redis 连接池的空闲超时？", "category": "redis-config",
     "type": "howto", "note": "实操→redis-failover.md 的 minEvictableIdleTimeMillis"},

    # ── 概念型 ── type: concept
    {"id": "concept-001", "query": "What is the purpose of a ReplicaSet?", "category": "k8s-concept", "type": "concept"},
    {"id": "concept-002", "query": "Kubernetes 命名空间的作用是什么？", "category": "k8s-namespace", "type": "concept"},

    # ── 边缘型 ── type: concept
    {"id": "edge-001", "query": "What is a sidecar container?", "category": "k8s-pattern", "type": "concept"},
    {"id": "edge-002", "query": "Kubernetes 中的 DaemonSet 是什么？", "category": "k8s-daemonset", "type": "concept"},

    # ── 未收录（应返回"未找到"）── type: notfound
    {"id": "notfound-001", "query": "How to configure Kubernetes with blockchain?", "category": "not-in-kb", "type": "notfound", "expect_no_results": True},
    {"id": "notfound-002", "query": "MongoDB 分片集群如何配置？", "category": "not-in-kb", "type": "notfound", "expect_no_results": True},
]

KEYWORD_CHECKS = {
    "k8s-basic": ["pod", "container", "kubernetes"],
    "k8s-service": ["service", "网络", "network", "负载", "load"],
    "k8s-init": ["init", "container", "初始化"],
    "redis-pipeline": ["pipeline", "管道", "批量", "batch", "redis"],
    "k8s-comparison": ["deployment", "statefulset", "区别", "difference"],
    "k8s-troubleshooting": ["crashloopbackoff", "debug", "排查", "troubleshoot", "log"],
    "k8s-service-discovery": ["service", "discovery", "发现", "dns"],
    "k8s-howto": ["pod", "container", "multi", "多容器", "sidecar"],
    "k8s-resources": ["resource", "limit", "request", "资源", "cpu", "memory"],
    "k8s-concept": ["replicaset", "replica", "副本"],
    "k8s-namespace": ["namespace", "命名空间", "隔离"],
    "k8s-pattern": ["sidecar", "container", "pattern"],
    "k8s-daemonset": ["daemonset", "node", "节点"],
    # ── 新增 category 的关键词检查 ──
    "redis-error": ["readonly", "read only", "replica", "写入", "failover", "切换"],
    "k8s-oom": ["oomkilled", "oom", "memory", "内存", "limit"],
    "api-errorcode": ["token_expired", "过期", "401", "错误码", "error"],
    "api-jwt": ["jwt", "token", "sub", "exp", "签名", "signature"],
    "redis-sentinel": ["sentinel", "failover", "主从", "切换"],
    "redis-symptom": ["redis", "readonly", "写入", "failover", "sentinel", "主从", "切换", "只读"],
    "k8s-symptom": ["crash", "restart", "重启", "crashloop", "pod", "容器"],
    "k8s-oom-semantic": ["oom", "memory", "内存", "killed", "limit", "资源"],
    "api-session": ["token", "jwt", "oauth", "认证", "登录", "session", "会话"],
    "redis-cross": ["failover", "sentinel", "master", "slave", "切换", "恢复", "redis"],
    "k8s-cross": ["crash", "debug", "log", "pod", "restart", "troubleshoot"],
    "redis-ha": ["sentinel", "redis", "高可用", "health", "状态", "master"],
    "api-rbac": ["rbac", "role", "权限", "admin", "viewer", "editor", "授权"],
    "redis-connpool": ["连接池", "connection", "sentinel", "redis", "配置", "testOnBorrow"],
    "multi-doc": ["pod", "redis", "crash", "连接", "重启", "failover"],
    "multi-doc-security": ["认证", "oauth", "jwt", "token", "安全", "https", "权限"],
    "api-refresh": ["refresh", "token", "过期", "刷新", "access_token"],
    "redis-config": ["连接池", "idle", "timeout", "minEvictable", "配置", "超时"],
}

# 是否启用 MCP（模型加载需要 15-20 分钟，可选关闭）
USE_MCP = os.environ.get("USE_MCP", "0") == "1"

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

知识库文档在 docs/ 目录下，格式为 Markdown，包含 Kubernetes 和 Redis 相关技术文档。

检索策略：
1. 使用 Grep 搜索关键词
2. 使用 Glob 查找相关文件（如 docs/**/*.md）
3. 使用 Read 读取命中文件的相关段落
4. 综合分析并回答，必须带引用 [来源: docs/xxx.md]

回答要求：
- 基于检索到的文档内容回答
- 如果文档中没有相关信息，明确说明"未找到相关文档"
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
    """评估答案"""
    ev = {"passed": False, "reasons": [], "quality": {}}
    if result["status"] != "success":
        ev["reasons"].append(f"执行失败: {result.get('error', '')[:80]}")
        return ev

    answer = result.get("answer", "")

    if tc.get("expect_no_results"):
        nf = ["未找到", "没有找到", "not found", "no relevant", "无法找到", "no results", "没有相关", "don't have"]
        if any(w.lower() in answer.lower() for w in nf) or len(answer) < 500:
            ev["passed"] = True
            ev["quality"]["no_results_ok"] = True
        else:
            ev["reasons"].append("应识别为无结果")
        return ev

    if len(answer) < 50:
        ev["reasons"].append(f"答案过短 ({len(answer)})")
        return ev

    ev["quality"]["has_citation"] = any(m in answer for m in ["来源:", "docs/", "[来源", ".md"])
    expected = KEYWORD_CHECKS.get(tc["category"], [])
    matched = [k for k in expected if k.lower() in answer.lower()]
    ev["quality"]["keywords"] = matched

    if len(answer) >= 100 and len(matched) >= 1:
        ev["passed"] = True
    else:
        if len(answer) < 100:
            ev["reasons"].append(f"内容不足 ({len(answer)})")
        if not matched:
            ev["reasons"].append(f"缺关键词 ({expected})")
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
        log("=" * 80, lf)
        log(f"🤖 Agentic RAG 测试 (Agent SDK)", lf)
        log("=" * 80, lf)
        log(f"用例: {len(TEST_CASES)} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", lf)
        log(f"模式: {mode}", lf)
        log(f"策略: Claude 自主选择检索策略 (Grep/Glob/Read{' + MCP hybrid_search' if USE_MCP else ''})", lf)
        log(f"日志: {log_path}", lf)
        log(f"详细: {detail_path}", lf)
        log("", lf)

        results = []
        passed = failed = errors = 0
        total_time = total_cost = 0.0
        session_id = None

        for i, tc in enumerate(TEST_CASES, 1):
            log(f"\n{'='*60}", lf)
            log(f"[{i}/{len(TEST_CASES)}] {tc['id']} ({tc['category']}) [{tc.get('type', '?')}]", lf)
            log(f"  Q: {tc['query']}", lf)
            if tc.get("note"):
                log(f"  💡 {tc['note']}", lf)
            if i == 1:
                log(f"  ⏳ 首次查询，加载 MCP server (BGE-M3)...", lf)
            log(f"  开始: {datetime.now().strftime('%H:%M:%S')}", lf)

            # 如果有 MCP + skills，用 /search；否则直接提问
            prompt = f"/search {tc['query']}" if USE_MCP else f"请在 docs/ 目录中检索并回答: {tc['query']}"
            result = await run_query(prompt, session_id, lf)

            if result.get("session_id"):
                session_id = result["session_id"]
                if i == 1:
                    log(f"  📌 Session: {session_id}", lf)

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
                tools = set(result.get("tools_used", []))
                cite = "引用✅" if ev["quality"].get("has_citation") else "引用❌"
                kw = ev.get("quality", {}).get("keywords", [])
                log(f"  ✅ 通过 | {ans_len}字符 | {elapsed:.1f}s | ${result.get('cost_usd', 0):.4f} | {cite}", lf)
                if tools:
                    log(f"  🔧 工具: {', '.join(tools)}", lf)
                if kw:
                    log(f"  🔑 关键词: {', '.join(kw)}", lf)
                passed += 1
                status = "passed"
            else:
                log(f"  ❌ 失败: {'; '.join(ev['reasons'])}", lf)
                failed += 1
                status = "failed"

            log(f"  结束: {datetime.now().strftime('%H:%M:%S')} | 耗时: {elapsed:.1f}s", lf)

            # 写入详细 JSONL（每个 query 一行，包含完整消息日志）
            detail_record = {
                "test_id": tc["id"],
                "category": tc["category"],
                "type": tc.get("type", "unknown"),
                "query": tc["query"],
                "status": status,
                "elapsed_seconds": elapsed,
                "cost_usd": result.get("cost_usd", 0),
                "num_turns": result.get("num_turns", 0),
                "answer_length": len(result.get("answer", "")),
                "answer": result.get("answer", ""),
                "tools_used": list(set(result.get("tools_used", []))),
                "has_citation": ev.get("quality", {}).get("has_citation", False),
                "matched_keywords": ev.get("quality", {}).get("keywords", []),
                "failure_reasons": ev.get("reasons", []),
                "messages": result.get("messages_log", []),
            }
            df.write(json.dumps(detail_record, ensure_ascii=False) + "\n")
            df.flush()

            results.append({
                "test_id": tc["id"], "category": tc["category"],
                "type": tc.get("type", "unknown"), "query": tc["query"],
                "status": status, "elapsed_seconds": elapsed,
                "cost_usd": result.get("cost_usd", 0),
                "num_turns": result.get("num_turns", 0),
                "answer_length": len(result.get("answer", "")),
                "tools_used": list(set(result.get("tools_used", []))),
                "has_citation": ev.get("quality", {}).get("has_citation", False),
                "matched_keywords": ev.get("quality", {}).get("keywords", []),
                "failure_reasons": ev.get("reasons", []),
                "answer_preview": result.get("answer", "")[:300],
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
            "keyword": "关键词基础", "exact": "精确匹配(Grep擅长)",
            "semantic": "语义/症状(Hybrid擅长)", "cross-lang": "跨语言",
            "paraphrase": "同义改写(Hybrid擅长)", "complex": "复杂推理/多文档",
            "howto": "实操问答", "concept": "概念型", "notfound": "未收录",
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

        # 保存汇总 JSON
        out_dir = PROJECT_ROOT / "eval"
        out_file = out_dir / f"agentic_rag_test_{timestamp}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(), "test_type": "agentic_rag",
                "method": "claude_agent_sdk_session_reuse", "total": total,
                "passed": passed, "failed": failed, "errors": errors,
                "total_time": total_time, "total_cost": total_cost,
                "type_stats": {t: {"total": s["t"], "passed": s["p"]} for t, s in type_stats.items()},
                "results": results,
            }, f, indent=2, ensure_ascii=False)

        log(f"\n📁 汇总: {out_file}", lf)
        log(f"📋 日志: {log_path}", lf)
        log(f"📝 详细: {detail_path}", lf)

    # 生成对比报告
    generate_comparison(str(out_file))
    return results


def generate_comparison(agentic_file: str):
    """生成 Simple RAG vs Agentic RAG 对比"""
    baseline = PROJECT_ROOT / "eval" / "comprehensive_test_20260213_234320.json"
    if not baseline.exists():
        candidates = sorted((PROJECT_ROOT / "eval").glob("comprehensive_test_*.json"))
        if not candidates:
            print("❌ 未找到 Simple RAG baseline", flush=True)
            return
        baseline = candidates[-1]

    with open(baseline) as f: simple = json.load(f)
    with open(agentic_file) as f: agentic = json.load(f)

    s_map = {r["test_id"]: r for r in simple["results"]}
    a_map = {r["test_id"]: r for r in agentic["results"]}
    s_rate = simple["passed"]/simple["total"]*100
    a_rate = agentic["passed"]/agentic["total"]*100
    s_avg = simple.get("total_time",0)/simple["total"]
    a_avg = agentic.get("total_time",0)/agentic["total"]

    improved = [t for t in TEST_CASES if s_map.get(t["id"],{}).get("status")!="passed" and a_map.get(t["id"],{}).get("status")=="passed"]
    regressed = [t for t in TEST_CASES if s_map.get(t["id"],{}).get("status")=="passed" and a_map.get(t["id"],{}).get("status")!="passed"]

    report = f"""# Simple RAG vs Agentic RAG 对比报告

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | **方法**: Claude Agent SDK + Session 复用

## 📊 总体

| 指标 | Simple RAG | Agentic RAG | 变化 |
|------|-----------|-------------|------|
| 通过率 | {simple['passed']}/{simple['total']} ({s_rate:.1f}%) | {agentic['passed']}/{agentic['total']} ({a_rate:.1f}%) | **{a_rate-s_rate:+.1f}%** |
| 失败 | {simple['failed']} | {agentic['failed']} | {agentic['failed']-simple['failed']:+d} |
| 平均耗时 | {s_avg:.1f}s | {a_avg:.1f}s | {a_avg-s_avg:+.1f}s |
| 费用 | ~${simple.get('total_tokens',0)*0.000003:.4f} | ${agentic.get('total_cost',0):.4f} | - |

## 逐用例

| ID | 查询 | Simple | Agentic | |
|----|------|--------|---------|--|
"""
    for tc in TEST_CASES:
        s = "✅" if s_map.get(tc["id"],{}).get("status")=="passed" else "❌"
        a = "✅" if a_map.get(tc["id"],{}).get("status")=="passed" else "❌"
        ch = "🟢" if s=="❌" and a=="✅" else "🔴" if s=="✅" and a=="❌" else ""
        q = tc["query"][:35]+"..." if len(tc["query"])>35 else tc["query"]
        report += f"| {tc['id']} | {q} | {s} | {a} | {ch} |\n"

    if improved:
        report += f"\n## 🟢 改善 ({len(improved)})\n\n"
        for tc in improved:
            a = a_map.get(tc["id"],{})
            report += f"- **{tc['id']}**: {tc['query']} → {a.get('answer_length',0)}字符, 工具: {', '.join(a.get('tools_used',[]))}\n"

    if regressed:
        report += f"\n## 🔴 退步 ({len(regressed)})\n\n"
        for tc in regressed:
            a = a_map.get(tc["id"],{})
            report += f"- **{tc['id']}**: {tc['query']} → {'; '.join(a.get('failure_reasons',[]))}\n"

    report += f"\n## 结论\n\n通过率 {s_rate:.1f}% → {a_rate:.1f}% ({a_rate-s_rate:+.1f}%), 改善 {len(improved)} 个, 退步 {len(regressed)} 个。\n"

    rf = PROJECT_ROOT / "eval" / f"AGENTIC_VS_SIMPLE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(rf, "w", encoding="utf-8") as f: f.write(report)
    print(f"📊 报告: {rf}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
