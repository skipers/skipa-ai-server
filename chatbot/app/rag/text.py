"""Text utilities for RAG prompts and source cards."""

from __future__ import annotations

from typing import Any

from .quality import compact_text, filter_usable_hits

# 섹션 유형별 중요도에 따른 chars 할당 (평가/청구항은 더 많이)
_HIGH_PRIORITY_SECTIONS = {"자동 평가 점수", "LLM 평가 점수", "청구항", "보고서 메타정보", "종합 평가 요약"}


def format_hits_for_prompt(hits: list[dict[str, Any]], *, limit: int = 5, chars_per_hit: int = 1400) -> str:
    lines: list[str] = []
    for index, hit in enumerate(filter_usable_hits(hits, limit=limit), 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        source_type = metadata.get("source_type") or "unknown"
        section = metadata.get("section_title") or metadata.get("file_name") or metadata.get("title") or "source"
        # 중요 섹션은 더 많은 토큰 할당
        limit_chars = 1800 if section in _HIGH_PRIORITY_SECTIONS else chars_per_hit
        excerpt = compact_text(hit.get("excerpt") or hit.get("page_content"), limit_chars)
        lines.append(f"[{index}] {source_type} / {section}\n{excerpt}")
    return "\n\n".join(lines) if lines else "No local evidence."
