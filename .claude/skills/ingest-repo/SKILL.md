---
name: ingest-repo
description: 从 Git 仓库导入文档到知识库。Clone 整个 repo，提取 Markdown 文件，注入溯源 front-matter，建立向量索引。当用户提到"导入仓库"、"ingest repo"、"添加 Git 仓库"时触发。
argument-hint: <repo-url> [--target-dir <path>] [--md-root <subdir>] [--branch <branch>]
allowed-tools: Read, Write, Bash, Glob, Edit
---

# Git 仓库导入

将一个 Git 仓库中的 Markdown 文档导入知识库，建立向量索引，保留完整溯源信息。

## 参数

- `$REPO_URL`: Git 仓库 URL（必需）
- `--target-dir`: 输出目录，默认 `../kb-output/<repo-name>/`（外部独立 Git 目录）
- `--md-root`: 仓库中 Markdown 文件的根目录，默认 `.`（仓库根目录）
- `--branch`: 分支名，默认 `main`
- `--exclude`: 排除的文件 glob 模式，如 `_index.md,CHANGELOG.md`
- `--rebuild`: 强制 drop + 全量重建（默认行为）

## 执行流程

### 1. 参数解析与预检查

```
- 从 repo URL 提取 repo-name（如 https://github.com/redis/docs → redis-docs）
- 确认 target-dir 存在，不存在则创建并 git init
- 确认 Qdrant 运行中：curl -s http://localhost:6333/collections
```

### 2. Clone 或 Pull 仓库

```bash
# 首次 clone（shallow clone 节省空间）
git clone --depth 1 --branch <branch> <repo-url> /tmp/ingest-<repo-name>

# 如果已存在，pull 最新
cd /tmp/ingest-<repo-name> && git pull
```

记录 commit hash：
```bash
cd /tmp/ingest-<repo-name> && git rev-parse --short HEAD
```

### 3. 扫描与提取文件

```
- 用 Glob 扫描 /tmp/ingest-<repo-name>/<md-root>/**/*.md
- 排除 exclude 列表中的文件
- 统计文件数量，报告给用户
```

**格式路由（当前只实现 .md）：**
- `.md` → 直接复制 + 注入 front-matter
- `.pdf` → 跳过，日志提示 "PDF conversion not yet supported, skipping"
- `.docx` → 跳过，日志提示 "DOCX conversion not yet supported, skipping"
- `.html` → 跳过，日志提示 "HTML conversion not yet supported, skipping"

### 4. 注入 Front-matter 并写入 target-dir

对每个 .md 文件：

1. 用 Read 读取原始内容
2. 如果已有 front-matter，保留原有字段，补充溯源字段
3. 如果没有 front-matter，生成完整的 front-matter
4. 用 Write 写入 `<target-dir>/docs/<repo-name>/<relative-path>`

**Front-matter 模板：**

```yaml
---
id: "<8位稳定hash>"              # 基于 repo-name + relative-path 的 md5 前 8 位
title: "<从内容提取或用文件名>"
source_repo: "<repo-url>"
source_path: "<md-root>/<relative-path>"
source_commit: "<commit-hash>"
ingested_at: "<ISO8601 时间戳>"
confidence: medium
---
```

**id 生成规则：** `md5(f"{repo-name}/{relative-path}")[:8]`，确保跨机器稳定。

### 5. 生成 .repo_meta.json

在 `<target-dir>/docs/<repo-name>/` 下写入：

```json
{
  "repo_url": "<repo-url>",
  "branch": "<branch>",
  "last_commit": "<commit-hash>",
  "last_ingest": "<ISO8601>",
  "md_root": "<md-root>",
  "doc_count": <N>,
  "target_dir": "<target-dir>"
}
```

### 6. LLM 预处理（推荐）

导入完成后，对新文档运行 LLM 预处理，生成 sidecar 元数据：

```bash
# 需要配置 DOC_PROCESS_* 环境变量（见 /preprocess Skill）
.venv/bin/python scripts/doc_preprocess.py --dir <target-dir>/docs/<repo-name>/
```

预处理生成 `.preprocess/*.json` sidecar，包含 contextual_summary（注入 embedding 提升检索）、evidence_flags、gap_flags 等。如果未配置 LLM 环境变量，可跳过此步，索引仍可正常工作，但检索质量会略低。

### 7. Drop 旧索引 + 全量重建

```bash
# 删除该 repo 的旧 chunks（按 source_repo 过滤）
.venv/bin/python scripts/index.py --delete-by-repo "<repo-url>"

# 全量索引新文件（自动读取 sidecar 注入 embedding + metadata）
.venv/bin/python scripts/index.py --full <target-dir>/docs/<repo-name>/
```

### 8. Git Commit（在 target-dir 中）

```bash
cd <target-dir>
git add docs/<repo-name>/
git commit -m "ingest: <repo-name> @ <commit-hash> (<N> docs)"
```

### 9. 更新 CLAUDE.md 知识库描述（关键！）

**这一步必须执行。** Agent 根据 CLAUDE.md 的"知识库数据源"部分决定是否值得搜索某个主题。如果不更新，新导入的内容会被 Agent 跳过。

1. 用 Read 读取 `CLAUDE.md`
2. 找到 `## 知识库数据源` 部分
3. 在 Qdrant 索引列表中添加/更新该 repo 的描述：
   - repo 名称、文档数、chunk 数
   - 主要内容分类（从文件目录结构和 README 提取）
4. 更新总 chunk 数
5. 用 Edit 写回 `CLAUDE.md`

同时更新 `.claude/rules/testing-lessons.md` 中的"当前知识库实际内容"部分。

### 10. 生成 Repo 级 Skill（可选）

在当前项目的 `.claude/skills/repos/<repo-name>/SKILL.md` 生成检索 skill：

```markdown
---
name: search-<repo-name>
description: 搜索 <repo-name> 知识库
---
# <repo-name> 知识库检索

- 来源: <repo-url>
- 文档数: <N>
- 最后更新: <last_ingest>

搜索时使用 hybrid_search，scope 过滤 "docs/<repo-name>"
```

### 11. 输出摘要

```
✅ Ingest 完成
- 仓库: <repo-url> @ <commit-hash>
- 文件数: <N> 个 .md（跳过: X 个 .pdf, Y 个 .html）
- Chunks: <M> 个
- 输出目录: <target-dir>/docs/<repo-name>/
- 索引: knowledge-base collection
```

## 重要约束

- **每次 ingest 都是 drop + rebuild** — 初期仓库不大，全量重建保证一致性
- **不修改原始 repo** — 只读 clone，所有输出写到 target-dir
- **保留目录结构** — target-dir 中的文件路径和原始 repo 一致
- **front-matter 中的 id 必须稳定** — 基于 repo-name + relative-path，不依赖内容
- **清理临时文件** — ingest 完成后删除 /tmp/ingest-<repo-name>/

## 格式扩展（未来）

当前只处理 .md 文件。未来扩展：
- `.pdf` → MinerU (`magic-pdf`) 转换，可能需要 Subagent 做智能清洗
- `.docx` → Pandoc 或 Docling 转换
- `.html` → Pandoc + html2text
- 图片 OCR → 待定

扩展时在步骤 3 的格式路由中添加对应分支即可。
