---
name: search
description: 从知识库检索文档并回答问题。支持混合检索、多步推理、跨语言查询。
argument-hint: <查询内容> [--scope runbook|adr|api|postmortem|meeting-notes] [--top-k 5] [--min-score 0.3]
allowed-tools: Read, Grep, Glob, Bash
---

# 知识库检索 (Agentic RAG)

## 输入
- $0: 用户查询 (支持中英文)
- --scope: 限定目录范围（可选）
- --top-k: 返回结果数 (默认 5)
- --min-score: 最低相关性得分 (默认 0.3)

## 检索策略（智能三层）

### 第一层：快速关键词检索（0 成本）

**适用场景**:
- 查询包含明确关键词、术语、错误码
- 查找特定文件或目录
- 精确匹配场景

**工具**:
1. `Grep` - 全文搜索关键词
2. `Glob` - 按文件名/路径模式匹配
3. `Read` - 读取命中文件的相关段落

**示例**:
- "JWT 认证如何实现？" → Grep "JWT"
- "查找 Redis 配置文档" → Glob "**/redis*.md"

### 第二层：混合向量检索（语义理解）

**适用场景**:
- 模糊查询、概念性问题
- 跨语言检索 (中文查询 → 英文文档)
- 需要语义理解的查询

**工具**: 调用 `knowledge-base` MCP Server

**步骤**:
1. 调用 `hybrid_search` (Dense + Sparse + RRF + Reranker)
2. 参数: `top_k=5-10`, `min_score=0.3`
3. 对命中结果用 `Read` 读取完整上下文
4. 如果需要更多上下文，读取相邻段落

**示例**:
- "What is a Pod in Kubernetes?" → 语义检索
- "Redis 管道技术如何工作？" → 跨语言检索

### 第三层：多文档推理（复杂问题）

**适用场景**:
- 需要对比多个文档
- 需要综合多个来源
- 需要多步推理

**步骤**:
1. 先用第二层检索相关文档
2. 识别需要的多个文档
3. 逐个读取完整内容
4. 综合分析并回答

**示例**:
- "Compare Kubernetes Deployment and StatefulSet"
- "Redis 性能优化的最佳实践"
- "如何排查 Pod CrashLoopBackOff 问题？"

## 智能选择逻辑

```
用户查询
    ↓
分析查询类型
    ↓
┌─────────────┬─────────────┬─────────────┐
│ 关键词明确   │ 语义/模糊    │ 复杂推理     │
│ → 第一层    │ → 第二层    │ → 第三层     │
└─────────────┴─────────────┴─────────────┘
    ↓
如果结果不足
    ↓
升级到下一层
```

## 回答要求

### 1. 必须带引用
```
[来源: docs/runbook/redis.md:42-58]
[来源: docs/api/auth.md:120]
```

### 2. 评估文档质量
- `confidence: deprecated` → ⚠️ 警告：此文档已废弃
- `last_reviewed` > 6个月 → ⚠️ 提示：可能过时
- `confidence: low` → ⚠️ 注意：此信息可信度较低

### 3. 结构化回答

**简单查询**:
```
直接回答 + 引用
```

**复杂查询**:
```
1. 概述
2. 详细说明 (分点)
3. 示例/代码
4. 相关文档链接
5. 引用来源
```

### 4. 处理特殊情况

**检索不到**:
```
❌ 未找到相关文档。

可能原因:
1. 知识库中没有相关内容
2. 查询关键词不匹配
3. 建议: 尝试其他关键词或查看文档索引
```

**多个相关结果**:
```
找到 3 个相关文档:

1. [最相关] docs/xxx.md - 关于...
2. [相关] docs/yyy.md - 关于...
3. [参考] docs/zzz.md - 关于...

详细回答基于文档 1...
```

## 优化技巧

### 1. 上下文扩展
如果检索到的 chunk 不完整，读取：
- 前一个 chunk (prev_chunk)
- 后一个 chunk (next_chunk)
- 整个章节 (section_path)

### 2. 相关性判断
- 得分 > 0.7: 高度相关
- 得分 0.5-0.7: 相关
- 得分 0.3-0.5: 可能相关
- 得分 < 0.3: 不相关 (过滤)

### 3. 跨语言处理
- 中文查询 → 英文文档: 使用混合检索
- 英文查询 → 中文文档: 使用混合检索
- 回答语言跟随查询语言

### 4. 多步推理
对于复杂问题:
1. 分解为子问题
2. 逐个检索
3. 综合答案
4. 标注每个部分的来源

## 示例

### 示例 1: 简单查询
```
查询: "What is a Pod in Kubernetes?"

步骤:
1. 识别为语义查询 → 第二层
2. 调用 hybrid_search("What is a Pod in Kubernetes?", top_k=3)
3. 读取 top-1 结果的完整上下文
4. 生成回答

回答:
A Pod is the smallest deployable unit in Kubernetes...

[来源: docs/concepts/workloads/pods/_index.md:15-30]
```

### 示例 2: 跨语言查询
```
查询: "Redis 管道技术如何工作？"

步骤:
1. 识别为中文语义查询 → 第二层
2. 调用 hybrid_search("Redis 管道技术如何工作？", top_k=5)
3. 可能匹配到英文文档 (pipelining.md)
4. 读取并用中文回答

回答:
Redis 管道 (Pipelining) 技术通过批量发送命令来提升性能...

[来源: docs/topics/pipelining.md:20-45]
```

### 示例 3: 复杂推理
```
查询: "Compare Kubernetes Deployment and StatefulSet"

步骤:
1. 识别为对比查询 → 第三层
2. 检索 "Deployment" 相关文档
3. 检索 "StatefulSet" 相关文档
4. 读取两个文档的完整内容
5. 对比分析

回答:
Kubernetes Deployment 和 StatefulSet 的主要区别:

1. 用途:
   - Deployment: 无状态应用 [来源: deployment.md:10]
   - StatefulSet: 有状态应用 [来源: statefulset.md:15]

2. Pod 标识:
   - Deployment: 随机名称
   - StatefulSet: 稳定的序号标识

3. 存储:
   - Deployment: 共享存储或临时存储
   - StatefulSet: 每个 Pod 独立的 PVC

[来源: docs/concepts/workloads/controllers/deployment.md]
[来源: docs/concepts/workloads/controllers/statefulset.md]
```

## 性能优化

### 1. 缓存策略
- 相同查询 → 复用 session
- 相关查询 → 复用检索结果

### 2. 批量处理
- 多个相关查询 → 一次检索
- 批量读取文件

### 3. 增量检索
- 先检索少量 (top_k=3)
- 不够再增加 (top_k=10)

## 注意事项

### ⚠️ 禁止行为
- ❌ 不要在没有检索的情况下凭记忆回答
- ❌ 不要一次性 Read 整个目录的所有文件
- ❌ 不要返回没有引用的答案
- ❌ 不要忽略文档的 confidence 和 last_reviewed

### ✅ 最佳实践
- ✅ 总是先检索再回答
- ✅ 提供完整的引用信息
- ✅ 评估文档质量并告知用户
- ✅ 对于复杂问题，分步骤说明推理过程
- ✅ 如果不确定，明确告知用户

## 调试

如果检索效果不好:
1. 检查查询关键词是否准确
2. 尝试调整 min_score (降低到 0.2)
3. 增加 top_k (提高到 10)
4. 尝试不同的查询表述
5. 检查文档是否已索引 (调用 index_status)
