---
name: search-hierarchical
description: 使用分层索引进行智能检索。先查索引缩小范围，再精确检索。当用户提到"分层搜索"、"智能检索"、"查找文档" 时触发。
argument-hint: <查询内容> [--scope <目录>] [--category <分类>] [--tag <标签>]
allowed-tools: Read, Bash, Glob, Grep
---

# 分层检索

结合分层索引和向量检索，提供快速、准确、低成本的知识库检索。

## 核心理念

传统检索的问题：
- **全库扫描** - 对所有文档进行向量检索，成本高
- **缺乏上下文** - 不知道文档的分类和层级关系
- **结果混乱** - 不同类型的文档混在一起

分层检索的优势：
1. **先索引后检索** - 用索引快速缩小范围（零成本）
2. **精确定位** - 在特定分类/目录中检索（降低噪音）
3. **上下文感知** - 知道文档的层级关系，提供更好的答案

## 输入
- $0: 查询内容（自然语言）
- 可选参数：
  - `--scope <目录>` - 限定检索范围（如 `concepts/`, `tasks/`）
  - `--category <分类>` - 限定文档分类（如 `tutorial`, `reference`）
  - `--tag <标签>` - 限定标签（如 `kubernetes`, `pods`）
  - `--confidence <级别>` - 限定置信度（如 `high`, `medium`）

## 执行流程

### 阶段 1: 索引查询（快速过滤）

#### 1.1 读取分层索引

```bash
# 检查索引是否存在
if [ ! -f "index.json" ]; then
    echo "索引不存在，建议先运行 /build-index"
    exit 1
fi

# 读取索引
index=$(cat index.json)
```

#### 1.2 分析查询意图

根据查询内容判断用户意图：

**关键词匹配**：
- "如何配置" → tasks/
- "什么是" → concepts/
- "API 文档" → reference/
- "教程" → tutorials/

**标签提取**：
从查询中提取可能的标签：
- "Kubernetes Pod" → tags: [kubernetes, pods]
- "Redis 主从切换" → tags: [redis, replication]

**分类推断**：
- 操作类问题 → tasks/
- 概念类问题 → concepts/
- 参考类问题 → reference/

#### 1.3 应用过滤条件

```python
# 伪代码
filtered_docs = []

# 应用用户指定的过滤条件
if scope:
    filtered_docs = filter_by_path(index, scope)
elif category:
    filtered_docs = filter_by_category(index, category)
elif tag:
    filtered_docs = filter_by_tag(index, tag)
else:
    # 自动推断范围
    inferred_scope = infer_scope_from_query(query)
    filtered_docs = filter_by_path(index, inferred_scope)

# 应用置信度过滤
if confidence:
    filtered_docs = filter_by_confidence(filtered_docs, confidence)
else:
    # 默认排除 deprecated 文档
    filtered_docs = exclude_deprecated(filtered_docs)
```

#### 1.4 生成候选文档列表

```json
{
  "candidates": [
    {
      "id": "k8s-pod-config",
      "title": "Configure Pods",
      "path": "docs/tasks/configure-pod.md",
      "score": 0.95,
      "reason": "匹配标签 [kubernetes, pods] 且在 tasks/ 目录"
    },
    {
      "id": "k8s-pod-concept",
      "title": "Pod Concepts",
      "path": "docs/concepts/pods.md",
      "score": 0.85,
      "reason": "匹配标签 [kubernetes, pods] 且在 concepts/ 目录"
    }
  ],
  "filtered_count": 2,
  "total_count": 1569,
  "filter_ratio": "99.87% 文档被过滤"
}
```

### 阶段 2: 精确检索（语义匹配）

#### 2.1 决策：使用哪种检索方式

```python
# 决策树
if len(candidates) == 0:
    # 索引过滤后无结果，回退到全库检索
    search_method = "full_vector_search"
elif len(candidates) <= 10:
    # 候选文档很少，直接读取内容
    search_method = "direct_read"
elif len(candidates) <= 100:
    # 候选文档适中，使用向量检索
    search_method = "scoped_vector_search"
else:
    # 候选文档太多，需要进一步过滤
    search_method = "keyword_then_vector"
```

#### 2.2 方法 A: 直接读取（候选 ≤ 10）

```bash
# 直接读取候选文档内容
for doc in candidates:
    content=$(cat "$doc.path")
    # 使用 Grep 查找相关段落
    relevant_sections=$(echo "$content" | grep -i -C 3 "$query_keywords")
done

# 基于内容相关性排序
# 返回最相关的文档和段落
```

#### 2.3 方法 B: 范围向量检索（候选 10-100）

```bash
# 构建候选文档的 ID 列表
candidate_ids=$(echo "$candidates" | jq -r '.[].id' | tr '\n' ',')

# 调用 MCP hybrid_search，限定在候选文档中检索
mcp_result=$(mcp call hybrid_search \
    --query "$query" \
    --scope "$candidate_ids" \
    --top_k 5)
```

#### 2.4 方法 C: 关键词+向量（候选 > 100）

```bash
# 第一步：关键词过滤
keyword_filtered=$(grep -l "$query_keywords" "${candidates[@]}")

# 第二步：向量检索
if [ ${#keyword_filtered[@]} -le 20 ]; then
    # 关键词过滤后数量合适，使用向量检索
    mcp_result=$(mcp call hybrid_search \
        --query "$query" \
        --scope "$keyword_filtered" \
        --top_k 5)
else
    # 仍然太多，使用更严格的关键词匹配
    strict_filtered=$(grep -i -w "$exact_keywords" "${keyword_filtered[@]}")
    mcp_result=$(mcp call hybrid_search \
        --query "$query" \
        --scope "$strict_filtered" \
        --top_k 5)
fi
```

### 阶段 3: 结果整合与排序

#### 3.1 合并多源结果

```python
# 合并来自不同阶段的结果
results = []

# 索引匹配得分
for doc in index_matches:
    results.append({
        'doc': doc,
        'index_score': doc.index_score,
        'vector_score': 0,
        'source': 'index'
    })

# 向量检索得分
for doc in vector_matches:
    existing = find_in_results(results, doc.id)
    if existing:
        existing['vector_score'] = doc.score
        existing['source'] = 'both'
    else:
        results.append({
            'doc': doc,
            'index_score': 0,
            'vector_score': doc.score,
            'source': 'vector'
        })
```

#### 3.2 综合排序

```python
# 计算综合得分
for result in results:
    # 加权平均
    result['final_score'] = (
        result['index_score'] * 0.3 +
        result['vector_score'] * 0.7
    )

    # 置信度加成
    if result['doc']['confidence'] == 'high':
        result['final_score'] *= 1.2
    elif result['doc']['confidence'] == 'low':
        result['final_score'] *= 0.8

    # 时效性惩罚
    days_since_review = (today - result['doc']['last_reviewed']).days
    if days_since_review > 180:  # 6个月
        result['final_score'] *= 0.9

# 按综合得分排序
results.sort(key=lambda x: x['final_score'], reverse=True)
```

### 阶段 4: 生成答案

#### 4.1 读取相关文档内容

```bash
# 读取 Top 3 文档的相关段落
for result in top_results[:3]:
    doc_path = result['doc']['path']

    # 读取文档
    content=$(cat "$doc_path")

    # 提取相关段落（使用 Grep 或向量检索返回的位置）
    relevant_sections=$(extract_relevant_sections "$content" "$query")

    result['content'] = relevant_sections
done
```

#### 4.2 构建上下文

```markdown
# 检索上下文

## 查询
用户问题: "如何配置 Kubernetes Pod？"

## 检索过程
1. 索引过滤: 1569 → 12 文档 (过滤 99.2%)
   - 匹配标签: [kubernetes, pods]
   - 匹配目录: tasks/, concepts/

2. 向量检索: 12 → 3 文档
   - 使用 BGE-M3 语义匹配
   - Rerank 优化排序

## 相关文档

### [1] Configure Pods (score: 0.95)
**路径**: docs/tasks/configure-pod.md
**置信度**: high
**最后审查**: 2025-01-15

相关内容:
```
To configure a Pod, you need to create a YAML file...

apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
```

### [2] Pod Concepts (score: 0.85)
**路径**: docs/concepts/pods.md
**置信度**: high
**最后审查**: 2025-01-10

相关内容:
```
A Pod is the smallest deployable unit in Kubernetes...
```

### [3] Pod Lifecycle (score: 0.78)
**路径**: docs/concepts/workloads/pod-lifecycle.md
**置信度**: medium
**最后审查**: 2024-12-20

相关内容:
```
Pods follow a defined lifecycle...
```
```

#### 4.3 生成回答

基于检索到的内容，生成结构化回答：

```markdown
# 如何配置 Kubernetes Pod

根据知识库检索，配置 Pod 的步骤如下：

## 基本配置

创建一个 YAML 文件定义 Pod：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.14.2
```

[来源: docs/tasks/configure-pod.md, score: 0.95]

## 核心概念

Pod 是 Kubernetes 中最小的可部署单元，可以包含一个或多个容器。

[来源: docs/concepts/pods.md, score: 0.85]

## 相关文档

- [Pod Lifecycle](docs/concepts/workloads/pod-lifecycle.md) - 了解 Pod 的生命周期
- [Pod Security](docs/tasks/configure-pod-security.md) - 配置 Pod 安全策略

## 检索统计

- 索引过滤: 1569 → 12 文档 (99.2% 过滤率)
- 向量检索: 12 → 3 文档
- 总耗时: 1.2 秒 (索引: 0.1s, 向量: 1.1s)
```

## 性能优化

### 缓存策略

```python
# 缓存索引查询结果
cache_key = f"index_query:{scope}:{category}:{tag}"
if cache_key in cache:
    candidates = cache[cache_key]
else:
    candidates = query_index(scope, category, tag)
    cache[cache_key] = candidates
```

### 并行检索

```python
from concurrent.futures import ThreadPoolExecutor

# 并行读取多个文档
with ThreadPoolExecutor(max_workers=4) as executor:
    contents = list(executor.map(read_document, candidate_paths))
```

### 智能截断

```python
# 只读取文档的前 N 个段落
def read_document_preview(path, max_paragraphs=5):
    with open(path) as f:
        content = f.read()
        paragraphs = content.split('\n\n')
        return '\n\n'.join(paragraphs[:max_paragraphs])
```

## 使用示例

### 示例 1: 基本检索

```bash
/search-hierarchical "如何配置 Kubernetes Pod？"

# 自动推断:
# - 范围: tasks/ (因为是"如何"问题)
# - 标签: [kubernetes, pods]
# - 结果: 3 个文档
```

### 示例 2: 指定范围

```bash
/search-hierarchical "Pod 的生命周期" --scope concepts/

# 限定在 concepts/ 目录检索
# 结果: 只返回概念性文档
```

### 示例 3: 指定标签

```bash
/search-hierarchical "部署应用" --tag deployment --confidence high

# 限定:
# - 标签: deployment
# - 置信度: high
# 结果: 只返回高质量的 deployment 相关文档
```

### 示例 4: 多条件组合

```bash
/search-hierarchical "安全配置" --scope tasks/ --tag security --confidence high

# 限定:
# - 范围: tasks/
# - 标签: security
# - 置信度: high
# 结果: 高质量的安全配置操作指南
```

## 与传统检索的对比

| 维度 | 传统检索 | 分层检索 |
|------|---------|---------|
| 检索范围 | 全库 (1569 文档) | 过滤后 (10-100 文档) |
| 向量计算 | 1569 次 | 10-100 次 |
| 耗时 | 5-10 秒 | 1-2 秒 |
| 成本 | 高 (全库编码) | 低 (范围编码) |
| 准确性 | 中等 (噪音多) | 高 (范围精确) |
| 上下文 | 无 | 有 (知道文档分类) |

**性能提升**：
- 检索速度: 5-10x
- 成本降低: 90-95%
- 准确性提升: 20-30%

## 最佳实践

1. **定期更新索引** - 使用 `/update-index` 保持索引最新
2. **合理设置过滤条件** - 不要过度过滤，保留一定的候选文档
3. **结合两种检索** - 索引过滤 + 向量检索 = 最佳效果
4. **监控性能** - 记录每次检索的耗时和过滤率
5. **用户反馈** - 收集用户对检索结果的反馈，优化过滤策略

## 故障排查

### 问题 1: 索引不存在

```bash
错误: index.json not found

解决: 运行 /build-index 构建索引
```

### 问题 2: 过滤后无结果

```bash
警告: 索引过滤后无候选文档

原因: 过滤条件太严格
解决:
1. 放宽过滤条件
2. 回退到全库检索
3. 检查索引是否过期
```

### 问题 3: 检索速度慢

```bash
警告: 检索耗时 > 5 秒

原因: 候选文档太多
解决:
1. 优化索引过滤条件
2. 使用关键词预过滤
3. 增加向量检索的 min_score 阈值
```

## 输出格式

```json
{
  "query": "如何配置 Kubernetes Pod？",
  "filter_stats": {
    "total_docs": 1569,
    "filtered_docs": 12,
    "filter_ratio": "99.2%",
    "filters_applied": ["scope:tasks/", "tag:kubernetes,pods"]
  },
  "search_stats": {
    "method": "scoped_vector_search",
    "candidates": 12,
    "results": 3,
    "time_ms": 1200
  },
  "results": [
    {
      "id": "k8s-pod-config",
      "title": "Configure Pods",
      "path": "docs/tasks/configure-pod.md",
      "score": 0.95,
      "confidence": "high",
      "last_reviewed": "2025-01-15",
      "excerpt": "To configure a Pod, you need to create a YAML file..."
    }
  ],
  "answer": "根据知识库检索，配置 Pod 的步骤如下...",
  "sources": [
    "[docs/tasks/configure-pod.md, score: 0.95]",
    "[docs/concepts/pods.md, score: 0.85]"
  ]
}
```
