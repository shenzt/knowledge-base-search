# Agent 架构规范：Skill vs Python 脚本 vs Agent SDK

## 核心原则

**Skill 是第一入口。** 所有系统能力必须先封装为 Skill，确保 Agent 能调用。Python 脚本是 Skill 的底层载体，人类也可以直接使用。

## 三层分工

### Layer 1: Skill（SKILL.md）— 工作流编排

- 定义在 `.claude/skills/<name>/SKILL.md`
- 描述 **什么时候用、输入什么、执行步骤**
- Agent 用内置工具（Bash/Read/Write/Grep/Glob/Edit）执行
- 适用于：多步编排、文件操作、git 操作、调用 CLI 工具

**Skill 分两类：**
- **自动触发**（Claude 可自动加载）：`search`、`review`、`build-index` — 无副作用或副作用可控
- **手动触发**（`disable-model-invocation: true`）：`ingest`、`ingest-repo`、`preprocess`、`eval`、`convert-html`、`sync-from-raw`、`index-docs` — 有副作用（git commit、文件修改、LLM 调用、费用）

**判断标准：** 如果任务的每一步都能用 Claude Code 内置工具完成 → Skill

### Layer 2: Python 脚本（scripts/）— 确定性重活

- Agent 做不了的事情才写 Python（向量编码、常驻模型等）
- 脚本同时是 CLI 工具，人类可以直接运行（如 `python scripts/index.py --status`）
- Skill 通过 `Bash: python scripts/xxx.py` 调用
- 关键：每个 Python 脚本的能力必须有对应的 Skill 封装，不能只有 CLI 没有 Skill

**判断标准：** 需要常驻模型、GPU 推理、向量计算、持久连接 → Python 脚本

### Layer 3: Agent SDK（编程调用）— 独立 session 隔离

- 通过 `claude_agent_sdk.query()` 创建独立 session
- `ClaudeAgentOptions` 精确控制：`allowed_tools`、`disallowed_tools`、`mcp_servers`、`system_prompt`、`max_turns`
- 通过 `ANTHROPIC_BASE_URL` + claude-code-router 切换模型（Qwen/GLM-5/DeepSeek 等）
- 适用于：E2E 评测、Worker 委派、需要精确工具约束的自动化场景

**判断标准：** 需要独立 session + 精确工具控制 + 可能切换模型 → Agent SDK

### 关于 Subagent 和 context: fork

Claude Code 的 subagent（`.claude/agents/`）和 skill 的 `context: fork` 是**交互式 session 的功能**，不适用于 Agent SDK 编程调用场景：

- Agent SDK 的 `ClaudeAgentOptions` 提供了 `allowed_tools`、`mcp_servers`、`system_prompt` 等精确控制
- `context: fork` / subagent 的工具约束和 SDK 的控制机制是两套体系，混用会导致约束丢失
- claude-code-router 通过 `ANTHROPIC_BASE_URL` 代理 API 调用，subagent 的 `model` 配置可能与 router 冲突
- **结论：Agent SDK 调用场景不引入 subagent / context: fork**

## 禁止行为

- ❌ 不要把 Agent 能做的编排逻辑写成 Python 脚本
- ❌ 不要为了"自动化"而在 Python 里启动 Agent SDK（除非真的需要 LLM 决策）
- ❌ 不要写只有人类能用、Agent 调不了的工具 — 每个能力必须有 Skill 入口
- ❌ 不要在 Skill 里写复杂的条件逻辑 — Skill 描述意图，Agent 自主决策
- ❌ 不要在 Agent SDK session 中嵌套 subagent / context: fork — 会破坏工具约束

## 当前 Skill 清单

| Skill | 自动/手动 | 用途 |
|-------|----------|------|
| `/search` | 自动 | Agent 自主选择 Grep/hybrid_search/Read |
| `/review` | 自动 | 文档健康检查 |
| `/build-index` | 自动 | 构建/增量更新分层目录索引 |
| `/generate-index` | 手动 | 探索 KB 仓库，生成 INDEX.md 导航指南 |
| `/ingest` | 手动 | 导入单个文档（PDF/URL/DOCX） |
| `/ingest-repo` | 手动 | 导入 Git 仓库 |
| `/preprocess` | 手动 | LLM 文档预处理 |
| `/index-docs` | 手动 | 向量索引管理（调 index.py） |
| `/eval` | 手动 | RAG 评测 |
| `/convert-html` | 手动 | HTML → Markdown 批量转换 |
| `/sync-from-raw` | 手动 | 双仓同步 |

## 示例

| 能力 | 实现方式 | 原因 |
|------|---------|------|
| `/search` | Skill（自动触发） | Agent 自主选择 Grep/hybrid_search/Read |
| `/ingest-repo` | Skill（手动触发）+ 调 index.py | 有副作用（git commit），向量编码调 Python |
| `hybrid_search` | MCP Tool (Python) | 需要常驻 BGE-M3 模型 |
| 向量编码 | Python (index.py) | 需要 BGE-M3 推理 |
| E2E 评测 | Agent SDK + claude-code-router | 需要独立 session + 精确工具控制 + 模型切换 |
