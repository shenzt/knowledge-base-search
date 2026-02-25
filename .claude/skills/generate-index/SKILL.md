---
name: generate-index
description: 探索知识库文档仓库，生成 INDEX.md 导航指南。为搜索 Agent 提供目录结构、版本策略、主题路由等元信息。
argument-hint: <kb-repo-path> (e.g., kb/kb-redis-docs)
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Write
---

# 生成知识库 INDEX.md

你是知识库分析 Agent。目标：探索一个文档仓库，理解其结构和内容，生成 INDEX.md 供搜索 Agent 使用。

INDEX.md 之于知识库，就像 CLAUDE.md 之于代码仓库 — 告诉 Agent 如何导航和使用这个仓库。

## 输入

用户提供 KB 仓库路径，如 `kb/kb-redis-docs`。

## 探索步骤

### Step 1: 发现目录结构

```
Glob(pattern="<kb-path>/docs/**/_index.md")
Glob(pattern="<kb-path>/docs/**/", path="<kb-path>")
```

目标：了解顶层目录划分和文件数量分布。

### Step 2: 理解各区域内容

读取顶层和二级 `_index.md` 文件，了解每个区域的主题：

```
Read(file_path="<kb-path>/docs/<area>/_index.md")
```

重点关注：
- `title` / `description` / `linkTitle` 字段
- 目录的层级关系和命名规律

### Step 3: 检测版本目录

寻找同级目录中的版本号模式（如 `7.4/`, `7.8/`, `7.22/`, `0.12.1/`）：

```
Glob(pattern="<kb-path>/docs/**/[0-9]*.[0-9]*/")
```

对于每个版本化区域：
- 确定哪些目录有版本变体
- 识别哪个是 "latest"（通常是非版本化的同名目录）
- 读取版本目录的 `_index.md` 确认版本号

### Step 4: 统计文件分布

```
Glob(pattern="<kb-path>/docs/**/*.md")
```

按顶层目录统计 .md 文件数量，识别大区域和小区域。

### Step 5: 抽样阅读代表性文档

每个主要区域读 1-2 个文档，了解：
- 文档格式（frontmatter 字段、内容结构）
- 内容深度（概述 vs 详细指南 vs API 参考）
- 是否有交叉引用（relref 链接）

## INDEX.md 输出格式

写入 `<kb-path>/INDEX.md`，内容结构：

```markdown
# <KB Name> — Search Index Guide

> 本文件由 /generate-index 生成，供搜索 Agent 导航使用。

## Overview

- 来源: <source repo>
- 文档数: <count> 个 .md 文件
- 主要语言: <language>
- 最后生成: <date>

## Directory Map

| 路径 | 主题 | 文档数 | 说明 |
|------|------|--------|------|
| develop/data-types/ | 数据类型 | 42 | Strings, Lists, Sets, ... |
| ... | ... | ... | ... |

## Version Strategy

### 版本化区域

| 区域 | 版本目录 | Latest |
|------|---------|--------|
| operate/rs/ | 7.4/, 7.8/, 7.22/ | operate/rs/ (非版本化) |
| ... | ... | ... |

### 搜索规则

- **默认**: 只搜索非版本化（latest）目录
- **用户指定版本**: 搜索对应版本目录（如 "Redis Enterprise 7.4" → operate/rs/7.4/）
- **版本比较**: 同时搜索多个版本目录

## Topic Routing

| 问题类型 | 搜索路径 | 说明 |
|---------|---------|------|
| 数据类型 | develop/data-types/ | Strings, JSON, Streams... |
| 客户端库 | develop/clients/ | Python, Java, Node.js... |
| ... | ... | ... |

## Excluded Paths (Indexing)

以下路径建议在向量索引时跳过（旧版本，与 latest 重复）：

- operate/rs/7.4/
- operate/rs/7.8/
- ...

## Answer Rules

- 引用文件路径和 section
- 如果回答来自版本化文档，注明版本
- 优先使用非版本化（latest）文档
- 文档未覆盖的内容，明确声明
```

## 写作原则

- 写给 AI 搜索 Agent，不是人类读者
- 简洁：控制在 3-5KB，Agent 每次搜索前读取
- 可操作：重点是 "问题类型 → 搜索哪个目录"
- 准确：目录名、文件数、版本号必须基于实际探索结果
- 不要猜测：只写你实际读到和确认的信息
