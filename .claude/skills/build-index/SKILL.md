---
name: build-index
description: 构建知识库的分层目录索引。扫描文档结构，生成分类索引文件，提交到 Git。当用户提到"构建索引"、"生成目录"、"创建索引" 时触发。
argument-hint: <知识库根目录> [--format json|markdown|both]
allowed-tools: Read, Bash, Glob, Write, Grep
---

# 构建分层索引

扫描知识库文档结构，生成分层目录索引，帮助 agent 快速定位文档分类和层级关系。

## 核心理念

对于大型知识库，分层索引可以：
1. **加速检索** - Agent 先查索引了解文档分类，再精确检索
2. **降低成本** - 避免全库扫描，减少 token 消耗
3. **提升准确性** - 明确文档层级关系，提供更好的上下文

## 输入
- $0: 知识库根目录路径（如 `docs/`）
- $1: 输出格式（可选）
  - `json` - 生成 JSON 格式索引
  - `markdown` - 生成 Markdown 格式索引
  - `both` - 同时生成两种格式（默认）

## 执行流程

### 1. 扫描文档结构

使用 Glob 递归查找所有 Markdown 文件：
```bash
find "$0" -name "*.md" -type f | sort
```

### 2. 提取元数据

对每个文档读取 front-matter：
- `id` - 文档唯一标识
- `title` - 文档标题
- `tags` - 标签
- `category` - 分类
- `confidence` - 置信度
- `last_reviewed` - 最后审查日期

### 3. 构建层级结构

根据目录路径构建树形结构：
```
docs/
├── concepts/
│   ├── pods.md
│   └── deployments.md
├── tasks/
│   └── configure-pod.md
└── reference/
    └── api.md
```

### 4. 生成索引文件

#### 4.1 JSON 格式 (`index.json`)

```json
{
  "generated": "2025-02-13T10:30:00Z",
  "total_docs": 1569,
  "structure": {
    "concepts": {
      "path": "docs/concepts",
      "count": 45,
      "documents": [
        {
          "id": "k8s-pod-concept",
          "title": "Pods",
          "path": "docs/concepts/pods.md",
          "tags": ["kubernetes", "pods", "workload"],
          "confidence": "high",
          "last_reviewed": "2025-01-15"
        }
      ],
      "subdirs": {
        "workloads": {
          "path": "docs/concepts/workloads",
          "count": 12,
          "documents": [...]
        }
      }
    },
    "tasks": {...},
    "reference": {...}
  },
  "tags_index": {
    "kubernetes": ["k8s-pod-concept", "k8s-deploy-concept"],
    "pods": ["k8s-pod-concept", "k8s-pod-config"]
  },
  "categories": {
    "concepts": 45,
    "tasks": 120,
    "tutorials": 30,
    "reference": 80
  }
}
```

#### 4.2 Markdown 格式 (`INDEX.md`)

```markdown
---
id: "kb-index"
title: "知识库索引"
generated: 2025-02-13
total_docs: 1569
---

# 知识库索引

> 自动生成于 2025-02-13 10:30:00
> 总文档数: 1569

## 目录结构

### concepts/ (45 篇)

核心概念文档

- [Pods](docs/concepts/pods.md) `#kubernetes #pods #workload` ⭐ high
- [Deployments](docs/concepts/deployments.md) `#kubernetes #deployment` ⭐ high

#### concepts/workloads/ (12 篇)

- [Pod Lifecycle](docs/concepts/workloads/pod-lifecycle.md)
- ...

### tasks/ (120 篇)

操作指南

- [Configure Pod](docs/tasks/configure-pod.md)
- ...

### reference/ (80 篇)

参考文档

- [API Reference](docs/reference/api.md)
- ...

## 按标签分类

### kubernetes (234 篇)
- concepts/pods.md
- concepts/deployments.md
- ...

### pods (45 篇)
- concepts/pods.md
- tasks/configure-pod.md
- ...

## 按置信度分类

### high (890 篇)
### medium (520 篇)
### low (100 篇)
### deprecated (59 篇)

## 需要更新的文档

以下文档超过 6 个月未审查：
- concepts/old-feature.md (最后审查: 2024-06-01)
- ...
```

### 5. 生成统计报告

创建 `index-stats.md`：
```markdown
# 索引统计报告

生成时间: 2025-02-13 10:30:00

## 总体统计
- 总文档数: 1569
- 总目录数: 45
- 平均深度: 3.2 层

## 分类统计
| 分类 | 文档数 | 占比 |
|------|--------|------|
| concepts | 45 | 2.9% |
| tasks | 120 | 7.6% |
| tutorials | 30 | 1.9% |
| reference | 80 | 5.1% |

## 标签统计
| 标签 | 使用次数 |
|------|----------|
| kubernetes | 234 |
| pods | 45 |
| deployment | 38 |

## 质量指标
- 有 front-matter: 1500 (95.6%)
- 缺少 id: 69 (4.4%)
- 需要更新 (>6个月): 120 (7.6%)
- 置信度 high: 890 (56.7%)
- 置信度 deprecated: 59 (3.8%)

## 建议
- 为 69 个文档添加 id 字段
- 审查 120 个过期文档
- 考虑归档或删除 59 个已废弃文档
```

### 6. 提交到 Git

```bash
cd "$0/.."
git add index.json INDEX.md index-stats.md
git commit -m "docs: 更新知识库索引

- 扫描了 X 个文档
- 生成了分层索引
- 统计了标签和分类"
```

## 索引更新策略

### 增量更新
- 检测 Git 变更：`git diff --name-only HEAD~1`
- 只更新变更的目录分支
- 保持索引文件的增量更新

### 完全重建
- 删除旧索引文件
- 重新扫描全部文档
- 适用于大规模重构后

## 使用场景

### 场景 1: Agent 快速定位
```
用户: "Kubernetes 中如何配置 Pod？"
Agent:
1. 读取 index.json
2. 发现 tasks/ 目录有相关文档
3. 在 tasks/ 中精确检索
4. 返回结果
```

### 场景 2: 文档健康检查
```
用户: "检查文档质量"
Agent:
1. 读取 index-stats.md
2. 发现 69 个文档缺少 id
3. 发现 120 个文档需要更新
4. 生成待办清单
```

### 场景 3: 分类浏览
```
用户: "有哪些关于 deployment 的文档？"
Agent:
1. 读取 index.json 的 tags_index
2. 找到所有带 deployment 标签的文档
3. 按分类展示
```

## 注意事项

- 索引文件应该提交到 Git，作为知识库的一部分
- 大型知识库（>1000 文档）建议定期重建索引
- 索引文件本身也可以被向量化索引，提供"元检索"能力
- 考虑为不同语言生成独立索引（如 `index-en.json`, `index-zh.json`）

## 示例

```bash
# 为 K8s 文档构建索引
/build-index /home/user/kb-test-k8s-en/content/en/docs --format both

# 为 Redis 文档构建索引
/build-index /home/user/kb-test-redis-cn/docs --format markdown
```

## 与向量检索的配合

分层索引和向量检索是互补的：

| 维度 | 分层索引 | 向量检索 |
|------|---------|---------|
| 速度 | 极快（直接读文件） | 较慢（需要模型推理） |
| 成本 | 零 | 需要 GPU/API |
| 适用 | 结构化查询、分类浏览 | 语义查询、模糊匹配 |
| 准确性 | 精确匹配 | 语义相似 |

**最佳实践**：
1. 先用分层索引缩小范围
2. 再用向量检索精确匹配
3. 结合两者的结果提供最佳答案
