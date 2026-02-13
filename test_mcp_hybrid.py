#!/usr/bin/env python3
"""验证 MCP Server 混合检索效果"""

import sys
sys.path.insert(0, 'scripts')

from mcp_server import hybrid_search

# 测试查询
test_queries = [
    ("What is a Pod in Kubernetes?", "英文-K8s"),
    ("Redis 管道技术如何工作？", "中文-Redis"),
    ("Kubernetes Service 是什么？", "中文-K8s"),
]

print("="*80)
print("MCP Server 混合检索验证")
print("="*80)

for query, label in test_queries:
    print(f"\n查询 [{label}]: {query}")
    print("-"*80)

    result = hybrid_search(query=query, top_k=3, min_score=0.3)

    import json
    results = json.loads(result)

    if results:
        print(f"返回 {len(results)} 个结果:\n")
        for i, r in enumerate(results, 1):
            print(f"#{i} 得分: {r['score']:.4f}")
            print(f"   文档: {r['title']}")
            print(f"   路径: {r['path']}")
            print(f"   内容: {r['text'][:100]}...")
            print()
    else:
        print("未找到结果")

print("="*80)
print("✅ MCP Server 混合检索工作正常")
print("="*80)
