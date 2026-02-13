# 双层 Claude 架构实现总结

**日期**: 2025-02-13
**版本**: v2.0

---

## 🎯 架构概述

实现了 **Meta-Agent (元代理)** 架构，通过两层 Claude 模型协作：

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Meta-Agent (Claude Opus)                      │
│  - 角色: 架构师、代码生成器、系统优化器                    │
│  - 模型: claude-3-opus-20240229                          │
│  - Skills: meta_skills/ (生成代码、运行评测、优化系统)    │
│  - 位置: 用户直接交互的 Claude Code CLI                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Claude Agent SDK
                     │ from claude_agent_sdk import query
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Worker-Agent (Claude Sonnet)                  │
│  - 角色: 执行者、文档处理器、RAG 引擎                      │
│  - 模型: claude-3-5-sonnet-20241022                      │
│  - Skills: kb_skills/ (转换、索引、检索)                  │
│  - 位置: 被 Layer 1 通过 SDK 调用                        │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 目录结构

```
knowledge-base-search/
├── meta_skills/              # Layer 1 专属 (Opus)
│   └── run-sonnet-task/      # 调用 Sonnet Worker
│       └── SKILL.md
│
├── kb_skills/                # Layer 2 专属 (Sonnet)
│   ├── convert-html/         # HTML → Markdown
│   ├── build-index/          # 构建分层索引
│   ├── index-docs/           # 向量索引
│   ├── search/               # 混合检索
│   ├── search-hierarchical/  # 分层检索
│   ├── sync-from-raw/        # 双仓同步
│   └── update-index/         # 增量更新
│
├── sonnet_worker.py          # Layer 2 执行引擎 ✨ 新增
├── test_sonnet_worker.py     # Sonnet Worker 测试 ✨ 新增
│
├── docs/
│   └── dual-layer-architecture.md  # 架构设计文档 ✨ 新增
│
└── scripts/
    ├── mcp_server.py         # MCP Server (混合检索)
    └── index.py              # 索引工具
```

---

## 🔧 核心组件

### 1. Sonnet Worker (`sonnet_worker.py`)

使用 Claude Agent SDK 创建 Layer 2 执行引擎：

```python
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_rag_task(task: str, working_dir: str = "./kb_skills"):
    """调用 Sonnet agent 执行 RAG 任务"""
    async for message in query(
        prompt=task,
        options=ClaudeAgentOptions(
            model="claude-3-5-sonnet-20241022",
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            setting_sources=["project"],
            working_directory=working_dir,
            mcp_servers={
                "knowledge-base": {
                    "command": "python",
                    "args": ["scripts/mcp_server.py"]
                }
            }
        )
    ):
        # 处理消息...
```

**功能**:
- ✅ 异步执行任务
- ✅ 自动工具调用
- ✅ Session 管理
- ✅ Token 统计
- ✅ 错误处理

### 2. Meta Skill: `/run-sonnet-task`

Layer 1 (Opus) 用于调用 Layer 2 (Sonnet) 的 skill：

```markdown
# run-sonnet-task

调用 Sonnet Worker 执行知识库任务。

## 示例

/run-sonnet-task "将 Redis HTML 文档转换为 Markdown"
```

### 3. 预定义任务模板

```python
# HTML 转换
await convert_html_docs(input_dir, output_dir)

# 构建索引
await build_index(docs_dir, output_dir)

# 向量索引
await index_to_qdrant(docs_dir)

# 知识检索
await search_knowledge_base(query_text)
```

---

## 💡 核心优势

### 1. 成本优化 💰

| 模型 | 价格 (每 1M tokens) | 用途 |
|------|-------------------|------|
| Opus | $15 输入 / $75 输出 | 高级决策、代码生成 |
| Sonnet | $3 输入 / $15 输出 | 大量文档处理 |

**预计节省**: 70-80% 成本

**示例**:
- 处理 1569 个 K8s 文档
- 全用 Opus: ~$50
- 双层架构: ~$10 (Opus 决策 + Sonnet 执行)

### 2. 速度提升 ⚡

- **Sonnet 更快**: 处理文档速度快
- **Opus 专注**: 不被执行细节拖累
- **并行处理**: 可以同时运行多个 Sonnet worker

### 3. 自我进化 🔄

```
1. Opus 生成 KB Skill 代码
   ↓
2. Opus 调用 Sonnet 执行任务
   ↓
3. Sonnet 返回执行日志 (session_id, tool_calls)
   ↓
4. Opus 分析日志，发现问题
   ↓
5. Opus 修改代码
   ↓
6. 重新测试 → 闭环优化
```

### 4. 清晰解耦 🎯

| Layer | 角色 | 模型 | Skills | 职责 |
|-------|------|------|--------|------|
| 1 | 架构师 | Opus | meta_skills/ | 写代码、优化系统 |
| 2 | 执行者 | Sonnet | kb_skills/ | 处理文档、RAG |

---

## 🚀 使用示例

### 示例 1: 从 Opus 调用 Sonnet

```python
# 在 Opus 层 (Layer 1)
from sonnet_worker import run_rag_task

result = await run_rag_task(
    task="将 kb-test-redis-cn 的 HTML 转换为 Markdown，然后索引到 Qdrant"
)

print(result['result'])
print(f"Token 使用: {result['usage']['total_tokens']}")
```

### 示例 2: 使用 Meta Skill

```bash
# 在 Claude Code CLI 中 (Opus)
/run-sonnet-task "完成以下任务：
1. 转换 Redis HTML 文档
2. 构建分层索引
3. 索引到 Qdrant
4. 回答：Redis 管道技术如何工作？"
```

### 示例 3: 直接测试 Sonnet Worker

```bash
# 命令行测试
python sonnet_worker.py "列出所有 Python 文件"
python sonnet_worker.py search "What is a Pod in Kubernetes?"
```

---

## 📊 技术实现

### Claude Agent SDK 集成

```python
from claude_agent_sdk import query, ClaudeAgentOptions

# 配置 Sonnet agent
options = ClaudeAgentOptions(
    model="claude-3-5-sonnet-20241022",
    allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    setting_sources=["project"],  # 使用 kb_skills/ 配置
    working_directory="./kb_skills",
    mcp_servers={
        "knowledge-base": {
            "command": "python",
            "args": ["scripts/mcp_server.py"]
        }
    }
)

# 执行任务
async for message in query(prompt=task, options=options):
    # 处理消息
```

### Session 管理

```python
# 第一次调用
result1 = await run_rag_task("读取文档")
session_id = result1['session_id']

# 恢复 session 继续
result2 = await resume_task(session_id, "现在索引这些文档")
```

### 工具调用追踪

```python
# 收集所有工具调用
tool_calls = []
async for message in query(...):
    if message.type == "tool_use":
        tool_calls.append({
            "tool": message.name,
            "input": message.input
        })

# Opus 可以分析这些调用来优化代码
```

---

## 🎯 下一步计划

### 短期 (本周)

1. ✅ 安装 Claude Agent SDK
2. ✅ 创建 Sonnet Worker
3. ✅ 创建 Meta Skill: `/run-sonnet-task`
4. ⏳ 测试基本功能
5. ⏳ 创建更多 Meta Skills:
   - `/analyze-sonnet-logs` - 分析执行日志
   - `/optimize-kb-skill` - 优化 KB Skill 代码
   - `/run-eval` - 运行评测套件

### 中期 (下周)

1. 实现闭环优化流程
2. 创建评测套件
3. 自动化代码优化
4. 性能对比测试

### 长期

1. 多 Sonnet Worker 并行
2. 自动 Skill 生成
3. 持续学习和优化
4. 生产环境部署

---

## 📝 配置文件

### Layer 1 配置 (Opus)

```json
// .claude/config.json
{
  "model": "claude-3-opus-20240229",
  "skills_directory": "./meta_skills",
  "allowed_tools": ["Read", "Write", "Edit", "Bash", "Task"]
}
```

### Layer 2 配置 (Sonnet)

```json
// kb_skills/.claude/config.json
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

## 🎉 总结

### 已完成

✅ **架构设计**: 双层 Meta-Agent 架构
✅ **Sonnet Worker**: 基于 Claude Agent SDK
✅ **Meta Skill**: `/run-sonnet-task`
✅ **Skills 分离**: meta_skills/ vs kb_skills/
✅ **文档完善**: 架构设计、使用指南

### 核心价值

🚀 **成本降低**: 70-80% (Sonnet 处理大量任务)
⚡ **速度提升**: Sonnet 更快，Opus 专注决策
🔄 **自我进化**: 闭环优化，持续改进
🎯 **清晰解耦**: 架构师 vs 执行者

### 技术亮点

- 使用 Claude Agent SDK 实现双层调用
- Session 管理支持上下文延续
- 工具调用追踪用于优化分析
- MCP Server 集成混合检索

---

**双层 Claude 架构已就绪！** 🎉

可以开始使用 Opus 调用 Sonnet 处理大规模文档任务了。
