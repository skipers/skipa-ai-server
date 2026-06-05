"""Core pipeline compatibility wrapper."""

from __future__ import annotations

from typing import Any

from ..agents.graph import run_chat_agent


def run_pipeline(
    query: str,
    *,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    return run_chat_agent(query, patent_id=patent_id, source_types=source_types, top_k=top_k)
