---
name: sync-from-raw
description: 从原始文档仓同步并转换文档到 Agent KB 仓。检测变更、转换格式、增强元数据、更新索引。当用户提到"同步文档"、"更新知识库"、"从原始仓同步" 时触发。
argument-hint: <原始仓路径> [--incremental|--full]
allowed-tools: Read, Bash, Glob, Write, Grep
---

# 从原始仓同步文档

实现双仓架构的核心 skill：从原始文档仓（SSOT Raw Repo）增量同步并转换文档到 Agent KB 仓。

## 核心理念

**双仓架构（Dual-Repo）**：
- **原始仓 (Raw Repo)**: 存储 PDF、HTML、DOCX 等原始文档，使用 Git LFS 管理大文件
- **Agent KB 仓 (KB Repo)**: 存储解析后的 Markdown + 索引，100% 纯文本，Claude Code 专用

**优势**：
- 轻量高效：Agent 只读取纯文本仓库
- 解耦计算：文档转换不阻塞原始文档提交
- 权限隔离：敏感信息可在转换时清洗
- 完美溯源：每个 MD 文件记录源文件和 commit

## 输入
- $0: 原始文档仓路径
- $1: 同步模式（可选）
  - `--incremental` - 增量同步（默认）
  - `--full` - 全量重建

## 执行流程

### 阶段 1: 检测变更

#### 1.1 读取同步元数据

```bash
# 检查是否存在同步元数据
if [ -f ".sync_metadata.json" ]; then
    last_sync_commit=$(jq -r '.source_commit' .sync_metadata.json)
else
    # 首次同步，全量处理
    last_sync_commit="HEAD"
    mode="full"
fi
```

#### 1.2 检测原始仓变更

```bash
cd "$raw_repo_path"

# 获取变更文件列表
if [ "$mode" = "incremental" ]; then
    # 增量：检测自上次同步以来的变更
    changed_files=$(git diff --name-status $last_sync_commit HEAD)
else
    # 全量：处理所有文档
    changed_files=$(find . -type f \( -name "*.pdf" -o -name "*.html" -o -name "*.docx" \))
fi

# 分类变更
added_files=$(echo "$changed_files" | grep "^A" | cut -f2)
modified_files=$(echo "$changed_files" | grep "^M" | cut -f2)
deleted_files=$(echo "$changed_files" | grep "^D" | cut -f2)
```

#### 1.3 过滤需要处理的文件

```bash
# 只处理支持的文档格式
supported_extensions=("pdf" "html" "docx" "pptx" "md")

for file in $changed_files; do
    ext="${file##*.}"
    if [[ " ${supported_extensions[@]} " =~ " ${ext} " ]]; then
        process_queue+=("$file")
    fi
done
```

### 阶段 2: 转换文档

#### 2.1 选择转换工具

```python
# 根据文件类型选择转换器
def select_converter(file_path):
    ext = file_path.split('.')[-1].lower()

    converters = {
        'pdf': ['docling', 'mineru', 'marker'],
        'html': ['pandoc', 'html2text'],
        'docx': ['pandoc', 'docling'],
        'pptx': ['pandoc'],
        'md': ['copy']  # Markdown 直接复制
    }

    # 检查可用的转换器
    for converter in converters.get(ext, []):
        if is_tool_available(converter):
            return converter

    return None
```

#### 2.2 执行转换

```bash
for file in "${process_queue[@]}"; do
    echo "转换: $file"

    # 确定输出路径（保持目录结构）
    relative_path="${file#$raw_repo_path/}"
    output_path="${kb_repo_path}/${relative_path%.*}.md"

    # 创建输出目录
    mkdir -p "$(dirname "$output_path")"

    # 根据文件类型转换
    case "${file##*.}" in
        pdf)
            docling "$file" --output "$output_path"
            ;;
        html)
            pandoc -f html -t markdown "$file" -o "$output_path"
            ;;
        docx)
            pandoc "$file" -t markdown -o "$output_path"
            ;;
        md)
            cp "$file" "$output_path"
            ;;
    esac

    # 记录转换结果
    if [ $? -eq 0 ]; then
        converted_files+=("$output_path")
    else
        failed_files+=("$file")
    fi
done
```

### 阶段 3: AI 增强元数据

#### 3.1 提取文档信息

```python
# 使用 Claude Code 或本地小模型提取信息
def enhance_document(md_path, source_info):
    content = read_file(md_path)

    # 提取标题（从第一个 # 标题）
    title = extract_first_heading(content)

    # 生成摘要（使用 Claude 或本地模型）
    summary = generate_summary(content, max_length=200)

    # 提取关键词
    keywords = extract_keywords(content, top_k=5)

    # 推断分类
    category = infer_category(content, title)

    return {
        'title': title,
        'summary': summary,
        'keywords': keywords,
        'category': category
    }
```

#### 3.2 生成 Front-matter

```python
def generate_frontmatter(source_file, source_commit, enhanced_info):
    # 生成稳定的文档 ID
    doc_id = generate_doc_id(source_file)

    # 计算文档哈希
    doc_hash = calculate_file_hash(source_file)

    frontmatter = f"""---
id: "{doc_id}"
title: "{enhanced_info['title']}"
summary: "{enhanced_info['summary']}"
source_file: "{source_file}"
source_repo_commit: "{source_commit}"
source_repo_url: "{raw_repo_url}"
converted_at: "{datetime.now().isoformat()}"
converter: "{converter_name}"
doc_hash: "{doc_hash}"
confidence: medium
tags: {enhanced_info['keywords']}
category: "{enhanced_info['category']}"
created: "{datetime.now().date()}"
last_reviewed: "{datetime.now().date()}"
---

"""
    return frontmatter
```

#### 3.3 注入 Front-matter

```bash
for md_file in "${converted_files[@]}"; do
    # 读取原始内容
    content=$(cat "$md_file")

    # 生成 front-matter
    frontmatter=$(generate_frontmatter "$source_file" "$source_commit")

    # 合并并写回
    echo "$frontmatter" > "$md_file.tmp"
    echo "$content" >> "$md_file.tmp"
    mv "$md_file.tmp" "$md_file"
done
```

### 阶段 4: 更新索引

#### 4.1 更新分层索引

```bash
# 使用 /update-index skill 更新索引
/update-index "$kb_repo_path/docs"
```

#### 4.2 更新同步元数据

```python
def update_sync_metadata(converted_files, source_commit):
    metadata = load_sync_metadata()

    # 更新基本信息
    metadata['last_sync'] = datetime.now().isoformat()
    metadata['source_commit'] = source_commit

    # 记录本次同步历史
    sync_record = {
        'timestamp': datetime.now().isoformat(),
        'source_commit': source_commit,
        'files_added': [f for f in converted_files if is_new(f)],
        'files_modified': [f for f in converted_files if is_modified(f)],
        'files_deleted': deleted_files
    }
    metadata['sync_history'].append(sync_record)

    # 更新文件映射
    for md_file in converted_files:
        metadata['file_mapping'][md_file] = {
            'source_file': get_source_file(md_file),
            'source_commit': source_commit,
            'converted_at': datetime.now().isoformat(),
            'converter': converter_name,
            'doc_hash': calculate_file_hash(get_source_file(md_file))
        }

    save_sync_metadata(metadata)
```

### 阶段 5: Git 提交

#### 5.1 提交到 Agent KB 仓

```bash
cd "$kb_repo_path"

# 添加所有变更
git add docs/ index.json INDEX.md .sync_metadata.json

# 生成详细的 commit message
commit_msg="sync: 从原始仓同步文档 (${source_commit:0:7})

变更摘要:
- 新增: ${#added_files[@]} 个文档
- 修改: ${#modified_files[@]} 个文档
- 删除: ${#deleted_files[@]} 个文档

源仓库: $raw_repo_url
源提交: $source_commit

转换详情:
$(for file in "${converted_files[@]}"; do
    echo "  - $(basename "$file")"
done)"

git commit -m "$commit_msg"
```

#### 5.2 推送到远程（可选）

```bash
if [ "$auto_push" = "true" ]; then
    git push origin main
fi
```

## 自动化方案

### 方案 1: Git Hook（原始仓）

在原始仓的 `.git/hooks/post-commit` 或 `post-receive`：

```bash
#!/bin/bash
# .git/hooks/post-commit

# 触发同步到 Agent KB 仓
kb_repo_path="/path/to/agent-kb-repo"

cd "$kb_repo_path"
/sync-from-raw "$(pwd)/.." --incremental
```

### 方案 2: CI/CD 流水线

#### GitHub Actions 示例

```yaml
# .github/workflows/sync-to-kb.yml
name: Sync to Agent KB

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Raw Repo
        uses: actions/checkout@v3
        with:
          path: raw-repo

      - name: Checkout KB Repo
        uses: actions/checkout@v3
        with:
          repository: org/agent-kb-repo
          token: ${{ secrets.KB_REPO_TOKEN }}
          path: kb-repo

      - name: Install Dependencies
        run: |
          pip install docling html2text pandoc

      - name: Sync Documents
        run: |
          cd kb-repo
          /sync-from-raw ../raw-repo --incremental

      - name: Commit and Push
        run: |
          cd kb-repo
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git push
```

### 方案 3: 定时任务（Cron）

```bash
# crontab -e
# 每小时检查一次原始仓的变更
0 * * * * cd /path/to/kb-repo && /sync-from-raw /path/to/raw-repo --incremental
```

### 方案 4: Webhook 服务

```python
# webhook_server.py
from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/webhook/raw-repo', methods=['POST'])
def handle_raw_repo_push():
    payload = request.json

    # 验证 webhook 签名
    if not verify_signature(payload):
        return 'Unauthorized', 401

    # 触发同步
    result = subprocess.run([
        '/sync-from-raw',
        '/path/to/raw-repo',
        '--incremental'
    ], capture_output=True)

    return {'status': 'success', 'output': result.stdout}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## 处理删除的文档

```python
def handle_deleted_files(deleted_files):
    for source_file in deleted_files:
        # 找到对应的 MD 文件
        md_file = get_md_path(source_file)

        if os.path.exists(md_file):
            # 选项 1: 直接删除
            os.remove(md_file)

            # 选项 2: 标记为已删除（保留历史）
            mark_as_deleted(md_file)

            # 选项 3: 移动到归档目录
            archive_file(md_file)

        # 从索引中移除
        remove_from_index(md_file)

        # 更新同步元数据
        update_sync_metadata_for_deletion(source_file)
```

## 冲突处理

### 场景 1: 源文件被修改但 MD 也被手动编辑

```python
def handle_conflict(source_file, md_file):
    # 检测冲突
    source_hash = get_file_hash_from_metadata(md_file)
    current_hash = calculate_file_hash(source_file)

    if source_hash != current_hash:
        # 源文件已变更
        if is_md_manually_edited(md_file):
            # MD 也被手动编辑
            print(f"⚠️  冲突: {md_file}")
            print(f"   源文件已变更，但 MD 也被手动编辑")
            print(f"   选项:")
            print(f"   1. 保留手动编辑，跳过同步")
            print(f"   2. 覆盖为新转换的版本")
            print(f"   3. 创建新版本 (md_file.v2.md)")

            # 等待用户决策或使用默认策略
            return handle_user_choice()
```

### 场景 2: 同一源文件被多次转换

```python
def handle_duplicate_conversion(source_file):
    # 检查是否已存在转换记录
    existing_md = find_existing_md(source_file)

    if existing_md:
        # 比较源文件哈希
        if source_hash_changed(source_file):
            # 源文件已变更，重新转换
            return 'reconvert'
        else:
            # 源文件未变，跳过
            return 'skip'
```

## 性能优化

### 并行转换

```python
from concurrent.futures import ThreadPoolExecutor

def convert_documents_parallel(files, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(convert_document, file)
            for file in files
        ]

        results = [f.result() for f in futures]

    return results
```

### 增量 AI 增强

```python
# 只对新增或修改的文档进行 AI 增强
def should_enhance(md_file):
    metadata = get_file_metadata(md_file)

    # 如果已有摘要和关键词，跳过
    if metadata.get('summary') and metadata.get('keywords'):
        return False

    return True
```

## 监控和日志

### 生成同步报告

```markdown
# 同步报告

**时间**: 2025-02-13 14:30:00
**源仓库**: https://github.com/org/raw-docs
**源提交**: a1b2c3d4

## 变更统计
- 新增: 3 个文档
- 修改: 5 个文档
- 删除: 1 个文档

## 转换详情

### 成功 (7)
- ✅ network_guide.pdf → network_guide.md (docling, 2.3s)
- ✅ api_spec.html → api_spec.md (pandoc, 0.5s)
- ...

### 失败 (1)
- ❌ corrupted.pdf (错误: 文件损坏)

## 索引更新
- 更新了 index.json
- 更新了 INDEX.md
- 新增标签: [network, api]

## 下一步
- 检查失败的文档
- 审查 AI 生成的摘要
```

## 使用示例

```bash
# 首次全量同步
/sync-from-raw /path/to/raw-repo --full

# 增量同步（检测变更）
/sync-from-raw /path/to/raw-repo --incremental

# 查看同步状态
cat .sync_metadata.json | jq '.sync_history[-1]'
```

## 最佳实践

1. **定期全量重建** - 每周或每月执行一次全量同步，确保一致性
2. **监控转换质量** - 定期抽查转换后的 MD 文件
3. **版本对齐** - 在 Agent KB 仓的 commit message 中记录源仓的 commit hash
4. **备份策略** - 原始仓使用 Git LFS，Agent KB 仓纯文本易备份
5. **权限管理** - 原始仓可能有敏感信息，Agent KB 仓可以公开

## 故障恢复

### 同步中断

```bash
# 检查最后一次成功的同步
last_sync=$(jq -r '.last_sync' .sync_metadata.json)

# 从中断点继续
/sync-from-raw /path/to/raw-repo --since $last_sync
```

### 元数据损坏

```bash
# 重建同步元数据
rm .sync_metadata.json
/sync-from-raw /path/to/raw-repo --full --rebuild-metadata
```
