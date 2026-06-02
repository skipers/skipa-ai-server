"""Source-card builders for chatbot answers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from ..config import DATA_ROOT
from .quality import filter_usable_hits
from .source_card_utils import enrich_source_card


def _source_url(metadata: dict[str, Any]) -> str | None:
    source_path = metadata.get("source_path")
    if not source_path:
        return None
    path = Path(str(source_path))
    try:
        rel = path.resolve().relative_to(DATA_ROOT.resolve())
    except Exception:
        return None
    return "/files/data/" + quote(str(rel).replace("\\", "/"))


def cards_from_hits(hits: list[dict[str, Any]], *, query: str | None = None) -> list[dict[str, Any]]:
    cards = []
    for index, hit in enumerate(filter_usable_hits(hits), 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        source_type = str(metadata.get("source_type") or "unknown")
        title = metadata.get("section_title") or metadata.get("file_name") or metadata.get("title")
        page_no = metadata.get("page_no") or metadata.get("page")
        try:
            page_no = int(page_no) if page_no is not None else None
        except (TypeError, ValueError):
            page_no = None
        cards.append(
            enrich_source_card(
                {
                    "label": f"근거 {index}",
                    "title": str(title) if title else None,
                    "source_type": source_type,
                    "page_no": page_no,
                    "url": _source_url(metadata),
                    "snippet": str(hit.get("excerpt") or hit.get("page_content") or ""),
                    "metadata": metadata,
                },
                query=query,
                index=index,
            )
        )
    return cards


def cards_from_web(results: list[dict[str, Any]], *, start_index: int = 1, query: str | None = None) -> list[dict[str, Any]]:
    cards = []
    for offset, item in enumerate(results, start_index):
        cards.append(
            enrich_source_card(
                {
                    "label": f"웹 근거 {offset}",
                    "title": item.get("title"),
                    "source_type": "WEB",
                    "page_no": None,
                    "url": item.get("url"),
                    "snippet": str(item.get("snippet") or ""),
                    "metadata": {"url": item.get("url"), "provider_source_type": item.get("source_type", "WEB")},
                },
                query=query,
                index=offset,
            )
        )
    return cards
