#!/usr/bin/env python3
"""知识库检索 MCP Server。

提供向量检索能力，通过 MCP 协议供 Claude Code 调用。
这是项目中唯一需要常驻的服务（BGE-M3 模型 + Qdrant 连接）。

启动: python scripts/mcp_server.py
"""

import json
import logging
import os

from FlagEmbedding import BGEM3FlagModel, FlagReranker
from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient, models

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.environ.get("COLLECTION_NAME", "knowledge-base")
MODEL_NAME = os.environ.get("BGE_M3_MODEL", "BAAI/bge-m3")
RERANKER_NAME = os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")

# 初始化
mcp = FastMCP("knowledge-base")
_model = None
_reranker = None
_qdrant = None


def get_model():
    global _model
    if _model is None:
        log.info(f"加载 embedding 模型: {MODEL_NAME}")
        _model = BGEM3FlagModel(MODEL_NAME, use_fp16=True)
    return _model


def get_reranker():
    global _reranker
    if _reranker is None:
        log.info(f"加载 reranker 模型: {RERANKER_NAME}")
        _reranker = FlagReranker(RERANKER_NAME, use_fp16=True)
    return _reranker


def get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(url=QDRANT_URL)
    return _qdrant


@mcp.tool()
def hybrid_search(
    query: str,
    top_k: int = 5,
    min_score: float = 0.3,
    scope: str = "",
) -> str:
    """混合检索：dense + sparse 向量检索 + RRF 融合 + rerank。

    Args:
        query: 搜索查询
        top_k: 返回结果数
        min_score: 最低 rerank 得分
        scope: 限定目录范围，如 runbook/adr/api
    """
    model = get_model()
    reranker = get_reranker()
    client = get_qdrant()

    # 编码查询
    q = model.encode([query], return_dense=True, return_sparse=True)
    dense_vec = q["dense_vecs"][0].tolist()
    sparse = q["lexical_weights"][0]
    sparse_vec = models.SparseVector(
        indices=list(map(int, sparse.keys())),
        values=list(sparse.values()),
    )

    # 过滤条件
    filter_cond = None
    if scope:
        filter_cond = models.Filter(must=[
            models.FieldCondition(
                key="path",
                match=models.MatchText(text=f"/{scope}/"),
            )
        ])

    # Qdrant hybrid search
    try:
        results = client.query_points(
            collection_name=COLLECTION,
            prefetch=[
                models.Prefetch(
                    query=dense_vec, using="dense",
                    limit=20, filter=filter_cond,
                ),
                models.Prefetch(
                    query=sparse_vec, using="sparse",
                    limit=20, filter=filter_cond,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k * 3,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    if not results.points:
        return json.dumps([], ensure_ascii=False)

    # Rerank — 拼接 title + text 提升短文档的匹配质量
    # 注意：reranker 只做排序，不做过滤。最终判断权交给 Agent。
    pairs = []
    for p in results.points:
        title = p.payload.get("title", "")
        text = p.payload.get("text", "")
        rerank_text = f"{title}\n{text}" if title else text
        pairs.append((query, rerank_text))
    scores = reranker.compute_score(pairs)
    if isinstance(scores, (int, float)):
        scores = [scores]

    # RRF top-N 保护：reranker 不够可靠（对短文档/标题匹配评分过低），
    # 保证 RRF 排名靠前的结果不会被 reranker 完全淹没。
    # 策略：RRF top-3 必定保留，其余按 rerank 分数排序，合并去重取 top_k。
    RRF_PROTECT = 3
    indexed = list(zip(results.points, scores))
    # RRF 顺序就是 results.points 的原始顺序
    rrf_top = indexed[:RRF_PROTECT]
    rest = indexed[RRF_PROTECT:]
    # 对剩余按 rerank 分数排序
    rest_sorted = sorted(rest, key=lambda x: -x[1])
    # 合并：RRF top-N 在前（按 rerank 分数排序），再拼接剩余
    rrf_top_sorted = sorted(rrf_top, key=lambda x: -x[1])
    merged = rrf_top_sorted + rest_sorted
    # 去重（理论上不会重复，但防御性编程）
    seen_ids = set()
    ranked = []
    for point, score in merged:
        pid = point.id
        if pid not in seen_ids:
            seen_ids.add(pid)
            ranked.append((point, score))
    ranked = ranked[:top_k]

    # 格式化输出
    output = []
    for point, score in ranked:
        output.append({
            "score": round(float(score), 4),
            "doc_id": point.payload.get("doc_id", ""),
            "chunk_id": point.payload.get("chunk_id", ""),
            "chunk_index": point.payload.get("chunk_index", 0),
            "path": point.payload.get("path", ""),
            "title": point.payload.get("title", ""),
            "section_path": point.payload.get("section_path", ""),
            "confidence": point.payload.get("confidence", ""),
            "text": point.payload.get("text", ""),
        })

    # Agentic hint: 提醒 Agent 评估 chunk 充分性，必要时读取完整文档
    hint = ("[SEARCH NOTE] 以上为文档片段（chunks），可能不完整。"
            "如果 chunk 内容不足以完整回答问题（缺少具体步骤、命令、配置、代码），"
            "请用 Read(path) 读取对应文件获取完整上下文，严禁用通用知识补充。")
    result = json.dumps(output, ensure_ascii=False, indent=2)
    return result + "\n\n" + hint


@mcp.tool()
def keyword_search(query: str, top_k: int = 10) -> str:
    """关键词全文检索（Qdrant multilingual tokenizer）。

    Args:
        query: 搜索关键词
        top_k: 返回结果数
    """
    client = get_qdrant()

    try:
        results = client.scroll(
            collection_name=COLLECTION,
            scroll_filter=models.Filter(must=[
                models.FieldCondition(
                    key="text",
                    match=models.MatchText(text=query),
                )
            ]),
            limit=top_k,
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    output = []
    for point in results[0]:
        output.append({
            "doc_id": point.payload.get("doc_id", ""),
            "chunk_id": point.payload.get("chunk_id", ""),
            "path": point.payload.get("path", ""),
            "title": point.payload.get("title", ""),
            "text": point.payload.get("text", "")[:500],
        })

    return json.dumps(output, ensure_ascii=False, indent=2)


@mcp.tool()
def index_status() -> str:
    """查看索引状态：collection 信息、文档数、向量数。"""
    client = get_qdrant()

    try:
        info = client.get_collection(COLLECTION)
        return json.dumps({
            "collection": COLLECTION,
            "points_count": info.points_count,
            "status": str(info.status),
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
