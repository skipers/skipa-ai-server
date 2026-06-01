"""Helpers for user-facing source cards and citations."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


TERM_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")


def compact_text(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _first_value(card: dict[str, Any], metadata: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = card.get(key)
        if value not in (None, ""):
            return value
        value = metadata.get(key)
        if value not in (None, ""):
            return value
    return None


def _clean_file_title(value: Any) -> str | None:
    if value in (None, ""):
        return None
    title = Path(str(value)).name
    title = re.sub(r"\.(jsonl|json|pdf|html|htm|md|txt|do|jsp|bin)$", "", title, flags=re.I)
    title = re.sub(r"[_-]{2,}", "_", title)
    title = title.strip(" _.-")
    return title or None


def source_display_title(card: dict[str, Any], metadata: dict[str, Any]) -> str:
    direct = _first_value(card, metadata, "display_title", "source_title")
    if direct:
        return compact_text(direct, 80)
    title = _first_value(card, metadata, "title", "document_title")
    section = _first_value(card, metadata, "section_title")
    if title and section and str(section) not in str(title):
        return compact_text(f"{title} / {section}", 90)
    if title:
        return compact_text(title, 80)
    if section:
        return compact_text(section, 80)
    file_title = _clean_file_title(_first_value(card, metadata, "file_name", "relative_source_path", "source_path"))
    if file_title:
        return compact_text(file_title, 80)
    source_type = _first_value(card, metadata, "source_type") or "근거 자료"
    return str(source_type)


def short_citation_title(card: dict[str, Any]) -> str:
    title = str(card.get("display_title") or card.get("title") or card.get("label") or "근거")
    title = re.sub(r"\s+", " ", title).strip()
    return compact_text(title, 34)


def source_path_value(card: dict[str, Any], metadata: dict[str, Any]) -> str | None:
    value = _first_value(
        card,
        metadata,
        "source_path",
        "relative_source_path",
        "file_name",
        "url",
        "source_url",
    )
    return str(value) if value not in (None, "") else None


def source_location_label(card: dict[str, Any], metadata: dict[str, Any]) -> str:
    parts: list[str] = []
    source_type = _first_value(card, metadata, "source_type", "document_type")
    if source_type:
        parts.append(str(source_type))
    page = _first_value(card, metadata, "page_no", "page")
    if page not in (None, ""):
        parts.append(f"p.{page}")
    section = _first_value(card, metadata, "section_title")
    if section:
        parts.append(f"섹션: {compact_text(section, 42)}")
    chunk = _first_value(card, metadata, "chunk_index", "chunk_id")
    if chunk not in (None, ""):
        parts.append(f"청크: {compact_text(chunk, 36)}")
    path = source_path_value(card, metadata)
    if path:
        parts.append(f"파일: {compact_text(Path(path).name, 48)}")
    return " · ".join(parts) or "근거 위치 정보 없음"


def match_terms_from_query(query: str | None, text: str, *, limit: int = 10) -> list[str]:
    if not query:
        return []
    text_lower = text.lower()
    terms: list[str] = []
    for term in TERM_RE.findall(query):
        normalized = term.lower()
        if normalized in text_lower and normalized not in [item.lower() for item in terms]:
            terms.append(term)
        if len(terms) >= limit:
            break
    return terms


def normalize_match_terms(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()][:12]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def enrich_source_card(card: dict[str, Any], *, query: str | None = None, index: int | None = None) -> dict[str, Any]:
    enriched = dict(card)
    metadata = dict(enriched.get("metadata") or {})
    label = str(enriched.get("label") or f"근거 {index or 1}")
    display_title = source_display_title(enriched, metadata)
    location_label = source_location_label(enriched, metadata)
    snippet = str(enriched.get("snippet") or enriched.get("excerpt") or metadata.get("evidence_excerpt") or "")
    existing_terms = normalize_match_terms(enriched.get("match_terms") or metadata.get("match_terms"))
    match_terms = existing_terms or match_terms_from_query(query, f"{display_title}\n{snippet}", limit=10)
    source_path = source_path_value(enriched, metadata)

    metadata.setdefault("citation_label", label)
    metadata.setdefault("source_title", display_title)
    metadata.setdefault("location_label", location_label)
    metadata.setdefault("source_path_for_display", source_path)
    metadata.setdefault("evidence_excerpt", snippet)
    if match_terms:
        metadata.setdefault("match_terms", match_terms)

    enriched.update(
        {
            "label": label,
            "display_title": display_title,
            "location_label": location_label,
            "source_path": source_path,
            "match_terms": match_terms,
            "metadata": metadata,
        }
    )
    return enriched


def enrich_source_cards(cards: list[dict[str, Any]], *, query: str | None = None) -> list[dict[str, Any]]:
    return [enrich_source_card(card, query=query, index=index) for index, card in enumerate(cards, 1)]


def replace_answer_citation_labels(answer: str, cards: list[dict[str, Any]]) -> str:
    rewritten = str(answer or "")
    replacements: list[tuple[str, str]] = []
    for card in cards:
        metadata = card.get("metadata") if isinstance(card.get("metadata"), dict) else {}
        label = str(metadata.get("citation_label") or card.get("label") or "").strip()
        title = short_citation_title(card)
        if not label or not title or label == title:
            continue
        replacements.append((label, title))

    for label, title in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        rewritten = rewritten.replace(f"[{label}]", f"[{title}]")
    return rewritten
