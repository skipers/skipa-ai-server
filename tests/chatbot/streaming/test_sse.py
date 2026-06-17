from __future__ import annotations

import json

from chatbot.app.streaming.sse import STREAMING_HEADERS, public_source_cards, sse_event


def test_sse_event_formats_named_json_event() -> None:
    rendered = sse_event("token", {"text": "안녕", "count": 1})

    assert rendered.startswith("event: token\n")
    assert rendered.endswith("\n\n")
    payload = rendered.split("data: ", 1)[1].strip()
    assert json.loads(payload) == {"text": "안녕", "count": 1}


def test_public_source_cards_removes_internal_fields_and_non_dict_items() -> None:
    cards = public_source_cards(
        [
            {
                "label": "근거 1",
                "source_type": "REPORT",
                "snippet": "근거",
                "metadata": {"debug": True},
                "raw": "hidden",
            },
            "bad",
        ]
    )

    assert cards == [{"label": "근거 1", "source_type": "REPORT", "snippet": "근거"}]


def test_streaming_headers_disable_buffering() -> None:
    assert STREAMING_HEADERS["Cache-Control"] == "no-cache"
    assert STREAMING_HEADERS["X-Accel-Buffering"] == "no"

