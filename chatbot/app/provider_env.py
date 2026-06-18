"""Provider environment helpers for OpenAI-compatible open-source servers."""

from __future__ import annotations

import os


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def open_source_llm_base_url() -> str:
    return (
        _first_env(
            "OPEN_SOURCE_LLM_BASE_URL",
            "OPEN_SOURCE_BASE_URL",
            "VLLM_BASE_URL",
            "SGLANG_BASE_URL",
            "OPENAI_BASE_URL",
        )
        or "http://127.0.0.1:8000/v1"
    ).rstrip("/")


def open_source_embedding_base_url() -> str:
    return (
        _first_env(
            "OPEN_SOURCE_EMBEDDING_BASE_URL",
            "EMBEDDING_BASE_URL",
            "OPEN_SOURCE_BASE_URL",
            "VLLM_BASE_URL",
            "SGLANG_BASE_URL",
            "OPENAI_BASE_URL",
        )
        or "http://127.0.0.1:8001/v1"
    ).rstrip("/")


def open_source_llm_api_key() -> str:
    return _first_env(
        "OPEN_SOURCE_LLM_API_KEY",
        "OPEN_SOURCE_API_KEY",
        "VLLM_API_KEY",
        "SGLANG_API_KEY",
        "OPENAI_API_KEY",
    ) or "EMPTY"


def open_source_embedding_api_key() -> str:
    return _first_env(
        "OPEN_SOURCE_EMBEDDING_API_KEY",
        "EMBEDDING_API_KEY",
        "OPEN_SOURCE_API_KEY",
        "VLLM_API_KEY",
        "SGLANG_API_KEY",
        "OPENAI_API_KEY",
    ) or "EMPTY"
