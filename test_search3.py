#!/usr/bin/env python3
"""测试向量检索 - 正确的字段名"""

from qdrant_client import QdrantClient
from FlagEmbedding import BGEM3FlagModel

# 连接 Qdrant
client = QdrantClient(url="http://localhost:6333")

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
    limit=3,
    with_payload=True
).points

# 显示结果
print(f"\n✅ 找到 {len(results)} 个结果:\n")
for i, result in enumerate(results, 1):
    print(f"{'='*80}")
    print(f"结果 #{i}")
    print(f"{'='*80}")
    print(f"相似度得分: {result.score:.4f}")
    print(f"文档路径: {result.payload.get('path', 'N/A')}")
    print(f"文档标题: {result.payload.get('title', 'N/A')}")
    print(f"文档 ID: {result.payload.get('doc_id', 'N/A')}")
    print(f"Chunk 索引: {result.payload.get('chunk_index', 'N/A')}")
    print(f"置信度: {result.payload.get('confidence', 'N/A')}")
    print(f"标签: {result.payload.get('tags', 'N/A')}")
    print(f"\n内容片段:")
    text = result.payload.get('text', 'N/A')
    print(f"{text[:500]}...")
    print()
