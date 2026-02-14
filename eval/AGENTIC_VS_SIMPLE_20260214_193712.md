# Simple RAG vs Agentic RAG 对比报告

**时间**: 2026-02-14 19:37:12 | **方法**: Claude Agent SDK + Session 复用

## 📊 总体

| 指标 | Simple RAG | Agentic RAG | 变化 |
|------|-----------|-------------|------|
| 通过率 | 8/15 (53.3%) | 39/64 (60.9%) | **+7.6%** |
| 失败 | 7 | 25 | +18 |
| 平均耗时 | 46.3s | 103.2s | +56.9s |
| 费用 | ~$0.0255 | $3.2960 | - |

## 逐用例

| ID | 查询 | Simple | Agentic | |
|----|------|--------|---------|--|
| local-exact-001 | READONLY You can't write against a ... | ❌ | ✅ | 🟢 |
| local-exact-002 | kubectl describe pod 显示 OOMKilled 怎... | ❌ | ✅ | 🟢 |
| local-exact-003 | API 返回 401 TOKEN_EXPIRED，前端该怎么处理 | ❌ | ✅ | 🟢 |
| local-exact-004 | redis-cli SENTINEL get-master-addr-... | ❌ | ✅ | 🟢 |
| local-exact-005 | JWT RS256 签名验证流程是什么 | ❌ | ✅ | 🟢 |
| local-so-001 | 线上 Redis 突然大量写入失败，错误日志一直刷屏，应用都快挂了，急... | ❌ | ✅ | 🟢 |
| local-so-002 | 我的 pod 一直在 restart，已经重启了 50 多次了，des... | ❌ | ✅ | 🟢 |
| local-so-003 | 用户反馈说登录之后过一会儿就被踢出来了，要重新登录，是 token 的... | ❌ | ✅ | 🟢 |
| local-so-004 | 容器跑着跑着就被 kill 了，感觉是内存的问题但不确定怎么查 | ❌ | ✅ | 🟢 |
| local-so-005 | Redis 主库挂了之后从库顶上去了，但是应用还是连的旧地址，怎么让应... | ❌ | ✅ | 🟢 |
| local-so-006 | 我们有个多租户系统，不同租户的用户不能互相访问数据，这个权限怎么设计的 | ❌ | ✅ | 🟢 |
| local-cross-001 | How to recover when Redis sentinel ... | ❌ | ✅ | 🟢 |
| local-cross-002 | K8s 容器因为 liveness probe 失败一直重启怎么排查 | ❌ | ✅ | 🟢 |
| local-howto-001 | 怎么确认 Redis Sentinel 当前的 master 是哪个节... | ❌ | ✅ | 🟢 |
| local-howto-002 | 怎么看上一次容器崩溃的日志 | ❌ | ✅ | 🟢 |
| local-howto-003 | access_token 过期了怎么续期，调哪个接口 | ❌ | ✅ | 🟢 |
| local-multi-001 | Pod 重启后 Redis 连接断了，从排查 Pod 到恢复 Redi... | ❌ | ✅ | 🟢 |
| qdrant-redis-sentinel-001 | How does Redis Sentinel automatic f... | ❌ | ❌ |  |
| qdrant-redis-sentinel-002 | Redis Sentinel 的 quorum 是什么意思？怎么配置？ | ❌ | ❌ |  |
| qdrant-redis-repl-001 | Redis master-replica replication 是异... | ❌ | ✅ | 🟢 |
| qdrant-redis-repl-002 | Redis replica 断开连接后重连，是全量同步还是部分同步？ | ❌ | ❌ |  |
| qdrant-redis-persist-001 | RDB 和 AOF 有什么区别？该用哪个？ | ❌ | ❌ |  |
| qdrant-redis-persist-002 | Redis AOF rewrite 是怎么工作的？会阻塞主线程吗？ | ❌ | ❌ |  |
| qdrant-redis-cluster-001 | Redis Cluster 的 hash slot 是怎么分配的？ | ❌ | ❌ |  |
| qdrant-redis-strings-001 | Redis Strings 除了缓存还能做什么？支持哪些操作？ | ❌ | ❌ |  |
| qdrant-redis-sorted-set-001 | How to implement a leaderboard with... | ❌ | ✅ | 🟢 |
| qdrant-redis-streams-001 | Redis Streams 和 Pub/Sub 有什么区别？什么时候用... | ❌ | ❌ |  |
| qdrant-redis-bloom-001 | What is a Bloom filter in Redis and... | ❌ | ❌ |  |
| qdrant-redis-latency-001 | Redis 延迟突然变高怎么排查？有哪些常见原因？ | ❌ | ❌ |  |
| qdrant-redis-memory-001 | Redis 内存占用太高怎么优化？ | ❌ | ✅ | 🟢 |
| qdrant-redis-acl-001 | How to set up Redis ACL to restrict... | ❌ | ❌ |  |
| qdrant-redis-pipelining-001 | Redis pipelining 的原理是什么？和普通请求有什么区别？ | ❌ | ✅ | 🟢 |
| qdrant-redis-transactions-001 | Redis MULTI/EXEC 事务和 Lua 脚本哪个更好？ | ❌ | ❌ |  |
| qdrant-redis-debug-001 | 线上 Redis 出问题了怎么 debug？有哪些诊断命令？ | ❌ | ❌ |  |
| qdrant-redis-benchmark-001 | How to benchmark Redis performance?... | ❌ | ✅ | 🟢 |
| qdrant-redis-so-001 | 我的 Redis 主从同步一直断，日志里刷 LOADING Redis... | ❌ | ✅ | 🟢 |
| qdrant-redis-so-002 | Redis used_memory 比 maxmemory 大很多，但... | ❌ | ✅ | 🟢 |
| qdrant-k8s-pod-001 | What is a Pod in Kubernetes? | ❌ | ❌ |  |
| qdrant-k8s-service-001 | Kubernetes Service 有哪些类型？ClusterIP ... | ❌ | ✅ | 🟢 |
| qdrant-k8s-deploy-001 | Deployment 滚动更新卡住了，新旧 Pod 并存，怎么回滚？ | ❌ | ✅ | 🟢 |
| qdrant-k8s-configmap-001 | How to use ConfigMap to inject conf... | ❌ | ✅ | 🟢 |
| qdrant-k8s-secret-001 | Kubernetes Secret 和 ConfigMap 有什么区别... | ❌ | ❌ |  |
| qdrant-k8s-probe-001 | liveness probe 和 readiness probe 有什... | ❌ | ❌ |  |
| qdrant-k8s-ingress-001 | How does Kubernetes Ingress route t... | ❌ | ✅ | 🟢 |
| qdrant-k8s-volume-001 | Kubernetes 里怎么给 Pod 挂载持久化存储？PV 和 PV... | ❌ | ❌ |  |
| qdrant-k8s-init-001 | What are Init Containers and when s... | ❌ | ✅ | 🟢 |
| qdrant-k8s-lifecycle-001 | Pod 的生命周期有哪些阶段？Pending 和 Running 的区... | ❌ | ❌ |  |
| qdrant-k8s-namespace-001 | Kubernetes Namespace 是什么？什么时候需要用多个 ... | ❌ | ✅ | 🟢 |
| qdrant-k8s-label-001 | How do Labels and Selectors work in... | ❌ | ❌ |  |
| qdrant-k8s-resource-001 | 怎么给 Pod 设置 CPU 和内存的 requests 和 limi... | ❌ | ❌ |  |
| qdrant-k8s-node-001 | Kubernetes Node 的状态有哪些？NotReady 是什么... | ❌ | ❌ |  |
| qdrant-k8s-gc-001 | Kubernetes garbage collection 是怎么清理... | ❌ | ✅ | 🟢 |
| qdrant-k8s-so-001 | Pod 一直 Pending 不调度，describe 显示 Insu... | ❌ | ❌ |  |
| qdrant-k8s-so-002 | Deployment rollout 卡在 Progressing，m... | ❌ | ❌ |  |
| qdrant-k8s-so-003 | What's the difference between a Dep... | ❌ | ✅ | 🟢 |
| qdrant-k8s-so-004 | Container 的 preStop hook 没执行就被 kill... | ❌ | ❌ |  |
| qdrant-k8s-so-005 | LimitRange 和 ResourceQuota 有什么区别？怎么... | ❌ | ✅ | 🟢 |
| notfound-001 | Kubernetes HPA 自动扩缩容怎么配置 | ✅ | ❌ | 🔴 |
| notfound-002 | MongoDB 分片集群如何配置 | ❌ | ✅ | 🟢 |
| notfound-003 | Kafka consumer group rebalance 怎么优化... | ❌ | ✅ | 🟢 |
| notfound-004 | How to set up Prometheus alerting r... | ❌ | ✅ | 🟢 |
| notfound-005 | Nginx 反向代理配置 upstream 负载均衡 | ❌ | ✅ | 🟢 |
| notfound-006 | MySQL InnoDB 死锁怎么排查和解决？ | ❌ | ✅ | 🟢 |
| notfound-007 | Docker Compose 多容器编排怎么配置网络？ | ❌ | ✅ | 🟢 |

## 🟢 改善 (39)

- **local-exact-001**: READONLY You can't write against a read only replica 这个报错怎么解决 → 805字符, 工具: Grep
- **local-exact-002**: kubectl describe pod 显示 OOMKilled 怎么办 → 979字符, 工具: Grep
- **local-exact-003**: API 返回 401 TOKEN_EXPIRED，前端该怎么处理 → 1197字符, 工具: Read, Grep
- **local-exact-004**: redis-cli SENTINEL get-master-addr-by-name 命令返回什么 → 554字符, 工具: Grep
- **local-exact-005**: JWT RS256 签名验证流程是什么 → 604字符, 工具: Read, Grep
- **local-so-001**: 线上 Redis 突然大量写入失败，错误日志一直刷屏，应用都快挂了，急！ → 828字符, 工具: Grep, Glob
- **local-so-002**: 我的 pod 一直在 restart，已经重启了 50 多次了，describe 看了也没啥有用信息 → 1173字符, 工具: Read, Grep
- **local-so-003**: 用户反馈说登录之后过一会儿就被踢出来了，要重新登录，是 token 的问题吗 → 536字符, 工具: Read, Grep
- **local-so-004**: 容器跑着跑着就被 kill 了，感觉是内存的问题但不确定怎么查 → 1382字符, 工具: Grep
- **local-so-005**: Redis 主库挂了之后从库顶上去了，但是应用还是连的旧地址，怎么让应用自动切换 → 884字符, 工具: Grep
- **local-so-006**: 我们有个多租户系统，不同租户的用户不能互相访问数据，这个权限怎么设计的 → 963字符, 工具: Read, Grep
- **local-cross-001**: How to recover when Redis sentinel triggers a failover? → 1607字符, 工具: Grep
- **local-cross-002**: K8s 容器因为 liveness probe 失败一直重启怎么排查 → 1455字符, 工具: Read, Grep
- **local-howto-001**: 怎么确认 Redis Sentinel 当前的 master 是哪个节点 → 809字符, 工具: Grep
- **local-howto-002**: 怎么看上一次容器崩溃的日志 → 614字符, 工具: Grep
- **local-howto-003**: access_token 过期了怎么续期，调哪个接口 → 469字符, 工具: Grep
- **local-multi-001**: Pod 重启后 Redis 连接断了，从排查 Pod 到恢复 Redis 连接的完整流程是什么 → 1838字符, 工具: Read, Grep, Glob
- **qdrant-redis-repl-001**: Redis master-replica replication 是异步的还是同步的？ → 603字符, 工具: Grep
- **qdrant-redis-sorted-set-001**: How to implement a leaderboard with Redis Sorted Sets? → 1600字符, 工具: Grep
- **qdrant-redis-memory-001**: Redis 内存占用太高怎么优化？ → 1279字符, 工具: Grep
- **qdrant-redis-pipelining-001**: Redis pipelining 的原理是什么？和普通请求有什么区别？ → 1138字符, 工具: Grep
- **qdrant-redis-benchmark-001**: How to benchmark Redis performance? What tool should I use? → 1794字符, 工具: Grep
- **qdrant-redis-so-001**: 我的 Redis 主从同步一直断，日志里刷 LOADING Redis is loading the dataset in memory → 1510字符, 工具: Read, Grep
- **qdrant-redis-so-002**: Redis used_memory 比 maxmemory 大很多，但 keys 不多，内存去哪了？ → 980字符, 工具: Read, Grep
- **qdrant-k8s-service-001**: Kubernetes Service 有哪些类型？ClusterIP 和 NodePort 的区别？ → 1226字符, 工具: Grep
- **qdrant-k8s-deploy-001**: Deployment 滚动更新卡住了，新旧 Pod 并存，怎么回滚？ → 878字符, 工具: Grep
- **qdrant-k8s-configmap-001**: How to use ConfigMap to inject configuration into a Pod? → 2133字符, 工具: Grep
- **qdrant-k8s-ingress-001**: How does Kubernetes Ingress route traffic to different services? → 2291字符, 工具: Grep
- **qdrant-k8s-init-001**: What are Init Containers and when should I use them? → 2124字符, 工具: Grep
- **qdrant-k8s-namespace-001**: Kubernetes Namespace 是什么？什么时候需要用多个 Namespace？ → 1072字符, 工具: Grep
- **qdrant-k8s-gc-001**: Kubernetes garbage collection 是怎么清理资源的？ → 945字符, 工具: Grep
- **qdrant-k8s-so-003**: What's the difference between a Deployment and a ReplicationController? → 1839字符, 工具: Grep
- **qdrant-k8s-so-005**: LimitRange 和 ResourceQuota 有什么区别？怎么限制单个 Pod 的资源？ → 1916字符, 工具: Grep
- **notfound-002**: MongoDB 分片集群如何配置 → 216字符, 工具: Grep
- **notfound-003**: Kafka consumer group rebalance 怎么优化？ → 101字符, 工具: Grep
- **notfound-004**: How to set up Prometheus alerting rules? → 195字符, 工具: Grep
- **notfound-005**: Nginx 反向代理配置 upstream 负载均衡 → 94字符, 工具: Grep
- **notfound-006**: MySQL InnoDB 死锁怎么排查和解决？ → 88字符, 工具: Grep
- **notfound-007**: Docker Compose 多容器编排怎么配置网络？ → 306字符, 工具: Grep

## 🔴 退步 (1)

- **notfound-001**: Kubernetes HPA 自动扩缩容怎么配置 → notfound 用例输出了具体事实断言（疑似幻觉）

## 结论

通过率 53.3% → 60.9% (+7.6%), 改善 39 个, 退步 1 个。
