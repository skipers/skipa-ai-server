"""Small helpers for Server-Sent Events responses."""

from __future__ import annotations

import json
from typing import Any


PUBLIC_SOURCE_CARD_KEYS = (
    "label",
    "title",
    "display_title",
    "source_type",
    "page_no",
    "url",
    "location_label",
    "source_path",
    "match_terms",
    "snippet",
)


def sse_event(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def public_source_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean: list[dict[str, Any]] = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        clean.append({key: card.get(key) for key in PUBLIC_SOURCE_CARD_KEYS if key in card})
    return clean


STREAMING_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

