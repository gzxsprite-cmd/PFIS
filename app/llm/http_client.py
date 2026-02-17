from __future__ import annotations

import os

import httpx
from openai import DefaultHttpxClient


def _timeout() -> httpx.Timeout:
    return httpx.Timeout(float(os.getenv("LLM_TIMEOUT_SECONDS", "60")))


def build_openai_http_client() -> DefaultHttpxClient:
    proxy = os.getenv("HTTP_PROXY")
    if proxy:
        return DefaultHttpxClient(proxy=proxy, timeout=_timeout())
    return DefaultHttpxClient(timeout=_timeout())


def build_qwen_http_client() -> DefaultHttpxClient:
    # Qwen never uses proxy from env by product requirement.
    return DefaultHttpxClient(timeout=_timeout())
