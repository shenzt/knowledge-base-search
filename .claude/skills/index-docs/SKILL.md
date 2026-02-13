---
name: index-docs
description: 管理知识库索引。当用户提到"更新索引"、"重建索引"、"索引状态" 时触发。
argument-hint: [--incremental | --full | --status | --file <path>]
disable-model-invocation: true
allowed-tools: Bash
---

# 索引管理

## 可用操作

查看索引状态：
```bash
python scripts/index.py --status
```

增量更新（基于 git diff，仅处理变更文件）：
```bash
python scripts/index.py --incremental
```

索引单个文件（导入后立即索引）：
```bash
python scripts/index.py --file docs/runbook/xxx.md
```

全量重建（删除后重建，慎用）：
```bash
python scripts/index.py --full
```

## 注意事项
- 索引操作必须由用户明确请求，不要自动执行
- 全量重建前确认用户意图
- 操作完成后报告处理结果
