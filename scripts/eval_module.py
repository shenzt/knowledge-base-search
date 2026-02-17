#!/usr/bin/env python3
"""RAG 评测模块: 结构化 contexts 提取 + Gate 门禁 + LLM-as-Judge。

从 Agent SDK 的 messages_log 中提取结构化的 retrieved_contexts，
然后通过两阶段评估: Gate (确定性规则) → Score (LLM Judge)。
"""

import json
import os
import re
import subprocess
from typing import Any, Optional


# ── Context 提取 ─────────────────────────────────────────────────

def extract_contexts(messages_log: list[dict]) -> list[dict]:
    """从 Agent SDK messages_log 提取结构化的 retrieved_contexts。

    支持两种格式:
    1. 字符串序列化: content="[ToolUseBlock(...)]" (SDK 默认)
    2. 结构化 dict: content=[{"type": "tool_use", ...}] (未来兼容)

    返回: [{"tool": "Grep", "doc_path": "docs/xxx.md", "text": "...", ...}]
    """
    contexts = []
    for msg in messages_log:
        content = msg.get("content", "")

        # ── 格式 1: 字符串序列化 (当前 SDK 行为) ──
        if isinstance(content, str):
            # 解析 ToolUseBlock
            # 注意: MCP 工具名含连字符如 mcp__knowledge-base__hybrid_search
            tool_match = re.search(
                r"ToolUseBlock\(id='([^']*)', name='([\w-]+(?:__[\w-]+)*)', input=(\{.*\})\)",
                content,
            )
            if tool_match:
                tool_id = tool_match.group(1)
                tool_name = tool_match.group(2)
                try:
                    tool_input = eval(tool_match.group(3))  # safe: only from our own logs
                except Exception:
                    tool_input = {}

                contexts.append({
                    "type": "tool_call",
                    "tool": tool_name,
                    "tool_use_id": tool_id,
                    "input": tool_input,
                })
                continue

            # 解析 ToolResultBlock
            result_match = re.search(
                r"ToolResultBlock\(tool_use_id='([^']*)', content='(.*?)'(?:, is_error=\w+)?\)",
                content, re.DOTALL,
            )
            if result_match:
                tool_use_id = result_match.group(1)
                result_text = result_match.group(2).replace("\\n", "\n")

                # 按 tool_use_id 精确匹配对应的 tool_call
                matched = False
                for ctx in reversed(contexts):
                    if ctx.get("type") == "tool_call" and ctx.get("tool_use_id") == tool_use_id:
                        ctx["type"] = "context"
                        ctx["result"] = result_text
                        tool = ctx.get("tool", "")
                        ctx["doc_paths"] = _extract_doc_paths(result_text, tool)
                        if tool == "Read":
                            fp = ctx.get("input", {}).get("file_path", "")
                            if fp:
                                ctx["doc_paths"] = [fp]
                        matched = True
                        break
                # Fallback: 如果 ID 匹配失败，退回到最近未匹配的 tool_call
                if not matched:
                    for ctx in reversed(contexts):
                        if ctx.get("type") == "tool_call":
                            ctx["type"] = "context"
                            ctx["result"] = result_text
                            ctx["tool_use_id"] = tool_use_id
                            tool = ctx.get("tool", "")
                            ctx["doc_paths"] = _extract_doc_paths(result_text, tool)
                            if tool == "Read":
                                fp = ctx.get("input", {}).get("file_path", "")
                                if fp:
                                    ctx["doc_paths"] = [fp]
                            break
                continue

        # ── 格式 2: 结构化 list[dict] (未来兼容) ──
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type", "")
                if btype == "tool_use":
                    contexts.append({
                        "type": "tool_call",
                        "tool": block.get("name", ""),
                        "input": block.get("input", {}),
                    })
                elif btype == "tool_result":
                    result_text = block.get("content", "")
                    if isinstance(result_text, list):
                        result_text = "\n".join(
                            b.get("text", str(b)) for b in result_text
                        )
                    for ctx in reversed(contexts):
                        if ctx.get("type") == "tool_call":
                            ctx["type"] = "context"
                            ctx["result"] = result_text
                            ctx["tool_use_id"] = block.get("tool_use_id", "")
                            tool = ctx.get("tool", "")
                            ctx["doc_paths"] = _extract_doc_paths(result_text, tool)
                            if tool == "Read":
                                fp = ctx.get("input", {}).get("file_path", "")
                                if fp:
                                    ctx["doc_paths"] = [fp]
                            break

    # 只返回有结果的 context
    return [c for c in contexts if c.get("type") == "context" and c.get("result")]


def _extract_doc_paths(text: str, tool: str) -> list[str]:
    """从工具结果中提取文档路径。"""
    paths = []
    if tool == "Glob":
        # Glob 返回所有匹配文件，太多噪音，只记录工具类型
        return []

    # MCP hybrid_search / keyword_search: 解析 JSON 中的 "path" 字段
    if "mcp__" in tool or "hybrid_search" in tool or "keyword_search" in tool:
        # SDK 序列化产生多层转义: \\\\"path\\\\" → 需要多次反转义
        normalized = text
        for _ in range(3):  # 最多 3 轮反转义
            prev = normalized
            normalized = normalized.replace('\\\\"', '"').replace('\\\\', '\\')
            normalized = normalized.replace('\\"', '"')
            if normalized == prev:
                break
        for m in re.finditer(r'"path"\s*:\s*"([^"]+)"', normalized):
            paths.append(m.group(1))
        if not paths:
            # Fallback: 直接匹配各种转义变体
            for m in re.finditer(r'\\*"path\\*"\s*:\s*\\*"([^"\\]+)\\*"', text):
                paths.append(m.group(1))
        return list(set(paths))

    if tool == "Read":
        # Read 的 input 里有 file_path，但 result 里没有
        # 从 result 的第一行尝试提取
        for m in re.finditer(r'[\w/.:-]*\.md', text[:500]):
            path = m.group(0)
            if path:
                paths.append(path)
    else:
        # Grep 等工具：提取所有 .md 路径
        for m in re.finditer(r'[\w/.-]*\.md', text):
            path = m.group(0)
            if path and not path.startswith('.'):
                paths.append(path)
    return list(set(paths))


def get_tools_used(contexts: list[dict]) -> list[str]:
    """获取使用的工具列表。"""
    return list(set(c.get("tool", "") for c in contexts if c.get("tool")))


def get_retrieved_doc_paths(contexts: list[dict]) -> list[str]:
    """获取所有检索到的文档路径。"""
    paths = []
    for c in contexts:
        paths.extend(c.get("doc_paths", []))
    return list(set(paths))


def get_kb_commit() -> str:
    """获取当前 KB 的 git commit hash。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


# ── Gate 门禁 (确定性规则，一票否决) ─────────────────────────────

def gate_check(tc: dict, answer: str, contexts: list[dict]) -> dict:
    """Gate 门禁检查。返回 {"passed": bool, "checks": {...}, "reasons": [...]}。

    只有 Gate 通过的样本才会进入 LLM Judge 打分。
    """
    checks = {}
    reasons = []
    source = tc.get("source", "unknown")

    # 1. 工具调用检查
    tools_used = get_tools_used(contexts)
    checks["tools_used"] = tools_used

    must_use = tc.get("must_use", [])
    if must_use:
        missing = [t for t in must_use if t not in tools_used]
        checks["must_use_ok"] = len(missing) == 0
        if missing:
            reasons.append(f"未调用必需工具: {missing}")

    # 2. 检索结果检查 (found 用例必须有 context)
    is_notfound = tc.get("expect_no_results") or tc.get("source") == "notfound"
    has_contexts = len(contexts) > 0
    checks["has_contexts"] = has_contexts
    if not is_notfound and not has_contexts:
        reasons.append("无检索结果")

    # 3. expected_doc 命中检查 (从 contexts 的 doc_paths 判断，不从 answer 文本)
    expected_doc = tc.get("expected_doc") or ""
    if expected_doc and not is_notfound:
        retrieved_paths = get_retrieved_doc_paths(contexts)
        expected_docs = [d.strip() for d in expected_doc.split(",")]
        hit = any(
            any(exp in path for path in retrieved_paths)
            for exp in expected_docs
        )
        checks["expected_doc_hit"] = hit
        checks["retrieved_paths"] = retrieved_paths
        if not hit:
            reasons.append(f"未检索到期望文档 {expected_docs} (实际: {retrieved_paths})")

    # 4. 引用检查 (answer 中是否有机器可读的引用)
    citation_patterns = [r'来源:\s*\S+\.md', r'docs/\S+\.md', r'\[来源', r'chunk_id',
                         r'section_path', r'\S+\.md:\d+']
    has_citation = any(re.search(p, answer) for p in citation_patterns)
    checks["has_citation"] = has_citation

    # 5. notfound 严格检查 (支持 v4 expect_no_results 和 v5 source=="notfound")
    is_notfound = tc.get("expect_no_results") or tc.get("source") == "notfound"
    if is_notfound:
        nf_phrases = ["未找到", "没有找到", "not found", "no relevant", "无法找到",
                       "没有相关", "没有专门", "不包含", "无相关", "没有包含",
                       "不在知识库", "没有收录", "无法在", "does not contain",
                       "no documentation", "no docs"]
        admits_not_found = any(p.lower() in answer.lower() for p in nf_phrases)

        # 检查是否输出了具体事实性断言 (不应该)
        has_factual_claims = len(answer) > 500 and not admits_not_found
        checks["admits_not_found"] = admits_not_found
        checks["has_factual_claims"] = has_factual_claims

        if has_factual_claims:
            reasons.append("notfound 用例输出了具体事实断言（疑似幻觉）")

    # 6. Qdrant 用例在无 MCP 模式下的检查
    use_mcp = os.environ.get("USE_MCP", "0") == "1"
    if source == "qdrant" and not use_mcp:
        has_hybrid = "hybrid_search" in str(tools_used) or "mcp__knowledge-base__hybrid_search" in str(tools_used)
        checks["hybrid_search_used"] = has_hybrid
        if not has_hybrid:
            reasons.append("Qdrant 用例未使用 hybrid_search（无 MCP 模式）")

    passed = len(reasons) == 0
    return {"passed": passed, "checks": checks, "reasons": reasons}


# ── LLM-as-Judge ─────────────────────────────────────────────────

def llm_judge(query: str, answer: str, contexts: list[dict],
              model: str = "") -> dict:
    """用 LLM 评估 RAG 回答质量。只对 Gate 通过的样本调用。

    模型配置优先级：
    1. 环境变量 JUDGE_PROVIDER + JUDGE_MODEL（推荐）
    2. model 参数（向后兼容）
    3. 默认 anthropic/claude-sonnet-4-5-20250929

    返回: {"score": 0-5, "faithfulness": 0-5, "relevancy": 0-5,
           "used_contexts": [...], "unsupported_claims": [...], "reason": "..."}
    """
    # 拼接 contexts，截断防超长
    ctx_parts = []
    for i, c in enumerate(contexts[:10]):  # 最多 10 个 context
        tool = c.get("tool", "?")
        result = c.get("result", "")[:2000]  # 每个最多 2000 字符
        doc_paths = c.get("doc_paths", [])
        ctx_parts.append(f"[Context {i+1}] tool={tool} docs={doc_paths}\n{result}")
    context_str = "\n---\n".join(ctx_parts) if ctx_parts else "(无检索结果)"

    prompt = f"""你是 RAG 系统评测专家。严格基于【检索到的文档】评判回答质量，不能用你自己的知识。

【用户提问】: {query}

【检索到的文档】:
{context_str}

【系统回答】: {answer[:3000]}

请输出严格 JSON:
{{
  "score": 0-5,
  "faithfulness": 0-5,
  "relevancy": 0-5,
  "used_contexts": [1, 3],
  "unsupported_claims": ["具体的无支撑断言"],
  "reason": "不超过50字的评语"
}}

评分规则:
- score 5: 完全基于文档，准确全面，引用正确。文档无答案时明确拒答也给5分。
- score 3: 基于文档但引用不精确，或混入少量无害通用知识。
- score 0: 严重幻觉、答非所问、或文档有答案却说不知道。
- 若 unsupported_claims 非空，faithfulness ≤ 2。
- 若 used_contexts 为空且回答给出具体结论，score ≤ 1。"""

    try:
        from llm_client import get_client

        # 向后兼容：如果传了 model 参数且没设环境变量，用旧方式
        if model and not os.environ.get("JUDGE_PROVIDER"):
            from llm_client import AnthropicClient
            client = AnthropicClient(model=model)
        else:
            client = get_client("judge")

        text = client.generate(prompt, max_tokens=300, temperature=0)
        # 提取 JSON
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"score": -1, "reason": f"无法解析 JSON: {text[:100]}"}
    except Exception as e:
        return {"score": -1, "reason": f"LLM Judge 异常: {str(e)[:80]}"}
