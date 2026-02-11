from __future__ import annotations

import os
import time


DEFAULT_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT_SEC", "45"))
MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")


class AIClientError(RuntimeError):
    """Non-retryable AI client error."""


class AIClientTimeout(RuntimeError):
    """Timeout or transient network error after retries."""


def call_ai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIClientError("未配置 OPENAI_API_KEY。")

    try:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            OpenAI,
            PermissionDeniedError,
            RateLimitError,
        )
    except ModuleNotFoundError as exc:
        raise AIClientError("未安装 openai 依赖，请先执行 pip install -r requirements.txt。") from exc

    try:
        import httpx
    except ModuleNotFoundError as exc:
        raise AIClientError("未安装 httpx 依赖，请先执行 pip install -r requirements.txt。") from exc

    timeout = httpx.Timeout(DEFAULT_TIMEOUT, connect=min(10.0, DEFAULT_TIMEOUT))
    http_client = httpx.Client(timeout=timeout)
    client = OpenAI(api_key=api_key, http_client=http_client, max_retries=0)

    retryable = (APITimeoutError, APIConnectionError, RateLimitError)

    try:
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = client.responses.create(
                    model=DEFAULT_MODEL,
                    input=prompt,
                )
                return response.output_text or ""
            except retryable as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    time.sleep(2**attempt)
                    continue
                raise AIClientTimeout(str(exc)) from exc
            except (AuthenticationError, PermissionDeniedError, BadRequestError) as exc:
                raise AIClientError(str(exc)) from exc

        if last_error:
            raise AIClientTimeout(str(last_error))
        raise AIClientTimeout("请求失败，请稍后重试。")
    finally:
        http_client.close()
