# Simple RAG vs Agentic RAG 对比报告

**时间**: 2026-02-14 09:16:14 | **方法**: Claude Agent SDK + Session 复用

## 📊 总体

| 指标 | Simple RAG | Agentic RAG | 变化 |
|------|-----------|-------------|------|
| 通过率 | 8/15 (53.3%) | 34/34 (100.0%) | **+46.7%** |
| 失败 | 7 | 0 | -7 |
| 平均耗时 | 46.3s | 23.2s | -23.1s |
| 费用 | ~$0.0255 | $4.0812 | - |

## 逐用例

| ID | 查询 | Simple | Agentic | |
|----|------|--------|---------|--|
| basic-001 | What is a Pod in Kubernetes? | ✅ | ✅ |  |
| basic-002 | Kubernetes Service 是什么？ | ✅ | ✅ |  |
| basic-003 | What are Init Containers? | ✅ | ✅ |  |
| grep-001 | READONLY You can't write against a ... | ❌ | ✅ | 🟢 |
| grep-002 | OOMKilled | ❌ | ✅ | 🟢 |
| grep-003 | TOKEN_EXPIRED 错误码是什么意思？ | ❌ | ✅ | 🟢 |
| grep-004 | JWT token 的结构是什么？ | ❌ | ✅ | 🟢 |
| grep-005 | SENTINEL failover 命令怎么用？ | ❌ | ✅ | 🟢 |
| semantic-001 | 应用突然无法写入缓存，日志报只读错误 | ❌ | ✅ | 🟢 |
| semantic-002 | 容器一直重启，无法正常运行 | ❌ | ✅ | 🟢 |
| semantic-003 | 内存不足导致进程被杀 | ❌ | ✅ | 🟢 |
| semantic-004 | 用户登录后如何保持会话状态？ | ❌ | ✅ | 🟢 |
| cross-lang-001 | Redis 管道技术如何工作？ | ❌ | ✅ | 🟢 |
| cross-lang-002 | How does Redis pipelining improve p... | ✅ | ✅ |  |
| cross-lang-003 | How to recover from Redis master-sl... | ❌ | ✅ | 🟢 |
| cross-lang-004 | Kubernetes pod keeps crashing, how ... | ❌ | ✅ | 🟢 |
| paraphrase-001 | 如何检查 Redis 高可用集群的健康状态？ | ❌ | ✅ | 🟢 |
| paraphrase-002 | API 接口的权限控制是怎么设计的？ | ❌ | ✅ | 🟢 |
| paraphrase-003 | 应用连接数据库缓存的最佳实践 | ❌ | ✅ | 🟢 |
| complex-001 | What's the difference between Deplo... | ❌ | ✅ | 🟢 |
| complex-002 | How to troubleshoot CrashLoopBackOf... | ❌ | ✅ | 🟢 |
| complex-003 | Kubernetes 中如何实现服务发现？ | ✅ | ✅ |  |
| complex-004 | Pod 崩溃后 Redis 连接会怎样？需要怎么处理？ | ❌ | ✅ | 🟢 |
| complex-005 | 系统的安全机制有哪些？从认证到部署都说说 | ❌ | ✅ | 🟢 |
| howto-001 | How to create a Pod with multiple c... | ✅ | ✅ |  |
| howto-002 | 如何配置 Kubernetes 资源限制？ | ❌ | ✅ | 🟢 |
| howto-003 | refresh_token 过期了怎么办？ | ❌ | ✅ | 🟢 |
| howto-004 | 怎么配置 Redis 连接池的空闲超时？ | ❌ | ✅ | 🟢 |
| concept-001 | What is the purpose of a ReplicaSet... | ❌ | ✅ | 🟢 |
| concept-002 | Kubernetes 命名空间的作用是什么？ | ❌ | ✅ | 🟢 |
| edge-001 | What is a sidecar container? | ✅ | ✅ |  |
| edge-002 | Kubernetes 中的 DaemonSet 是什么？ | ❌ | ✅ | 🟢 |
| notfound-001 | How to configure Kubernetes with bl... | ✅ | ✅ |  |
| notfound-002 | MongoDB 分片集群如何配置？ | ❌ | ✅ | 🟢 |

## 🟢 改善 (26)

- **grep-001**: READONLY You can't write against a read only replica → 731字符, 工具: Read, Grep
- **grep-002**: OOMKilled → 707字符, 工具: Grep
- **grep-003**: TOKEN_EXPIRED 错误码是什么意思？ → 660字符, 工具: Read, Grep
- **grep-004**: JWT token 的结构是什么？ → 696字符, 工具: Grep
- **grep-005**: SENTINEL failover 命令怎么用？ → 642字符, 工具: Grep
- **semantic-001**: 应用突然无法写入缓存，日志报只读错误 → 1134字符, 工具: Grep
- **semantic-002**: 容器一直重启，无法正常运行 → 1403字符, 工具: Grep
- **semantic-003**: 内存不足导致进程被杀 → 872字符, 工具: Grep
- **semantic-004**: 用户登录后如何保持会话状态？ → 1068字符, 工具: Grep
- **cross-lang-001**: Redis 管道技术如何工作？ → 498字符, 工具: Read, Glob, Grep
- **cross-lang-003**: How to recover from Redis master-slave failover? → 1317字符, 工具: Grep
- **cross-lang-004**: Kubernetes pod keeps crashing, how to debug? → 1480字符, 工具: Grep
- **paraphrase-001**: 如何检查 Redis 高可用集群的健康状态？ → 865字符, 工具: Grep
- **paraphrase-002**: API 接口的权限控制是怎么设计的？ → 1238字符, 工具: Grep
- **paraphrase-003**: 应用连接数据库缓存的最佳实践 → 841字符, 工具: Grep
- **complex-001**: What's the difference between Deployment and StatefulSet? → 584字符, 工具: Grep
- **complex-002**: How to troubleshoot CrashLoopBackOff in Kubernetes? → 1473字符, 工具: Grep
- **complex-004**: Pod 崩溃后 Redis 连接会怎样？需要怎么处理？ → 1089字符, 工具: Grep
- **complex-005**: 系统的安全机制有哪些？从认证到部署都说说 → 1437字符, 工具: Read, Grep
- **howto-002**: 如何配置 Kubernetes 资源限制？ → 902字符, 工具: Grep
- **howto-003**: refresh_token 过期了怎么办？ → 886字符, 工具: Grep
- **howto-004**: 怎么配置 Redis 连接池的空闲超时？ → 712字符, 工具: Grep
- **concept-001**: What is the purpose of a ReplicaSet? → 701字符, 工具: Grep
- **concept-002**: Kubernetes 命名空间的作用是什么？ → 816字符, 工具: Grep
- **edge-002**: Kubernetes 中的 DaemonSet 是什么？ → 522字符, 工具: Grep
- **notfound-002**: MongoDB 分片集群如何配置？ → 511字符, 工具: Grep

## 结论

通过率 53.3% → 100.0% (+46.7%), 改善 26 个, 退步 0 个。
