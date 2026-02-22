#!/usr/bin/env python3
"""测试向量检索"""

import os
from qdrant_client import QdrantClient
from FlagEmbedding import BGEM3FlagModel

# 连接 Qdrant
client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))

# 加载模型
print("加载 BGE-M3 模型...")
model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

# 测试查询
query = "What is a Pod in Kubernetes?"
print(f"\n查询: {query}")

# 编码查询
print("编码查询...")
query_embeddings = model.encode([query], return_dense=True, return_sparse=True)

# 检索
print("执行检索...")
results = client.query_points(
    collection_name="knowledge-base",
    query=query_embeddings['dense_vecs'][0].tolist(),
    using="dense",
    limit=3
).points

# 显示结果
print(f"\n找到 {len(results)} 个结果:\n")
for i, result in enumerate(results, 1):
    print(f"{i}. Score: {result.score:.4f}")
    print(f"   ID: {result.id}")
    print(f"   Path: {result.payload.get('file_path', 'N/A')}")
    print(f"   Content: {result.payload.get('content', 'N/A')[:200]}...")
    print()
