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
    # 위/아래 참조 패턴
    "위에서", "위에 말한", "방금 말한", "그 특허에", "아니 위에",
    # 한국어 정정/추가 패턴
    "아니 ", "그건데", "근데 그거", "그거 말고",
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
    # 1. 명시적으로 선택된 특허
    for key in ("patent_id", "context_patent_id", "resolved_patent_id"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    # 2. source_card_patent_ids: 이전 답변에서 가장 많이 인용된 특허
    source_pids = item.get("source_card_patent_ids")
    if isinstance(source_pids, list) and source_pids:
        from collections import Counter
        counts = Counter(p for p in source_pids if isinstance(p, str) and p.strip())
        if counts:
            return counts.most_common(1)[0][0]

    # 3. metrics에서 추출
    metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
    value = metrics.get("patent_id") or metrics.get("resolved_patent_id")
    if isinstance(value, str) and value.strip():
        return value.strip()

    # 4. 텍스트에서 등록번호 패턴(10-XXXXXXX) 추출
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


def _is_followup(query: str) -> bool:
    """연속/참조/정정 질문 패턴 감지."""
    return any(term in query for term in FOLLOWUP_TERMS)


def _build_retrieval_query(query: str, chat_history: list[dict]) -> str:
    """연속 질문('더 자세하게', '위에서 말한' 등)일 때 이전 Q&A를 합쳐 검색 품질을 높인다."""
    if not _is_followup(query):
        return query
    if not chat_history:
        return query

    # 가장 최근 이전 Q&A에서 핵심 컨텍스트 추출
    for item in reversed(chat_history):
        if not isinstance(item, dict):
            continue
        prev_q = str(item.get("question") or item.get("query") or "").strip()
        prev_a = str(item.get("answer") or "").strip()
        if prev_q and len(prev_q) > 4:
            # 이전 질문 + 이전 답변 첫 100자 + 현재 질문 → 풍부한 검색 쿼리
            context = prev_q
            if prev_a:
                context += " " + prev_a[:100]
            combined = f"{context} {query}"
            return combined[:400]
    return query


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
    is_followup = _is_followup(query)
    if not resolved and is_followup:
        for item in reversed(chat_history):
            if isinstance(item, dict):
                resolved = _patent_id_from_item(item)
                if resolved:
                    history_used = True
                    break

    # 연속/참조 질문이면 이전 Q&A를 포함한 검색 쿼리 생성
    retrieval_query = _build_retrieval_query(query, chat_history)

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
            "retrieval_query": retrieval_query if retrieval_query != query else None,
            "query_patent_match": query_match,
            "override_reason": override_reason,
        }
    )
    return {**state, "resolved_patent_id": resolved, "retrieval_query": retrieval_query, "trace": trace}
