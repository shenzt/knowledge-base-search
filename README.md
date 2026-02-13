# knowledge-base-search

基于 Git + Qdrant + Claude Code 的中文知识库检索系统。

## 核心理念

Claude Code 就是 agent。文档预处理、分块、审查等全部由 Claude Code 通过 Skills 编排完成，项目只写真正需要的代码（向量检索 MCP Server）。

## 组件

- Git — 文档版本管理（单一事实源）
- Qdrant — 向量索引（可再生，不进 Git）
- Skills — 定义 agent 行为（ingest/search/index-docs/review）
- MCP Server — 唯一的代码，提供向量检索能力

## 快速开始

```bash
make bootstrap          # 安装依赖 + 启动 Qdrant
```

在 Claude Code 中：
```
/ingest raw/report.pdf runbook     # 导入文档
/search Redis 主从切换后如何重连？  # 检索问答
/index-docs --status               # 查看索引状态
/review                            # 文档健康度检查
```

## 常用命令

```bash
make bootstrap       # 一键初始化
make index           # 增量更新索引
make status          # 查看索引状态
make clean           # 停止 Qdrant
```

## 文档

详细设计见 [docs/design.md](docs/design.md)。
