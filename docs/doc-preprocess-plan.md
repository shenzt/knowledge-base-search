# LLM 文档预处理管线实现计划

## Context

当前 Agentic RAG 系统 100/100 gate + 4.27/5 Judge faithfulness。但存在两个问题：
1. **检索质量天花板**：embedding 只用 `title + text`，chunk 丢失了文档级上下文（Anthropic Contextual Retrieval 论文指出的问题）
2. **Agent 无法预判 chunk 质量**：必须 Read 完整文档才能判断 chunk 是否有具体命令/配置，浪费 turn 预算
3. **12 个低质量 redis-ops case**：文档本身缺具体命令/配置，Agent 不知道这一点就会用训练知识补充 → 幻觉

方案：在 chunking 前加一步 LLM 预处理，生成 sidecar JSON 元数据。核心收益：
- Contextual Summary 注入 embedding → 提升检索召回
- Evidence/Gap Flags → Agent 快速判断 chunk 充分性，避免幻觉
- 成本极低：GLM-4.5-Flash 免费，1000 docs = ¥0

## 决策记录（基于 ChatGPT/Gemini/Codex 三方反馈）

| 特性 | 决策 | 理由 |
|------|------|------|
| Contextual Summary | ✅ P0 | 三方一致推荐，Anthropic 论文验证，最高 ROI |
| Evidence Flags | ✅ P0 | 正则实现零成本，Agent 直接可用 |
| Gap Flags | ✅ P0 | 解决 redis-ops 幻觉问题的关键 |
| Quality Score | ✅ P1 | 软信号，Agent 参考用 |
| Doc Type | ✅ P1 | 辅助 Agent 选择回答风格 |
| Key Concepts | ✅ P1 | 未来可用于 faceted search |
| Hypothetical Questions | ❌ 跳过 | ChatGPT 明确反对，embedding 空间污染风险 |
| Cross-doc Linking | ❌ 跳过 | 复杂度高，当前规模不需要 |
| RAPTOR-lite | ❌ 延后 | 有价值但独立于预处理，未来单独做 |

## 实现方案：1 个新文件 + 3 处改动 + 1 个新 Skill

### 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/doc_preprocess.py` | 新建 | 批量 LLM 预处理 + evidence_flags 正则 |
| `scripts/index.py` | 修改 | 读取 sidecar JSON，注入 embedding + metadata |
| `scripts/mcp_server.py` | 修改 | hybrid_search 输出增加预处理字段 |
| `.claude/skills/search/SKILL.md` | 修改 | 教 Agent 使用预处理元数据 |
| `.claude/skills/preprocess/SKILL.md` | 新建 | `/preprocess` Skill 入口 |
| `.gitignore` | 修改 | 添加 `.preprocess/` |

---

### 1. LLM 输出 Schema（每个 doc 一次 LLM 调用）

```json
{
  "contextual_summary": "Redis Transactions enable atomic command group execution via MULTI/EXEC with optimistic locking through WATCH for CAS patterns.",
  "doc_type": "reference",
  "quality_score": 7,
  "key_concepts": ["MULTI", "EXEC", "WATCH", "optimistic locking"],
  "gap_flags": []
}
```

- `contextual_summary`: 1 句话（≤50 词），描述文档核心内容。注入 embedding 提升检索。
- `doc_type`: enum `tutorial | reference | guide | troubleshooting | overview | example`
- `quality_score`: 0-10，基于 actionability + specificity + structure
- `key_concepts`: 3-5 个关键术语
- `gap_flags`: `missing_command | missing_config | missing_example | incomplete_steps` 的子集，空数组=无缺陷

**evidence_flags 由 Python 正则计算，不走 LLM**：
```json
{
  "has_command": true,
  "has_config": false,
  "has_code_block": true,
  "has_steps": false
}
```

### 2. Sidecar 存储

```
docs/runbook/redis-failover.md
docs/runbook/.preprocess/redis-failover.json   ← sidecar

../my-agent-kb/docs/redis-docs/develop/hashes.md
../my-agent-kb/docs/redis-docs/develop/.preprocess/hashes.json
```

- `.preprocess/` 目录与 `.md` 同级，dotdir 不污染 `ls`
- 可随时 `rm -rf .preprocess/` 重建
- `.gitignore` 添加 `.preprocess/`
- 全局缓存：`scripts/.preprocess_cache.json`（content hash → 跳过未变更文档）

### 3. `scripts/doc_preprocess.py`（新建）

**架构**：
```
CLI args (--dir/--file/--status/--force)
  → 发现 .md 文件
  → content hash 过滤（跳过未变更）
  → ThreadPoolExecutor(max_workers=8) 并发 LLM 调用
  → 正则计算 evidence_flags
  → 写 sidecar JSON
  → 更新缓存 + 输出统计
```

**关键实现细节**：

- 使用 `get_client("doc_process")` 获取 LLM 客户端
- 文档内容截断到 3000 字符（控制 token 成本）
- LLM 返回 JSON，解析失败 → 跳过该文档（不阻塞批处理）
- 类型校验 + fallback（doc_type 不合法 → "reference"，quality_score clamp 0-10）
- evidence_flags 正则模式：
  - `has_command`: `` ```bash/sh/shell `` 或 `$ command` 或 `` `redis-cli/kubectl/docker...` ``
  - `has_config`: `` ```yaml/toml/ini/json `` 或 `key: value` 模式
  - `has_code_block`: `` ```\w+ ``
  - `has_steps`: `## Step N` 或 `第N步` 或 `1. **`

**LLM Prompt**（单次调用，~200 input tokens + doc content）：

```
You are a technical documentation analyst. Analyze this document and return a JSON object.

<document>
Title: {title}
Source: {source_repo} / {source_path}
{content[:3000]}
</document>

Return ONLY a JSON object:
- "contextual_summary": One sentence (max 50 words), what this doc covers. Start with the subject.
- "doc_type": tutorial | reference | guide | troubleshooting | overview | example
- "quality_score": 0-10 (actionability + specificity + structure)
- "key_concepts": Array of 3-5 key terms
- "gap_flags": Array from: "missing_command", "missing_config", "missing_example", "incomplete_steps". Empty if none.
```

**成本估算**（1000 docs）：
| 模型 | 输入 | 输出 | 总成本 |
|------|------|------|--------|
| GLM-4.5-Flash | ~1.5M tokens | ~200K tokens | ¥0（免费） |
| DeepSeek-Chat | ~1.5M tokens | ~200K tokens | ~¥1.5 |
| Claude Sonnet | ~1.5M tokens | ~200K tokens | ~$7.5 |

### 4. `scripts/index.py` 改动（3 处）

**4a. 新增 `_load_sidecar()` 辅助函数**（在 `_clean_hugo_shortcodes` 之后）：

```python
def _load_sidecar(filepath: str) -> Optional[dict]:
    """加载文档的 sidecar 预处理 JSON。不存在则返回 None。"""
    p = Path(filepath)
    sidecar = p.parent / ".preprocess" / (p.stem + ".json")
    if sidecar.exists():
        try:
            with open(sidecar) as f:
                return json.load(f)
        except Exception:
            return None
    return None
```

**4b. `parse_file()` 注入 sidecar 元数据**（line 318-346）：

在 `content = _clean_hugo_shortcodes(post.content)` 之后加载 sidecar，在 metadata dict 中注入新字段：

```python
    sidecar = _load_sidecar(filepath)
    # ... 现有 chunking 逻辑不变 ...

    # 在 metadata dict 构建处追加：
    if sidecar:
        metadata["doc_type"] = sidecar.get("doc_type", "")
        metadata["quality_score"] = sidecar.get("quality_score", 0)
        metadata["evidence_flags"] = sidecar.get("evidence_flags", {})
        metadata["key_concepts"] = sidecar.get("key_concepts", [])
        metadata["gap_flags"] = sidecar.get("gap_flags", [])
        metadata["contextual_summary"] = sidecar.get("contextual_summary", "")
```

**4c. `index_chunks()` embedding 注入 contextual_summary**（line 219-223）：

```python
    # 原始：encode_texts.append(f"{title}\n{text}" if title else text)
    # 改为：
    encode_texts = []
    for c in chunks:
        title = c.get("metadata", {}).get("title", "")
        ctx_summary = c.get("metadata", {}).get("contextual_summary", "")
        text = c["text"]
        parts = [p for p in [ctx_summary, title, text] if p]
        encode_texts.append("\n".join(parts))
```

这是最高 ROI 的改动 — 每个 chunk 的 embedding 现在包含文档级 summary，弥补 heading-based chunking 丢失的上下文。

### 5. `scripts/mcp_server.py` 改动（1 处）

**hybrid_search 输出增加 4 个字段**（line 155-165 的 output dict）：

```python
    output.append({
        # ... 现有字段不变 ...
        # 预处理元数据（如果存在）
        "doc_type": point.payload.get("doc_type", ""),
        "quality_score": point.payload.get("quality_score", 0),
        "evidence_flags": point.payload.get("evidence_flags", {}),
        "gap_flags": point.payload.get("gap_flags", []),
    })
```

不暴露 `contextual_summary` 和 `key_concepts` — 前者已融入 embedding，后者暂无检索时用途。避免浪费 Agent context window。

### 6. `.claude/skills/search/SKILL.md` 改动

在 Step 2（评估 chunk 充分性）之后追加：

```markdown
### Step 2b: 使用预处理元数据（如果存在）

检索结果可能包含预处理字段，用于快速判断 chunk 质量：

| 字段 | 用途 |
|------|------|
| `evidence_flags` | `has_command/has_config/has_code_block/has_steps`。问题需要命令但 has_command=false → chunk 可能不充分 |
| `gap_flags` | `missing_command/missing_config/missing_example`。非空时主动告知用户缺失内容，不要编造 |
| `quality_score` | 0-10。< 5 建议寻找更多来源或 Read 完整文档 |
| `doc_type` | tutorial 类更可能有完整步骤，reference 类更可能有精确定义 |

使用规则：
- 这些是辅助信号，不是硬过滤
- gap_flags 非空 → 在回答中声明缺失内容，不用训练知识补充
- 多个结果 quality_score < 5 → 考虑 Read(path) 确认
```

### 7. `.claude/skills/preprocess/SKILL.md`（新建）

```markdown
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

- GLM-4.5-Flash（免费）推荐用于大批量
- .env 中配置 DOC_PROCESS_* 环境变量

## 约束

- 不修改原始文档，只生成 .preprocess/*.json sidecar
- 增量处理：内容未变的文档自动跳过
- 预处理后必须重新索引才能生效
```

---

## 实施顺序

1. `scripts/doc_preprocess.py` — 新建，可独立测试
2. `.claude/skills/preprocess/SKILL.md` — 新建 Skill 入口
3. `scripts/index.py` — 3 处改动（_load_sidecar + parse_file + index_chunks）
4. `scripts/mcp_server.py` — 1 处改动（输出增加 4 字段）
5. `.claude/skills/search/SKILL.md` — 追加 Step 2b
6. `.gitignore` — 添加 `.preprocess/` 和 `scripts/.preprocess_cache.json`
7. 验证

## 验证方式

```bash
# 1. 单文件预处理测试
DOC_PROCESS_PROVIDER=openai DOC_PROCESS_MODEL=glm-4.5-flash \
DOC_PROCESS_BASE_URL=https://open.bigmodel.cn/api/paas/v4 \
DOC_PROCESS_API_KEY=$ZHIPU_KEY \
.venv/bin/python scripts/doc_preprocess.py --file docs/runbook/redis-failover.md

# 2. 检查 sidecar 输出
cat docs/runbook/.preprocess/redis-failover.json

# 3. 重新索引（验证 sidecar 被读取）
.venv/bin/python scripts/index.py --file docs/runbook/redis-failover.md

# 4. 搜索验证（确认新字段出现在结果中）
# 通过 MCP hybrid_search 搜索，检查返回结果是否包含 doc_type/evidence_flags 等

# 5. 批量预处理 + 全量重建 + 评测
.venv/bin/python scripts/doc_preprocess.py --dir ../my-agent-kb/docs/redis-docs/
.venv/bin/python scripts/index.py --full ../my-agent-kb/docs/
USE_MCP=1 USE_JUDGE=1 .venv/bin/python tests/e2e/test_agentic_rag_sdk.py
```

对比基线（R9: gate 100/100, faithfulness 4.27/5）。预期：
- Gate 保持 100/100
- Faithfulness 4.27 → 4.4+（contextual summary 提升召回 + gap_flags 减少幻觉）
- redis-ops 低质量 case 减少（Agent 看到 gap_flags 后主动声明缺失而非编造）
