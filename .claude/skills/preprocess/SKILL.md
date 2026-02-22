---
name: preprocess
description: 对知识库文档进行 LLM 预处理，生成元数据。当用户提到"预处理"、"preprocess"、"文档分析" 时触发。
argument-hint: [--dir <path>] [--file <path>] [--status <path>] [--force]
disable-model-invocation: true
allowed-tools: Bash, Read, Glob
---

# 文档预处理

在 chunking 前为每个文档生成 sidecar JSON 元数据，提升检索质量和 Agent 决策能力。

## 核心价值

- **Contextual Summary** → 注入 embedding，弥补 heading-based chunking 丢失的文档级上下文（Anthropic Contextual Retrieval）
- **Evidence Flags** → 正则检测（零 LLM 成本），Agent 快速判断 chunk 是否有命令/配置/代码
- **Gap Flags** → LLM + 规则融合，Agent 据此避免幻觉（不编造文档中没有的内容）

## 执行流程

### 1. 运行预处理

```bash
# 批量预处理（推荐 DeepSeek V3，1000 docs ≈ ¥1.5）
DOC_PROCESS_PROVIDER=openai DOC_PROCESS_MODEL=deepseek-chat \
DOC_PROCESS_BASE_URL=https://api.deepseek.com \
DOC_PROCESS_API_KEY=$DEEPSEEK_KEY \
.venv/bin/python scripts/doc_preprocess.py --dir <path>

# 单文件预处理
.venv/bin/python scripts/doc_preprocess.py --file <path>

# 强制重新处理（忽略缓存）
.venv/bin/python scripts/doc_preprocess.py --dir <path> --force
```

### 2. 预处理后重新索引（必须）

```bash
.venv/bin/python scripts/index.py --full <path>
```

index.py 自动读取 `.preprocess/*.json` sidecar：
- `contextual_summary` 拼接到 embedding 文本（title + section_path + text + DOC_SUMMARY: summary）
- `doc_type` / `quality_score` / `evidence_flags` / `gap_flags` / `key_concepts` 写入 Qdrant payload

### 3. 查看状态

```bash
.venv/bin/python scripts/doc_preprocess.py --status <path>
```

输出：文档数、已预处理数、类型分布、平均质量分。

## Sidecar JSON Schema

```json
{
  "schema_version": 1,
  "content_hash": "sha1:abc123...",
  "generated_at": "2025-02-18T12:00:00Z",
  "model": "deepseek-chat",
  "prompt_version": "doc_preprocess_v1",
  "llm_status": "ok",
  "contextual_summary": "Redis Transactions enable atomic command group execution via MULTI/EXEC...",
  "doc_type": "reference",
  "quality_score": 7,
  "key_concepts": ["MULTI", "EXEC", "WATCH", "optimistic locking"],
  "gap_flags": [],
  "evidence_flags": {
    "has_command": true,
    "has_config": false,
    "has_code_block": true,
    "has_steps": false
  }
}
```

存储位置：与 `.md` 同级的 `.preprocess/` 目录（dotdir，不污染 `ls`）。

## LLM Provider 配置

通过环境变量配置（或 `.env` 文件）：

| 变量 | 说明 | 示例 |
|------|------|------|
| `DOC_PROCESS_PROVIDER` | `openai` 或 `anthropic` | `openai` |
| `DOC_PROCESS_MODEL` | 模型名 | `deepseek-chat` / `glm-4.5-flash` |
| `DOC_PROCESS_BASE_URL` | API endpoint | `https://api.deepseek.com` |
| `DOC_PROCESS_API_KEY` | API key | `sk-xxx` |

成本参考：
| 模型 | 1000 docs 成本 | 说明 |
|------|---------------|------|
| DeepSeek V3 (deepseek-chat) | ≈ ¥1.5 | 推荐，质量好 |
| GLM-4.5-Flash | ¥0（免费） | 大批量首选 |
| Claude Sonnet | ≈ $7.5 | 质量最好但贵 |

## 约束

- 不修改原始文档，只生成 `.preprocess/*.json` sidecar
- 增量处理：基于 content hash，未变更的文档自动跳过
- LLM 失败时仍写 sidecar（evidence_flags 由正则计算，始终可用）
- 预处理后必须重新索引才能生效
- `.preprocess/` 和 `scripts/.preprocess_cache.json` 已在 `.gitignore` 中
