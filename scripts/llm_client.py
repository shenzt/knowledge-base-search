#!/usr/bin/env python3
"""统一 LLM 调用接口。

支持 Anthropic + OpenAI-compatible（DeepSeek、Qwen、GLM、豆包、Kimi 等）。
三个场景独立配置：文档预处理、LLM Judge、Agentic Search。

用法:
    from llm_client import get_client

    # 按场景获取客户端
    judge = get_client("judge")
    doc = get_client("doc_process")

    # 统一调用
    result = judge.generate("评估这个回答的质量...", max_tokens=300)
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger(__name__)


class LLMClient(ABC):
    """LLM 调用统一接口。"""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1000,
                 temperature: float = 0, system: Optional[str] = None) -> str:
        """生成文本。返回纯文本结果。"""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model})"


class AnthropicClient(LLMClient):
    """Anthropic API 客户端（Claude 系列）。"""

    def __init__(self, model: str, api_key: Optional[str] = None):
        super().__init__(model)
        import anthropic
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        self._client = anthropic.Anthropic(**kwargs)

    def generate(self, prompt: str, max_tokens: int = 1000,
                 temperature: float = 0, system: Optional[str] = None) -> str:
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        msg = self._client.messages.create(**kwargs)
        return msg.content[0].text


class OpenAICompatibleClient(LLMClient):
    """OpenAI-compatible API 客户端。

    支持所有兼容 OpenAI API 的服务：
    - DeepSeek: https://api.deepseek.com
    - 智谱 GLM: https://open.bigmodel.cn/api/paas/v4
    - 通义千问: https://dashscope.aliyuncs.com/compatible-mode/v1
    - 豆包: https://ark.cn-beijing.volces.com/api/v3
    - Kimi: https://api.moonshot.cn/v1
    - OpenAI: https://api.openai.com/v1
    """

    def __init__(self, model: str, base_url: str,
                 api_key: Optional[str] = None):
        super().__init__(model)
        from openai import OpenAI
        self._client = OpenAI(
            base_url=base_url,
            api_key=api_key or "dummy",
        )

    def generate(self, prompt: str, max_tokens: int = 1000,
                 temperature: float = 0, system: Optional[str] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content


# ── 场景配置 ─────────────────────────────────────────────────────

# 每个场景独立的环境变量前缀
SCENE_ENV = {
    "judge": {
        "provider": "JUDGE_PROVIDER",
        "model": "JUDGE_MODEL",
        "base_url": "JUDGE_BASE_URL",
        "api_key": "JUDGE_API_KEY",
    },
    "doc_process": {
        "provider": "DOC_PROCESS_PROVIDER",
        "model": "DOC_PROCESS_MODEL",
        "base_url": "DOC_PROCESS_BASE_URL",
        "api_key": "DOC_PROCESS_API_KEY",
    },
    "worker": {
        "provider": "WORKER_PROVIDER",
        "model": "WORKER_MODEL",
        "base_url": "WORKER_BASE_URL",
        "api_key": "WORKER_API_KEY",
    },
}

# 默认配置
DEFAULTS = {
    "judge": {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
    "doc_process": {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
    "worker": {"provider": "anthropic", "model": "claude-sonnet-4-5-20250929"},
}


def get_client(scene: str = "worker") -> LLMClient:
    """按场景获取 LLM 客户端。

    Args:
        scene: "judge" | "doc_process" | "worker"

    环境变量示例（以 judge 为例）：
        JUDGE_PROVIDER=openai       # anthropic | openai
        JUDGE_MODEL=deepseek-chat   # 模型名
        JUDGE_BASE_URL=https://api.deepseek.com  # OpenAI-compatible endpoint
        JUDGE_API_KEY=sk-xxx        # API key
    """
    if scene not in SCENE_ENV:
        raise ValueError(f"未知场景: {scene}，可选: {list(SCENE_ENV.keys())}")

    env = SCENE_ENV[scene]
    defaults = DEFAULTS[scene]

    provider = os.environ.get(env["provider"], defaults["provider"])
    model = os.environ.get(env["model"], defaults["model"])
    base_url = os.environ.get(env["base_url"], "")
    api_key = os.environ.get(env["api_key"], "")

    if provider == "anthropic":
        client = AnthropicClient(model=model, api_key=api_key or None)
    elif provider == "openai":
        if not base_url:
            raise ValueError(
                f"{env['base_url']} 未设置。"
                f"OpenAI-compatible 模式需要指定 base_url。"
            )
        client = OpenAICompatibleClient(
            model=model, base_url=base_url, api_key=api_key or None,
        )
    else:
        raise ValueError(f"未知 provider: {provider}，可选: anthropic, openai")

    log.info(f"[LLM] {scene}: {client}")
    return client
