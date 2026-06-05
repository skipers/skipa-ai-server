"""Web search compatibility wrapper."""

from __future__ import annotations

from typing import Any

from ..rag.web_answers import search_web as _search_web


def search_web(query: str) -> dict[str, Any]:
    return _search_web(query)
