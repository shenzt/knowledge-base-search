# 双层 Claude 架构设计文档

**版本**: v1.0
**日期**: 2025-02-13

---

## 架构概述

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Meta-Agent (Claude Opus)                      │
│  - 角色: 架构师、代码生成器、系统优化器                    │
│  - 模型: claude-3-opus-20240229                          │
│  - 工具: Meta Skills (生成代码、运行评测、优化系统)        │
│  - 位置: 用户直接交互的 Claude Code CLI                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ 通过 Claude Agent SDK 调用
                     │ from claude_agent_sdk import query
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Worker-Agent (Claude Sonnet)                  │
│  - 角色: 执行者、文档处理器、RAG 引擎                      │
│  - 模型: claude-3-5-sonnet-20241022                      │
│  - 工具: KB Skills (转换、索引、检索)                      │
│  - 位置: 被 Layer 1 通过 SDK 调用的 agent                │
└─────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
knowledge-base-search/
├── meta_skills/              # Layer 1 专属 (Opus)
│   ├── generate-tool/        # 生成新的 KB Skill
│   ├── run-eval/             # 运行评测套件
│   ├── optimize-code/        # 优化 Layer 2 代码
│   └── analyze-logs/         # 分析 Sonnet 执行日志
│
├── kb_skills/                # Layer 2 专属 (Sonnet)
│   ├── convert-html/         # HTML → Markdown
│   ├── build-index/          # 构建分层索引
│   ├── index-docs/           # 向量索引
│   ├── search/               # 混合检索
│   └── sync-from-raw/        # 双仓同步
│
├── sonnet_worker.py          # Layer 2 执行引擎
├── opus_supervisor.py        # Layer 1 调度器 (可选)
└── eval/                     # 评测套件
    ├── test_cases.json       # 测试用例
    └── run_eval.py           # 评测脚本
```

---

## 核心组件

### 1. Sonnet Worker (Layer 2)

使用 Claude Agent SDK 创建专门的文档处理 agent：

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_rag_task(task: str):
    """调用 Sonnet agent 执行 RAG 任务"""
    async for message in query(
        prompt=task,
        options=ClaudeAgentOptions(
            model="claude-3-5-sonnet-20241022",
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            setting_sources=["project"],  # 使用 kb_skills/
            working_directory="./kb_skills"
        )
    ):
        if hasattr(message, "result"):
            return message.result
```

### 2. Opus Supervisor (Layer 1)

你当前交互的 Claude Code CLI，使用 Opus 模型：

```bash
# 在 .claude/config.json 中配置
{
  "model": "claude-3-opus-20240229",
  "skills_directory": "./meta_skills"
}
```

### 3. 闭环优化流程

```
1. Opus 生成 KB Skill 代码
   ↓
2. Opus 调用 Sonnet Worker 执行��务
   ↓
3. Sonnet 使用 KB Skills 处理文档
   ↓
4. Sonnet 返回执行日志和结果
   ↓
5. Opus 分析结果，发现问题
   ↓
6. Opus 修改 KB Skill 代码
   ↓
7. 回到步骤 2，重新测试
```

---

## 实现方案

### 方案 A: SDK 嵌套调用 (推荐)

**优势**:
- 完整的 agent 能力
- 自动工具执行
- 会话管理
- 日志追踪

**实现**:

```python
# sonnet_worker.py
from claude_agent_sdk import query, ClaudeAgentOptions

async def process_documents(task: str, skills_dir: str = "./kb_skills"):
    """Layer 2: Sonnet 处理文档"""
    session_id = None
    results = []

    async for message in query(
        prompt=task,
        options=ClaudeAgentOptions(
            model="claude-3-5-sonnet-20241022",
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            setting_sources=["project"],
            working_directory=skills_dir,
            mcp_servers={
                "knowledge-base": {
                    "command": "python",
                    "args": ["scripts/mcp_server.py"]
                }
            }
        )
    ):
        # 捕获 session_id
        if hasattr(message, "session_id"):
            session_id = message.session_id

        # 收集结果
        if hasattr(message, "result"):
            results.append(message.result)

        # 收集工具调用日志
        if hasattr(message, "tool_use"):
            results.append({
                "tool": message.tool_use.name,
                "input": message.tool_use.input
            })

    return {
        "session_id": session_id,
        "results": results
    }
```

### 方案 B: Subagent 模式

**优势**:
- 更清晰的层级关系
- 自动上下文传递
- 内置结果聚合

**实现**:

```python
# 在 Opus 层定义 Sonnet subagent
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

async def main():
    async for message in query(
        prompt="使用 doc-processor agent 处理 Redis 文档",
        options=ClaudeAgentOptions(
            model="claude-3-opus-20240229",
            allowed_tools=["Task", "Read", "Write"],
            agents={
                "doc-processor": AgentDefinition(
                    description="文档处理专家，负责 HTML 转换、索引构建、RAG 检索",
                    prompt="你是文档处理专家，使用 kb_skills 中的工具完成任务",
                    model="claude-3-5-sonnet-20241022",
                    tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                    working_directory="./kb_skills"
                )
            }
        )
    ):
        print(message)
```

---

## Meta Skills 设计

### /generate-tool

```markdown
# generate-tool

生成新的 KB Skill 或优化现有 Skill。

## 输入
- skill_name: Skill 名称
- description: 功能描述
- requirements: 需求列表

## 输出
- SKILL.md 文件
- 相关 Python 脚本 (如需要)

## 流程
1. 分析需求
2. 生成 SKILL.md
3. 生成实现代码
4. 创建测试用例
```

### /run-eval

```markdown
# run-eval

运行评测套件，测试 RAG 系统准确性。

## 输入
- test_suite: 测试套件路径 (默认 eval/test_cases.json)
- model: 使用的模型 (默认 sonnet)

## 输出
- 准确率报告
- 失败用例分析
- 优化建议

## 流程
1. 加载测试用例
2. 调用 Sonnet Worker 执行
3. 对比预期结果
4. 生成报告
```

### /optimize-code

```markdown
# optimize-code

分析 Sonnet 执行日志，优化 KB Skill 代码。

## 输入
- session_id: Sonnet 执行的 session ID
- target_skill: 要优化的 Skill

## 输出
- 问题分析
- 优化后的代码
- 性能对比

## 流程
1. 读取 session 日志
2. 分析工具调用
3. 识别瓶颈
4. 生成优化代码
5. 运行对比测试
```

---

## 使用示例

### 示例 1: 生成新 Skill

```bash
# Layer 1 (Opus)
/generate-tool --name semantic-chunking --description "基于标题的语义分块"
```

Opus 会：
1. 生成 `kb_skills/semantic-chunking/SKILL.md`
2. 生成实现代码
3. 调用 Sonnet 测试新 Skill
4. 根据测试结果优化

### 示例 2: 评测 + 优化闭环

```bash
# Layer 1 (Opus)
/run-eval --test-suite eval/rag_accuracy.json
```

Opus 会：
1. 调用 Sonnet Worker 运行所有测试用例
2. 收集 Sonnet 的执行日志
3. 分析失败用例
4. 识别问题 Skill (如 search-hierarchical)
5. 自动修改代码
6. 重新运行测试
7. 生成优化报告

### 示例 3: 文档处理任务

```python
# Layer 1 调用 Layer 2
from sonnet_worker import process_documents

result = await process_documents(
    task="将 kb-test-redis-cn 中的 HTML 转换为 Markdown，构建索引，然后回答：Redis 管道技术如何工作？"
)

print(result["results"])
```

---

## 配置文件

### .claude/config.json (Layer 1 - Opus)

```json
{
  "model": "claude-3-opus-20240229",
  "skills_directory": "./meta_skills",
  "allowed_tools": ["Read", "Write", "Edit", "Bash", "Task"],
  "agents": {
    "sonnet-worker": {
      "description": "文档处理和 RAG 执行引擎",
      "model": "claude-3-5-sonnet-20241022",
      "working_directory": "./kb_skills"
    }
  }
}
```

### kb_skills/.claude/config.json (Layer 2 - Sonnet)

```json
{
  "model": "claude-3-5-sonnet-20241022",
  "skills_directory": "./",
  "allowed_tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
  "mcp_servers": {
    "knowledge-base": {
      "command": "python",
      "args": ["../scripts/mcp_server.py"]
    }
  }
}
```

---

## 优势

### 1. 成本优化
- Opus 只做高级决策 (生成代码、分析结果)
- Sonnet 做大量执行 (处理 1569 个文件)
- 预计成本降低 70-80%

### 2. 速度提升
- Sonnet 更快 (处理文档)
- Opus 专注优化 (不被执行细节拖累)

### 3. 自我进化
- Opus 分析 Sonnet 日志
- 自动识别问题
- 自动优化代码
- 闭环迭代

### 4. 清晰解耦
- Meta Skills vs KB Skills
- 架构师 vs 执行者
- 代码生成 vs 任务执行

---

## 下一步

1. ✅ 安装 Claude Agent SDK
2. ✅ 创建 sonnet_worker.py
3. ⏳ 创建 Meta Skills
4. ⏳ 创建评测套件
5. ⏳ 实现闭环优化

---

**准备开始实现？**
