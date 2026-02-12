from __future__ import annotations

from ..config import LLM_PROVIDER
from .openai_provider import OpenAIProvider
from .qwen_provider import QwenProvider


def get_llm():
    if LLM_PROVIDER == "qwen":
        return QwenProvider()
    return OpenAIProvider()
