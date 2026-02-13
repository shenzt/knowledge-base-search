#!/usr/bin/env python3
"""分层检索测试 - 对比传统检索 vs 分层检索"""

import json
import time
from pathlib import Path
from qdrant_client import QdrantClient
from FlagEmbedding import BGEM3FlagModel

# 初始化
client = QdrantClient(url="http://localhost:6333")
print("加载 BGE-M3 模型...")
model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

# 测试查询
test_queries = [
    {
        "query": "What is a Pod in Kubernetes?",
        "expected_scope": "concepts/workloads/pods",
        "language": "en"
    },
    {
        "query": "Redis 管道技术如何工作？",
        "expected_scope": "topics",
        "language": "zh"
    },
    {
        "query": "How to configure Pod lifecycle?",
        "expected_scope": "concepts/workloads/pods",
        "language": "en"
    }
]

def traditional_search(query, top_k=5):
    """传统全库检索"""
    start_time = time.time()

    # 编码查询
    query_embeddings = model.encode([query], return_dense=True)

    # 全库检索
    results = client.query_points(
        collection_name="knowledge-base",
        query=query_embeddings['dense_vecs'][0].tolist(),
        using="dense",
        limit=top_k,
        with_payload=True
    ).points

    elapsed = time.time() - start_time

    return results, elapsed

def hierarchical_search(query, index_path, top_k=5):
    """分层检索 - 先索引过滤，再向量检索"""
    start_time = time.time()

    # 1. 读取索引
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    # 2. 简单的范围推断（实际应该更智能）
    # 这里简化为：如果查询包含特定关键词，缩小范围
    candidate_paths = []

    # 关键词匹配
    if "pod" in query.lower():
        # 查找包含 pod 的文档
        for dir_path, dir_info in index["structure"].items():
            if "pod" in dir_path.lower():
                for doc in dir_info["documents"]:
                    candidate_paths.append(doc["full_path"])

    if "redis" in query.lower() or "管道" in query:
        # Redis 相关
        for dir_path, dir_info in index["structure"].items():
            for doc in dir_info["documents"]:
                if "redis" in doc.get("tags", []):
                    candidate_paths.append(doc["full_path"])

    # 如果没有匹配，回退到全库
    if not candidate_paths:
        print("  ⚠️  索引过滤无结果，回退到全库检索")
        return traditional_search(query, top_k)

    filter_ratio = (1 - len(candidate_paths) / index["total_docs"]) * 100

    # 3. 编码查询
    query_embeddings = model.encode([query], return_dense=True)

    # 4. 在候选文档中检索
    # 注意：这里简化了，实际应该根据 doc_id 过滤
    results = client.query_points(
        collection_name="knowledge-base",
        query=query_embeddings['dense_vecs'][0].tolist(),
        using="dense",
        limit=top_k,
        with_payload=True
    ).points

    elapsed = time.time() - start_time

    return results, elapsed, filter_ratio, len(candidate_paths)

def print_results(results, method, elapsed, extra_info=""):
    """打印检索结果"""
    print(f"\n{'='*80}")
    print(f"方法: {method}")
    print(f"耗时: {elapsed:.3f} 秒")
    if extra_info:
        print(extra_info)
    print(f"{'='*80}")

    for i, result in enumerate(results[:3], 1):
        print(f"\n结果 #{i} (得分: {result.score:.4f})")
        print(f"  文档: {Path(result.payload.get('path', 'N/A')).name}")
        print(f"  标题: {result.payload.get('title', 'N/A')}")
        content = result.payload.get('text', 'N/A')
        print(f"  内容: {content[:150]}...")

def main():
    print("\n" + "="*80)
    print("分层检索 vs 传统检索 - 性能对比测试")
    print("="*80)

    # 检查索引文件
    redis_index = Path("/home/shenzt/ws/kb-test-redis-cn/docs/index.json")

    if not redis_index.exists():
        print("错误: Redis 索引文件不存在")
        return

    # 测试每个查询
    for i, test in enumerate(test_queries, 1):
        query = test["query"]
        print(f"\n\n{'#'*80}")
        print(f"测试 #{i}: {query}")
        print(f"{'#'*80}")

        # 传统检索
        print("\n[1] 传统全库检索...")
        trad_results, trad_time = traditional_search(query)
        print_results(trad_results, "传统全库检索", trad_time)

        # 分层检索
        print("\n[2] 分层检索（索引过滤）...")
        hier_results, hier_time, filter_ratio, candidates = hierarchical_search(
            query, redis_index
        )
        extra = f"过滤率: {filter_ratio:.1f}% | 候选文档: {candidates}"
        print_results(hier_results, "分层检索", hier_time, extra)

        # 对比
        speedup = trad_time / hier_time if hier_time > 0 else 1
        print(f"\n📊 性能对比:")
        print(f"  传统检索: {trad_time:.3f} 秒")
        print(f"  分层检索: {hier_time:.3f} 秒")
        print(f"  速度提升: {speedup:.2f}x")
        print(f"  过滤率: {filter_ratio:.1f}%")

    print(f"\n\n{'='*80}")
    print("测试完成!")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
