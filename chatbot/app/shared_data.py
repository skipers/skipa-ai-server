"""Loader for PROJECT_ROOT/data/{patent_id}/ patent dataset.

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

from .config import SHARED_DATA_ROOT
from .index_rotation import active_documents_path, active_manifest_path, rotation_status, write_rotating_index


SHARED_VECTORSTORE_ROOT = SHARED_DATA_ROOT / "_vectorstore"
TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")

# Source types for shared data
SHARED_PATENT_SOURCE_TYPE = "SHARED_PATENT"
SHARED_REPORT_SOURCE_TYPE = "SHARED_REPORT"


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


# ---------------------------------------------------------------------------
# Patent folder listing
# ---------------------------------------------------------------------------

def list_shared_patent_ids() -> list[str]:
    """Return patent IDs that have at least parsed.json or report.json."""
    if not SHARED_DATA_ROOT.exists():
        return []
    ids = []
    for d in sorted(SHARED_DATA_ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("_") or d.name.startswith("."):
            continue
        if (d / "parsed.json").exists() or (d / "report.json").exists():
            ids.append(d.name)
    return ids


def shared_patent_summary(patent_id: str) -> dict[str, Any]:
    folder = SHARED_DATA_ROOT / patent_id
    parsed = _read_json(folder / "parsed.json")
    patent = parsed.get("normalized_patent") if isinstance(parsed.get("normalized_patent"), dict) else {}
    meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
    brief = parsed.get("brief_summary") if isinstance(parsed.get("brief_summary"), dict) else {}
    has_report = (folder / "report.json").exists()
    return {
        "patent_id": patent_id,
        "title": meta.get("title") or patent.get("title") or patent_id,
        "has_parsed": (folder / "parsed.json").exists(),
        "has_report": has_report,
        "has_pdf": (folder / "patent.pdf").exists(),
        "brief": brief.get("개요") or brief.get("핵심_내용") or "",
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
    source_path = str(SHARED_DATA_ROOT / patent_id / "parsed.json")
    base_meta = {
        "patent_id": patent_id,
        "source_type": SHARED_PATENT_SOURCE_TYPE,
        "title": title,
        "source_path": source_path,
        "relative_source_path": f"data/{patent_id}/parsed.json",
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
    source_path = str(SHARED_DATA_ROOT / patent_id / "report.json")
    base_meta = {
        "patent_id": patent_id,
        "source_type": SHARED_REPORT_SOURCE_TYPE,
        "source_path": source_path,
        "relative_source_path": f"data/{patent_id}/report.json",
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

    return docs


# ---------------------------------------------------------------------------
# Vectorstore build / search
# ---------------------------------------------------------------------------

def build_shared_vectorstore() -> dict[str, Any]:
    """Index all patents in SHARED_DATA_ROOT into a single vectorstore."""
    all_docs: list[dict[str, Any]] = []
    patent_ids = list_shared_patent_ids()
    for pid in patent_ids:
        folder = SHARED_DATA_ROOT / pid
        parsed = _read_json(folder / "parsed.json")
        if parsed:
            all_docs.extend(_parsed_to_docs(pid, parsed))
        report = _read_json(folder / "report.json")
        if report:
            all_docs.extend(_report_to_docs(pid, report))

    vs_root = SHARED_VECTORSTORE_ROOT
    manifest = {
        "scope": "shared_patents",
        "refreshed_at": _now(),
        "backend": "local_hashed_bow",
        "document_count": len(all_docs),
        "patent_count": len(patent_ids),
        "source": "shared_data_root",
    }
    rotation = write_rotating_index(vs_root, all_docs, manifest)
    return {
        "status": "built",
        "patent_count": len(patent_ids),
        "document_count": len(all_docs),
        "rotation": rotation,
    }


def search_shared_vectorstore(query: str, top_k: int = 8) -> dict[str, Any]:
    """Search the shared patent vectorstore."""
    docs_path = active_documents_path(SHARED_VECTORSTORE_ROOT)
    if not docs_path.exists():
        return {"query": query, "hit_count": 0, "hits": [], "mode": "shared_vectorstore"}

    q_tokens = _tokens(query)
    q_vec = _vectorize(query)

    def _dot(a: dict, b: dict) -> float:
        return sum(a.get(k, 0.0) * v for k, v in b.items())

    scored: list[tuple[float, dict]] = []
    for line in docs_path.open(encoding="utf-8"):
        try:
            doc = json.loads(line)
        except Exception:
            continue
        vec = doc.get("vector") if isinstance(doc.get("vector"), dict) else {}
        score = _dot(q_vec, {str(k): float(v) for k, v in vec.items()})
        scored.append((score, doc))

    scored.sort(key=lambda p: p[0], reverse=True)
    hits = []
    for score, doc in scored[:top_k]:
        meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        text = str(doc.get("page_content") or "")
        hits.append({
            "patent_id": meta.get("patent_id", ""),
            "score": round(score, 6),
            "excerpt": text[:360],
            "page_content": text,
            "metadata": meta,
        })

    return {
        "query": query,
        "hit_count": len(hits),
        "hits": hits,
        "mode": "shared_vectorstore",
        "documents_path": str(docs_path),
    }


def shared_vectorstore_status() -> dict[str, Any]:
    vs_root = SHARED_VECTORSTORE_ROOT
    manifest = _read_json(active_manifest_path(vs_root))
    return {
        "exists": active_manifest_path(vs_root).exists(),
        "document_count": manifest.get("document_count", 0),
        "patent_count": manifest.get("patent_count", 0),
        "refreshed_at": manifest.get("refreshed_at"),
        "vectorstore_path": str(vs_root),
        "rotation": rotation_status(vs_root),
    }
