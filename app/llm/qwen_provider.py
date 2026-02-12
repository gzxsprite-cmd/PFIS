from __future__ import annotations

import httpx
from openai import DefaultHttpxClient, OpenAI

from ..config import DASHSCOPE_API_KEY, LLM_PROXY, LLM_TIMEOUT_SECONDS, QWEN_BASE_URL, QWEN_MODEL


class QwenProvider:
    def __init__(self) -> None:
        if not DASHSCOPE_API_KEY:
            raise RuntimeError("DASHSCOPE_API_KEY 未配置，无法调用千问。")

        self.client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=QWEN_BASE_URL,
            http_client=DefaultHttpxClient(
                proxy=LLM_PROXY,
                timeout=httpx.Timeout(LLM_TIMEOUT_SECONDS),
            ),
            max_retries=0,
        )
        self.model = QWEN_MODEL

    def chat(self, messages: list[dict[str, str]]) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return completion.choices[0].message.content or ""
