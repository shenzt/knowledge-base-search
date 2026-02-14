# Simple RAG vs Agentic RAG 对比报告

**时间**: 2026-02-14 00:54:17 | **方法**: Claude Agent SDK + Session 复用

## 📊 总体

| 指标 | Simple RAG | Agentic RAG | 变化 |
|------|-----------|-------------|------|
| 通过率 | 8/15 (53.3%) | 15/15 (100.0%) | **+46.7%** |
| 失败 | 7 | 0 | -7 |
| 平均耗时 | 46.3s | 24.4s | -21.9s |
| 费用 | ~$0.0255 | $1.2726 | - |

## 逐用例

| ID | 查询 | Simple | Agentic | |
|----|------|--------|---------|--|
| basic-001 | What is a Pod in Kubernetes? | ✅ | ✅ |  |
| basic-002 | Kubernetes Service 是什么？ | ✅ | ✅ |  |
| basic-003 | What are Init Containers? | ✅ | ✅ |  |
| cross-lang-001 | Redis 管道技术如何工作？ | ❌ | ✅ | 🟢 |
| cross-lang-002 | How does Redis pipelining improve p... | ✅ | ✅ |  |
| complex-001 | What's the difference between Deplo... | ❌ | ✅ | 🟢 |
| complex-002 | How to troubleshoot CrashLoopBackOf... | ❌ | ✅ | 🟢 |
| complex-003 | Kubernetes 中如何实现服务发现？ | ✅ | ✅ |  |
| howto-001 | How to create a Pod with multiple c... | ✅ | ✅ |  |
| howto-002 | 如何配置 Kubernetes 资源限制？ | ❌ | ✅ | 🟢 |
| concept-001 | What is the purpose of a ReplicaSet... | ❌ | ✅ | 🟢 |
| concept-002 | Kubernetes 命名空间的作用是什么？ | ❌ | ✅ | 🟢 |
| edge-001 | What is a sidecar container? | ✅ | ✅ |  |
| edge-002 | Kubernetes 中的 DaemonSet 是什么？ | ❌ | ✅ | 🟢 |
| notfound-001 | How to configure Kubernetes with bl... | ✅ | ✅ |  |

## 🟢 改善 (7)

- **cross-lang-001**: Redis 管道技术如何工作？ → 414字符, 工具: Read, Grep
- **complex-001**: What's the difference between Deployment and StatefulSet? → 470字符, 工具: Read, Grep
- **complex-002**: How to troubleshoot CrashLoopBackOff in Kubernetes? → 1230字符, 工具: Read, Grep
- **howto-002**: 如何配置 Kubernetes 资源限制？ → 603字符, 工具: Grep
- **concept-001**: What is the purpose of a ReplicaSet? → 313字符, 工具: Grep
- **concept-002**: Kubernetes 命名空间的作用是什么？ → 537字符, 工具: Grep
- **edge-002**: Kubernetes 中的 DaemonSet 是什么？ → 307字符, 工具: Grep

## 结论

通过率 53.3% → 100.0% (+46.7%), 改善 7 个, 退步 0 个。
