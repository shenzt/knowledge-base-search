# 重建索引 + 评测改进计划

## 现状

- K8s 源文档: 164 个 .md，当前只索引了 11 个（手选的核心概念）
- Redis 源文档: 11 个 .md，全部已索引（但多数是 meta 页面如 download/community/support）
- 本地 docs/: 3 个技术文档，已用新 heading-based chunking 索引
- 旧索引: K8s/Redis 用旧的固定大小分块，无 section_path

## 计划

### Step 1: 清空 Qdrant，用新 chunking 全量重建索引

```bash
# 1. 删除 collection
# 2. 用 index.py --full 重新索引所有源文档
#    - ~/ws/kb-test-k8s-en/ (选择核心文档，不是全部 164 个)
#    - ~/ws/kb-test-redis-cn/docs/topics/ (有实际内容的)
#    - docs/ (本地 3 个)
# 3. 验证 --status
```

注意: 不索引全部 164 个 K8s 文档。很多是 _index.md 目录页或边缘内容。
选择策略: 索引当前测试用例覆盖的 + 一些额外的核心文档。

### Step 2: 创建 eval skill

`.claude/skills/eval/SKILL.md` — 定义评测流程:
- 触发: `/eval [--full|--quick|--mcp]`
- 行为: 运行 test_agentic_rag_sdk.py，分析结果，输出改进建议
- 依赖: eval_module.py 的 Gate + Quality 评估

### Step 3: 运行评测，分析结果

- USE_MCP=0 跑一次（测 Grep/Glob/Read 对本地 docs/）
- USE_MCP=1 跑一次（测 hybrid_search 对 Qdrant）
- 对比两次结果，发现问题

### Step 4: 引入真实问题

从 StackOverflow/GitHub Issues 收集真实问题，扩充测试用例:
- K8s 常见问题 (CrashLoopBackOff, ImagePullBackOff, OOMKilled 等)
- Redis 常见问题 (连接超时, 内存满, 主从切换等)
- 这些问题的答案必须能在我们索引的文档中找到

### Step 5: 固化发现到 skills

根据评测中发现的问题，更新:
- search skill: 改进检索策略
- CLAUDE.md: 更新约束
- testing-lessons.md: 新的经验教训
