"""Chat history context resolver for follow-up patent questions."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from ..store import list_patents
from .state import ChatAgentState


PATENT_ID_RE = re.compile(r"\b\d{2}-\d{6,8}\b")
TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[가-힣]+")
FOLLOWUP_TERMS = (
    "이거", "이것", "이 특허", "그거", "앞에서", "방금", "이전", "계속", "그 특허",
    "더 자세하게", "자세히", "이어서", "계속해서", "추가로", "좀 더",
)
GENERIC_TITLE_TERMS = {
    "방법",
    "시스템",
    "장치",
    "및",
    "기반",
    "관리",
    "모니터링",
    "제조",
    "검사",
    "특허",
}


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


def _normalize_match_text(value: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9가-힣]+", "", value or "").lower()
    # Titles often contain Korean possessive particles ("Pad의") while users omit them.
    return compact.replace("의", "")


def _title_terms(value: str) -> set[str]:
    terms = set()
    for token in TOKEN_RE.findall(value or ""):
        lowered = token.lower()
        if len(lowered) < 2:
            continue
        if lowered in GENERIC_TITLE_TERMS:
            continue
        terms.add(lowered)
    return terms


def _patent_from_query(query: str) -> tuple[str | None, dict[str, Any] | None]:
    explicit = PATENT_ID_RE.search(query or "")
    if explicit:
        return explicit.group(0), {"method": "explicit_patent_id", "score": 1.0, "matched": explicit.group(0)}

    query_norm = _normalize_match_text(query)
    query_terms = _title_terms(query)
    best: tuple[float, dict[str, Any]] | None = None
    for patent in list_patents():
        patent_id = str(patent.get("patent_id") or "")
        title = str(patent.get("title") or "")
        if not patent_id or not title:
            continue
        title_norm = _normalize_match_text(title)
        if title_norm and title_norm in query_norm:
            score = 1.0
            matched_terms = sorted(_title_terms(title))
        else:
            title_terms = _title_terms(title)
            matched_terms = sorted(title_terms & query_terms)
            if len(matched_terms) < 2:
                score = 0.0
            else:
                score = len(matched_terms) / max(len(title_terms), 1)
        if score <= 0:
            continue
        candidate = {
            "patent_id": patent_id,
            "title": title,
            "method": "title_match",
            "score": round(score, 4),
            "matched_terms": matched_terms,
        }
        if best is None or score > best[0]:
            best = (score, candidate)

    if best and best[0] >= 0.55:
        return str(best[1]["patent_id"]), best[1]
    return None, None


def resolve_history_context(state: ChatAgentState) -> ChatAgentState:
    query = state.get("query", "")
    chat_history = list(state.get("chat_history") or [])
    requested = state.get("patent_id") or state.get("context_patent_id")
    query_patent_id, query_match = _patent_from_query(query)
    resolved = query_patent_id or requested
    override_reason = None
    if query_patent_id and requested and query_patent_id != requested:
        override_reason = "query_title_overrode_selected_patent"
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
            "requested_patent_id": requested,
            "resolved_patent_id": resolved,
            "query_patent_match": query_match,
            "override_reason": override_reason,
        }
    )
    return {**state, "resolved_patent_id": resolved, "trace": trace}
