"""Optional web-search agent for questions requiring external evidence."""

from __future__ import annotations

from datetime import datetime
import json

from ..config import PATENTS_ROOT
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
    lines = [
        f"# Web Search Draft: {state.get('query', '')}",
        "",
        "이 문서는 웹 검색 결과를 자연어 Markdown으로 임시 저장한 파일입니다.",
        "감사 프로세스에서 사람이 확인한 뒤 승인된 내용만 vectorstore에 반영합니다.",
        "",
        f"- Provider: {result.get('provider') or 'unknown'}",
        f"- Patent ID: `{patent_id}`",
        "",
        "## Results",
    ]
    for index, item in enumerate(results, 1):
        lines.extend(
            [
                "",
                f"### {index}. {item.get('title') or 'web result'}",
                "",
                f"- URL: {item.get('url') or '-'}",
                "",
                str(item.get("snippet") or ""),
            ]
        )
    lines.extend(["", "## Raw JSON", "", "```json", json.dumps(results, ensure_ascii=False, indent=2), "```"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def retrieve_web_context(state: ChatAgentState) -> ChatAgentState:
    intent = state.get("intent") or {}
    should_search = bool(intent.get("needs_web") or "web" in set(intent.get("source_plan") or []))
    result = {"enabled": should_search, "provider": None, "results": [], "error": None}
    if should_search:
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
            "provider": result.get("provider"),
            "result_count": len(result.get("results") or []),
            "error": result.get("error"),
            "wiki_draft_path": result.get("wiki_draft_path"),
        }
    )
    return {**state, "web_context": result, "trace": trace}
