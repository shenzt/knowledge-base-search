#!/usr/bin/env python3
"""混合检索测试 - dense + sparse + RRF"""

import time
from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint, Prefetch
from FlagEmbedding import BGEM3FlagModel

# 初始化
client = QdrantClient(url="http://localhost:6333")
print("加载 BGE-M3 模型...")
model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

# 更全面的测试查询
test_queries = [
    # K8s 基础概念
    ("What is a Pod in Kubernetes?", "en", "k8s-basic"),
    ("Kubernetes Pod 的生命周期是什么？", "zh", "k8s-lifecycle"),
    ("How does Kubernetes Deployment work?", "en", "k8s-deployment"),

    # K8s 网络
    ("How to expose a service in Kubernetes?", "en", "k8s-service"),
    ("Kubernetes Ingress 如何配置？", "zh", "k8s-ingress"),

    # Redis 基础
    ("Redis 管道技术如何工作？", "zh", "redis-pipeline"),
    ("How does Redis pipelining improve performance?", "en", "redis-pipeline-en"),
    ("Redis 性能基准测试", "zh", "redis-benchmark"),

    # 跨语言测试
    ("What is Redis pipelining?", "en", "cross-lang-1"),
    ("Kubernetes Service 是什么？", "zh", "cross-lang-2"),
]

print("\n" + "="*80)
print("混合检索性能测试 (Dense + Sparse + RRF)")
print("="*80)

# 获取 collection 信息
collection_info = client.get_collection("knowledge-base")
print(f"\nCollection 信息:")
print(f"  总 chunks: {collection_info.points_count}")
print(f"  状态: {collection_info.status}")

results_summary = []

for i, (query, lang, test_id) in enumerate(test_queries, 1):
    print(f"\n{'='*80}")
    print(f"测试 #{i} [{test_id}]: {query}")
    print(f"{'='*80}")

    # 计时
    start_time = time.time()

    # 编码查询 (dense + sparse)
    query_embeddings = model.encode(
        [query],
        return_dense=True,
        return_sparse=True
    )

    # 转换 sparse 向量格式
    sparse_dict = query_embeddings['lexical_weights'][0]
    sparse_indices = list(sparse_dict.keys())
    sparse_values = [float(sparse_dict[k]) for k in sparse_indices]

    # 混合检索 (dense + sparse + RRF)
    from qdrant_client.models import SparseVector
    results = client.query_points(
        collection_name="knowledge-base",
        prefetch=[
            Prefetch(
                query=query_embeddings['dense_vecs'][0].tolist(),
                using="dense",
                limit=20,
            ),
            Prefetch(
                query=SparseVector(
                    indices=sparse_indices,
                    values=sparse_values
                ),
                using="sparse",
                limit=20,
            ),
        ],
        query=Prefetch(limit=5),  # RRF fusion
        with_payload=True
    ).points

    elapsed = time.time() - start_time

    print(f"\n⏱️  耗时: {elapsed:.3f} 秒")
    print(f"📊 返回结果: {len(results)} 个\n")

    if results:
        top_score = results[0].score
        results_summary.append({
            'test_id': test_id,
            'query': query,
            'lang': lang,
            'score': top_score,
            'time': elapsed
        })

        for j, result in enumerate(results[:3], 1):
            print(f"结果 #{j} (得分: {result.score:.4f})")
            print(f"  文档: {result.payload.get('title', 'N/A')}")
            print(f"  路径: {result.payload.get('path', 'N/A')}")
            content = result.payload.get('text', 'N/A')
            print(f"  内容: {content[:150]}...")
            print()
    else:
        print("⚠️  未找到结果")
        results_summary.append({
            'test_id': test_id,
            'query': query,
            'lang': lang,
            'score': 0.0,
            'time': elapsed
        })

# 统计分析
print("\n" + "="*80)
print("测试结果统计")
print("="*80)

en_scores = [r['score'] for r in results_summary if r['lang'] == 'en']
zh_scores = [r['score'] for r in results_summary if r['lang'] == 'zh']
all_scores = [r['score'] for r in results_summary]
all_times = [r['time'] for r in results_summary]

print(f"\n📊 准确性:")
print(f"  英文查询平均得分: {sum(en_scores)/len(en_scores):.4f}")
print(f"  中文查询平均得分: {sum(zh_scores)/len(zh_scores):.4f}")
print(f"  总体平均得分: {sum(all_scores)/len(all_scores):.4f}")
print(f"  最高得分: {max(all_scores):.4f}")
print(f"  最低得分: {min(all_scores):.4f}")

print(f"\n⏱️  性能:")
print(f"  平均耗时: {sum(all_times)/len(all_times):.3f} 秒")
print(f"  最快: {min(all_times):.3f} 秒")
print(f"  最慢: {max(all_times):.3f} 秒")

print(f"\n✅ 测试完成!")
print(f"✅ 使用混合检索 (Dense + Sparse + RRF)")
print(f"✅ 测试用例: {len(test_queries)} 个")
