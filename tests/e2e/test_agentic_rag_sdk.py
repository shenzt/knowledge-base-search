#!/usr/bin/env python3
"""Agentic RAG 自动化测试 - 使用 Claude Agent SDK + Session 复用

关键优化：使用 session resume 保持 MCP server 活跃，避免每次重新加载模型。
完整记录中间过程到日志文件，方便排查和调优。
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from claude_agent_sdk import query, ClaudeAgentOptions

PROJECT_ROOT = Path(__file__).parent.parent.parent

# 导入评测模块
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from eval_module import extract_contexts, gate_check, get_tools_used, get_retrieved_doc_paths, get_kb_commit

TEST_CASES = [
    # ══════════════════════════════════════════════════════════════════
    # v3: 基于全量 K8s + Redis 官方文档的测试用例
    #
    # 数据源 1 — 本地 docs/（Grep/Glob/Read 可达）:
    #   - runbook/redis-failover.md (中文, Redis Sentinel 主从切换)
    #   - runbook/kubernetes-pod-crashloop.md (English, CrashLoopBackOff)
    #   - api/authentication.md (中文, OAuth 2.0 + JWT)
    #
    # 数据源 2 — Qdrant 索引（MCP hybrid_search 可达）:
    #   K8s: 144 docs from kubernetes/website (concepts section)
    #     Pod, Service, Ingress, Deployment, ConfigMap, Secret, Probes,
    #     Volumes, Namespaces, Labels, Nodes, GC, ResourceQuota, etc.
    #   Redis: ~62 docs from redis/docs (official English)
    #     Sentinel, Replication, Persistence, Scaling, Data Types,
    #     Pipelining, Transactions, ACL, Latency, Memory, Debugging, etc.
    # ══════════════════════════════════════════════════════════════════

    # ── A. 本地文档：精确关键词（Grep 直接命中）──
    {"id": "local-exact-001",
     "query": "READONLY You can't write against a read only replica 这个报错怎么解决",
     "category": "redis-failover", "type": "exact", "source": "local",
     "expected_doc": "redis-failover.md",
     "note": "SO风格：贴错误信息求解"},
    {"id": "local-exact-002",
     "query": "kubectl describe pod 显示 OOMKilled 怎么办",
     "category": "k8s-crashloop", "type": "exact", "source": "local",
     "expected_doc": "kubernetes-pod-crashloop.md",
     "note": "SO风格：贴命令输出求解"},
    {"id": "local-exact-003",
     "query": "API 返回 401 TOKEN_EXPIRED，前端该怎么处理",
     "category": "api-auth", "type": "exact", "source": "local",
     "expected_doc": "authentication.md",
     "note": "SO风格：具体错误码"},
    {"id": "local-exact-004",
     "query": "redis-cli SENTINEL get-master-addr-by-name 命令返回什么",
     "category": "redis-failover", "type": "exact", "source": "local",
     "expected_doc": "redis-failover.md"},
    {"id": "local-exact-005",
     "query": "JWT RS256 签名验证流程是什么",
     "category": "api-auth", "type": "exact", "source": "local",
     "expected_doc": "authentication.md"},

    # ── B. 本地文档：StackOverflow 真实场景（症状描述）──
    {"id": "local-so-001",
     "query": "线上 Redis 突然大量写入失败，错误日志一直刷屏，应用都快挂了，急！",
     "category": "redis-failover", "type": "scenario", "source": "local",
     "expected_doc": "redis-failover.md",
     "note": "SO紧急求助，不含 READONLY/Sentinel/failover"},
    {"id": "local-so-002",
     "query": "我的 pod 一直在 restart，已经重启了 50 多次了，describe 看了也没啥有用信息",
     "category": "k8s-crashloop", "type": "scenario", "source": "local",
     "expected_doc": "kubernetes-pod-crashloop.md",
     "note": "SO口语化，不含 CrashLoopBackOff"},
    {"id": "local-so-003",
     "query": "用户反馈说登录之后过一会儿就被踢出来了，要重新登录，是 token 的问题吗",
     "category": "api-auth", "type": "scenario", "source": "local",
     "expected_doc": "authentication.md",
     "note": "SO用户反馈，不含 JWT/refresh_token"},
    {"id": "local-so-004",
     "query": "容器跑着跑着就被 kill 了，感觉是内存的问题但不确定怎么查",
     "category": "k8s-crashloop", "type": "scenario", "source": "local",
     "expected_doc": "kubernetes-pod-crashloop.md",
     "note": "模糊描述→OOMKilled"},
    {"id": "local-so-005",
     "query": "Redis 主库挂了之后从库顶上去了，但是应用还是连的旧地址，怎么让应用自动切换",
     "category": "redis-failover", "type": "scenario", "source": "local",
     "expected_doc": "redis-failover.md",
     "note": "口语化描述 failover + Sentinel 客户端"},
    {"id": "local-so-006",
     "query": "我们有个多租户系统，不同租户的用户不能互相访问数据，这个权限怎么设计的",
     "category": "api-auth", "type": "scenario", "source": "local",
     "expected_doc": "authentication.md",
     "note": "指向 tenant_id + RBAC"},

    # ── C. 本地文档：跨语言 ──
    {"id": "local-cross-001",
     "query": "How to recover when Redis sentinel triggers a failover?",
     "category": "redis-failover", "type": "cross-lang", "source": "local",
     "expected_doc": "redis-failover.md",
     "note": "英文问→中文文档"},
    {"id": "local-cross-002",
     "query": "K8s 容器因为 liveness probe 失败一直重启怎么排查",
     "category": "k8s-crashloop", "type": "cross-lang", "source": "local",
     "expected_doc": "kubernetes-pod-crashloop.md",
     "note": "中文问→英文文档"},

    # ── D. 本地文档：How-to 实操 ──
    {"id": "local-howto-001",
     "query": "怎么确认 Redis Sentinel 当前的 master 是哪个节点",
     "category": "redis-failover", "type": "howto", "source": "local",
     "expected_doc": "redis-failover.md"},
    {"id": "local-howto-002",
     "query": "怎么看上一次容器崩溃的日志",
     "category": "k8s-crashloop", "type": "howto", "source": "local",
     "expected_doc": "kubernetes-pod-crashloop.md",
     "note": "文档中有 kubectl logs --previous"},
    {"id": "local-howto-003",
     "query": "access_token 过期了怎么续期，调哪个接口",
     "category": "api-auth", "type": "howto", "source": "local",
     "expected_doc": "authentication.md",
     "note": "文档中有 /api/v1/auth/refresh"},

    # ── E. 本地文档：多文档综合 ──
    {"id": "local-multi-001",
     "query": "Pod 重启后 Redis 连接断了，从排查 Pod 到恢复 Redis 连接的完整流程是什么",
     "category": "multi-doc", "type": "multi-doc", "source": "local",
     "expected_doc": "kubernetes-pod-crashloop.md,redis-failover.md",
     "note": "需要综合两个 runbook"},

    # ── F. Qdrant: Redis 官方文档 ──
    {"id": "qdrant-redis-sentinel-001",
     "query": "How does Redis Sentinel automatic failover work?",
     "category": "redis-sentinel", "type": "concept", "source": "qdrant",
     "expected_doc": "sentinel.md",
     "note": "Official Sentinel doc has full failover explanation"},
    {"id": "qdrant-redis-sentinel-002",
     "query": "Redis Sentinel 的 quorum 是什么意思？怎么配置？",
     "category": "redis-sentinel", "type": "howto", "source": "qdrant",
     "expected_doc": "sentinel.md",
     "note": "Cross-lang: Chinese question → English doc"},
    {"id": "qdrant-redis-repl-001",
     "query": "Redis master-replica replication 是异步的还是同步的？",
     "category": "redis-replication", "type": "concept", "source": "qdrant",
     "expected_doc": "replication.md"},
    {"id": "qdrant-redis-repl-002",
     "query": "Redis replica 断开连接后重连，是全量同步还是部分同步？",
     "category": "redis-replication", "type": "scenario", "source": "qdrant",
     "expected_doc": "replication.md"},
    {"id": "qdrant-redis-persist-001",
     "query": "RDB 和 AOF 有什么区别？该用哪个？",
     "category": "redis-persistence", "type": "concept", "source": "qdrant",
     "expected_doc": "persistence.md"},
    {"id": "qdrant-redis-persist-002",
     "query": "Redis AOF rewrite 是怎么工作的？会阻塞主线程吗？",
     "category": "redis-persistence", "type": "scenario", "source": "qdrant",
     "expected_doc": "persistence.md"},
    {"id": "qdrant-redis-cluster-001",
     "query": "Redis Cluster 的 hash slot 是怎么分配的？",
     "category": "redis-scaling", "type": "concept", "source": "qdrant",
     "expected_doc": "scaling.md"},
    {"id": "qdrant-redis-strings-001",
     "query": "Redis Strings 除了缓存还能做什么？支持哪些操作？",
     "category": "redis-strings", "type": "concept", "source": "qdrant",
     "expected_doc": "strings.md"},
    {"id": "qdrant-redis-sorted-set-001",
     "query": "How to implement a leaderboard with Redis Sorted Sets?",
     "category": "redis-sorted-sets", "type": "howto", "source": "qdrant",
     "expected_doc": "sorted-sets.md"},
    {"id": "qdrant-redis-streams-001",
     "query": "Redis Streams 和 Pub/Sub 有什么区别？什么时候用 Streams？",
     "category": "redis-streams", "type": "concept", "source": "qdrant",
     "expected_doc": "streams/_index.md",
     "note": "Streams vs Pub/Sub comparison"},
    {"id": "qdrant-redis-bloom-001",
     "query": "What is a Bloom filter in Redis and when should I use it?",
     "category": "redis-bloom", "type": "concept", "source": "qdrant",
     "expected_doc": "bloom-filter.md"},
    {"id": "qdrant-redis-latency-001",
     "query": "Redis 延迟突然变高怎么排查？有哪些常见原因？",
     "category": "redis-latency", "type": "scenario", "source": "qdrant",
     "expected_doc": "latency.md"},
    {"id": "qdrant-redis-memory-001",
     "query": "Redis 内存占用太高怎么优化？",
     "category": "redis-memory", "type": "scenario", "source": "qdrant",
     "expected_doc": "memory-optimization.md"},
    {"id": "qdrant-redis-acl-001",
     "query": "How to set up Redis ACL to restrict user permissions?",
     "category": "redis-acl", "type": "howto", "source": "qdrant",
     "expected_doc": "acl.md"},
    {"id": "qdrant-redis-pipelining-001",
     "query": "Redis pipelining 的原理是什么？和普通请求有什么区别？",
     "category": "redis-pipelining", "type": "concept", "source": "qdrant",
     "expected_doc": "pipelining.md"},
    {"id": "qdrant-redis-transactions-001",
     "query": "Redis MULTI/EXEC 事务和 Lua 脚本哪个更好？",
     "category": "redis-transactions", "type": "concept", "source": "qdrant",
     "expected_doc": "transactions.md"},
    {"id": "qdrant-redis-debug-001",
     "query": "线上 Redis 出问题了怎么 debug？有哪些诊断命令？",
     "category": "redis-debugging", "type": "scenario", "source": "qdrant",
     "expected_doc": "debugging.md"},
    {"id": "qdrant-redis-benchmark-001",
     "query": "How to benchmark Redis performance? What tool should I use?",
     "category": "redis-benchmark", "type": "howto", "source": "qdrant",
     "expected_doc": "benchmarks/index.md"},
    {"id": "qdrant-redis-so-001",
     "query": "我的 Redis 主从同步一直断，日志里刷 LOADING Redis is loading the dataset in memory",
     "category": "redis-replication", "type": "scenario", "source": "qdrant",
     "expected_doc": "replication.md",
     "note": "SO-style: full resync loop problem"},
    {"id": "qdrant-redis-so-002",
     "query": "Redis used_memory 比 maxmemory 大很多，但 keys 不多，内存去哪了？",
     "category": "redis-memory", "type": "scenario", "source": "qdrant",
     "expected_doc": "memory-optimization.md",
     "note": "SO-style: memory fragmentation"},

    # ── G. Qdrant: K8s 官方文档 ──
    {"id": "qdrant-k8s-pod-001",
     "query": "What is a Pod in Kubernetes?",
     "category": "k8s-pod", "type": "concept", "source": "qdrant",
     "expected_doc": "pods/_index.md"},
    {"id": "qdrant-k8s-service-001",
     "query": "Kubernetes Service 有哪些类型？ClusterIP 和 NodePort 的区别？",
     "category": "k8s-service", "type": "concept", "source": "qdrant",
     "expected_doc": "service.md"},
    {"id": "qdrant-k8s-deploy-001",
     "query": "Deployment 滚动更新卡住了，新旧 Pod 并存，怎么回滚？",
     "category": "k8s-deployment", "type": "scenario", "source": "qdrant",
     "expected_doc": "deployment.md"},
    {"id": "qdrant-k8s-configmap-001",
     "query": "How to use ConfigMap to inject configuration into a Pod?",
     "category": "k8s-configmap", "type": "howto", "source": "qdrant",
     "expected_doc": "configmap.md"},
    {"id": "qdrant-k8s-secret-001",
     "query": "Kubernetes Secret 和 ConfigMap 有什么区别？Secret 安全吗？",
     "category": "k8s-secret", "type": "concept", "source": "qdrant",
     "expected_doc": "secret.md"},
    {"id": "qdrant-k8s-probe-001",
     "query": "liveness probe 和 readiness probe 有什么区别？什么时候用哪个？",
     "category": "k8s-probes", "type": "concept", "source": "qdrant",
     "expected_doc": "liveness-readiness-startup-probes.md"},
    {"id": "qdrant-k8s-ingress-001",
     "query": "How does Kubernetes Ingress route traffic to different services?",
     "category": "k8s-ingress", "type": "concept", "source": "qdrant",
     "expected_doc": "ingress.md"},
    {"id": "qdrant-k8s-volume-001",
     "query": "Kubernetes 里怎么给 Pod 挂载持久化存储？PV 和 PVC 的关系？",
     "category": "k8s-volumes", "type": "concept", "source": "qdrant",
     "expected_doc": "volumes.md"},
    {"id": "qdrant-k8s-init-001",
     "query": "What are Init Containers and when should I use them?",
     "category": "k8s-init", "type": "concept", "source": "qdrant",
     "expected_doc": "init-containers.md"},
    {"id": "qdrant-k8s-lifecycle-001",
     "query": "Pod 的生命周期有哪些阶段？Pending 和 Running 的区别？",
     "category": "k8s-lifecycle", "type": "concept", "source": "qdrant",
     "expected_doc": "pod-lifecycle.md"},
    {"id": "qdrant-k8s-namespace-001",
     "query": "Kubernetes Namespace 是什么？什么时候需要用多个 Namespace？",
     "category": "k8s-namespace", "type": "concept", "source": "qdrant",
     "expected_doc": "namespaces.md"},
    {"id": "qdrant-k8s-label-001",
     "query": "How do Labels and Selectors work in Kubernetes?",
     "category": "k8s-labels", "type": "concept", "source": "qdrant",
     "expected_doc": "labels.md"},
    {"id": "qdrant-k8s-resource-001",
     "query": "怎么给 Pod 设置 CPU 和内存的 requests 和 limits？",
     "category": "k8s-resources", "type": "howto", "source": "qdrant",
     "expected_doc": "manage-resources-containers.md"},
    {"id": "qdrant-k8s-node-001",
     "query": "Kubernetes Node 的状态有哪些？NotReady 是什么意思？",
     "category": "k8s-nodes", "type": "concept", "source": "qdrant",
     "expected_doc": "nodes.md"},
    {"id": "qdrant-k8s-gc-001",
     "query": "Kubernetes garbage collection 是怎么清理资源的？",
     "category": "k8s-gc", "type": "concept", "source": "qdrant",
     "expected_doc": "garbage-collection.md"},
    {"id": "qdrant-k8s-so-001",
     "query": "Pod 一直 Pending 不调度，describe 显示 Insufficient cpu，怎么办？",
     "category": "k8s-resources", "type": "scenario", "source": "qdrant",
     "expected_doc": "manage-resources-containers.md",
     "note": "SO-style: resource quota issue"},
    {"id": "qdrant-k8s-so-002",
     "query": "Deployment rollout 卡在 Progressing，maxUnavailable 和 maxSurge 怎么调？",
     "category": "k8s-deployment", "type": "scenario", "source": "qdrant",
     "expected_doc": "deployment.md"},
    {"id": "qdrant-k8s-so-003",
     "query": "What's the difference between a Deployment and a ReplicationController?",
     "category": "k8s-deploy-vs-rc", "type": "concept", "source": "qdrant",
     "expected_doc": "deployment.md,replicationcontroller.md"},
    {"id": "qdrant-k8s-so-004",
     "query": "Container 的 preStop hook 没执行就被 kill 了，怎么保证优雅退出？",
     "category": "k8s-lifecycle-hooks", "type": "scenario", "source": "qdrant",
     "expected_doc": "container-lifecycle-hooks.md"},
    {"id": "qdrant-k8s-so-005",
     "query": "LimitRange 和 ResourceQuota 有什么区别？怎么限制单个 Pod 的资源？",
     "category": "k8s-policy", "type": "concept", "source": "qdrant",
     "expected_doc": "limit-range.md,resource-quotas.md"},

    # ── H. 未收录内容（应明确说"未找到"）──
    {"id": "notfound-001",
     "query": "Kubernetes HPA 自动扩缩容怎么配置",
     "category": "not-in-kb", "type": "notfound", "source": "none",
     "expect_no_results": True,
     "note": "KB 没有 HPA 内容"},
    {"id": "notfound-002",
     "query": "MongoDB 分片集群如何配置",
     "category": "not-in-kb", "type": "notfound", "source": "none",
     "expect_no_results": True,
     "note": "KB 完全没有 MongoDB"},
    {"id": "notfound-003",
     "query": "Kafka consumer group rebalance 怎么优化？",
     "category": "not-in-kb", "type": "notfound", "source": "none",
     "expect_no_results": True,
     "note": "KB 没有 Kafka 内容"},
    {"id": "notfound-004",
     "query": "How to set up Prometheus alerting rules?",
     "category": "not-in-kb", "type": "notfound", "source": "none",
     "expect_no_results": True,
     "note": "KB 没有 Prometheus 内容"},
    {"id": "notfound-005",
     "query": "Nginx 反向代理配置 upstream 负载均衡",
     "category": "not-in-kb", "type": "notfound", "source": "none",
     "expect_no_results": True,
     "note": "KB 没有 Nginx 内容"},
    {"id": "notfound-006",
     "query": "MySQL InnoDB 死锁怎么排查和解决？",
     "category": "not-in-kb", "type": "notfound", "source": "none",
     "expect_no_results": True,
     "note": "KB 没有 MySQL 内容"},
    {"id": "notfound-007",
     "query": "Docker Compose 多容器编排怎么配置网络？",
     "category": "not-in-kb", "type": "notfound", "source": "none",
     "expect_no_results": True,
     "note": "KB 没有 Docker Compose 内容"},
]

KEYWORD_CHECKS = {
    # 本地文档
    "redis-failover": ["redis", "sentinel", "failover", "主从", "切换", "master",
                        "readonly", "read only", "连接", "恢复"],
    "k8s-crashloop": ["pod", "crash", "restart", "重启", "oom", "log", "kubectl",
                       "liveness", "memory", "container"],
    "api-auth": ["token", "jwt", "oauth", "认证", "refresh", "rbac", "role",
                  "权限", "401", "login", "登录"],
    "multi-doc": ["redis", "pod", "token", "认证", "安全", "连接", "重启",
                   "sentinel", "crash", "权限"],
    # Qdrant: Redis 官方文档
    "redis-sentinel": ["sentinel", "failover", "master", "replica", "quorum",
                        "monitor", "high availability"],
    "redis-replication": ["replication", "replica", "master", "sync", "resync",
                           "partial", "full", "async", "leader", "follower"],
    "redis-persistence": ["rdb", "aof", "persistence", "snapshot", "append",
                           "rewrite", "fsync", "backup"],
    "redis-scaling": ["cluster", "hash slot", "node", "shard", "scaling"],
    "redis-strings": ["string", "SET", "GET", "counter", "INCR", "cache"],
    "redis-sorted-sets": ["sorted set", "ZADD", "ZRANGE", "score", "rank", "leaderboard"],
    "redis-streams": ["stream", "XADD", "XREAD", "consumer", "group", "message"],
    "redis-bloom": ["bloom", "filter", "probabilistic", "false positive"],
    "redis-latency": ["latency", "slow", "delay", "slowlog", "monitor"],
    "redis-memory": ["memory", "maxmemory", "eviction", "fragmentation", "optimization"],
    "redis-acl": ["acl", "user", "permission", "auth", "password"],
    "redis-pipelining": ["pipeline", "pipelining", "RTT", "batch", "round trip"],
    "redis-transactions": ["MULTI", "EXEC", "transaction", "WATCH", "atomic", "lua"],
    "redis-debugging": ["debug", "crash", "log", "INFO", "MONITOR", "SLOWLOG"],
    "redis-benchmark": ["benchmark", "redis-benchmark", "QPS", "throughput",
                         "performance", "ops"],
    # Qdrant: K8s 官方文档
    "k8s-pod": ["pod", "container", "kubernetes", "workload"],
    "k8s-service": ["service", "clusterip", "nodeport", "loadbalancer", "endpoint"],
    "k8s-deployment": ["deployment", "rollout", "rollback", "replica", "update"],
    "k8s-configmap": ["configmap", "configuration", "env", "volume", "mount"],
    "k8s-secret": ["secret", "base64", "opaque", "tls", "password", "sensitive"],
    "k8s-probes": ["liveness", "readiness", "startup", "probe", "health"],
    "k8s-ingress": ["ingress", "service", "host", "path", "rule", "tls"],
    "k8s-volumes": ["volume", "pv", "pvc", "storage", "mount", "persistent"],
    "k8s-init": ["init", "container", "before", "app"],
    "k8s-lifecycle": ["lifecycle", "phase", "pending", "running", "succeeded", "failed"],
    "k8s-namespace": ["namespace", "isolation", "default", "kube-system"],
    "k8s-labels": ["label", "selector", "matchLabels", "annotation", "metadata"],
    "k8s-resources": ["requests", "limits", "cpu", "memory", "resource", "quota"],
    "k8s-nodes": ["node", "NotReady", "condition", "kubelet", "status"],
    "k8s-gc": ["garbage", "collection", "owner", "dependent", "cascading", "finalizer"],
    "k8s-deploy-vs-rc": ["deployment", "replicationcontroller", "replicaset", "replica"],
    "k8s-lifecycle-hooks": ["preStop", "postStart", "hook", "lifecycle", "graceful"],
    "k8s-policy": ["limitrange", "resourcequota", "limit", "quota", "constraint"],
}

# 是否启用 MCP（模型加载需要 15-20 分钟，可选关闭）
USE_MCP = os.environ.get("USE_MCP", "0") == "1"

if USE_MCP:
    BASE_OPTIONS = dict(
        allowed_tools=[
            "Read", "Grep", "Glob", "Bash",
            "mcp__knowledge-base__hybrid_search",
            "mcp__knowledge-base__keyword_search",
            "mcp__knowledge-base__index_status",
        ],
        mcp_servers={
            "knowledge-base": {
                "command": str(PROJECT_ROOT / ".venv" / "bin" / "python"),
                "args": [str(PROJECT_ROOT / "scripts" / "mcp_server.py")],
                "env": {
                    "QDRANT_URL": os.environ.get("QDRANT_URL", "http://localhost:6333"),
                    "COLLECTION_NAME": os.environ.get("COLLECTION_NAME", "knowledge-base"),
                },
            }
        },
        setting_sources=["project"],
        permission_mode="bypassPermissions",
        cwd=str(PROJECT_ROOT),
        max_turns=15,
    )
else:
    # 无 MCP 模式：仅使用 Grep/Glob/Read（Agentic Layer 1）
    # 注意：不能用 setting_sources=["project"]，否则会加载 .mcp.json 启动 MCP server
    # 改用 system_prompt 注入 CLAUDE.md 和 search skill 的关键指令
    BASE_OPTIONS = dict(
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        permission_mode="bypassPermissions",
        cwd=str(PROJECT_ROOT),
        max_turns=15,
        system_prompt="""你是一个知识库检索助手。用户会用 /search 命令查询知识库。

知识库文档在 docs/ 目录下，格式为 Markdown，包含 Kubernetes 和 Redis 相关技术文档。

检索策略：
1. 使用 Grep 搜索关键词
2. 使用 Glob 查找相关文件（如 docs/**/*.md）
3. 使用 Read 读取命中文件的相关段落
4. 综合分析并回答，必须带引用 [来源: docs/xxx.md]

回答要求：
- 基于检索到的文档内容回答
- 如果文档中没有相关信息，明确说明"未找到相关文档"
- 回答语言跟随查询语言（中文问中文答，英文问英文答）
- 引用具体文档路径
""",
    )


def log(msg: str, log_file=None):
    """同时输出到 stdout 和日志文件"""
    print(msg, flush=True)
    if log_file:
        log_file.write(msg + "\n")
        log_file.flush()


async def run_query(prompt: str, session_id: Optional[str], log_file) -> Dict[str, Any]:
    """执行单个查询，完整记录中间过程"""
    start = time.time()
    answer = ""
    new_session_id = session_id
    cost = 0.0
    num_turns = 0
    tools_used = []
    messages_log = []  # 完整消息日志

    try:
        if session_id:
            opts = ClaudeAgentOptions(
                resume=session_id,
                permission_mode="bypassPermissions",
                max_turns=15,
            )
        else:
            opts = ClaudeAgentOptions(**BASE_OPTIONS)

        async for msg in query(prompt=prompt, options=opts):
            # 记录每条消息的完整信息
            msg_dict = {}
            for attr in ["type", "subtype", "role", "result", "session_id",
                         "cost_usd", "num_turns", "tool_name", "tool_input",
                         "tool_result", "content", "text", "data",
                         "stop_reason", "duration_ms", "total_cost_usd",
                         "usage", "modelUsage", "permission_denials"]:
                val = getattr(msg, attr, None)
                if val is not None:
                    try:
                        json.dumps(val)  # 确保可序列化
                        msg_dict[attr] = val
                    except (TypeError, ValueError):
                        msg_dict[attr] = str(val)

            messages_log.append(msg_dict)

            # 详细日志输出 - 解析 SDK 消息结构
            subtype = getattr(msg, "subtype", None)
            content = getattr(msg, "content", None)

            if subtype == "init":
                data = getattr(msg, "data", {}) or {}
                if isinstance(data, dict):
                    new_session_id = data.get("session_id", new_session_id)
                    model = data.get("model", "unknown")
                    log(f"    [INIT] session={new_session_id} model={model}", log_file)
                if hasattr(msg, "session_id"):
                    new_session_id = msg.session_id

            elif subtype == "success":
                # 最终结果
                if hasattr(msg, "result"):
                    answer = msg.result if isinstance(msg.result, str) else str(msg.result)
                num_turns = getattr(msg, "num_turns", num_turns)
                cost = getattr(msg, "total_cost_usd", cost) or cost
                duration = getattr(msg, "duration_ms", 0)
                log(f"    [RESULT] {len(answer)} chars | {num_turns} turns | {duration}ms", log_file)

            elif content:
                # 解析 content blocks（TextBlock, ToolUseBlock, ToolResultBlock）
                if isinstance(content, list):
                    for block in content:
                        block_type = getattr(block, "type", None)
                        if block_type is None and isinstance(block, dict):
                            block_type = block.get("type", "")

                        if block_type == "text" or (hasattr(block, "text") and not hasattr(block, "name") and not hasattr(block, "tool_use_id")):
                            # TextBlock - Claude 的推理/回复
                            text = getattr(block, "text", "") if hasattr(block, "text") else block.get("text", "")
                            if text:
                                # 多行文本截断显示
                                lines = text.strip().split("\n")
                                preview = lines[0][:200]
                                if len(lines) > 1:
                                    preview += f" (+{len(lines)-1} lines)"
                                log(f"    [THINK] {preview}", log_file)

                        elif block_type == "tool_use" or hasattr(block, "name"):
                            # ToolUseBlock - 工具调用
                            tool_name = getattr(block, "name", "unknown")
                            tool_input = getattr(block, "input", {})
                            if isinstance(tool_input, dict):
                                input_str = json.dumps(tool_input, ensure_ascii=False)
                            else:
                                input_str = str(tool_input)
                            if len(input_str) > 300:
                                input_str = input_str[:300] + "..."
                            log(f"    [TOOL] {tool_name}({input_str})", log_file)
                            tools_used.append(tool_name)

                        elif block_type == "tool_result" or hasattr(block, "tool_use_id"):
                            # ToolResultBlock - 工具返回
                            result_content = getattr(block, "content", "")
                            if isinstance(result_content, str):
                                # 截断长结果，保留关键信息
                                lines = result_content.strip().split("\n")
                                if len(lines) > 5:
                                    preview = "\n".join(lines[:3]) + f"\n    ... ({len(lines)} lines total)"
                                else:
                                    preview = result_content[:400]
                                log(f"    [TOOL_OUT] {preview}", log_file)
                            elif isinstance(result_content, list):
                                for rc in result_content:
                                    rc_text = getattr(rc, "text", str(rc)) if hasattr(rc, "text") else str(rc)
                                    log(f"    [TOOL_OUT] {rc_text[:300]}", log_file)

            # 提取元数据
            if hasattr(msg, "cost_usd") and msg.cost_usd:
                cost = msg.cost_usd
            if hasattr(msg, "total_cost_usd") and msg.total_cost_usd:
                cost = msg.total_cost_usd
            if hasattr(msg, "num_turns") and msg.num_turns:
                num_turns = msg.num_turns

            # 检查 permission denials
            denials = getattr(msg, "permission_denials", None)
            if denials:
                for d in denials:
                    tool = d.get("tool_name", "unknown") if isinstance(d, dict) else str(d)
                    log(f"    [DENIED] {tool}", log_file)

        elapsed = time.time() - start
        return {
            "status": "success",
            "answer": answer,
            "session_id": new_session_id,
            "elapsed": elapsed,
            "cost_usd": cost,
            "num_turns": num_turns,
            "tools_used": tools_used,
            "messages_log": messages_log,
        }
    except Exception as e:
        elapsed = time.time() - start
        log(f"    [ERROR] {e}", log_file)
        return {
            "status": "error",
            "error": str(e),
            "session_id": new_session_id,
            "elapsed": elapsed,
            "messages_log": messages_log,
        }


def evaluate(tc: Dict, result: Dict) -> Dict:
    """两阶段评估: Gate 门禁 (确定性) → 关键词质量检查 (辅助)。"""
    ev = {"passed": False, "reasons": [], "quality": {}, "gate": {}}

    if result["status"] != "success":
        ev["reasons"].append(f"执行失败: {result.get('error', '')[:80]}")
        return ev

    answer = result.get("answer", "")
    messages_log = result.get("messages_log", [])

    # ── Stage 1: 结构化 context 提取 ──
    contexts = extract_contexts(messages_log)
    ev["quality"]["contexts_count"] = len(contexts)
    ev["quality"]["tools_used"] = get_tools_used(contexts)
    ev["quality"]["retrieved_paths"] = get_retrieved_doc_paths(contexts)

    # ── Stage 2: Gate 门禁 ──
    gate = gate_check(tc, answer, contexts)
    ev["gate"] = gate

    if not gate["passed"]:
        ev["passed"] = False
        ev["reasons"] = gate["reasons"]
        return ev

    # ── Stage 3: 质量检查 (Gate 通过后的辅助指标) ──
    if len(answer) < 50:
        ev["reasons"].append(f"答案过短 ({len(answer)})")
        return ev

    # 引用质量 (从 gate 获取)
    ev["quality"]["has_citation"] = gate["checks"].get("has_citation", False)

    # 关键词匹配 (辅助信号，不作为 pass/fail 判据)
    expected = KEYWORD_CHECKS.get(tc["category"], [])
    matched = [k for k in expected if k.lower() in answer.lower()]
    ev["quality"]["keywords"] = matched

    # 正确文档引用 (从 gate 的 expected_doc_hit 获取)
    ev["quality"]["correct_doc"] = gate["checks"].get("expected_doc_hit", None)

    # Gate 通过 + 答案足够长 → 通过
    if len(answer) >= 50:
        ev["passed"] = True
    else:
        ev["reasons"].append(f"答案过短 ({len(answer)})")

    return ev


async def main():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_dir = PROJECT_ROOT / "eval" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"agentic_rag_{timestamp}.log"
    detail_path = log_dir / f"agentic_rag_{timestamp}_detail.jsonl"

    with open(log_path, "w", encoding="utf-8") as lf, \
         open(detail_path, "w", encoding="utf-8") as df:

        mode = "MCP + Grep/Glob/Read" if USE_MCP else "Grep/Glob/Read (无 MCP)"
        kb_commit_header = get_kb_commit()
        log("=" * 80, lf)
        log(f"🤖 Agentic RAG 测试 (Agent SDK)", lf)
        log("=" * 80, lf)
        log(f"用例: {len(TEST_CASES)} | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", lf)
        log(f"模式: {mode}", lf)
        log(f"KB commit: {kb_commit_header}", lf)
        log(f"评估: eval_module (Gate 门禁 + 质量检查)", lf)
        log(f"策略: Claude 自主选择检索策略 (Grep/Glob/Read{' + MCP hybrid_search' if USE_MCP else ''})", lf)
        log(f"日志: {log_path}", lf)
        log(f"详细: {detail_path}", lf)
        log("", lf)

        results = []
        passed = failed = errors = 0
        total_time = total_cost = 0.0
        session_id = None

        for i, tc in enumerate(TEST_CASES, 1):
            log(f"\n{'='*60}", lf)
            log(f"[{i}/{len(TEST_CASES)}] {tc['id']} ({tc['category']}) [{tc.get('type', '?')}]", lf)
            log(f"  Q: {tc['query']}", lf)
            if tc.get("note"):
                log(f"  💡 {tc['note']}", lf)
            if i == 1:
                log(f"  ⏳ 首次查询，加载 MCP server (BGE-M3)...", lf)
            log(f"  开始: {datetime.now().strftime('%H:%M:%S')}", lf)

            # 如果有 MCP + skills，用 /search；否则直接提问
            prompt = f"/search {tc['query']}" if USE_MCP else f"请在 docs/ 目录中检索并回答: {tc['query']}"
            result = await run_query(prompt, session_id, lf)

            if result.get("session_id"):
                session_id = result["session_id"]
                if i == 1:
                    log(f"  📌 Session: {session_id}", lf)

            elapsed = result.get("elapsed", 0)
            total_time += elapsed
            total_cost += result.get("cost_usd", 0)

            ev = evaluate(tc, result)

            if result["status"] == "error":
                log(f"  ❌ 错误: {result.get('error', '')[:80]}", lf)
                errors += 1
                status = "error"
            elif ev["passed"]:
                ans_len = len(result.get("answer", ""))
                quality = ev.get("quality", {})
                tools = quality.get("tools_used", [])
                cite = "引用✅" if quality.get("has_citation") else "引用❌"
                correct_doc = quality.get("correct_doc")
                doc_tag = "文档✅" if correct_doc else ("文档❌" if correct_doc is False else "")
                ctx_count = quality.get("contexts_count", 0)
                kw = quality.get("keywords", [])
                log(f"  ✅ 通过 | {ans_len}字符 | {elapsed:.1f}s | ${result.get('cost_usd', 0):.4f} | {cite} {doc_tag} | ctx:{ctx_count}", lf)
                if tools:
                    log(f"  🔧 工具: {', '.join(tools)}", lf)
                if quality.get("retrieved_paths"):
                    log(f"  📄 检索: {', '.join(quality['retrieved_paths'][:5])}", lf)
                if kw:
                    log(f"  🔑 关键词: {', '.join(kw)}", lf)
                passed += 1
                status = "passed"
            else:
                log(f"  ❌ 失败: {'; '.join(ev['reasons'])}", lf)
                failed += 1
                status = "failed"

            # 输出答案预览（通过和失败都输出）
            ans_preview = result.get("answer", "")[:500]
            if ans_preview:
                log(f"  📝 答案: {ans_preview}{'...' if len(result.get('answer',''))>500 else ''}", lf)

            log(f"  结束: {datetime.now().strftime('%H:%M:%S')} | 耗时: {elapsed:.1f}s", lf)

            # 写入详细 JSONL（每个 query 一行，包含完整消息日志）
            gate = ev.get("gate", {})
            quality = ev.get("quality", {})
            detail_record = {
                "test_id": tc["id"],
                "category": tc["category"],
                "type": tc.get("type", "unknown"),
                "source": tc.get("source", "unknown"),
                "query": tc["query"],
                "status": status,
                "elapsed_seconds": elapsed,
                "cost_usd": result.get("cost_usd", 0),
                "num_turns": result.get("num_turns", 0),
                "answer_length": len(result.get("answer", "")),
                "answer": result.get("answer", ""),
                "tools_used": quality.get("tools_used", []),
                "retrieved_paths": quality.get("retrieved_paths", []),
                "contexts_count": quality.get("contexts_count", 0),
                "has_citation": quality.get("has_citation", False),
                "correct_doc": quality.get("correct_doc"),
                "matched_keywords": quality.get("keywords", []),
                "gate_passed": gate.get("passed"),
                "gate_checks": gate.get("checks", {}),
                "failure_reasons": ev.get("reasons", []),
                "messages": result.get("messages_log", []),
            }
            df.write(json.dumps(detail_record, ensure_ascii=False) + "\n")
            df.flush()

            results.append({
                "test_id": tc["id"], "category": tc["category"],
                "type": tc.get("type", "unknown"),
                "source": tc.get("source", "unknown"),
                "query": tc["query"],
                "status": status, "elapsed_seconds": elapsed,
                "cost_usd": result.get("cost_usd", 0),
                "num_turns": result.get("num_turns", 0),
                "answer_length": len(result.get("answer", "")),
                "tools_used": quality.get("tools_used", []),
                "retrieved_paths": quality.get("retrieved_paths", []),
                "contexts_count": quality.get("contexts_count", 0),
                "has_citation": quality.get("has_citation", False),
                "correct_doc": quality.get("correct_doc"),
                "matched_keywords": quality.get("keywords", []),
                "gate_passed": gate.get("passed"),
                "failure_reasons": ev.get("reasons", []),
                "answer_preview": result.get("answer", "")[:300],
            })
            log("-" * 80, lf)

        # 总结
        total = len(TEST_CASES)
        log(f"\n{'=' * 80}", lf)
        log(f"📊 总结: ✅{passed} ❌{failed} ⚠️{errors} / {total} ({passed/total*100:.1f}%)", lf)
        log(f"⏱️  总耗时: {total_time:.1f}s | 平均: {total_time/max(passed+failed,1):.1f}s", lf)
        log(f"💰 总费用: ${total_cost:.4f}", lf)

        # 按查询类型统计
        type_stats = {}
        for i2, r in enumerate(results):
            qtype = TEST_CASES[i2].get("type", "unknown")
            type_stats.setdefault(qtype, {"t": 0, "p": 0})
            type_stats[qtype]["t"] += 1
            if r["status"] == "passed": type_stats[qtype]["p"] += 1

        log("", lf)
        log("📈 按查询类型:", lf)
        type_labels = {
            "exact": "精确匹配(Grep擅长)",
            "scenario": "SO场景/症状描述",
            "cross-lang": "跨语言",
            "howto": "实操问答",
            "multi-doc": "多文档综合",
            "concept": "概念型(需Qdrant)",
            "notfound": "未收录",
        }
        for t, s in sorted(type_stats.items()):
            r2 = s["p"]/s["t"]*100
            label = type_labels.get(t, t)
            log(f"  {'✅' if r2==100 else '⚠️' if r2>0 else '❌'} {label}: {s['p']}/{s['t']} ({r2:.0f}%)", lf)

        log("", lf)
        log("📋 按 category:", lf)
        cats = {}
        for r in results:
            c = r["category"]
            cats.setdefault(c, {"t": 0, "p": 0})
            cats[c]["t"] += 1
            if r["status"] == "passed": cats[c]["p"] += 1
        for c, s in sorted(cats.items()):
            r2 = s["p"]/s["t"]*100
            log(f"  {'✅' if r2==100 else '⚠️' if r2>0 else '❌'} {c}: {s['p']}/{s['t']} ({r2:.0f}%)", lf)

        # 按数据源统计
        source_stats = {}
        for i2, r in enumerate(results):
            src = TEST_CASES[i2].get("source", "unknown")
            source_stats.setdefault(src, {"t": 0, "p": 0})
            source_stats[src]["t"] += 1
            if r["status"] == "passed": source_stats[src]["p"] += 1

        log("", lf)
        log("🗄️ 按数据源:", lf)
        source_labels = {
            "local": "本地 docs/ (Grep/Glob/Read)",
            "qdrant": "Qdrant 索引 (需 MCP hybrid_search)",
        }
        for src, s in sorted(source_stats.items()):
            r2 = s["p"]/s["t"]*100
            label = source_labels.get(src, src)
            icon = "✅" if r2 == 100 else ("⚠️" if r2 > 0 else "❌")
            log(f"  {icon} {label}: {s['p']}/{s['t']} ({r2:.0f}%)", lf)

        if not USE_MCP and source_stats.get("qdrant", {}).get("t", 0) > 0:
            qdrant_total = source_stats["qdrant"]["t"]
            qdrant_pass = source_stats["qdrant"]["p"]
            log(f"\n  ⚠️  注意: {qdrant_total} 个 Qdrant 用例在无 MCP 模式下运行", lf)
            log(f"     通过 {qdrant_pass}/{qdrant_total} — 可能是 Claude 用通用知识回答（非检索）", lf)
            log(f"     设置 USE_MCP=1 启用 hybrid_search 以测试真正的向量检索", lf)

        # 保存汇总 JSON
        kb_commit = get_kb_commit()
        out_dir = PROJECT_ROOT / "eval"
        out_file = out_dir / f"agentic_rag_test_{timestamp}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(), "test_type": "agentic_rag",
                "method": "claude_agent_sdk_session_reuse", "total": total,
                "passed": passed, "failed": failed, "errors": errors,
                "total_time": total_time, "total_cost": total_cost,
                "kb_commit": kb_commit,
                "eval_module": "eval_module.py (gate + quality)",
                "type_stats": {t: {"total": s["t"], "passed": s["p"]} for t, s in type_stats.items()},
                "source_stats": {s: {"total": v["t"], "passed": v["p"]} for s, v in source_stats.items()},
                "use_mcp": USE_MCP,
                "results": results,
            }, f, indent=2, ensure_ascii=False)

        log(f"\n📁 汇总: {out_file}", lf)
        log(f"📋 日志: {log_path}", lf)
        log(f"📝 详细: {detail_path}", lf)

    # 生成对比报告
    generate_comparison(str(out_file))
    return results


def generate_comparison(agentic_file: str):
    """生成 Simple RAG vs Agentic RAG 对比"""
    baseline = PROJECT_ROOT / "eval" / "comprehensive_test_20260213_234320.json"
    if not baseline.exists():
        candidates = sorted((PROJECT_ROOT / "eval").glob("comprehensive_test_*.json"))
        if not candidates:
            print("❌ 未找到 Simple RAG baseline", flush=True)
            return
        baseline = candidates[-1]

    with open(baseline) as f: simple = json.load(f)
    with open(agentic_file) as f: agentic = json.load(f)

    s_map = {r["test_id"]: r for r in simple["results"]}
    a_map = {r["test_id"]: r for r in agentic["results"]}
    s_rate = simple["passed"]/simple["total"]*100
    a_rate = agentic["passed"]/agentic["total"]*100
    s_avg = simple.get("total_time",0)/simple["total"]
    a_avg = agentic.get("total_time",0)/agentic["total"]

    improved = [t for t in TEST_CASES if s_map.get(t["id"],{}).get("status")!="passed" and a_map.get(t["id"],{}).get("status")=="passed"]
    regressed = [t for t in TEST_CASES if s_map.get(t["id"],{}).get("status")=="passed" and a_map.get(t["id"],{}).get("status")!="passed"]

    report = f"""# Simple RAG vs Agentic RAG 对比报告

**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | **方法**: Claude Agent SDK + Session 复用

## 📊 总体

| 指标 | Simple RAG | Agentic RAG | 变化 |
|------|-----------|-------------|------|
| 通过率 | {simple['passed']}/{simple['total']} ({s_rate:.1f}%) | {agentic['passed']}/{agentic['total']} ({a_rate:.1f}%) | **{a_rate-s_rate:+.1f}%** |
| 失败 | {simple['failed']} | {agentic['failed']} | {agentic['failed']-simple['failed']:+d} |
| 平均耗时 | {s_avg:.1f}s | {a_avg:.1f}s | {a_avg-s_avg:+.1f}s |
| 费用 | ~${simple.get('total_tokens',0)*0.000003:.4f} | ${agentic.get('total_cost',0):.4f} | - |

## 逐用例

| ID | 查询 | Simple | Agentic | |
|----|------|--------|---------|--|
"""
    for tc in TEST_CASES:
        s = "✅" if s_map.get(tc["id"],{}).get("status")=="passed" else "❌"
        a = "✅" if a_map.get(tc["id"],{}).get("status")=="passed" else "❌"
        ch = "🟢" if s=="❌" and a=="✅" else "🔴" if s=="✅" and a=="❌" else ""
        q = tc["query"][:35]+"..." if len(tc["query"])>35 else tc["query"]
        report += f"| {tc['id']} | {q} | {s} | {a} | {ch} |\n"

    if improved:
        report += f"\n## 🟢 改善 ({len(improved)})\n\n"
        for tc in improved:
            a = a_map.get(tc["id"],{})
            report += f"- **{tc['id']}**: {tc['query']} → {a.get('answer_length',0)}字符, 工具: {', '.join(a.get('tools_used',[]))}\n"

    if regressed:
        report += f"\n## 🔴 退步 ({len(regressed)})\n\n"
        for tc in regressed:
            a = a_map.get(tc["id"],{})
            report += f"- **{tc['id']}**: {tc['query']} → {'; '.join(a.get('failure_reasons',[]))}\n"

    report += f"\n## 结论\n\n通过率 {s_rate:.1f}% → {a_rate:.1f}% ({a_rate-s_rate:+.1f}%), 改善 {len(improved)} 个, 退步 {len(regressed)} 个。\n"

    rf = PROJECT_ROOT / "eval" / f"AGENTIC_VS_SIMPLE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(rf, "w", encoding="utf-8") as f: f.write(report)
    print(f"📊 报告: {rf}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
