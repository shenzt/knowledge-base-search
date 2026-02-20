#!/usr/bin/env python3
"""CRAG 数据集导入脚本。

从 CRAG (Comprehensive RAG Benchmark) 导入指定领域的 QA pairs，
将搜索结果页面转为 Markdown 并生成评测用例。

用法:
    # 先下载: curl -sL -o /tmp/crag_dev.jsonl.bz2 \
    #   "https://github.com/facebookresearch/CRAG/raw/main/data/crag_task_1_and_2_dev_v4.jsonl.bz2"
    .venv/bin/python scripts/import_crag.py --domain finance --n 50
"""

import argparse
import bz2
import hashlib
import json
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def html_to_markdown(html: str, max_len: int = 5000) -> str:
    """HTML → Markdown，截断到合理长度。"""
    try:
        from markdownify import markdownify as md
        text = md(html, heading_style="ATX", strip=["script", "style", "nav", "footer"])
    except Exception:
        # Fallback: 简单去标签
        text = re.sub(r'<[^>]+>', '', html)

    text = _clean_markdown(text, max_len)
    return text


def _clean_markdown(text: str, max_len: int = 5000) -> str:
    """清理 Markdown 中残留的 JS/CSS/HTML 垃圾。"""
    # 去除残留 JS 代码块
    text = re.sub(r'```(?:javascript|js)?\n.*?```', '', text, flags=re.DOTALL)
    # 去除内联 JS（window.xxx, function(), var xxx =, gtag, dataLayer）
    text = re.sub(r'^.*(?:window\.\w+|function\s*\(|var\s+\w+\s*=|gtag\(|dataLayer|Munchkin|\.init\().*$',
                  '', text, flags=re.MULTILINE)
    # 去除 CSS 片段
    text = re.sub(r'^.*(?:\.css\{|@media\s|@font-face|@keyframes|@import).*$',
                  '', text, flags=re.MULTILINE)
    # 去除 SVG/xmlns
    text = re.sub(r'<svg[^>]*>.*?</svg>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]*xmlns[^>]*>.*?</[^>]*>', '', text, flags=re.DOTALL)
    # 去除 HTML 标签残留
    text = re.sub(r'<(?:div|span|img|input|button|form|iframe|link|meta)[^>]*/?>', '', text)
    # 去除空链接
    text = re.sub(r'\[([^\]]*)\]\(\s*\)', r'\1', text)
    # 去除 cookie/consent 段落
    text = re.sub(r'^.*(?:cookie|consent|I Agree|Terms and Conditions|Skip to).*$',
                  '', text, flags=re.MULTILINE | re.IGNORECASE)
    # 清理多余空行
    text = re.sub(r'\n{3,}', '\n\n', text.strip())
    text = re.sub(r' +\n', '\n', text)
    text = re.sub(r'[ \t]{4,}', '  ', text)

    if len(text) > max_len:
        text = text[:max_len] + "\n\n...(truncated)"
    return text


def _is_garbage(content: str) -> bool:
    """检测内容是否主要是 JS/CSS 垃圾。"""
    garbage_patterns = [
        r'window\.\w+\s*=', r'function\s*\(', r'var\s+\w+\s*=',
        r'\.css\{', r'@media\s', r'<svg', r'xmlns',
        r'gtag\(', r'dataLayer', r'Munchkin',
    ]
    matches = sum(1 for p in garbage_patterns if re.search(p, content))
    return matches >= 2


def main():
    parser = argparse.ArgumentParser(description="导入 CRAG 数据集")
    parser.add_argument("--input", default="/tmp/crag_dev.jsonl.bz2",
                        help="CRAG JSONL.bz2 文件路径")
    parser.add_argument("--domain", default="finance",
                        help="选择领域: finance, sports, movie, music, open")
    parser.add_argument("--n", type=int, default=50, help="导入 QA 数量")
    parser.add_argument("--out-dir", default=None, help="文档输出目录")
    parser.add_argument("--cases-out", default=None, help="测试用例输出文件")
    args = parser.parse_args()

    if args.out_dir is None:
        args.out_dir = f"docs/crag-{args.domain}"
    if args.cases_out is None:
        args.cases_out = f"tests/fixtures/crag_{args.domain}_cases.py"

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 读取并过滤
    log.info(f"读取 CRAG 数据集: {args.input}")
    records = []
    with bz2.open(args.input, 'rt') as f:
        for line in f:
            record = json.loads(line)
            if record.get("domain") == args.domain:
                records.append(record)
            if len(records) >= args.n:
                break

    log.info(f"选取 {len(records)} 条 {args.domain} 领域 QA")

    # 为每个 QA 的搜索结果生成文档
    doc_map = {}  # content_hash -> (filename, content)
    qa_doc_mapping = []

    for i, record in enumerate(records):
        doc_files = []
        search_results = record.get("search_results", [])

        for j, sr in enumerate(search_results[:3]):  # 每条最多取 3 个页面
            page_name = sr.get("page_name", f"page_{j}")
            snippet = sr.get("page_snippet", "")
            html = sr.get("page_result", "")

            # 优先用 snippet（干净），HTML 仅在 snippet 不足时使用
            content = ""
            if html and len(html) < 200000:
                md_content = html_to_markdown(html, max_len=5000)
                if not _is_garbage(md_content) and len(md_content) > 100:
                    content = md_content
            if not content and snippet:
                content = f"# {page_name}\n\n{snippet}"
            if not content:
                continue

            if len(content) < 30:
                continue

            content_hash = hashlib.md5(content[:500].encode()).hexdigest()[:12]
            if content_hash not in doc_map:
                did = hashlib.md5(
                    f"crag-{args.domain}-{i}-{j}".encode()
                ).hexdigest()[:8]
                title = re.sub(r'[#*\[\]"\'\\]', '', page_name).strip()[:80]

                front_matter = f"""---
id: "{did}"
title: "{title}"
source_repo: "facebookresearch/CRAG"
source_path: "crag/{args.domain}/{i}/page_{j}"
tags: [crag, {args.domain}]
confidence: medium
---

"""
                doc_map[content_hash] = (f"{did}.md", front_matter + content)
            doc_files.append(doc_map[content_hash][0])

        qa_doc_mapping.append((i, doc_files))

    # 写入文档
    log.info(f"写入 {len(doc_map)} 个唯一文档到 {out_dir}/")
    for content_hash, (filename, content) in doc_map.items():
        (out_dir / filename).write_text(content, encoding="utf-8")

    # 生成测试用例
    cases = []
    for i, (qa_idx, doc_files) in enumerate(qa_doc_mapping):
        record = records[qa_idx]
        case_id = f"crag-{args.domain[:3]}-{i+1:03d}"
        answer = record.get("answer", "")
        if isinstance(answer, list):
            answer = ", ".join(str(a) for a in answer)
        answer = str(answer)

        # 提取关键词
        query_words = record["query"].split()
        keywords = [w for w in query_words if len(w) > 4 and w.isalpha()][:5]

        cases.append({
            "id": case_id,
            "query": record["query"],
            "source": "qdrant",
            "category": f"crag-{args.domain}",
            "question_type": record.get("question_type", "unknown"),
            "expected_doc": doc_files[0] if doc_files else "",
            "expected_keywords": keywords,
            "gold_answer": answer,
        })

    # 写入测试用例
    cases_path = Path(args.cases_out)
    cases_path.parent.mkdir(parents=True, exist_ok=True)

    with open(cases_path, "w", encoding="utf-8") as f:
        f.write(f'"""CRAG {args.domain} 评测用例（自动生成）。"""\n\n')
        f.write(f"# 从 facebookresearch/CRAG dev split 导入\n")
        f.write(f"# 领域: {args.domain}, 共 {len(cases)} 条\n\n")
        f.write(f"CRAG_{args.domain.upper()}_CASES = ")
        f.write(json.dumps(cases, ensure_ascii=False, indent=2))
        f.write("\n")

    log.info(f"生成 {len(cases)} 个测试用例 → {cases_path}")

    # 统计问题类型分布
    qtypes = {}
    for record in records:
        qt = record.get("question_type", "unknown")
        qtypes[qt] = qtypes.get(qt, 0) + 1
    log.info(f"问题类型分布: {qtypes}")

    log.info(f"\n下一步:")
    log.info(f"  1. .venv/bin/python scripts/doc_preprocess.py --dir {out_dir}")
    log.info(f"  2. .venv/bin/python scripts/index.py --full {out_dir}")


if __name__ == "__main__":
    main()
