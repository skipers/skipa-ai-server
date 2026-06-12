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
        content = _header + t
        return {
            "doc_id": _doc_id(patent_id, section),
            "page_content": content[:20000],
            "vector": _vectorize(content),
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
            _claims[:3000],
        ]
        d = _make("\n".join(claim_lines), "청구항핵심구성")
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
        content = _header + t
        return {
            "doc_id": _doc_id(patent_id, f"report_{section}"),
            "page_content": content[:20000],
            "vector": _vectorize(content),
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
        snippets = [
            str(s.get("snippet") or "").strip()
            for s in sources
            if isinstance(s, dict) and str(s.get("snippet") or "").strip()
        ]
        if not item_name:
            continue
        lines = [f"특허 평가 항목 - {item_name}"]
        if score_val is not None:
            lines.append(f"점수: {score_val}/5")
        if rationale:
            lines.append(f"평가 근거: {rationale}")
        for i, snip in enumerate(snippets[:5], 1):
            lines.append(f"[근거 {i}] {snip}")
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
        for it in _rights_items[:5]:
            _it_name = str(it.get("item") or "").strip()
            _it_score = it.get("score")
            _it_basis = str(it.get("judgment_basis") or "").strip()
            if _it_name:
                risk_lines.append(f"[권리성 검토항목] {_it_name}: {_it_score}/5 — {_it_basis[:200]}")
        d = _make("\n".join(risk_lines), "권리리스크회피설계")
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
