#!/usr/bin/env python3
"""RAGBench techqa 数据集导入脚本。

从 HuggingFace 下载 rungalileo/ragbench techqa 子集，
将文档转为 Markdown 并生成评测用例。

用法:
    .venv/bin/python scripts/import_ragbench.py [--n 50] [--out-dir docs/ragbench-techqa]
"""

import argparse
import hashlib
import json
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """清理文档文本，转为 Markdown 格式。"""
    # 去除多余空行
    text = re.sub(r'\n{3,}', '\n\n', text.strip())
    # 去除行尾空格
    text = re.sub(r' +\n', '\n', text)
    return text


def doc_id(question: str, idx: int) -> str:
    """生成稳定的文档 ID。"""
    return hashlib.md5(f"ragbench-techqa-{question[:50]}-{idx}".encode()).hexdigest()[:8]


def main():
    parser = argparse.ArgumentParser(description="导入 RAGBench techqa 数据集")
    parser.add_argument("--n", type=int, default=50, help="导入 QA 数量")
    parser.add_argument("--out-dir", default="docs/ragbench-techqa", help="文档输出目录")
    parser.add_argument("--cases-out", default="tests/fixtures/ragbench_techqa_cases.py",
                        help="测试用例输出文件")
    args = parser.parse_args()

    from datasets import load_dataset

    log.info("下载 RAGBench techqa 数据集...")
    ds = load_dataset("rungalileo/ragbench", "techqa", split="test")
    log.info(f"总计 {len(ds)} 条，选取前 {args.n} 条")

    # 选取前 N 条
    selected = ds.select(range(min(args.n, len(ds))))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 收集所有唯一文档（去重）
    doc_map = {}  # content_hash -> (filename, content)
    qa_doc_mapping = []  # (qa_idx, [doc_filenames])

    for i, record in enumerate(selected):
        doc_files = []
        for j, doc_text in enumerate(record["documents"]):
            content = clean_text(doc_text)
            if len(content) < 20:
                continue
            content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
            if content_hash not in doc_map:
                did = doc_id(record["question"], j)
                # 从文档首行提取标题
                first_line = content.split('\n')[0].strip()
                title = first_line[:80] if first_line else f"techqa-doc-{did}"
                title = re.sub(r'[#*\[\]]', '', title).strip()

                filename = f"{did}.md"
                front_matter = f"""---
id: "{did}"
title: "{title}"
source_repo: "rungalileo/ragbench"
source_path: "techqa/test/{i}/doc_{j}"
tags: [ragbench, techqa]
confidence: medium
---

"""
                doc_map[content_hash] = (filename, front_matter + content)
            doc_files.append(doc_map[content_hash][0])
        qa_doc_mapping.append((i, doc_files))

    # 写入文档文件
    log.info(f"写入 {len(doc_map)} 个唯一文档到 {out_dir}/")
    for content_hash, (filename, content) in doc_map.items():
        filepath = out_dir / filename
        filepath.write_text(content, encoding="utf-8")

    # 生成测试用例
    cases = []
    for i, (qa_idx, doc_files) in enumerate(qa_doc_mapping):
        record = selected[qa_idx]
        case_id = f"ragbench-techqa-{i+1:03d}"
        # 用第一个文档作为 expected_doc
        expected_doc = doc_files[0] if doc_files else ""
        # 从 gold answer 提取关键词
        answer_words = record["response"].split()
        keywords = [w for w in answer_words if len(w) > 4 and w.isalpha()][:5]

        cases.append({
            "id": case_id,
            "query": record["question"],
            "source": "qdrant",
            "category": "ragbench-techqa",
            "expected_doc": expected_doc,
            "expected_keywords": keywords,
            "gold_answer": record["response"],
            "gold_ragas_faithfulness": record.get("ragas_faithfulness", None),
        })

    # 写入测试用例文件
    cases_path = Path(args.cases_out)
    cases_path.parent.mkdir(parents=True, exist_ok=True)

    with open(cases_path, "w", encoding="utf-8") as f:
        f.write('"""RAGBench techqa 评测用例（自动生成）。"""\n\n')
        f.write(f"# 从 rungalileo/ragbench techqa test split 导入\n")
        f.write(f"# 共 {len(cases)} 条\n\n")
        f.write("RAGBENCH_TECHQA_CASES = ")
        f.write(json.dumps(cases, ensure_ascii=False, indent=2))
        f.write("\n")

    log.info(f"生成 {len(cases)} 个测试用例 → {cases_path}")
    log.info(f"\n下一步:")
    log.info(f"  1. .venv/bin/python scripts/doc_preprocess.py --dir {out_dir}")
    log.info(f"  2. .venv/bin/python scripts/index.py --full {out_dir}")


if __name__ == "__main__":
    main()
