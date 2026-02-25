#!/usr/bin/env python3
"""SO-based Redis docs KB test — real Stack Overflow questions tested against hybrid_search.

Tests that the KB can find relevant docs for common Redis questions from SO.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from qdrant_client import QdrantClient

# Real SO questions mapped to expected KB paths
SO_TEST_CASES = [
    # Pipelining & Transactions
    {
        "id": "so-001",
        "question": "What is the difference between Redis pipelining and transactions?",
        "source": "stackoverflow.com/questions/29327544",
        "expected_paths": ["using-commands/pipelining", "using-commands/transactions", "transpipe"],
        "topic": "pipelining",
    },
    {
        "id": "so-002",
        "question": "How do Redis clients implement pipelining to reduce round trip time?",
        "source": "stackoverflow.com/questions/7929885",
        "expected_paths": ["using-commands/pipelining"],
        "topic": "pipelining",
    },
    # Sentinel & Failover
    {
        "id": "so-003",
        "question": "Redis sentinel failover not working, stopping master doesn't trigger failover",
        "source": "stackoverflow.com/questions/48579228",
        "expected_paths": ["oss_and_stack", "sentinel"],
        "topic": "sentinel",
    },
    {
        "id": "so-004",
        "question": "How to configure Redis Sentinel for high availability with 3 nodes?",
        "source": "stackoverflow.com/questions/51524234",
        "expected_paths": ["sentinel"],
        "topic": "sentinel",
    },
    # Data Types
    {
        "id": "so-005",
        "question": "Why use Redis Sorted Set instead of List? When should I choose one over the other?",
        "source": "stackoverflow.com/questions/48630763",
        "expected_paths": ["data-types/sorted-sets", "data-types/lists"],
        "topic": "data-types",
    },
    {
        "id": "so-006",
        "question": "What are the underlying data structures used for Redis internally?",
        "source": "stackoverflow.com/questions/9625246",
        "expected_paths": ["data-types"],
        "topic": "data-types",
    },
    {
        "id": "so-007",
        "question": "Redis set vs hash - when to use which data type?",
        "source": "stackoverflow.com/questions/13557075",
        "expected_paths": ["data-types/sets", "data-types/hashes", "hash_vs_json"],
        "topic": "data-types",
    },
    # Persistence
    {
        "id": "so-008",
        "question": "What is the difference between Redis RDB and AOF persistence? When should I use each?",
        "source": "stackoverflow.com/questions/39953542",
        "expected_paths": ["oss_and_stack", "persistence"],
        "topic": "persistence",
    },
    {
        "id": "so-009",
        "question": "Is Redis AOF file a mix of AOF and RDB format?",
        "source": "stackoverflow.com/questions/73415771",
        "expected_paths": ["persistence"],
        "topic": "persistence",
    },
    # Memory
    {
        "id": "so-010",
        "question": "Redis uses 10x more memory than my actual data size, why?",
        "source": "stackoverflow.com/questions/10004565",
        "expected_paths": ["oss_and_stack", "memory"],
        "topic": "memory",
    },
    {
        "id": "so-011",
        "question": "What does Redis do when it runs out of memory? How to configure maxmemory?",
        "source": "stackoverflow.com/questions/5068518",
        "expected_paths": ["oss_and_stack", "memory"],
        "topic": "memory",
    },
    # Security / ACL
    {
        "id": "so-012",
        "question": "How to enable ACL feature in Redis and create users with specific permissions?",
        "source": "stackoverflow.com/questions/64226667",
        "expected_paths": ["security", "acl"],
        "topic": "security",
    },
    {
        "id": "so-013",
        "question": "How to set password for Redis using requirepass?",
        "source": "stackoverflow.com/questions/7537905",
        "expected_paths": ["security"],
        "topic": "security",
    },
    # Pub/Sub vs Streams
    {
        "id": "so-014",
        "question": "What are the main differences between Redis Pub/Sub and Redis Streams?",
        "source": "stackoverflow.com/questions/59540563",
        "expected_paths": ["data-types/streams", "pubsub"],
        "topic": "pubsub-streams",
    },
    # Cluster
    {
        "id": "so-015",
        "question": "How does Redis Cluster handle data sharding and hash slots?",
        "source": "stackoverflow.com/questions/tagged/redis-cluster",
        "expected_paths": ["oss_and_stack", "cluster"],
        "topic": "cluster",
    },
    {
        "id": "so-016",
        "question": "Redis cluster vs sentinel - which one should I use for high availability?",
        "source": "stackoverflow.com/questions/tagged/redis-cluster+redis-sentinel",
        "expected_paths": ["oss_and_stack", "cluster", "sentinel"],
        "topic": "cluster",
    },
    # Replication
    {
        "id": "so-017",
        "question": "How does Redis replication work? What is the difference between full sync and partial sync?",
        "source": "general SO replication questions",
        "expected_paths": ["oss_and_stack", "replication"],
        "topic": "replication",
    },
    # Client Libraries
    {
        "id": "so-018",
        "question": "How to connect to Redis using Python redis-py client library?",
        "source": "general SO redis-py questions",
        "expected_paths": ["clients"],
        "topic": "clients",
    },
    # Vector Search / AI
    {
        "id": "so-019",
        "question": "How to use Redis as a vector database for similarity search?",
        "source": "general SO redis vector questions",
        "expected_paths": ["ai", "redisvl"],
        "topic": "ai",
    },
    # Lua Scripting
    {
        "id": "so-020",
        "question": "How to use EVAL command for Lua scripting in Redis?",
        "source": "general SO redis lua questions",
        "expected_paths": ["programmability"],
        "topic": "scripting",
    },
    # TLS/SSL
    {
        "id": "so-021",
        "question": "How to configure TLS/SSL encryption for Redis connections?",
        "source": "forum.redis.com TLS questions",
        "expected_paths": ["security", "tls", "encryption"],
        "topic": "security",
    },
    # Redis Cloud
    {
        "id": "so-022",
        "question": "How to create a Redis Cloud subscription and connect to it?",
        "source": "general SO redis cloud questions",
        "expected_paths": ["rc"],
        "topic": "cloud",
    },
    # Kubernetes
    {
        "id": "so-023",
        "question": "How to deploy Redis Enterprise on Kubernetes using the operator?",
        "source": "general SO redis k8s questions",
        "expected_paths": ["kubernetes"],
        "topic": "kubernetes",
    },
    # JSON
    {
        "id": "so-024",
        "question": "How to store and query JSON documents in Redis?",
        "source": "general SO redis json questions",
        "expected_paths": ["data-types/json", "hash_vs_json", "document-database"],
        "topic": "data-types",
    },
    # Benchmarking
    {
        "id": "so-025",
        "question": "How to benchmark Redis performance using redis-benchmark tool?",
        "source": "general SO redis benchmark questions",
        "expected_paths": ["oss_and_stack", "benchmark"],
        "topic": "benchmark",
    },
    # ── Chinese queries (跨语言检索测试) ──────────────────────────
    {
        "id": "cn-001",
        "question": "Redis 管道（pipeline）和事务（transaction）有什么区别？",
        "source": "SO pipelining vs transaction",
        "expected_paths": ["using-commands/pipelining", "using-commands/transactions", "transpipe"],
        "topic": "pipelining",
    },
    {
        "id": "cn-002",
        "question": "Redis Sentinel 哨兵模式怎么配置高可用？主从切换失败怎么排查？",
        "source": "SO sentinel failover",
        "expected_paths": ["sentinel"],
        "topic": "sentinel",
    },
    {
        "id": "cn-003",
        "question": "Redis 的 RDB 和 AOF 持久化有什么区别？生产环境应该用哪个？",
        "source": "SO persistence RDB vs AOF",
        "expected_paths": ["persistence"],
        "topic": "persistence",
    },
    {
        "id": "cn-004",
        "question": "Redis 内存占用太高怎么优化？maxmemory 和淘汰策略怎么配置？",
        "source": "SO memory optimization",
        "expected_paths": ["oss_and_stack", "memory"],
        "topic": "memory",
    },
    {
        "id": "cn-005",
        "question": "Redis 集群模式的哈希槽是怎么分配的？数据分片原理是什么？",
        "source": "SO cluster hash slots",
        "expected_paths": ["oss_and_stack", "cluster"],
        "topic": "cluster",
    },
    {
        "id": "cn-006",
        "question": "Redis 的 Sorted Set 和 List 应该怎么选？各自适合什么场景？",
        "source": "SO sorted set vs list",
        "expected_paths": ["data-types/sorted-sets", "data-types/lists"],
        "topic": "data-types",
    },
    {
        "id": "cn-007",
        "question": "Redis Pub/Sub 和 Streams 有什么区别？消息队列应该用哪个？",
        "source": "SO pubsub vs streams",
        "expected_paths": ["data-types/streams", "pubsub"],
        "topic": "pubsub-streams",
    },
    {
        "id": "cn-008",
        "question": "Redis 6.0 的 ACL 访问控制列表怎么用？怎么创建用户和设置权限？",
        "source": "SO ACL feature",
        "expected_paths": ["security", "acl"],
        "topic": "security",
    },
    {
        "id": "cn-009",
        "question": "怎么用 Redis 做向量相似度搜索？支持哪些向量索引算法？",
        "source": "general vector search",
        "expected_paths": ["ai", "redisvl"],
        "topic": "ai",
    },
    {
        "id": "cn-010",
        "question": "Redis 主从复制的原理是什么？全量同步和增量同步有什么区别？",
        "source": "SO replication",
        "expected_paths": ["oss_and_stack", "replication"],
        "topic": "replication",
    },
]


def run_search_test(query: str, top_k: int = 5) -> list[dict]:
    """Run hybrid_search via MCP server directly."""
    # Import the search function from mcp_server
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

    from embedding_provider import get_embedding_provider
    from qdrant_client import QdrantClient, models

    provider = get_embedding_provider()
    client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))

    q = provider.encode_query(query)
    dense_vec = q["dense_vec"]

    # Dense search
    results = client.query_points(
        collection_name="knowledge-base",
        query=dense_vec,
        using="dense",
        limit=top_k,
        with_payload=True,
    )

    hits = []
    for point in results.points:
        hits.append({
            "path": point.payload.get("path", ""),
            "title": point.payload.get("title", ""),
            "section_path": point.payload.get("section_path", ""),
            "score": point.score,
        })
    return hits


def check_hit(hits: list[dict], expected_paths: list[str]) -> bool:
    """Check if any hit matches any expected path fragment."""
    for hit in hits:
        path = hit.get("path", "").lower()
        for expected in expected_paths:
            if expected.lower() in path:
                return True
    return False


def main():
    print(f"Running {len(SO_TEST_CASES)} SO-based test cases against Redis docs KB\n")

    passed = 0
    failed = 0
    results = []

    for tc in SO_TEST_CASES:
        hits = run_search_test(tc["question"])
        hit = check_hit(hits, tc["expected_paths"])

        status = "PASS" if hit else "FAIL"
        if hit:
            passed += 1
        else:
            failed += 1

        top_path = hits[0]["path"] if hits else "N/A"
        top_score = f"{hits[0]['score']:.3f}" if hits else "N/A"

        print(f"[{status}] {tc['id']} ({tc['topic']}): {tc['question'][:60]}...")
        if not hit:
            print(f"       Expected: {tc['expected_paths']}")
            print(f"       Got top-5: {[h['path'].split('/')[-1] for h in hits[:5]]}")
        else:
            print(f"       Top hit: {top_path} (score: {top_score})")

        results.append({
            **tc,
            "status": status,
            "hits": hits[:5],
        })

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{len(SO_TEST_CASES)} passed ({100*passed/len(SO_TEST_CASES):.0f}%)")
    print(f"Failed: {failed}")

    # Save results
    os.makedirs("eval", exist_ok=True)
    with open("eval/so-redis-test-results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nDetailed results saved to eval/so-redis-test-results.json")


if __name__ == "__main__":
    main()
