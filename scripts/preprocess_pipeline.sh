#!/usr/bin/env bash
set -euo pipefail

# ── 预处理流水线 ──────────────────────────────────────────────
# 串联：预处理 → 索引 → 导出快照 → 同步到 kb repo → push
#
# 用法:
#   scripts/preprocess_pipeline.sh --kb-repo kb/kb-redis-docs --source ../my-agent-kb/docs/redis-docs
#   scripts/preprocess_pipeline.sh --kb-repo kb/kb-redis-docs --source ../my-agent-kb/docs/redis-docs --skip-preprocess
#   scripts/preprocess_pipeline.sh --kb-repo kb/kb-redis-docs --source ../my-agent-kb/docs/redis-docs --skip-index
#   scripts/preprocess_pipeline.sh --kb-repo kb/kb-redis-docs --source ../my-agent-kb/docs/redis-docs --dry-run

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$PROJECT_ROOT/.venv/bin/python"

# 默认值
KB_REPO=""
SOURCE_DIR=""
SKIP_PREPROCESS=false
SKIP_INDEX=false
DRY_RUN=false
COMMIT_MSG=""

usage() {
    cat <<EOF
用法: $0 --kb-repo <path> --source <path> [options]

必选:
  --kb-repo <path>      KB 仓库路径 (如 kb/kb-redis-docs)
  --source <path>       源文档目录 (如 ../my-agent-kb/docs/redis-docs)

可选:
  --skip-preprocess     跳过 LLM 预处理步骤
  --skip-index          跳过索引构建步骤（仅导出快照）
  --dry-run             只打印步骤，不执行
  --message <msg>       自定义 commit message
  -h, --help            显示帮助
EOF
    exit 1
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --kb-repo) KB_REPO="$2"; shift 2 ;;
        --source) SOURCE_DIR="$2"; shift 2 ;;
        --skip-preprocess) SKIP_PREPROCESS=true; shift ;;
        --skip-index) SKIP_INDEX=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --message) COMMIT_MSG="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo "未知参数: $1"; usage ;;
    esac
done

[[ -z "$KB_REPO" ]] && echo "错误: 缺少 --kb-repo" && usage
[[ -z "$SOURCE_DIR" ]] && echo "错误: 缺少 --source" && usage

# 解析绝对路径
KB_REPO="$(cd "$PROJECT_ROOT" && realpath "$KB_REPO")"
SOURCE_DIR="$(realpath "$SOURCE_DIR")"
KB_NAME="$(basename "$KB_REPO")"
# 从 kb-redis-docs 提取 redis-docs 作为子目录名
DOC_SUBDIR="${KB_NAME#kb-}"
SNAPSHOT_PATH="$KB_REPO/snapshots/knowledge-base.snapshot"

echo "═══════════════════════════════════════════════════"
echo "  预处理流水线: $KB_NAME"
echo "═══════════════════════════════════════════════════"
echo "  源目录:   $SOURCE_DIR"
echo "  KB 仓库:  $KB_REPO"
echo "  文档子目录: docs/$DOC_SUBDIR"
echo "  快照路径: $SNAPSHOT_PATH"
echo "═══════════════════════════════════════════════════"

if $DRY_RUN; then
    echo "[dry-run] 以下步骤将被执行:"
    $SKIP_PREPROCESS || echo "  1. LLM 预处理: $VENV scripts/doc_preprocess.py --dir $SOURCE_DIR"
    $SKIP_INDEX || echo "  2. 全量索引: $VENV scripts/index.py --full $SOURCE_DIR"
    echo "  3. 同步文档: rsync $SOURCE_DIR/ → $KB_REPO/docs/$DOC_SUBDIR/"
    echo "  4. 导出快照: $VENV scripts/index.py --snapshot-export $SNAPSHOT_PATH"
    echo "  5. Git commit + push: $KB_REPO"
    exit 0
fi

# Step 1: LLM 预处理
if ! $SKIP_PREPROCESS; then
    echo ""
    echo "── Step 1/5: LLM 预处理 ──"
    $VENV "$PROJECT_ROOT/scripts/doc_preprocess.py" --dir "$SOURCE_DIR"
else
    echo ""
    echo "── Step 1/5: LLM 预处理 [跳过] ──"
fi

# Step 2: 全量索引
if ! $SKIP_INDEX; then
    echo ""
    echo "── Step 2/5: 全量索引 ──"
    $VENV "$PROJECT_ROOT/scripts/index.py" --full "$SOURCE_DIR"
else
    echo ""
    echo "── Step 2/5: 全量索引 [跳过] ──"
fi

# Step 3: 同步文档到 KB 仓库
echo ""
echo "── Step 3/5: 同步文档 ──"
mkdir -p "$KB_REPO/docs/$DOC_SUBDIR"
rsync -a --delete "$SOURCE_DIR/" "$KB_REPO/docs/$DOC_SUBDIR/"
DOC_COUNT=$(find "$KB_REPO/docs/$DOC_SUBDIR" -name "*.md" | wc -l)
echo "同步完成: $DOC_COUNT 个 markdown 文件"

# Step 4: 导出快照
echo ""
echo "── Step 4/5: 导出 Qdrant 快照 ──"
mkdir -p "$KB_REPO/snapshots"
$VENV "$PROJECT_ROOT/scripts/index.py" --snapshot-export "$SNAPSHOT_PATH"

# Step 5: Git commit + push
echo ""
echo "── Step 5/5: Git commit + push ──"
cd "$KB_REPO"

if [[ -z "$COMMIT_MSG" ]]; then
    COMMIT_MSG="chore: update $DOC_SUBDIR docs + snapshot ($(date +%Y-%m-%d))"
fi

git add -A
if git diff --cached --quiet; then
    echo "无变更，跳过 commit"
else
    SNAP_SIZE=$(du -h "$SNAPSHOT_PATH" | cut -f1)
    git commit -m "$COMMIT_MSG

$DOC_COUNT markdown files, snapshot $SNAP_SIZE

Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>"
    git push
    echo "已 push 到远程仓库"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  完成! $KB_NAME 已更新"
echo "═══════════════════════════════════════════════════"
