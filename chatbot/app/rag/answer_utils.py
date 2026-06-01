"""Answer formatting helpers."""

from __future__ import annotations

from typing import Any

from .text import compact_text


def fallback_answer(
    query: str,
    *,
    local_hits: list[dict[str, Any]],
    web_results: list[dict[str, Any]],
    llm_error: str | None = None,
) -> str:
    if not local_hits and not web_results:
        return (
            "관련 근거를 찾지 못했습니다.\n\n"
            "- 특허를 전체 범위로 바꾸거나 질문 키워드를 더 구체화해 주세요.\n"
            "- 감사 적용 후 vectorstore가 비어 있다면 감사 적용 또는 vectorstore 갱신을 먼저 실행해 주세요."
        )

    lines = [
        "LLM 답변 생성에 실패했거나 모델 응답이 비어 있어 검색 근거 기반으로 답변합니다.",
        "",
        "## 근거 요약",
    ]
    if llm_error:
        lines.insert(1, f"모델 상태: {llm_error}")
    for index, hit in enumerate(local_hits[:4], 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        source_type = metadata.get("source_type") or "unknown"
        section = metadata.get("section_title") or metadata.get("file_name") or metadata.get("title") or "근거"
        lines.append(f"{index}. {source_type} / {section}: {compact_text(hit.get('excerpt') or hit.get('page_content'), 220)}")
    if web_results:
        lines.append("")
        lines.append("## 웹 근거")
        for index, item in enumerate(web_results[:3], 1):
            lines.append(f"{index}. {item.get('title')}: {compact_text(item.get('snippet'), 220)}")
    return "\n".join(lines)


def build_metrics(
    *,
    intent: dict[str, Any],
    local_result: dict[str, Any],
    web_result: dict[str, Any],
    llm_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "intent": intent,
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
