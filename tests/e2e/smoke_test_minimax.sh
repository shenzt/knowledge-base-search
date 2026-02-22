#!/bin/bash
# MiniMax M2.5 Smoke Test — 5 cases
# 测试: redis-dt-001, redis-ops-001, llm-rag-001, local-001, notfound-001

export ANTHROPIC_BASE_URL="https://api.minimaxi.com/anthropic"
export ANTHROPIC_API_KEY="${MINIMAX_API_KEY:?请设置 MINIMAX_API_KEY 环境变量}"
export MODEL_NAME="MiniMax-M2.5"
export USE_MCP=1
export USE_JUDGE=0
export EVAL_CONCURRENCY=1
export EVAL_SMOKE_IDS="redis-dt-001,redis-ops-001,llm-rag-001,local-001,notfound-001"

.venv/bin/python tests/e2e/test_agentic_rag_sdk.py
