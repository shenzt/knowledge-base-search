.PHONY: bootstrap ingest index search review eval clean

# 一键初始化：安装依赖 + 启动 Qdrant
bootstrap:
	pip install -r scripts/requirements.txt
	docker compose up -d
	@echo "✅ Qdrant 已启动，运行 'make index' 构建索引"

# 导入原始文件（PDF/网页等）到知识库
# 用法: make ingest SRC=raw/xxx.pdf DEST=docs/runbook/
ingest:
	@test -n "$(SRC)" || (echo "❌ 用法: make ingest SRC=<文件路径> DEST=<目标目录>" && exit 1)
	python scripts/index.py --ingest "$(SRC)" --dest "$(DEST)"

# 构建/增量更新索引
index:
	python scripts/index.py --incremental

# 全量重建索引
index-full:
	python scripts/index.py --full

# 查看索引状态
index-status:
	python scripts/index.py --status

# 交互式检索测试
# 用法: make search Q="Redis 主从切换后如何重连？"
search:
	@test -n "$(Q)" || (echo "❌ 用法: make search Q=\"查询内容\"" && exit 1)
	python scripts/index.py --search "$(Q)"

# 文档健康度检查
review:
	python scripts/index.py --review

# 运行检索回归测试
eval:
	python eval/eval.py

# 清理：停止 Qdrant
clean:
	docker compose down
