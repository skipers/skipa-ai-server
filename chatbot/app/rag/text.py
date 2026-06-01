"""Text utilities for RAG prompts and source cards."""

from __future__ import annotations

from typing import Any


def compact_text(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def format_hits_for_prompt(hits: list[dict[str, Any]], *, limit: int = 5, chars_per_hit: int = 900) -> str:
    lines: list[str] = []
    for index, hit in enumerate(hits[:limit], 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        source_type = metadata.get("source_type") or "unknown"
        section = metadata.get("section_title") or metadata.get("file_name") or metadata.get("title") or "source"
        excerpt = compact_text(hit.get("excerpt") or hit.get("page_content"), chars_per_hit)
        lines.append(f"[{index}] {source_type} / {section}\n{excerpt}")
    return "\n\n".join(lines) if lines else "No local evidence."
