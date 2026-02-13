# E2E 测试和评测系统

**版本**: v1.0
**日期**: 2025-02-13

---

## 概述

完整的端到端测试和评测系统，用于验证双层 Claude 架构和 Agentic RAG 的效果。

---

## 组件

### 1. 测试用例配置 (`eval/test_cases.json`)

**22 个测试用例**，覆盖 5 个测试套件：

| 套件 | 用例数 | 描述 |
|------|--------|------|
| basic_search | 5 | 基础检索 - 简单单文档查询 |
| cross_language | 3 | 跨语言检索 - 中英文互查 |
| complex_reasoning | 4 | 复杂推理 - 多文档综合 |
| technical_details | 5 | 技术细节 - 精确信息 |
| edge_cases | 3 | 边界情况 - 鲁棒性测试 |

**测试用例结构**:
```json
{
  "id": "basic-001",
  "query": "What is a Pod in Kubernetes?",
  "language": "en",
  "category": "k8s-basic",
  "expected_keywords": ["pod", "container", "smallest"],
  "min_score": 0.5,
  "expected_doc": "pods/_index.md"
}
```

### 2. E2E 测试运行器 (`test_e2e.py`)

**功能**:
- 从配置文件加载测试用例
- 调用 Sonnet Worker 执行检索
- 评估关键词覆盖率
- 统计性能指标
- 保存测试结果 (JSON)

**使用方式**:
```bash
python test_e2e.py
```

**输出**:
- 实时测试进度
- 总体统计
- 分类统计
- 失败用例详情
- Token 使用统计
- 结果文件: `eval/e2e_results_YYYYMMDD_HHMMSS.json`

### 3. 报告生成器 (`generate_e2e_report.py`)

**功能**:
- 加载最新测试结果
- 生成详细 Markdown 报告
- 分析失败原因
- 提供改进建议

**使用方式**:
```bash
python generate_e2e_report.py
```

**报告内容**:
- 📊 总体统计
- ⏱️ 性能统计
- 📈 分类统计
- 🌍 语言统计
- 🔍 关键词覆盖率分析
- ❌ 失败用例详情
- ✅ 优秀用例
- 💡 改进建议

### 4. 优化的 Search Skill (`kb_skills/search/SKILL.md`)

**改进**:
- ✅ 智能三层检索策略
- ✅ 跨语言检索支持
- ✅ 多文档推理指导
- ✅ 结构化回答要求
- ✅ 上下文扩展技巧
- ✅ 性能优化建议

**三层检索策略**:
```
第一层: 快速关键词检索 (Grep/Glob) - 0 成本
第二层: 混合向量检索 (Dense+Sparse+RRF) - 语义理解
第三层: 多文档推理 - 复杂问题
```

---

## 测试覆盖

### 基础检索 (5 个用例)
- ✅ K8s Pod 概念
- ✅ K8s Service 概念
- ✅ K8s Deployment 工作原理
- ✅ Redis 管道技术
- ✅ K8s Volume 概念

### 跨语言检索 (3 个用例)
- ✅ 英文查询 → 中文文档
- ✅ 中文查询 → 英文文档
- ✅ 混合语言场景

### 复杂推理 (4 个用例)
- ✅ 故障排查 (CrashLoopBackOff)
- ✅ 对比分析 (Deployment vs StatefulSet)
- ✅ 最佳实践 (Redis 性能优化)
- ✅ 容器类型对比 (Init vs Sidecar)

### 技术细节 (5 个用例)
- ✅ Service 类型
- ✅ Volume 类型
- ✅ Ingress 路由
- ✅ Pod QoS
- ✅ Redis 客户端

### 边界情况 (3 个用例)
- ✅ 模糊查询
- ✅ 超出范围查询
- ✅ 仅关键词查询

---

## 评估标准

### 关键词覆盖率
- **优秀**: 80%+
- **良好**: 60-80%
- **一般**: 40-60%
- **较差**: <40%

### 响应时间
- **快速**: < 1.0s
- **正常**: 1.0-3.0s
- **较慢**: > 3.0s

### 相关性得分
- **高度相关**: > 0.7
- **相关**: 0.5-0.7
- **可能相关**: 0.3-0.5
- **不相关**: < 0.3

---

## 工作流程

### 1. 运行测试
```bash
# 运行完整测试套件
python test_e2e.py

# 输出示例:
# ================================================================================
# 测试用例: basic-001
# 查询: What is a Pod in Kubernetes?
# ================================================================================
# ✅ 状态: 通过
# ⏱️  耗时: 0.85s
# 📊 关键词覆盖: 100% (4/4)
# 🔍 找到的关键词: pod, container, smallest, deployable
```

### 2. 生成报告
```bash
# 生成详细报告
python generate_e2e_report.py

# 输出: eval/e2e_report_YYYYMMDD_HHMMSS.md
```

### 3. 分析结果
```bash
# 查看报告
cat eval/e2e_report_*.md

# 或在编辑器中打开
code eval/e2e_report_*.md
```

### 4. 优化改进
根据报告中的改进建议：
- 调整 KB Skills
- 优化检索策略
- 改进文档分块
- 调整参数配置

### 5. 重新测试
```bash
# 验证改进效果
python test_e2e.py
python generate_e2e_report.py
```

---

## 扩展测试用例

### 添加新测试用例

编辑 `eval/test_cases.json`:

```json
{
  "test_suites": {
    "your_suite": {
      "description": "你的测试套件描述",
      "test_cases": [
        {
          "id": "your-001",
          "query": "你的查询",
          "language": "zh",
          "category": "your-category",
          "expected_keywords": ["关键词1", "关键词2"],
          "min_score": 0.5
        }
      ]
    }
  }
}
```

### 测试用例最佳实践

1. **明确的期望关键词**: 选择能代表正确答案的关键词
2. **合理的 min_score**: 根据查询难度设置阈值
3. **清晰的分类**: 便于统计和分析
4. **覆盖边界情况**: 测试系统鲁棒性

---

## 性能基准

### 目标指标

| 指标 | 目标 | 当前 |
|------|------|------|
| 总体通过率 | > 80% | 待测试 |
| 基础检索通过率 | > 90% | 待测试 |
| 跨语言通过率 | > 70% | 待测试 |
| 平均响应时间 | < 2.0s | 待测试 |
| 关键词覆盖率 | > 60% | 待测试 |

### 成本估算

- **每次完整测试**: ~22 个查询
- **预估 Token**: ~50,000 tokens
- **预估成本**: ~$0.15 (Sonnet 定价)

---

## 持续改进

### 监控指标

1. **通过率趋势**: 跟踪每次测试的通过率
2. **性能趋势**: 监控响应时间变化
3. **成本趋势**: 跟踪 Token 使用量
4. **失败模式**: 分析常见失败原因

### 优化循环

```
运行测试
    ↓
生成报告
    ↓
分析失败原因
    ↓
优化 KB Skills / 调整参数
    ↓
重新测试
    ↓
对比改进效果
```

---

## 文件清单

```
eval/
├── test_cases.json           # 测试用例配置
├── e2e_results_*.json        # 测试结果 (自动生成)
└── e2e_report_*.md           # 测试报告 (自动生成)

test_e2e.py                   # E2E 测试运行器
generate_e2e_report.py        # 报告生成器

kb_skills/search/SKILL.md     # 优化的 Search Skill
```

---

## 下一步

1. ✅ 运行首次完整测试
2. ⏳ 分析测试结果
3. ⏳ 根据报告优化 KB Skills
4. ⏳ 重新测试验证改进
5. ⏳ 建立持续测试流程

---

**E2E 测试系统已就绪！** 🎉

可以开始运行测试并持续优化 Agentic RAG 系统了。
