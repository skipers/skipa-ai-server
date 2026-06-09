"""Answer formatting helpers."""

from __future__ import annotations

from typing import Any

from .quality import compact_text, filter_usable_hits


def fallback_answer(
    query: str,
    *,
    local_hits: list[dict[str, Any]],
    web_results: list[dict[str, Any]],
    llm_error: str | None = None,
) -> str:
    local_hits = filter_usable_hits(local_hits, limit=6)
    if not local_hits and not web_results:
        return (
            "내부 승인 데이터와 원문/보고서에서 직접 답할 만한 근거가 충분하지 않습니다.\n\n"
            "- 같은 질문으로 웹 검색 보강이 가능하면 외부 근거를 함께 확인합니다.\n"
            "- 특허명을 더 구체적으로 쓰거나 전체 특허 범위로 다시 질문하면 후보를 넓힐 수 있습니다."
        )

    lines = [
        "모델 답변 생성이 지연되어 검색 근거 기반으로 먼저 정리합니다.",
        "",
        "## 핵심 근거 요약",
    ]
    if llm_error:
        lines.insert(1, f"모델 상태: {llm_error}")
    for index, hit in enumerate(local_hits[:5], 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        source_type = metadata.get("source_type") or "unknown"
        section = metadata.get("section_title") or metadata.get("file_name") or metadata.get("title") or "근거"
        lines.append(f"{index}. {source_type} / {section}: {compact_text(hit.get('excerpt') or hit.get('page_content'), 220)}")
    if web_results:
        lines.append("")
        lines.append("## 웹 근거 보강")
        for index, item in enumerate(web_results[:3], 1):
            lines.append(f"{index}. {item.get('title')}: {compact_text(item.get('snippet'), 220)}")
    return "\n".join(lines)


def build_metrics(
    *,
    intent: dict[str, Any],
    local_result: dict[str, Any],
    web_result: dict[str, Any],
    llm_result: dict[str, Any],
    patent_id: str | None = None,
) -> dict[str, Any]:
    return {
        "intent": intent,
        "scope": patent_id or local_result.get("patent_id"),  # UI scope 표시용
        "mode": local_result.get("mode"),
        "hit_count": local_result.get("hit_count", 0),
        "web_enabled": web_result.get("enabled"),
        "web_provider": web_result.get("provider"),
        "web_result_count": len(web_result.get("results") or []),
        "web_error": web_result.get("error"),
        "llm_used": bool(llm_result.get("ok")),
        "llm_model": llm_result.get("model"),
        "llm_error": llm_result.get("error"),
    }
