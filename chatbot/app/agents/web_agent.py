"""Optional web-search agent for questions requiring external evidence."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json

from ..rag.quality import compact_text, filter_usable_hits, preprocess_evidence_text
from ..rag.web_answers import search_web
from ..vectorstore import auto_approve_web_draft, is_duplicate_web_query
from ..wiki.topics import get_patent_topic, topic_draft_dir
from .state import ChatAgentState


def _query_hash(query: str) -> str:
    return hashlib.sha1(query.encode("utf-8")).hexdigest()[:12]


def _avg_relevance(results: list) -> float:
    scores = [float((r.get("relevance") or {}).get("score") or 0.0) for r in results]
    return sum(scores) / len(scores) if scores else 0.0


def _archive_web_results(state: ChatAgentState, result: dict) -> tuple[str | None, str]:
    results = result.get("results") or []
    if not results:
        return None, "_general"
    patent_id = state.get("resolved_patent_id") or state.get("patent_id") or "_global"
    # pre-eval case IDs look like "20260605_161436_특허명..." — derive topic from the name part
    import re as _re
    _preval_match = _re.match(r"^\d{8}_\d{6}_(.+)$", patent_id)
    if _preval_match:
        from ..wiki.topics import classify_title_to_topic
        topic = classify_title_to_topic(_preval_match.group(1).replace("_", " "))
    elif patent_id != "_global":
        topic = get_patent_topic(patent_id)
    else:
        topic = "_general"
    wiki_dir = topic_draft_dir(topic)
    wiki_dir.mkdir(parents=True, exist_ok=True)
    path = wiki_dir / (datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".md")
    query = str(state.get("query") or "")
    avg_rel = _avg_relevance(results)
    lines = [
        "# Web Search Draft",
        "",
        "## 질문",
        "",
        query,
        "",
        f"## 결과 요약  (평균 관련도: {avg_rel:.2f}, 결과 수: {len(results)})",
        "",
        "아래 내용은 웹 검색 결과입니다. 평균 관련도가 기준 이상이면 자동 승인되어 wiki vectorstore에 즉시 반영됩니다. 그렇지 않으면 감사 후 사람이 승인한 내용만 반영됩니다.",
    ]
    for index, item in enumerate(results, 1):
        snippet = preprocess_evidence_text(item.get("snippet"), max_chars=700)
        rel = item.get("relevance") if isinstance(item.get("relevance"), dict) else {}
        matched = rel.get("matched_terms") or []
        lines.extend(
            [
                "",
                f"### {index}. {item.get('title') or 'web result'}",
                "",
                f"- URL: {item.get('url') or '-'}",
                f"- 관련도: {rel.get('score', 0):.2f}  매칭: {', '.join(str(t) for t in matched) or '-'}",
                f"- 요약: {compact_text(snippet, 500)}",
                "",
                snippet,
            ]
        )
    lines.extend(
        [
            "",
            "## 메타정보",
            "",
            f"- Provider: {result.get('provider') or 'unknown'}",
            f"- Patent ID: `{patent_id}`",
            f"- Topic: `{topic}`",
            f"- Created at: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "### Raw JSON",
            "",
            "```json",
            json.dumps(results, ensure_ascii=False, indent=2),
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path), topic


def retrieve_web_context(state: ChatAgentState) -> ChatAgentState:
    intent = state.get("intent") or {}
    should_search = bool(intent.get("needs_web") or "web" in set(intent.get("source_plan") or []))
    wiki_hits = filter_usable_hits(list((state.get("wiki_context") or {}).get("hits") or []), limit=1)
    result = {"enabled": should_search, "provider": None, "results": [], "error": None}
    skipped_by_wiki = False
    skipped_by_dedup = False
    auto_approve_result: dict | None = None

    if should_search:
        if wiki_hits:
            skipped_by_wiki = True
            result = {
                "enabled": False,
                "provider": None,
                "results": [],
                "error": None,
                "skipped": True,
                "skip_reason": "patent_local_wiki_context_available",
            }
        else:
            query = state.get("query", "")
            patent_id = state.get("resolved_patent_id") or state.get("patent_id") or "_global"
            qhash = _query_hash(query)

            if patent_id != "_global" and is_duplicate_web_query(patent_id, qhash):
                skipped_by_dedup = True
                result = {
                    "enabled": False,
                    "provider": None,
                    "results": [],
                    "error": None,
                    "skipped": True,
                    "skip_reason": "duplicate_query_within_dedup_window",
                }
            else:
                result = search_web(query)
                archive_path, archived_topic = _archive_web_results(state, result)
                if archive_path:
                    result["wiki_draft_path"] = archive_path
                results = result.get("results") or []
                if results:
                    auto_approve_result = auto_approve_web_draft(
                        patent_id,
                        draft_path=archive_path,
                        query=query,
                        results=results,
                        topic_override=archived_topic,
                    )
                    result["wiki_auto_approve"] = auto_approve_result

    trace = list(state.get("trace", []))
    trace.append(
        {
            "node": "retrieve_web_context",
            "status": "success" if not result.get("error") else "warning",
            "at": datetime.now().isoformat(timespec="seconds"),
            "enabled": should_search,
            "skipped_by_wiki": skipped_by_wiki,
            "skipped_by_dedup": skipped_by_dedup,
            "provider": result.get("provider"),
            "result_count": len(result.get("results") or []),
            "error": result.get("error"),
            "skip_reason": result.get("skip_reason"),
            "wiki_draft_path": result.get("wiki_draft_path"),
            "wiki_auto_approve": auto_approve_result,
        }
    )
    return {**state, "web_context": result, "trace": trace}
