---
name: update-index
description: 增量更新知识库索引。检测文档变更，只更新受影响的索引部分。当用户提到"更新索引"、"刷新索引"、"同步索引" 时触发。
argument-hint: <知识库根目录> [--since <commit>]
allowed-tools: Read, Bash, Glob, Write, Grep
---

# 增量更新索引

检测文档变更，增量更新分层索引，避免全量重建的开销。

## 核心理念

对于大型知识库，全量重建索引成本高：
- 需要读取所有文档的 front-matter
- 需要重新构建整个树形结构
- 对于 1000+ 文档的库，可能需要几分钟

增量更新只处理变更部分：
- 检测 Git 变更的文件
- 只更新受影响的目录分支
- 保持索引的实时性

## 输入
- $0: 知识库根目录路径（如 `docs/`）
- $1: 变更基准（可选）
  - `--since <commit>` - 从指定 commit 开始的变更
  - 默认：`HEAD~1`（上次提交以来的变更）

## 执行流程

### 1. 检测文档变更

使用 Git 检测变更的文件：
```bash
cd "$0/.."
git diff --name-only ${since_commit} -- "$0/**/*.md"
```

输出示例：
```
docs/concepts/pods.md          # 修改
docs/tasks/new-task.md         # 新增
docs/reference/old-api.md      # 删除
```

### 2. 分类变更类型

对每个变更文件：
- **新增** (`A`) - 添加到索引
- **修改** (`M`) - 更新索引条目
- **删除** (`D`) - 从索引移除
- **重命名** (`R`) - 更新路径

```bash
git diff --name-status ${since_commit} -- "$0/**/*.md"
```

### 3. 读取现有索引

```bash
# 检查索引文件是否存在
if [ -f "index.json" ]; then
    # 读取现有索引
    existing_index=$(cat index.json)
else
    # 如果不存在，执行全量构建
    /build-index "$0"
    exit 0
fi
```

### 4. 增量更新索引

#### 4.1 处理新增文件

```python
# 伪代码
for new_file in added_files:
    # 读取 front-matter
    metadata = extract_frontmatter(new_file)

    # 确定目录路径
    dir_path = os.path.dirname(new_file)

    # 添加到索引
    index['structure'][dir_path]['documents'].append({
        'id': metadata['id'],
        'title': metadata['title'],
        'path': new_file,
        'tags': metadata['tags'],
        'confidence': metadata['confidence']
    })

    # 更新计数
    index['structure'][dir_path]['count'] += 1
    index['total_docs'] += 1

    # 更新标签索引
    for tag in metadata['tags']:
        index['tags_index'][tag].append(metadata['id'])
```

#### 4.2 处理修改文件

```python
for modified_file in modified_files:
    # 读取新的 front-matter
    new_metadata = extract_frontmatter(modified_file)

    # 在索引中查找并更新
    doc_entry = find_in_index(index, modified_file)
    if doc_entry:
        # 更新元数据
        doc_entry['title'] = new_metadata['title']
        doc_entry['tags'] = new_metadata['tags']
        doc_entry['confidence'] = new_metadata['confidence']
        doc_entry['last_reviewed'] = new_metadata['last_reviewed']

        # 更新标签索引（移除旧标签，添加新标签）
        update_tags_index(index, doc_entry['id'], old_tags, new_tags)
```

#### 4.3 处理删除文件

```python
for deleted_file in deleted_files:
    # 从索引中移除
    doc_entry = find_in_index(index, deleted_file)
    if doc_entry:
        # 移除文档条目
        remove_from_index(index, deleted_file)

        # 更新计数
        dir_path = os.path.dirname(deleted_file)
        index['structure'][dir_path]['count'] -= 1
        index['total_docs'] -= 1

        # 从标签索引移除
        for tag in doc_entry['tags']:
            index['tags_index'][tag].remove(doc_entry['id'])
```

#### 4.4 处理重命名文件

```python
for renamed_file in renamed_files:
    old_path, new_path = renamed_file

    # 查找旧条目
    doc_entry = find_in_index(index, old_path)
    if doc_entry:
        # 更新路径
        doc_entry['path'] = new_path

        # 如果目录变了，移动到新目录
        old_dir = os.path.dirname(old_path)
        new_dir = os.path.dirname(new_path)
        if old_dir != new_dir:
            move_in_index(index, doc_entry, old_dir, new_dir)
```

### 5. 更新时间戳和统计

```json
{
  "generated": "2025-02-13T10:30:00Z",
  "last_updated": "2025-02-13T14:45:00Z",
  "total_docs": 1572,
  "changes_since_last_build": {
    "added": 3,
    "modified": 5,
    "deleted": 1,
    "renamed": 0
  }
}
```

### 6. 重新生成 Markdown 索引

基于更新后的 JSON 索引，重新生成 `INDEX.md`：
```bash
# 使用 /build-index 的 Markdown 生成逻辑
# 但基于已更新的 JSON 数据
```

### 7. 更新统计报告

重新计算 `index-stats.md` 中的统计数据：
- 总文档数
- 分类统计
- 标签统计
- 质量指标

### 8. Git 提交

```bash
git add index.json INDEX.md index-stats.md
git commit -m "docs: 增量更新索引

变更摘要:
- 新增: 3 个文档
- 修改: 5 个文档
- 删除: 1 个文档

受影响目录:
- concepts/
- tasks/"
```

## 性能优化

### 批量处理
对于大量变更，批量处理而不是逐个处理：
```python
# 一次性读取所有变更文件的 front-matter
changed_files = get_changed_files()
metadata_batch = read_frontmatter_batch(changed_files)

# 批量更新索引
update_index_batch(index, metadata_batch)
```

### 缓存机制
缓存最近读取的索引，避免重复读取：
```python
# 检查索引文件的修改时间
index_mtime = os.path.getmtime('index.json')
if cached_index and cached_mtime == index_mtime:
    index = cached_index
else:
    index = load_index('index.json')
    cache_index(index, index_mtime)
```

### 并行处理
对于大量文件，并行读取 front-matter：
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    metadata_list = list(executor.map(extract_frontmatter, changed_files))
```

## 触发时机

### 自动触发（推荐）
使用 Git hooks 在提交后自动更新索引：

`.git/hooks/post-commit`:
```bash
#!/bin/bash
# 检查是否有文档变更
if git diff --name-only HEAD~1 | grep -q "^docs/.*\.md$"; then
    echo "检测到文档变更，更新索引..."
    /update-index docs/
fi
```

### 手动触发
```bash
# 更新自上次提交以来的变更
/update-index docs/

# 更新自特定提交以来的变更
/update-index docs/ --since abc123

# 更新最近 5 次提交的变更
/update-index docs/ --since HEAD~5
```

### CI/CD 集成
在 CI 流程中自动更新索引：
```yaml
# .github/workflows/update-index.yml
name: Update Index
on:
  push:
    paths:
      - 'docs/**/*.md'
jobs:
  update-index:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Update index
        run: |
          /update-index docs/
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add index.json INDEX.md index-stats.md
          git commit -m "docs: auto-update index [skip ci]" || true
          git push
```

## 错误处理

### 索引文件损坏
```bash
if ! jq empty index.json 2>/dev/null; then
    echo "索引文件损坏，执行全量重建..."
    /build-index "$0"
    exit 0
fi
```

### 文档 front-matter 缺失
```python
try:
    metadata = extract_frontmatter(file)
except FrontmatterError:
    # 记录警告，跳过该文件
    warnings.append(f"文件 {file} 缺少有效的 front-matter")
    continue
```

### Git 变更检测失败
```bash
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "错误: 不在 Git 仓库中，无法检测变更"
    echo "建议: 使用 /build-index 进行全量构建"
    exit 1
fi
```

## 与全量构建的对比

| 维度 | 增量更新 | 全量构建 |
|------|---------|---------|
| 速度 | 快（秒级） | 慢（分钟级） |
| 适用场景 | 日常更新 | 初始化、大重构 |
| 准确性 | 依赖 Git 历史 | 100% 准确 |
| 资源消耗 | 低 | 高 |

**建议**：
- 日常使用增量更新
- 每周或大重构后执行一次全量构建
- 发现索引异常时执行全量构建

## 示例

```bash
# 场景 1: 提交后更新索引
git add docs/concepts/new-concept.md
git commit -m "docs: add new concept"
/update-index docs/

# 场景 2: 检查最近一周的变更
/update-index docs/ --since HEAD~20

# 场景 3: 从特定分支合并后更新
git merge feature-branch
/update-index docs/ --since main
```

## 输出示例

```
🔍 检测文档变更...
  基准: HEAD~1
  范围: docs/**/*.md

📊 变更统计:
  ✅ 新增: 3 个文档
  📝 修改: 5 个文档
  ❌ 删除: 1 个文档
  🔄 重命名: 0 个文档

🔧 更新索引...
  ├─ 读取现有索引: index.json
  ├─ 处理新增文档: docs/concepts/new-concept.md
  ├─ 处理修改文档: docs/tasks/configure-pod.md
  ├─ 处理删除文档: docs/reference/old-api.md
  └─ 更新统计数据

💾 保存索引文件...
  ├─ index.json (更新)
  ├─ INDEX.md (重新生成)
  └─ index-stats.md (更新)

✅ 索引更新完成！
  总文档数: 1572 (+2)
  耗时: 2.3 秒
```
