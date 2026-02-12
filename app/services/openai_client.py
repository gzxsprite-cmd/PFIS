from __future__ import annotations

import os

import httpx
from openai import DefaultHttpxClient, OpenAI


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 未配置，无法调用 AI 分析。请在 .env 或系统环境变量中设置。")

    return OpenAI(
        api_key=api_key,
        http_client=DefaultHttpxClient(
            proxy="socks5h://127.0.0.1:1080",
            timeout=httpx.Timeout(90.0),
        ),
        max_retries=0,
    )
