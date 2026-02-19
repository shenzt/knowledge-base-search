#!/usr/bin/env python3
"""RAGAS 评测封装 — 替代 self-built llm_judge()。

使用 RAGAS 标准化指标：
- faithfulness (0-1): claim-level 验证，回答是否忠于检索 context
- answer_relevancy (0-1): 回答是否切题

用法:
    from ragas_judge import ragas_judge
    result = ragas_judge(query, answer, contexts)
    # {'faithfulness': 0.85, 'answer_relevancy': 0.92, 'score': 4.4, ...}
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
            max_tokens=1024,
        )
    else:
        # OpenAI-compatible (DeepSeek, GLM, etc.)
        from langchain_openai import ChatOpenAI
        chat = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key or "dummy",
            temperature=0,
            max_tokens=1024,
        )

    return LangchainLLMWrapper(chat)


def _get_ragas_embeddings():
    """RAGAS answer_relevancy 需要 embedding model。

    默认用 OpenAI text-embedding-3-small。
    如果没有有效的 OPENAI_API_KEY，跳过 answer_relevancy。
    """
    api_key = os.environ.get("RAGAS_OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    # 排除非 OpenAI key（如 Claude key cr_*, Anthropic key sk-ant-*）
    if not api_key or api_key.startswith(("cr_", "sk-ant-")):
        return None

    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=api_key,
    )
    return LangchainEmbeddingsWrapper(embeddings)


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
        gold_answer: 参考答案（可选，用于 answer_correctness）

    Returns:
        {
            "faithfulness": 0.0-1.0,
            "answer_relevancy": 0.0-1.0 或 -1（无 embedding 时）,
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

    # 4. 执行评估
    try:
        result = evaluate(dataset=eval_dataset, metrics=metrics)
        df = result.to_pandas()

        faith_score = float(df["faithfulness"].iloc[0])
        rel_score = float(df["answer_relevancy"].iloc[0]) if has_relevancy else -1

        # 5. 映射到 0-5 scale（向后兼容）
        if has_relevancy and rel_score >= 0:
            combined = faith_score * 0.6 + rel_score * 0.4
        else:
            combined = faith_score
        legacy_score = round(combined * 5, 1)

        return {
            "faithfulness": round(faith_score, 3),
            "answer_relevancy": round(rel_score, 3) if rel_score >= 0 else -1,
            "relevancy": round(rel_score, 3) if rel_score >= 0 else -1,
            "score": legacy_score,
            "reason": f"RAGAS: faith={faith_score:.2f}"
                      + (f" rel={rel_score:.2f}" if rel_score >= 0 else ""),
        }
    except Exception as e:
        log.error(f"RAGAS 评估异常: {e}")
        return {
            "faithfulness": -1,
            "answer_relevancy": -1,
            "relevancy": -1,
            "score": -1,
            "reason": f"RAGAS 异常: {str(e)[:120]}",
        }


def _extract_context_texts(contexts: list[dict]) -> list[str]:
    """从 extract_contexts() 的结构化输出中提取纯文本。"""
    texts = []
    for c in contexts[:10]:
        # contexts 可能有不同结构
        result = c.get("result", "")
        if isinstance(result, str) and result:
            # MCP hybrid_search 返回的是 JSON 字符串
            try:
                import json
                parsed = json.loads(result)
                if isinstance(parsed, list):
                    for item in parsed[:5]:
                        text = item.get("text", "")
                        if text:
                            texts.append(text[:2000])
                    continue
            except (json.JSONDecodeError, TypeError):
                pass
            texts.append(result[:2000])
        elif c.get("tool") == "Read" and result:
            texts.append(result[:3000])
    return texts
