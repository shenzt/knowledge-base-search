#!/usr/bin/env python3
"""Embedding Provider 抽象层。

通过 EMBEDDING_PROVIDER 环境变量切换本地 BGE-M3 和外部 OpenAI-compatible API。

环境变量:
  EMBEDDING_PROVIDER=local          # 默认，本地 BGE-M3
  EMBEDDING_PROVIDER=openai         # 外部 API（SiliconFlow、Jina 等）
  EMBEDDING_API_KEY=sk-xxx          # API key（openai 模式必需）
  EMBEDDING_BASE_URL=https://...    # API endpoint（openai 模式必需）
  EMBEDDING_MODEL=BAAI/bge-m3      # 模型名（openai 模式）
  EMBEDDING_DIM=1024                # 向量维度（openai 模式，默认 1024）
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
from qdrant_client import models

log = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Embedding 编码抽象基类。"""

    @abstractmethod
    def encode_texts(self, texts: list[str], batch_size: int = 256) -> dict:
        """批量编码文档文本。

        返回:
            {"dense_vecs": ndarray (N, dim), "lexical_weights": list[dict] | None}
            lexical_weights 为 None 表示不支持 sparse（外部 API 模式）。
        """

    @abstractmethod
    def encode_query(self, query: str) -> dict:
        """编码单条查询。

        返回:
            {"dense_vec": list[float], "sparse_vec": SparseVector | None}
            sparse_vec 为 None 表示不支持 sparse。
        """


class LocalBGEM3Provider(EmbeddingProvider):
    """本地 BGE-M3 模型，支持 dense + sparse。"""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        from FlagEmbedding import BGEM3FlagModel
        log.info(f"加载本地模型 {model_name}...")
        self._model = BGEM3FlagModel(model_name, use_fp16=True)

    def encode_texts(self, texts: list[str], batch_size: int = 256) -> dict:
        output = self._model.encode(
            texts, return_dense=True, return_sparse=True, batch_size=batch_size
        )
        return {
            "dense_vecs": output["dense_vecs"],
            "lexical_weights": output["lexical_weights"],
        }

    def encode_query(self, query: str) -> dict:
        q = self._model.encode([query], return_dense=True, return_sparse=True)
        dense_vec = q["dense_vecs"][0].tolist()
        sparse = q["lexical_weights"][0]
        sparse_vec = models.SparseVector(
            indices=list(map(int, sparse.keys())),
            values=list(sparse.values()),
        )
        return {"dense_vec": dense_vec, "sparse_vec": sparse_vec}


class OpenAICompatibleProvider(EmbeddingProvider):
    """OpenAI-compatible API（SiliconFlow、Jina 等），仅 dense。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "BAAI/bge-m3",
        dim: int = 1024,
    ):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._dim = dim
        log.info(f"使用外部 embedding API: {base_url} model={model} dim={dim}")

    def encode_texts(self, texts: list[str], batch_size: int = 256) -> dict:
        import time

        # 外部 API 用较小 batch 避免超时/空响应（OpenRouter 等限制）
        api_batch = min(batch_size, 64)
        all_vecs = []
        max_retries = 3

        for start in range(0, len(texts), api_batch):
            batch = texts[start : start + api_batch]
            for attempt in range(max_retries):
                try:
                    resp = self._client.embeddings.create(input=batch, model=self._model)
                    vecs = [item.embedding for item in resp.data]
                    if not vecs:
                        raise ValueError("No embedding data received")
                    all_vecs.extend(vecs)
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait = 2 ** (attempt + 1)
                        log.warning(f"  API batch {start} 失败 (attempt {attempt + 1}): {e}, {wait}s 后重试")
                        time.sleep(wait)
                    else:
                        raise
            if len(texts) > api_batch:
                log.info(f"  API embedding {start + len(batch)}/{len(texts)}")

        return {
            "dense_vecs": np.array(all_vecs, dtype=np.float32),
            "lexical_weights": None,
        }

    def encode_query(self, query: str) -> dict:
        resp = self._client.embeddings.create(input=[query], model=self._model)
        return {
            "dense_vec": resp.data[0].embedding,
            "sparse_vec": None,
        }


_provider: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    """根据环境变量返回 embedding provider 单例。"""
    global _provider
    if _provider is not None:
        return _provider

    provider_type = os.environ.get("EMBEDDING_PROVIDER", "local")

    if provider_type == "openai":
        api_key = os.environ.get("EMBEDDING_API_KEY", "")
        base_url = os.environ.get("EMBEDDING_BASE_URL", "")
        model = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-m3")
        dim = int(os.environ.get("EMBEDDING_DIM", "1024"))
        if not api_key or not base_url:
            raise ValueError(
                "EMBEDDING_PROVIDER=openai 需要设置 EMBEDDING_API_KEY 和 EMBEDDING_BASE_URL"
            )
        _provider = OpenAICompatibleProvider(
            api_key=api_key, base_url=base_url, model=model, dim=dim
        )
    else:
        model_name = os.environ.get("BGE_M3_MODEL", "BAAI/bge-m3")
        _provider = LocalBGEM3Provider(model_name=model_name)

    return _provider
