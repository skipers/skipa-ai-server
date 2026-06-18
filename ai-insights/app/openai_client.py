"""Portfolio insight client backed by the configured LLM provider."""

from __future__ import annotations

from typing import Any

from .providers.llm import portfolio_model, request_portfolio_insights


def call_openai_portfolio_insights(
    *,
    system_prompt: str,
    user_prompt: str,
    timeout: int = 30,
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
