from __future__ import annotations

import httpx
from openai import DefaultHttpxClient, OpenAI

from ..config import LLM_PROXY, LLM_TIMEOUT_SECONDS, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


class OpenAIProvider:
    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY 未配置，无法调用 OpenAI。")

        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            http_client=DefaultHttpxClient(
                proxy=LLM_PROXY,
                timeout=httpx.Timeout(LLM_TIMEOUT_SECONDS),
            ),
            max_retries=0,
        )
        self.model = OPENAI_MODEL

    def chat(self, messages: list[dict[str, str]]) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return completion.choices[0].message.content or ""
