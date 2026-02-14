# Agent 架构规范：Skill vs Python 脚本 vs Subagent

## 核心原则

**Skill 是第一入口。** 所有系统能力必须先封装为 Skill，确保 Agent 能调用。Python 脚本是 Skill 的底层载体，人类也可以直接使用。

## 三层分工

### Layer 1: Skill（SKILL.md）— 工作流编排

- 定义在 `.claude/skills/<name>/SKILL.md`
- 描述 **什么时候用、输入什么、执行步骤**
- Agent 用内置工具（Bash/Read/Write/Grep/Glob/Edit）执行
- 适用于：多步编排、文件操作、git 操作、调用 CLI 工具

**判断标准：** 如果任务的每一步都能用 Claude Code 内置工具完成 → Skill

### Layer 2: Python 脚本（scripts/）— 确定性重活

- Agent 做不了的事情才写 Python（向量编码、常驻模型等）
- 脚本同时是 CLI 工具，人类可以直接运行（如 `python scripts/index.py --status`）
- Skill 通过 `Bash: python scripts/xxx.py` 调用
- 关键：每个 Python 脚本的能力必须有对应的 Skill 封装，不能只有 CLI 没有 Skill

**判断标准：** 需要常驻模型、GPU 推理、向量计算、持久连接 → Python 脚本

### Layer 3: Subagent（.claude/agents/）— 隔离的智能任务

- 需要独立 context window 的复杂任务
- 产生大量输出但主对话不需要全部看到
- 需要不同的工具权限或模型
- 通过 `context: fork` 或 Agent SDK 调用

**判断标准：** 需要 LLM 做决策 + 隔离 context + 大量输出 → Subagent

## 禁止行为

- ❌ 不要把 Agent 能做的编排逻辑写成 Python 脚本
- ❌ 不要为了"自动化"而在 Python 里启动 Agent SDK（除非真的需要 LLM 决策）
- ❌ 不要写只有人类能用、Agent 调不了的工具 — 每个能力必须有 Skill 入口
- ❌ 不要在 Skill 里写复杂的条件逻辑 — Skill 描述意图，Agent 自主决策

## 示例

| 能力 | 实现方式 | 原因 |
|------|---------|------|
| `/search` | Skill | Agent 自主选择 Grep/hybrid_search/Read |
| `/ingest-repo` | Skill + 调 index.py | clone/复制/front-matter 注入用内置工具，向量编码调 Python |
| `hybrid_search` | MCP Tool (Python) | 需要常驻 BGE-M3 模型 |
| 向量编码 | Python (index.py) | 需要 BGE-M3 推理 |
| PDF → Markdown | 未来: Subagent | 需要 LLM 判断布局和清洗内容 |
| E2E 评测 | Agent SDK + Sonnet | 需要独立 session 隔离 |
