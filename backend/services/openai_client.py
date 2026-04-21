"""Thin wrappers around OpenAI endpoints. Kept separate so tests can mock."""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .. import config

_client: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured")
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def chat_completion(messages: list[dict], **kwargs: Any) -> str:
    """Return just the assistant text; caller handles errors."""
    resp = client().chat.completions.create(
        model=kwargs.pop("model", config.CHAT_MODEL),
        messages=messages,
        temperature=kwargs.pop("temperature", 0.7),
        max_tokens=kwargs.pop("max_tokens", 1500),
        **kwargs,
    )
    return resp.choices[0].message.content or ""


def chat_json(messages: list[dict], **kwargs: Any) -> dict:
    """Chat completion with response_format=json_object — returns parsed dict."""
    resp = client().chat.completions.create(
        model=kwargs.pop("model", config.CHAT_MODEL),
        messages=messages,
        temperature=kwargs.pop("temperature", 0.4),
        max_tokens=kwargs.pop("max_tokens", 3000),
        response_format={"type": "json_object"},
        **kwargs,
    )
    text = resp.choices[0].message.content or "{}"
    return json.loads(text)


def embed(texts: list[str]) -> list[list[float]]:
    resp = client().embeddings.create(
        model=config.EMBED_MODEL,
        input=texts,
    )
    return [d.embedding for d in resp.data]
