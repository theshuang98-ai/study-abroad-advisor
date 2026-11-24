"""DeepSeek chat model configured through environment variables."""

from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


class MissingAPIKeyError(RuntimeError):
    """Raised when DEEPSEEK_API_KEY is absent."""


def load_deepseek_chat_model(
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    timeout: float = 60.0,
) -> ChatOpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise MissingAPIKeyError("DEEPSEEK_API_KEY is not set")

    options = {
        "model": os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL),
        "api_key": api_key,
        "base_url": os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        "temperature": temperature,
        "timeout": timeout,
    }
    if max_tokens is not None:
        options["max_tokens"] = max_tokens
    return ChatOpenAI(**options)
