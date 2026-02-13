# knowledge-base-search

基于 Git + Qdrant + BGE-M3 + MCP + Claude Code 的中文知识库检索系统。

## 架构

- Git 仓库 = 文档单一事实源（SSOT），通过 commit 管理版本
- Qdrant = 可再生索引层（本地 Docker），dense + sparse 混合检索
- MCP Server = 检索 + 预处理工具层，Claude Code 通过 Skills 编排
- 可复现（index manifest）、可追溯（引用链）、可回归（eval 框架）

## 快速开始

```bash
make bootstrap          # 安装依赖 + 启动 Qdrant
make index              # 构建索引
```

在 Claude Code 中使用：
```
/search Redis 主从切换后如何重连？
/ingest raw/report.pdf
/review
```

## 常用命令

```bash
make bootstrap           # 一键初始化
make ingest SRC=raw/x.pdf DEST=docs/runbook/  # 导入文档
make index               # 增量更新索引
make index-full          # 全量重建索引
make index-status        # 查看索引状态
make search Q="查询内容"  # 交互式检索
make review              # 文档健康度检查
make eval                # 检索回归测试
make clean               # 停止 Qdrant
```

## 文档

详细设计文档见 [docs/design.md](docs/design.md)。
