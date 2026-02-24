#!/usr/bin/env python3
"""文档预处理：批量 LLM 分析，生成 sidecar JSON 元数据。

用法:
  python scripts/doc_preprocess.py --dir ../my-agent-kb/docs/redis-docs/
  python scripts/doc_preprocess.py --file docs/runbook/redis-failover.md
  python scripts/doc_preprocess.py --status ../my-agent-kb/docs/
  python scripts/doc_preprocess.py --dir ../my-agent-kb/docs/ --force
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Semaphore
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import frontmatter

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

SIDECAR_DIR = ".preprocess"
MAX_WORKERS = int(os.environ.get("PREPROCESS_WORKERS", "8"))
CACHE_FILE = "scripts/.preprocess_cache.json"
SCHEMA_VERSION = 1
PROMPT_VERSION = "doc_preprocess_v1"

# 截断策略：head 2000 + tail 1000（ChatGPT 建议：ops 文档命令常在后半段）
HEAD_CHARS = 2000
TAIL_CHARS = 1000

# 全局速率控制（Gemini 建议：防 provider 限流）
_rate_semaphore = Semaphore(MAX_WORKERS)


# ── Evidence Flags（正则，零 LLM 成本）─────────────────────────

def compute_evidence_flags(content: str) -> dict:
    """用正则检测文档中的证据类型。"""
    return {
        "has_command": bool(re.search(
            r'(```(?:bash|sh|shell|console)[\s\S]*?```'
            r'|^\s*\$\s+\w+'
            r'|`(?:redis-cli|kubectl|docker|curl|pip|npm|git|make)\b[^`]*`)',
            content, re.MULTILINE)),
        "has_config": bool(re.search(
            r'(```(?:yaml|yml|toml|ini|conf|json|xml|env|properties)[\s\S]*?```'
            r'|(?:^|\n)\s*\w+\s*[:=]\s*\S+)',
            content, re.MULTILINE)),
        "has_code_block": bool(re.search(r'```\w*\n', content)),
        "has_steps": bool(re.search(
            r'(^#{1,4}\s+(?:step\s+\d|第[一二三四五六七八九十\d]+步|\d+\.\s)'
            r'|^(?:\d+)\.\s+\*\*)',
            content, re.MULTILINE | re.IGNORECASE)),
    }


# ── 确定性 Gap Flags 融合（ChatGPT 建议：不完全依赖 LLM）────

def merge_gap_flags(llm_gaps: list, doc_type: str,
                    evidence_flags: dict) -> list:
    """用确定性规则融合 gap_flags，LLM 输出仅作补充。"""
    gaps = set(llm_gaps) if llm_gaps else set()

    # 规则：guide/tutorial/troubleshooting 类文档应该有命令
    if doc_type in ("guide", "tutorial", "troubleshooting"):
        if not evidence_flags.get("has_command"):
            gaps.add("missing_command")
        if not evidence_flags.get("has_config"):
            gaps.add("missing_config")

    return sorted(gaps)


# ── Content Hash ────────────────────────────────────────────────

def content_hash(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_FILE) or ".", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


# ── 截断策略：head + tail + code blocks ────────────────────────

def smart_truncate(content: str) -> str:
    """head 2000 + tail 1000，中间用省略标记。"""
    if len(content) <= HEAD_CHARS + TAIL_CHARS:
        return content
    head = content[:HEAD_CHARS]
    tail = content[-TAIL_CHARS:]
    return f"{head}\n\n[... 中间内容省略 ...]\n\n{tail}"


# ── LLM 调用 ───────────────────────────────────────────────────

SYSTEM_PROMPT = "You are a technical documentation analyst. Return only valid JSON."

USER_PROMPT_TEMPLATE = """Analyze this document and return a JSON object.

<document>
Title: {title}
Source: {source_repo} / {source_path}

{content}
</document>

Return ONLY a JSON object with these fields:
- "contextual_summary": One sentence (max 50 words) describing what this document covers. Start with the document subject, not "This document".
- "doc_type": One of: tutorial, reference, guide, troubleshooting, overview, example
- "quality_score": Integer 0-10. Score based on: actionability (has concrete steps/commands?), specificity (covers topic in depth?), structure (well-organized?).
- "key_concepts": Array of 3-5 key technical terms from this document.
- "gap_flags": Array of applicable flags from: "missing_command", "missing_config", "missing_example", "incomplete_steps". Empty array if no gaps.

JSON only, no markdown fences, no explanation."""


def _extract_json(raw: str) -> Optional[dict]:
    """从 LLM 输出中提取 JSON（Gemini 建议：正则清洗）。"""
    raw = raw.strip()
    # 去掉 markdown 围栏
    if raw.startswith("```"):
        raw = re.sub(r'^```\w*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw)
    # 提取第一个 {...} 块
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def call_llm(title: str, source_repo: str, source_path: str,
             content: str) -> Optional[dict]:
    """调用 LLM 分析单个文档。"""
    from llm_client import get_client

    prompt = USER_PROMPT_TEMPLATE.format(
        title=title,
        source_repo=source_repo or "local",
        source_path=source_path or "",
        content=smart_truncate(content),
    )

    _rate_semaphore.acquire()
    try:
        client = get_client("doc_process")
        raw = client.generate(prompt, max_tokens=500, temperature=0,
                              system=SYSTEM_PROMPT)
        result = _extract_json(raw)
        if result is None:
            log.warning(f"  JSON 解析失败: {raw[:200]}")
            return None

        # 校验必需字段
        required = ["contextual_summary", "doc_type", "quality_score",
                     "key_concepts", "gap_flags"]
        for field in required:
            if field not in result:
                log.warning(f"  缺少字段 {field}")
                return None

        # 类型校验 + 修正
        valid_types = {"tutorial", "reference", "guide", "troubleshooting",
                       "overview", "example"}
        if result["doc_type"] not in valid_types:
            result["doc_type"] = "reference"
        result["quality_score"] = max(0, min(10, int(result["quality_score"])))

        return result
    except Exception as e:
        log.error(f"  LLM 调用失败: {e}")
        return None
    finally:
        _rate_semaphore.release()


# ── 处理单个文档 ────────────────────────────────────────────────

def _sidecar_path(filepath: str) -> str:
    p = Path(filepath)
    return str(p.parent / SIDECAR_DIR / (p.stem + ".json"))


def process_doc(filepath: str, force: bool = False,
                cache: Optional[dict] = None) -> Optional[str]:
    """处理单个文档。返回 sidecar 路径，跳过返回 None。"""
    post = frontmatter.load(filepath)
    content = post.content
    h = content_hash(content)

    # 增量跳过
    if not force and cache and cache.get(filepath) == h:
        sidecar = _sidecar_path(filepath)
        if os.path.exists(sidecar):
            return None

    title = post.metadata.get("title", os.path.basename(filepath))
    source_repo = post.metadata.get("source_repo", "")
    source_path = post.metadata.get("source_path", "")

    # 正则 evidence_flags（始终计算）
    evidence_flags = compute_evidence_flags(content)

    # LLM 分析
    llm_result = call_llm(title, source_repo, source_path, content)

    # 组装 sidecar（ChatGPT 建议：LLM 失败也写，至少 evidence_flags 可用）
    if llm_result:
        gap_flags = merge_gap_flags(
            llm_result.get("gap_flags", []),
            llm_result.get("doc_type", "reference"),
            evidence_flags,
        )
        sidecar_data = {
            "schema_version": SCHEMA_VERSION,
            "content_hash": f"sha1:{h}",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": os.environ.get("DOC_PROCESS_MODEL", "unknown"),
            "prompt_version": PROMPT_VERSION,
            "llm_status": "ok",
            "contextual_summary": llm_result["contextual_summary"],
            "doc_type": llm_result["doc_type"],
            "quality_score": llm_result["quality_score"],
            "key_concepts": llm_result["key_concepts"],
            "gap_flags": gap_flags,
            "evidence_flags": evidence_flags,
        }
    else:
        # LLM 失败：仍写 sidecar，evidence_flags 仍有价值
        sidecar_data = {
            "schema_version": SCHEMA_VERSION,
            "content_hash": f"sha1:{h}",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": os.environ.get("DOC_PROCESS_MODEL", "unknown"),
            "prompt_version": PROMPT_VERSION,
            "llm_status": "failed",
            "contextual_summary": "",
            "doc_type": "",
            "quality_score": 0,
            "key_concepts": [],
            "gap_flags": [],
            "evidence_flags": evidence_flags,
        }

    # 写 sidecar
    sidecar_path = _sidecar_path(filepath)
    os.makedirs(os.path.dirname(sidecar_path), exist_ok=True)
    with open(sidecar_path, "w") as f:
        json.dump(sidecar_data, f, ensure_ascii=False, indent=2)

    # 更新缓存
    if cache is not None:
        cache[filepath] = h

    status = "✅" if llm_result else "⚠️ (evidence_flags only)"
    return f"{status} {sidecar_path}"


# ── 批量处理 ────────────────────────────────────────────────────

def process_directory(docs_dir: str, force: bool = False) -> dict:
    md_files = sorted(Path(docs_dir).rglob("*.md"))
    # 跳过 .preprocess 目录下的文件
    md_files = [f for f in md_files if SIDECAR_DIR not in f.parts]
    if not md_files:
        log.info(f"目录 {docs_dir} 下没有 .md 文件")
        return {"total": 0, "processed": 0, "skipped": 0, "failed": 0}

    cache = load_cache()
    stats = {"total": len(md_files), "processed": 0, "skipped": 0,
             "failed": 0, "llm_failed": 0}

    log.info(f"📦 预处理: {len(md_files)} 个文件 ({docs_dir})")
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for f in md_files:
            future = executor.submit(process_doc, str(f), force, cache)
            futures[future] = str(f)

        for future in as_completed(futures):
            filepath = futures[future]
            try:
                result = future.result()
                if result is None:
                    stats["skipped"] += 1
                elif "⚠️" in result:
                    stats["llm_failed"] += 1
                    stats["processed"] += 1
                    log.info(f"  {result}")
                else:
                    stats["processed"] += 1
                    log.info(f"  {result}")
            except Exception as e:
                stats["failed"] += 1
                log.error(f"  ❌ {filepath}: {e}")

    save_cache(cache)
    elapsed = time.time() - t0
    log.info(f"\n📊 预处理完成 ({elapsed:.1f}s):")
    log.info(f"  处理: {stats['processed']} | 跳过: {stats['skipped']} "
             f"| 失败: {stats['failed']} | LLM失败: {stats['llm_failed']} "
             f"| 共: {stats['total']}")
    return stats


def show_status(docs_dir: str) -> None:
    md_files = list(Path(docs_dir).rglob("*.md"))
    md_files = [f for f in md_files if SIDECAR_DIR not in f.parts]
    sidecars = list(Path(docs_dir).rglob(f"{SIDECAR_DIR}/*.json"))

    log.info(f"目录: {docs_dir}")
    log.info(f"  文档数: {len(md_files)}")
    log.info(f"  已预处理: {len(sidecars)}")
    log.info(f"  未处理: {len(md_files) - len(sidecars)}")

    type_counts = {}
    quality_scores = []
    llm_ok = 0
    llm_fail = 0
    for s in sidecars:
        with open(s) as f:
            data = json.load(f)
        if data.get("llm_status") == "ok":
            llm_ok += 1
            dt = data.get("doc_type", "unknown")
            type_counts[dt] = type_counts.get(dt, 0) + 1
            quality_scores.append(data.get("quality_score", 0))
        else:
            llm_fail += 1

    if type_counts:
        log.info(f"  类型分布: {type_counts}")
    if quality_scores:
        avg = sum(quality_scores) / len(quality_scores)
        log.info(f"  平均质量分: {avg:.1f}/10")
    if llm_fail:
        log.info(f"  LLM 失败: {llm_fail} (仅 evidence_flags)")


# ── CLI ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="文档预处理工具")
    parser.add_argument("--dir", nargs="+", help="处理目录（支持多个）")
    parser.add_argument("--file", help="处理单个文件")
    parser.add_argument("--status", metavar="DIR", help="查看预处理状态")
    parser.add_argument("--force", action="store_true", help="忽略缓存")
    args = parser.parse_args()

    if args.status:
        show_status(args.status)
    elif args.file:
        cache = load_cache()
        result = process_doc(args.file, args.force, cache)
        save_cache(cache)
        if result:
            log.info(result)
        else:
            log.info("⏭️  跳过（未变更）")
    elif args.dir:
        for d in args.dir:
            process_directory(d, args.force)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
