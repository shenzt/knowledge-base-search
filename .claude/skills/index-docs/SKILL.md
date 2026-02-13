---
name: index-docs
description: 管理知识库索引。当用户提到"更新索引"、"重建索引"、"索引状态" 时触发。
argument-hint: [--incremental | --full | --status]
disable-model-invocation: true
allowed-tools: Bash
---

# 索引管理

根据用户指令执行对应的索引操作。

## 可用操作

### 查看索引状态
```bash
python scripts/index.py --status
```
或调用 MCP 工具 `index_status`。

### 增量更新（仅变更文件）
```bash
python scripts/index.py --incremental
```
通过 `git diff` 获取变更文件列表，仅重新索引变更文件。

### 全量重建
```bash
python scripts/index.py --full
```
删除现有 collection 后从头构建。耗时较长，仅在必要时使用。

## 注意事项
- 索引操作必须由用户明确请求，不要自动执行
- 全量重建前确认用户意图
- 操作完成后报告：处理文件数、新增/更新/删除 chunk 数、耗时
