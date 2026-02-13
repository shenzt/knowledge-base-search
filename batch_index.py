#!/usr/bin/env python3
"""批量索引 K8s 文档"""

import sys
import subprocess
from pathlib import Path

# 要索引的文档列表
docs_to_index = [
    "/home/shenzt/ws/kb-test-k8s-en/content/en/docs/concepts/workloads/pods/pod-lifecycle.md",
    "/home/shenzt/ws/kb-test-k8s-en/content/en/docs/concepts/workloads/pods/init-containers.md",
    "/home/shenzt/ws/kb-test-k8s-en/content/en/docs/concepts/workloads/pods/ephemeral-containers.md",
    "/home/shenzt/ws/kb-test-k8s-en/content/en/docs/concepts/workloads/pods/sidecar-containers.md",
    "/home/shenzt/ws/kb-test-k8s-en/content/en/docs/concepts/workloads/pods/pod-qos.md",
    "/home/shenzt/ws/kb-test-k8s-en/content/en/docs/concepts/workloads/controllers/replicationcontroller.md",
    "/home/shenzt/ws/kb-test-k8s-en/content/en/docs/concepts/workloads/controllers/deployment.md",
    "/home/shenzt/ws/kb-test-k8s-en/content/en/docs/concepts/services-networking/service.md",
    "/home/shenzt/ws/kb-test-k8s-en/content/en/docs/concepts/services-networking/ingress.md",
    "/home/shenzt/ws/kb-test-k8s-en/content/en/docs/concepts/storage/volumes.md",
]

print(f"准备索引 {len(docs_to_index)} 个文档...\n")

success_count = 0
failed_count = 0
failed_docs = []

for i, doc_path in enumerate(docs_to_index, 1):
    doc_file = Path(doc_path)

    if not doc_file.exists():
        print(f"[{i}/{len(docs_to_index)}] ⚠️  文件不存在: {doc_file.name}")
        failed_count += 1
        failed_docs.append((doc_path, "文件不存在"))
        continue

    print(f"[{i}/{len(docs_to_index)}] 索引: {doc_file.name}...", end=" ", flush=True)

    try:
        result = subprocess.run(
            ["python", "scripts/index.py", "--file", str(doc_path)],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            # 从输出中提取 chunks 数量
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
            failed_docs.append((doc_path, result.stderr[:200]))
    except subprocess.TimeoutExpired:
        print("❌ 超时")
        failed_count += 1
        failed_docs.append((doc_path, "索引超时"))
    except Exception as e:
        print(f"❌ 错误: {e}")
        failed_count += 1
        failed_docs.append((doc_path, str(e)))

print(f"\n{'='*80}")
print(f"索引完成!")
print(f"{'='*80}")
print(f"✅ 成功: {success_count}/{len(docs_to_index)}")
print(f"❌ 失败: {failed_count}/{len(docs_to_index)}")

if failed_docs:
    print(f"\n失败的文档:")
    for doc, reason in failed_docs:
        print(f"  - {Path(doc).name}: {reason}")

sys.exit(0 if failed_count == 0 else 1)
