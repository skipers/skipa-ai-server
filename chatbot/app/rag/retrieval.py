"""Local retrieval over patent original/report/wiki vectorstores."""

from __future__ import annotations

from typing import Any

from ..store import search_chunks


def retrieve_local(
    query: str,
    *,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    return search_chunks(query, patent_id=patent_id, source_types=source_types, top_k=top_k)
