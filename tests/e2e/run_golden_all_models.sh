#!/bin/bash
# Golden Eval — 6 models × 20 cases × RAGAS judge
# 串行执行，每个模型 ~30-60 min，总计 ~3-5h
# No set -e: continue even if one model fails

cd /home/shenzt/ws/knowledge-base-search

export USE_MCP=1
export USE_JUDGE=1
export EVAL_DATASET=golden
export EVAL_CONCURRENCY=1

echo "=========================================="
echo "Golden Eval: 6 models × 20 cases + RAGAS"
echo "=========================================="
echo "Start: $(date)"
echo ""

# 1. Claude Sonnet (direct, no router)
echo "[1/6] Claude Sonnet (direct)"
unset USE_ROUTER ROUTER_MODEL ANTHROPIC_API_KEY MODEL_NAME
.venv/bin/python tests/e2e/test_agentic_rag_sdk.py 2>&1
echo "[1/6] Done: $(date)"
echo ""

# 2. Qwen 3.5 Plus (router)
echo "[2/6] Qwen 3.5 Plus (router)"
unset ANTHROPIC_API_KEY MODEL_NAME
export USE_ROUTER=1
export ROUTER_MODEL=qwen-3.5-plus
.venv/bin/python tests/e2e/test_agentic_rag_sdk.py 2>&1
echo "[2/6] Done: $(date)"
echo ""

# 3. GLM-5 (router)
echo "[3/6] GLM-5 (router)"
export ROUTER_MODEL=glm-5
.venv/bin/python tests/e2e/test_agentic_rag_sdk.py 2>&1
echo "[3/6] Done: $(date)"
echo ""

# 4. DeepSeek V3.2 (router)
echo "[4/6] DeepSeek V3.2 (router)"
export ROUTER_MODEL=deepseek-chat
.venv/bin/python tests/e2e/test_agentic_rag_sdk.py 2>&1
echo "[4/6] Done: $(date)"
echo ""

# 5. Kimi K2.5 (router)
echo "[5/6] Kimi K2.5 (router)"
export ROUTER_MODEL=kimi-k2.5
.venv/bin/python tests/e2e/test_agentic_rag_sdk.py 2>&1
echo "[5/6] Done: $(date)"
echo ""

# 6. MiniMax M2.5 (direct Anthropic-compatible)
echo "[6/6] MiniMax M2.5 (direct)"
unset USE_ROUTER ROUTER_MODEL
export ANTHROPIC_BASE_URL="https://api.minimaxi.com/anthropic"
export ANTHROPIC_API_KEY="${MINIMAX_API_KEY:?请设置 MINIMAX_API_KEY 环境变量}"
export MODEL_NAME="MiniMax-M2.5"
.venv/bin/python tests/e2e/test_agentic_rag_sdk.py 2>&1
echo "[6/6] Done: $(date)"
echo ""

echo "=========================================="
echo "All 6 models done: $(date)"
echo "=========================================="
