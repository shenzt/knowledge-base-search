# Simple RAG vs Agentic RAG 对比报告

**时间**: 2026-02-14 00:37:16 | **方法**: Claude Agent SDK + Session 复用

## 📊 总体

| 指标 | Simple RAG | Agentic RAG | 变化 |
|------|-----------|-------------|------|
| 通过率 | 8/15 (53.3%) | 1/15 (6.7%) | **-46.7%** |
| 失败 | 7 | 14 | +7 |
| 平均耗时 | 46.3s | 1.6s | -44.8s |
| 费用 | ~$0.0255 | $0.0000 | - |

## 逐用例

| ID | 查询 | Simple | Agentic | |
|----|------|--------|---------|--|
| basic-001 | What is a Pod in Kubernetes? | ✅ | ❌ | 🔴 |
| basic-002 | Kubernetes Service 是什么？ | ✅ | ❌ | 🔴 |
| basic-003 | What are Init Containers? | ✅ | ❌ | 🔴 |
| cross-lang-001 | Redis 管道技术如何工作？ | ❌ | ❌ |  |
| cross-lang-002 | How does Redis pipelining improve p... | ✅ | ❌ | 🔴 |
| complex-001 | What's the difference between Deplo... | ❌ | ❌ |  |
| complex-002 | How to troubleshoot CrashLoopBackOf... | ❌ | ❌ |  |
| complex-003 | Kubernetes 中如何实现服务发现？ | ✅ | ❌ | 🔴 |
| howto-001 | How to create a Pod with multiple c... | ✅ | ❌ | 🔴 |
| howto-002 | 如何配置 Kubernetes 资源限制？ | ❌ | ❌ |  |
| concept-001 | What is the purpose of a ReplicaSet... | ❌ | ❌ |  |
| concept-002 | Kubernetes 命名空间的作用是什么？ | ❌ | ❌ |  |
| edge-001 | What is a sidecar container? | ✅ | ❌ | 🔴 |
| edge-002 | Kubernetes 中的 DaemonSet 是什么？ | ❌ | ❌ |  |
| notfound-001 | How to configure Kubernetes with bl... | ✅ | ✅ |  |

## 🔴 退步 (7)

- **basic-001**: What is a Pod in Kubernetes? → 答案过短 (21)
- **basic-002**: Kubernetes Service 是什么？ → 答案过短 (21)
- **basic-003**: What are Init Containers? → 答案过短 (21)
- **cross-lang-002**: How does Redis pipelining improve performance? → 答案过短 (21)
- **complex-003**: Kubernetes 中如何实现服务发现？ → 答案过短 (21)
- **howto-001**: How to create a Pod with multiple containers? → 答案过短 (21)
- **edge-001**: What is a sidecar container? → 答案过短 (21)

## 结论

通过率 53.3% → 6.7% (-46.7%), 改善 0 个, 退步 7 个。
