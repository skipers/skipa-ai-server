"""LLM provider switch for pre-application valuation reports."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_runtime.providers import (  # noqa: E402
    chat_json,
    default_llm_model,
    llm_configured,
    provider,
)


def report_model(*env_names: str) -> str:
    return default_llm_model(
        *env_names,
        "OPEN_SOURCE_PRE_APPLICATION_MODEL",
        "OPEN_SOURCE_REPORT_MODEL",
        "OPEN_SOURCE_LLM_MODEL",
        "OPENAI_PRE_APPLICATION_MODEL",
        "OPENAI_REPORT_MODEL",
        "OPENAI_MODEL",
    )


def request_report_json(
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
            "OPEN_SOURCE_PRE_APPLICATION_MODEL",
            "OPEN_SOURCE_REPORT_MODEL",
            "OPEN_SOURCE_LLM_MODEL",
            "OPENAI_PRE_APPLICATION_MODEL",
            "OPENAI_REPORT_MODEL",
            "OPENAI_MODEL",
        ),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout_seconds,
    )
    return result["json"]


__all__ = ["llm_configured", "provider", "report_model", "request_report_json"]

