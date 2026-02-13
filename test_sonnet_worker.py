#!/usr/bin/env python3
"""测试 Sonnet Worker 基本功能"""

import asyncio
from sonnet_worker import run_rag_task

async def test_basic():
    """测试基本任务执行"""
    print("="*80)
    print("测试 1: 基本文件操作")
    print("="*80)

    result = await run_rag_task(
        task="列出当前目录下的所有 Python 文件",
        working_dir=".",
        allowed_tools=["Bash", "Glob"],
        enable_mcp=False
    )

    print(f"\n状态: {result['status']}")
    print(f"Session ID: {result.get('session_id', 'N/A')}")
    print(f"\n结果:\n{result.get('result', 'N/A')}")

    if result.get('tool_calls'):
        print(f"\n工具调用: {len(result['tool_calls'])} 次")
        for call in result['tool_calls'][:5]:
            print(f"  - {call['tool']}")

    if result.get('usage'):
        print(f"\nToken 使用: {result['usage']['total_tokens']}")

    return result

async def test_read_file():
    """测试文件读取"""
    print("\n" + "="*80)
    print("测试 2: 读取文件")
    print("="*80)

    result = await run_rag_task(
        task="读取 CLAUDE.md 文件并总结其内容",
        working_dir=".",
        allowed_tools=["Read"],
        enable_mcp=False
    )

    print(f"\n状态: {result['status']}")
    print(f"\n结果:\n{result.get('result', 'N/A')[:500]}...")

    return result

async def test_kb_skills():
    """测试 KB Skills 访问"""
    print("\n" + "="*80)
    print("测试 3: KB Skills 目录")
    print("="*80)

    result = await run_rag_task(
        task="列出 kb_skills 目录下的所有 skills，并简要说明每个 skill 的功能",
        working_dir="./kb_skills",
        allowed_tools=["Bash", "Glob", "Read"],
        enable_mcp=False
    )

    print(f"\n状态: {result['status']}")
    print(f"\n结果:\n{result.get('result', 'N/A')}")

    return result

async def main():
    print("\n🚀 Sonnet Worker 测试套件\n")

    # 测试 1: 基本操作
    result1 = await test_basic()

    # 测试 2: 文件读取
    result2 = await test_read_file()

    # 测试 3: KB Skills
    result3 = await test_kb_skills()

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    total_tokens = sum([
        result1.get('usage', {}).get('total_tokens', 0),
        result2.get('usage', {}).get('total_tokens', 0),
        result3.get('usage', {}).get('total_tokens', 0)
    ])

    print(f"\n✅ 所有测试完成")
    print(f"📊 总 Token 使用: {total_tokens}")
    print(f"💰 预估成本: ${total_tokens * 0.000003:.4f} (Sonnet 定价)")
    print("\n双层架构已就绪！")

if __name__ == "__main__":
    asyncio.run(main())
