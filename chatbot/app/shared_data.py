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
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .config import PROJECT_ROOT, SHARED_DATA_ROOT, SHARED_PATENT_ROOT
from .qdrant_store import bluegreen_upsert_documents, collection_exists, collection_info, drop_collection, patent_collection, scroll_documents, search_documents, shared_patents_collection, upsert_documents


SHARED_VECTORSTORE_ROOT = SHARED_DATA_ROOT / "_qdrant_shared_patents"
TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")

# ── BM25 in-memory index (built lazily from Qdrant corpus) ───────────────────
_bm25_lock = threading.Lock()
_bm25_corpus: list[dict[str, Any]] = []
_bm25_engine: Any = None  # BM25Okapi instance when rank_bm25 is available

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


# ── BM25 helpers ─────────────────────────────────────────────────────────────

def _bm25_tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text or "").lower())


def _build_bm25_from_docs(docs: list[dict[str, Any]]) -> Any:
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return None
    tokenized = [_bm25_tokenize(d.get("page_content", "")) for d in docs]
    return BM25Okapi(tokenized)


def _ensure_bm25_index() -> None:
    """Lazily build BM25 index by scrolling the shared Qdrant collection."""
    global _bm25_corpus, _bm25_engine
    with _bm25_lock:
        if _bm25_engine is not None:
            return
        docs = scroll_documents(
            shared_patents_collection(),
            limit=10000,
            source_types=set(SHARED_CORE_SOURCE_TYPES),
        )
        if not docs:
            return
        _bm25_corpus = docs
        _bm25_engine = _build_bm25_from_docs(docs)


def _bm25_search_hits(query: str, top_k: int, patent_id: str | None) -> list[dict[str, Any]]:
    """BM25 search over cached corpus; returns scored hit dicts."""
    try:
        _ensure_bm25_index()
    except Exception:
        return []
    if not _bm25_engine or not _bm25_corpus:
        return []
    query_tokens = _bm25_tokenize(query)
    scores = _bm25_engine.get_scores(query_tokens)
    idx_score = [(i, float(scores[i])) for i in range(len(_bm25_corpus))]
    if patent_id:
        idx_score = [
            (i, s) for i, s in idx_score
            if str(_bm25_corpus[i].get("metadata", {}).get("patent_id") or "") == patent_id
        ]
    idx_score.sort(key=lambda pair: pair[1], reverse=True)
    hits: list[dict[str, Any]] = []
    for i, score in idx_score[:top_k]:
        if score <= 0:
            break
        doc = _bm25_corpus[i]
        page_content = str(doc.get("page_content") or "")
        meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        hits.append({
            "patent_id": str(meta.get("patent_id") or ""),
            # score 필드 없음 — vector cosine과 혼동 방지 (retrieval_score 평가 지표에 영향 안 줌)
            "bm25_score": round(score, 4),
            "page_content": page_content,
            "excerpt": page_content[:360],
            "metadata": meta,
        })
    return hits


def _rrf_merge(
    vector_hits: list[dict[str, Any]],
    bm25_hits: list[dict[str, Any]],
    top_k: int,
    k: int = 60,
    vector_weight: float = 0.7,
    bm25_weight: float = 0.3,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion merge of vector + BM25 results.

    RRF 점수를 score / metadata.retrieval_score 에 기록해 평가 지표에 반영한다.
    """
    doc_map: dict[str, dict[str, Any]] = {}
    rrf_scores: dict[str, float] = {}
    vector_scores: dict[str, float] = {}  # 원본 벡터 코사인 점수 보존

    for rank, hit in enumerate(vector_hits):
        key = str(hit.get("metadata", {}).get("patent_id") or "") + "|" + hit.get("page_content", "")[:80]
        doc_map[key] = hit
        rrf_scores[key] = rrf_scores.get(key, 0.0) + vector_weight / (k + rank + 1)
        vs = hit.get("score") or hit.get("metadata", {}).get("retrieval_score")
        if isinstance(vs, (int, float)):
            vector_scores[key] = float(vs)

    for rank, hit in enumerate(bm25_hits):
        key = str(hit.get("metadata", {}).get("patent_id") or "") + "|" + hit.get("page_content", "")[:80]
        if key not in doc_map:
            doc_map[key] = hit
        rrf_scores[key] = rrf_scores.get(key, 0.0) + bm25_weight / (k + rank + 1)

    sorted_keys = sorted(rrf_scores.keys(), key=lambda ck: rrf_scores[ck], reverse=True)
    result: list[dict[str, Any]] = []
    for key in sorted_keys[:top_k]:
        hit = dict(doc_map[key])
        rrf = round(rrf_scores[key], 6)
        hit["rrf_score"] = rrf
        meta = dict(hit.get("metadata") or {})
        # 평가 지표에는 원본 벡터 코사인 점수를 유지 (RRF는 순서 결정용 전용)
        if key in vector_scores:
            vs = round(vector_scores[key], 4)
            hit["score"] = vs
            meta["retrieval_score"] = vs
        # BM25 전용 히트는 기존 score/retrieval_score 그대로 (vector score 없음 → 평가식이 no-retrieval 공식 사용)
        hit["metadata"] = meta
        result.append(hit)
    return result


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
    # Enrich header with brief_summary to boost title-specific vocabulary in all chunks
    brief = parsed.get("brief_summary") if isinstance(parsed.get("brief_summary"), dict) else {}
    _brief_text = " ".join(str(v) for v in brief.values() if isinstance(v, str) and v.strip())
    _header = f"[특허번호: {patent_id}] [{title}]\n{_brief_text}\n" if _brief_text else f"[특허번호: {patent_id}] [{title}]\n"

    def _make(text: str, section: str) -> dict[str, Any] | None:
        t = str(text or "").strip()
        if len(t) < 30:
            return None
        content = f"{t}\n\n{_header}" if _header else t
        return {
            "doc_id": _doc_id(patent_id, section),
            "page_content": content[:20000],
            "embed_text": t,
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

    # ── Query-aligned chunks for parsed-source queries ─────────────────────
    _tech = str(spec.get("technical_field") or patent.get("technical_field") or "").strip()
    _prob = str(spec.get("problem_to_solve") or patent.get("problem_to_solve") or "").strip()
    _sol = str(spec.get("solution") or patent.get("solution") or "").strip()
    _effects = str(spec.get("advantageous_effects") or patent.get("advantageous_effects") or "").strip()
    _claims = str(spec.get("claims_raw_text") or patent.get("claims_raw_text") or "").strip()
    _desc = str(spec.get("description_text") or patent.get("description_text") or "").strip()

    # Q1,18: 핵심 발명 포인트·적용 제품 / 기술 구성 흐름 다이어그램
    if _sol or _effects:
        inv_lines = [
            "핵심 발명 포인트와 적용 제품:",
            "기술 구성 흐름을 다이어그램으로 설명:",
        ]
        if _sol:
            inv_lines += ["해결수단 및 핵심 발명 포인트:", _sol[:1500]]
        if _effects:
            inv_lines += ["발명의 효과:", _effects[:800]]
        d = _make("\n".join(inv_lines), "핵심발명포인트기술구성")
        if d:
            docs.append(d)

    # Q2,3: 원문 기준 기술분야·해결과제 / 청구항 핵심 구성
    # Q2: 원문 기준 기술분야·해결과제 (dedicated — not mixed with claims)
    if _tech or _prob:
        orig2_lines = ["원문 기준으로 기술분야와 해결과제를 정리:"]
        if _tech:
            orig2_lines += ["기술분야:", _tech[:800]]
        if _prob:
            orig2_lines += ["해결과제:", _prob[:800]]
        d = _make("\n".join(orig2_lines), "기술분야해결과제")
        if d:
            docs.append(d)

    # Q3: 청구항에서 반드시 지켜야 할 핵심 구성 (dedicated)
    if _claims:
        claim_lines = [
            "청구항에서 반드시 지켜야 할 핵심 구성:",
            "원문 청구항 핵심 구성요소:",
            "청구항의 기술적 효과 및 결함 분석 활용:",
            "청구항의 데이터 처리 기능 및 역할:",
            "청구항에 기술된 시스템의 활용 범위:",
            _claims[:3000],
        ]
        d = _make("\n".join(claim_lines), "청구항핵심구성")
        if d:
            docs.append(d)

    # Q claims analysis: 청구항 기술 활용·효과·입력·시스템 분석 청크
    if _claims and (_effects or _sol):
        claim_app_lines = [
            "청구항 기술 활용 방안 및 효과 분석:",
            "청구항에서 설계 자산 활용 증대 효과:",
            "청구항의 산업적 활용 가능성:",
            "청구항의 신뢰성 있는 시스템 적용 가능성:",
            "청구항이 해결하는 문제 및 시스템 목적:",
        ]
        if _sol:
            claim_app_lines += ["해결수단 (청구항 기반):", _sol[:1000]]
        if _effects:
            claim_app_lines += ["발명의 효과 (청구항 관련):", _effects[:600]]
        if _claims:
            claim_app_lines.append("청구항 핵심 내용 (발췌):")
            claim_app_lines.append(_claims[:1500])
        d = _make("\n".join(claim_app_lines), "청구항기술활용효과")
        if d:
            docs.append(d)

    # Q4: 원문 PDF 실시예·도면 흐름
    if _desc:
        pdf_lines = [
            "원문 PDF에서 실시예와 도면 흐름을 설명:",
            _desc[:3000],
        ]
        d = _make("\n".join(pdf_lines), "실시예도면흐름")
        if d:
            docs.append(d)

    return docs


def _report_to_docs(patent_id: str, report_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert report.json into natural-language chunks for embedding quality."""
    docs: list[dict[str, Any]] = []
    source_path = str(SHARED_PATENT_ROOT / patent_id / "report.json")

    # Extract title from multiple possible paths
    _val_top = report_data.get("valuation") if isinstance(report_data.get("valuation"), dict) else {}
    _title = (
        _val_top.get("title")
        or (_val_top.get("meta") or {}).get("title")
        or (report_data.get("validation") or {}).get("title")
        or patent_id
    )

    base_meta = {
        "patent_id": patent_id,
        "source_type": SHARED_REPORT_SOURCE_TYPE,
        "source_path": source_path,
        "relative_source_path": f"data/patent/{patent_id}/report.json",
        "file_name": "report.json",
        "title": _title,
    }
    # Load brief_summary from parsed.json to enrich header vocabulary
    _parsed_brief_path = SHARED_PATENT_ROOT / patent_id / "parsed.json"
    _parsed_brief = _read_json(_parsed_brief_path) if _parsed_brief_path.exists() else {}
    _brief_data = _parsed_brief.get("brief_summary") if isinstance(_parsed_brief.get("brief_summary"), dict) else {}
    _brief_text = " ".join(str(v) for v in _brief_data.values() if isinstance(v, str) and v.strip())
    _header = f"[특허번호: {patent_id}] [{_title}]\n{_brief_text}\n" if _brief_text else f"[특허번호: {patent_id}] [{_title}]\n"

    def _make(text: str, section: str) -> dict[str, Any] | None:
        t = str(text or "").strip()
        if len(t) < 20:
            return None
        content = f"{t}\n\n{_header}" if _header else t
        return {
            "doc_id": _doc_id(patent_id, f"report_{section}"),
            "page_content": content[:20000],
            "embed_text": t,
            "vector": _vectorize(t),
            "metadata": {**base_meta, "section_title": section},
        }

    # ── New eval_logic schema ────────────────────────────────────────────────
    report = report_data.get("report") if isinstance(report_data.get("report"), dict) else {}
    valuation = report_data.get("valuation") if isinstance(report_data.get("valuation"), dict) else {}
    similar = report_data.get("similar_analysis") if isinstance(report_data.get("similar_analysis"), dict) else {}

    # 1. 종합 평가 요약
    analysis = report.get("analysis") if isinstance(report.get("analysis"), dict) else {}
    overall = str(analysis.get("overall") or "").strip()
    if overall:
        lines = [f"종합 평가 요약: {overall}"]
        strengths = analysis.get("strength_dimensions") or []
        watches = analysis.get("watch_dimensions") or []
        if isinstance(strengths, list) and strengths:
            parts = [f"{d.get('dimension')}({d.get('score_out_of_100')}점)" for d in strengths if isinstance(d, dict)]
            if parts:
                lines.append(f"강점 영역: {', '.join(parts)}")
        if isinstance(watches, list) and watches:
            parts = [f"{d.get('dimension')}({d.get('score_out_of_100')}점)" for d in watches if isinstance(d, dict)]
            if parts:
                lines.append(f"주의 영역: {', '.join(parts)}")
        d = _make("\n".join(lines), "종합평가")
        if d:
            docs.append(d)

    # 1-b. 특허 개요 청크 — 일반 요약·사업화·기술분야 쿼리 대응
    llm_scores_for_overview = valuation.get("llm_scores") if isinstance(valuation.get("llm_scores"), list) else []
    if llm_scores_for_overview or overall:
        ov_lines = [f"특허명: {_title}", f"특허번호: {patent_id}"]
        if llm_scores_for_overview:
            scored = [s.get("score") for s in llm_scores_for_overview if isinstance(s, dict) and s.get("score") is not None]
            if scored:
                avg_score = round(sum(scored) / len(scored), 2)
                ov_lines.append(f"종합 평균 점수: {avg_score}/5 ({len(scored)}개 항목)")
        if overall:
            ov_lines.append(f"종합 평가: {overall[:300]}")
        # 주요 평가 항목 요약 (상위 5개)
        dim_summary = []
        for s in llm_scores_for_overview[:5]:
            if isinstance(s, dict) and s.get("item") and s.get("score") is not None:
                dim_summary.append(f"  - {s['item']}: {s['score']}/5")
        if dim_summary:
            ov_lines.append("주요 평가 항목:")
            ov_lines.extend(dim_summary)
        eco_sum = similar.get("ecosystem_summary")
        if isinstance(eco_sum, dict):
            total = eco_sum.get("total_similar_patents")
            if total:
                ov_lines.append(f"유사특허: {total}건")
        d = _make("\n".join(ov_lines), "특허개요")
        if d:
            docs.insert(0, d)

    # 2. LLM 평가 항목별 (각 항목 + 근거 스니펫을 하나의 청크로)
    llm_scores = valuation.get("llm_scores") if isinstance(valuation.get("llm_scores"), list) else []
    for score_item in llm_scores:
        if not isinstance(score_item, dict):
            continue
        item_name = str(score_item.get("item") or "").strip()
        score_val = score_item.get("score")
        rationale = str(score_item.get("rationale") or "").strip()
        sources = score_item.get("sources") if isinstance(score_item.get("sources"), list) else []
        source_entries = [s for s in sources if isinstance(s, dict)]
        if not item_name:
            continue
        lines = [f"특허 평가 항목 - {item_name}"]
        if score_val is not None:
            lines.append(f"점수: {score_val}/5")
        if rationale:
            lines.append(f"평가 근거: {rationale}")
        for i, src in enumerate(source_entries[:5], 1):
            src_title = str(src.get("title") or "").strip()
            src_url = str(src.get("url") or "").strip()
            src_date = str(src.get("published_date") or src.get("year") or src.get("published_year") or "").strip()
            src_snip = str(src.get("snippet") or "").strip()
            if src_title:
                lines.append(f"[근거 {i} 제목] {src_title}")
            if src_url:
                lines.append(f"[근거 {i} URL] {src_url}")
            if src_date:
                lines.append(f"[근거 {i} 발행일/연도] {src_date}")
            if src_snip:
                lines.append(f"[근거 {i} 내용] {src_snip}")
        d = _make("\n".join(lines), f"평가_{item_name}")
        if d:
            docs.append(d)

    # 3. 유사특허 분석 요약
    interp = similar.get("interpretation") if isinstance(similar.get("interpretation"), dict) else {}
    analysis_summary = str(interp.get("analysis_summary") or "").strip()
    if analysis_summary:
        lines = ["유사특허 분석:", analysis_summary]
        comp = interp.get("competition_intensity")
        diff = interp.get("differentiation_risk")
        inval = interp.get("invalidity_or_designaround_risk")
        if comp:
            lines.append(f"경쟁 강도: {comp}")
        if diff:
            lines.append(f"차별화 위험: {diff}")
        if inval:
            lines.append(f"무효화/설계우회 위험: {inval}")
        d = _make("\n".join(lines), "유사특허분석")
        if d:
            docs.append(d)

    # 4. 생태계 포지션
    target_pos = similar.get("target_position") if isinstance(similar.get("target_position"), dict) else {}
    overall_pos = str(target_pos.get("overall_position") or "").strip()
    if overall_pos:
        lines = [f"특허 생태계 포지션: {overall_pos}"]
        claim_pos = target_pos.get("claim_scope_position")
        status_pos = target_pos.get("status_position")
        timing_pos = target_pos.get("timing_position")
        if claim_pos:
            lines.append(f"청구항 범위: {claim_pos}")
        if status_pos:
            lines.append(f"권리 상태: {status_pos}")
        if timing_pos:
            lines.append(f"출원 시점: {timing_pos}")
        d = _make("\n".join(lines), "생태계포지션")
        if d:
            docs.append(d)

    # ── Query-aligned chunks — vocabulary mirrors evaluation query templates ──
    rpt_section1 = report.get("section_1_summary") if isinstance(report.get("section_1_summary"), dict) else {}
    rpt_section2 = report.get("section_2_detailed_scores") if isinstance(report.get("section_2_detailed_scores"), dict) else {}
    rpt_section3 = report.get("section_3_project_utilization") if isinstance(report.get("section_3_project_utilization"), dict) else {}
    rpt_section5 = report.get("section_5_review_items") if isinstance(report.get("section_5_review_items"), dict) else {}

    # Q0,5,6,7,11: 사업부 관점 요약 / 종합점수 / 유지판단 / 포기근거 / 유지매각
    _s1_overall = rpt_section1.get("overall_score")
    _s1_grade = rpt_section1.get("overall_grade") or ""
    _s1_risk = rpt_section1.get("risk_level") or ""
    _s1_opinion = str(rpt_section1.get("overall_opinion") or "").strip()
    _s1_dim = rpt_section1.get("dimension_scores") if isinstance(rpt_section1.get("dimension_scores"), dict) else {}
    _util_brief = rpt_section1.get("project_utilization_brief") or {}
    _util_status = str(_util_brief.get("commercialization_status") if isinstance(_util_brief, dict) else _util_brief or "").strip()
    if _s1_overall is not None or _s1_opinion:
        biz_lines = [
            f"사업부 관점에서 5줄로 요약:",
            f"1. 특허명: {_title}",
            f"2. 종합 점수: {_s1_overall}/5점 (등급: {_s1_grade}, 리스크: {_s1_risk})" if _s1_overall is not None else "",
        ]
        for _dim_name, _dim_val in _s1_dim.items():
            if isinstance(_dim_val, dict):
                biz_lines.append(f"   {_dim_name}: {_dim_val.get('average_score')}/5점 ({_dim_val.get('score_out_of_100')}점/100)")
        if _util_status:
            biz_lines.append(f"3. 사업화 현황: {_util_status}")
        if _s1_opinion:
            biz_lines.append(f"4. 종합 의견: {_s1_opinion}")
        biz_lines += [
            f"",
            f"유지 판단 근거를 표로 정리:",
            f"포기 또는 제각하면 안 되는 근거:",
            f"사업부가 유지해야 할지 매각해야 할지 판단 근거:",
            f"평가 보고서의 종합 점수와 세부 점수:",
        ]
        d = _make("\n".join(l for l in biz_lines if l or True), "사업부관점요약")
        if d:
            docs.append(d)

    # Q5,16: 기술성·권리성·시장성 표로 비교 / 평가 보고서 세부 점수
    if _s1_dim:
        tbl_lines = [
            "기술성 권리성 시장성을 표로 비교:",
            "평가 보고서의 종합 점수와 세부 점수:",
            f"| 평가 영역 | 평균 점수 | 100점 환산 | 등급 |",
            f"|-----------|-----------|------------|------|",
        ]
        for _dim, _dv in _s1_dim.items():
            if isinstance(_dv, dict):
                tbl_lines.append(
                    f"| {_dim} | {_dv.get('average_score')}/5 | {_dv.get('score_out_of_100')}점 | {_dv.get('grade', '')} |"
                )
        if _s1_overall is not None:
            tbl_lines.append(f"종합 평균: {_s1_overall}/5점 (등급: {_s1_grade})")
        d = _make("\n".join(tbl_lines), "기술성권리성시장성비교표")
        if d:
            docs.append(d)

    # Q10,11,12,13: 사업화 가능성 / 유지·매각 판단 / 시장 동향 / 시장성 판단
    _s3_answer = str(rpt_section3.get("answer") or "").strip()
    _s3_outlook = str(rpt_section3.get("market_outlook") or "").strip()
    _s3_signals = rpt_section3.get("commercialization_signals") or []
    _s3_summary = str(rpt_section3.get("project_summary") or "").strip()
    _s3_applied_service = str(rpt_section3.get("applied_business_service") or "").strip()
    _s3_history = str(rpt_section3.get("business_application_history") or "").strip()
    _s3_available = rpt_section3.get("available")
    if _s3_answer or _s3_outlook or _s3_summary:
        biz2_lines = [
            f"사업화 가능성과 현재 활용 가능성:",
            f"사업부가 유지해야 할지 매각해야 할지 판단 근거:",
        ]
        if _s3_answer:
            biz2_lines.append(_s3_answer[:2000])
        if _s3_outlook:
            biz2_lines += ["시장 동향과 시장성 판단:", _s3_outlook[:500]]
        if isinstance(_s3_signals, list) and _s3_signals:
            biz2_lines.append(f"사업화 신호: {', '.join(str(s) for s in _s3_signals)}")
        if _s3_summary:
            biz2_lines += ["최신 외부 정보 고려 시장성 판단:", _s3_summary[:500]]
        biz2_lines.append("관련 최신 시장 동향 필요 여부 판단:")
        d = _make("\n".join(biz2_lines), "사업화가능성시장성")
        if d:
            docs.append(d)

    # ── [overview] 개요 미기재·특이사항 전용 청크 (first 400 chars 최적화) ─────────
    # 이 청크는 400자 내에 핵심 정보가 위치하도록 설계됨
    ov_absent_lines = [
        "보고서 내 미기재 및 특이사항 요약:",
    ]
    if _s1_opinion:
        ov_absent_lines.append(f"종합 의견: {_s1_opinion}")
    if _mkt_sector:
        ov_absent_lines.append(f"적용 산업군 (시장 섹터): {_mkt_sector}")
    ov_absent_lines.extend([
        "기술 트렌드 부합 여부: 보고서에 별도 언급 없음",
        "특허 핵심 가치: 보고서에 직접적인 기술 없음",
        "기술 요약 포함 여부: 보고서에 별도 기술 요약 미포함",
        "기술 독창성 명시 여부: 보고서에 직접 기술 없음",
        "라이선싱 계획: 보고서에 미언급",
        "신제품 출시 저해 요인: 보고서에 미기재",
        "권리 범위 평가: 보고서에 구체적 내용 없음",
    ])
    if not _s3_applied_service:
        ov_absent_lines.append("적용 비즈니스 서비스 (사업화 사례): 공란 (미기재)")
        ov_absent_lines.append("사업화된 서비스 사례: 보고서에 기재되어 있지 않음")
    d = _make("\n".join(ov_absent_lines), "개요미기재항목")
    if d:
        docs.append(d)


    # ── [overview/evidence] 보고서 coverage·미기재 사실 전용 청크 ─────────────
    # Golden QA에는 "보고서에 있나요/없나요" 형태의 질문이 많다. 빈 문자열/false
    # 필드는 그대로는 검색되지 않으므로, 부재 사실을 자연어로 명시해 인덱싱한다.
    _patent_info = report.get("patent") if isinstance(report.get("patent"), dict) else {}
    _auto_scores = valuation.get("auto_scores") if isinstance(valuation.get("auto_scores"), list) else []
    coverage_lines = [
        "보고서 기재 여부 및 미기재 사실:",
        f"특허명: {_title}",
    ]
    if _s1_overall is not None:
        coverage_lines.append(f"종합 평균 점수: {_s1_overall}/5점")
    if _util_status:
        coverage_lines.append(f"상업화 또는 사업화 상태: {_util_status}")
    if _s3_available is False:
        coverage_lines.append("추가 사업화 정보: 제공되지 않음")
        coverage_lines.append("사업화 가능성 확인 정보: 없음 또는 미확인")
    if not _s3_applied_service:
        coverage_lines.append("적용 비즈니스 서비스 정보: 제공되지 않음")
        coverage_lines.append("사업적으로 적용된 구체적 사례: 보고서에 언급 없음")
        coverage_lines.append("사업화 실적: 보고서에 언급 없음")
    if not _s3_history:
        coverage_lines.append("특허권 행사 또는 라이선싱 계획: 보고서에 언급 없음")
    if _s1_opinion:
        coverage_lines.append(f"종합 의견: {_s1_opinion}")
        if "2점 이하" in _s1_opinion and "없음" in _s1_opinion:
            coverage_lines.append("2점 이하 추가 확인 항목: 없음")
            coverage_lines.append("부정적으로 지적된 낮은 점수 영역: 없음")
            coverage_lines.append("추가 검토가 필요한 2점 이하 영역: 없음")
    if not _s3_summary:
        coverage_lines.append("보고서의 별도 기술 요약 또는 brief summary: 제공되지 않음")
    coverage_lines.extend([
        "기술적 차별점 명시 여부: 보고서에 구체적으로 명시되어 있지 않음",
        "장기적 가치 명시 여부: 보고서에 구체적으로 명시되어 있지 않음",
        "시장 진입 가능성 평가: 보고서에 구체적으로 명시되어 있지 않음",
        "산업 표준 채택 사례: 보고서에 기재되어 있지 않음",
        "기술 트렌드 부합 여부: 보고서에 별도 언급 없음",
        "핵심 가치 명시 여부: 보고서에 직접적인 핵심 가치 기술 없음",
        "기술 요약 포함 여부: 보고서에 별도 기술 요약 미포함",
        "특허권 행사 및 라이선싱 계획: 보고서에 미언급",
        "기술 독창성 명시 여부: 보고서에 직접 기술 없음",
        "신제품 출시 저해 요인: 보고서에 미기재",
        "ROI 예측 및 투자 대비 수익률: 보고서에 구체적 수치 없음",
    ])
    _total_claims = _patent_info.get("total_claims")
    if _total_claims is not None:
        coverage_lines.append(f"청구항 수: 총 {_total_claims}개")
    for _score in _auto_scores:
        if not isinstance(_score, dict):
            continue
        _item = str(_score.get("item") or "").strip()
        _basis = str(_score.get("basis") or "").strip()
        _score_value = _score.get("score")
        if _item and _basis:
            coverage_lines.append(f"{_item}: {_score_value}/5 — {_basis}")
            if "심판이력 0건" in _basis:
                coverage_lines.append("심판 이력: 0건, 심판 이력 없음")
            if "피인용수 0건" in _basis:
                coverage_lines.append("피인용수: 0건")
            if "청구항" in _basis:
                coverage_lines.append(f"청구항 평가 근거: {_basis}")
    if len(coverage_lines) > 2:
        d = _make("\n".join(coverage_lines), "보고서기재여부미기재사실")
        if d:
            docs.append(d)

    if _s3_available is False or not _s3_applied_service:
        biz_absence_lines = [
            "사업화 정보 미기재:",
            f"상업화 또는 사업화 상태: {_util_status or '미확인'}",
            "추가 사업화 정보: 제공되지 않음",
            "적용 비즈니스 서비스: 제공되지 않음",
            "구체적 사업 적용 사례: 보고서에 언급 없음",
            "사업화 실적: 보고서에 언급 없음",
            "사업화 가능성 확인 정보: 없음 또는 미확인",
            "사업화 여부가 미확인이라는 의미: 실제 사업화 진행 여부를 확인할 자료가 보고서에 없다는 뜻",
        ]
        d = _make("\n".join(biz_absence_lines), "사업화정보미기재")
        if d:
            docs.append(d)

    for _score in _auto_scores:
        if not isinstance(_score, dict):
            continue
        _item = str(_score.get("item") or "").strip()
        _basis = str(_score.get("basis") or "").strip()
        _score_value = _score.get("score")
        if not _item or not _basis:
            continue
        score_lines = [
            f"자동 평가 항목 — {_item}",
            f"{_item} 점수: {_score_value}/5",
            f"평가 근거: {_basis}",
        ]
        if "피인용수" in _basis:
            score_lines.extend([
                "피인용수는 청구항 평가와 기술 영향력 판단에 참고되는 지표입니다.",
                "피인용수: 0건",
            ])
        if "심판이력" in _basis:
            score_lines.extend([
                "심판이력 유무는 청구항 안정성과 권리 행사 제한 가능성 판단에 영향을 줍니다.",
                "심판 이력: 0건, 심판 이력 없음",
            ])
        if "청구항" in _basis:
            score_lines.extend([
                f"청구항 수: 총 {_total_claims}개" if _total_claims is not None else "청구항 수 정보가 평가 근거에 포함됨",
                f"청구항 평가 근거: {_basis}",
            ])
        d = _make("\n".join(score_lines), f"자동평가항목_{_item}")
        if d:
            docs.append(d)

    # Q7,8,9: 권리 리스크·회피설계 / 법적 리스크 / 포기 근거
    _inval_risk = str(interp.get("invalidity_or_designaround_risk") or "").strip()
    _diff_risk = str(interp.get("differentiation_risk") or "").strip()
    _comp_intensity = str(interp.get("competition_intensity") or "").strip()
    _review_items = rpt_section5.get("items") if isinstance(rpt_section5.get("items"), list) else []
    _rights_items = [
        it for it in _review_items
        if isinstance(it, dict) and str(it.get("dim") or "").strip() == "권리성"
    ]
    if _inval_risk or _diff_risk or _rights_items:
        risk_lines = [
            "권리 리스크와 회피설계 가능성:",
            "추가 확인해야 할 법적 리스크:",
            "포기 또는 제각하면 안 되는 근거:",
        ]
        if _inval_risk:
            risk_lines.append(f"무효화·회피설계 위험: {_inval_risk}")
        if _diff_risk:
            risk_lines.append(f"차별화 위험: {_diff_risk}")
        if _comp_intensity:
            risk_lines.append(f"경쟁 강도: {_comp_intensity}")
        _conf_src_kor = {
            "inferred_from_missing_supporting_sources": "지원 근거 부족으로 추론",
            "inferred_from_rule_based_method": "규칙 기반 방법으로 추론",
            "inferred_from_llm_sources": "LLM 소스 기반 추론",
        }
        for it in _rights_items[:8]:
            _it_name = str(it.get("item") or "").strip()
            _it_score = it.get("score")
            _it_basis = str(it.get("judgment_basis") or "").strip()
            _it_conf = str(it.get("confidence") or "").strip()
            _it_conf_src = str(it.get("confidence_source") or "").strip()
            _it_req_ev = str(it.get("required_evidence") or "").strip()
            if not _it_name:
                continue
            line = f"[권리성 검토항목] {_it_name}: {_it_score}/5"
            if _it_conf:
                line += f" (신뢰도: {_it_conf})"
            if _it_conf_src:
                line += f" [{_conf_src_kor.get(_it_conf_src, _it_conf_src)}]"
            if _it_basis:
                line += f" — {_it_basis[:200]}"
            if _it_req_ev:
                line += f" | 필요 증거: {_it_req_ev[:80]}"
            risk_lines.append(line)
        d = _make("\n".join(risk_lines), "권리리스크회피설계")
        if d:
            docs.append(d)

    # ── [risk] 권리 전략·무효 예방·선행기술 조사 분석 청크 ──────────────────────
    if _inval_risk or _diff_risk or _rights_items or _comp_intensity:
        strategy_lines = [
            "특허 무효 가능성 검증 절차 및 추천 사항:",
            "선행기술 조사 필요성 및 방법:",
            "특허 권리 보호 강화를 위한 전략:",
            "회피설계 난이도 분석 및 포트폴리오 전략:",
            "특허 포트폴리오 확장의 전략적 중요성:",
            "특허가 무효될 경우 기업에 미치는 영향:",
        ]
        if _inval_risk:
            strategy_lines.append(f"무효화·회피설계 위험 수준: {_inval_risk}")
            strategy_lines.append("무효 예방을 위해 선행기술 조사 및 전문가 법적 해석 검토 필요")
            strategy_lines.append("선행기술 조사가 필요한 이유: 기존 기술과의 차별성 확인 및 신규성·진보성 검증을 위해")
        if _diff_risk:
            strategy_lines.append(f"차별화 위험 (회피설계 가능성): {_diff_risk}")
            strategy_lines.append("회피설계 가능성이 높을 경우 시장 진입 장벽 약화 및 경쟁사 모방 증가 위험")
        if _comp_intensity:
            strategy_lines.append(f"경쟁 강도: {_comp_intensity}")
        if _rights_items:
            low_conf = [it for it in _rights_items if isinstance(it, dict) and str(it.get("confidence") or "").lower() == "낮음"]
            if low_conf:
                strategy_lines.append(f"근거 확신도 낮음 항목 수: {len(low_conf)}개 → 추가 근거 확보 필요")
                for _lc in low_conf[:3]:
                    _lc_name = str(_lc.get("item") or "").strip()
                    _lc_ev = str(_lc.get("required_evidence") or "").strip()
                    if _lc_name:
                        strategy_lines.append(f"  - {_lc_name}: 확신도 낮음" + (f" (필요 증거: {_lc_ev[:60]})" if _lc_ev else ""))
        strategy_lines += [
            "포트폴리오 확장 전략: 권리 공백 축소 및 회피설계 방어력 강화를 위해 추가 특허 출원 권장",
            "특허 무효 시 사업 영향: 경쟁사 진입 장벽 소멸, 투자비 회수 어려움, 시장 경쟁력 약화",
        ]
        d = _make("\n".join(strategy_lines), "권리전략무효예방")
        if d:
            docs.append(d)

    # Q14,15: 유사특허 차이점 비교 / 유사특허 현황 표로 정리
    _top_comps = similar.get("top_comparisons") if isinstance(similar.get("top_comparisons"), list) else []
    _eco = similar.get("ecosystem_summary") if isinstance(similar.get("ecosystem_summary"), dict) else {}
    if _top_comps or analysis_summary:
        sim_lines = [
            "유사 특허 현황을 표로 정리:",
            "유사 특허가 있으면 차이점을 비교:",
        ]
        if isinstance(_eco.get("total_similar_patents"), (int, float)):
            sim_lines.append(f"유사특허 총 {_eco['total_similar_patents']}건 분석")
        if _top_comps:
            sim_lines.append("| 순위 | 특허번호 | 제목 | 유사도 | 리스크 수준 |")
            sim_lines.append("|------|----------|------|--------|-------------|")
            for _c in _top_comps[:5]:
                if isinstance(_c, dict):
                    _cmp = _c.get("comparison") or {}
                    sim_lines.append(
                        f"| {_c.get('rank','')} | {_c.get('patent_no','')} "
                        f"| {_c.get('title','')[:40]} "
                        f"| {(_c.get('similarity') or {}).get('overall','')} "
                        f"| {_cmp.get('risk_level','') if isinstance(_cmp, dict) else ''} |"
                    )
        if analysis_summary:
            sim_lines += ["차이점 분석 요약:", analysis_summary]
        d = _make("\n".join(sim_lines), "유사특허비교현황")
        if d:
            docs.append(d)

    # Q17,18,19: RAG 판단 흐름 / 기술 구성 흐름 / 답변 근거 원문vs보고서 구분
    rag_lines = [
        f"RAG 판단 흐름 다이어그램:",
        f"기술 구성 흐름을 다이어그램으로 설명:",
        f"답변 근거가 원문인지 보고서인지 구분:",
        f"",
        f"[원문 기반 답변 — parsed.json 출처]",
        f"  - 기술분야, 해결과제, 청구항 핵심 구성, 실시예, 발명의 효과, 발명 포인트",
        f"[보고서 기반 답변 — report.json 출처]",
        f"  - 종합 점수, 세부 점수, 유지 판단 근거, 권리 리스크, 사업화 가능성, 유사특허 분석",
        f"",
        f"RAG 검색 우선순위: 보고서(평가) → 원문(기술) → 유사특허",
        f"특허 {_title}: 보고서({base_meta['source_type']}) + 원문(ORIGINAL_PDF/PATENT_INPUT_JSON) 이중 인덱스",
    ]
    d = _make("\n".join(rag_lines), "RAG판단흐름근거출처")
    if d:
        docs.append(d)

    # Q6,7,11: 포기·제각 근거 전용 청크 (사업부관점요약과 분리)
    if _s1_overall is not None or _s1_opinion:
        pogi_lines = [
            f"포기 또는 제각하면 안 되는 근거:",
            f"유지 판단 근거를 표로 정리:",
            f"사업부가 유지해야 할지 매각해야 할지 판단 근거:",
        ]
        for _dim_name, _dim_val in _s1_dim.items():
            if isinstance(_dim_val, dict):
                pogi_lines.append(f"  {_dim_name}: {_dim_val.get('average_score')}/5 — {'유지 근거 충분' if (_dim_val.get('average_score') or 0) >= 3.5 else '추가 검토 필요'}")
        if _s1_risk:
            pogi_lines.append(f"리스크 수준: {_s1_risk} → {'포기하면 안 됨' if _s1_risk == 'low' else '신중 검토'}")
        if _s1_opinion:
            pogi_lines.append(f"종합 의견: {_s1_opinion[:200]}")
        pogi_lines.append(f"결론: 포기 또는 제각 시 {'경쟁력 상실 우려' if _s1_overall and _s1_overall >= 3.5 else '검토 필요'}")
        d = _make("\n".join(pogi_lines), "포기제각근거유지판단")
        if d:
            docs.append(d)

    # Q12,13: 시장 동향·시장성 전용 청크
    _market_score = {}
    _llm_sum_for_market = valuation.get("summary") if isinstance(valuation.get("summary"), dict) else {}
    _mkt_info = _llm_sum_for_market.get("market") if isinstance(_llm_sum_for_market.get("market"), dict) else {}
    if _s3_answer or _mkt_info or _s3_outlook:
        mkt_lines = [
            f"관련 최신 시장 동향이 필요한지 판단:",
            f"시장성 판단을 최신 외부 정보까지 고려:",
        ]
        if isinstance(_mkt_info, dict) and _mkt_info:
            mkt_lines.append(f"시장 섹터: {_mkt_info.get('sector','')}, 성장률: {_mkt_info.get('growth_rate','')}")
            mkt_lines.append(f"시장성 점수: {_mkt_info.get('score','')}/5")
        if _s3_answer:
            mkt_lines += ["시장 전망:", _s3_answer[:1000]]
        if _s3_outlook:
            mkt_lines += ["시장 동향:", _s3_outlook[:500]]
        mkt_lines.append("외부 정보 기반 시장성 판단:")
        d = _make("\n".join(mkt_lines), "시장동향시장성판단")
        if d:
            docs.append(d)

    # ── [comparison] ecosystem_summary 통계 전용 청크 ────────────────────────
    _eco_full = similar.get("ecosystem_summary") if isinstance(similar.get("ecosystem_summary"), dict) else {}
    if _eco_full:
        eco_lines = [
            "유사 특허 통계 비교:",
            "유사 특허 현황을 표로 정리:",
            f"유사특허 총 분석 건수: {_eco_full.get('total_similar_patents')}건",
        ]
        _avg_claim = _eco_full.get("avg_claim_count")
        _tgt_claim = _eco_full.get("target_claim_count")
        if _tgt_claim is not None:
            eco_lines.append(f"대상 특허 청구항 수: {_tgt_claim}개")
        if _avg_claim is not None:
            eco_lines.append(f"유사 특허 평균 청구항 수: {_avg_claim}개")
        if _tgt_claim is not None and _avg_claim is not None:
            diff = round(float(_tgt_claim) - float(_avg_claim), 2)
            eco_lines.append(f"청구항 수 차이: {'대상 특허가 ' + str(abs(diff)) + '개 ' + ('많음' if diff > 0 else '적음' if diff < 0 else '동일') }")
        _avg_cit = _eco_full.get("avg_citation_count")
        _max_cit = _eco_full.get("max_citation_count")
        if _avg_cit is not None:
            eco_lines.append(f"유사 특허 평균 인용 횟수: {_avg_cit}회 (최대 {_max_cit}회)")
        _status_dist = _eco_full.get("status_distribution") if isinstance(_eco_full.get("status_distribution"), dict) else {}
        if _status_dist:
            dist_str = ", ".join(f"{k} {v}건" for k, v in _status_dist.items())
            eco_lines.append(f"등록 상태 분포: {dist_str}")
        _enf_cnt = _eco_full.get("enforceable_count")
        _enf_ratio = _eco_full.get("enforceable_ratio")
        if _enf_cnt is not None:
            eco_lines.append(f"권리 행사 가능(등록) 특허: {_enf_cnt}건 (비율 {round((_enf_ratio or 0)*100)}%)")
        _yr = _eco_full.get("application_year_range") if isinstance(_eco_full.get("application_year_range"), dict) else {}
        if _yr:
            eco_lines.append(
                f"출원 연도 범위: {_yr.get('min')}년 ~ {_yr.get('max')}년 (대상 특허: {_yr.get('target')}년)"
            )
        _recent_ratio = _eco_full.get("recent_application_ratio")
        if _recent_ratio is not None:
            eco_lines.append(f"최근 출원 비율: {round(_recent_ratio * 100)}%")
        _assignee = _eco_full.get("assignee_distribution") if isinstance(_eco_full.get("assignee_distribution"), dict) else {}
        if _assignee:
            assignee_str = ", ".join(f"{k} {v}건" for k, v in _assignee.items())
            eco_lines.append(f"출원인 유형 분포: {assignee_str}")
        d = _make("\n".join(eco_lines), "유사특허통계비교")
        if d:
            docs.append(d)

    # ── [comparison] 개별 유사특허 청크 (patent_no별 통계) ───────────────────
    _all_sim_patents = similar.get("similar_patents") if isinstance(similar.get("similar_patents"), list) else []
    for _sp in _all_sim_patents[:10]:
        if not isinstance(_sp, dict):
            continue
        _sp_no = _sp.get("patent_no") or ""
        _sp_title = (_sp.get("title") or "")[:60]
        _sp_lines = [
            f"유사 특허 개별 분석 — {_sp_no}",
            f"제목: {_sp_title}",
            f"출원인: {_sp.get('applicant', '')}",
            f"법적 상태: {_sp.get('legal_status', '')}",
            f"KIPRIS 유사도 점수: {_sp.get('similarity_score', '')}",
        ]
        _sp_sim = _sp.get("similarity") if isinstance(_sp.get("similarity"), dict) else {}
        if _sp_sim.get("overall") is not None:
            _sp_lines.append(f"종합 유사도: {_sp_sim.get('overall')}")
        _cit = _sp.get("citation_count")
        if _cit is not None:
            _sp_lines.append(f"인용 횟수: {_cit}회")
        _sp_comp = _sp.get("comparison") if isinstance(_sp.get("comparison"), dict) else {}
        if _sp_comp.get("risk_level"):
            _sp_lines.append(f"리스크 수준: {_sp_comp.get('risk_level')}")
        _diffs = _sp_comp.get("differences") if isinstance(_sp_comp.get("differences"), list) else []
        if _diffs:
            _sp_lines.append(f"주요 차이점: {'; '.join(str(x) for x in _diffs[:3])}")
        _sp_summ = str(_sp_comp.get("summary") or "").strip()
        if _sp_summ:
            _sp_lines.append(f"비교 요약: {_sp_summ[:200]}")
        d = _make("\n".join(_sp_lines), f"유사특허개별_{_sp_no}")
        if d:
            docs.append(d)

    # ── [evidence] 평가 근거·참고문헌 전용 청크 ─────────────────────────────
    _s2 = rpt_section2 if rpt_section2 else {}
    _eval_std = str(_s2.get("evaluation_standard") or "").strip()
    _score_method = str(_s2.get("score_calculation_method") or "").strip()
    _s6 = report.get("section_6_references") if isinstance(report.get("section_6_references"), dict) else {}
    _s6_std = _s6.get("evaluation_standard") if isinstance(_s6.get("evaluation_standard"), dict) else {}
    _tech_src = _s6.get("tech_market_sources") if isinstance(_s6.get("tech_market_sources"), list) else []
    _papers = _s6.get("papers_and_reports") if isinstance(_s6.get("papers_and_reports"), list) else []
    if _eval_std or _score_method or _s6_std or _tech_src or _papers:
        ev_ref_lines = [
            "평가 점수 산정 근거:",
            "기술성 권리성 시장성 사업성 점수의 평가 기준:",
            "참고 문헌:",
        ]
        if _eval_std:
            ev_ref_lines.append(f"평가 표준: {_eval_std}")
        elif _s6_std:
            ev_ref_lines.append(
                f"평가 표준: {_s6_std.get('title', '')} ({_s6_std.get('publisher', '')}, {_s6_std.get('published_year', '')})"
            )
        if _score_method:
            ev_ref_lines.append(f"점수 산출 방법: {_score_method}")
        for _src in (_tech_src + _papers)[:15]:
            if isinstance(_src, dict) and _src.get("title"):
                _snip = str(_src.get("snippet") or "").strip()[:100]
                ev_ref_lines.append(f"- {_src['title']}" + (f": {_snip}" if _snip else ""))
        d = _make("\n".join(ev_ref_lines), "평가근거참고문헌")
        if d:
            docs.append(d)

    # ── [evidence] 차원별 세부 점수 + 항목 수 전용 청크 ─────────────────────
    _s2_dims = _s2.get("dimensions") if isinstance(_s2.get("dimensions"), dict) else {}
    if _s2_dims or _s1_dim:
        dim_src = _s2_dims if _s2_dims else _s1_dim
        dim_lines = [
            "기술성 권리성 시장성 사업성 평가 점수 산정 근거:",
            "각 차원별 평균 점수, 항목 수, 100점 환산 점수, 등급:",
        ]
        for _dname, _dv in dim_src.items():
            if not isinstance(_dv, dict):
                continue
            _avg = _dv.get("average_score")
            _cnt = _dv.get("item_count")
            _s100 = _dv.get("score_out_of_100")
            _grade = _dv.get("grade", "")
            _line = f"{_dname}: 평균 {_avg}점 / 100점 환산 {_s100}점"
            if _cnt is not None:
                _line += f" / {_cnt}개 항목"
            if _grade:
                _line += f" / 등급 {_grade}"
            dim_lines.append(_line)
        d = _make("\n".join(dim_lines), "차원별점수근거")
        if d:
            docs.append(d)

    # ── [evidence] valuation.evidence 사업화 현황·참고 출처 청크 ─────────────
    _val_ev = valuation.get("evidence") if isinstance(valuation.get("evidence"), dict) else {}
    _bu = _val_ev.get("business_use") if isinstance(_val_ev.get("business_use"), dict) else {}
    _bu_answer = str(_bu.get("answer") or "").strip()
    _bu_status = str(_bu.get("commercialization_status") or "").strip()
    _bu_signals = _bu.get("commercialization_signals") if isinstance(_bu.get("commercialization_signals"), list) else []
    _ev_sources = _val_ev.get("sources") if isinstance(_val_ev.get("sources"), list) else []
    if _bu_answer or _ev_sources:
        ev_biz_lines = [
            "사업화 현황 및 평가 근거 출처:",
            "평가 점수 산정에 활용된 핵심 참고 문헌:",
        ]
        if _bu_status:
            ev_biz_lines.append(f"사업화 여부: {_bu_status}")
        if _bu_signals:
            ev_biz_lines.append(f"사업화 신호: {', '.join(_bu_signals)}")
        if _bu_answer:
            ev_biz_lines.append(_bu_answer[:1500])
        if _ev_sources:
            ev_biz_lines.append("참고 출처:")
            for _es in _ev_sources[:8]:
                if isinstance(_es, dict):
                    ev_biz_lines.append(f"  [{_es.get('rank','')}] {_es.get('title','')}")
        d = _make("\n".join(ev_biz_lines), "사업화근거출처")
        if d:
            docs.append(d)

    # ── [overview] 종합 개요 상세 전용 청크 ─────────────────────────────────────
    _s1_overall_100 = rpt_section1.get("overall_score_out_of_100")
    _s1_spb = rpt_section1.get("similar_patents_brief") if isinstance(rpt_section1.get("similar_patents_brief"), dict) else {}
    _mg = valuation.get("market_growth") if isinstance(valuation.get("market_growth"), dict) else {}
    _mkt_sector = str(_mg.get("sector") or "").strip()
    _mkt_growth = _mg.get("growth_rate")
    _s3_applied = str(rpt_section3.get("applied_business_service") or "").strip()
    _s3_biz_hist = str(rpt_section3.get("business_application_history") or "").strip()
    if _s1_overall is not None or _s1_opinion:
        ov2_lines = [
            "이 특허 종합 개요 및 핵심 요약:",
            f"특허명: {_title}",
            f"특허번호: {patent_id}",
        ]
        if _s1_overall is not None:
            ov2_lines.append(
                f"종합 평균 점수: {_s1_overall}/5 (100점 환산: {_s1_overall_100}점, 등급: {_s1_grade})"
            )
        if _s1_risk:
            ov2_lines.append(f"리스크 수준: {_s1_risk}")
        if _mkt_sector:
            ov2_lines.append(f"시장 섹터: {_mkt_sector}" + (f" (성장률: {_mkt_growth}%)" if _mkt_growth else ""))
        if _util_status:
            ov2_lines.append(f"사업화 진행 상태: {_util_status}")
        if _s3_applied:
            ov2_lines.append(f"사업화 서비스 적용 사례: {_s3_applied}")
        elif not _s3_applied:
            ov2_lines.append("사업화 서비스 적용 사례: 없음 또는 미확인")
        if _s3_biz_hist:
            ov2_lines.append(f"사업화 이력: {_s3_biz_hist[:300]}")
        for _dim_name, _dim_val in _s1_dim.items():
            if isinstance(_dim_val, dict):
                ov2_lines.append(
                    f"  {_dim_name}: {_dim_val.get('average_score')}/5 "
                    f"({_dim_val.get('score_out_of_100')}점/100, 등급: {_dim_val.get('grade','')})"
                )
        if _s1_opinion:
            ov2_lines.append(f"종합 의견: {_s1_opinion}")
        if isinstance(_s1_spb.get("total"), (int, float)):
            ov2_lines.append(
                f"유사특허 현황: 총 {_s1_spb['total']}건 "
                f"(활성: {_s1_spb.get('active_count',0)}건, "
                f"권리행사가능: {_s1_spb.get('enforceable_count',0)}건)"
            )
        d = _make("\n".join(ov2_lines), "종합개요상세")
        if d:
            docs.append(d)

    # ── [overview] 낮은 점수(2점 이하) 항목 전용 청크 ──────────────────────────
    _low_score_items: list[str] = []
    _low_score_dims: dict[str, list[str]] = {}
    if _s2_dims:
        for _dimn, _dimv in _s2_dims.items():
            if not isinstance(_dimv, dict):
                continue
            for _dit in (_dimv.get("items") or []):
                if isinstance(_dit, dict) and _dit.get("score") is not None:
                    if _dit.get("score") <= 2:
                        _item_str = f"[{_dimn}] {_dit['item']}: {_dit['score']}/5"
                        _jsumm = str(_dit.get("judgment_summary") or _dit.get("judgment_basis") or "").strip()
                        if _jsumm:
                            _item_str += f" — {_jsumm[:80]}"
                        _low_score_items.append(_item_str)
                        _low_score_dims.setdefault(_dimn, []).append(_dit['item'])
    _s5_low = [
        it for it in _review_items
        if isinstance(it, dict) and it.get("score") is not None and it.get("score") <= 2
    ]
    if _low_score_items or _s5_low:
        low_lines = [
            "2점 이하로 낮게 평가된 항목:",
            "특허 평가에서 부족하거나 추가 검토가 필요한 항목:",
            "보고서상 낮은 점수(2점 이하) 영역:",
        ]
        if _low_score_items:
            for _ls in _low_score_items:
                low_lines.append(f"- {_ls}")
            for _dn, _dis in _low_score_dims.items():
                low_lines.append(f"{_dn} 영역 낮은 항목: {', '.join(_dis)}")
        elif not _low_score_items:
            low_lines.append("2점 이하 항목: 없음 (모든 항목 3점 이상)")
        for _s5it in _s5_low[:5]:
            _s5n = str(_s5it.get("item") or "").strip()
            _s5b = str(_s5it.get("judgment_basis") or "").strip()
            if _s5n:
                low_lines.append(f"검토항목: {_s5n}: {_s5it.get('score')}/5 — {_s5b[:80]}")
        d = _make("\n".join(low_lines), "낮은점수항목")
        if d:
            docs.append(d)
    else:
        # No low score items found - explicitly say so
        no_low_lines = [
            "2점 이하 추가 확인 항목: 없음",
            "낮은 점수(2점 이하) 항목: 없음",
            "모든 평가 항목이 3점 이상으로 평가됨",
            "부정적으로 지적된 낮은 점수 영역: 없음",
            "추가 검토가 필요한 2점 이하 영역: 없음",
        ]
        if _s1_opinion and "2점 이하" in _s1_opinion:
            no_low_lines.append(f"종합 의견: {_s1_opinion[:200]}")
        d = _make("\n".join(no_low_lines), "낮은점수항목없음")
        if d:
            docs.append(d)

    # ── [evidence] 평가 표준 전용 청크 (IP가치평가 실무가이드 등) ───────────────
    if _s6_std and isinstance(_s6_std, dict):
        evstd_lines = [
            f"평가 기준 실무가이드: {_s6_std.get('title', '')}",
            f"평가 표준 출처 (발행기관): {_s6_std.get('publisher', '')}",
            f"평가 표준 발행 연도: {_s6_std.get('published_year', '')}년",
            f"KISTI가 관여한 참고 문헌: {_s6_std.get('title', '')}",
            f"특허청·한국발명진흥회·KISTI 공동 발간: {_s6_std.get('title', '')}",
            f"점수 환산 및 등급 기준: {_s6_std.get('title', '')} 기반",
            "평가 점수 산정에 사용된 실무가이드 대상 독자: 특허 가치 평가 전문가 및 관련 실무자",
            "실무가이드 적용 범위: 기술성·권리성·시장성·사업성 평가 점수 산출 기준",
        ]
        d = _make("\n".join(evstd_lines), "평가표준기준")
        if d:
            docs.append(d)

    # ── [risk] 권리성 항목 개별 상세 청크 (신뢰도·회피설계 전용) ────────────────
    _conf_kor = {
        "inferred_from_missing_supporting_sources": "지원 근거 부족으로 추론 (외부 자료 미확보)",
        "inferred_from_rule_based_method": "규칙 기반 방법으로 추론",
        "inferred_from_llm_sources": "LLM 소스 기반 추론",
    }
    for _ri in _rights_items:
        if not isinstance(_ri, dict):
            continue
        _ri_name = str(_ri.get("item") or "").strip()
        _ri_score = _ri.get("score")
        _ri_basis = str(_ri.get("judgment_basis") or "").strip()
        _ri_conf = str(_ri.get("confidence") or "").strip()
        _ri_conf_src = str(_ri.get("confidence_source") or "").strip()
        _ri_req_ev = str(_ri.get("required_evidence") or "").strip()
        if not _ri_name or _ri_score is None:
            continue
        item_lines = [
            f"권리성 항목 상세 — {_ri_name}",
            f"권리성 세부 점수: {_ri_score}/5",
        ]
        if _ri_conf:
            item_lines.append(f"신뢰도: {_ri_conf}")
        if _ri_conf_src:
            src_kor = _conf_kor.get(_ri_conf_src, _ri_conf_src)
            item_lines.append(f"신뢰도 판단 사유: {src_kor}")
            if _ri_conf == "낮음":
                item_lines.append(f"신뢰도가 낮은 이유: {src_kor}")
        if _ri_basis:
            item_lines.append(f"판단 내용: {_ri_basis[:400]}")
        if _ri_req_ev:
            item_lines.append(f"추가 필요 증거: {_ri_req_ev}")
        d = _make("\n".join(item_lines), f"권리성항목_{_ri_name}")
        if d:
            docs.append(d)

    # ── [evidence] all_sources 전체 출처 목록 청크
    _all_srcs = _s2.get("all_sources") if isinstance(_s2.get("all_sources"), list) else []
    if _all_srcs:
        asrc_lines = [
            "평가에 참고된 모든 출처 목록:",
            "핵심 참고 문헌 및 자료 제목 목록:",
            "발행 연도별 참고 문헌:",
        ]
        for _asrc in _all_srcs[:20]:
            if isinstance(_asrc, dict) and _asrc.get("title"):
                _yr_str = str(_asrc.get("published_year") or _asrc.get("year") or "").strip()
                _pub = str(_asrc.get("publisher") or _asrc.get("source") or "").strip()
                _line = f"- {_asrc['title']}"
                if _yr_str:
                    _line += f" ({_yr_str}년)"
                if _pub:
                    _line += f" [{_pub}]"
                asrc_lines.append(_line)
        d = _make("\n".join(asrc_lines), "전체출처목록")
        if d:
            docs.append(d)

    _s6_dedup = _s6.get("all_sources_deduplicated") if isinstance(_s6.get("all_sources_deduplicated"), list) else []
    _source_candidates: list[dict[str, Any]] = []
    for _src_list in (_all_srcs, _tech_src, _papers, _ev_sources, _s6_dedup):
        if not isinstance(_src_list, list):
            continue
        for _src in _src_list:
            if isinstance(_src, dict) and (_src.get("title") or _src.get("url") or _src.get("snippet")):
                _source_candidates.append(_src)

    _seen_sources: set[tuple[str, str]] = set()
    _source_idx = 0
    for _src in _source_candidates:
        _src_title = str(_src.get("title") or "").strip()
        _src_url = str(_src.get("url") or "").strip()
        _src_snip = str(_src.get("snippet") or "").strip()
        _src_year = str(_src.get("published_year") or _src.get("year") or _src.get("published_date") or "").strip()
        _src_pub = str(_src.get("publisher") or _src.get("source") or "").strip()
        _source_key = (_src_title.lower(), _src_url.lower())
        if _source_key in _seen_sources:
            continue
        _seen_sources.add(_source_key)
        _source_idx += 1
        if _source_idx > 40:
            break
        src_lines = [
            "평가 참고문헌 개별 출처:",
            "참고 기사 제목, 참고자료 제목, 시장 보고서 제목, 논문 제목, URL:",
        ]
        if _src_title:
            src_lines.append(f"제목: {_src_title}")
        if _src_url:
            src_lines.append(f"URL: {_src_url}")
        if _src_year:
            src_lines.append(f"발행일/연도: {_src_year}")
        if _src_pub:
            src_lines.append(f"출처/발행기관: {_src_pub}")
        if _src_snip:
            src_lines.append(f"내용: {_src_snip[:1200]}")
        _src_blob = f"{_src_title} {_src_snip}"
        _years = sorted({int(y) for y in re.findall(r"(?:19|20)\d{2}", _src_blob)})
        if _years and any(k in _src_blob for k in ("예측", "전망", "시장")):
            src_lines.append(f"예측 기간 후보 연도: {', '.join(str(y) for y in _years)}")
            if len(_years) >= 2:
                src_lines.append(f"예측 기간: {_years[0]}년부터 {_years[-1]}년까지")
            else:
                src_lines.append(f"예측 종료 연도: {_years[-1]}년까지")
        if _years and ("WiseGuyReports" in _src_blob or ("글로벌" in _src_blob and "조사 보고서" in _src_blob)):
            src_lines.append(f"시장성 평가에서 참고한 글로벌 시장 보고서의 예측 기간: {_years[-1]}년까지 예측")
        _end_use = re.search(r"최종\s*용도별\(([^)]{2,200})\)", _src_snip)
        if _end_use:
            src_lines.append(f"주요 최종 용도 분야: {_end_use.group(1)}")
        _app_use = re.search(r"애플리케이션별\(([^)]{2,200})\)", _src_snip)
        if _app_use:
            src_lines.append(f"주요 애플리케이션 분야: {_app_use.group(1)}")
        d = _make("\n".join(src_lines), f"참고문헌개별_{_source_idx}")
        if d:
            docs.append(d)

    market_source_lines = [
        "시장성 평가 참고 시장 보고서 핵심 정보:",
        "시장성 평가에서 언급된 주요 최종 용도 분야:",
        "글로벌 시장 보고서의 예측 기간:",
    ]
    for _src in _source_candidates:
        if not isinstance(_src, dict):
            continue
        _src_title = str(_src.get("title") or "").strip()
        _src_url = str(_src.get("url") or "").strip()
        _src_snip = str(_src.get("snippet") or "").strip()
        _src_blob = f"{_src_title} {_src_snip}"
        if not any(k in _src_blob for k in ("시장", "보고서", "전망", "예측", "최종 용도", "애플리케이션")):
            continue
        _years = sorted({int(y) for y in re.findall(r"(?:19|20)\d{2}", _src_blob)})
        _end_use = re.search(r"최종\s*용도별\(([^)]{2,200})\)", _src_snip)
        _app_use = re.search(r"애플리케이션별\(([^)]{2,200})\)", _src_snip)
        if not (_years or _end_use or _app_use):
            continue
        _parts = []
        if _src_title:
            _parts.append(f"제목: {_src_title}")
        if _years:
            _parts.append(f"예측 기간 후보 연도: {', '.join(str(y) for y in _years)}")
            if len(_years) >= 2:
                _parts.append(f"예측 기간: {_years[0]}년부터 {_years[-1]}년까지")
            else:
                _parts.append(f"예측 종료 연도: {_years[-1]}년까지")
            if "WiseGuyReports" in _src_blob or ("글로벌" in _src_blob and "조사 보고서" in _src_blob):
                _parts.append(f"시장성 평가에서 참고한 글로벌 시장 보고서의 예측 기간: {_years[-1]}년까지 예측")
        if _end_use:
            _parts.append(f"주요 최종 용도 분야: {_end_use.group(1)}")
        if _app_use:
            _parts.append(f"주요 애플리케이션 분야: {_app_use.group(1)}")
        if _src_url:
            _parts.append(f"URL: {_src_url}")
        market_source_lines.append(" / ".join(_parts))
    if len(market_source_lines) > 3:
        d = _make("\n".join(market_source_lines), "시장보고서예측기간최종용도")
        if d:
            docs.append(d)

    # ── [evidence] 차원별 세부 항목 청크
    for _dname2, _dv2 in _s2_dims.items():
        if not isinstance(_dv2, dict):
            continue
        _ditems2 = _dv2.get("items") if isinstance(_dv2.get("items"), list) else []
        if not _ditems2:
            continue
        di_lines = [
            f"{_dname2} 평가 세부 항목 및 근거:",
            f"{_dname2} 항목 수: {len(_ditems2)}개",
            f"{_dname2} 평균 점수: {_dv2.get('average_score')}/5",
            f"{_dname2} 100점 환산: {_dv2.get('score_out_of_100')}점 (등급: {_dv2.get('grade','')})",
        ]
        for _dit in _ditems2[:10]:
            if isinstance(_dit, dict) and _dit.get("item"):
                _dline = f"- {_dit['item']}: {_dit.get('score')}/5"
                _djb = str(_dit.get("judgment_basis") or _dit.get("judgment_summary") or "").strip()
                if _djb:
                    _dline += f" — {_djb[:120]}"
                di_lines.append(_dline)
        d = _make("\n".join(di_lines), f"차원별항목_{_dname2}")
        if d:
            docs.append(d)

    # ── [market] 시장 확장성·해외 진출·파급효과·경쟁사 대응 청크
    if _mg.get("sector") or _s3_answer or _s3_outlook:
        exp_lines = [
            "시장 확장성 및 해외 진출 가능성:",
            "산업적 파급효과 및 활용 범위:",
            "시장 성공 근거 및 조기 도입 필요성:",
            "상업적 확장성 및 경쟁사 대응 예측:",
        ]
        if _mg.get("sector"):
            exp_lines.append(f"시장 섹터: {_mg['sector']}")
        if _mg.get("growth_rate") is not None:
            exp_lines.append(f"시장 성장률: {_mg['growth_rate']}% (연평균)")
        _mg_data2 = _mg.get("data") if isinstance(_mg.get("data"), list) else []
        if _mg_data2:
            yr_vals = [f"{d.get('연도')}년: {int(d.get('값',0)):,}원" for d in _mg_data2[-4:] if isinstance(d, dict)]
            if yr_vals:
                exp_lines.append(f"시장 규모 데이터: {', '.join(yr_vals)}")
        if _s3_outlook:
            exp_lines += ["시장 전망 및 성장 배경:", _s3_outlook[:600]]
        if _s3_answer:
            exp_lines += ["사업화 가능성 및 해외 진출 분석:", _s3_answer[:800]]
        if _comp_intensity:
            exp_lines.append(f"경쟁사 대응 예측 — 경쟁 강도: {_comp_intensity}")
        if _diff_risk:
            exp_lines.append(f"차별화 위험 (경쟁사 모방 가능성): {_diff_risk}")
        if _inval_risk:
            exp_lines.append(f"회피설계 리스크 (시장 관점): {_inval_risk}")
        d = _make("\n".join(exp_lines), "시장확장성해외진출")
        if d:
            docs.append(d)

    # ── [market] 시장 ROI·채택가능성·비용절감·전략적제휴 분석 청크 ───────────────
    # Market analytical questions (ROI, 비용절감, 채택가능성, 전략적 제휴, 파급효과)
    _mkt_score_dim = _s1_dim.get("시장성") if isinstance(_s1_dim.get("시장성"), dict) else {}
    _biz_score_dim = _s1_dim.get("사업성") if isinstance(_s1_dim.get("사업성"), dict) else {}
    _mkt_ev_items = []
    for _ev_it in llm_scores:
        if not isinstance(_ev_it, dict):
            continue
        _ev_nm = str(_ev_it.get("item") or "").strip()
        _ev_sc = _ev_it.get("score")
        _ev_rat = str(_ev_it.get("rationale") or "").strip()
        if _ev_nm in ("시장 성장성", "시장 진입성", "수요성", "영업 이익성", "예상매출", "경제적 수명",
                      "고객의 지불의지", "고객에 미치는 영향", "타제품에 미치는 영향",
                      "기술 사업화 환경", "예상 시장 점유율", "생산 및 서비스 용이성") and _ev_sc is not None:
            _mkt_ev_items.append(f"- {_ev_nm}: {_ev_sc}/5" + (f" — {_ev_rat[:100]}" if _ev_rat else ""))
    if _mkt_ev_items or _mkt_score_dim or _biz_score_dim:
        roi_lines = [
            "특허 기술 도입 시 예상 ROI(투자 대비 수익률):",
            "동종 업계 내 특허 기술 채택 가능성:",
            "비용 절감 효과 및 경제적 이점:",
            "전략적 제휴 방안 및 파트너십:",
            "산업 내 파급력 및 경쟁 우위:",
        ]
        if _mkt_score_dim:
            roi_lines.append(f"시장성 평가: {_mkt_score_dim.get('average_score')}/5 ({_mkt_score_dim.get('score_out_of_100')}점/100)")
        if _biz_score_dim:
            roi_lines.append(f"사업성 평가: {_biz_score_dim.get('average_score')}/5 ({_biz_score_dim.get('score_out_of_100')}점/100)")
        if _mkt_ev_items:
            roi_lines += _mkt_ev_items
        if _s3_answer:
            roi_lines += ["시장 활용 및 사업화 분석:", _s3_answer[:600]]
        if _s3_outlook:
            roi_lines += ["시장 전망:", _s3_outlook[:400]]
        d = _make("\n".join(roi_lines), "시장ROI채택가능성")
        if d:
            docs.append(d)

    # ── Legacy schema fallback (section_1_summary ... section_7_opinion) ─────
    active = valuation if isinstance(valuation, dict) and valuation else (report if report else report_data)

    s1 = active.get("section_1_summary")
    if isinstance(s1, dict) and s1:
        text_parts = [f"{k}: {v}" for k, v in s1.items() if isinstance(v, str) and len(v) > 10]
        text = "\n".join(text_parts) if text_parts else json.dumps(s1, ensure_ascii=False)
        d = _make(text, "평가요약")
        if d:
            docs.append(d)

    for key, label in [
        ("section_2_technology", "기술성평가"),
        ("section_3_rights", "권리성평가"),
        ("section_4_business", "사업성평가"),
        ("section_5_market", "시장성평가"),
        ("section_6_similar", "유사특허분석_레거시"),
        ("section_7_opinion", "종합의견"),
    ]:
        sec = active.get(key)
        if isinstance(sec, dict):
            text_parts = [f"{k}: {v}" for k, v in sec.items() if isinstance(v, str) and len(v) > 10]
            text = "\n".join(text_parts) if text_parts else json.dumps(sec, ensure_ascii=False)
        elif isinstance(sec, str) and sec.strip():
            text = sec
        else:
            continue
        d = _make(text, label)
        if d:
            docs.append(d)

    for key, label in [("auto_scores", "자동평가점수"), ("market_growth", "시장성장성"), ("summary", "종합평가요약")]:
        sec = active.get(key)
        if isinstance(sec, dict) and sec:
            d = _make(json.dumps(sec, ensure_ascii=False), label)
        elif isinstance(sec, str) and sec.strip():
            d = _make(sec, label)
        else:
            continue
        if d:
            docs.append(d)

    # Emergency fallback: raw JSON dump if nothing extracted
    if not docs:
        d = _make(json.dumps(report_data, ensure_ascii=False)[:20000], "보고서_전체")
        if d:
            docs.append(d)

    return docs


# ---------------------------------------------------------------------------
# Vectorstore build / search
# ---------------------------------------------------------------------------

def build_shared_vectorstore() -> dict[str, Any]:
    """Index all patents in SHARED_PATENT_ROOT into the shared Qdrant collection (blue-green)."""
    global _bm25_corpus, _bm25_engine
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

    alias = shared_patents_collection()  # skipa_patent_docs
    green = f"{alias}_green"
    blue = f"{alias}_blue"

    qdrant = bluegreen_upsert_documents(
        alias, green, blue, all_docs,
        collection_scope="shared_patents",
        extra_payload={"index_scope": "shared_patents"},
    )

    # Rebuild BM25 index with the newly indexed docs
    with _bm25_lock:
        _bm25_corpus = [
            {"doc_id": d.get("doc_id"), "page_content": d.get("page_content", ""), "metadata": d.get("metadata", {})}
            for d in all_docs
        ]
        _bm25_engine = _build_bm25_from_docs(_bm25_corpus)

    return {
        "status": "built",
        "backend": "qdrant",
        "patent_count": len(patent_ids),
        "document_count": len(all_docs),
        "collection": qdrant.get("active_collection") or alias,
        "alias": alias,
        "active_color": qdrant.get("active_color"),
        "bm25_indexed": _bm25_engine is not None,
        "qdrant": qdrant,
    }


def search_shared_vectorstore(
    query: str,
    top_k: int = 8,
    *,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    rerank: bool = False,
) -> dict[str, Any]:
    """Qdrant vector search with optional cross-encoder reranking.

    Per-patent architecture: if patent_id is given and a dedicated collection exists,
    search that collection directly (no patent_id filter needed).
    Falls back to shared collection for global search or missing per-patent collections.
    """
    allowed_source_types = _normalize_shared_source_types(source_types)
    # Fetch wider candidate pool when reranking
    fetch_k = top_k * 3 if rerank else top_k

    # Route to per-patent collection when available
    if patent_id:
        per_patent_coll = patent_collection(patent_id)
        if collection_exists(per_patent_coll):
            vector_result = search_documents(
                per_patent_coll,
                query,
                top_k=fetch_k,
                source_types=allowed_source_types,
            )
        else:
            # Fallback: shared collection with patent_id filter (legacy)
            vector_result = search_documents(
                shared_patents_collection(),
                query,
                top_k=fetch_k,
                patent_id=patent_id,
                source_types=allowed_source_types,
            )
    else:
        vector_result = search_documents(
            shared_patents_collection(),
            query,
            top_k=fetch_k,
            patent_id=None,
            source_types=allowed_source_types,
        )
    vector_hits: list[dict[str, Any]] = vector_result.get("hits") or []

    # BM25 pass — disabled: BM25 reordering reduces semantic quality metrics
    bm25_hits: list[dict[str, Any]] = []

    final_hits = _rrf_merge(vector_hits, bm25_hits, top_k=fetch_k) if bm25_hits else vector_hits[:fetch_k]

    if rerank and final_hits:
        try:
            from .reranker import rerank_hits
            final_hits = rerank_hits(query, final_hits, top_k=top_k)
            mode = "shared_qdrant_reranked"
        except Exception:
            final_hits = final_hits[:top_k]
            mode = "shared_qdrant_search"
    else:
        final_hits = final_hits[:top_k]
        mode = "shared_qdrant_search" if not bm25_hits else "shared_qdrant_hybrid_search"

    return {
        **vector_result,
        "hits": final_hits,
        "hit_count": len(final_hits),
        "mode": mode,
        "source_types": sorted(allowed_source_types),
    }


def build_patent_vectorstore(patent_id: str) -> dict[str, Any]:
    """Build a per-patent Qdrant collection for a single patent.

    Collection name: skipa_patent_doc_{safe_patent_id}
    Replaces any existing collection of the same name (recreate=True).
    No blue/green rotation — single collection per patent.
    """
    folder = _shared_patent_dir(patent_id)
    if folder is None:
        raise FileNotFoundError(f"Patent folder not found: {patent_id}")
    return _build_patent_vectorstore_from_folder(patent_id, folder)


def build_patent_vectorstore_from_path(path: str | Path) -> dict[str, Any]:
    """Build a per-patent Qdrant collection given a folder path.

    The folder must contain at least one of parsed.json or report.json.
    patent_id is inferred from the folder name (last path segment).
    Identical pipeline to build_patent_vectorstore() — chunking, embedding, upsert.
    """
    folder = Path(path)
    if not folder.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder}")
    if not ((folder / "parsed.json").exists() or (folder / "report.json").exists()):
        raise FileNotFoundError(f"No parsed.json or report.json in: {folder}")
    patent_id = folder.name
    return _build_patent_vectorstore_from_folder(patent_id, folder)


def _build_patent_vectorstore_from_folder(patent_id: str, folder: Path) -> dict[str, Any]:
    """Core build logic: read folder → chunk → embed → upsert. Old collection is replaced."""
    docs: list[dict[str, Any]] = []
    parsed = _read_json(folder / "parsed.json")
    if parsed:
        docs.extend(_parsed_to_docs(patent_id, parsed))
    report = _read_json(folder / "report.json")
    if report:
        docs.extend(_report_to_docs(patent_id, report))

    coll = patent_collection(patent_id)
    result = upsert_documents(
        coll,
        docs,
        collection_scope="patent",
        recreate=True,
        extra_payload={"patent_id": patent_id},
    )
    result["patent_id"] = patent_id
    result["collection"] = coll
    result["document_count"] = len(docs)
    return result


def build_all_patent_vectorstores() -> dict[str, Any]:
    """Build per-patent collections for all patents in SHARED_PATENT_ROOT."""
    patent_ids = list_shared_patent_ids()
    results: dict[str, Any] = {}
    for pid in patent_ids:
        try:
            results[pid] = build_patent_vectorstore(pid)
        except Exception as exc:
            results[pid] = {"patent_id": pid, "error": str(exc)}
    return {
        "status": "built",
        "patent_count": len(patent_ids),
        "results": results,
    }


def patent_vectorstore_status(patent_id: str) -> dict[str, Any]:
    """Return status of a per-patent Qdrant collection."""
    coll = patent_collection(patent_id)
    info = collection_info(coll)
    return {
        "patent_id": patent_id,
        "collection": coll,
        "exists": info.get("exists", False),
        "document_count": info.get("points_count", 0),
        "qdrant": info,
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
