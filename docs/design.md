# 基于 Git + 向量检索 + Claude Code Agent 的中文知识库检索系统 — 设计文档

> 版本: v0.2 | 日期: 2025-07
> 状态: 方案调研 & 架构设计
> 部署模式: 纯本地（所有组件本地运行，仅首次下载模型/镜像需联网）

---

## 1. 背景与动机

团队工程文档（Runbook、ADR、API 文档、事后复盘、会议纪要等）散落各处，缺乏统一检索入口。目标：

- Git 仓库作为文档单一事实源（SSOT）：版本化、PR 审核、可追溯、可回滚
- 本地混合检索（关键词 + 语义），对中文有一流支持
- AI Agent 自动编排"问题 → 检索 → 取证 → 归纳 → 带引用输出"的完整流程

---

## 2. 方案对比与选型

### 2.1 QMD 方案（原始方案）— 不推荐用于中文场景

QMD 是 Tobi Lütke 开源的本地文档搜索引擎，架构精巧（BM25 + 向量 + query expansion + rerank），但存在中文硬伤：

| 问题 | 详情 |
|------|------|
| Embedding 模型 | embeddinggemma-300M，以英文训练为主，中文语义表示质量未知 |
| BM25 分词 | SQLite FTS5 默认 tokenizer 不做中文分词，逐字切分或 trigram，召回率差 |
| Query Expansion | fine-tuned Qwen3-1.7B，虽然 Qwen 系列支持中文，但该微调数据集未公开，中文扩展质量不确定 |
| Reranker | Qwen3-Reranker-0.6B，中文能力相对可靠，但上游召回差则无用 |
| 不可替换模型 | 模型硬编码在代码中，无法换成中文专用模型 |

结论：QMD 适合英文 Markdown 知识库，中文场景需要另选方案。

### 2.2 向量数据库对比

| 维度 | Qdrant | ChromaDB |
|------|--------|----------|
| 部署方式 | Docker / 二进制 / Python 嵌入式 | pip install / Docker / 嵌入式 |
| 中文向量检索 | ✅ 模型无关，支持任意 embedding | ✅ 模型无关，支持任意 embedding |
| 中文全文检索 | ✅ `multilingual` tokenizer（基于 charabia/jieba） | ❌ 仅 substring match，无分词 |
| 混合检索 | ✅ 原生支持 dense + sparse + RRF/DBSF 融合 | ❌ 无 BM25，无混合检索 |
| 稀疏向量 | ✅ 原生支持（配合 BGE-M3 的 learned sparse） | ❌ 不支持 |
| MCP Server | ✅ 官方 `qdrant/mcp-server-qdrant`（1.2k stars） | ✅ 官方 `chroma-core/chroma-mcp`（491 stars） |
| 资源占用 | 10K 文档 ~100MB RAM | 10K 文档 ~100MB RAM |
| 成熟度 | 22k stars，Rust 实现，生产级 | 26k stars，Rust 核心，广泛采用 |

### 2.3 中文 Embedding 模型对比

| 模型 | 维度 | 最大 Token | 参数量 | C-MTEB 均分 | 特点 |
|------|------|-----------|--------|------------|------|
| BAAI/bge-large-zh-v1.5 | 1024 | 512 | 326M | **64.53** | 纯中文最强 |
| BAAI/bge-m3 | 1024 | **8192** | 568M | ~62-63 | 多语言 + 长文档 + 内置 dense/sparse/ColBERT |
| moka-ai/m3e-base | 768 | 512 | 110M | ~57-58 | 轻量中文，性价比高 |
| intfloat/multilingual-e5-large | 1024 | 512 | 560M | ~60-61 | 100+ 语言覆盖 |
| shibing624/text2vec-base-chinese | 768 | 128 | 102M | ~47-51 | 最轻量，但 128 token 限制太短 |

### 2.4 最终选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 文档源 | Git 仓库 | 版本化、可审核、可追溯 |
| 向量数据库 | **Qdrant**（本地 Docker 或嵌入式） | 原生混合检索（dense + sparse + RRF），中文全文索引支持 |
| Embedding 模型 | **BAAI/bge-m3** | 8K 上下文、单模型输出 dense + sparse + ColBERT、中文表现优秀 |
| Reranker | **BAAI/bge-reranker-v2-m3** | 同系列，中文 rerank 效果好 |
| 中文 BM25 | BGE-M3 的 learned sparse 向量（替代传统 jieba + BM25） | 无需额外分词管线 |
| Agent 编排 | Claude Code + MCP | 原生 MCP 协议，CLAUDE.md 规约控制行为 |
| MCP Server | 自建薄层（包装 Qdrant hybrid search API） | 官方 MCP Server 仅支持 dense search，需扩展 |

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户 / IDE                            │
│              (Claude Code / Terminal)                    │
└──────────────────────┬──────────────────────────────────┘
                       │ 自然语言问题
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Claude Code Agent (编排层)                   │
│                                                         │
│  CLAUDE.md 检索规约:                                      │
│  1. 优先调用 MCP 工具检索，不要 Glob/Grep 全仓库           │
│  2. hybrid_search → get_document → 归纳回答               │
│  3. 回答必须带 source + chunk_id 引用                     │
└──────────────────────┬──────────────────────────────────┘
                       │ MCP 协议 (stdio / HTTP)
                       ▼
┌─────────────────────────────────────────────────────────┐
│           自建 MCP Server (检索层 / Python)               │
│                                                         │
│  工具:                                                   │
│  - hybrid_search: dense + sparse 混合检索 + rerank       │
│  - keyword_search: 纯关键词检索（Qdrant 全文索引）         │
│  - get_document: 按 ID/路径取完整文档                     │
│  - list_collections: 列出可用知识库                       │
│  - index_status: 索引健康状态                             │
│                                                         │
│  内部组件:                                               │
│  - BGE-M3 encoder (dense + sparse)                      │
│  - BGE-Reranker-v2-M3                                   │
│  - Qdrant client                                        │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API / gRPC
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Qdrant (存储层 / Docker 或嵌入式)             │
│                                                         │
│  Collection: knowledge-base                              │
│  ├── dense vectors (1024d, cosine)                       │
│  ├── sparse vectors (BGE-M3 lexical weights)             │
│  ├── full-text index (multilingual tokenizer)            │
│  └── payload: path, title, owner, tags, chunk_id, ...   │
└──────────────────────┬──────────────────────────────────┘
                       │ 文件系统读取
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Git 知识库仓库 (数据层)                       │
│                                                         │
│  /docs                                                   │
│    ├── runbook/        运维手册                           │
│    ├── adr/            架构决策记录                       │
│    ├── api/            API 文档                          │
│    ├── postmortem/     事后复盘                           │
│    └── meeting-notes/  会议纪要                           │
└─────────────────────────────────────────────────────────┘
```

### 检索管线

```
用户查询
  │
  ▼
BGE-M3 编码 ──→ dense vector (1024d) + sparse vector (lexical weights)
  │
  ▼
Qdrant Hybrid Search
  ├── Prefetch: dense top-20 (cosine similarity)
  ├── Prefetch: sparse top-20 (dot product)
  └── Fusion: RRF (Reciprocal Rank Fusion)
  │
  ▼
Top-10 候选 chunks
  │
  ▼
BGE-Reranker-v2-M3 重排序
  │
  ▼
Top-5 最终结果（含 path、chunk_id、score）
```

### 纯本地部署说明

所有组件均在本地运行，无需云端服务：

| 组件 | 运行位置 | 联网需求 |
|------|---------|---------|
| Qdrant | 本地 Docker 或 Python 嵌入式（写本地磁盘） | 仅首次拉取镜像 |
| BGE-M3 | 本地 Python 进程，HuggingFace 模型缓存 (~2GB) | 仅首次下载模型 |
| BGE-Reranker | 本地 Python 进程，HuggingFace 模型缓存 (~1.2GB) | 仅首次下载模型 |
| MCP Server | 本地 Python 进程，stdio/localhost HTTP | 无 |
| Git 仓库 | 本地文件系统 | 仅 git pull 时 |
| Claude Code | 本地 IDE/CLI | 调用 Anthropic API（这是唯一持续联网的部分） |

> 注意：Claude Code 本身需要调用 Anthropic API，这是整个方案中唯一需要持续联网的部分。
> 检索管线（编码 → 搜索 → 重排序）完全离线。

---

## 4. 详细设计

### 4.1 知识库 Git 仓库规范

#### 目录结构

```
knowledge-base-search/
├── docs/
│   ├── design.md          # 本设计文档
│   ├── runbook/           # 运维手册
│   ├── adr/               # 架构决策记录
│   ├── api/               # API 文档
│   ├── postmortem/        # 事后复盘
│   └── meeting-notes/     # 会议纪要
├── scripts/
│   ├── index.py           # 索引构建/更新脚本
│   ├── mcp_server.py      # 自建 MCP Server
│   └── requirements.txt   # Python 依赖
├── CLAUDE.md              # Agent 检索行为规约
├── .gitignore
└── README.md
```

#### 文档 Front-matter 规范

```yaml
---
title: "xxx 服务故障处理手册"
owner: "@zhangsan"
tags: [runbook, service-xxx, on-call]
created: 2025-01-15
last_reviewed: 2025-06-01
confidence: high          # high / medium / low / deprecated
---
```

### 4.2 索引构建（index.py 核心逻辑）

```python
from FlagEmbedding import BGEM3FlagModel
from qdrant_client import QdrantClient, models
import frontmatter, glob, hashlib

# 初始化
model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
qdrant = QdrantClient("localhost", port=6333)

# 创建 collection（首次）
qdrant.create_collection(
    collection_name="knowledge-base",
    vectors_config={
        "dense": models.VectorParams(size=1024, distance=models.Distance.COSINE),
    },
    sparse_vectors_config={
        "sparse": models.SparseVectorParams(),
    },
)

# 创建中文全文索引
qdrant.create_payload_index(
    collection_name="knowledge-base",
    field_name="content",
    field_schema=models.TextIndexParams(
        type="text",
        tokenizer=models.TokenizerType.MULTILINGUAL,  # charabia/jieba
        min_token_len=1,
        max_token_len=20,
    ),
)

def chunk_markdown(text: str, max_chars: int = 3200, overlap: int = 480) -> list[str]:
    """按段落/句子边界切分，3200 字符 (~800 token)，15% 重叠"""
    # 优先在 \n\n → \n → 。→ 空格 处切分
    ...

def index_file(filepath: str):
    post = frontmatter.load(filepath)
    chunks = chunk_markdown(post.content)

    # BGE-M3 同时输出 dense + sparse
    output = model.encode(chunks, return_dense=True, return_sparse=True)

    points = []
    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{filepath}:{i}".encode()).hexdigest()
        sparse = output["lexical_weights"][i]

        points.append(models.PointStruct(
            id=chunk_id,
            vector={
                "dense": output["dense_vecs"][i].tolist(),
                "sparse": models.SparseVector(
                    indices=list(sparse.keys()),
                    values=list(sparse.values()),
                ),
            },
            payload={
                "content": chunk,
                "path": filepath,
                "chunk_index": i,
                "title": post.metadata.get("title", ""),
                "owner": post.metadata.get("owner", ""),
                "tags": post.metadata.get("tags", []),
                "confidence": post.metadata.get("confidence", "unknown"),
                "last_reviewed": post.metadata.get("last_reviewed", ""),
            },
        ))

    qdrant.upsert(collection_name="knowledge-base", points=points)

# 索引所有文档
for f in glob.glob("docs/**/*.md", recursive=True):
    index_file(f)
```

### 4.3 自建 MCP Server（mcp_server.py 核心逻辑）

使用 `mcp` Python SDK 构建，暴露 5 个工具：

```python
from mcp.server import Server
from mcp.types import Tool, TextContent
from FlagEmbedding import BGEM3FlagModel, FlagReranker
from qdrant_client import QdrantClient, models

app = Server("knowledge-base-search")
model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
qdrant = QdrantClient("localhost", port=6333)

@app.tool()
async def hybrid_search(query: str, top_k: int = 5, min_score: float = 0.3,
                         collection: str = "knowledge-base",
                         scope: str = None) -> str:
    """混合检索：dense + sparse + RRF + rerank"""
    # 1. 编码查询
    q = model.encode([query], return_dense=True, return_sparse=True)
    dense_vec = q["dense_vecs"][0].tolist()
    sparse = q["lexical_weights"][0]
    sparse_vec = models.SparseVector(
        indices=list(sparse.keys()), values=list(sparse.values())
    )

    # 2. 构造过滤条件（按 scope 过滤目录）
    filter_cond = None
    if scope:
        filter_cond = models.Filter(must=[
            models.FieldCondition(key="path", match=models.MatchText(text=f"/{scope}/"))
        ])

    # 3. Qdrant hybrid search (dense + sparse + RRF)
    results = qdrant.query_points(
        collection_name=collection,
        prefetch=[
            models.Prefetch(query=dense_vec, using="dense", limit=20, filter=filter_cond),
            models.Prefetch(query=sparse_vec, using="sparse", limit=20, filter=filter_cond),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=top_k * 2,
    )

    # 4. Rerank
    if results.points:
        pairs = [(query, p.payload["content"]) for p in results.points]
        scores = reranker.compute_score(pairs)
        ranked = sorted(zip(results.points, scores), key=lambda x: -x[1])
        ranked = [(p, s) for p, s in ranked if s >= min_score][:top_k]

    # 5. 格式化输出
    output = []
    for point, score in ranked:
        output.append({
            "score": round(score, 4),
            "path": point.payload["path"],
            "chunk_index": point.payload["chunk_index"],
            "title": point.payload.get("title", ""),
            "confidence": point.payload.get("confidence", ""),
            "content_preview": point.payload["content"][:500],
        })
    return json.dumps(output, ensure_ascii=False, indent=2)

@app.tool()
async def keyword_search(query: str, top_k: int = 10,
                          collection: str = "knowledge-base") -> str:
    """纯关键词检索（Qdrant multilingual 全文索引）"""
    ...

@app.tool()
async def get_document(path: str, collection: str = "knowledge-base") -> str:
    """按路径获取文档所有 chunks 的完整内容"""
    ...

@app.tool()
async def list_collections() -> str:
    """列出所有可用知识库集合"""
    ...

@app.tool()
async def index_status(collection: str = "knowledge-base") -> str:
    """索引健康状态：文档数、向量数、最后更新时间"""
    ...
```

#### MCP 配置（~/.claude/settings.json）

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "python",
      "args": ["/path/to/scripts/mcp_server.py"],
      "env": {
        "QDRANT_URL": "http://localhost:6333"
      }
    }
  }
}
```

### 4.4 索引更新策略

| 策略 | 实现方式 | 适用场景 |
|------|---------|---------|
| 手动更新 | `python scripts/index.py` | 开发者本地，按需 |
| Git Hook | `post-merge` hook 触发增量更新 | 每次 git pull 后自动更新 |
| 定时任务 | cron 每日执行 | 低频更新的知识库 |

增量更新逻辑：对比 git diff 获取变更文件列表，仅重新索引变更文件，删除已移除文件的 chunks。

---

## 5. 与 QMD 方案的对比总结

| 维度 | QMD 方案 | 本方案（Qdrant + BGE-M3） |
|------|---------|--------------------------|
| 中文 BM25 | ❌ FTS5 无中文分词 | ✅ BGE-M3 learned sparse + Qdrant multilingual |
| 中文语义检索 | ⚠️ embeddinggemma 中文未验证 | ✅ BGE-M3 C-MTEB ~62-63 |
| 混合检索 | ✅ 内置 RRF | ✅ Qdrant 原生 RRF/DBSF |
| Rerank | ✅ Qwen3-Reranker | ✅ BGE-Reranker-v2-M3（中文更强） |
| 模型可替换 | ❌ 硬编码 | ✅ 任意 HuggingFace 模型 |
| 部署复杂度 | 低（单 CLI） | 中（Qdrant + Python MCP Server） |
| MCP 集成 | ✅ 原生 | ✅ 自建（更灵活） |
| 适合场景 | 英文 Markdown | 中文/多语言文档 |

---

## 6. 已知风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| BGE-M3 模型较大（~568M 参数，~2GB 磁盘） | 可降级为 m3e-base（110M）牺牲精度换速度 |
| Qdrant 需要额外运维（Docker） | 可用 Python 嵌入式模式（无需 Docker），适合个人使用 |
| 自建 MCP Server 有开发成本 | 核心代码 ~200 行，可参考上方示例快速实现 |
| 首次索引较慢（BGE-M3 编码） | GPU 加速；或用 fp16 + batch encoding |
| 官方 Qdrant MCP Server 不支持 hybrid search | 自建 MCP Server 解决；或等官方支持 |
| Claude Code 需要联网调用 Anthropic API | 这是方案中唯一持续联网的部分，检索管线本身完全离线 |

---

## 7. 实施路线

### Phase 1: 验证（2-3 天）
- [ ] 本地部署 Qdrant（Docker 或嵌入式）
- [ ] 用 BGE-M3 对 20-30 篇中文文档做索引
- [ ] 中文检索 benchmark：30+ 查询，对比 dense / sparse / hybrid 的召回率和准确率
- [ ] 验证 Qdrant multilingual tokenizer 的中文全文检索效果

### Phase 2: MCP Server 开发（2-3 天）
- [ ] 实现 5 个 MCP 工具（hybrid_search / keyword_search / get_document / list_collections / index_status）
- [ ] 集成 BGE-Reranker-v2-M3
- [ ] 接入 Claude Code，端到端验证

### Phase 3: 工程化（3-5 天）
- [ ] 编写索引构建/增量更新脚本
- [ ] 制定文档 front-matter 规范，存量文档补充元数据
- [ ] 编写 CLAUDE.md 检索规约
- [ ] 配置 Git hook 自动更新索引
- [ ] 编写团队使用指南

### Phase 4: 团队推广（1 周）
- [ ] 每人本地初始化环境
- [ ] 收集反馈，调优参数（min_score、top_k、RRF vs DBSF、reranker 权重）
- [ ] 抽象为可复用 Skill，支持多仓库/多知识库切换

---

## 8. 依赖清单

```
# Python
FlagEmbedding          # BGE-M3 + Reranker
qdrant-client          # Qdrant Python SDK
mcp                    # MCP Server SDK
python-frontmatter     # Markdown front-matter 解析
torch                  # PyTorch (FlagEmbedding 依赖)

# 基础设施
Docker                 # 运行 Qdrant（或用嵌入式模式免 Docker）
Git                    # 文档版本管理
Claude Code            # Agent 编排（唯一需要持续联网的组件）
```
