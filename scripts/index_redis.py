#!/usr/bin/env python3
"""索引 Redis 中文文档"""

import sys
import subprocess
from pathlib import Path

# Redis 文档目录
redis_docs_dir = Path("/home/shenzt/ws/kb-test-redis-cn/docs")

# 查找所有 MD 文件
md_files = list(redis_docs_dir.rglob("*.md"))

print(f"找到 {len(md_files)} 个 Markdown 文件")
print(f"准备索引...\n")

success_count = 0
failed_count = 0

for i, md_file in enumerate(md_files, 1):
    rel_path = md_file.relative_to(redis_docs_dir)
    print(f"[{i}/{len(md_files)}] 索引: {rel_path}...", end=" ", flush=True)

    try:
        result = subprocess.run(
            ["python", "scripts/index.py", "--file", str(md_file)],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            output = result.stdout + result.stderr
            if "已索引" in output:
                chunks_line = [line for line in output.split('\n') if '已索引' in line]
                if chunks_line:
                    print(f"✅ {chunks_line[-1].strip()}")
                else:
                    print("✅ 成功")
            else:
                print("✅ 成功")
            success_count += 1
        else:
            print(f"❌ 失败")
            failed_count += 1
    except Exception as e:
        print(f"❌ 错误: {e}")
        failed_count += 1

print(f"\n{'='*80}")
print(f"索引完成!")
print(f"{'='*80}")
print(f"✅ 成功: {success_count}/{len(md_files)}")
print(f"❌ 失败: {failed_count}/{len(md_files)}")
