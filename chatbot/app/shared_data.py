"""Loader for PROJECT_ROOT/data/patent/{patent_id}/ patent dataset.

Each patent folder contains:
  parsed.json   — normalized_patent, brief_summary, keywords
  report.json   — full eval_logic valuation report
  patent.pdf    — original PDF (not indexed, only referenced)
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .config import PROJECT_ROOT, SHARED_DATA_ROOT, SHARED_PATENT_ROOT
from .qdrant_store import collection_info, search_documents, shared_patents_collection, upsert_documents


SHARED_VECTORSTORE_ROOT = SHARED_DATA_ROOT / "_qdrant_shared_patents"
TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")

# Source types for shared data
SHARED_PATENT_SOURCE_TYPE = "SHARED_PATENT"
SHARED_REPORT_SOURCE_TYPE = "SHARED_REPORT"
SHARED_CORE_SOURCE_TYPES = frozenset({SHARED_PATENT_SOURCE_TYPE, SHARED_REPORT_SOURCE_TYPE})
_SOURCE_TYPE_ALIASES: dict[str, set[str]] = {
    "ORIGINAL_PDF": {SHARED_PATENT_SOURCE_TYPE},
    "PATENT_INPUT_JSON": {SHARED_PATENT_SOURCE_TYPE},
    "SHARED_PATENT": {SHARED_PATENT_SOURCE_TYPE},
    "REPORT_PDF": {SHARED_REPORT_SOURCE_TYPE},
    "REPORT_JSON": {SHARED_REPORT_SOURCE_TYPE},
    "APPLICATION_FEEDBACK_REPORT": {SHARED_REPORT_SOURCE_TYPE},
    "SHARED_REPORT": {SHARED_REPORT_SOURCE_TYPE},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text or "").lower())


def _vectorize(text: str) -> dict[str, float]:
    tokens = _tokens(text)
    if not tokens:
        return {}
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = len(tokens)
    return {t: round(c / total, 6) for t, c in counts.items()}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _doc_id(patent_id: str, suffix: str) -> str:
    seed = f"{patent_id}:{suffix}"
    return hashlib.sha1(seed.encode()).hexdigest()[:16]


def _safe_relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except Exception:
        return str(path)


def _iso_mtime(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return None


def _file_summary(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": str(path),
        "relative_path": _safe_relative(path),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
        "modified_at": _iso_mtime(path) if exists else None,
    }


def _shared_patent_dir(patent_id: str) -> Path | None:
    if not patent_id or "/" in patent_id or "\\" in patent_id:
        return None
    folder = SHARED_PATENT_ROOT / patent_id
    if not folder.is_dir():
        return None
    if not ((folder / "parsed.json").exists() or (folder / "report.json").exists()):
        return None
    return folder


def _normalize_shared_source_types(source_types: set[str] | None) -> set[str]:
    if source_types is None:
        return set(SHARED_CORE_SOURCE_TYPES)
    normalized: set[str] = set()
    for source_type in source_types:
        normalized.update(_SOURCE_TYPE_ALIASES.get(str(source_type), set()))
    return normalized


def is_shared_patent_id(patent_id: str | None) -> bool:
    return bool(patent_id and _shared_patent_dir(str(patent_id)))


# ---------------------------------------------------------------------------
# Patent folder listing
# ---------------------------------------------------------------------------

def list_shared_patent_ids() -> list[str]:
    """Return patent IDs that have at least parsed.json or report.json."""
    if not SHARED_PATENT_ROOT.exists():
        return []
    ids = []
    for d in sorted(SHARED_PATENT_ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("_") or d.name.startswith("."):
            continue
        if (d / "parsed.json").exists() or (d / "report.json").exists():
            ids.append(d.name)
    return ids


def shared_patent_summary(patent_id: str) -> dict[str, Any]:
    folder = SHARED_PATENT_ROOT / patent_id
    parsed = _read_json(folder / "parsed.json")
    patent = parsed.get("normalized_patent") if isinstance(parsed.get("normalized_patent"), dict) else {}
    meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
    brief = parsed.get("brief_summary") if isinstance(parsed.get("brief_summary"), dict) else {}
    has_report = (folder / "report.json").exists()
    all_chunks_estimate = len(_parsed_to_docs(patent_id, parsed)) + len(_report_to_docs(patent_id, _read_json(folder / "report.json")))
    return {
        "patent_id": patent_id,
        "title": meta.get("title") or patent.get("title") or patent_id,
        "patent_dir": str(folder),
        "relative_path": _safe_relative(folder),
        "updated_at": max(
            [value for value in [_iso_mtime(folder / "parsed.json"), _iso_mtime(folder / "report.json")] if value],
            default=None,
        ),
        "data_origin": "shared_project_data",
        "has_parsed": (folder / "parsed.json").exists(),
        "has_report": has_report,
        "has_pdf": (folder / "patent.pdf").exists(),
        "has_manifest": False,
        "has_latest_input": (folder / "parsed.json").exists(),
        "has_latest_pdf": (folder / "patent.pdf").exists(),
        "has_latest_report": has_report,
        "has_patent_index": False,
        "has_local_vectorstore": bool(collection_info(shared_patents_collection()).get("exists")),
        "has_qdrant_vectorstore": bool(collection_info(shared_patents_collection()).get("exists")),
        "chunk_count": all_chunks_estimate,
        "report_json_count": 1 if has_report else 0,
        "asset_count": 0,
        "manifest_path": None,
        "brief": brief.get("개요") or brief.get("핵심_내용") or "",
    }


def shared_patent_detail(patent_id: str, include_files: bool = True) -> dict[str, Any]:
    folder = _shared_patent_dir(patent_id)
    if folder is None:
        raise FileNotFoundError(patent_id)
    detail = shared_patent_summary(patent_id)
    parsed = _read_json(folder / "parsed.json")
    report = _read_json(folder / "report.json")
    detail["manifest"] = {
        "patent_id": patent_id,
        "title": detail.get("title"),
        "data_origin": "shared_project_data",
        "paths": {
            "parsed_json": str(folder / "parsed.json"),
            "report_json": str(folder / "report.json"),
            "patent_pdf": str(folder / "patent.pdf"),
        },
    }
    detail["paths"] = {
        "latest_input": _file_summary(folder / "parsed.json"),
        "latest_pdf": _file_summary(folder / "patent.pdf"),
        "latest_report": _file_summary(folder / "report.json"),
        "all_chunks": _file_summary(SHARED_VECTORSTORE_ROOT),
        "patent_index": _file_summary(SHARED_VECTORSTORE_ROOT),
        "local_vectorstore": collection_info(shared_patents_collection()),
        "qdrant_vectorstore": collection_info(shared_patents_collection()),
    }
    detail["parsed_summary"] = {
        "keys": sorted(parsed.keys()) if isinstance(parsed, dict) else [],
        "report_keys": sorted(report.keys()) if isinstance(report, dict) else [],
    }
    if include_files:
        detail["files"] = shared_list_files(patent_id, limit=300)
    return detail


def shared_list_files(patent_id: str, limit: int = 300) -> list[dict[str, Any]]:
    folder = _shared_patent_dir(patent_id)
    if folder is None:
        raise FileNotFoundError(patent_id)
    files = []
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            files.append(_file_summary(path))
        if len(files) >= limit:
            break
    return files


def shared_latest_json(patent_id: str, kind: str) -> dict[str, Any]:
    folder = _shared_patent_dir(patent_id)
    if folder is None:
        raise FileNotFoundError(patent_id)
    if kind == "input":
        path = folder / "parsed.json"
    elif kind == "report":
        path = folder / "report.json"
    else:
        raise ValueError(kind)
    if not path.exists():
        raise FileNotFoundError(path)
    return {"path": _file_summary(path), "data": _read_json(path)}


def shared_patent_chunks(
    patent_id: str,
    *,
    offset: int = 0,
    limit: int = 20,
    source_types: set[str] | None = None,
) -> dict[str, Any]:
    folder = _shared_patent_dir(patent_id)
    if folder is None:
        raise FileNotFoundError(patent_id)
    allowed = _normalize_shared_source_types(source_types)
    docs = _parsed_to_docs(patent_id, _read_json(folder / "parsed.json"))
    docs.extend(_report_to_docs(patent_id, _read_json(folder / "report.json")))
    items = []
    matched = 0
    for index, doc in enumerate(docs, 1):
        meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        if allowed and meta.get("source_type") not in allowed:
            continue
        if matched >= offset and len(items) < limit:
            items.append({**doc, "_line_no": index, "_chunk_file": "qdrant"})
        matched += 1
    return {
        "path": _file_summary(SHARED_VECTORSTORE_ROOT),
        "offset": offset,
        "limit": limit,
        "matched_count": matched,
        "items": items,
        "patent_id": patent_id,
        "chunk_file": "shared_docs",
    }


# ---------------------------------------------------------------------------
# Document builders
# ---------------------------------------------------------------------------

def _parsed_to_docs(patent_id: str, parsed: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    patent = parsed.get("normalized_patent") if isinstance(parsed.get("normalized_patent"), dict) else {}
    meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
    spec = patent.get("specification") if isinstance(patent.get("specification"), dict) else {}
    title = meta.get("title") or patent_id
    source_path = str(SHARED_PATENT_ROOT / patent_id / "parsed.json")
    base_meta = {
        "patent_id": patent_id,
        "source_type": SHARED_PATENT_SOURCE_TYPE,
        "title": title,
        "source_path": source_path,
        "relative_source_path": f"data/patent/{patent_id}/parsed.json",
        "file_name": "parsed.json",
    }

    def _make(text: str, section: str) -> dict[str, Any] | None:
        t = str(text or "").strip()
        if len(t) < 30:
            return None
        return {
            "doc_id": _doc_id(patent_id, section),
            "page_content": t[:20000],
            "vector": _vectorize(t),
            "metadata": {**base_meta, "section_title": section},
        }

    # Brief summary
    brief = parsed.get("brief_summary") if isinstance(parsed.get("brief_summary"), dict) else {}
    for k, v in brief.items():
        d = _make(str(v), f"요약_{k}")
        if d:
            docs.append(d)

    # Specification sections
    for key, label in [
        ("technical_field", "기술분야"),
        ("background_art", "배경기술"),
        ("problem_to_solve", "해결과제"),
        ("solution", "해결수단"),
        ("advantageous_effects", "효과"),
        ("description_text", "발명설명"),
        ("claims_raw_text", "청구항"),
    ]:
        v = spec.get(key) or patent.get(key) or ""
        d = _make(str(v), label)
        if d:
            docs.append(d)

    return docs


def _report_to_docs(patent_id: str, report_data: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    report = report_data.get("report") if isinstance(report_data.get("report"), dict) else {}
    valuation = report_data.get("valuation") if isinstance(report_data.get("valuation"), dict) else report
    source_path = str(SHARED_PATENT_ROOT / patent_id / "report.json")
    base_meta = {
        "patent_id": patent_id,
        "source_type": SHARED_REPORT_SOURCE_TYPE,
        "source_path": source_path,
        "relative_source_path": f"data/patent/{patent_id}/report.json",
        "file_name": "report.json",
    }

    def _make(text: str, section: str) -> dict[str, Any] | None:
        t = str(text or "").strip()
        if len(t) < 20:
            return None
        return {
            "doc_id": _doc_id(patent_id, f"report_{section}"),
            "page_content": t[:20000],
            "vector": _vectorize(t),
            "metadata": {**base_meta, "section_title": section},
        }

    # Iterate over common report structures
    active = valuation if isinstance(valuation, dict) and valuation else report
    if not active:
        return docs

    # section_1_summary
    s1 = active.get("section_1_summary") if isinstance(active.get("section_1_summary"), dict) else {}
    if s1:
        summary_text = json.dumps(s1, ensure_ascii=False)
        d = _make(summary_text, "평가요약")
        if d:
            docs.append(d)

    # Current eval_logic report structure used by PROJECT_ROOT/data/patent/{patent_id}/report.json
    for key, label in [
        ("meta", "보고서 메타정보"),
        ("auto_scores", "자동 평가 점수"),
        ("llm_scores", "LLM 평가 점수"),
        ("llm_sources", "LLM 평가 근거"),
        ("evidence", "평가 근거"),
        ("market_growth", "시장 성장성"),
        ("summary", "종합 평가 요약"),
        ("legal", "법적 상태"),
    ]:
        sec = active.get(key)
        if isinstance(sec, dict) and sec:
            d = _make(json.dumps(sec, ensure_ascii=False), label)
            if d:
                docs.append(d)
        elif isinstance(sec, list) and sec:
            d = _make(json.dumps(sec, ensure_ascii=False), label)
            if d:
                docs.append(d)
        elif isinstance(sec, str) and sec.strip():
            d = _make(sec, label)
            if d:
                docs.append(d)

    # Each section text
    for key, label in [
        ("section_2_technology", "기술성평가"),
        ("section_3_rights", "권리성평가"),
        ("section_4_business", "사업성평가"),
        ("section_5_market", "시장성평가"),
        ("section_6_similar", "유사특허분석"),
        ("section_7_opinion", "종합의견"),
    ]:
        sec = active.get(key)
        if isinstance(sec, dict):
            text = json.dumps(sec, ensure_ascii=False)
            d = _make(text, label)
            if d:
                docs.append(d)
        elif isinstance(sec, str) and sec.strip():
            d = _make(sec, label)
            if d:
                docs.append(d)

    known = {
        "section_1_summary",
        "section_2_technology",
        "section_3_rights",
        "section_4_business",
        "section_5_market",
        "section_6_similar",
        "section_7_opinion",
        "schema_version",
        "patent_id",
        "title",
        "meta",
        "legal",
        "auto_scores",
        "llm_scores",
        "llm_sources",
        "evidence",
        "market_growth",
        "summary",
    }
    for key, sec in active.items():
        if key in known:
            continue
        if isinstance(sec, (dict, list)) and sec:
            d = _make(json.dumps(sec, ensure_ascii=False), f"보고서_{key}")
            if d:
                docs.append(d)
        elif isinstance(sec, str) and sec.strip():
            d = _make(sec, f"보고서_{key}")
            if d:
                docs.append(d)

    return docs


# ---------------------------------------------------------------------------
# Vectorstore build / search
# ---------------------------------------------------------------------------

def build_shared_vectorstore() -> dict[str, Any]:
    """Index all patents in SHARED_PATENT_ROOT into the shared Qdrant collection."""
    all_docs: list[dict[str, Any]] = []
    patent_ids = list_shared_patent_ids()
    for pid in patent_ids:
        folder = SHARED_PATENT_ROOT / pid
        parsed = _read_json(folder / "parsed.json")
        if parsed:
            all_docs.extend(_parsed_to_docs(pid, parsed))
        report = _read_json(folder / "report.json")
        if report:
            all_docs.extend(_report_to_docs(pid, report))

    manifest = {
        "scope": "shared_patents",
        "refreshed_at": _now(),
        "backend": "qdrant",
        "document_count": len(all_docs),
        "patent_count": len(patent_ids),
        "source": "shared_patent_root",
        "shared_patent_root": str(SHARED_PATENT_ROOT),
    }
    qdrant = upsert_documents(
        shared_patents_collection(),
        all_docs,
        collection_scope="shared_patents",
        recreate=True,
        extra_payload={"index_scope": "shared_patents"},
    )
    return {
        "status": "built",
        "backend": "qdrant",
        "patent_count": len(patent_ids),
        "document_count": len(all_docs),
        "collection": qdrant["collection"],
        "qdrant": qdrant,
        "manifest": manifest,
    }


def search_shared_vectorstore(
    query: str,
    top_k: int = 8,
    *,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
) -> dict[str, Any]:
    """Search the shared patent Qdrant collection."""
    allowed_source_types = _normalize_shared_source_types(source_types)
    result = search_documents(
        shared_patents_collection(),
        query,
        top_k=top_k,
        patent_id=patent_id,
        source_types=allowed_source_types,
    )
    return {
        **result,
        "mode": "shared_qdrant_search",
        "source_types": sorted(allowed_source_types),
    }


def shared_vectorstore_status() -> dict[str, Any]:
    info = collection_info(shared_patents_collection())
    return {
        "backend": "qdrant",
        "exists": info.get("exists", False),
        "document_count": info.get("points_count", 0),
        "patent_count": len(list_shared_patent_ids()),
        "refreshed_at": None,
        "collection": shared_patents_collection(),
        "qdrant": info,
    }
