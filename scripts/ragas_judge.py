#!/usr/bin/env python3
"""RAGAS 评测封装 — 替代 self-built llm_judge()。

使用 RAGAS 标准化指标：
- faithfulness (0-1): claim-level 验证，回答是否忠于检索 context
- answer_relevancy (0-1): 回答是否切题
- context_precision (0-1): 检索到的 chunks 有多少是相关的（需要 reference_answer）
- context_recall (0-1): 是否检索到了所有必要信息（需要 reference_answer）
- answer_correctness (0-1): 答案事实正确性（需要 reference_answer）

用法:
    from ragas_judge import ragas_judge
    result = ragas_judge(query, answer, contexts)
    # {'faithfulness': 0.85, 'answer_relevancy': 0.92, 'score': 4.4, ...}

    # 带 reference_answer 启用更多指标:
    result = ragas_judge(query, answer, contexts, gold_answer="...")
    # {'faithfulness': 0.85, 'context_precision': 0.90, 'context_recall': 0.80, ...}
"""

import logging
import os
from typing import Optional

log = logging.getLogger(__name__)


def _get_ragas_llm():
    """构建 RAGAS 使用的 Judge LLM（默认 DeepSeek V3.2 reasoner）。"""
    from ragas.llms import LangchainLLMWrapper

    provider = os.environ.get("JUDGE_PROVIDER", "openai")
    model = os.environ.get("JUDGE_MODEL", "deepseek-chat")
    base_url = os.environ.get("JUDGE_BASE_URL", "https://api.deepseek.com")
    api_key = (os.environ.get("JUDGE_API_KEY")
               or os.environ.get("DEEPSEEK_API_KEY")
               or os.environ.get("DOC_PROCESS_API_KEY", ""))

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        anthropic_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        chat = ChatAnthropic(
            model=model,
            anthropic_api_key=anthropic_key,
            temperature=0,
            max_tokens=4096,
        )
    else:
        # OpenAI-compatible (DeepSeek, GLM, etc.)
        from langchain_openai import ChatOpenAI
        chat = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key or "dummy",
            temperature=0,
            max_tokens=4096,
        )

    return LangchainLLMWrapper(chat)


def _get_ragas_embeddings():
    """RAGAS answer_relevancy 需要 embedding model。

    优先使用本地 BGE-m3（零成本，与索引一致）。
    设置 RAGAS_EMBEDDING=openai 可切换回 OpenAI。
    """
    backend = os.environ.get("RAGAS_EMBEDDING", "bge-m3")

    if backend == "openai":
        api_key = os.environ.get("RAGAS_OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
        if not api_key or api_key.startswith(("cr_", "sk-ant-")):
            return None
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_openai import OpenAIEmbeddings
        return LangchainEmbeddingsWrapper(OpenAIEmbeddings(
            model="text-embedding-3-small", openai_api_key=api_key,
        ))

    # 默认：本地 BGE-m3
    try:
        from ragas.embeddings import LangchainEmbeddingsWrapper
        embeddings = _BGEM3Embeddings()
        return LangchainEmbeddingsWrapper(embeddings)
    except Exception as e:
        log.warning(f"BGE-m3 embedding 加载失败，跳过 answer_relevancy: {e}")
        return None


class _BGEM3Embeddings:
    """Langchain-compatible wrapper for local BGE-m3 (FlagEmbedding).

    实现 embed_documents / embed_query 接口，
    通过 duck typing 兼容 LangchainEmbeddingsWrapper。
    """

    _model_instance = None  # 类级单例，避免重复加载 ~2GB 模型

    def __init__(self):
        if _BGEM3Embeddings._model_instance is None:
            from FlagEmbedding import BGEM3FlagModel
            model_name = os.environ.get("BGE_M3_MODEL", "BAAI/bge-m3")
            log.info(f"加载 BGE-m3 embedding for RAGAS: {model_name}")
            _BGEM3Embeddings._model_instance = BGEM3FlagModel(model_name, use_fp16=True)
        self._model = _BGEM3Embeddings._model_instance

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        output = self._model.encode(texts, return_dense=True, return_sparse=False)
        return output["dense_vecs"].tolist()

    def embed_query(self, text: str) -> list[float]:
        output = self._model.encode([text], return_dense=True, return_sparse=False)
        return output["dense_vecs"][0].tolist()


def ragas_judge(
    query: str,
    answer: str,
    contexts: list[dict],
    gold_answer: Optional[str] = None,
) -> dict:
    """用 RAGAS 评估单个 RAG 回答。

    Args:
        query: 用户问题
        answer: Agent 回答
        contexts: extract_contexts() 返回的结构化 context list
        gold_answer: 参考答案（可选，启用 ContextPrecision/Recall/AnswerCorrectness）

    Returns:
        {
            "faithfulness": 0.0-1.0,
            "answer_relevancy": 0.0-1.0 或 -1（无 embedding 时）,
            "context_precision": 0.0-1.0 或 -1（无 gold_answer 时）,
            "context_recall": 0.0-1.0 或 -1（无 gold_answer 时）,
            "answer_correctness": 0.0-1.0 或 -1（无 gold_answer 时）,
            "score": 0-5（向后兼容映射）,
            "reason": "RAGAS评估详情",
        }
    """
    from ragas import evaluate
    from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
    from ragas.metrics import Faithfulness, ResponseRelevancy

    # 1. 从 contexts 提取纯文本
    context_texts = _extract_context_texts(contexts)
    if not context_texts:
        context_texts = ["(无检索结果)"]

    # 2. 构建 RAGAS sample
    sample = SingleTurnSample(
        user_input=query,
        response=answer[:4000],
        retrieved_contexts=context_texts,
    )
    if gold_answer:
        sample.reference = gold_answer

    eval_dataset = EvaluationDataset(samples=[sample])

    # 3. 配置 metrics + LLM
    llm = _get_ragas_llm()
    embeddings = _get_ragas_embeddings()

    metrics = [Faithfulness(llm=llm)]
    has_relevancy = False
    if embeddings:
        metrics.append(ResponseRelevancy(llm=llm, embeddings=embeddings))
        has_relevancy = True

    # 4. 如果有 gold_answer，启用 ContextPrecision/Recall/AnswerCorrectness
    has_ctx_precision = False
    has_ctx_recall = False
    has_correctness = False
    if gold_answer:
        try:
            from ragas.metrics import LLMContextPrecisionWithReference, LLMContextRecallWithoutReference
            metrics.append(LLMContextPrecisionWithReference(llm=llm))
            has_ctx_precision = True
            metrics.append(LLMContextRecallWithoutReference(llm=llm))
            has_ctx_recall = True
        except ImportError:
            # 旧版 RAGAS 可能没有这些指标，尝试备选名称
            try:
                from ragas.metrics import ContextPrecision, ContextRecall
                metrics.append(ContextPrecision(llm=llm))
                has_ctx_precision = True
                metrics.append(ContextRecall(llm=llm))
                has_ctx_recall = True
            except ImportError:
                log.warning("RAGAS ContextPrecision/Recall 不可用，跳过")

        try:
            from ragas.metrics import AnswerCorrectness
            if embeddings:
                metrics.append(AnswerCorrectness(llm=llm, embeddings=embeddings))
                has_correctness = True
            else:
                metrics.append(AnswerCorrectness(llm=llm))
                has_correctness = True
        except ImportError:
            log.warning("RAGAS AnswerCorrectness 不可用，跳过")

    # 5. 执行评估
    try:
        result = evaluate(dataset=eval_dataset, metrics=metrics)
        df = result.to_pandas()

        faith_score = float(df["faithfulness"].iloc[0])
        rel_score = float(df["answer_relevancy"].iloc[0]) if has_relevancy else -1

        # 提取新指标
        ctx_precision = -1
        ctx_recall = -1
        correctness = -1
        if has_ctx_precision:
            for col in ["context_precision", "llm_context_precision_with_reference"]:
                if col in df.columns:
                    ctx_precision = float(df[col].iloc[0])
                    break
        if has_ctx_recall:
            for col in ["context_recall", "llm_context_recall_without_reference"]:
                if col in df.columns:
                    ctx_recall = float(df[col].iloc[0])
                    break
        if has_correctness and "answer_correctness" in df.columns:
            correctness = float(df["answer_correctness"].iloc[0])

        # 6. 映射到 0-5 scale（向后兼容）
        if has_relevancy and rel_score >= 0:
            combined = faith_score * 0.6 + rel_score * 0.4
        else:
            combined = faith_score
        legacy_score = round(combined * 5, 1)

        reason_parts = [f"faith={faith_score:.2f}"]
        if rel_score >= 0:
            reason_parts.append(f"rel={rel_score:.2f}")
        if ctx_precision >= 0:
            reason_parts.append(f"ctx_prec={ctx_precision:.2f}")
        if ctx_recall >= 0:
            reason_parts.append(f"ctx_rec={ctx_recall:.2f}")
        if correctness >= 0:
            reason_parts.append(f"correct={correctness:.2f}")

        return {
            "faithfulness": round(faith_score, 3),
            "answer_relevancy": round(rel_score, 3) if rel_score >= 0 else -1,
            "relevancy": round(rel_score, 3) if rel_score >= 0 else -1,
            "context_precision": round(ctx_precision, 3) if ctx_precision >= 0 else -1,
            "context_recall": round(ctx_recall, 3) if ctx_recall >= 0 else -1,
            "answer_correctness": round(correctness, 3) if correctness >= 0 else -1,
            "score": legacy_score,
            "reason": f"RAGAS: {' '.join(reason_parts)}",
        }
    except Exception as e:
        log.error(f"RAGAS 评估异常: {e}")
        return {
            "faithfulness": -1,
            "answer_relevancy": -1,
            "relevancy": -1,
            "context_precision": -1,
            "context_recall": -1,
            "answer_correctness": -1,
            "score": -1,
            "reason": f"RAGAS 异常: {str(e)[:120]}",
        }


def _unescape_sdk_str(s: str) -> str:
    """清理从 SDK str() 序列化中提取的文本片段。"""
    s = s.replace('\\\n', '\n')
    s = s.replace('\\\\"', '"')
    s = s.replace("\\\\'", "'")
    s = s.replace('\\\\', '\\')
    return s


def _extract_context_texts(contexts: list[dict]) -> list[str]:
    """从 extract_contexts() 的结构化输出中提取纯文本。

    处理多种格式:
    - MCP hybrid_search: {"result":"[{\"text\":\"...\"}]"} (双层 JSON, 经过 str() 转义)
    - Grep: "Found N files\npath1\npath2" 或匹配内容
    - Read: 文件全文内容
    """
    import json as _json
    texts = []
    for c in contexts[:10]:
        tool = c.get("tool", "")
        result = c.get("result", "")

        # Read 结果优先处理（完整文档内容）
        if tool == "Read" and result:
            texts.append(str(result)[:5000])
            continue

        if not isinstance(result, str) or not result:
            continue

        # 尝试解析 MCP JSON 结果
        if result.startswith("{"):
            extracted = _extract_mcp_texts(result)
            if extracted:
                texts.extend(extracted[:5])
                continue

        # Grep/Glob 结果或其他纯文本
        if result and not result.startswith("{"):
            texts.append(result[:2000])

    return texts


def _extract_mcp_texts(result: str) -> list[str] | None:
    """从 MCP 工具返回的 JSON 结果中提取 text 字段。

    处理多层 JSON 转义（SDK str() 序列化导致）。
    优先尝试 json.loads，失败时用 regex 提取。
    """
    import json as _json
    import re

    # 尝试 1: 直接 json.loads（无额外转义时）
    try:
        parsed = _json.loads(result)
        items = None
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict) and "result" in parsed:
            inner = parsed["result"]
            if isinstance(inner, list):
                items = inner
            elif isinstance(inner, str):
                try:
                    items = _json.loads(inner)
                except _json.JSONDecodeError:
                    pass
        if isinstance(items, list):
            return [item.get("text", "")[:2000] for item in items
                    if isinstance(item, dict) and item.get("text")]
    except (_json.JSONDecodeError, TypeError):
        pass

    # 尝试 2: regex 提取 "text" 字段值（处理多层转义的 fallback）
    # 匹配模式: \\"text\\": \\"<content>\\" 或变体
    pattern = r'\\\\?"text\\\\?"\s*:\s*\\\\?"((?:[^"\\]|\\\\?.)*?)\\\\?"'
    matches = re.findall(pattern, result)
    if matches:
        texts = []
        for m in matches:
            t = _unescape_sdk_str(m)
            if len(t) > 20:  # 跳过太短的片段
                texts.append(t[:2000])
        if texts:
            return texts

    # 尝试 3: 更宽松的 regex
    pattern2 = r'"text"[^:]*:\s*"([^"]{20,}?)"'
    matches2 = re.findall(pattern2, result)
    if matches2:
        return [_unescape_sdk_str(m)[:2000] for m in matches2]

    return None
