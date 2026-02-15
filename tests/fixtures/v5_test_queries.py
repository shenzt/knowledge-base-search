"""v5 评测用例 — 100 个真实问题
数据源:
  - redis-docs (234 docs): develop/ + operate/oss_and_stack/
  - awesome-llm-apps (207 docs): RAG, agents, multi-agent teams
  - local docs/ (3 docs): redis-failover, k8s-crashloop, api-auth
  - notfound: 知识库中不存在的主题

用例分布: 40 redis + 35 llm-apps + 15 local + 10 notfound = 100
"""

TEST_CASES_V5 = [
    # ══════════════════════════════════════════════════════════════
    # A. Redis Docs — 数据类型 (10)
    # ══════════════════════════════════════════════════════════════
    {"id": "redis-dt-001",
     "query": "What is the difference between Redis Sorted Sets and regular Sets?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "sorted-sets.md",
     "expected_keywords": ["sorted set", "score", "ranking"]},

    {"id": "redis-dt-002",
     "query": "How do I use Redis Streams for message queuing?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "streams",
     "expected_keywords": ["stream", "XADD", "consumer"]},

    {"id": "redis-dt-003",
     "query": "Redis Bloom Filter 的误判率怎么配置？",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "bloom-filter.md",
     "expected_keywords": ["bloom", "error rate", "filter"]},

    {"id": "redis-dt-004",
     "query": "When should I use Redis Hashes vs JSON?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "hashes.md,compare-data-types.md,json",
     "expected_keywords": ["hash", "field", "HSET"]},

    {"id": "redis-dt-005",
     "query": "How does HyperLogLog count unique elements in Redis?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "hyperloglogs.md",
     "expected_keywords": ["hyperloglog", "cardinality", "PFADD"]},

    {"id": "redis-dt-006",
     "query": "Redis Lists 作为消息队列和 Streams 有什么区别？",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "lists.md",
     "expected_keywords": ["list", "LPUSH", "RPOP"]},

    {"id": "redis-dt-007",
     "query": "What are Redis Bitfields and when would I use them?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "bitfields.md",
     "expected_keywords": ["bitfield", "counter", "integer"]},

    {"id": "redis-dt-008",
     "query": "How to store and query geospatial data in Redis?",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "geospatial.md",
     "expected_keywords": ["geo", "GEOADD", "radius"]},

    {"id": "redis-dt-009",
     "query": "Redis TimeSeries 适合什么场景？怎么配置 retention？",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "timeseries",
     "expected_keywords": ["time series", "retention", "TS."]},

    {"id": "redis-dt-010",
     "query": "Compare Count-Min Sketch and Top-K in Redis probabilistic data structures",
     "source": "qdrant", "category": "redis-data-types",
     "expected_doc": "count-min-sketch.md",
     "expected_keywords": ["count-min", "frequency", "probabilistic"]},

    # ══════════════════════════════════════════════════════════════
    # B. Redis Docs — 运维管理 (15)
    # ══════════════════════════════════════════════════════════════
    {"id": "redis-ops-001",
     "query": "How does Redis Sentinel handle automatic failover?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "sentinel.md",
     "expected_keywords": ["sentinel", "failover", "master"]},

    {"id": "redis-ops-002",
     "query": "Redis cluster 是怎么做数据分片的？hash slot 机制是什么？",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "scaling.md",
     "expected_keywords": ["cluster", "hash slot", "16384"]},

    {"id": "redis-ops-003",
     "query": "What is the difference between RDB and AOF persistence in Redis?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "persistence.md",
     "expected_keywords": ["RDB", "AOF", "snapshot"]},

    {"id": "redis-ops-004",
     "query": "How to configure Redis ACL for fine-grained access control?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "acl.md",
     "expected_keywords": ["ACL", "user", "permission"]},

    {"id": "redis-ops-005",
     "query": "Redis 主从复制的原理是什么？PSYNC 怎么工作？",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "replication.md",
     "expected_keywords": ["replication", "replica", "PSYNC"]},

    {"id": "redis-ops-006",
     "query": "How to diagnose and fix Redis latency spikes?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "latency.md",
     "expected_keywords": ["latency", "slow", "monitor"]},

    {"id": "redis-ops-007",
     "query": "Redis memory optimization best practices",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "memory-optimization.md",
     "expected_keywords": ["memory", "optimization", "encoding"]},

    {"id": "redis-ops-008",
     "query": "How to enable TLS encryption for Redis connections?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "encryption.md",
     "expected_keywords": ["TLS", "SSL", "encrypt"]},

    {"id": "redis-ops-009",
     "query": "Redis debugging 有哪些常用工具和命令？",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "debugging.md",
     "expected_keywords": ["debug", "OBJECT", "MEMORY"]},

    {"id": "redis-ops-010",
     "query": "How to upgrade a Redis cluster without downtime?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "cluster.md",
     "expected_keywords": ["upgrade", "cluster", "rolling"]},

    {"id": "redis-ops-011",
     "query": "What signals does Redis handle and how to gracefully shutdown?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "signals.md",
     "expected_keywords": ["signal", "SIGTERM", "shutdown"]},

    {"id": "redis-ops-012",
     "query": "Redis pipelining 能提升多少性能？怎么用？",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "pipelining.md",
     "expected_keywords": ["pipeline", "RTT", "batch"]},

    {"id": "redis-ops-013",
     "query": "How do Redis transactions work? What is MULTI/EXEC?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "transactions.md",
     "expected_keywords": ["MULTI", "EXEC", "transaction"]},

    {"id": "redis-ops-014",
     "query": "Redis client-side caching mechanism and invalidation",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "client-side-caching.md",
     "expected_keywords": ["client-side", "caching", "invalidat"]},

    {"id": "redis-ops-015",
     "query": "How to use Redis Lua scripting with EVAL command?",
     "source": "qdrant", "category": "redis-ops",
     "expected_doc": "eval-intro.md",
     "expected_keywords": ["EVAL", "Lua", "script"]},

    # ══════════════════════════════════════════════════════════════
    # C. Redis Docs — SO 风格真实问题 (15)
    # ══════════════════════════════════════════════════════════════
    {"id": "redis-so-001",
     "query": "My Redis is using too much memory, maxmemory is set but keys keep growing. How does eviction work?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "eviction",
     "expected_keywords": ["eviction", "maxmemory", "policy"]},

    {"id": "redis-so-002",
     "query": "Redis Sentinel 一直报 failover-abort-no-good-slave，怎么排查？",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "sentinel.md",
     "expected_keywords": ["sentinel", "failover", "replica"]},

    {"id": "redis-so-003",
     "query": "I need to run SORT and SUNION across different Redis cluster nodes, but getting CROSSSLOT error",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "scaling.md,multi-key-operations.md,cluster",
     "expected_keywords": ["cluster", "hash slot", "CROSSSLOT"]},

    {"id": "redis-so-004",
     "query": "Redis AOF rewrite keeps failing with 'Can't open the append-only file', disk is not full",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "persistence.md",
     "expected_keywords": ["AOF", "rewrite", "append"]},

    {"id": "redis-so-005",
     "query": "线上 Redis 延迟突然飙到 200ms，SLOWLOG 里全是 KEYS 命令，怎么办？",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "latency.md",
     "expected_keywords": ["latency", "SLOWLOG", "KEYS"]},

    {"id": "redis-so-006",
     "query": "How to implement a rate limiter using Redis sorted sets?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "sorted-sets.md",
     "expected_keywords": ["sorted set", "score", "ZADD"]},

    {"id": "redis-so-007",
     "query": "Redis keyspace notifications 怎么配置？我想监听 key 过期事件",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "keyspace-notifications.md",
     "expected_keywords": ["keyspace", "notification", "expired"]},

    {"id": "redis-so-008",
     "query": "What is the Redis RESP protocol? How does client-server communication work?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "protocol-spec.md",
     "expected_keywords": ["RESP", "protocol", "bulk string"]},

    {"id": "redis-so-009",
     "query": "Redis cluster spec says 16384 hash slots, why this number? How are keys mapped?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "cluster-spec.md",
     "expected_keywords": ["16384", "CRC16", "hash slot"]},

    {"id": "redis-so-010",
     "query": "我的 Redis 用了 10GB 内存但只存了 2GB 数据，内存碎片怎么处理？",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "memory-optimization.md",
     "expected_keywords": ["memory", "fragmentation", "jemalloc"]},

    {"id": "redis-so-011",
     "query": "How to set up Redis Sentinel with 3 nodes for high availability?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "sentinel.md",
     "expected_keywords": ["sentinel", "quorum", "monitor"]},

    {"id": "redis-so-012",
     "query": "Redis Functions vs Lua scripts — what's the difference and when to use which?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "functions-intro.md",
     "expected_keywords": ["function", "FCALL", "library"]},

    {"id": "redis-so-013",
     "query": "How to benchmark Redis performance? What tool should I use?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "benchmarks",
     "expected_keywords": ["benchmark", "redis-benchmark", "throughput"]},

    {"id": "redis-so-014",
     "query": "Redis vector sets 怎么做 filtered search？能结合标签过滤吗？",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "filtered-search.md",
     "expected_keywords": ["vector", "filter", "search"]},

    {"id": "redis-so-015",
     "query": "How to install Redis Stack on Ubuntu with apt?",
     "source": "qdrant", "category": "redis-so",
     "expected_doc": "apt.md,install-redis-on-linux.md,ubuntu,linux.md",
     "expected_keywords": ["install", "apt", "ubuntu"]},

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
     "expected_doc": "code-reviewer",
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
]
