"""Text utilities for RAG prompts and source cards."""

from __future__ import annotations

from .quality import compact_text, filter_usable_hits


def format_hits_for_prompt(hits: list[dict[str, Any]], *, limit: int = 5, chars_per_hit: int = 900) -> str:
    lines: list[str] = []
    for index, hit in enumerate(filter_usable_hits(hits, limit=limit), 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        source_type = metadata.get("source_type") or "unknown"
        section = metadata.get("section_title") or metadata.get("file_name") or metadata.get("title") or "source"
        excerpt = compact_text(hit.get("excerpt") or hit.get("page_content"), chars_per_hit)
        lines.append(f"[{index}] {source_type} / {section}\n{excerpt}")
    return "\n\n".join(lines) if lines else "No local evidence."
