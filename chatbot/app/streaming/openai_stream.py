"""Dependency-light streaming clients for OpenAI and opensource LLM servers."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import requests

from ..provider_env import open_source_llm_api_key, open_source_llm_base_url
from ..rag.config import OPENAI_API_KEY, OPENAI_BASE_URL

_OPENSOURCE_LLM_BASE_URL = open_source_llm_base_url()
_OPENSOURCE_LLM_API_KEY = open_source_llm_api_key()


def _text_delta(data: dict[str, Any]) -> str:
    event_type = str(data.get("type") or data.get("event") or "")
    if event_type in {"response.output_text.delta", "response.refusal.delta"}:
        return str(data.get("delta") or "")
    if "delta" in data and isinstance(data.get("delta"), str):
        return str(data.get("delta") or "")

    # Chat Completions compatible fallback for OpenAI-compatible gateways.
    choices = data.get("choices")
    if isinstance(choices, list):
        chunks: list[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta")
            if isinstance(delta, dict) and delta.get("content"):
                chunks.append(str(delta.get("content") or ""))
            message = choice.get("message")
            if isinstance(message, dict) and message.get("content"):
                chunks.append(str(message.get("content") or ""))
        return "".join(chunks)
    return ""


def stream_openai_prompt(
    prompt: str,
    *,
    model: str,
    timeout: int,
    max_output_tokens: int | None = None,
    temperature: float | None = 0.2,
) -> Iterator[str]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    payload: dict[str, Any] = {
        "model": model,
        "stream": True,
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
    }
    if max_output_tokens:
        payload["max_output_tokens"] = max_output_tokens
    if temperature is not None:
        payload["temperature"] = temperature

    with requests.post(
        f"{OPENAI_BASE_URL}/responses",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        json=payload,
        stream=True,
        timeout=(10, timeout),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith(":"):
                continue
            if not line.startswith("data:"):
                continue
            raw_data = line[5:].strip()
            if not raw_data or raw_data == "[DONE]":
                continue
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                continue
            delta = _text_delta(data)
            if delta:
                yield delta


def stream_opensource_prompt(
    prompt: str,
    *,
    model: str,
    timeout: int,
    max_output_tokens: int | None = None,
    temperature: float | None = 0.2,
) -> Iterator[str]:
    """Stream from local opensource LLM server (Chat Completions SSE format)."""
    payload: dict[str, Any] = {
        "model": model,
        "stream": True,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_output_tokens or 2000,
        "temperature": temperature if temperature is not None else 0.2,
    }
    with requests.post(
        f"{_OPENSOURCE_LLM_BASE_URL}/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_OPENSOURCE_LLM_API_KEY}",
        },
        json=payload,
        stream=True,
        timeout=(10, timeout),
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            raw_data = line[5:].strip()
            if not raw_data or raw_data == "[DONE]":
                continue
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                continue
            delta = _text_delta(data)
            if delta:
                yield delta
