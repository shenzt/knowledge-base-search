---
name: convert-html
description: 批量转换 HTML 文档为 Markdown 格式并添加 front-matter。当用户提到"转换 HTML"、"HTML 转 Markdown"、"准备文档" 时触发。
argument-hint: <HTML目录路径> <输出目录路径>
disable-model-invocation: true
allowed-tools: Read, Bash, Glob, Write, Grep
---

# HTML 转 Markdown

将 HTML 文档批量转换为 Markdown 格式，添加标准 front-matter，准备用于知识库索引。

## 输入
- $0: HTML 文件所在目录路径
- $1: 输出 Markdown 目录路径（通常是 docs/ 下的子目录）

## 执行流程

### 1. 发现 HTML 文件

使用 Glob 查找所有 HTML 文件：
```bash
find "$0" -name "*.html" -type f
```

### 2. 批量转换

对每个 HTML 文件：

#### 2.1 使用 pandoc 转换
```bash
pandoc -f html -t markdown "$html_file" -o "$output_file"
```

如果没有 pandoc，尝试使用 Python html2text：
```bash
python3 -c "
import html2text
import sys
h = html2text.HTML2Text()
h.ignore_links = False
h.ignore_images = False
h.body_width = 0
with open('$html_file', 'r', encoding='utf-8') as f:
    print(h.handle(f.read()))
" > "$output_file"
```

#### 2.2 提取标题

从 HTML 中提取 `<title>` 或 `<h1>` 作为文档标题：
- 优先使用 `<title>` 标签内容
- 如果没有，使用第一个 `<h1>` 标签
- 都没有则使用文件名

#### 2.3 生成 front-matter

为每个转换后的 Markdown 文件添加：
```yaml
---
id: "<生成唯一ID，如 redis-cmd-get>"
title: "<从HTML提取的标题>"
source: "<原始HTML文件路径>"
converted: <转换日期 YYYY-MM-DD>
confidence: medium
tags: [<根据目录结构或文件名推断>]
---
```

ID 生成规则：
- 基于文件路径和名称生成稳定的 ID
- 例如：`cn/commands/get.html` → `redis-cmd-get`
- 使用小写字母、数字和连字符

### 3. 清理和优化

- 移除多余的空行（连续超过 2 个空行压缩为 2 个）
- 修复常见的转换问题（如表格格式）
- 保留代码块格式
- 确保中文字符正确编码

### 4. 组织输出

保持原有目录结构：
```
输入: kb-test-redis-cn/cn/commands/get.html
输出: kb-test-redis-cn/docs/commands/get.md
```

### 5. 生成转换报告

创建 `conversion-report.md` 包含：
- 转换文件总数
- 成功/失败统计
- 失败文件列表及原因
- 建议的后续操作

### 6. Git 提交

```bash
cd "$1/.."
git add docs/
git commit -m "docs: 批量转换 HTML 到 Markdown

- 转换了 X 个 HTML 文件
- 添加了标准 front-matter
- 保持原有目录结构"
```

## 工具选择

优先级：
1. **pandoc** - 最成熟的文档转换工具
2. **html2text** - Python 库，轻量级
3. **BeautifulSoup + 手动解析** - 最后备选

检查工具可用性：
```bash
which pandoc || echo "pandoc not found"
python3 -c "import html2text" 2>/dev/null || echo "html2text not installed"
```

## 注意事项

- 转换前先备份原始 HTML 文件
- 检查转换质量，特别是：
  - 代码块是否正确保留
  - 表格格式是否完整
  - 中文字符是否正确
  - 链接是否有效
- 大批量转换建议分批进行，避免一次性处理过多文件
- 转换后建议人工抽查几个文件确认质量

## 示例

```bash
# 转换 Redis 中文文档
/convert-html ../kb-test-redis-cn/cn ../kb-test-redis-cn/docs
```

转换后的文件示例：
```markdown
---
id: "redis-cmd-get"
title: "GET - Redis 命令"
source: "cn/commands/get.html"
converted: 2025-02-13
confidence: medium
tags: [redis, command, string]
---

# GET

获取指定 key 的值...
```
