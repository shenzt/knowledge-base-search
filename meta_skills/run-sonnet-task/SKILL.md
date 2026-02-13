# run-sonnet-task

调用 Sonnet Worker (Layer 2) 执行知识库相关任务。

## 描述

这是 Layer 1 (Opus) 专属的 Meta Skill，用于将任务委派给 Layer 2 (Sonnet) 执行。

Sonnet Worker 负责：
- 文档处理 (HTML 转换、分块)
- 索引构建 (向量化、写入 Qdrant)
- 知识检索 (混合检索、RRF 融合)
- 数据同步 (双仓同步)

## 使用场景

1. **文档转换**: 将大量 HTML 文档转换为 Markdown
2. **批量索引**: 索引数百个文档到 Qdrant
3. **知识检索**: 在知识库中搜索答案
4. **端到端流程**: 转换 → 索引 → 检索

## 参数

- `task`: 任务描述 (自然语言)
- `working_dir`: 工作目录 (默认 `./kb_skills`)
- `enable_mcp`: 是否启用 MCP Server (默认 true)

## 示例

### 示例 1: HTML 转换

```
/run-sonnet-task "将 kb-test-redis-cn 目录中的 HTML 文档转换为 Markdown，输出到 docs/redis/"
```

### 示例 2: 批量索引

```
/run-sonnet-task "将 docs/redis/ 目录中的所有文档索引到 Qdrant"
```

### 示例 3: 知识检索

```
/run-sonnet-task "在知识库中搜索：Redis 管道技术如何工作？"
```

### 示例 4: 端到端流程

```
/run-sonnet-task "完成以下任务：
1. 将 kb-test-redis-cn 的 HTML 转换为 Markdown
2. 构建分层索引
3. 索引到 Qdrant
4. 回答：Redis 管道技术如何提升性能？"
```

## 工作流程

1. **接收任务**: Opus 接收用户指令
2. **调用 Sonnet**: 通过 `sonnet_worker.py` 调用 Sonnet agent
3. **执行任务**: Sonnet 使用 KB Skills 完成任务
4. **收集日志**: 记录 session_id、工具调用、token 使用
5. **返回结果**: 将结果返回给 Opus
6. **分析优化**: Opus 分析执行日志，识别改进点

## 输出

执行结果包含：
- `status`: 成功/失败状态
- `session_id`: Sonnet session ID (可用于恢复)
- `result`: 任务执行结果
- `tool_calls`: 工具调用列表
- `usage`: Token 使用统计

## 实现

使用 Claude Agent SDK 调用 Sonnet:

```python
from sonnet_worker import run_rag_task

result = await run_rag_task(
    task="用户的任务描述",
    working_dir="./kb_skills",
    enable_mcp=True
)
```

## 注意事项

1. **成本优化**: Sonnet 比 Opus 便宜 5-10 倍，适合大量文档处理
2. **速度优势**: Sonnet 更快，适合批量操作
3. **日志追踪**: 保存 session_id 用于后续分析和优化
4. **错误处理**: 如果 Sonnet 失败，Opus 可以分析日志并重试

## 相关 Skills

- `/analyze-sonnet-logs`: 分析 Sonnet 执行日志
- `/optimize-kb-skill`: 优化 KB Skill 代码
- `/run-eval`: 运行评测套件
