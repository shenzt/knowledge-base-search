---
paths:
  - "scripts/**/*.py"
---

# Python 代码风格

- 类型注解：所有函数签名必须有 type hints
- 文档字符串：公开函数用中文 docstring
- 异步：MCP Server 的工具函数用 async def
- 日志：用 logging 模块，不要 print
- 错误处理：Qdrant/模型调用必须 try-except，返回有意义的错误信息
