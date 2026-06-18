"""Portfolio insight client backed by the configured LLM provider."""

from __future__ import annotations

import os
from typing import Any

from .providers.llm import portfolio_model, request_portfolio_insights

_LLM_TIMEOUT = int(os.getenv("INSIGHTS_LLM_TIMEOUT", "120"))


def call_openai_portfolio_insights(
    *,
    system_prompt: str,
    user_prompt: str,
    timeout: int = _LLM_TIMEOUT,
) -> dict[str, Any]:
    result = request_portfolio_insights(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        timeout=timeout,
    )
    if not isinstance(result.get("json"), dict):
        raise ValueError("LLM provider response root is not an object")
    return result


__all__ = ["call_openai_portfolio_insights", "portfolio_model"]
