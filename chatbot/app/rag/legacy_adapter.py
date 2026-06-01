"""Adapter that lets the current LangGraph app use the restored rag.zip engine."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.responses import FileResponse

from ..config import LOG_ROOT, PATENTS_ROOT
from ..store import list_patents
from ..vectorstore import refresh_vectorstores


@lru_cache(maxsize=1)
def _legacy_import_error() -> str | None:
    try:
        from ..legacy.rag_pipeline import PatentRAGPipeline  # noqa: F401
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


@lru_cache(maxsize=1)
def _pipeline() -> Any:
    error = _legacy_import_error()
    if error:
        raise RuntimeError(error)
    from ..legacy.rag_pipeline import PatentRAGPipeline

    return PatentRAGPipeline()


def legacy_engine_status() -> dict[str, Any]:
    error = _legacy_import_error()
    return {
        "available": error is None,
        "engine": "rag.zip FAISS+BM25+RRF+intent+web" if error is None else "lightweight-fallback",
        "error": error,
    }


def _card_value(card: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = card.get(key)
        if value not in (None, ""):
            return value
    return None


def _resolve_source_url(url: str | None, metadata: dict[str, Any]) -> str | None:
    if not url:
        return None
    normalized = url.replace("http://localhost:8000/files/patents", "/files/patents")
    normalized = normalized.replace("http://localhost:8000/files/business", "/files/business")
    normalized = normalized.replace("http://localhost:8000/files/data", "/files/data")
    if not normalized.startswith("/files/patents/"):
        return normalized

    suffix = normalized.removeprefix("/files/patents/")
    patent_id, _, rel = suffix.partition("/")
    if not patent_id:
        return normalized
    rel_no_fragment = rel.split("#", 1)[0]
    patent_dir = PATENTS_ROOT / patent_id
    candidates = []
    if rel_no_fragment:
        candidates.append(patent_dir / rel_no_fragment)
    if rel_no_fragment == "original.pdf":
        candidates.append(patent_dir / "original" / "pdf" / "latest.pdf")
    if rel_no_fragment in {"report.html", "report.pdf"}:
        candidates.append(patent_dir / "reports" / "json" / "latest.json")
    for candidate in candidates:
        if candidate.exists():
            try:
                current_rel = candidate.relative_to(PATENTS_ROOT).as_posix()
            except ValueError:
                return normalized
            fragment = f"#{normalized.split('#', 1)[1]}" if "#" in normalized else ""
            return f"/files/patents/{current_rel}{fragment}"
    source_type = str(metadata.get("source_type") or "")
    if source_type:
        return f"/api/v1/chatbot/patents/{patent_id}/chunks?source_type={source_type}&limit=20"
    return f"/api/v1/chatbot/patents/{patent_id}/chunks?limit=20"


def _normalize_source_card(card: dict[str, Any], index: int) -> dict[str, Any]:
    metadata = dict(card.get("metadata") or {})
    for key, value in card.items():
        if key not in {"label", "title", "source_type", "page_no", "url", "source_url", "snippet", "metadata"}:
            metadata.setdefault(key, value)
    page_no = _card_value(card, "page_no", "page")
    try:
        page_no = int(page_no) if page_no is not None else None
    except (TypeError, ValueError):
        page_no = None
    raw_url = _card_value(card, "url", "source_url")
    url = _resolve_source_url(raw_url if isinstance(raw_url, str) else None, metadata)
    return {
        "label": str(card.get("label") or f"자료{index}"),
        "title": _card_value(card, "title", "section_title", "file_name"),
        "source_type": str(card.get("source_type") or metadata.get("source_type") or "UNKNOWN"),
        "page_no": page_no,
        "url": url,
        "snippet": str(card.get("snippet") or card.get("excerpt") or ""),
        "metadata": metadata,
    }


def normalize_legacy_answer(result: dict[str, Any], *, query: str, patent_id: str | None) -> dict[str, Any]:
    metrics = dict(result.get("metrics") or {})
    metrics.setdefault("engine", "legacy_faiss_bm25_rrf")
    metrics.setdefault("legacy_available", True)
    cards = [
        _normalize_source_card(card, index)
        for index, card in enumerate(list(result.get("source_cards") or []), 1)
        if isinstance(card, dict)
    ]
    return {
        "query": query,
        "patent_id": patent_id or metrics.get("patent_id"),
        "answer": str(result.get("answer") or ""),
        "source_cards": cards,
        "metrics": metrics,
    }


def try_answer_with_legacy(
    query: str,
    *,
    patent_id: str | None = None,
    top_k: int = 5,
    user_id: str | None = None,
    chat_history: list[dict[str, Any]] | None = None,
    context_patent_id: str | None = None,
) -> dict[str, Any] | None:
    if _legacy_import_error():
        return None
    try:
        pipeline = _pipeline()
        if patent_id:
            result = pipeline.answer(
                patent_id=patent_id,
                question=query,
                user_id=user_id,
                chat_history=chat_history,
                context_patent_id=context_patent_id,
            )
        else:
            result = pipeline.answer_global(
                question=query,
                user_id=user_id,
                chat_history=chat_history,
                context_patent_id=context_patent_id,
            )
        normalized = normalize_legacy_answer(result, query=query, patent_id=patent_id)
        normalized["metrics"]["requested_top_k"] = top_k
        return normalized
    except Exception as exc:
        return {
            "query": query,
            "patent_id": patent_id,
            "answer": "",
            "source_cards": [],
            "metrics": {
                "engine": "legacy_faiss_bm25_rrf",
                "legacy_available": True,
                "legacy_error": f"{type(exc).__name__}: {exc}",
                "fallback_required": True,
            },
        }


def patent_summary_cards() -> dict[str, Any]:
    if not _legacy_import_error():
        try:
            return {"engine": "legacy_faiss_bm25_rrf", "items": _pipeline().build_patent_summary_cards()}
        except Exception as exc:
            fallback = _summary_card_fallback()
            fallback["legacy_error"] = f"{type(exc).__name__}: {exc}"
            return fallback
    return _summary_card_fallback()


def _summary_card_fallback() -> dict[str, Any]:
    items = []
    for patent in list_patents():
        items.append(
            {
                "patent_id": patent.get("patent_id"),
                "title": patent.get("title"),
                "total": None,
                "score_level": "UNKNOWN",
                "domain_terms": [],
                "chunk_count": patent.get("chunk_count", 0),
                "has_latest_input": patent.get("has_latest_input"),
                "has_latest_report": patent.get("has_latest_report"),
                "has_patent_index": patent.get("has_patent_index"),
            }
        )
    return {"engine": "fallback_catalog", "items": items}


def reindex_patent(patent_id: str, *, force_rebuild: bool = True, refresh_reviewed_vectorstore: bool = False) -> dict[str, Any]:
    if _legacy_import_error():
        raise HTTPException(status_code=503, detail=f"레거시 RAG 의존성이 없습니다: {_legacy_import_error()}")
    try:
        _pipeline().build_or_load_patent_index(patent_id=patent_id, force_rebuild=force_rebuild)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    result: dict[str, Any] = {
        "status": "OK",
        "scope": "PATENT",
        "patent_id": patent_id,
        "engine": "legacy_faiss_bm25_rrf",
        "force_rebuild": force_rebuild,
    }
    if refresh_reviewed_vectorstore:
        result["reviewed_vectorstore"] = refresh_vectorstores(use_reviewed=True)
    return result


def reindex_global(*, force_rebuild: bool = True, refresh_reviewed_vectorstore: bool = False) -> dict[str, Any]:
    if _legacy_import_error():
        raise HTTPException(status_code=503, detail=f"레거시 RAG 의존성이 없습니다: {_legacy_import_error()}")
    try:
        _pipeline().build_or_load_global_index(force_rebuild=force_rebuild)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    result: dict[str, Any] = {
        "status": "OK",
        "scope": "GLOBAL",
        "engine": "legacy_faiss_bm25_rrf",
        "force_rebuild": force_rebuild,
    }
    if refresh_reviewed_vectorstore:
        result["reviewed_vectorstore"] = refresh_vectorstores(use_reviewed=True)
    return result


def reindex_business(*, force_rebuild: bool = True, refresh_reviewed_vectorstore: bool = False) -> dict[str, Any]:
    if _legacy_import_error():
        raise HTTPException(status_code=503, detail=f"레거시 RAG 의존성이 없습니다: {_legacy_import_error()}")
    try:
        _pipeline().build_or_load_business_index(force_rebuild=force_rebuild)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    result: dict[str, Any] = {
        "status": "OK",
        "scope": "BUSINESS",
        "engine": "legacy_faiss_bm25_rrf",
        "force_rebuild": force_rebuild,
    }
    if refresh_reviewed_vectorstore:
        result["reviewed_vectorstore"] = refresh_vectorstores(use_reviewed=True)
    return result


def write_feedback(row: dict[str, Any]) -> dict[str, str]:
    path = LOG_ROOT / "rag_feedback_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"status": "OK", "path": str(path)}


def render_page_image(patent_id: str, *, file_name: str = "original.pdf", page_no: int = 1) -> FileResponse:
    if page_no < 1:
        raise HTTPException(status_code=400, detail="page_no must be >= 1")
    patent_dir = (PATENTS_ROOT / patent_id).resolve()
    if not patent_dir.exists():
        raise HTTPException(status_code=404, detail=f"특허 폴더를 찾을 수 없습니다: {patent_id}")

    candidates = []
    if file_name == "original.pdf":
        candidates.append(patent_dir / "original" / "pdf" / "latest.pdf")
    candidates.append(patent_dir / file_name)
    pdf_path = next((path.resolve() for path in candidates if path.exists()), None)
    if pdf_path is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    try:
        pdf_path.relative_to(patent_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid pdf path") from exc
    if pdf_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="invalid pdf path")

    cache_dir = patent_dir / "extracted" / "page_images"
    cache_dir.mkdir(parents=True, exist_ok=True)
    image_path = cache_dir / f"{pdf_path.stem}_p{page_no}.png"
    if not image_path.exists():
        try:
            import fitz
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"PyMuPDF가 필요합니다: {exc}") from exc
        with fitz.open(str(pdf_path)) as pdf:
            if page_no > len(pdf):
                raise HTTPException(status_code=404, detail="page not found")
            page = pdf.load_page(page_no - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.15, 1.15), alpha=False)
            pix.save(str(image_path))

    return FileResponse(str(image_path), media_type="image/png")
