.PHONY: help setup start stop status test test-unit test-integration test-e2e clean index

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Setup Python environment and install dependencies
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r scripts/requirements.txt
	.venv/bin/pip install pytest pytest-asyncio
	@echo "✅ Setup complete. Activate with: source .venv/bin/activate"

start: ## Start Qdrant service
	docker compose up -d
	@echo "✅ Qdrant started on http://localhost:6333"

stop: ## Stop Qdrant service
	docker compose down
	@echo "✅ Qdrant stopped"

status: ## Check Qdrant index status
	.venv/bin/python scripts/index.py --status

test: ## Run all tests
	.venv/bin/pytest tests/ -v

test-unit: ## Run unit tests
	.venv/bin/pytest tests/unit/ -v

test-integration: ## Run integration tests
	.venv/bin/pytest tests/integration/ -v

test-e2e: ## Run end-to-end tests
	.venv/bin/pytest tests/e2e/ -v

index: ## Index example documents
	.venv/bin/python scripts/index.py --file docs/runbook/redis-failover.md
	.venv/bin/python scripts/index.py --file docs/runbook/kubernetes-pod-crashloop.md
	.venv/bin/python scripts/index.py --file docs/api/authentication.md
	@echo "✅ Example documents indexed"

clean: ## Clean up generated files and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .ruff_cache
	@echo "✅ Cleaned up"

verify: ## Verify installation and configuration
	@echo "Checking Python version..."
	@python3 --version
	@echo "Checking virtual environment..."
	@test -d .venv && echo "✅ Virtual environment exists" || echo "❌ Virtual environment missing (run: make setup)"
	@echo "Checking Qdrant..."
	@docker compose ps | grep -q qdrant && echo "✅ Qdrant is running" || echo "❌ Qdrant not running (run: make start)"
	@echo "Checking .env file..."
	@test -f .env && echo "✅ .env file exists" || echo "⚠️  .env file missing (copy from .env.example)"
