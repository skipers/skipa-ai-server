"""Shared state types for chatbot agents."""

from __future__ import annotations

from typing import Any, TypedDict


class ChatAgentState(TypedDict, total=False):
    query: str
    patent_id: str | None
    source_types: set[str] | None
    top_k: int
    intent: dict[str, Any]
    result: dict[str, Any]
    trace: list[dict[str, Any]]
    errors: list[str]
