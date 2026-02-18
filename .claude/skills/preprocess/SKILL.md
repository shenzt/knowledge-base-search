---
name: preprocess
description: 对知识库文档进行 LLM 预处理，生成元数据。当用户提到"预处理"、"preprocess"、"文档分析" 时触发。
argument-hint: [--dir <path>] [--file <path>] [--status <path>] [--force]
allowed-tools: Bash, Read, Glob
---

# 文档预处理

## 执行流程

1. 运行预处理：`.venv/bin/python scripts/doc_preprocess.py --dir <path>`
2. 预处理后重新索引：`.venv/bin/python scripts/index.py --full <path>`
3. 查看状态：`.venv/bin/python scripts/doc_preprocess.py --status <path>`

## 成本

- DeepSeek V3（deepseek-chat）：1000 docs ≈ ¥1.5
- GLM-4.5-Flash（免费）推荐用于大批量
- .env 中配置 DOC_PROCESS_* 环境变量

## 约束

- 不修改原始文档，只生成 .preprocess/*.json sidecar
- 增量处理：内容未变的文档自动跳过
- 预处理后必须重新索引才能生效
