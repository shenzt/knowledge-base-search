# 双仓架构设计文档

**版本**: v1.0
**日期**: 2025-02-13
**状态**: 设计阶段

---

## 1. 架构概述

### 1.1 核心理念

采用**双仓架构（Dual-Repo）**实现读写分离：

```
┌─────────────────────────────────────────────────────────┐
│  原始文档仓 (SSOT Raw Repo)                              │
│  - 存储: PDF, HTML, DOCX 等原始文档                      │
│  - 管理: Git + Git LFS                                   │
│  - 用户: 人类编辑者                                       │
│  - 特点: 单一事实源，完整历史                             │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ 同步流水线
                  │ (Webhook / CI/CD / Cron)
                  ▼
┌─────────────────────────────────────────────────────────┐
│  Agent 知识库仓 (Agent KB Repo)                          │
│  - 存储: Markdown + JSON 索引                            │
│  - 管理: Git (纯文本)                                     │
│  - 用户: Claude Code Agent                               │
│  - 特点: 轻量、高效、可检索                               │
└─────────────────────────────────────────────────────────┘
```

### 1.2 为什么不用单仓？

| 维度 | 单仓 (Mono-repo) | 双仓 (Dual-repo) |
|------|-----------------|------------------|
| 仓库体积 | ❌ 膨胀（二进制文件） | ✅ 轻量（纯文本） |
| Agent 效率 | ❌ 被原始文件干扰 | ✅ 100% 相关内容 |
| 转换性能 | ❌ Git Hook 阻塞提交 | ✅ 异步处理 |
| 权限隔离 | ❌ 无法分离 | ✅ 可独立控制 |
| 版本对齐 | ✅ 强一致性 | ⚠️ 需要元数据管理 |

**结论**: 双仓架构在工程实践中更优，唯一需要解决的是版本溯源问题。

---

## 2. 仓库设计

### 2.1 原始文档仓 (Raw Repo)

**目的**: 作为 SSOT（Single Source of Truth），存储所有原始文档。

**目录结构**:
```
raw-docs/
├── .git/
├── .gitattributes          # Git LFS 配置
├── README.md
├── docs/
│   ├── architecture/
│   │   ├── system_design.pdf
│   │   └── network_guide.pdf
│   ├── api/
│   │   ├── rest_api.html
│   │   └── graphql_spec.md
│   ├── runbooks/
│   │   └── incident_response.docx
│   └── meetings/
│       └── 2025-02-13-planning.pdf
└── .github/
    └── workflows/
        └── trigger-sync.yml    # 触发同步到 KB 仓
```

**Git LFS 配置** (`.gitattributes`):
```
*.pdf filter=lfs diff=lfs merge=lfs -text
*.docx filter=lfs diff=lfs merge=lfs -text
*.pptx filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
```

**特点**:
- 人类友好：可以直接拖拽 PDF、Word 文件
- 完整历史：保留所有版本
- 大文件支持：使用 Git LFS 避免仓库膨胀

### 2.2 Agent 知识库仓 (KB Repo)

**目的**: 为 Claude Code Agent 提供纯文本、高效、可检索的知识库。

**目录结构**:
```
agent-kb/
├── .git/
├── README.md
├── docs/
│   ├── architecture/
│   │   ├── system_design.md       # 从 PDF 转换
│   │   └── network_guide.md
│   ├── api/
│   │   ├── rest_api.md            # 从 HTML 转换
│   │   └── graphql_spec.md        # 直接复制
│   ├── runbooks/
│   │   └── incident_response.md   # 从 DOCX 转换
│   └── meetings/
│       └── 2025-02-13-planning.md
├── index.json                      # 分层索引
├── INDEX.md                        # 人类可读索引
├── index-stats.md                  # 统计报告
├── .sync_metadata.json             # 同步元数据
└── .claude/
    └── rules/
        └── kb-context.md           # Agent 上下文规则
```

**特点**:
- 100% 纯文本：无二进制文件
- 轻量快速：克隆和检索极快
- Agent 友好：Claude Code 可直接使用 Grep/Glob
- 完整溯源：每个文件记录源文件和 commit

---

## 3. 同步机制

### 3.1 同步元数据 (`.sync_metadata.json`)

**作用**: 记录同步历史，实现版本溯源和增量更新。

**结构**:
```json
{
  "version": "1.0",
  "last_sync": "2025-02-13T14:30:00Z",
  "source_repo": "https://github.com/org/raw-docs.git",
  "source_commit": "a1b2c3d4e5f6",
  "sync_history": [
    {
      "timestamp": "2025-02-13T14:30:00Z",
      "source_commit": "a1b2c3d4e5f6",
      "files_added": 3,
      "files_modified": 5,
      "files_deleted": 1,
      "duration_seconds": 45.2,
      "status": "success"
    }
  ],
  "file_mapping": {
    "docs/architecture/system_design.md": {
      "source_file": "docs/architecture/system_design.pdf",
      "source_commit": "a1b2c3d4e5f6",
      "source_repo": "https://github.com/org/raw-docs",
      "converted_at": "2025-02-13T14:30:00Z",
      "converter": "docling",
      "converter_version": "1.2.0",
      "doc_hash": "sha256:abc123...",
      "file_size_bytes": 245678
    }
  },
  "statistics": {
    "total_documents": 156,
    "by_format": {
      "pdf": 45,
      "html": 32,
      "docx": 28,
      "md": 51
    },
    "by_converter": {
      "docling": 45,
      "pandoc": 60,
      "copy": 51
    }
  }
}
```

### 3.2 文档 Front-matter

**每个转换后的 MD 文件头部**:

```yaml
---
# 文档标识
id: "system-design-2025"
title: "系统架构设计文档"

# 溯源信息
source_file: "docs/architecture/system_design.pdf"
source_repo: "https://github.com/org/raw-docs"
source_commit: "a1b2c3d4e5f6"
source_url: "https://github.com/org/raw-docs/blob/a1b2c3d4/docs/architecture/system_design.pdf"

# 转换信息
converted_at: "2025-02-13T14:30:00Z"
converter: "docling"
converter_version: "1.2.0"
doc_hash: "sha256:abc123..."

# AI 增强信息
summary: "本文档描述了系统的整体架构，包括微服务设计、数据流和部署策略。"
keywords: [architecture, microservices, design, deployment]
category: "architecture"

# 质量元数据
confidence: high
owner: "@architecture-team"
created: 2025-01-15
last_reviewed: 2025-02-13
---

# 系统架构设计文档

[AI 生成的摘要]
本文档描述了...

## 目录
...
```

### 3.3 同步流程

```
┌─────────────────────────────────────────────────────────┐
│ 1. 触发 (Trigger)                                        │
│    - Git Hook (post-commit)                             │
│    - Webhook (GitHub/GitLab)                            │
│    - CI/CD (GitHub Actions)                             │
│    - Cron (定时任务)                                     │
└─────────────────┬───────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 2. 检测变更 (Detect Changes)                            │
│    - 读取 .sync_metadata.json                           │
│    - git diff $last_commit HEAD                         │
│    - 分类: 新增/修改/删除                                │
└─────────────────┬───────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 3. 转换文档 (Convert Documents)                         │
│    - PDF → Markdown (docling/mineru)                    │
│    - HTML → Markdown (pandoc/html2text)                 │
│    - DOCX → Markdown (pandoc)                           │
│    - 并行处理，提升效率                                  │
└─────────────────┬───────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 4. AI 增强 (AI Enhancement)                             │
│    - 提取标题                                            │
│    - 生成摘要 (Claude/本地模型)                          │
│    - 提取关键词                                          │
│    - 推断分类                                            │
└─────────────────┬───────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 5. 注入元数据 (Inject Metadata)                         │
│    - 生成 front-matter                                  │
│    - 记录溯源信息                                        │
│    - 计算文档哈希                                        │
└─────────────────┬───────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 6. 更新索引 (Update Index)                              │
│    - 调用 /update-index                                 │
│    - 更新 index.json                                    │
│    - 更新 INDEX.md                                      │
└─────────────────┬───────────────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────────────┐
│ 7. Git 提交 (Git Commit)                                │
│    - git add docs/ index.json .sync_metadata.json       │
│    - git commit -m "sync: ..."                          │
│    - git push (可选)                                     │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 自动化方案

### 4.1 方案对比

| 方案 | 触发方式 | 延迟 | 复杂度 | 推荐场景 |
|------|---------|------|--------|---------|
| Git Hook | 本地 commit | 实时 | 低 | 个人使用 |
| Webhook | HTTP 回调 | 秒级 | 中 | 团队协作 |
| CI/CD | Push 触发 | 分钟级 | 中 | 企业级 |
| Cron | 定时轮询 | 小时级 | 低 | 低频更新 |

### 4.2 推荐方案：GitHub Actions

**优势**:
- 无需额外服务器
- 与 GitHub 深度集成
- 支持并行和缓存
- 免费额度充足

**配置示例** (`.github/workflows/sync-to-kb.yml`):

```yaml
name: Sync to Agent KB

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'

jobs:
  sync:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout Raw Repo
        uses: actions/checkout@v3
        with:
          fetch-depth: 2  # 需要前一个 commit 用于 diff

      - name: Checkout KB Repo
        uses: actions/checkout@v3
        with:
          repository: org/agent-kb-repo
          token: ${{ secrets.KB_REPO_TOKEN }}
          path: kb-repo

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          cache: 'pip'

      - name: Install Dependencies
        run: |
          pip install docling html2text pandoc-python
          sudo apt-get install -y pandoc

      - name: Sync Documents
        run: |
          cd kb-repo
          python ../scripts/sync_from_raw.py \
            --raw-repo .. \
            --mode incremental

      - name: Commit and Push
        run: |
          cd kb-repo
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add .
          git diff --staged --quiet || git commit -m "sync: from raw repo (${{ github.sha }})"
          git push
```

---

## 5. 版本溯源

### 5.1 从 MD 追溯到源文件

```bash
# 读取 MD 文件的 front-matter
source_file=$(yq '.source_file' docs/architecture/system_design.md)
source_commit=$(yq '.source_commit' docs/architecture/system_design.md)
source_repo=$(yq '.source_repo' docs/architecture/system_design.md)

# 构建源文件 URL
source_url="${source_repo}/blob/${source_commit}/${source_file}"

echo "源文件: $source_url"
```

### 5.2 从源文件查找对应的 MD

```bash
# 在 .sync_metadata.json 中查找
md_file=$(jq -r \
  --arg src "docs/architecture/system_design.pdf" \
  '.file_mapping | to_entries[] | select(.value.source_file == $src) | .key' \
  .sync_metadata.json)

echo "对应的 MD: $md_file"
```

### 5.3 检测源文件是否变更

```bash
# 计算当前源文件的哈希
current_hash=$(sha256sum "$source_file" | cut -d' ' -f1)

# 读取记录的哈希
recorded_hash=$(jq -r \
  --arg md "$md_file" \
  '.file_mapping[$md].doc_hash' \
  .sync_metadata.json | cut -d: -f2)

if [ "$current_hash" != "$recorded_hash" ]; then
    echo "⚠️  源文件已变更，需要重新同步"
fi
```

---

## 6. 冲突处理

### 6.1 场景：源文件变更 + MD 被手动编辑

**检测**:
```python
def detect_conflict(md_file, source_file):
    # 检查源文件是否变更
    source_changed = check_source_hash(source_file)

    # 检查 MD 是否被手动编辑
    md_manually_edited = check_md_manual_edit(md_file)

    if source_changed and md_manually_edited:
        return 'conflict'
```

**处理策略**:

1. **保守策略**（默认）：保留手动编辑，跳过同步
   ```bash
   echo "⚠️  冲突: $md_file 被手动编辑，跳过同步"
   echo "   如需重新同步，请先备份手动编辑的内容"
   ```

2. **覆盖策略**：用新转换的版本覆盖
   ```bash
   echo "⚠️  覆盖 $md_file 为新转换的版本"
   convert_and_overwrite "$source_file" "$md_file"
   ```

3. **版本策略**：创建新版本
   ```bash
   echo "⚠️  创建新版本: ${md_file%.md}.v2.md"
   convert_to_new_version "$source_file" "${md_file%.md}.v2.md"
   ```

### 6.2 场景：删除的源文件

**处理策略**:

1. **软删除**（推荐）：标记为已删除，保留内容
   ```yaml
   ---
   id: "system-design-2025"
   title: "系统架构设计文档"
   status: deleted
   deleted_at: "2025-02-13T14:30:00Z"
   deleted_reason: "源文件已从原始仓删除"
   ---
   ```

2. **硬删除**：直接删除 MD 文件
   ```bash
   git rm "$md_file"
   ```

3. **归档**：移动到归档目录
   ```bash
   mkdir -p archive/
   git mv "$md_file" "archive/$(basename $md_file)"
   ```

---

## 7. 性能优化

### 7.1 并行转换

```python
from concurrent.futures import ThreadPoolExecutor

def convert_documents_parallel(files, max_workers=4):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(convert_document, f): f
            for f in files
        }

        results = []
        for future in futures:
            try:
                result = future.result(timeout=300)
                results.append(result)
            except Exception as e:
                print(f"转换失败: {futures[future]}, 错误: {e}")

    return results
```

### 7.2 缓存机制

```python
# 缓存转换结果，避免重复转换
def should_reconvert(source_file, md_file):
    # 检查源文件哈希
    current_hash = calculate_hash(source_file)
    cached_hash = get_cached_hash(md_file)

    if current_hash == cached_hash:
        return False  # 源文件未变，跳过转换

    return True
```

### 7.3 增量 AI 增强

```python
# 只对新文档或缺少元数据的文档进行 AI 增强
def should_enhance(md_file):
    frontmatter = read_frontmatter(md_file)

    # 如果已有摘要和关键词，跳过
    if frontmatter.get('summary') and frontmatter.get('keywords'):
        return False

    return True
```

---

## 8. 监控和告警

### 8.1 同步报告

每次同步后生成报告：

```markdown
# 同步报告

**时间**: 2025-02-13 14:30:00
**源仓库**: https://github.com/org/raw-docs
**源提交**: a1b2c3d4e5f6
**耗时**: 45.2 秒

## 变更统计
- ✅ 新增: 3 个文档
- 📝 修改: 5 个文档
- ❌ 删除: 1 个文档

## 转换详情

### 成功 (8/9)
| 文件 | 转换器 | 耗时 | 状态 |
|------|--------|------|------|
| system_design.pdf | docling | 12.3s | ✅ |
| api_spec.html | pandoc | 0.8s | ✅ |
| ...

### 失败 (1/9)
| 文件 | 错误 |
|------|------|
| corrupted.pdf | 文件损坏，无法解析 |

## 索引更新
- ✅ 更新了 index.json
- ✅ 更新了 INDEX.md
- ✅ 新增标签: [architecture, api]

## 下一步
- [ ] 检查失败的文档
- [ ] 审查 AI 生成的摘要
```

### 8.2 告警规则

```yaml
# 告警配置
alerts:
  - name: sync_failure
    condition: status == 'failed'
    action: send_email
    recipients: [team@example.com]

  - name: conversion_rate_low
    condition: success_rate < 0.9
    action: send_slack
    channel: '#kb-alerts'

  - name: sync_duration_long
    condition: duration > 300  # 5 分钟
    action: log_warning
```

---

## 9. 最佳实践

### 9.1 原始仓管理

1. **使用 Git LFS** - 避免仓库膨胀
2. **规范目录结构** - 便于自动化处理
3. **添加 README** - 说明文档分类和命名规范
4. **定期清理** - 归档或删除过期文档

### 9.2 Agent KB 仓管理

1. **保持纯文本** - 绝不提交二进制文件
2. **定期重建索引** - 每周执行一次全量索引
3. **监控仓库大小** - 超过 100MB 考虑拆分
4. **备份元数据** - `.sync_metadata.json` 很重要

### 9.3 同步策略

1. **增量为主** - 日常使用增量同步
2. **定期全量** - 每周或每月全量重建
3. **监控质量** - 定期抽查转换质量
4. **版本对齐** - 确保元数据准确

---

## 10. 未来扩展

### 10.1 多源支持

支持从多个原始仓同步：

```json
{
  "sources": [
    {
      "name": "main-docs",
      "repo": "https://github.com/org/raw-docs",
      "branch": "main",
      "path": "docs/"
    },
    {
      "name": "legacy-docs",
      "repo": "https://github.com/org/legacy-docs",
      "branch": "master",
      "path": "archive/"
    }
  ]
}
```

### 10.2 智能路由

根据文档类型自动选择最佳转换器：

```python
def select_best_converter(file_path, content_type):
    # 基于文件内容智能选择
    if is_scanned_pdf(file_path):
        return 'mineru'  # OCR 能力强
    elif is_complex_layout(file_path):
        return 'docling'  # 布局保留好
    else:
        return 'marker'  # 速度快
```

### 10.3 质量评分

对转换质量进行评分：

```python
def evaluate_conversion_quality(source_file, md_file):
    score = 0

    # 检查标题提取
    if has_valid_title(md_file):
        score += 20

    # 检查段落结构
    if has_good_structure(md_file):
        score += 30

    # 检查代码块
    if code_blocks_preserved(md_file):
        score += 20

    # 检查表格
    if tables_preserved(md_file):
        score += 30

    return score  # 0-100
```

---

## 11. 总结

双仓架构的核心价值：

✅ **轻量高效** - Agent KB 仓 100% 纯文本，极速检索
✅ **解耦计算** - 文档转换不阻塞原始文档提交
✅ **完整溯源** - 每个 MD 文件记录源文件和 commit
✅ **权限隔离** - 原始仓和 KB 仓可独立控制访问权限
✅ **易于扩展** - 支持多源、智能路由、质量评分等

通过 `/sync-from-raw` skill 和自动化流水线，实现了从原始文档到 Agent 友好知识库的无缝转换。
