---
name: ingest
description: 导入文档到知识库。支持 PDF、网页、DOCX 等。当用户提到"导入"、"添加文档"、"解析 PDF"、"抓取网页" 时触发。
argument-hint: <文件路径或URL> [目标目录]
allowed-tools: Read, Bash, Glob, Write
---

# 文档导入

将外部文档转换为 Markdown 并纳入知识库版本管理。

## 输入
- $0: 文件路径或网页 URL
- $1: 目标子目录（可选，如 runbook/adr/api/postmortem/meeting-notes）

## 执行流程

### 1. 判断输入类型并转换

PDF 文件（优先用 MinerU，备选 Docling/Marker）：
```bash
# MinerU
magic-pdf -p "$0" -o /tmp/mineru_output -m auto
# 或 Docling
docling "$0" --output /tmp/docling_output
# 或 Marker
marker_single "$0" /tmp/marker_output
```

网页 URL（用 curl + 简单清洗，或已安装的工具）：
```bash
# 简单方式：curl + pandoc
curl -s "$0" | pandoc -f html -t markdown -o /tmp/output.md
# 或 Crawl4AI / Firecrawl CLI（如已安装）
```

DOCX/PPTX：
```bash
docling "$0" --output /tmp/docling_output
# 或 pandoc
pandoc "$0" -t markdown -o /tmp/output.md
```

### 2. 整理 Markdown

- 读取转换后的 Markdown
- 补充 front-matter（生成 id、填入 title、设置 confidence: medium）
- 保存到 `docs/<目标子目录>/`
- 将原始文件复制到 `raw/`

### 3. 版本管理

```bash
git add docs/ raw/
git commit -m "docs: 导入 <文件名>"
```

### 4. 建立索引

```bash
python scripts/index.py --file docs/<目标路径>
```

## 注意事项
- 转换工具按本地已安装的来选，不强制依赖特定工具
- 如果没有安装任何转换工具，提示用户安装建议
- 导入后提示用户检查 Markdown 质量、补充 owner 和 tags
