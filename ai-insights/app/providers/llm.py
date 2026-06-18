"""LLM provider switch for portfolio insights."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai_runtime.providers import chat_json, default_llm_model, provider  # noqa: E402


def portfolio_model() -> str:
    return default_llm_model(
        "OPEN_SOURCE_PORTFOLIO_INSIGHTS_MODEL",
        "OPEN_SOURCE_LLM_MODEL",
        "OPENAI_PORTFOLIO_INSIGHTS_MODEL",
        "OPENAI_MODEL",
    )


def request_portfolio_insights(
    *,
    system_prompt: str,
    user_prompt: str,
    timeout: int = 30,
) -> dict[str, Any]:
    result = chat_json(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=portfolio_model(),
        temperature=0.35,
        max_tokens=700,
        timeout=timeout,
    )
    return {"provider": provider(), "model": result["model"], "json": result["json"], "raw": result["raw"]}


__all__ = ["portfolio_model", "provider", "request_portfolio_insights"]

