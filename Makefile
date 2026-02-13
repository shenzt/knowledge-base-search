.PHONY: bootstrap index status clean

# 一键初始化
bootstrap:
	pip install -r scripts/requirements.txt
	docker compose up -d
	@echo "✅ 就绪。在 Claude Code 中使用 /ingest 导入文档，/search 检索"

# 增量更新索引（索引 docs/ 下所有 .md 文件）
index:
	@for f in docs/**/*.md; do \
		[ -f "$$f" ] && python scripts/index.py --file "$$f"; \
	done

# 查看索引状态
status:
	python scripts/index.py --status

# 停止 Qdrant
clean:
	docker compose down
