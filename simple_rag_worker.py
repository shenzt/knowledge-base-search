#!/usr/bin/env python3
"""简化的 RAG Worker - 使用 Anthropic SDK 直接调用

不使用 Claude Agent SDK，而是直接使用 Anthropic SDK + MCP Server。
这样可以更好地控制执行流程和错误处理。
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List

# 添加 scripts 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from mcp_server import hybrid_search

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# 配置
WORKER_MODEL = os.environ.get("WORKER_MODEL", "claude-sonnet-4-20250514")


async def search_with_rag(query: str, top_k: int = 3) -> Dict[str, Any]:
    """使用 RAG 检索并回答问题

    Args:
        query: 用户问题
        top_k: 返回结果数

    Returns:
        包含检索结果和答案的字典
    """
    log.info(f"[Simple RAG] 查询: {query}")

    try:
        # 1. 调用混合检索
        search_results_json = hybrid_search(
            query=query,
            top_k=top_k,
            min_score=0.3
        )

        search_results = json.loads(search_results_json)
        log.info(f"[Simple RAG] 检索到 {len(search_results)} 个结果")

        if not search_results:
            return {
                "status": "success",
                "query": query,
                "search_results": [],
                "answer": "抱歉，在知识库中没有找到相关信息。",
                "sources": []
            }

        # 2. 构建上下文
        context_parts = []
        sources = []

        for i, result in enumerate(search_results, 1):
            context_parts.append(f"""
文档 {i}:
标题: {result.get('title', 'N/A')}
路径: {result.get('path', 'N/A')}
得分: {result.get('score', 0):.4f}
内容:
{result.get('text', '')}
""")
            sources.append({
                "title": result.get('title', 'N/A'),
                "path": result.get('path', 'N/A'),
                "score": result.get('score', 0),
                "doc_id": result.get('doc_id', 'N/A')
            })

        context = "\n---\n".join(context_parts)

        # 3. 使用 Anthropic SDK 生成答案
        try:
            import anthropic

            client = anthropic.Anthropic()

            prompt = f"""基于以下检索到的文档内容，回答用户的问题。

用户问题: {query}

检索到的文档:
{context}

要求:
1. 基于检索到的文档内容回答问题
2. 如果文档中没有足够信息，明确说明
3. 引用具体的文档来源
4. 使用清晰、准确的语言
5. 如果问题是中文，用中文回答；如果是英文，用英文回答

请回答:"""

            response = client.messages.create(
                model=WORKER_MODEL,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            answer = response.content[0].text

            log.info(f"[Simple RAG] 生成答案成功")

            return {
                "status": "success",
                "query": query,
                "search_results": search_results,
                "answer": answer,
                "sources": sources,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            }

        except Exception as e:
            log.error(f"[Simple RAG] 生成答案失败: {e}")
            # 如果 API 调用失败，至少返回检索结果
            return {
                "status": "partial",
                "query": query,
                "search_results": search_results,
                "answer": f"检索成功，但生成答案时出错: {e}",
                "sources": sources,
                "error": str(e)
            }

    except Exception as e:
        log.error(f"[Simple RAG] 检索失败: {e}")
        return {
            "status": "error",
            "query": query,
            "error": str(e)
        }


async def main():
    """CLI 入口"""
    if len(sys.argv) < 2:
        print("用法: python simple_rag_worker.py '<查询>'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    result = await search_with_rag(query)

    print("\n" + "="*80)
    print("Simple RAG Worker 执行结果")
    print("="*80)

    if result["status"] in ["success", "partial"]:
        print(f"\n✅ 查询: {result['query']}")
        print(f"\n📚 检索到 {len(result.get('search_results', []))} 个文档")

        for i, source in enumerate(result.get('sources', []), 1):
            print(f"\n  {i}. {source['title']}")
            print(f"     路径: {source['path']}")
            print(f"     得分: {source['score']:.4f}")

        print(f"\n💡 答案:\n{result.get('answer', 'N/A')}")

        if result.get('usage'):
            usage = result['usage']
            print(f"\n📊 Token 使用:")
            print(f"  输入: {usage['input_tokens']}")
            print(f"  输出: {usage['output_tokens']}")
            print(f"  总计: {usage['total_tokens']}")
    else:
        print(f"\n❌ 查询失败")
        print(f"\n错误: {result.get('error', 'Unknown error')}")

    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
