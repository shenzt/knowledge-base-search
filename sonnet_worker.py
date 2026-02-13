#!/usr/bin/env python3
"""Sonnet Worker - Layer 2 执行引擎

使用 Claude Agent SDK 调用 Sonnet 模型执行知识库任务。
这是被 Layer 1 (Opus) 调用的执行层。

职责:
- 文档处理 (HTML 转换、分块)
- 索引构建 (向量化、写入 Qdrant)
- 知识检索 (混合检索、RRF 融合)
- 数据同步 (双仓同步)

使用方式:
    from sonnet_worker import run_rag_task

    result = await run_rag_task(
        task="请将 Redis 文档从 HTML 转换为 Markdown",
        working_dir="./kb_skills"
    )
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from claude_agent_sdk import query, ClaudeAgentOptions

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# 配置
SONNET_MODEL = os.environ.get("SONNET_MODEL", "claude-3-5-sonnet-20241022")
KB_SKILLS_DIR = os.environ.get("KB_SKILLS_DIR", "./kb_skills")


async def run_rag_task(
    task: str,
    working_dir: str = KB_SKILLS_DIR,
    allowed_tools: Optional[List[str]] = None,
    max_turns: int = 50,
    enable_mcp: bool = True
) -> Dict[str, Any]:
    """运行 RAG 任务 (Layer 2 执行入口)。

    Args:
        task: 任务描述 (自然语言)
        working_dir: 工作目录 (包含 KB Skills)
        allowed_tools: 允许使用的工具列表
        max_turns: 最大轮次
        enable_mcp: 是否启用 MCP Server

    Returns:
        {
            "status": "success" | "error",
            "session_id": "...",
            "result": "...",
            "tool_calls": [...],
            "usage": {...}
        }
    """
    log.info(f"[Sonnet Worker] 启动任务: {task}")
    log.info(f"[Sonnet Worker] 工作目录: {working_dir}")

    # 默认工具
    if allowed_tools is None:
        allowed_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

    # 配置选项
    options = ClaudeAgentOptions(
        model=SONNET_MODEL,
        allowed_tools=allowed_tools,
        setting_sources=["project"],  # 使用 kb_skills 中的配置
        working_directory=working_dir,
        max_turns=max_turns
    )

    # 启用 MCP Server (混合检索)
    if enable_mcp:
        options.mcp_servers = {
            "knowledge-base": {
                "command": "python",
                "args": [os.path.abspath("scripts/mcp_server.py")]
            }
        }

    # 执行任务
    session_id = None
    result_text = ""
    tool_calls = []
    total_input_tokens = 0
    total_output_tokens = 0

    try:
        async for message in query(prompt=task, options=options):
            # 捕获 session_id
            if hasattr(message, "session_id"):
                session_id = message.session_id
                log.info(f"[Sonnet Worker] Session ID: {session_id}")

            # 收集最终结果
            if hasattr(message, "result"):
                result_text = message.result
                log.info(f"[Sonnet Worker] 任务完成")

            # 收集工具调用日志
            if hasattr(message, "type") and message.type == "tool_use":
                tool_call = {
                    "tool": message.name if hasattr(message, "name") else "unknown",
                    "input": message.input if hasattr(message, "input") else {}
                }
                tool_calls.append(tool_call)
                log.info(f"[Sonnet Worker] 工具调用: {tool_call['tool']}")

            # 收集 token 使用
            if hasattr(message, "usage"):
                if hasattr(message.usage, "input_tokens"):
                    total_input_tokens += message.usage.input_tokens
                if hasattr(message.usage, "output_tokens"):
                    total_output_tokens += message.usage.output_tokens

        return {
            "status": "success",
            "session_id": session_id,
            "result": result_text,
            "tool_calls": tool_calls,
            "usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens
            }
        }

    except Exception as e:
        log.error(f"[Sonnet Worker] 任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": session_id,
            "tool_calls": tool_calls
        }


async def resume_task(
    session_id: str,
    new_prompt: str,
    working_dir: str = KB_SKILLS_DIR
) -> Dict[str, Any]:
    """恢复之前的 session 继续执行。

    Args:
        session_id: 之前任务的 session ID
        new_prompt: 新的指令
        working_dir: 工作目录

    Returns:
        执行结果字典
    """
    log.info(f"[Sonnet Worker] 恢复 Session: {session_id}")
    log.info(f"[Sonnet Worker] 新指令: {new_prompt}")

    options = ClaudeAgentOptions(
        model=SONNET_MODEL,
        resume=session_id,
        working_directory=working_dir
    )

    result_text = ""
    tool_calls = []

    try:
        async for message in query(prompt=new_prompt, options=options):
            if hasattr(message, "result"):
                result_text = message.result

            if hasattr(message, "type") and message.type == "tool_use":
                tool_calls.append({
                    "tool": message.name if hasattr(message, "name") else "unknown",
                    "input": message.input if hasattr(message, "input") else {}
                })

        return {
            "status": "success",
            "session_id": session_id,
            "result": result_text,
            "tool_calls": tool_calls
        }

    except Exception as e:
        log.error(f"[Sonnet Worker] 恢复任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "session_id": session_id
        }


# ============================================================================
# 预定义任务模板
# ============================================================================

async def convert_html_docs(input_dir: str, output_dir: str) -> Dict[str, Any]:
    """HTML 转 Markdown 任务"""
    task = f"""
请将 {input_dir} 目录中的 HTML 文档转换为 Markdown 格式，输出到 {output_dir}。

要求:
1. 使用 pandoc 进行转换
2. 自动提取标题 (从 <title> 或 <h1>)
3. 生成 front-matter (id, title, source_file, converted_at)
4. 保持目录结构
5. 报告转换结果 (成功/失败数量)
"""
    return await run_rag_task(task)


async def build_index(docs_dir: str, output_dir: str) -> Dict[str, Any]:
    """构建分层索引任务"""
    task = f"""
请为 {docs_dir} 目录构建分层索引，输出到 {output_dir}。

要求:
1. 扫描所有 Markdown 文件
2. 提取 front-matter (id, title, tags, category, confidence)
3. 生成 index.json (机器可读)
4. 生成 INDEX.md (人类可读)
5. 包含目录结构、标签索引、分类统计
"""
    return await run_rag_task(task)


async def index_to_qdrant(docs_dir: str, collection: str = "knowledge-base") -> Dict[str, Any]:
    """向量索引任务"""
    task = f"""
请将 {docs_dir} 目录中的文档索引到 Qdrant collection: {collection}。

要求:
1. 使用 scripts/index.py 批量索引
2. 编码 dense + sparse 向量
3. 报告索引结果 (成功数量、失败数量)
4. 显示最终 collection 状态
"""
    return await run_rag_task(task)


async def search_knowledge_base(query_text: str, top_k: int = 5) -> Dict[str, Any]:
    """知识库检索任务"""
    task = f"""
请在知识库中检索以下问题的答案:

问题: {query_text}

要求:
1. 使用混合检索 (Dense + Sparse + RRF)
2. 返回 top {top_k} 结果
3. 包含文档标题、路径、得分、内容片段
4. 基于检索结果回答问题
"""
    return await run_rag_task(task, enable_mcp=True)


# ============================================================================
# CLI 入口 (用于测试)
# ============================================================================

async def main():
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python sonnet_worker.py '<任务描述>'")
        print("  python sonnet_worker.py convert <input_dir> <output_dir>")
        print("  python sonnet_worker.py index <docs_dir>")
        print("  python sonnet_worker.py search '<query>'")
        sys.exit(1)

    command = sys.argv[1]

    if command == "convert" and len(sys.argv) >= 4:
        result = await convert_html_docs(sys.argv[2], sys.argv[3])
    elif command == "index" and len(sys.argv) >= 3:
        result = await index_to_qdrant(sys.argv[2])
    elif command == "search" and len(sys.argv) >= 3:
        result = await search_knowledge_base(sys.argv[2])
    else:
        # 自由任务
        task = " ".join(sys.argv[1:])
        result = await run_rag_task(task)

    # 输出结果
    print("\n" + "="*80)
    print("Sonnet Worker 执行结果")
    print("="*80)

    if result["status"] == "success":
        print(f"\n✅ 任务完成")
        print(f"\nSession ID: {result.get('session_id', 'N/A')}")
        print(f"\n结果:\n{result.get('result', 'N/A')}")

        if result.get("tool_calls"):
            print(f"\n工具调用 ({len(result['tool_calls'])} 次):")
            for i, call in enumerate(result["tool_calls"][:10], 1):
                print(f"  {i}. {call['tool']}")

        if result.get("usage"):
            usage = result["usage"]
            print(f"\nToken 使用:")
            print(f"  输入: {usage.get('input_tokens', 0)}")
            print(f"  输出: {usage.get('output_tokens', 0)}")
            print(f"  总计: {usage.get('total_tokens', 0)}")
    else:
        print(f"\n❌ 任务失败")
        print(f"\n错误: {result.get('error', 'Unknown error')}")

    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
