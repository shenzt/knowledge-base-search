#!/usr/bin/env python3
"""构建知识库分层索引"""

import json
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import hashlib

def extract_frontmatter(md_file):
    """提取 Markdown 文件的 front-matter"""
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否有 front-matter
        if not content.startswith('---'):
            return None

        # 提取 front-matter
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None

        frontmatter_str = parts[1].strip()

        # 解析 YAML
        try:
            frontmatter = yaml.safe_load(frontmatter_str)
            return frontmatter
        except:
            return None
    except Exception as e:
        print(f"  警告: 无法读取 {md_file.name} - {e}")
        return None

def generate_doc_id(file_path):
    """为没有 ID 的文档生成 ID"""
    # 使用文件路径的哈希
    path_str = str(file_path)
    return hashlib.md5(path_str.encode()).hexdigest()[:8]

def build_index(docs_dir):
    """构建分层索引"""
    docs_dir = Path(docs_dir)

    if not docs_dir.exists():
        print(f"错误: 目录不存在 - {docs_dir}")
        return None

    print(f"扫描目录: {docs_dir}")

    # 查找所有 Markdown 文件
    md_files = list(docs_dir.rglob("*.md"))
    print(f"找到 {len(md_files)} 个 Markdown 文件\n")

    # 构建索引结构
    index = {
        "generated": datetime.now().isoformat(),
        "total_docs": 0,
        "structure": {},
        "tags_index": defaultdict(list),
        "categories": defaultdict(int),
        "confidence_levels": defaultdict(int)
    }

    # 处理每个文档
    for i, md_file in enumerate(md_files, 1):
        if i % 10 == 0:
            print(f"处理中... {i}/{len(md_files)}")

        # 提取 front-matter
        frontmatter = extract_frontmatter(md_file)

        # 计算相对路径
        rel_path = md_file.relative_to(docs_dir)
        dir_path = str(rel_path.parent) if rel_path.parent != Path('.') else "root"

        # 确保目录存在于结构中
        if dir_path not in index["structure"]:
            index["structure"][dir_path] = {
                "path": str(docs_dir / dir_path),
                "count": 0,
                "documents": []
            }

        # 构建文档条目
        doc_entry = {
            "path": str(rel_path),
            "full_path": str(md_file)
        }

        if frontmatter:
            doc_entry["id"] = frontmatter.get("id", generate_doc_id(rel_path))
            doc_entry["title"] = frontmatter.get("title", md_file.stem)
            doc_entry["tags"] = frontmatter.get("tags", [])
            doc_entry["confidence"] = frontmatter.get("confidence", "unknown")
            doc_entry["category"] = frontmatter.get("category", "uncategorized")
            doc_entry["last_reviewed"] = frontmatter.get("last_reviewed", "")

            # 更新标签索引
            for tag in doc_entry["tags"]:
                index["tags_index"][tag].append(doc_entry["id"])

            # 更新分类统计
            index["categories"][doc_entry["category"]] += 1

            # 更新置信度统计
            index["confidence_levels"][doc_entry["confidence"]] += 1
        else:
            # 没有 front-matter
            doc_entry["id"] = generate_doc_id(rel_path)
            doc_entry["title"] = md_file.stem
            doc_entry["tags"] = []
            doc_entry["confidence"] = "unknown"
            doc_entry["category"] = "uncategorized"
            doc_entry["last_reviewed"] = ""

            index["confidence_levels"]["unknown"] += 1
            index["categories"]["uncategorized"] += 1

        # 添加到结构
        index["structure"][dir_path]["documents"].append(doc_entry)
        index["structure"][dir_path]["count"] += 1
        index["total_docs"] += 1

    # 转换 defaultdict 为普通 dict
    index["tags_index"] = dict(index["tags_index"])
    index["categories"] = dict(index["categories"])
    index["confidence_levels"] = dict(index["confidence_levels"])

    print(f"\n✅ 索引构建完成!")
    print(f"   总文档数: {index['total_docs']}")
    print(f"   目录数: {len(index['structure'])}")
    print(f"   标签数: {len(index['tags_index'])}")

    return index

def save_json_index(index, output_path):
    """保存 JSON 格式索引"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON 索引已保存: {output_path}")

def save_markdown_index(index, output_path):
    """保存 Markdown 格式索引"""
    lines = []

    lines.append("# 知识库索引\n")
    lines.append(f"> 生成时间: {index['generated']}\n")
    lines.append(f"> 总文档数: {index['total_docs']}\n")
    lines.append("\n## 目录结构\n")

    # 按目录组织
    for dir_path, dir_info in sorted(index["structure"].items()):
        lines.append(f"\n### {dir_path}/ ({dir_info['count']} 篇)\n")

        for doc in dir_info["documents"]:
            confidence_icon = {
                "high": "⭐",
                "medium": "📝",
                "low": "⚠️",
                "deprecated": "❌",
                "unknown": "❓"
            }.get(doc["confidence"], "")

            tags_str = " ".join([f"`#{tag}`" for tag in doc["tags"]]) if doc["tags"] else ""
            lines.append(f"- [{doc['title']}]({doc['path']}) {confidence_icon} {tags_str}\n")

    # 标签索引
    if index["tags_index"]:
        lines.append("\n## 按标签分类\n")
        for tag, doc_ids in sorted(index["tags_index"].items()):
            lines.append(f"\n### #{tag} ({len(doc_ids)} 篇)\n")

    # 统计信息
    lines.append("\n## 统计信息\n")

    lines.append("\n### 按分类\n")
    for category, count in sorted(index["categories"].items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- {category}: {count} 篇\n")

    lines.append("\n### 按置信度\n")
    for confidence, count in sorted(index["confidence_levels"].items(), key=lambda x: x[1], reverse=True):
        icon = {"high": "⭐", "medium": "📝", "low": "⚠️", "deprecated": "❌", "unknown": "❓"}.get(confidence, "")
        lines.append(f"- {icon} {confidence}: {count} 篇\n")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"✅ Markdown 索引已保存: {output_path}")

def main():
    import sys

    if len(sys.argv) < 2:
        print("用法: python build_index.py <文档目录>")
        sys.exit(1)

    docs_dir = sys.argv[1]

    # 构建索引
    index = build_index(docs_dir)

    if not index:
        sys.exit(1)

    # 保存索引
    output_dir = Path(docs_dir)
    save_json_index(index, output_dir / "index.json")
    save_markdown_index(index, output_dir / "INDEX.md")

    print(f"\n{'='*80}")
    print("索引构建完成!")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
