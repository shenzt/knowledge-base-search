"""v5 评测用例 — 120 个真实问题
数据源:
  - redis-docs (234 docs): develop/ + operate/oss_and_stack/
  - awesome-llm-apps (207 docs): RAG, agents, multi-agent teams
  - local docs/ (3 docs): redis-failover, k8s-crashloop, api-auth
  - notfound: 知识库中不存在的主题

用例分布: 40 redis + 35 llm-apps + 15 local + 10 notfound + 20 新增 = 120
新增维度: 5 multi-hop + 5 cross-source + 5 ambiguous + 5 long-answer
"""

TEST_CASES_V5 = [
    # ══════════════════════════════════════════════════════════════
    # A. Redis Docs — 数据类型 (10)
    # ══════════════════════════════════════════════════════════════
    {"id": "redis-dt-001",
     "query": "What is the difference between Redis Sorted Sets and regular Sets?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "sorted-sets.md",
     "expected_keywords": ["sorted set", "score", "ranking"],
     "reference_answer": "Redis Sets are unordered collections of unique strings. Sorted Sets are similar but each member has an associated score (floating point). Members are ordered by score, enabling range queries by score or rank. Sorted Sets support commands like ZADD, ZRANGE, ZRANGEBYSCORE, ZRANK. Use cases include leaderboards, rate limiters, and priority queues."},

    {"id": "redis-dt-002",
     "query": "How do I use Redis Streams for message queuing?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "streams",
     "expected_keywords": ["stream", "XADD", "consumer"],
     "reference_answer": "Redis Streams is an append-only log data structure. Use XADD to add messages, XREAD to read. For consumer groups, use XGROUP CREATE to create a group, XREADGROUP to read as a consumer, and XACK to acknowledge. Streams support multiple consumers, message acknowledgment, pending entry lists, and automatic ID generation."},

    {"id": "redis-dt-003",
     "query": "Redis Bloom Filter 的误判率怎么配置？",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "bloom-filter.md",
     "expected_keywords": ["bloom", "error rate", "filter"],
     "reference_answer": "Redis Bloom Filter 通过 BF.RESERVE 命令配置误判率（error_rate）和预期容量（capacity）。error_rate 越低，内存占用越大。默认误判率为 0.01（1%）。BF.ADD 添加元素，BF.EXISTS 检查是否存在。Bloom Filter 只有假阳性，没有假阴性。"},

    {"id": "redis-dt-004",
     "query": "When should I use Redis Hashes vs JSON?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "hashes.md,compare-data-types.md,json",
     "expected_keywords": ["hash", "field", "HSET"],
     "reference_answer": "Redis Hashes store field-value pairs, good for flat objects. Use HSET/HGET for individual fields. Redis JSON (RedisJSON module) supports nested structures, JSONPath queries, and partial updates. Use Hashes for simple flat objects with field-level access. Use JSON for nested/complex documents needing path-based queries."},

    {"id": "redis-dt-005",
     "query": "How does HyperLogLog count unique elements in Redis?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "hyperloglogs.md",
     "expected_keywords": ["hyperloglog", "cardinality", "PFADD"],
     "reference_answer": "HyperLogLog is a probabilistic data structure for cardinality estimation using only ~12KB memory regardless of element count. PFADD adds elements, PFCOUNT returns approximate unique count (standard error 0.81%). PFMERGE combines multiple HyperLogLogs. Ideal for counting unique visitors, IPs, or queries."},

    {"id": "redis-dt-006",
     "query": "Redis Lists 作为消息队列和 Streams 有什么区别？",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "lists.md",
     "expected_keywords": ["list", "LPUSH", "RPOP"],
     "reference_answer": "Redis Lists 用 LPUSH/RPOP 实现简单队列，支持阻塞操作 BRPOP。但 Lists 没有消费者组、消息确认、消息 ID 等功能。Streams 支持消费者组（XGROUP）、消息确认（XACK）、消息 ID、范围查询、持久化。Streams 更适合生产级消息队列，Lists 适合简单的任务队列。"},

    {"id": "redis-dt-007",
     "query": "What are Redis Bitfields and when would I use them?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "bitfields.md",
     "expected_keywords": ["bitfield", "counter", "integer"],
     "reference_answer": "Redis Bitfields allow setting, incrementing, and getting integer values of arbitrary bit widths at arbitrary offsets in a string value. Use BITFIELD command with GET, SET, INCRBY subcommands. Supports signed (i) and unsigned (u) integers. Use cases: compact counters, flags, sensor readings, game stats where memory efficiency matters."},

    {"id": "redis-dt-008",
     "query": "How to store and query geospatial data in Redis?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "geospatial.md",
     "expected_keywords": ["geo", "GEOADD", "radius"],
     "reference_answer": "Use GEOADD to add longitude/latitude/member tuples. GEODIST calculates distance between members. GEOSEARCH finds members within a radius or box from a point or member. GEOPOS returns coordinates. Internally uses Sorted Sets with geohash encoding. Use cases: nearby search, delivery tracking, location-based services."},

    {"id": "redis-dt-009",
     "query": "Redis TimeSeries 适合什么场景？怎么配置 retention？",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "timeseries",
     "expected_keywords": ["time series", "retention", "TS."],
     "reference_answer": "Redis TimeSeries 适合 IoT 传感器数据、监控指标、股票价格等时序数据。TS.CREATE 创建时序键，RETENTION 参数设置数据保留时间（毫秒）。TS.ADD 添加数据点，TS.RANGE 范围查询。支持自动降采样（compaction rules）、标签过滤、聚合查询。"},

    {"id": "redis-dt-010",
     "query": "Compare Count-Min Sketch and Top-K in Redis probabilistic data structures",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "count-min-sketch.md",
     "expected_keywords": ["count-min", "frequency", "probabilistic"],
     "reference_answer": "Count-Min Sketch estimates frequency of elements with configurable error rate. CMS.INITBYDIM/CMS.INITBYPROB to create, CMS.INCRBY to count, CMS.QUERY to get frequency. Top-K maintains a list of k most frequent items. TOPK.ADD adds items, TOPK.LIST returns top-k. CMS is for frequency queries on any item; Top-K is for finding the most frequent items."},

    # ══════════════════════════════════════════════════════════════
    # B. Redis Docs — 运维管理 (15)
    # ══════════════════════════════════════════════════════════════
    {"id": "redis-ops-001",
     "query": "How does Redis Sentinel handle automatic failover?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "sentinel.md",
     "expected_keywords": ["sentinel", "failover", "master"],
     "reference_answer": "Redis Sentinel monitors master/replica instances. When a master is unreachable (down-after-milliseconds), Sentinels agree via quorum. The leader Sentinel selects the best replica (replication offset, priority), promotes it to master, reconfigures other replicas, and notifies clients. Requires at least 3 Sentinel instances for robustness."},

    {"id": "redis-ops-002",
     "query": "Redis cluster 是怎么做数据分片的？hash slot 机制是什么？",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "scaling.md",
     "expected_keywords": ["cluster", "hash slot", "16384"],
     "reference_answer": "Redis Cluster 将键空间分为 16384 个 hash slot。每个键通过 CRC16(key) % 16384 映射到一个 slot。每个节点负责一部分 slot。支持 hash tag（{tag}）让相关键映射到同一 slot。通过 CLUSTER ADDSLOTS/DELSLOTS 管理 slot 分配，支持在线 resharding。"},

    {"id": "redis-ops-003",
     "query": "What is the difference between RDB and AOF persistence in Redis?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "persistence.md",
     "expected_keywords": ["RDB", "AOF", "snapshot"],
     "reference_answer": "RDB creates point-in-time snapshots at intervals (SAVE/BGSAVE). Compact, fast restart, but may lose data between snapshots. AOF logs every write operation, can be configured with fsync policies (always/everysec/no). More durable but larger files. AOF rewrite compacts the log. Can use both: AOF for durability, RDB for backups. Redis 7+ supports Multi-Part AOF."},

    {"id": "redis-ops-004",
     "query": "How to configure Redis ACL for fine-grained access control?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "acl.md",
     "expected_keywords": ["ACL", "user", "permission"],
     "reference_answer": "Redis ACL controls per-user command and key access. ACL SETUSER creates users with passwords, command permissions (+/-command), key patterns (~pattern), and channel patterns (&pattern). ACL LIST shows all users. ACL LOAD loads from aclfile. Default user has full access. Supports command categories (+@read, -@dangerous)."},

    {"id": "redis-ops-005",
     "query": "Redis 主从复制的原理是什么？PSYNC 怎么工作？",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "replication.md",
     "expected_keywords": ["replication", "replica", "PSYNC"],
     "reference_answer": "Redis 复制分全量同步和增量同步。首次连接时 master 执行 BGSAVE 生成 RDB 发送给 replica（全量同步）。之后通过 replication backlog 增量同步。PSYNC 命令支持部分重同步：replica 断线重连后发送 replication ID + offset，如果 backlog 中有对应数据则增量同步，否则全量同步。"},

    {"id": "redis-ops-006",
     "query": "How to diagnose and fix Redis latency spikes?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "latency.md",
     "expected_keywords": ["latency", "slow", "monitor"],
     "reference_answer": "Use LATENCY LATEST/HISTORY to check latency events. SLOWLOG GET shows slow commands. Common causes: slow commands (KEYS, SORT), fork latency (RDB/AOF), swapping, network issues, large keys. Fixes: avoid O(N) commands, use SCAN instead of KEYS, tune vm.overcommit_memory, use lazyfree for async deletion, monitor with redis-cli --latency."},

    {"id": "redis-ops-007",
     "query": "Redis memory optimization best practices",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "memory-optimization.md",
     "expected_keywords": ["memory", "optimization", "encoding"],
     "reference_answer": "Use compact encodings: small hashes/lists/sets use ziplist/listpack. Set hash-max-ziplist-entries/value thresholds. Use OBJECT ENCODING to check. Avoid large keys. Use short key names. Enable activedefrag for fragmentation. Use 32-bit Redis for small datasets. MEMORY USAGE checks per-key memory. Consider data structure choice (Hash vs String for objects)."},

    {"id": "redis-ops-008",
     "query": "How to enable TLS encryption for Redis connections?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "encryption.md",
     "expected_keywords": ["TLS", "SSL", "encrypt"],
     "reference_answer": "Configure in redis.conf: tls-port, tls-cert-file, tls-key-file, tls-ca-cert-file. Enable tls-auth-clients for mutual TLS. Disable non-TLS port (port 0) for security. Client connects with --tls flag. Supports TLS for replication (tls-replication yes) and cluster bus (tls-cluster yes). Requires Redis built with TLS support (BUILD_TLS=yes)."},

    {"id": "redis-ops-009",
     "query": "Redis debugging 有哪些常用工具和命令？",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "debugging.md",
     "expected_keywords": ["debug", "OBJECT", "MEMORY"],
     "reference_answer": "常用调试命令：OBJECT ENCODING/REFCOUNT/IDLETIME 查看键内部信息。MEMORY USAGE 查看键内存占用。DEBUG OBJECT 获取详细信息。SLOWLOG 查看慢查询。MONITOR 实时监控所有命令（生产慎用）。CLIENT LIST 查看连接。INFO 查看服务器状态。redis-cli --bigkeys 扫描大键。"},

    {"id": "redis-ops-010",
     "query": "How to upgrade a Redis cluster without downtime?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "cluster.md",
     "expected_keywords": ["upgrade", "cluster", "rolling"],
     "reference_answer": "Rolling upgrade: upgrade replicas first, then failover masters one by one. Steps: 1) Upgrade a replica node, restart. 2) CLUSTER FAILOVER to promote upgraded replica to master. 3) Upgrade the old master (now replica). 4) Repeat for all nodes. Ensure cluster health between each step with CLUSTER INFO. Compatible versions can coexist during upgrade."},

    {"id": "redis-ops-011",
     "query": "What signals does Redis handle and how to gracefully shutdown?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "signals.md",
     "expected_keywords": ["signal", "SIGTERM", "shutdown"],
     "reference_answer": "SIGTERM triggers graceful shutdown: Redis saves RDB/AOF, closes connections, then exits. SIGINT same as SIGTERM. SIGUSR1 saves RDB. SIGKILL cannot be caught (immediate kill, may lose data). Use SHUTDOWN command for graceful stop (SHUTDOWN SAVE/NOSAVE). SHUTDOWN also handles AOF rewrite completion before exit."},

    {"id": "redis-ops-012",
     "query": "Redis pipelining 能提升多少性能？怎么用？",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "pipelining.md",
     "expected_keywords": ["pipeline", "RTT", "batch"],
     "reference_answer": "Pipelining 将多个命令一次性发送，不等待每个响应，减少 RTT 开销。可提升 5-10 倍吞吐量。客户端缓冲命令后批量发送，服务端按序执行并返回。注意：pipeline 不是原子操作（不同于 MULTI/EXEC）。大量命令时分批发送（如每批 1000 条）避免内存暴涨。"},

    {"id": "redis-ops-013",
     "query": "How do Redis transactions work? What is MULTI/EXEC?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "transactions.md",
     "expected_keywords": ["MULTI", "EXEC", "transaction"],
     "reference_answer": "MULTI starts a transaction, commands are queued (not executed). EXEC executes all queued commands atomically. DISCARD cancels. WATCH enables optimistic locking: if watched keys change before EXEC, transaction aborts (returns nil). Transactions are atomic but not isolated (no rollback on individual command failure). Errors in EXEC: syntax errors abort all, runtime errors skip only the failed command."},

    {"id": "redis-ops-014",
     "query": "Redis client-side caching mechanism and invalidation",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "client-side-caching.md",
     "expected_keywords": ["client-side", "caching", "invalidat"],
     "reference_answer": "Redis client-side caching uses tracking mode: CLIENT TRACKING ON. Server sends invalidation messages when tracked keys are modified. Two modes: default (server remembers which keys each client tracks) and broadcasting (clients subscribe to key prefixes). RESP3 protocol supports push notifications for invalidation. Reduces latency by avoiding network round-trips for frequently read keys."},

    {"id": "redis-ops-015",
     "query": "How to use Redis Lua scripting with EVAL command?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "eval-intro.md",
     "expected_keywords": ["EVAL", "Lua", "script"],
     "reference_answer": "EVAL runs Lua scripts atomically on the server. Syntax: EVAL script numkeys key1 key2 arg1 arg2. Access keys via KEYS[1], args via ARGV[1]. Call Redis commands with redis.call() or redis.pcall(). Scripts are atomic (no other command runs during execution). EVALSHA runs cached scripts by SHA1 hash. SCRIPT LOAD caches scripts. Use for complex atomic operations that need multiple commands."},

    # ══════════════════════════════════════════════════════════════
    # C. Redis Docs — SO 风格真实问题 (15)
    # ══════════════════════════════════════════════════════════════
    {"id": "redis-so-001",
     "query": "My Redis is using too much memory, maxmemory is set but keys keep growing. How does eviction work?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "eviction",
     "expected_keywords": ["eviction", "maxmemory", "policy"],
     "reference_answer": "When maxmemory is reached, Redis applies the configured maxmemory-policy. Policies: noeviction (return errors), allkeys-lru (evict least recently used), volatile-lru (evict LRU among keys with TTL), allkeys-random, volatile-random, volatile-ttl (evict shortest TTL), allkeys-lfu, volatile-lfu. Set via CONFIG SET maxmemory-policy. LRU is approximated using sampling (maxmemory-samples)."},

    {"id": "redis-so-002",
     "query": "Redis Sentinel 一直报 failover-abort-no-good-slave，怎么排查？",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "sentinel.md",
     "expected_keywords": ["sentinel", "failover", "replica"],
     "reference_answer": "failover-abort-no-good-slave 表示 Sentinel 找不到合适的 replica 来提升为 master。排查：1) 检查 replica 是否在线（SENTINEL replicas <master>）。2) 检查 replica 优先级（replica-priority 0 表示不参与选举）。3) 检查复制延迟是否超过阈值。4) 确认 Sentinel 配置的 master 名称正确。5) 检查网络连通性。"},

    {"id": "redis-so-003",
     "query": "I need to run SORT and SUNION across different Redis cluster nodes, but getting CROSSSLOT error",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "scaling.md,multi-key-operations.md,cluster",
     "expected_keywords": ["cluster", "hash slot", "CROSSSLOT"],
     "reference_answer": "CROSSSLOT error occurs when multi-key commands access keys in different hash slots. Solutions: 1) Use hash tags {tag} to force related keys to the same slot (e.g., user:{123}:name, user:{123}:email). 2) Move logic to Lua scripts (still requires same slot). 3) Handle cross-slot operations in application code. 4) Consider if cluster is necessary for your use case."},

    {"id": "redis-so-004",
     "query": "Redis AOF rewrite keeps failing with 'Can't open the append-only file', disk is not full",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "persistence.md",
     "expected_keywords": ["AOF", "rewrite", "append"],
     "reference_answer": "AOF rewrite failure with file open error (disk not full) common causes: 1) File descriptor limit (ulimit -n) too low. 2) Permission issues on the AOF directory. 3) Another process holding the file. 4) aof-use-rdb-preamble configuration issues. Check: CONFIG GET dir, verify directory permissions, check ulimit, check Redis logs for detailed error. Fix: increase open file limit, ensure correct directory ownership."},

    {"id": "redis-so-005",
     "query": "线上 Redis 延迟突然飙到 200ms，SLOWLOG 里全是 KEYS 命令，怎么办？",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "latency.md",
     "expected_keywords": ["latency", "SLOWLOG", "KEYS"],
     "reference_answer": "KEYS 命令是 O(N) 操作，会阻塞 Redis 主线程。解决方案：1) 用 SCAN 替代 KEYS（游标迭代，不阻塞）。2) 通过 ACL 禁止 KEYS 命令（ACL SETUSER ... -keys）。3) rename-command KEYS '' 在配置中禁用。4) 检查是哪个客户端在调用（CLIENT LIST + MONITOR）。5) 如果是监控工具在调用，修改监控配置。"},

    {"id": "redis-so-006",
     "query": "How to implement a rate limiter using Redis sorted sets?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "sorted-sets.md",
     "expected_keywords": ["sorted set", "score", "ZADD"],
     "reference_answer": "Sliding window rate limiter with Sorted Sets: 1) ZADD key <timestamp> <unique_id> to record each request. 2) ZREMRANGEBYSCORE key 0 <now - window_size> to remove expired entries. 3) ZCARD key to count requests in window. 4) If count > limit, reject. Use MULTI/EXEC for atomicity. Score = timestamp, member = unique request ID. Set TTL on the key equal to window size."},

    {"id": "redis-so-007",
     "query": "Redis keyspace notifications 怎么配置？我想监听 key 过期事件",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "keyspace-notifications.md",
     "expected_keywords": ["keyspace", "notification", "expired"],
     "reference_answer": "配置 notify-keyspace-events 参数启用通知。监听过期事件：CONFIG SET notify-keyspace-events Ex（E=keyevent, x=expired）。订阅：SUBSCRIBE __keyevent@0__:expired。K=keyspace 事件，E=keyevent 事件。事件类型：g=通用命令，$=string，l=list，s=set，h=hash，z=sorted set，x=expired，e=evicted。注意：过期通知不保证实时性。"},

    {"id": "redis-so-008",
     "query": "What is the Redis RESP protocol? How does client-server communication work?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "protocol-spec.md",
     "expected_keywords": ["RESP", "protocol", "bulk string"],
     "reference_answer": "RESP (Redis Serialization Protocol) is the wire protocol for client-server communication. RESP2 types: Simple Strings (+OK), Errors (-ERR), Integers (:1), Bulk Strings ($6\\r\\nfoobar), Arrays (*2). Commands sent as arrays of bulk strings. RESP3 adds: Maps, Sets, Doubles, Booleans, Nulls, Push notifications. Clients send commands, server responds with typed data. Text-based, human-readable."},

    {"id": "redis-so-009",
     "query": "Redis cluster spec says 16384 hash slots, why this number? How are keys mapped?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "cluster-spec.md",
     "expected_keywords": ["16384", "CRC16", "hash slot"],
     "reference_answer": "16384 hash slots chosen as a balance: enough for up to 1000 nodes (each gets ~16 slots minimum), small enough for efficient bitmap representation (2KB) in cluster bus messages. Key mapping: CRC16(key) mod 16384. Hash tags: if key contains {tag}, only the content inside {} is hashed, allowing related keys to share a slot."},

    {"id": "redis-so-010",
     "query": "我的 Redis 用了 10GB 内存但只存了 2GB 数据，内存碎片怎么处理？",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "memory-optimization.md",
     "expected_keywords": ["memory", "fragmentation", "jemalloc"],
     "reference_answer": "内存碎片率 = used_memory_rss / used_memory（INFO memory 查看）。碎片率 > 1.5 需要处理。解决方案：1) 启用 activedefrag（CONFIG SET activedefrag yes），Redis 自动整理碎片。2) 调整 active-defrag-threshold-lower/upper 控制触发阈值。3) 重启 Redis（最彻底但有停机）。4) jemalloc 是默认分配器，碎片率通常较低。5) 避免频繁删除大量不同大小的键。"},

    {"id": "redis-so-011",
     "query": "How to set up Redis Sentinel with 3 nodes for high availability?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "sentinel.md",
     "expected_keywords": ["sentinel", "quorum", "monitor"],
     "reference_answer": "Minimum 3 Sentinel instances for majority voting. Config: sentinel monitor mymaster <ip> <port> 2 (quorum=2). sentinel down-after-milliseconds mymaster 5000. sentinel failover-timeout mymaster 60000. Each Sentinel needs its own config file. Start with redis-sentinel /path/to/sentinel.conf. Sentinels auto-discover each other via the monitored master's Pub/Sub."},

    {"id": "redis-so-012",
     "query": "Redis Functions vs Lua scripts — what's the difference and when to use which?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "functions-intro.md",
     "expected_keywords": ["function", "FCALL", "library"],
     "reference_answer": "Redis Functions (7.0+) are persistent, named, and organized in libraries. FUNCTION LOAD registers a library, FCALL calls a function by name. Lua scripts (EVAL/EVALSHA) are ephemeral, identified by SHA1 hash, lost on restart. Functions survive restarts, support library management, and are the recommended approach. Both execute atomically on the server. Functions use the same Lua engine but with better lifecycle management."},

    {"id": "redis-so-013",
     "query": "How to benchmark Redis performance? What tool should I use?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "benchmarks",
     "expected_keywords": ["benchmark", "redis-benchmark", "throughput"],
     "reference_answer": "redis-benchmark is the built-in tool. Usage: redis-benchmark -h host -p port -c clients -n requests -d datasize. Key flags: -t (specific tests like SET,GET), -P (pipeline), -q (quiet, summary only), --csv (CSV output). Measures throughput (requests/sec) and latency percentiles. For realistic benchmarks: use pipelining, test with actual data sizes, use multiple clients, test on production-like hardware."},

    {"id": "redis-so-014",
     "query": "Redis vector sets 怎么做 filtered search？能结合标签过滤吗？",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "filtered-search.md,vector-database.md,vector-sets",
     "expected_keywords": ["vector", "filter", "search"],
     "reference_answer": "Redis Vector Sets 支持 filtered search，通过 VSIM 命令的 FILTER 参数实现。可以结合标签/属性过滤向量搜索结果。使用 VADD 添加向量时可附加属性，VSIM 搜索时用 FILTER 表达式过滤。支持数值范围、字符串匹配等过滤条件。这是 pre-filtering 方式，先过滤再做向量相似度计算。"},

    {"id": "redis-so-015",
     "query": "How to install Redis Stack on Ubuntu with apt?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "apt.md,install-redis-on-linux.md,ubuntu,linux.md",
     "expected_keywords": ["install", "apt", "ubuntu"],
     "reference_answer": "Install Redis on Ubuntu: 1) Add Redis APT repository: curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg. 2) Add repo to sources.list. 3) sudo apt-get update && sudo apt-get install redis. For Redis Stack: use redis-stack-server package from the same repository. Start with systemctl start redis-stack-server."},

    # ══════════════════════════════════════════════════════════════
    # D. Awesome LLM Apps — RAG 相关 (12)
    # ══════════════════════════════════════════════════════════════
    {"id": "llm-rag-001",
     "query": "How to build a local RAG agent with Llama?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "local_rag_agent",
     "expected_keywords": ["RAG", "local", "Llama"]},

    {"id": "llm-rag-002",
     "query": "What is Corrective RAG and how does it improve retrieval quality?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "corrective_rag",
     "expected_keywords": ["corrective", "RAG", "retrieval"]},

    {"id": "llm-rag-003",
     "query": "怎么用 Agentic RAG 实现带推理能力的检索？",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "agentic_rag",
     "expected_keywords": ["agentic", "RAG", "reasoning"]},

    {"id": "llm-rag-004",
     "query": "How to build a RAG app that can chat with PDF documents?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "chat_with_pdf",
     "expected_keywords": ["PDF", "chat", "RAG"]},

    {"id": "llm-rag-005",
     "query": "What is Vision RAG? How to do RAG with images?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "vision_rag",
     "expected_keywords": ["vision", "image", "RAG"]},

    {"id": "llm-rag-006",
     "query": "How to build a RAG chain using LangChain?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "rag_chain,rag_database_routing,rag.md",
     "expected_keywords": ["RAG", "chain", "LangChain"]},

    {"id": "llm-rag-007",
     "query": "How to chat with YouTube videos using RAG?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "chat_with_youtube",
     "expected_keywords": ["YouTube", "video", "chat"]},

    {"id": "llm-rag-008",
     "query": "How to build a RAG app with Cohere Command R?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "rag_with_cohere,rag_agent_cohere,cohere",
     "expected_keywords": ["Cohere", "RAG", "command"]},

    {"id": "llm-rag-009",
     "query": "Can I chat with my Gmail inbox using an LLM?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "chat_with_gmail",
     "expected_keywords": ["Gmail", "email", "chat"]},

    {"id": "llm-rag-010",
     "query": "How to build a chat app for research papers?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "chat_with_research_papers,chat_with_pdf",
     "expected_keywords": ["research", "paper", "chat"]},

    {"id": "llm-rag-011",
     "query": "How to chat with a GitHub repository using RAG?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "chat_with_github",
     "expected_keywords": ["GitHub", "repository", "chat"]},

    {"id": "llm-rag-012",
     "query": "What is a streaming AI chatbot and how to build one?",
     "source": "qdrant", "category": "llm-rag",
     "expected_doc": "streaming_ai_chatbot",
     "expected_keywords": ["streaming", "chatbot", "real-time"]},

    # ══════════════════════════════════════════════════════════════
    # E. Awesome LLM Apps — AI Agents (13)
    # ══════════════════════════════════════════════════════════════
    {"id": "llm-agent-001",
     "query": "How to build a multi-agent finance team with AI?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "ai_finance_agent_team",
     "expected_keywords": ["finance", "agent", "team"]},

    {"id": "llm-agent-002",
     "query": "What is an AI recruitment agent team? How does it work?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "ai_recruitment_agent_team",
     "expected_keywords": ["recruitment", "agent", "hiring"]},

    {"id": "llm-agent-003",
     "query": "How to build an AI travel planner with multiple agents?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "ai_travel_planner",
     "expected_keywords": ["travel", "planner", "agent"]},

    {"id": "llm-agent-004",
     "query": "AI agent that can play chess — how is it built?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "ai_chess_agent",
     "expected_keywords": ["chess", "game", "agent"]},

    {"id": "llm-agent-005",
     "query": "How to build an AI legal agent team for document review?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "ai_legal_agent_team",
     "expected_keywords": ["legal", "agent", "document"]},

    {"id": "llm-agent-006",
     "query": "What is an AI SEO audit team and how does it analyze websites?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "ai_seo_audit",
     "expected_keywords": ["SEO", "audit", "website"]},

    {"id": "llm-agent-007",
     "query": "How to build a competitor intelligence agent with AI?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "ai_competitor_intelligence",
     "expected_keywords": ["competitor", "intelligence", "analysis"]},

    {"id": "llm-agent-008",
     "query": "AI agent for web scraping — what tools does it use?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "web_scrapping_ai_agent",
     "expected_keywords": ["scraping", "web", "agent"]},

    {"id": "llm-agent-009",
     "query": "How to fine-tune Llama 3.2 for a specific task?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "llama3.2_finetuning",
     "expected_keywords": ["fine-tune", "Llama", "training"]},

    {"id": "llm-agent-010",
     "query": "How to add persistent memory to an LLM application?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "llm_app_personalized_memory",
     "expected_keywords": ["memory", "personalized", "persistent"]},

    {"id": "llm-agent-011",
     "query": "How to build a voice RAG agent using OpenAI SDK?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "voice_rag",
     "expected_keywords": ["voice", "RAG", "audio"]},

    {"id": "llm-agent-012",
     "query": "What is an AI VC due diligence agent team?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "ai_vc_due_diligence",
     "expected_keywords": ["VC", "due diligence", "investment"]},

    {"id": "llm-agent-013",
     "query": "How to build an AI teaching agent team for education?",
     "source": "qdrant", "category": "llm-agent",
     "expected_doc": "ai_teaching_agent_team",
     "expected_keywords": ["teaching", "education", "agent"]},

    # ══════════════════════════════════════════════════════════════
    # F. Awesome LLM Apps — 框架教程 (10)
    # ══════════════════════════════════════════════════════════════
    {"id": "llm-fw-001",
     "query": "OpenAI Agents SDK crash course — how to get started?",
     "source": "qdrant", "category": "llm-framework",
     "expected_doc": "openai_sdk_crash_course",
     "expected_keywords": ["OpenAI", "SDK", "agent"]},

    {"id": "llm-fw-002",
     "query": "Google ADK crash course for building AI agents",
     "source": "qdrant", "category": "llm-framework",
     "expected_doc": "google_adk_crash_course",
     "expected_keywords": ["Google", "ADK", "agent"]},

    {"id": "llm-fw-003",
     "query": "How to build a multimodal AI agent?",
     "source": "qdrant", "category": "llm-framework",
     "expected_doc": "multimodal_ai_agent,multimodal_design_agent",
     "expected_keywords": ["multimodal", "vision", "agent"]},

    {"id": "llm-fw-004",
     "query": "How to build an AI code reviewer agent?",
     "source": "qdrant", "category": "llm-framework",
     "expected_doc": "code-reviewer,ai_consultant_agent,multi_agent",
     "expected_keywords": ["code", "review", "agent"]},

    {"id": "llm-fw-005",
     "query": "What is an AI customer support voice agent?",
     "source": "qdrant", "category": "llm-framework",
     "expected_doc": "customer_support_voice_agent",
     "expected_keywords": ["customer", "support", "voice"]},

    {"id": "llm-fw-006",
     "query": "How to build a resume job matcher with AI?",
     "source": "qdrant", "category": "llm-framework",
     "expected_doc": "resume_job_matcher",
     "expected_keywords": ["resume", "job", "match"]},

    {"id": "llm-fw-007",
     "query": "AI real estate agent team — how does it analyze properties?",
     "source": "qdrant", "category": "llm-framework",
     "expected_doc": "ai_real_estate_agent_team",
     "expected_keywords": ["real estate", "property", "agent"]},

    {"id": "llm-fw-008",
     "query": "How to build an AI sales intelligence agent?",
     "source": "qdrant", "category": "llm-framework",
     "expected_doc": "ai_sales_intelligence",
     "expected_keywords": ["sales", "intelligence", "agent"]},

    {"id": "llm-fw-009",
     "query": "What is an AI game design agent team?",
     "source": "qdrant", "category": "llm-framework",
     "expected_doc": "ai_game_design_agent_team",
     "expected_keywords": ["game", "design", "agent"]},

    {"id": "llm-fw-010",
     "query": "How to build an AI services agency with multiple agents?",
     "source": "qdrant", "category": "llm-framework",
     "expected_doc": "ai_services_agency",
     "expected_keywords": ["services", "agency", "agent"]},

    # ══════════════════════════════════════════════════════════════
    # G. Local Docs (15)
    # ══════════════════════════════════════════════════════════════
    {"id": "local-001",
     "query": "READONLY You can't write against a read only replica 这个报错怎么解决",
     "source": "local", "category": "redis-failover",
     "expected_doc": "redis-failover.md",
     "expected_keywords": ["READONLY", "replica", "failover"]},

    {"id": "local-002",
     "query": "kubectl describe pod 显示 OOMKilled 怎么办",
     "source": "local", "category": "k8s-crashloop",
     "expected_doc": "kubernetes-pod-crashloop.md",
     "expected_keywords": ["OOMKilled", "memory", "limit"]},

    {"id": "local-003",
     "query": "API 返回 401 TOKEN_EXPIRED，前端该怎么处理",
     "source": "local", "category": "api-auth",
     "expected_doc": "authentication.md",
     "expected_keywords": ["TOKEN_EXPIRED", "refresh", "401"]},

    {"id": "local-004",
     "query": "redis-cli SENTINEL get-master-addr-by-name 命令返回什么",
     "source": "local", "category": "redis-failover",
     "expected_doc": "redis-failover.md",
     "expected_keywords": ["SENTINEL", "master", "addr"]},

    {"id": "local-005",
     "query": "JWT RS256 签名验证流程是什么",
     "source": "local", "category": "api-auth",
     "expected_doc": "authentication.md",
     "expected_keywords": ["JWT", "RS256", "签名"]},

    {"id": "local-006",
     "query": "线上 Redis 突然大量写入失败，错误日志一直刷屏，应用都快挂了",
     "source": "local", "category": "redis-failover",
     "expected_doc": "redis-failover.md",
     "expected_keywords": ["写入失败", "failover"]},

    {"id": "local-007",
     "query": "我的 pod 一直在 restart，已经重启了 50 多次了",
     "source": "local", "category": "k8s-crashloop",
     "expected_doc": "kubernetes-pod-crashloop.md",
     "expected_keywords": ["restart", "CrashLoopBackOff"]},

    {"id": "local-008",
     "query": "用户登录后 token 过一会就失效了，要重新登录很烦",
     "source": "local", "category": "api-auth",
     "expected_doc": "authentication.md",
     "expected_keywords": ["token", "过期", "refresh"]},

    {"id": "local-009",
     "query": "How to manually trigger Redis Sentinel failover?",
     "source": "local", "category": "redis-failover",
     "expected_doc": "redis-failover.md",
     "expected_keywords": ["SENTINEL", "failover", "manual"]},

    {"id": "local-010",
     "query": "Pod stuck in CrashLoopBackOff with exit code 137",
     "source": "local", "category": "k8s-crashloop",
     "expected_doc": "kubernetes-pod-crashloop.md",
     "expected_keywords": ["CrashLoopBackOff", "137", "OOM"]},

    {"id": "local-011",
     "query": "OAuth 2.0 authorization code flow 怎么实现",
     "source": "local", "category": "api-auth",
     "expected_doc": "authentication.md",
     "expected_keywords": ["OAuth", "authorization", "code"]},

    {"id": "local-012",
     "query": "Redis 主从切换后客户端怎么自动重连？",
     "source": "local", "category": "redis-failover",
     "expected_doc": "redis-failover.md",
     "expected_keywords": ["主从切换", "重连", "Sentinel"]},

    {"id": "local-013",
     "query": "Container keeps getting killed, how to check resource limits?",
     "source": "local", "category": "k8s-crashloop",
     "expected_doc": "kubernetes-pod-crashloop.md",
     "expected_keywords": ["resource", "limit", "killed"]},

    {"id": "local-014",
     "query": "access token 和 refresh token 的区别是什么？",
     "source": "local", "category": "api-auth",
     "expected_doc": "authentication.md",
     "expected_keywords": ["access token", "refresh token"]},

    {"id": "local-015",
     "query": "Redis failover 后数据会丢失吗？怎么保证数据一致性？",
     "source": "local", "category": "redis-failover",
     "expected_doc": "redis-failover.md",
     "expected_keywords": ["failover", "数据丢失", "一致性"]},

    # ══════════════════════════════════════════════════════════════
    # H. Notfound — 知识库中不存在的主题 (10)
    # ══════════════════════════════════════════════════════════════
    {"id": "notfound-001",
     "query": "How to configure MongoDB sharding with mongos router?",
     "source": "notfound", "category": "notfound",
     "expected_doc": None,
     "expected_keywords": []},

    {"id": "notfound-002",
     "query": "Kafka consumer group rebalancing 怎么优化？",
     "source": "notfound", "category": "notfound",
     "expected_doc": None,
     "expected_keywords": []},

    {"id": "notfound-003",
     "query": "How to set up Prometheus alerting rules for CPU usage?",
     "source": "notfound", "category": "notfound",
     "expected_doc": None,
     "expected_keywords": []},

    {"id": "notfound-004",
     "query": "Elasticsearch index mapping 怎么设计？",
     "source": "notfound", "category": "notfound",
     "expected_doc": None,
     "expected_keywords": []},

    {"id": "notfound-005",
     "query": "How to configure Nginx reverse proxy with load balancing?",
     "source": "notfound", "category": "notfound",
     "expected_doc": None,
     "expected_keywords": []},

    {"id": "notfound-006",
     "query": "PostgreSQL VACUUM 和 ANALYZE 什么时候需要手动执行？",
     "source": "notfound", "category": "notfound",
     "expected_doc": None,
     "expected_keywords": []},

    {"id": "notfound-007",
     "query": "How to deploy a Spring Boot application to AWS ECS?",
     "source": "notfound", "category": "notfound",
     "expected_doc": None,
     "expected_keywords": []},

    {"id": "notfound-008",
     "query": "RabbitMQ dead letter queue 怎么配置？",
     "source": "notfound", "category": "notfound",
     "expected_doc": None,
     "expected_keywords": []},

    {"id": "notfound-009",
     "query": "How to implement circuit breaker pattern with Hystrix?",
     "source": "notfound", "category": "notfound",
     "expected_doc": None,
     "expected_keywords": []},

    {"id": "notfound-010",
     "query": "Terraform state management best practices for team collaboration",
     "source": "notfound", "category": "notfound",
     "expected_doc": None,
     "expected_keywords": []},

    # ══════════════════════════════════════════════════════════════
    # I. Multi-hop — 需综合多个文档回答 (5)
    # ══════════════════════════════════════════════════════════════
    {"id": "multi-hop-001",
     "query": "Redis Sentinel 和 Cluster 能同时用吗？各自解决什么问题？",
     "source": "qdrant", "category": "multi-hop",
     "expected_doc": "sentinel.md,scaling.md,cluster",
     "expected_keywords": ["sentinel", "cluster", "failover", "hash slot"],
     "reference_answer": "Sentinel 提供高可用（自动故障转移），Cluster 提供数据分片（水平扩展）。Redis Cluster 内置了故障转移机制，不需要额外的 Sentinel。Sentinel 适用于单主多从架构，Cluster 适用于数据量超过单机内存的场景。两者不需要同时使用——Cluster 已包含 Sentinel 的故障转移功能。"},

    {"id": "multi-hop-002",
     "query": "If I use RDB persistence with Redis replication, what happens during a failover? Will I lose data?",
     "source": "qdrant", "category": "multi-hop",
     "expected_doc": "persistence.md,replication.md,sentinel.md",
     "expected_keywords": ["RDB", "replication", "failover", "data loss"],
     "reference_answer": "During failover, the replica promoted to master may not have the latest writes (asynchronous replication). With RDB only, data between the last snapshot and failover is lost. The new master starts from its own dataset. To minimize loss: use AOF with everysec fsync, configure min-replicas-to-write and min-replicas-max-lag to reject writes when replicas are too far behind."},

    {"id": "multi-hop-003",
     "query": "怎么用 Redis Streams 的消费者组配合 ACL 做多租户消息隔离？",
     "source": "qdrant", "category": "multi-hop",
     "expected_doc": "streams,acl.md",
     "expected_keywords": ["stream", "consumer group", "ACL", "tenant"],
     "reference_answer": "为每个租户创建独立的 Stream key（如 tenant:{id}:events）。用 ACL 限制每个用户只能访问自己的 key pattern（ACL SETUSER tenant1 ~tenant:1:* +xadd +xreadgroup +xack）。每个租户有独立的消费者组（XGROUP CREATE）。这样实现了 key 级别的隔离 + 命令级别的权限控制。"},

    {"id": "multi-hop-004",
     "query": "How to build a RAG system that uses Redis as both vector store and cache?",
     "source": "qdrant", "category": "multi-hop",
     "expected_doc": "vector-sets,client-side-caching.md,agentic_rag,rag_chain",
     "expected_keywords": ["RAG", "vector", "cache", "Redis"],
     "reference_answer": "Redis can serve dual roles in RAG: 1) Vector store: use Redis Vector Sets (VADD/VSIM) or RediSearch to store and search document embeddings. 2) Cache: use Redis Strings/Hashes to cache LLM responses for repeated queries, with TTL for freshness. Client-side caching can further reduce latency. Combine with Redis Streams for async document ingestion pipeline."},

    {"id": "multi-hop-005",
     "query": "Redis Lua scripting 和 pipelining 都能批量执行命令，什么时候该用哪个？",
     "source": "qdrant", "category": "multi-hop",
     "expected_doc": "eval-intro.md,pipelining.md",
     "expected_keywords": ["Lua", "pipeline", "atomic", "batch"],
     "reference_answer": "Pipelining 减少网络 RTT，命令独立执行，不保证原子性。Lua 脚本原子执行，适合需要读后写、条件逻辑的场景。选择：纯批量读写无依赖 → pipeline；需要原子性或命令间有依赖 → Lua。Pipeline 更简单、性能更好（无 Lua 解释开销）；Lua 更灵活但会阻塞其他命令。"},

    # ══════════════════════════════════════════════════════════════
    # J. Cross-source — 跨数据源 (5)
    # ══════════════════════════════════════════════════════════════
    {"id": "cross-src-001",
     "query": "RAG 应用中如何用 Redis 做语义缓存？有没有现成的实现？",
     "source": "qdrant", "category": "cross-source",
     "expected_doc": "client-side-caching.md,agentic_rag,rag_chain,memory-optimization.md",
     "expected_keywords": ["RAG", "cache", "Redis", "semantic"]},

    {"id": "cross-src-002",
     "query": "How to handle Redis failover in a Kubernetes environment? Pod restarts and Sentinel together?",
     "source": "qdrant", "category": "cross-source",
     "expected_doc": "sentinel.md,redis-failover.md,kubernetes-pod-crashloop.md",
     "expected_keywords": ["failover", "Kubernetes", "Sentinel", "pod"]},

    {"id": "cross-src-003",
     "query": "AI Agent 开发中，怎么用 Redis Streams 做 agent 间的消息传递？",
     "source": "qdrant", "category": "cross-source",
     "expected_doc": "streams,ai_finance_agent_team,ai_recruitment_agent_team",
     "expected_keywords": ["agent", "stream", "message", "Redis"]},

    {"id": "cross-src-004",
     "query": "OAuth token 存在 Redis 里，怎么配置 TTL 和安全访问控制？",
     "source": "qdrant", "category": "cross-source",
     "expected_doc": "authentication.md,acl.md,encryption.md",
     "expected_keywords": ["OAuth", "token", "TTL", "ACL", "Redis"]},

    {"id": "cross-src-005",
     "query": "How to add persistent memory to an LLM agent using Redis?",
     "source": "qdrant", "category": "cross-source",
     "expected_doc": "llm_app_personalized_memory,hashes.md,streams",
     "expected_keywords": ["memory", "LLM", "agent", "Redis", "persistent"]},

    # ══════════════════════════════════════════════════════════════
    # K. Ambiguous — 模糊查询，测模型自主判断能力 (5)
    # ══════════════════════════════════════════════════════════════
    {"id": "ambiguous-001",
     "query": "Redis 性能不好怎么办？",
     "source": "qdrant", "category": "ambiguous",
     "expected_doc": "latency.md,memory-optimization.md,benchmarks,pipelining.md,cpu-profiling",
     "expected_keywords": ["latency", "memory", "optimization", "benchmark"]},

    {"id": "ambiguous-002",
     "query": "How to make my RAG better?",
     "source": "qdrant", "category": "ambiguous",
     "expected_doc": "corrective_rag,agentic_rag,rag_chain,rag_tutorials,hybrid_search_rag,rag-as-a-service",
     "expected_keywords": ["RAG", "retrieval", "quality"]},

    {"id": "ambiguous-003",
     "query": "Redis 数据丢了怎么恢复？",
     "source": "qdrant", "category": "ambiguous",
     "expected_doc": "persistence.md,replication.md,redis-failover.md",
     "expected_keywords": ["persistence", "RDB", "AOF", "recovery"]},

    {"id": "ambiguous-004",
     "query": "What's the best way to use Redis?",
     "source": "qdrant", "category": "ambiguous",
     "expected_doc": "memory-optimization.md,pipelining.md,client-side-caching.md,admin.md,config.md,data-store.md,get-started",
     "expected_keywords": ["Redis", "best practice"]},

    {"id": "ambiguous-005",
     "query": "AI agent 老是出错怎么办？",
     "source": "qdrant", "category": "ambiguous",
     "expected_doc": "corrective_rag,agentic_rag,code-reviewer,guardrails,exception_handling,tracing,agent_framework",
     "expected_keywords": ["agent", "error", "debug"]},

    # ══════════════════════════════════════════════════════════════
    # L. Long-answer — 需要 Read 完整文档的深度问题 (5)
    # ══════════════════════════════════════════════════════════════
    {"id": "long-ans-001",
     "query": "请详细解释 Redis Cluster 的完整架构：数据分片、故障检测、故障转移、客户端路由的完整流程",
     "source": "qdrant", "category": "long-answer",
     "expected_doc": "scaling.md,cluster-spec.md,cluster",
     "expected_keywords": ["cluster", "hash slot", "gossip", "failover", "MOVED", "ASK"]},

    {"id": "long-ans-002",
     "query": "Give me a comprehensive guide to Redis persistence: RDB, AOF, and hybrid approach with all configuration options",
     "source": "qdrant", "category": "long-answer",
     "expected_doc": "persistence.md",
     "expected_keywords": ["RDB", "AOF", "save", "appendonly", "fsync", "rewrite"]},

    {"id": "long-ans-003",
     "query": "详细介绍 Redis Sentinel 的完整工作机制：监控、通知、自动故障转移、配置传播",
     "source": "qdrant", "category": "long-answer",
     "expected_doc": "sentinel.md",
     "expected_keywords": ["sentinel", "SDOWN", "ODOWN", "quorum", "failover", "epoch"]},

    {"id": "long-ans-004",
     "query": "Explain the complete Redis replication mechanism: full sync, partial sync, PSYNC, replication backlog, and diskless replication",
     "source": "qdrant", "category": "long-answer",
     "expected_doc": "replication.md",
     "expected_keywords": ["replication", "PSYNC", "backlog", "RDB", "diskless", "offset"]},

    {"id": "long-ans-005",
     "query": "How to build a complete Agentic RAG system from scratch? Cover architecture, retrieval strategies, agent reasoning, and evaluation",
     "source": "qdrant", "category": "long-answer",
     "expected_doc": "agentic_rag,corrective_rag,rag_chain",
     "expected_keywords": ["agentic", "RAG", "retrieval", "agent", "reasoning"]},
]

# ══════════════════════════════════════════════════════════════
# Golden DataSet — 20 个代表性 case，覆盖所有 category + 已知问题
# EVAL_DATASET=golden 快速回归（~30min vs full eval ~3h）
# ══════════════════════════════════════════════════════════════
GOLDEN_IDS = [
    "redis-dt-001", "redis-ops-009", "redis-so-010", "redis-dt-002",  # Redis
    "llm-agent-001", "llm-fw-004", "llm-rag-002",                     # LLM
    "local-003", "local-002", "local-015",                             # 本地
    "notfound-003", "notfound-002",                                    # Notfound
    "multi-hop-002", "multi-hop-003", "cross-src-002", "ambiguous-001",# 新维度
    "long-ans-003", "ambiguous-004",                                   # 边界
    "redis-ops-002",   # 概念+操作混合 — 测早停是否误伤操作类问题
    "redis-so-003",    # 中文排障 — 测跨语言改写是否命中英文文档
]

GOLDEN_CASES = [tc for tc in TEST_CASES_V5 if tc["id"] in GOLDEN_IDS]
