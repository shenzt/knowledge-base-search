#!/usr/bin/env python3
"""知识库检索 MCP Server。

提供向量检索能力，通过 MCP 协议供 Claude Code 调用。
这是项目中唯一需要常驻的服务（BGE-M3 模型 + Qdrant 连接）。

启动: python scripts/mcp_server.py
"""

import json
import logging
import os

from FlagEmbedding import FlagReranker
from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient, models

from embedding_provider import EmbeddingProvider, get_embedding_provider

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.environ.get("COLLECTION_NAME", "knowledge-base")
RERANKER_NAME = os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")

# 初始化
mcp = FastMCP("knowledge-base")
_provider = None
_reranker = None
_qdrant = None


def get_provider() -> EmbeddingProvider:
    """延迟加载 embedding provider。"""
    global _provider
    if _provider is None:
        _provider = get_embedding_provider()
    return _provider


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
    model = get_provider()
    reranker = get_reranker()
    client = get_qdrant()

    # 编码查询
    q = model.encode_query(query)
    dense_vec = q["dense_vec"]
    sparse_vec = q["sparse_vec"]  # 可能为 None（外部 API 模式）

    # 过滤条件
    filter_cond = None
    if scope:
        filter_cond = models.Filter(must=[
            models.FieldCondition(
                key="path",
                match=models.MatchText(text=f"/{scope}/"),
            )
        ])

    # Qdrant hybrid search — sparse_vec 为 None 时用 BM25 全文检索替代
    try:
        prefetch_list = [
            models.Prefetch(
                query=dense_vec, using="dense",
                limit=20, filter=filter_cond,
            ),
        ]
        if sparse_vec is not None:
            prefetch_list.append(
                models.Prefetch(
                    query=sparse_vec, using="sparse",
                    limit=20, filter=filter_cond,
                ),
            )

        if len(prefetch_list) > 1:
            # hybrid: dense + sparse → RRF 融合
            results = client.query_points(
                collection_name=COLLECTION,
                prefetch=prefetch_list,
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=top_k * 3,
            )
        else:
            # dense + BM25 全文检索 → RRF 融合
            # Qdrant 的 MatchText 用 multilingual tokenizer 做 BM25-like 匹配
            bm25_filter = models.Filter(must=[
                models.FieldCondition(
                    key="text",
                    match=models.MatchText(text=query),
                )
            ])
            if filter_cond and filter_cond.must:
                bm25_filter.must.extend(filter_cond.must)

            # 先用 BM25 拿候选，再和 dense 做 RRF
            bm25_results = client.scroll(
                collection_name=COLLECTION,
                scroll_filter=bm25_filter,
                limit=20,
                with_vectors=False,
            )
            bm25_ids = [p.id for p in bm25_results[0]] if bm25_results[0] else []

            if bm25_ids:
                # 有 BM25 命中：用 dense prefetch + BM25 ID 过滤做 RRF
                bm25_prefetch = models.Prefetch(
                    query=dense_vec, using="dense",
                    limit=20,
                    filter=models.Filter(must=[
                        models.HasIdCondition(has_id=bm25_ids),
                    ]),
                )
                results = client.query_points(
                    collection_name=COLLECTION,
                    prefetch=[prefetch_list[0], bm25_prefetch],
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=top_k * 3,
                )
            else:
                # BM25 无命中：降级为 dense-only
                results = client.query_points(
                    collection_name=COLLECTION,
                    query=dense_vec,
                    using="dense",
                    limit=top_k * 3,
                    query_filter=filter_cond,
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
        item = {
            "score": round(float(score), 4),
            "doc_id": point.payload.get("doc_id", ""),
            "chunk_id": point.payload.get("chunk_id", ""),
            "chunk_index": point.payload.get("chunk_index", 0),
            "path": point.payload.get("path", ""),
            "title": point.payload.get("title", ""),
            "section_path": point.payload.get("section_path", ""),
            "confidence": point.payload.get("confidence", ""),
            "text": point.payload.get("text", ""),
        }
        # 预处理元数据（如果存在）
        doc_type = point.payload.get("doc_type", "")
        quality_score = point.payload.get("quality_score", 0)
        evidence_flags = point.payload.get("evidence_flags", {})
        gap_flags = point.payload.get("gap_flags", [])
        if doc_type or evidence_flags or gap_flags:
            hints = []
            if doc_type:
                hints.append(doc_type)
            if quality_score and quality_score < 5:
                hints.append(f"quality:{quality_score}/10")
            if gap_flags:
                hints.append(f"gaps:{','.join(gap_flags)}")
            # 压缩为单行提示，节省 context window
            item["agent_hint"] = f"[{' | '.join(hints)}]" if hints else ""
            item["evidence_flags"] = evidence_flags
        output.append(item)

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
