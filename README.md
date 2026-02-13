# knowledge-base-search

基于 Git + Qdrant + Claude Code 的 Agentic RAG 本地知识库检索系统。

## 核心理念

**Claude Code 就是 agent。** 能用 agent 做的事情就让它做，不写多余代码。

- Git 仓库 = 文档单一事实源（SSOT）
- Claude Code = 核心 agent（预处理、分块、检索、审查）
- Qdrant = 可再生向量索引（不进 Git）
- MCP Server = 唯一的自建代码（向量检索需要常驻模型）

## 前置条件

- Python 3.10+
- Docker（用于运行 Qdrant）
- 约 3GB 磁盘空间（BGE-M3 模型首次运行时自动下载）

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url> && cd knowledge-base-search

# 2. 创建 venv 并安装依赖
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt

# 3. 启动 Qdrant
docker compose up -d

# 4. 索引示例文档（首次运行会下载 BGE-M3 模型，约 2-3 分钟）
.venv/bin/python scripts/index.py --file docs/runbook/redis-failover.md
.venv/bin/python scripts/index.py --file docs/runbook/kubernetes-pod-crashloop.md
.venv/bin/python scripts/index.py --file docs/api/authentication.md

# 5. 确认索引状态
.venv/bin/python scripts/index.py --status
```

> CPU-only PyTorch 即可运行（约 190MB），无需 GPU。安装时可用：
> `pip install torch --index-url https://download.pytorch.org/whl/cpu`

在 Claude Code 中使用：
```
/search Redis 主从切换后如何重连？
/search How to fix pod CrashLoopBackOff?
/ingest raw/report.pdf runbook
/index-docs --status
/review
```

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 向量数据库 | Qdrant | dense + sparse 混合检索 + RRF |
| Embedding | BAAI/bge-m3 | 1024d，中英文，dense + sparse |
| Reranker | BAAI/bge-reranker-v2-m3 | 中英文重排序 |
| Agent | Claude Code | Skills 编排，内置工具执行 |
| 版本管理 | Git | 文档 SSOT |

## 常用命令

```bash
docker compose up -d                              # 启动 Qdrant
.venv/bin/python scripts/index.py --status        # 查看索引状态
.venv/bin/python scripts/index.py --file <path>   # 索引单个文件
docker compose down                               # 停止 Qdrant
```

## 文档

详细设计见 [docs/design.md](docs/design.md)。
