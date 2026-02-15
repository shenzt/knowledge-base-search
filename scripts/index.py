#!/usr/bin/env python3
"""知识库索引构建工具。

按 Markdown 标题语义分块，注入 section_path 到 Qdrant payload。
支持单文件、全量重建、增量更新。

用法:
  # 索引单个文件
  python scripts/index.py --file docs/runbook/redis.md

  # 全量重建（遍历指定目录下所有 .md）
  python scripts/index.py --full docs/

  # 增量更新（基于 git diff）
  python scripts/index.py --incremental

  # 从 stdin 接收 chunks JSON
  echo '[{"doc_id":"abc","chunk_id":"abc-000","text":"...","metadata":{}}]' | python scripts/index.py

  # 删除某个文档的所有 chunks
  python scripts/index.py --delete --doc-id abc12345

  # 查看索引状态
  python scripts/index.py --status
"""

import argparse
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import frontmatter
import numpy as np
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient, models

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.environ.get("COLLECTION_NAME", "knowledge-base")
MODEL_NAME = os.environ.get("BGE_M3_MODEL", "BAAI/bge-m3")
MAX_CHUNK_CHARS = 3200

_model = None


def get_model() -> BGEM3FlagModel:
    """延迟加载 BGE-M3 模型。"""
    global _model
    if _model is None:
        log.info(f"加载模型 {MODEL_NAME}...")
        _model = BGEM3FlagModel(MODEL_NAME, use_fp16=True)
    return _model


def get_qdrant() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection(client: QdrantClient) -> None:
    """确保 collection 存在。"""
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION not in collections:
        log.info(f"创建 collection: {COLLECTION}")
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={
                "dense": models.VectorParams(size=1024, distance=models.Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(),
            },
        )


# ── 标题分块 ──────────────────────────────────────────────────────

def _clean_hugo_shortcodes(content: str) -> str:
    """清理 Hugo shortcodes，保留有意义的文本。"""
    # {{< glossary_tooltip text="containers" term_id="container" >}} → containers
    content = re.sub(
        r'\{\{<\s*glossary_tooltip\s+text="([^"]+)"[^>]*>\}\}',
        r'\1', content)
    # {{< glossary_tooltip term_id="node" >}} → node
    content = re.sub(
        r'\{\{<\s*glossary_tooltip\s+term_id="([^"]+)"[^>]*>\}\}',
        r'\1', content)
    # {{< note >}} ... {{< /note >}} → keep content
    content = re.sub(r'\{\{[<%]\s*/?\s*note\s*[%>]\}\}', '', content)
    # {{< warning >}} ... {{< /warning >}} → keep content
    content = re.sub(r'\{\{[<%]\s*/?\s*warning\s*[%>]\}\}', '', content)
    # {{< feature-state ... >}} → remove
    content = re.sub(r'\{\{<\s*feature-state[^>]*>\}\}', '', content)
    # {{% code_sample file="..." %}} → [code sample: ...]
    content = re.sub(
        r'\{\{%\s*code_sample\s+file="([^"]+)"\s*%\}\}',
        r'[code: \1]', content)
    # <!-- overview --> etc HTML comments → remove
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    # Any remaining shortcodes → remove
    content = re.sub(r'\{\{[<%][^}]*[%>]\}\}', '', content)
    # {{< relref "..." >}} inside links → keep link text
    content = re.sub(r'\{\{<\s*relref\s+"[^"]*"\s*>\}\}', '', content)
    return content

def _find_code_fence_ranges(content: str) -> list[tuple[int, int]]:
    """找出所有代码围栏 (```) 的范围，返回 [(start, end), ...]。"""
    fence_re = re.compile(r'^```', re.MULTILINE)
    ranges = []
    matches = list(fence_re.finditer(content))
    for i in range(0, len(matches) - 1, 2):
        ranges.append((matches[i].start(), matches[i + 1].end()))
    return ranges


def _in_code_fence(pos: int, ranges: list[tuple[int, int]]) -> bool:
    """判断某个位置是否在代码围栏内。"""
    return any(start <= pos <= end for start, end in ranges)


def split_by_headings(content: str) -> list[dict]:
    """按 Markdown 标题切分，保留 section_path 层级。跳过代码块中的 #。

    返回: [{"text": "...", "section_path": "故障恢复 > 手动恢复 > 确认新 Master"}]
    """
    heading_re = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    code_ranges = _find_code_fence_ranges(content)
    sections = []
    headings_stack: list[tuple[int, str]] = []  # [(level, title), ...]
    last_pos = 0

    for match in heading_re.finditer(content):
        # 跳过代码块中的 #
        if _in_code_fence(match.start(), code_ranges):
            continue

        # 保存上一段
        if last_pos < match.start():
            text = content[last_pos:match.start()].strip()
            if text:
                path = " > ".join(h[1] for h in headings_stack)
                sections.append({"text": text, "section_path": path})

        # 更新标题栈
        level = len(match.group(1))
        title = match.group(2).strip()
        # 弹出同级或更低级的标题
        while headings_stack and headings_stack[-1][0] >= level:
            headings_stack.pop()
        headings_stack.append((level, title))
        last_pos = match.end()

    # 最后一段
    if last_pos < len(content):
        text = content[last_pos:].strip()
        if text:
            path = " > ".join(h[1] for h in headings_stack)
            sections.append({"text": text, "section_path": path})

    return sections if sections else [{"text": content.strip(), "section_path": ""}]


def merge_small_sections(sections: list[dict], max_chars: int = MAX_CHUNK_CHARS) -> list[dict]:
    """合并过短的相邻 section（同一 section_path 前缀下）。"""
    if not sections:
        return sections

    merged = []
    buf_text = ""
    buf_path = ""

    for sec in sections:
        if not buf_text:
            buf_text = sec["text"]
            buf_path = sec["section_path"]
        elif len(buf_text) + len(sec["text"]) < max_chars and _same_parent(buf_path, sec["section_path"]):
            buf_text = buf_text + "\n\n" + sec["text"]
            buf_path = sec["section_path"]  # 用最新的 path
        else:
            merged.append({"text": buf_text, "section_path": buf_path})
            buf_text = sec["text"]
            buf_path = sec["section_path"]

    if buf_text:
        merged.append({"text": buf_text, "section_path": buf_path})

    return merged


def _same_parent(path_a: str, path_b: str) -> bool:
    """判断两个 section_path 是否有相同的父级。"""
    parts_a = path_a.split(" > ")[:-1]
    parts_b = path_b.split(" > ")[:-1]
    return parts_a == parts_b


# ── 索引核心 ──────────────────────────────────────────────────────

def index_chunks(chunks: list[dict], batch_size: int = 256) -> None:
    """将 chunks 编码为向量并写入 Qdrant。支持大批量分批编码。"""
    if not chunks:
        log.info("没有 chunks 需要索引")
        return

    model = get_model()
    client = get_qdrant()
    ensure_collection(client)

    # 编码时拼接 title + text，提升短文档的语义信号
    # 存储的 payload.text 保持原始内容不变
    encode_texts = []
    for c in chunks:
        title = c.get("metadata", {}).get("title", "")
        text = c["text"]
        encode_texts.append(f"{title}\n{text}" if title else text)

    log.info(f"编码 {len(encode_texts)} 个 chunks（batch_size={batch_size}）...")
    output = model.encode(encode_texts, return_dense=True, return_sparse=True,
                          batch_size=batch_size)

    points = []
    for i, chunk in enumerate(chunks):
        sparse = output["lexical_weights"][i]
        point_id = hashlib.md5(chunk["chunk_id"].encode()).hexdigest()

        payload = {
            "doc_id": chunk["doc_id"],
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
        }
        payload.update(chunk.get("metadata", {}))

        points.append(models.PointStruct(
            id=point_id,
            vector={
                "dense": output["dense_vecs"][i].tolist(),
                "sparse": models.SparseVector(
                    indices=list(map(int, sparse.keys())),
                    values=list(sparse.values()),
                ),
            },
            payload=payload,
        ))

    # 分批 upsert（Qdrant 单次上限约 1000 点）
    UPSERT_BATCH = 500
    for start in range(0, len(points), UPSERT_BATCH):
        batch = points[start:start + UPSERT_BATCH]
        client.upsert(collection_name=COLLECTION, points=batch)
        if len(points) > UPSERT_BATCH:
            log.info(f"  upsert {start + len(batch)}/{len(points)}")

    log.info(f"✅ 已索引 {len(points)} 个 chunks")


def delete_doc(doc_id: str) -> None:
    """删除某个文档的所有 chunks。"""
    client = get_qdrant()
    client.delete(
        collection_name=COLLECTION,
        points_selector=models.FilterSelector(
            filter=models.Filter(must=[
                models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))
            ])
        ),
    )
    log.info(f"✅ 已删除 doc_id={doc_id} 的所有 chunks")


def delete_by_source_repo(repo_url: str) -> None:
    """按 source_repo 字段批量删除某个仓库的所有 chunks。"""
    client = get_qdrant()
    # 先统计数量
    count_result = client.count(
        collection_name=COLLECTION,
        count_filter=models.Filter(must=[
            models.FieldCondition(key="source_repo", match=models.MatchValue(value=repo_url))
        ]),
    )
    n = count_result.count
    if n == 0:
        log.info(f"source_repo={repo_url} 无 chunks，跳过删除")
        return

    client.delete(
        collection_name=COLLECTION,
        points_selector=models.FilterSelector(
            filter=models.Filter(must=[
                models.FieldCondition(key="source_repo", match=models.MatchValue(value=repo_url))
            ])
        ),
    )
    log.info(f"✅ 已删除 source_repo={repo_url} 的 {n} 个 chunks")


def _stable_doc_id(filepath: str) -> str:
    """从文件路径生成稳定的 doc_id（基于相对路径，跨机器一致）。"""
    # 去掉常见前缀，保留有意义的路径部分
    p = filepath
    for prefix in ["tests/fixtures/kb-sources/k8s-website/content/en/docs/",
                    "tests/fixtures/kb-sources/redis-docs/content/",
                    "docs/"]:
        if prefix in p:
            p = p[p.index(prefix) + len(prefix):]
            break
    # 用路径的 md5 前 8 位
    return hashlib.md5(p.encode()).hexdigest()[:8]


def parse_file(filepath: str) -> list[dict]:
    """解析单个 Markdown 文件为 chunks（不编码、不写入 Qdrant）。"""
    post = frontmatter.load(filepath)
    doc_id = post.metadata.get("id", _stable_doc_id(filepath))
    title = post.metadata.get("title", os.path.basename(filepath))

    content = _clean_hugo_shortcodes(post.content)
    sections = split_by_headings(content)
    sections = merge_small_sections(sections)

    chunk_data = []
    for i, sec in enumerate(sections):
        chunk_data.append({
            "doc_id": doc_id,
            "chunk_id": f"{doc_id}-{i:03d}",
            "text": sec["text"],
            "metadata": {
                "path": filepath,
                "title": title,
                "section_path": sec["section_path"],
                "chunk_index": i,
                "confidence": post.metadata.get("confidence", "unknown"),
                "tags": post.metadata.get("tags", []),
                "source_repo": post.metadata.get("source_repo", ""),
                "source_path": post.metadata.get("source_path", ""),
                "source_commit": post.metadata.get("source_commit", ""),
            },
        })
    return chunk_data


def index_file(filepath: str) -> int:
    """索引单个 Markdown 文件（解析 + 编码 + 写入）。返回 chunk 数。"""
    post = frontmatter.load(filepath)
    doc_id = post.metadata.get("id", _stable_doc_id(filepath))

    # 先删除旧 chunks
    try:
        delete_doc(doc_id)
    except Exception:
        pass

    chunk_data = parse_file(filepath)
    index_chunks(chunk_data)
    return len(chunk_data)


# ── 全量 / 增量 ──────────────────────────────────────────────────

def index_full(docs_dir: str) -> None:
    """全量重建：先收集所有 chunks，再一次性批量编码 + 写入。"""
    md_files = sorted(Path(docs_dir).rglob("*.md"))
    if not md_files:
        log.info(f"目录 {docs_dir} 下没有 .md 文件")
        return

    log.info(f"全量索引: {len(md_files)} 个文件 ({docs_dir})")

    # Phase 1: 收集所有 doc_id 用于批量删除
    doc_ids: set[str] = set()
    all_chunks: list[dict] = []
    errors = 0

    for f in md_files:
        try:
            chunks = parse_file(str(f))
            if chunks:
                doc_ids.add(chunks[0]["doc_id"])
                all_chunks.extend(chunks)
                log.info(f"  📄 {f} → {len(chunks)} chunks")
        except Exception as e:
            log.error(f"  ❌ {f}: {e}")
            errors += 1

    log.info(f"解析完成: {len(md_files) - errors} 文件, {len(all_chunks)} chunks")

    if not all_chunks:
        return

    # Phase 2: 批量删除旧 chunks
    client = get_qdrant()
    ensure_collection(client)
    for doc_id in doc_ids:
        try:
            client.delete(
                collection_name=COLLECTION,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=[
                        models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))
                    ])
                ),
            )
        except Exception:
            pass
    log.info(f"已清理 {len(doc_ids)} 个旧文档的 chunks")

    # Phase 3: 一次性批量编码 + 写入
    index_chunks(all_chunks)
    log.info(f"✅ 全量索引完成: {len(md_files) - errors} 文件, {len(all_chunks)} chunks")


def index_incremental() -> None:
    """增量更新：基于 git diff 找出变更的 .md 文件。"""
    try:
        # 找出最近一次 commit 到工作区的变更
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", "*.md"],
            capture_output=True, text=True, check=True,
        )
        changed = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

        # 也包括未跟踪的新文件
        result2 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--", "*.md"],
            capture_output=True, text=True, check=True,
        )
        new_files = [f.strip() for f in result2.stdout.strip().split("\n") if f.strip()]

        all_changed = list(set(changed + new_files))
    except subprocess.CalledProcessError:
        log.error("git 命令失败，请确认在 git 仓库中运行")
        return

    if not all_changed:
        log.info("没有变更的 .md 文件")
        return

    log.info(f"增量索引: {len(all_changed)} 个变更文件")
    total_chunks = 0
    for f in all_changed:
        if not os.path.exists(f):
            # 文件被删除，尝试删除索引
            doc_id = hashlib.md5(f.encode()).hexdigest()[:8]
            try:
                delete_doc(doc_id)
                log.info(f"  🗑️ {f} (已删除)")
            except Exception:
                pass
            continue
        try:
            n = index_file(f)
            total_chunks += n
            log.info(f"  {f} → {n} chunks")
        except Exception as e:
            log.error(f"  ❌ {f}: {e}")

    log.info(f"✅ 增量索引完成: {len(all_changed)} 文件, {total_chunks} chunks")


# ── 状态 ──────────────────────────────────────────────────────────

def show_status() -> None:
    """显示索引状态。"""
    client = get_qdrant()
    try:
        info = client.get_collection(COLLECTION)
        log.info(f"Collection: {COLLECTION}")
        log.info(f"  向量数: {info.points_count}")
        log.info(f"  状态: {info.status}")

        # 按 doc_id 统计
        scroll_result = client.scroll(
            collection_name=COLLECTION,
            limit=1000,
            with_payload=["doc_id", "path", "title", "section_path"],
        )
        docs: dict[str, dict] = {}
        for point in scroll_result[0]:
            doc_id = point.payload.get("doc_id", "unknown")
            if doc_id not in docs:
                docs[doc_id] = {
                    "path": point.payload.get("path", ""),
                    "title": point.payload.get("title", ""),
                    "chunks": 0,
                    "has_section_path": False,
                }
            docs[doc_id]["chunks"] += 1
            if point.payload.get("section_path"):
                docs[doc_id]["has_section_path"] = True

        log.info(f"  文档数: {len(docs)}")
        for doc_id, info_d in sorted(docs.items(), key=lambda x: x[1]["path"]):
            sp_tag = "📑" if info_d["has_section_path"] else "📄"
            log.info(f"    {sp_tag} {info_d['path']} ({info_d['chunks']} chunks) [{doc_id}]")
    except Exception:
        log.info(f"Collection '{COLLECTION}' 不存在，运行索引命令创建")


def drop_collection() -> None:
    """删除整个 collection。"""
    client = get_qdrant()
    try:
        client.delete_collection(COLLECTION)
        log.info(f"✅ 已删除 collection: {COLLECTION}")
    except Exception:
        log.info(f"Collection '{COLLECTION}' 不存在，无需删除")


# ── CLI ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="知识库索引工具")
    parser.add_argument("--file", help="索引单个 Markdown 文件")
    parser.add_argument("--full", metavar="DIR", nargs="+", help="全量重建指定目录（支持多个）")
    parser.add_argument("--incremental", action="store_true", help="增量更新（基于 git diff）")
    parser.add_argument("--delete", action="store_true", help="删除文档")
    parser.add_argument("--doc-id", help="要删除的 doc_id")
    parser.add_argument("--delete-by-repo", metavar="REPO_URL", help="按 source_repo 批量删除某仓库的所有 chunks")
    parser.add_argument("--drop", action="store_true", help="删除整个 collection（清空索引）")
    parser.add_argument("--status", action="store_true", help="查看索引状态")
    args = parser.parse_args()

    if args.drop:
        drop_collection()
    elif args.status:
        show_status()
    elif args.delete_by_repo:
        delete_by_source_repo(args.delete_by_repo)
    elif args.delete and args.doc_id:
        delete_doc(args.doc_id)
    elif args.file:
        index_file(args.file)
    elif args.full:
        for d in args.full:
            index_full(d)
    elif args.incremental:
        index_incremental()
    else:
        # 从 stdin 读取 chunks JSON
        data = sys.stdin.read().strip()
        if data:
            chunks = json.loads(data)
            index_chunks(chunks)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
