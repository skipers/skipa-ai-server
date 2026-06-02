"""Optional web-search agent for questions requiring external evidence."""

from __future__ import annotations

from datetime import datetime
import json

from ..config import PATENTS_ROOT
from ..rag.quality import compact_text, filter_usable_hits, preprocess_evidence_text
from ..rag.web_answers import search_web
from .state import ChatAgentState


def _archive_web_results(state: ChatAgentState, result: dict) -> str | None:
    results = result.get("results") or []
    if not results:
        return None
    patent_id = state.get("resolved_patent_id") or state.get("patent_id") or "_global"
    wiki_dir = PATENTS_ROOT / patent_id / "wiki" / "web_search_drafts"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    path = wiki_dir / (datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".md")
    query = str(state.get("query") or "")
    lines = [
        f"# Web Search Draft",
        "",
        "## 질문",
        "",
        query,
        "",
        "## 답변",
        "",
        "아래 내용은 웹 검색 결과를 자연어 Markdown으로 정리한 답변 후보입니다. 감사 프로세스에서 사람이 확인한 뒤 승인된 내용만 해당 특허의 wiki vectorstore에 반영합니다.",
    ]
    for index, item in enumerate(results, 1):
        snippet = preprocess_evidence_text(item.get("snippet"), max_chars=700)
        lines.extend(
            [
                "",
                f"### {index}. {item.get('title') or 'web result'}",
                "",
                f"- URL: {item.get('url') or '-'}",
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
            f"- Created at: {datetime.now().isoformat(timespec='seconds')}",
            "- Review policy: 사람이 승인하기 전에는 global vectorstore에 반영하지 않습니다.",
            "",
            "### Raw JSON",
            "",
            "```json",
            json.dumps(results, ensure_ascii=False, indent=2),
            "```",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def retrieve_web_context(state: ChatAgentState) -> ChatAgentState:
    intent = state.get("intent") or {}
    should_search = bool(intent.get("needs_web") or "web" in set(intent.get("source_plan") or []))
    wiki_hits = filter_usable_hits(list((state.get("wiki_context") or {}).get("hits") or []), limit=1)
    result = {"enabled": should_search, "provider": None, "results": [], "error": None}
    skipped_by_wiki = False
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
            result = search_web(state.get("query", ""))
            archive_path = _archive_web_results(state, result)
            if archive_path:
                result["wiki_draft_path"] = archive_path

    trace = list(state.get("trace", []))
    trace.append(
        {
            "node": "retrieve_web_context",
            "status": "success" if not result.get("error") else "warning",
            "at": datetime.now().isoformat(timespec="seconds"),
            "enabled": should_search,
            "skipped_by_wiki": skipped_by_wiki,
            "provider": result.get("provider"),
            "result_count": len(result.get("results") or []),
            "error": result.get("error"),
            "skip_reason": result.get("skip_reason"),
            "wiki_draft_path": result.get("wiki_draft_path"),
        }
    )
    return {**state, "web_context": result, "trace": trace}
