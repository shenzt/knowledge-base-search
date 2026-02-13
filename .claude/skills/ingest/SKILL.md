---
name: ingest
description: 导入文档到知识库。支持 PDF、网页 URL、DOCX 等格式。当用户提到"导入文档"、"添加到知识库"、"抓取网页"、"解析 PDF" 时触发。
argument-hint: [文件路径或URL] [--converter docling|mineru|marker|firecrawl]
allowed-tools: Read, Bash, Glob
---

# 文档导入

## 输入
- $0: 文件路径（本地 PDF/DOCX/PPTX）或网页 URL
- --converter: 指定预处理工具（可选，默认自动选择）

## 自动选择预处理工具

| 输入类型 | 默认工具 | 备选 |
|---------|---------|------|
| 中文 PDF | MinerU (CLI) | Docling MCP |
| 英文/通用 PDF | Docling MCP | Marker (高精度表格/公式) |
| DOCX/PPTX/XLSX | Docling MCP | — |
| 网页 URL | Firecrawl MCP | Crawl4AI MCP |

## 执行流程

1. 判断输入类型（文件扩展名或 URL 格式）
2. 将原始文件复制到 `raw/` 目录
3. 调用对应的预处理工具转换为 Markdown
4. 为输出的 Markdown 补充 front-matter：
   - 生成 `id`（8 位短 hash）
   - 填入 title（从文档标题提取）
   - 设置 confidence: medium（新导入默认）
   - 设置 created 和 last_reviewed 为今天
5. 保存到 `docs/` 对应子目录
6. 调用 knowledge-base MCP 的 `index_file` 建立索引
7. 将转换日志写入 `docs/.ingest_logs/`
8. 执行 `git add` + `git commit`

## 输出格式

```json
{
  "raw_artifact_path": "raw/xxx.pdf",
  "converter_used": "mineru",
  "converter_version": "1.3.0",
  "markdown_path": "docs/api/xxx.md",
  "doc_id": "e8f4b2c1",
  "doc_hash": "sha256:...",
  "index_points": 12,
  "warnings": []
}
```

## 注意事项
- 导入前确认目标子目录（runbook/adr/api/postmortem/meeting-notes）
- 如果 OCR 置信度低或表格解析异常，在 warnings 中标注
- 导入完成后提示用户检查 Markdown 质量并补充 front-matter 中的 owner 和 tags
