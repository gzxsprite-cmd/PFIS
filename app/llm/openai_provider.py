from __future__ import annotations

from openai import OpenAI

from ..config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from .http_client import build_openai_http_client


class OpenAIProvider:
    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY 未配置，无法调用 OpenAI。")

        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            http_client=build_openai_http_client(),
            max_retries=0,
        )
        self.model = OPENAI_MODEL

    def chat(self, messages: list[dict[str, str]]) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return completion.choices[0].message.content or ""
