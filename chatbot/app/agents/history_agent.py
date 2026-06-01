"""Chat history context resolver for follow-up patent questions."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from .state import ChatAgentState


PATENT_ID_RE = re.compile(r"\b\d{2}-\d{6,8}\b")
FOLLOWUP_TERMS = ("이거", "이것", "이 특허", "그거", "앞에서", "방금", "이전", "계속", "그 특허")


def _patent_id_from_item(item: dict[str, Any]) -> str | None:
    for key in ("patent_id", "context_patent_id"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
    value = metrics.get("patent_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    text = " ".join(str(item.get(key) or "") for key in ("question", "query", "answer", "content"))
    match = PATENT_ID_RE.search(text)
    return match.group(0) if match else None


def resolve_history_context(state: ChatAgentState) -> ChatAgentState:
    query = state.get("query", "")
    chat_history = list(state.get("chat_history") or [])
    resolved = state.get("patent_id") or state.get("context_patent_id")
    history_used = False
    if not resolved and any(term in query for term in FOLLOWUP_TERMS):
        for item in reversed(chat_history):
            if isinstance(item, dict):
                resolved = _patent_id_from_item(item)
                if resolved:
                    history_used = True
                    break

    trace = list(state.get("trace", []))
    trace.append(
        {
            "node": "resolve_history_context",
            "status": "success",
            "at": datetime.now().isoformat(timespec="seconds"),
            "history_count": len(chat_history),
            "history_used": history_used,
            "resolved_patent_id": resolved,
        }
    )
    return {**state, "resolved_patent_id": resolved, "trace": trace}
