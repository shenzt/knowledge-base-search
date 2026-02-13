# Agentic RAG 测试计划

## 测试目标

验证两个核心能力：
1. **Agentic Search** - `/search` skill 的智能检索能力
2. **Knowledge Base Preparation** - 文档导入、索引、管理的完整流程

## 1. Agentic Search 测试

### 测试方法
直接在 Claude Code 中使用 `/search` skill，观察：
- 是否正确选择检索策略（Grep vs MCP）
- 是否进行多步推理
- 是否自主扩展上下文
- 答案质量和引用准确性

### 测试用例（15-20个）

#### 基础检索（5个）
- `/search What is a Pod in Kubernetes?`
- `/search Kubernetes Service 是什么？`
- `/search What are Init Containers?`
- `/search 如何创建 Deployment？`
- `/search Explain ReplicaSet`

#### 跨语言检索（3个）
- `/search Redis 管道技术如何工作？` (中文查英文文档)
- `/search How does Redis pipelining work?` (英文查中文文档)
- `/search Kubernetes 中的 Service Discovery` (混合)

#### 复杂推理（5个）
- `/search Compare Deployment and StatefulSet` (对比)
- `/search How to troubleshoot CrashLoopBackOff?` (多步骤)
- `/search Best practices for Kubernetes resource limits` (综合)
- `/search 如何实现 Kubernetes 高可用？` (架构)
- `/search What's the difference between Service types?` (分类对比)

#### 边界情况（3个）
- `/search JWT authentication` (应该用 Grep 快速找到)
- `/search kubernetes blockchain integration` (不存在的内容)
- `/search 如何配置非常复杂的多层网络策略？` (需要多文档)

### 评估指标
- ✅ 策略选择正确性（是否选对 Grep/MCP/多文档）
- ✅ 答案准确性（是否回答了问题）
- ✅ 引用完整性（是否提供来源）
- ✅ 响应时间（是否合理）
- ✅ Token 效率（是否过度消耗）

## 2. Knowledge Base Preparation 测试

### 测试流程

#### 2.1 文档导入
```
/ingest raw/new-doc.pdf runbook
```
验证：
- PDF 转 Markdown 质量
- Front-matter 自动生成
- Git commit 正确性

#### 2.2 索引构建
```
/index-docs --file docs/runbook/new-doc.md
```
验证：
- 向量编码正确
- Qdrant 写入成功
- 索引状态更新

#### 2.3 文档审查
```
/review --scope runbook
```
验证：
- Front-matter 完整性检查
- 文档时效性评估
- 健康度评分

#### 2.4 端到端流程
```
1. /ingest raw/k8s-guide.pdf runbook
2. /index-docs --file docs/runbook/k8s-guide.md
3. /search How to use the new k8s feature?
4. /review --scope runbook
```

### 评估指标
- ✅ 导入成功率
- ✅ 索引准确性
- ✅ 检索可用性
- ✅ 文档质量评分

## 3. Baseline 对比测试

### Simple RAG vs Agentic RAG

使用相同的 10 个查询，对比：

| 指标 | Simple RAG | Agentic RAG | 提升 |
|------|-----------|-------------|------|
| 准确率 | ? | ? | ? |
| 平均响应时间 | ? | ? | ? |
| 平均 Token | ? | ? | ? |
| 用户满意度 | ? | ? | ? |

### 测试查询
1. What is a Pod?
2. Kubernetes Service 是什么？
3. Compare Deployment and StatefulSet
4. How to troubleshoot CrashLoopBackOff?
5. Redis 管道技术如何工作？
6. JWT authentication
7. Best practices for resource limits
8. 如何实现服务发现？
9. What are Init Containers?
10. Kubernetes 高可用架构

## 4. Embedding 服务优化

### 当前问题
- 每次调用初始化 2-3 分钟
- BGE-M3 模型加载慢
- 无法复用

### 解决方案：独立 MCP Server

#### 架构
```
┌─────────────────┐
│  Claude Code    │
│  (Agentic RAG)  │
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌──────────────────┐
│ Qdrant MCP      │  │ Embedding MCP    │
│ (hybrid_search) │  │ (encode/rerank)  │
└─────────────────┘  └──────────────────┘
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌──────────────────┐
│   Qdrant DB     │  │   BGE-M3 Model   │
│   (vectors)     │  │   (GPU/CPU)      │
└─────────────────┘  └──────────────────┘
```

#### 新的 Embedding MCP Server

**工具：**
1. `encode_query(text)` → {dense, sparse}
2. `encode_documents(texts[])` → [{dense, sparse}, ...]
3. `rerank(query, documents[])` → sorted results

**优势：**
- 模型常驻内存，无需重复加载
- 可以部署到远程 GPU 服务器
- 支持批量编码
- 独立扩展和优化

#### 实现步骤
1. 创建 `scripts/embedding_mcp_server.py`
2. 实现三个工具函数
3. 更新 `.mcp.json` 配置
4. 修改 `scripts/index.py` 调用 embedding MCP
5. 修改 `scripts/mcp_server.py` 调用 embedding MCP

## 5. 测试执行计划

### Phase 1: Agentic Search 验证（优先）
- [ ] 手动测试 15-20 个查询
- [ ] 记录策略选择和答案质量
- [ ] 识别问题和改进点

### Phase 2: Knowledge Base Preparation 验证
- [ ] 测试完整的导入-索引-检索流程
- [ ] 验证各个 skill 的功能
- [ ] 记录问题和改进点

### Phase 3: Baseline 对比
- [ ] 运行 Simple RAG baseline
- [ ] 对比 Agentic RAG 提升
- [ ] 生成对比报告

### Phase 4: Embedding 服务优化
- [ ] 实现独立 Embedding MCP Server
- [ ] 测试性能提升
- [ ] 部署到远程服务器（可选）

## 6. 成功标准

### Agentic Search
- ✅ 90%+ 查询选择正确的检索策略
- ✅ 85%+ 答案准确且完整
- ✅ 100% 提供引用来源
- ✅ 平均响应时间 < 10s

### Knowledge Base Preparation
- ✅ 文档导入成功率 > 95%
- ✅ 索引构建成功率 100%
- ✅ 文档审查准确率 > 90%

### Baseline 对比
- ✅ Agentic RAG 准确率提升 > 20%
- ✅ 用户满意度提升 > 30%
- ✅ Token 效率提升 > 15%

## 下一步行动

1. **立即执行**: 手动测试 Agentic Search（15-20 个查询）
2. **短期**: 实现独立 Embedding MCP Server
3. **中期**: 完善测试套件和自动化
4. **长期**: 持续优化和扩展知识库
