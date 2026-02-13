#!/usr/bin/env python3
"""独立的 Embedding MCP Server

提供常驻的 embedding 和 reranking 服务，避免每次重复加载模型。

工具：
- encode_query: 编码查询文本 → dense + sparse vectors
- encode_documents: 批量编码文档 → dense + sparse vectors
- rerank: 重排序文档

优势：
- 模型常驻内存，无需重复加载（节省 2-3 分钟）
- 支持批量编码
- 可部署到远程 GPU 服务器
- 独立扩展和优化
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List

from FlagEmbedding import BGEM3FlagModel, FlagReranker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# 配置
BGE_M3_MODEL = os.environ.get("BGE_M3_MODEL", "BAAI/bge-m3")
RERANKER_MODEL = os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
USE_FP16 = os.environ.get("USE_FP16", "true").lower() == "true"

# 全局模型实例（常驻内存）
embedding_model = None
reranker_model = None


def load_models():
    """加载模型到内存（启动时执行一次）"""
    global embedding_model, reranker_model

    log.info(f"加载 embedding 模型: {BGE_M3_MODEL}")
    embedding_model = BGEM3FlagModel(
        BGE_M3_MODEL,
        use_fp16=USE_FP16,
        device="cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"
    )
    log.info("✅ Embedding 模型加载完成")

    log.info(f"加载 reranker 模型: {RERANKER_MODEL}")
    reranker_model = FlagReranker(
        RERANKER_MODEL,
        use_fp16=USE_FP16,
        device="cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"
    )
    log.info("✅ Reranker 模型加载完成")


async def encode_query(text: str) -> Dict[str, Any]:
    """编码查询文本

    Args:
        text: 查询文本

    Returns:
        {
            "dense": [float, ...],  # 1024d dense vector
            "sparse": {int: float, ...},  # sparse vector
            "colbert": [[float, ...], ...]  # colbert vectors (optional)
        }
    """
    try:
        log.info(f"编码查询: {text[:50]}...")

        # 使用 BGE-M3 编码
        result = embedding_model.encode(
            text,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False  # 暂不使用 ColBERT
        )

        return {
            "dense": result["dense_vecs"].tolist(),
            "sparse": {
                str(k): float(v)
                for k, v in zip(result["lexical_weights"][0].indices,
                               result["lexical_weights"][0].values)
            }
        }

    except Exception as e:
        log.error(f"编码查询失败: {e}")
        raise


async def encode_documents(texts: List[str], batch_size: int = 32) -> List[Dict[str, Any]]:
    """批量编码文档

    Args:
        texts: 文档文本列表
        batch_size: 批处理大小

    Returns:
        [
            {
                "dense": [float, ...],
                "sparse": {int: float, ...}
            },
            ...
        ]
    """
    try:
        log.info(f"批量编码 {len(texts)} 个文档")

        # 批量编码
        result = embedding_model.encode(
            texts,
            batch_size=batch_size,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False
        )

        # 转换格式
        encoded = []
        for i in range(len(texts)):
            encoded.append({
                "dense": result["dense_vecs"][i].tolist(),
                "sparse": {
                    str(k): float(v)
                    for k, v in zip(result["lexical_weights"][i].indices,
                                   result["lexical_weights"][i].values)
                }
            })

        log.info(f"✅ 编码完成: {len(encoded)} 个文档")
        return encoded

    except Exception as e:
        log.error(f"批量编码失败: {e}")
        raise


async def rerank(query: str, documents: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
    """重排序文档

    Args:
        query: 查询文本
        documents: 文档列表，每个文档包含 text 和其他元数据
        top_k: 返回前 k 个结果

    Returns:
        重排序后的文档列表，添加 rerank_score 字段
    """
    try:
        log.info(f"重排序 {len(documents)} 个文档")

        # 提取文档文本
        doc_texts = [doc.get("text", "") for doc in documents]

        # 构建 query-document pairs
        pairs = [[query, text] for text in doc_texts]

        # 计算 rerank 分数
        scores = reranker_model.compute_score(pairs, normalize=True)

        # 添加分数到文档
        for i, doc in enumerate(documents):
            doc["rerank_score"] = float(scores[i])

        # 按分数排序
        sorted_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)

        # 返回 top_k
        result = sorted_docs[:top_k]
        log.info(f"✅ 重排序完成，返回 top {len(result)} 个结果")

        return result

    except Exception as e:
        log.error(f"重排序失败: {e}")
        raise


# MCP Server 工具定义
TOOLS = [
    {
        "name": "encode_query",
        "description": "编码查询文本为 dense + sparse 向量",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "查询文本"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "encode_documents",
        "description": "批量编码文档为 dense + sparse 向量",
        "inputSchema": {
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "文档文本列表"
                },
                "batch_size": {
                    "type": "integer",
                    "description": "批处理大小",
                    "default": 32
                }
            },
            "required": ["texts"]
        }
    },
    {
        "name": "rerank",
        "description": "使用 reranker 模型重排序文档",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "查询文本"
                },
                "documents": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "文档列表，每个文档需包含 text 字段"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回前 k 个结果",
                    "default": 10
                }
            },
            "required": ["query", "documents"]
        }
    }
]


async def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """处理工具调用"""
    if tool_name == "encode_query":
        return await encode_query(arguments["text"])

    elif tool_name == "encode_documents":
        return await encode_documents(
            arguments["texts"],
            arguments.get("batch_size", 32)
        )

    elif tool_name == "rerank":
        return await rerank(
            arguments["query"],
            arguments["documents"],
            arguments.get("top_k", 10)
        )

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


async def main():
    """启动 MCP Server"""
    log.info("=" * 80)
    log.info("Embedding MCP Server 启动中...")
    log.info("=" * 80)

    # 加载模型
    load_models()

    log.info("\n✅ 服务就绪，等待请求...")
    log.info("=" * 80)

    # MCP Server 主循环
    while True:
        try:
            # 从 stdin 读取请求
            line = await asyncio.get_event_loop().run_in_executor(None, input)

            if not line:
                continue

            request = json.loads(line)

            # 处理请求
            if request.get("method") == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {"tools": TOOLS}
                }

            elif request.get("method") == "tools/call":
                tool_name = request["params"]["name"]
                arguments = request["params"].get("arguments", {})

                try:
                    result = await handle_tool_call(tool_name, arguments)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {"content": [{"type": "text", "text": json.dumps(result)}]}
                    }
                except Exception as e:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {"code": -1, "message": str(e)}
                    }

            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -32601, "message": "Method not found"}
                }

            # 发送响应
            print(json.dumps(response), flush=True)

        except KeyboardInterrupt:
            log.info("\n服务停止")
            break
        except Exception as e:
            log.error(f"处理请求失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
