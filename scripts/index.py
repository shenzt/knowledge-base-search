#!/usr/bin/env python3
"""知识库索引构建工具。

接收 chunks JSON（由 Claude Code agent 生成），编码为向量后写入 Qdrant。
也支持直接索引单个 Markdown 文件（简单按段落切分）。

用法:
  # 从 stdin 接收 Claude Code 生成的 chunks JSON
  echo '[{"doc_id":"abc","chunk_id":"abc-000","text":"...","metadata":{}}]' | python scripts/index.py

  # 索引单个文件（简单切分）
  python scripts/index.py --file docs/runbook/redis.md

  # 删除某个文档的所有 chunks
  python scripts/index.py --delete --doc-id abc12345

  # 查看索引状态
  python scripts/index.py --status
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone

import frontmatter
import numpy as np
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient, models

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.environ.get("COLLECTION_NAME", "knowledge-base")
MODEL_NAME = os.environ.get("BGE_M3_MODEL", "BAAI/bge-m3")

# 延迟加载模型（只在需要编码时加载）
_model = None


def get_model():
    global _model
    if _model is None:
        log.info(f"加载模型 {MODEL_NAME}...")
        _model = BGEM3FlagModel(MODEL_NAME, use_fp16=True)
    return _model


def get_qdrant():
    return QdrantClient(url=QDRANT_URL)


def ensure_collection(client: QdrantClient):
    """确保 collection 存在。"""
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION not in collections:
        log.info(f"创建 collection: {COLLECTION}")
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={
                "dense": models.VectorParams(size=1024, distance=models.Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(),
            },
        )


def index_chunks(chunks: list[dict]):
    """将 chunks 编码为向量并写入 Qdrant。

    chunks 格式: [{"doc_id", "chunk_id", "text", "metadata": {...}}]
    """
    if not chunks:
        log.info("没有 chunks 需要索引")
        return

    model = get_model()
    client = get_qdrant()
    ensure_collection(client)

    texts = [c["text"] for c in chunks]
    log.info(f"编码 {len(texts)} 个 chunks...")
    output = model.encode(texts, return_dense=True, return_sparse=True)

    points = []
    for i, chunk in enumerate(chunks):
        sparse = output["lexical_weights"][i]
        point_id = hashlib.md5(chunk["chunk_id"].encode()).hexdigest()

        payload = {
            "doc_id": chunk["doc_id"],
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
        }
        payload.update(chunk.get("metadata", {}))

        points.append(models.PointStruct(
            id=point_id,
            vector={
                "dense": output["dense_vecs"][i].tolist(),
                "sparse": models.SparseVector(
                    indices=list(map(int, sparse.keys())),
                    values=list(sparse.values()),
                ),
            },
            payload=payload,
        ))

    client.upsert(collection_name=COLLECTION, points=points)
    log.info(f"✅ 已索引 {len(points)} 个 chunks")


def delete_doc(doc_id: str):
    """删除某个文档的所有 chunks。"""
    client = get_qdrant()
    client.delete(
        collection_name=COLLECTION,
        points_selector=models.FilterSelector(
            filter=models.Filter(must=[
                models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))
            ])
        ),
    )
    log.info(f"✅ 已删除 doc_id={doc_id} 的所有 chunks")


def index_file(filepath: str):
    """索引单个 Markdown 文件（简单按双换行切分）。"""
    post = frontmatter.load(filepath)
    doc_id = post.metadata.get("id", hashlib.md5(filepath.encode()).hexdigest()[:8])
    title = post.metadata.get("title", os.path.basename(filepath))

    # 先删除旧 chunks
    try:
        delete_doc(doc_id)
    except Exception:
        pass

    # 简单按双换行切分
    paragraphs = [p.strip() for p in post.content.split("\n\n") if p.strip()]

    # 合并过短的段落
    chunks = []
    buf = ""
    for p in paragraphs:
        if len(buf) + len(p) < 3200:
            buf = buf + "\n\n" + p if buf else p
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)

    chunk_data = []
    for i, text in enumerate(chunks):
        chunk_data.append({
            "doc_id": doc_id,
            "chunk_id": f"{doc_id}-{i:03d}",
            "text": text,
            "metadata": {
                "path": filepath,
                "title": title,
                "chunk_index": i,
                "confidence": post.metadata.get("confidence", "unknown"),
                "tags": post.metadata.get("tags", []),
            },
        })

    index_chunks(chunk_data)


def show_status():
    """显示索引状态。"""
    client = get_qdrant()
    try:
        info = client.get_collection(COLLECTION)
        log.info(f"Collection: {COLLECTION}")
        log.info(f"  向量数: {info.points_count}")
        log.info(f"  状态: {info.status}")
    except Exception:
        log.info(f"Collection '{COLLECTION}' 不存在，运行索引命令创建")


def main():
    parser = argparse.ArgumentParser(description="知识库索引工具")
    parser.add_argument("--file", help="索引单个 Markdown 文件")
    parser.add_argument("--delete", action="store_true", help="删除文档")
    parser.add_argument("--doc-id", help="要删除的 doc_id")
    parser.add_argument("--status", action="store_true", help="查看索引状态")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.delete and args.doc_id:
        delete_doc(args.doc_id)
    elif args.file:
        index_file(args.file)
    else:
        # 从 stdin 读取 chunks JSON
        data = sys.stdin.read().strip()
        if data:
            chunks = json.loads(data)
            index_chunks(chunks)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
