#!/usr/bin/env python3
"""转换 Redis HTML 文档为 Markdown"""

import os
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime

def generate_doc_id(file_path):
    """生成稳定的文档 ID"""
    # 基于文件路径生成 ID
    path_str = str(file_path).replace('cn/', '').replace('.html', '')
    # 转换为小写，替换特殊字符
    doc_id = path_str.replace('/', '-').replace('_', '-').lower()
    return f"redis-{doc_id}"

def extract_title_from_html(html_path):
    """从 HTML 提取标题"""
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 简单提取 <title> 标签
            if '<title>' in content and '</title>' in content:
                start = content.find('<title>') + 7
                end = content.find('</title>')
                title = content[start:end].strip()
                # 移除 " - Redis" 后缀
                if ' - Redis' in title:
                    title = title.replace(' - Redis', '')
                return title
            # 尝试提取第一个 <h1>
            if '<h1>' in content and '</h1>' in content:
                start = content.find('<h1>') + 4
                end = content.find('</h1>')
                return content[start:end].strip()
    except Exception as e:
        print(f"  警告: 无法提取标题 - {e}")

    # 使用文件名作为标题
    return Path(html_path).stem.replace('-', ' ').title()

def convert_html_to_md(html_path, output_path):
    """使用 pandoc 转换 HTML 到 Markdown"""
    try:
        result = subprocess.run(
            ['pandoc', '-f', 'html', '-t', 'markdown', str(html_path), '-o', str(output_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  错误: {e}")
        return False

def add_frontmatter(md_path, html_path, doc_id, title):
    """添加 front-matter"""
    try:
        # 读取转换后的内容
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 生成 front-matter
        frontmatter = f"""---
id: "{doc_id}"
title: "{title}"
source_file: "{html_path}"
converted_at: "{datetime.now().isoformat()}"
converter: "pandoc"
confidence: medium
tags: [redis]
category: "documentation"
---

"""

        # 写回文件
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter + content)

        return True
    except Exception as e:
        print(f"  错误: 添加 front-matter 失败 - {e}")
        return False

def main():
    base_dir = Path('/home/shenzt/ws/kb-test-redis-cn')
    html_dir = base_dir / 'cn'
    output_dir = base_dir / 'docs'

    # 创建输出目录
    output_dir.mkdir(exist_ok=True)

    # 查找所有 HTML 文件
    html_files = list(html_dir.rglob('*.html'))

    # 只转换前 10 个作为测试
    html_files = html_files[:10]

    print(f"准备转换 {len(html_files)} 个 HTML 文件...\n")

    success_count = 0
    failed_count = 0

    for i, html_path in enumerate(html_files, 1):
        # 计算相对路径
        rel_path = html_path.relative_to(html_dir)

        # 生成输出路径
        md_rel_path = rel_path.with_suffix('.md')
        md_path = output_dir / md_rel_path

        # 创建输出目录
        md_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"[{i}/{len(html_files)}] {rel_path}", end=" ", flush=True)

        # 提取标题
        title = extract_title_from_html(html_path)

        # 生成文档 ID
        doc_id = generate_doc_id(rel_path)

        # 转换
        if convert_html_to_md(html_path, md_path):
            # 添加 front-matter
            if add_frontmatter(md_path, str(rel_path), doc_id, title):
                print(f"✅ → {md_rel_path}")
                success_count += 1
            else:
                print(f"⚠️  转换成功但 front-matter 失败")
                success_count += 1
        else:
            print(f"❌ 转换失败")
            failed_count += 1

    print(f"\n{'='*80}")
    print(f"转换完成!")
    print(f"{'='*80}")
    print(f"✅ 成功: {success_count}/{len(html_files)}")
    print(f"❌ 失败: {failed_count}/{len(html_files)}")
    print(f"\n输出目录: {output_dir}")

if __name__ == '__main__':
    main()
