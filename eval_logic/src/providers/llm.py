"""AI provider switch for eval_logic report generation."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_runtime.providers import (  # noqa: E402
    chat_json,
    chat_text,
    default_embedding_model,
    default_llm_model,
    embed_texts,
    embedding_configured,
    llm_configured,
    provider,
)


def report_model(*env_names: str) -> str:
    return default_llm_model(
        *env_names,
        "OPEN_SOURCE_EVAL_LOGIC_MODEL",
        "OPEN_SOURCE_REPORT_MODEL",
        "OPEN_SOURCE_LLM_MODEL",
        "OPENAI_REPORT_MODEL",
        "OPENAI_MODEL",
    )


def embedding_model(*env_names: str) -> str:
    return default_embedding_model(
        *env_names,
        "OPEN_SOURCE_EMBEDDING_MODEL",
        "OPENAI_EMBEDDING_MODEL",
        "EMBEDDING_MODEL",
    )


def request_json(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    timeout_seconds: int = 60,
    max_tokens: int = 1000,
    temperature: float = 0.2,
) -> dict[str, Any]:
    result = chat_json(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        model_env=(
            "OPEN_SOURCE_EVAL_LOGIC_MODEL",
            "OPEN_SOURCE_REPORT_MODEL",
            "OPEN_SOURCE_LLM_MODEL",
            "OPENAI_REPORT_MODEL",
            "OPENAI_MODEL",
        ),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout_seconds,
    )
    return result["json"]


def request_text(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    timeout_seconds: int = 60,
    max_tokens: int = 1000,
    temperature: float = 0.2,
) -> str:
    result = chat_text(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        model_env=(
            "OPEN_SOURCE_EVAL_LOGIC_MODEL",
            "OPEN_SOURCE_REPORT_MODEL",
            "OPEN_SOURCE_LLM_MODEL",
            "OPENAI_REPORT_MODEL",
            "OPENAI_MODEL",
        ),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout_seconds,
    )
    return str(result["text"]).strip()


def request_embeddings(texts: list[str], *, timeout_seconds: int = 60) -> list[list[float]]:
    result = embed_texts(
        texts,
        model=embedding_model(),
        timeout=timeout_seconds,
    )
    return result["embeddings"]


__all__ = [
    "embedding_configured",
    "embedding_model",
    "llm_configured",
    "provider",
    "report_model",
    "request_embeddings",
    "request_json",
    "request_text",
]

