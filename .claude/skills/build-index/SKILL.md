---
name: build-index
description: 构建或增量更新知识库的分层目录索引。扫描文档结构，生成分类索引文件，提交到 Git。当用户提到"构建索引"、"生成目录"、"创建索引"、"更新索引"、"刷新索引"、"同步索引" 时触发。
argument-hint: <知识库根目录> [--format json|markdown|both] [--incremental] [--since <commit>]
allowed-tools: Read, Bash, Glob, Write, Grep
---

# 构建/更新分层索引

扫描知识库文档结构，生成或增量更新分层目录索引。

## 输入

- $0: 知识库根目录路径（如 `docs/`）
- 可选参数：
  - `--format json|markdown|both` — 输出格式（默认 both）
  - `--incremental` 或 `--since <commit>` — 增量更新模式

## 模式选择

### 全量构建（默认）

适用于初始化、大规模重构后。扫描全部文档，重建索引。

### 增量更新（`--incremental`）

适用于日常更新。检测 Git 变更，只更新受影响的目录分支。

```bash
# 检测变更
git diff --name-status ${since_commit:-HEAD~1} -- "$0/**/*.md"
```

变更类型处理：
- **新增** (`A`) — 添加到索引，更新标签索引和计数
- **修改** (`M`) — 更新索引条目的元数据
- **删除** (`D`) — 从索引移除，更新计数
- **重命名** (`R`) — 更新路径，必要时移动目录分支

如果 `index.json` 不存在或损坏，自动回退到全量构建。

## 执行流程

### 1. 扫描文档结构

使用 Glob 递归查找所有 Markdown 文件。

### 2. 提取元数据

对每个文档读取 front-matter：id, title, tags, category, confidence, last_reviewed。

### 3. 构建层级结构

根据目录路径构建树形结构。

### 4. 生成索引文件

#### JSON 格式 (`index.json`)

```json
{
  "generated": "2025-02-13T10:30:00Z",
  "total_docs": 1569,
  "structure": {
    "concepts": {
      "path": "docs/concepts",
      "count": 45,
      "documents": [{"id": "...", "title": "...", "path": "...", "tags": [...], "confidence": "high"}],
      "subdirs": {}
    }
  },
  "tags_index": {"kubernetes": ["k8s-pod-concept", "k8s-deploy-concept"]},
  "categories": {"concepts": 45, "tasks": 120}
}
```

#### Markdown 格式 (`INDEX.md`)

目录结构 + 标签分类 + 置信度分类 + 需要更新的文档列表。

### 5. 生成统计报告 (`index-stats.md`)

总体统计、分类统计、标签统计、质量指标（缺少 id、需要更新、已废弃）。

### 6. Git 提交

```bash
git add index.json INDEX.md index-stats.md
git commit -m "docs: 更新知识库索引 (全量/增量)"
```

## 注意事项

- 索引文件应提交到 Git
- 大型知识库（>1000 文档）建议定期全量重建
- 日常使用增量更新，每周或大重构后全量构建
- 索引和向量检索互补：索引做结构化过滤（零成本），向量做语义匹配
