# knowledge-base-search

## 环境
- Python 3.10+, 依赖见 @scripts/requirements.txt
- Qdrant 本地运行: `docker run -d -p 6333:6333 qdrant/qdrant`
- 所有检索组件纯本地，仅 Claude Code 调用 Anthropic API 需联网

## 工作流
- 文档变更后运行 `python scripts/index.py --incremental` 更新索引
- 不要自动执行索引命令，必须由用户手动触发
- MCP Server 由 Claude Code 根据 .mcp.json 自动启动

## 文档语言
- 知识库文档以中文为主，部分 API 文档为英文
- 回答和交互使用中文
