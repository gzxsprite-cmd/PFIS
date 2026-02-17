from __future__ import annotations

from ..config import LLM_PROVIDER


def get_llm():
    if LLM_PROVIDER == "qwen":
        from .qwen_provider import QwenProvider

        return QwenProvider()

    from .openai_provider import OpenAIProvider

    return OpenAIProvider()
