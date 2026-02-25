#!/usr/bin/env python3
"""SO-based Redis docs KB test — real Stack Overflow questions tested against hybrid_search.

Tests that the KB can find relevant docs for common Redis questions from SO.
Questions are written in realistic SO style with context, setup details, and error messages.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from qdrant_client import QdrantClient

# Real SO questions mapped to expected KB paths
# Each question is written in realistic SO style with context and details
SO_TEST_CASES = [
    # Pipelining & Transactions
    {
        "id": "so-001",
        "question": (
            "I'm building a Python app that needs to execute ~5000 Redis SET commands "
            "to update user session data. I've read about both pipelining and MULTI/EXEC "
            "transactions but I'm confused about the difference. Pipelining seems to batch "
            "commands to reduce RTT, while MULTI/EXEC provides atomicity. Can I use both "
            "together? When should I choose one over the other? My main concern is throughput, "
            "not atomicity."
        ),
        "source": "stackoverflow.com/questions/29327544",
        "expected_paths": ["using-commands/pipelining", "using-commands/transactions", "transpipe"],
        "topic": "pipelining",
    },
    {
        "id": "so-002",
        "question": (
            "I'm using redis-py in a high-latency network environment (cross-region, ~50ms RTT). "
            "Sending 200 individual GET commands takes about 10 seconds. I know pipelining can "
            "help reduce round trip time by batching commands, but how exactly does it work under "
            "the hood? Does the client buffer all commands and send them in one TCP packet? "
            "What happens if the pipeline is very large — is there a risk of filling the TCP buffer?"
        ),
        "source": "stackoverflow.com/questions/7929885",
        "expected_paths": ["using-commands/pipelining"],
        "topic": "pipelining",
    },
    # Sentinel & Failover
    {
        "id": "so-003",
        "question": (
            "I have a Redis Sentinel setup with 3 sentinels and 1 master + 2 replicas on "
            "CentOS 7. When I stop the master with `redis-cli -p 6379 DEBUG SLEEP 60`, the "
            "sentinels detect +sdown but never reach +odown and no failover happens. My sentinel "
            "config has `sentinel monitor mymaster 192.168.1.10 6379 2` with quorum 2. All three "
            "sentinels are running and can ping each other. What am I missing? Is it a network "
            "or bind address issue?"
        ),
        "source": "stackoverflow.com/questions/48579228",
        "expected_paths": ["oss_and_stack", "sentinel"],
        "topic": "sentinel",
    },
    {
        "id": "so-004",
        "question": (
            "I'm setting up Redis Sentinel for high availability in production with 3 servers. "
            "Each server runs both a Redis instance and a Sentinel instance. Server A is master, "
            "B and C are replicas. I want automatic failover when the master goes down. What's "
            "the recommended sentinel.conf configuration? Specifically: what should the quorum "
            "value be for 3 sentinels? Should I set `sentinel down-after-milliseconds` to a low "
            "value for faster detection, or will that cause false positives?"
        ),
        "source": "stackoverflow.com/questions/51524234",
        "expected_paths": ["sentinel"],
        "topic": "sentinel",
    },
    # Data Types
    {
        "id": "so-005",
        "question": (
            "I'm building a real-time leaderboard for a mobile game with ~100K daily active "
            "users. I need to store player scores and quickly retrieve the top 100 players, "
            "as well as a specific player's rank. I initially used a Redis List with LPUSH and "
            "LRANGE, but updating a player's score requires removing and re-inserting which is "
            "O(N). Should I switch to a Sorted Set? What are the time complexity trade-offs "
            "between ZADD/ZRANK vs LPUSH/LRANGE for this use case?"
        ),
        "source": "stackoverflow.com/questions/48630763",
        "expected_paths": ["data-types/sorted-sets", "data-types/lists"],
        "topic": "data-types",
    },
    {
        "id": "so-006",
        "question": (
            "I'm trying to understand Redis internals for a systems design interview. I know "
            "Redis has Strings, Lists, Sets, Sorted Sets, and Hashes as user-facing data types, "
            "but what data structures does Redis actually use internally? For example, I've heard "
            "that small Lists use a ziplist encoding while larger ones use a linked list. What "
            "are the underlying data structures for each type, and when does Redis switch between "
            "encodings?"
        ),
        "source": "stackoverflow.com/questions/9625246",
        "expected_paths": ["data-types"],
        "topic": "data-types",
    },
    {
        "id": "so-007",
        "question": (
            "I need to store user profile data in Redis. Each user has fields like name, email, "
            "age, and preferences. I'm debating between using a Redis Hash (HSET user:123 name "
            "'John' email 'john@example.com') vs a Redis Set for storing unique attributes. "
            "When should I use a Hash vs a Set? Also, I've seen people mention Redis JSON as an "
            "alternative — how does that compare to Hashes for structured data?"
        ),
        "source": "stackoverflow.com/questions/13557075",
        "expected_paths": ["data-types/sets", "data-types/hashes", "hash_vs_json"],
        "topic": "data-types",
    },
    # Persistence
    {
        "id": "so-008",
        "question": (
            "I'm running Redis in production as a primary data store (not just cache) and need "
            "to configure persistence. I understand there are two options: RDB snapshots and AOF "
            "(Append Only File). RDB creates point-in-time snapshots at intervals, while AOF "
            "logs every write operation. My concern is data loss — with RDB, I could lose up to "
            "5 minutes of data if Redis crashes between snapshots. But AOF seems to have "
            "performance overhead. Can I use both together? What's the recommended setup for "
            "production where I need both performance and minimal data loss?"
        ),
        "source": "stackoverflow.com/questions/39953542",
        "expected_paths": ["oss_and_stack", "persistence"],
        "topic": "persistence",
    },
    {
        "id": "so-009",
        "question": (
            "I'm looking at my Redis AOF file and noticed it starts with the string 'REDIS' "
            "followed by binary data, which looks like an RDB preamble. Then the rest of the "
            "file has the normal AOF command format (*2\\r\\n$6\\r\\nSELECT...). Is the AOF file "
            "actually a mix of RDB and AOF format? When did Redis start doing this? I'm on "
            "Redis 7.0 and trying to understand the file format for a backup tool I'm building."
        ),
        "source": "stackoverflow.com/questions/73415771",
        "expected_paths": ["persistence"],
        "topic": "persistence",
    },
    # Memory
    {
        "id": "so-010",
        "question": (
            "I stored about 500MB of string data in Redis (verified by summing the sizes of "
            "all values), but `INFO memory` shows `used_memory_human: 4.8G` — almost 10x more "
            "than my actual data. I'm using Redis 6.2 on Linux with jemalloc. I understand "
            "there's some overhead for data structures, but 10x seems excessive. Running "
            "`MEMORY DOCTOR` says 'Sam, I have a few things to report' and mentions high "
            "fragmentation ratio. What's causing this and how can I reduce memory usage?"
        ),
        "source": "stackoverflow.com/questions/10004565",
        "expected_paths": ["oss_and_stack", "memory"],
        "topic": "memory",
    },
    {
        "id": "so-011",
        "question": (
            "I'm running Redis as a session cache with `maxmemory 2gb` and "
            "`maxmemory-policy volatile-lru`. Today I noticed Redis is using 2.3GB according "
            "to `INFO memory`, which exceeds my maxmemory setting. I thought maxmemory was a "
            "hard limit? Also, some keys without TTL are being evicted even though I set "
            "volatile-lru (which should only evict keys with an expire set). What does Redis "
            "actually do when it hits the maxmemory limit? Is the eviction policy not working "
            "correctly?"
        ),
        "source": "stackoverflow.com/questions/5068518",
        "expected_paths": ["oss_and_stack", "memory"],
        "topic": "memory",
    },
    # Security / ACL
    {
        "id": "so-012",
        "question": (
            "I just upgraded to Redis 6.0 and want to use the new ACL feature to create "
            "separate users for different microservices. Currently everything connects with "
            "the default user and `requirepass`. I want to create a user 'analytics' that can "
            "only run read commands (GET, MGET, HGETALL) on keys matching 'analytics:*', and "
            "another user 'writer' with full access. How do I set this up? Do I use `ACL SETUSER` "
            "or edit the ACL file? What's the syntax for key pattern restrictions?"
        ),
        "source": "stackoverflow.com/questions/64226667",
        "expected_paths": ["security", "acl"],
        "topic": "security",
    },
    {
        "id": "so-013",
        "question": (
            "I just installed Redis on an Ubuntu server and it's accessible without any "
            "authentication. I need to set a password before exposing it to the network. "
            "I know I can use `requirepass` in redis.conf, but I have a few questions: "
            "1) Can I set it at runtime with CONFIG SET without restarting? "
            "2) Is requirepass sent in plaintext or is it hashed? "
            "3) Should I also set `bind` to restrict which interfaces Redis listens on? "
            "I'm worried about security since I've read about Redis instances being compromised."
        ),
        "source": "stackoverflow.com/questions/7537905",
        "expected_paths": ["security"],
        "topic": "security",
    },
    # Pub/Sub vs Streams
    {
        "id": "so-014",
        "question": (
            "I need to implement a message queue in Redis for processing background jobs. "
            "I've been using Pub/Sub but realized that if a subscriber is disconnected when a "
            "message is published, it misses that message entirely — there's no replay or "
            "acknowledgment. I heard Redis Streams (XADD/XREAD/XACK) solve this with consumer "
            "groups and message persistence. What are the main differences between Pub/Sub and "
            "Streams? Is Streams basically a replacement for Pub/Sub, or do they serve different "
            "use cases?"
        ),
        "source": "stackoverflow.com/questions/59540563",
        "expected_paths": ["data-types/streams", "pubsub"],
        "topic": "pubsub-streams",
    },
    # Cluster
    {
        "id": "so-015",
        "question": (
            "I'm migrating from a single Redis instance to Redis Cluster for horizontal "
            "scaling. I understand the cluster uses 16384 hash slots distributed across nodes. "
            "When I run a command, Redis computes CRC16(key) % 16384 to determine which slot "
            "(and thus which node) handles it. But I'm confused about what happens during "
            "resharding — if I add a new node and migrate slots, what happens to in-flight "
            "requests? I'm getting MOVED and ASK redirections. What's the difference between "
            "MOVED and ASK? Do I need to handle these in my client code?"
        ),
        "source": "stackoverflow.com/questions/tagged/redis-cluster",
        "expected_paths": ["oss_and_stack", "cluster"],
        "topic": "cluster",
    },
    {
        "id": "so-016",
        "question": (
            "I need high availability for my Redis deployment and I'm confused about whether "
            "to use Redis Sentinel or Redis Cluster. My dataset is about 8GB and fits on a "
            "single machine. I don't need sharding, just automatic failover. Sentinel seems "
            "simpler — it monitors a master-replica setup and promotes a replica if the master "
            "fails. But Cluster also provides HA with automatic failover. What's the trade-off? "
            "Is Sentinel sufficient if I don't need to shard data, or should I just go with "
            "Cluster anyway for future-proofing?"
        ),
        "source": "stackoverflow.com/questions/tagged/redis-cluster+redis-sentinel",
        "expected_paths": ["oss_and_stack", "cluster", "sentinel"],
        "topic": "cluster",
    },
    # Replication
    {
        "id": "so-017",
        "question": (
            "I'm setting up Redis replication with 1 master and 2 replicas. During initial "
            "sync, I see in the logs that the master is doing a BGSAVE and sending the RDB "
            "file to the replica (full synchronization). But after that, it switches to sending "
            "just the replication stream. My questions: 1) What triggers a full sync vs partial "
            "sync? 2) If a replica disconnects briefly and reconnects, does it always need a "
            "full resync? 3) What is the replication backlog buffer and how should I size it "
            "to avoid unnecessary full resyncs?"
        ),
        "source": "general SO replication questions",
        "expected_paths": ["oss_and_stack", "replication"],
        "topic": "replication",
    },
    # Client Libraries
    {
        "id": "so-018",
        "question": (
            "I'm new to Redis and trying to connect from a Python application using redis-py. "
            "I installed it with `pip install redis` and wrote `r = redis.Redis(host='localhost', "
            "port=6379, db=0)` but I'm not sure about connection pooling. The docs mention "
            "ConnectionPool but the basic Redis() client seems to work fine. Do I need to "
            "explicitly create a connection pool for a web application handling 100+ concurrent "
            "requests? Also, should I use `redis.Redis` or `redis.StrictRedis`?"
        ),
        "source": "general SO redis-py questions",
        "expected_paths": ["clients"],
        "topic": "clients",
    },
    # Vector Search / AI
    {
        "id": "so-019",
        "question": (
            "I want to use Redis as a vector database for a RAG (Retrieval Augmented Generation) "
            "application. I have ~1M document embeddings (768-dimensional vectors from "
            "sentence-transformers) and need to do k-nearest-neighbor similarity search. I see "
            "Redis Stack has a vector search module (RediSearch). How do I create a vector index, "
            "store embeddings, and query for similar vectors? Is there a Python client like "
            "RedisVL that simplifies this? What index types are supported — FLAT vs HNSW?"
        ),
        "source": "general SO redis vector questions",
        "expected_paths": ["ai", "redisvl"],
        "topic": "ai",
    },
    # Lua Scripting
    {
        "id": "so-020",
        "question": (
            "I need to implement a rate limiter in Redis that atomically checks and increments "
            "a counter. Using separate GET and INCR commands has a race condition in concurrent "
            "scenarios. I know I can use EVAL with a Lua script to make it atomic, but I'm not "
            "sure about the syntax. How do I pass keys and arguments to a Lua script via EVAL? "
            "Also, what's the difference between EVAL and EVALSHA? Should I use Redis Functions "
            "instead of EVAL in Redis 7.0+?"
        ),
        "source": "general SO redis lua questions",
        "expected_paths": ["programmability"],
        "topic": "scripting",
    },
    # TLS/SSL
    {
        "id": "so-021",
        "question": (
            "I need to enable TLS encryption for Redis connections in production. Our security "
            "team requires all data in transit to be encrypted. I'm running Redis 6.2 and I see "
            "there's a `tls-port` config option. How do I generate the required certificates "
            "(CA cert, server cert, server key) and configure Redis to accept TLS connections? "
            "Do I also need to configure the client side? I'm using redis-py and need to pass "
            "SSL parameters."
        ),
        "source": "forum.redis.com TLS questions",
        "expected_paths": ["security", "tls", "encryption"],
        "topic": "security",
    },
    # Redis Cloud
    {
        "id": "so-022",
        "question": (
            "I want to try Redis Cloud for a new project instead of self-hosting. How do I "
            "create a subscription and get a database endpoint? I see there's a free tier. "
            "After creating the database, how do I connect to it from my application? Do I "
            "need to use TLS? Is there a REST API for managing Redis Cloud subscriptions "
            "programmatically?"
        ),
        "source": "general SO redis cloud questions",
        "expected_paths": ["rc"],
        "topic": "cloud",
    },
    # Kubernetes
    {
        "id": "so-023",
        "question": (
            "I'm deploying Redis Enterprise on Kubernetes using the Redis Enterprise Operator. "
            "I've installed the operator via Helm but I'm confused about the CRDs — there's "
            "RedisEnterpriseCluster and RedisEnterpriseDatabase. Do I create the cluster first "
            "and then databases inside it? How do I configure persistent storage for the cluster "
            "nodes? My K8s cluster uses EBS volumes on AWS. Also, how does the operator handle "
            "failover when a pod gets evicted?"
        ),
        "source": "general SO redis k8s questions",
        "expected_paths": ["kubernetes"],
        "topic": "kubernetes",
    },
    # JSON
    {
        "id": "so-024",
        "question": (
            "I need to store complex nested JSON documents in Redis and query them by nested "
            "fields. For example, I have user profiles like `{name: 'John', address: {city: "
            "'NYC', zip: '10001'}, tags: ['premium', 'active']}` and I want to find all users "
            "in a specific city. I know Redis has a JSON module (RedisJSON). How do I store "
            "JSON with JSON.SET, query nested paths with JSON.GET, and create secondary indexes "
            "on nested fields? Should I use JSON or just flatten everything into a Hash?"
        ),
        "source": "general SO redis json questions",
        "expected_paths": ["data-types/json", "hash_vs_json", "document-database"],
        "topic": "data-types",
    },
    # Benchmarking
    {
        "id": "so-025",
        "question": (
            "I want to benchmark my Redis server to establish a performance baseline before "
            "deploying to production. I know there's a built-in `redis-benchmark` tool. How "
            "do I use it to test specific commands like SET and GET with different payload sizes? "
            "I want to test with 100 concurrent connections and 1KB values. Also, the default "
            "benchmark uses random keys — can I configure it to use a specific key pattern? "
            "What's a reasonable ops/sec to expect on a modern server?"
        ),
        "source": "general SO redis benchmark questions",
        "expected_paths": ["oss_and_stack", "benchmark"],
        "topic": "benchmark",
    },
    # ── Chinese queries (跨语言检索测试) ──────────────────────────
    {
        "id": "cn-001",
        "question": (
            "我在用 Python 开发一个批量数据导入工具，需要往 Redis 里写入大约 5 万条数据。"
            "我看到 Redis 有 pipeline（管道）和 MULTI/EXEC（事务）两种批量执行方式。"
            "pipeline 是把多条命令打包发送减少网络往返，而事务是保证原子性执行。"
            "这两者能一起用吗？我的场景不需要原子性，只需要高吞吐，应该选哪个？"
            "pipeline 一次打包多少条命令比较合适？"
        ),
        "source": "SO pipelining vs transaction",
        "expected_paths": ["using-commands/pipelining", "using-commands/transactions", "transpipe"],
        "topic": "pipelining",
    },
    {
        "id": "cn-002",
        "question": (
            "我在 3 台 CentOS 服务器上部署了 Redis Sentinel 哨兵模式，1 主 2 从，每台机器上"
            "都跑了一个 sentinel 进程。配置了 `sentinel monitor mymaster 10.0.1.10 6379 2`，"
            "quorum 设为 2。但是当我手动 kill 掉 master 进程后，sentinel 日志只显示 +sdown，"
            "一直没有触发 +odown 和 failover。三个 sentinel 之间能互相 ping 通。"
            "是不是 bind 地址配置有问题？还是 quorum 设置不对？怎么排查主从切换失败？"
        ),
        "source": "SO sentinel failover",
        "expected_paths": ["sentinel"],
        "topic": "sentinel",
    },
    {
        "id": "cn-003",
        "question": (
            "我们的 Redis 是作为主数据库使用的（不只是缓存），需要配置持久化防止数据丢失。"
            "RDB 是定时快照，AOF 是记录每条写命令。我担心 RDB 模式下如果 Redis 崩溃会丢失"
            "两次快照之间的数据（比如 5 分钟）。AOF 的 everysec 策略最多丢 1 秒数据，但听说"
            "有性能开销。生产环境应该用哪个？能不能 RDB 和 AOF 同时开启？Redis 7.0 的 AOF "
            "文件格式是不是变了，开头有 RDB 前缀？"
        ),
        "source": "SO persistence RDB vs AOF",
        "expected_paths": ["persistence"],
        "topic": "persistence",
    },
    {
        "id": "cn-004",
        "question": (
            "我的 Redis 实例设置了 `maxmemory 4gb`，淘汰策略是 `volatile-lru`。但是 "
            "`INFO memory` 显示 `used_memory` 已经到了 4.6GB，超过了 maxmemory 限制。"
            "而且我发现一些没有设置 TTL 的 key 也被淘汰了，volatile-lru 不是应该只淘汰"
            "有过期时间的 key 吗？另外，`mem_fragmentation_ratio` 显示 1.8，碎片率很高。"
            "怎么优化 Redis 内存占用？maxmemory 到底是硬限制还是软限制？"
        ),
        "source": "SO memory optimization",
        "expected_paths": ["oss_and_stack", "memory"],
        "topic": "memory",
    },
    {
        "id": "cn-005",
        "question": (
            "我们要从单机 Redis 迁移到 Redis Cluster 集群模式。我知道集群用 16384 个哈希槽"
            "来分片数据，每个 key 通过 CRC16(key) % 16384 计算属于哪个槽。但我有几个疑问："
            "1) 新加节点后需要手动迁移哈希槽吗？还是自动重新分配？"
            "2) 迁移过程中客户端会收到 MOVED 和 ASK 重定向，这两个有什么区别？"
            "3) 多 key 操作（如 MGET）在集群模式下是不是不能用了？CROSSSLOT 错误怎么解决？"
        ),
        "source": "SO cluster hash slots",
        "expected_paths": ["oss_and_stack", "cluster"],
        "topic": "cluster",
    },
    {
        "id": "cn-006",
        "question": (
            "我在做一个手游实时排行榜，日活大概 10 万用户。需要存储玩家分数，快速查询 Top 100 "
            "和某个玩家的排名。一开始用 Redis List 存储，但更新分数需要先删除再插入，效率很低。"
            "后来看到 Sorted Set 可以用 ZADD 更新分数、ZREVRANK 查排名、ZREVRANGE 取 Top N，"
            "时间复杂度都是 O(log N)。Sorted Set 和 List 各自适合什么场景？"
            "如果排行榜数据量到千万级别，Sorted Set 还能扛住吗？"
        ),
        "source": "SO sorted set vs list",
        "expected_paths": ["data-types/sorted-sets", "data-types/lists"],
        "topic": "data-types",
    },
    {
        "id": "cn-007",
        "question": (
            "我需要在 Redis 里实现一个消息队列来处理异步任务。之前用 Pub/Sub 做的，但发现"
            "如果消费者断线期间发布的消息会丢失，没有重放机制。而且 Pub/Sub 没有消息确认，"
            "消费者处理失败了消息就没了。听说 Redis 5.0 引入的 Streams 支持消费者组、消息"
            "持久化和 ACK 确认机制（XADD/XREADGROUP/XACK）。Pub/Sub 和 Streams 的主要"
            "区别是什么？Streams 是不是可以完全替代 Pub/Sub？还是各有适用场景？"
        ),
        "source": "SO pubsub vs streams",
        "expected_paths": ["data-types/streams", "pubsub"],
        "topic": "pubsub-streams",
    },
    {
        "id": "cn-008",
        "question": (
            "我们升级到 Redis 6.0 后想用 ACL 功能给不同的微服务分配不同的访问权限。"
            "之前所有服务都用同一个 requirepass 密码连接。现在想创建一个只读用户 "
            "'readonly' 只能执行 GET/HGETALL 等读命令，访问 'cache:*' 前缀的 key；"
            "另一个用户 'admin' 有完全权限。ACL SETUSER 的语法是什么？"
            "key 的模式匹配怎么写？能不能限制用户只能访问特定前缀的 key？"
        ),
        "source": "SO ACL feature",
        "expected_paths": ["security", "acl"],
        "topic": "security",
    },
    {
        "id": "cn-009",
        "question": (
            "我想用 Redis 做向量相似度搜索，存储大约 100 万条文档的 embedding 向量"
            "（768 维，用 sentence-transformers 生成）。需要支持 KNN 查询找最相似的 "
            "Top-K 文档。我看到 Redis Stack 有向量搜索功能，支持 FLAT 和 HNSW 两种"
            "索引类型。FLAT 是暴力搜索，HNSW 是近似最近邻。100 万条数据应该选哪种？"
            "有没有 Python 客户端（比如 RedisVL）可以简化向量索引的创建和查询？"
        ),
        "source": "general vector search",
        "expected_paths": ["ai", "redisvl"],
        "topic": "ai",
    },
    {
        "id": "cn-010",
        "question": (
            "我在搭建 Redis 主从复制，1 主 2 从。初始同步时看到 master 日志在做 BGSAVE "
            "然后把 RDB 文件发给 replica（全量同步）。同步完成后切换到增量的复制流。"
            "我的问题是：1) 什么情况下会触发全量同步？什么情况下是增量同步？"
            "2) 如果 replica 短暂断开后重连，是不是一定要重新全量同步？"
            "3) repl-backlog-size 复制积压缓冲区应该设多大才能避免不必要的全量同步？"
        ),
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

        print(f"[{status}] {tc['id']} ({tc['topic']}): {tc['question'][:80]}...")
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
