#!/usr/bin/env python3
"""快速混合检索对比测试"""

import os
import time
from qdrant_client import QdrantClient
from qdrant_client.models import SparseVector, Prefetch
from FlagEmbedding import BGEM3FlagModel

# 初始化
client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))
print("加载 BGE-M3 模型...")
model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

# 测试查询
test_queries = [
    ("What is a Pod in Kubernetes?", "英文-K8s"),
    ("Redis 管道技术如何工作？", "中文-Redis"),
    ("Kubernetes Service 是什么？", "中文-K8s"),
]

print("\n" + "="*80)
print("混合检索 vs 纯 Dense 检索对比")
print("="*80)

for query, label in test_queries:
    print(f"\n{'='*80}")
    print(f"查询 [{label}]: {query}")
    print(f"{'='*80}")

    # 编码
    embeddings = model.encode([query], return_dense=True, return_sparse=True)

    # 转换 sparse 格式
    sparse_dict = embeddings['lexical_weights'][0]
    sparse_indices = list(sparse_dict.keys())
    sparse_values = [float(sparse_dict[k]) for k in sparse_indices]

    # 方法1: 纯 Dense
    start = time.time()
    dense_results = client.query_points(
        collection_name="knowledge-base",
        query=embeddings['dense_vecs'][0].tolist(),
        using="dense",
        limit=3,
        with_payload=True
    ).points
    dense_time = time.time() - start

    # 方法2: 混合检索 (Dense + Sparse + RRF)
    # 使用 search 方法而不是 query_points
    from qdrant_client.models import SearchRequest, QueryRequest, FusionQuery
    start = time.time()
    hybrid_results = client.query_batch_points(
        collection_name="knowledge-base",
        requests=[
            QueryRequest(
                prefetch=[
                    Prefetch(
                        query=embeddings['dense_vecs'][0].tolist(),
                        using="dense",
                        limit=20,
                    ),
                    Prefetch(
                        query=SparseVector(indices=sparse_indices, values=sparse_values),
                        using="sparse",
                        limit=20,
                    ),
                ],
                query=FusionQuery(fusion="rrf"),
                limit=3,
                with_payload=True
            )
        ]
    )[0].points
    hybrid_time = time.time() - start

    # 对比结果
    print(f"\n📊 纯 Dense 检索:")
    print(f"   耗时: {dense_time:.3f}s | Top-1 得分: {dense_results[0].score:.4f}")
    print(f"   文档: {dense_results[0].payload.get('title', 'N/A')}")

    print(f"\n📊 混合检索 (Dense+Sparse+RRF):")
    print(f"   耗时: {hybrid_time:.3f}s | Top-1 得分: {hybrid_results[0].score:.4f}")
    print(f"   文档: {hybrid_results[0].payload.get('title', 'N/A')}")

    score_diff = hybrid_results[0].score - dense_results[0].score
    print(f"\n💡 得分提升: {score_diff:+.4f} ({score_diff/dense_results[0].score*100:+.1f}%)")

print("\n" + "="*80)
print("测试完成!")
print("="*80)
