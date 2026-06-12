"""Pre-application valuation case management: evaluate, index, search, chat."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from fastapi import HTTPException

from .config import PRE_EVAL_ROOT, PROJECT_ROOT, WIKI_ROOT
from .qdrant_store import (
    collection_exists,
    collection_info,
    pre_application_collection,
    pre_eval_collection,
    search_documents,
    upsert_documents,
)
from .rag.quality import compact_text, is_usable_evidence


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRE_EVAL_SOURCE_TYPE = "PRE_EVAL_REPORT"
TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _safe_case_id(raw: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z가-힣_.-]", "_", str(raw or "")).strip("._")
    return cleaned[:80] or "unknown"


def _case_id_from_name(patent_name: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^0-9A-Za-z가-힣]", "_", patent_name.strip())[:40].strip("_")
    return f"{stamp}_{slug}"


def _pre_eval_case_dir(case_id: str) -> Path:
    return PRE_EVAL_ROOT / case_id


def _case_metadata_path(case_id: str) -> Path:
    return _pre_eval_case_dir(case_id) / "metadata.json"


def _case_report_path(case_id: str) -> Path:
    return _pre_eval_case_dir(case_id) / "report.json"


def _case_report_md_path(case_id: str) -> Path:
    return _pre_eval_case_dir(case_id) / "report.md"


def _case_input_path(case_id: str) -> Path:
    return _pre_eval_case_dir(case_id) / "input.json"


def _case_vectorstore_root(case_id: str) -> Path:
    return _pre_eval_case_dir(case_id) / "index" / "qdrant"


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Vectorizer (same lightweight BoW as vectorstore.py)
# ---------------------------------------------------------------------------

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


def _dot(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(a.get(k, 0.0) * v for k, v in b.items())


# ---------------------------------------------------------------------------
# pre_application_valuation integration
# ---------------------------------------------------------------------------

def _run_evaluation(request_data: dict[str, Any], *, enable_llm: bool = True) -> dict[str, Any]:
    preval_root = PROJECT_ROOT / "pre_application_valuation"
    if not preval_root.exists():
        raise HTTPException(status_code=500, detail=f"pre_application_valuation 모듈 없음: {preval_root}")
    inserted = False
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
        inserted = True
    try:
        from pre_application_valuation.service import evaluate_pre_application
        from pre_application_valuation.schemas import PreApplicationValuationRequest

        if not enable_llm:
            import pre_application_valuation.llm_comment as _llm_mod
            _orig = _llm_mod.generate_llm_overall_comment
            _llm_mod.generate_llm_overall_comment = lambda *a, **kw: {
                "overall_comment": (a[3] if len(a) > 3 else kw.get("fallback_comment", "")),
                "source": "fallback", "model": None,
            }
        result = evaluate_pre_application(PreApplicationValuationRequest.model_validate(request_data))
        if not enable_llm:
            _llm_mod.generate_llm_overall_comment = _orig
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"사전 평가 실패: {type(exc).__name__}: {exc}") from exc
    finally:
        if inserted:
            try:
                sys.path.remove(str(PROJECT_ROOT))
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# Report → vectorstore documents
# ---------------------------------------------------------------------------

def _report_to_docs(case_id: str, report: dict[str, Any], report_md: str) -> list[dict[str, Any]]:
    """Convert evaluation report into indexable chunks."""
    docs: list[dict[str, Any]] = []
    base_meta = {
        "case_id": case_id,
        "source_type": PRE_EVAL_SOURCE_TYPE,
        "patent_title": report.get("patent_title", ""),
        "schema_version": report.get("schema_version", ""),
    }

    def _doc(text: str, extra: dict[str, Any]) -> dict[str, Any] | None:
        t = str(text or "").strip()
        if not t or len(t) < 20:
            return None
        h = hashlib.sha1(t.encode("utf-8")).hexdigest()[:12]
        return {
            "doc_id": f"{case_id}_{h}",
            "page_content": t[:20000],
            "vector": _vectorize(t),
            "metadata": {**base_meta, **extra, "source_path": str(_case_report_path(case_id))},
        }

    # Full markdown summary
    if report_md:
        d = _doc(report_md, {"section_title": "전체 보고서 요약", "file_name": "report.md"})
        if d:
            docs.append(d)

    # Overall comment
    overall = report.get("overall") if isinstance(report.get("overall"), dict) else {}
    if overall.get("comment"):
        d = _doc(
            f"종합 등급: {overall.get('grade')} / {overall.get('score_out_of_100')}점\n{overall['comment']}",
            {"section_title": "종합 평가", "file_name": "overall_comment"},
        )
        if d:
            docs.append(d)

    # Dimension comments
    for item in (report.get("comments") or []):
        if isinstance(item, dict) and item.get("comment"):
            d = _doc(item["comment"], {"section_title": item.get("dimension", "영역"), "file_name": "dimension_comment"})
            if d:
                docs.append(d)

    # Recommendations
    recs = report.get("recommendations") or []
    if recs:
        d = _doc("개선 권고사항:\n" + "\n".join(f"- {r}" for r in recs), {"section_title": "개선 권고사항", "file_name": "recommendations"})
        if d:
            docs.append(d)

    # Score items
    for item in (report.get("score_items") or []):
        if not isinstance(item, dict):
            continue
        text = f"{item.get('dimension','')}/{item.get('name','')} 점수={item.get('score_out_of_100','')} {item.get('comment','')}"
        d = _doc(text, {"section_title": f"점수항목_{item.get('name','')}", "file_name": "score_item"})
        if d:
            docs.append(d)

    return docs


# ---------------------------------------------------------------------------
# Vectorstore write / search
# ---------------------------------------------------------------------------

def _write_pre_eval_vectorstore(case_id: str, docs: list[dict[str, Any]]) -> dict[str, Any]:
    vs_root = _case_vectorstore_root(case_id)
    manifest = {
        "scope": f"pre_eval:{case_id}",
        "refreshed_at": _now(),
        "backend": "qdrant",
        "document_count": len(docs),
        "source": "pre_application_valuation",
    }
    vs_root.mkdir(parents=True, exist_ok=True)
    result = upsert_documents(
        pre_eval_collection(case_id),
        docs,
        collection_scope=f"pre_eval:{case_id}",
        recreate=True,
        extra_payload={"case_id": case_id, "source": "pre_application_valuation"},
    )
    _write_json(vs_root / "manifest.json", {**manifest, "collection": pre_eval_collection(case_id), "qdrant": result})
    return result


def search_pre_eval_vectorstore(case_id: str, query: str, top_k: int = 8) -> dict[str, Any]:
    """Search the pre-eval case Qdrant collection."""
    collection = pre_eval_collection(case_id)
    if not collection_exists(collection):
        return {"query": query, "case_id": case_id, "mode": "pre_eval_qdrant", "collection": collection, "hit_count": 0, "hits": []}
    result = search_documents(collection, query, top_k=top_k, case_id=case_id)
    return {
        "query": query,
        "case_id": case_id,
        "mode": "pre_eval_qdrant",
        "collection": collection,
        "hit_count": result.get("hit_count", 0),
        "hits": result.get("hits", []),
        "embedding_provider": result.get("embedding_provider"),
        "embedding_error": result.get("embedding_error"),
    }


# ---------------------------------------------------------------------------
# Report markdown
# ---------------------------------------------------------------------------

def _build_report_markdown(case_id: str, report: dict[str, Any]) -> str:
    overall = report.get("overall") if isinstance(report.get("overall"), dict) else {}
    dimensions = report.get("dimensions") if isinstance(report.get("dimensions"), list) else []
    ipc = report.get("ai_classification") if isinstance(report.get("ai_classification"), dict) else {}
    recommendations = report.get("recommendations") or []
    comments = report.get("comments") or []
    frontend = report.get("frontend_summary") if isinstance(report.get("frontend_summary"), dict) else {}

    lines = [
        f"# {report.get('patent_title', case_id)} 출원 전 사전평가 보고서",
        "",
        "## 평가 개요",
        f"- Case ID: `{case_id}`",
        f"- 특허명: {report.get('patent_title', '-')}",
        f"- 평가 ID: `{report.get('evaluation_id', '-')}`",
        f"- 평가일시: {report.get('evaluated_at', '-')}",
        f"- IPC 분류: {ipc.get('ipc', '-')}  분야: {ipc.get('field', '-')}",
        "",
        "## 종합 점수",
        f"- **등급: {overall.get('grade', '-')}**",
        f"- 100점 환산: {overall.get('score_out_of_100', '-')}점",
        f"- 평균(1~5): {overall.get('score', '-')}",
        "",
        f"> {overall.get('comment', '종합 의견 없음')}",
        "",
        "## 영역별 점수",
        "| 영역 | 평균(1~5) | 100점 |",
        "| --- | ---: | ---: |",
    ]
    for dim in dimensions:
        lines.append(f"| {dim.get('label', dim.get('key', '-'))} | {dim.get('average_score', '-')} | {dim.get('score_out_of_100', '-')} |")
    lines.extend(["", "## 영역별 의견", ""])
    for c in comments:
        lines.append(f"- **{c.get('dimension', '-')}**: {c.get('comment', '')}")
    lines.extend(["", "## 개선 권고사항", ""])
    for r in recommendations:
        lines.append(f"- {r}")
    lines.extend([
        "",
        "## 강점 / 약점",
        f"- 강점 영역: {frontend.get('strongest_dimension', '-')}",
        f"- 약점 영역: {frontend.get('weakest_dimension', '-')}",
    ])
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Wiki web search during evaluation
# ---------------------------------------------------------------------------

def _run_wiki_web_search_for_case(case_id: str, patent_title: str, ipc_field: str) -> dict[str, Any]:
    """Run web search for the patent topic and save results to wiki."""
    from .wiki.topics import classify_title_to_topic, topic_draft_dir
    from .vectorstore import auto_approve_web_draft
    from .rag.web_answers import search_web

    topic = classify_title_to_topic(patent_title)
    queries = [
        f"{patent_title} 선행기술 동향",
        f"{ipc_field or patent_title} 특허 기술 분야",
    ]
    results_summary: list[dict[str, Any]] = []
    for query in queries:
        try:
            result = search_web(query)
            web_results = result.get("results") or []
            if web_results:
                # Save draft to topic wiki folder
                draft_dir = topic_draft_dir(topic)
                draft_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                draft_path = draft_dir / f"preval_{case_id}_{stamp}.md"
                lines = [
                    "# Pre-eval Web Search Draft",
                    f"- Query: {query}",
                    f"- Case ID: {case_id}",
                    f"- Patent: {patent_title}",
                    f"- Topic: {topic}",
                    "",
                ]
                for idx, r in enumerate(web_results, 1):
                    lines.extend([f"### {idx}. {r.get('title', '')}", f"- URL: {r.get('url', '')}", "", str(r.get("snippet", "")), ""])
                draft_path.write_text("\n".join(lines), encoding="utf-8")
                # Auto-approve to wiki
                auto_approve_result = auto_approve_web_draft(
                    f"_preval_{case_id}",
                    draft_path=str(draft_path),
                    query=query,
                    results=web_results,
                )
                results_summary.append({"query": query, "topic": topic, "result_count": len(web_results), "auto_approve": auto_approve_result})
        except Exception as exc:
            results_summary.append({"query": query, "error": str(exc)})
    return {"topic": topic, "queries": results_summary}


# ---------------------------------------------------------------------------
# Case CRUD
# ---------------------------------------------------------------------------

def create_pre_eval_case(
    request_data: dict[str, Any],
    *,
    enable_llm: bool = True,
    run_web_search: bool = True,
) -> dict[str, Any]:
    """Run evaluation, save report, build vectorstore, optionally do wiki web search."""
    patent_name = str(request_data.get("patentName") or request_data.get("patent_name") or "").strip()
    if not patent_name:
        raise HTTPException(status_code=400, detail="patentName은 필수입니다.")

    case_id = _case_id_from_name(patent_name)
    case_dir = _pre_eval_case_dir(case_id)
    case_dir.mkdir(parents=True, exist_ok=True)

    # Save input
    _write_json(_case_input_path(case_id), {**request_data, "case_id": case_id, "created_at": _now()})

    # Run evaluation
    report = _run_evaluation(request_data, enable_llm=enable_llm)
    report["case_id"] = case_id

    # Build markdown
    report_md = _build_report_markdown(case_id, report)

    # Save report
    _write_json(_case_report_path(case_id), report)
    _case_report_md_path(case_id).write_text(report_md, encoding="utf-8")

    # Build vectorstore from report
    docs = _report_to_docs(case_id, report, report_md)
    rotation = _write_pre_eval_vectorstore(case_id, docs)

    # Wiki web search
    wiki_result: dict[str, Any] = {}
    if run_web_search:
        try:
            ipc = report.get("ai_classification") if isinstance(report.get("ai_classification"), dict) else {}
            wiki_result = _run_wiki_web_search_for_case(case_id, patent_name, str(ipc.get("field") or ""))
        except Exception as exc:
            wiki_result = {"error": str(exc)}

    # Save metadata
    overall = report.get("overall") if isinstance(report.get("overall"), dict) else {}
    metadata = {
        "case_id": case_id,
        "patent_title": patent_name,
        "created_at": _now(),
        "evaluation_id": report.get("evaluation_id"),
        "overall_grade": overall.get("grade"),
        "overall_score_out_of_100": overall.get("score_out_of_100"),
        "schema_version": report.get("schema_version"),
        "vectorstore_document_count": len(docs),
        "wiki_web_search": wiki_result,
    }
    _write_json(_case_metadata_path(case_id), metadata)

    return {
        "status": "created",
        "case_id": case_id,
        "patent_title": patent_name,
        "overall_grade": overall.get("grade"),
        "overall_score_out_of_100": overall.get("score_out_of_100"),
        "vectorstore_document_count": len(docs),
        "rotation": rotation,
        "wiki_web_search": wiki_result,
        "report_path": str(_case_report_path(case_id)),
        "report_md_path": str(_case_report_md_path(case_id)),
    }


def list_pre_eval_cases() -> list[dict[str, Any]]:
    if not PRE_EVAL_ROOT.exists():
        return []
    cases = []
    for d in sorted(PRE_EVAL_ROOT.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta = _read_json(d / "metadata.json")
        cases.append({
            "case_id": d.name,
            "patent_title": meta.get("patent_title", d.name),
            "created_at": meta.get("created_at"),
            "overall_grade": meta.get("overall_grade"),
            "overall_score_out_of_100": meta.get("overall_score_out_of_100"),
            "has_report": (d / "report.json").exists(),
            "has_vectorstore": collection_exists(pre_eval_collection(d.name)),
            "backend": "qdrant",
            "collection": pre_eval_collection(d.name),
        })
    return cases


def pre_eval_case_status(case_id: str) -> dict[str, Any]:
    safe_id = _safe_case_id(case_id)
    case_dir = _pre_eval_case_dir(safe_id)
    if not case_dir.exists():
        raise HTTPException(status_code=404, detail=f"사전 평가 케이스를 찾을 수 없습니다: {safe_id}")
    meta = _read_json(_case_metadata_path(safe_id))
    qdrant = collection_info(pre_eval_collection(safe_id))
    return {
        "case_id": safe_id,
        "patent_title": meta.get("patent_title"),
        "created_at": meta.get("created_at"),
        "overall_grade": meta.get("overall_grade"),
        "overall_score_out_of_100": meta.get("overall_score_out_of_100"),
        "schema_version": meta.get("schema_version"),
        "backend": "qdrant",
        "collection": pre_eval_collection(safe_id),
        "vectorstore_exists": bool(qdrant.get("exists")),
        "vectorstore_document_count": qdrant.get("points_count", 0),
        "vectorstore_refreshed_at": None,
        "qdrant": qdrant,
        "report_path": str(_case_report_path(safe_id)),
        "report_md_path": str(_case_report_md_path(safe_id)),
    }


def refresh_pre_eval_case_index(case_id: str) -> dict[str, Any]:
    safe_id = _safe_case_id(case_id)
    report_path = _case_report_path(safe_id)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"보고서 없음: {safe_id}")
    report = _read_json(report_path)
    report_md_path = _case_report_md_path(safe_id)
    report_md = report_md_path.read_text(encoding="utf-8") if report_md_path.exists() else ""
    docs = _report_to_docs(safe_id, report, report_md)
    rotation = _write_pre_eval_vectorstore(safe_id, docs)
    return {"case_id": safe_id, "document_count": len(docs), "rotation": rotation}


def get_pre_eval_report(case_id: str) -> dict[str, Any]:
    safe_id = _safe_case_id(case_id)
    report_path = _case_report_path(safe_id)
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"보고서 없음: {safe_id}")
    return _read_json(report_path)


# ---------------------------------------------------------------------------
# 사전 출원 특허 보고서 웹훅 — MinIO → pre-{patent_id} vectorstore
# ---------------------------------------------------------------------------

def _pre_application_case_dir(patent_id: str) -> Path:
    safe = re.sub(r"[^0-9A-Za-z가-힣_.-]", "_", str(patent_id or "")).strip("._")[:80]
    return PRE_EVAL_ROOT / f"pre_{safe}"


def _index_pre_application_report(patent_id: str, report: dict[str, Any]) -> dict[str, Any]:
    """보고서 dict를 pre-{patent_id} 컬렉션에 인덱싱합니다."""
    # 보고서 텍스트를 청크로 변환 (기존 _report_to_docs 활용)
    case_dir = _pre_application_case_dir(patent_id)
    case_dir.mkdir(parents=True, exist_ok=True)

    report_path = case_dir / "report.json"
    _write_json(report_path, report)

    report_md = _build_report_markdown(patent_id, report)
    (case_dir / "report.md").write_text(report_md, encoding="utf-8")

    docs = _report_to_docs(patent_id, report, report_md)

    collection = pre_application_collection(patent_id)
    result = upsert_documents(
        collection,
        docs,
        collection_scope=f"pre_application:{patent_id}",
        recreate=False,
        extra_payload={"patent_id": patent_id, "source": "pre_application_webhook"},
    )

    manifest = {
        "patent_id": patent_id,
        "collection": collection,
        "indexed_at": _now(),
        "document_count": len(docs),
        "source": "minio_webhook",
        "qdrant": result,
    }
    _write_json(case_dir / "manifest.json", manifest)
    return manifest


def handle_report_complete_webhook(patent_id: str) -> dict[str, Any]:
    """외부 시스템이 보고서 생성 완료를 알릴 때 호출됩니다.

    MinIO에서 report.json을 찾아 pre-{patent_id} 컬렉션에 임베딩·저장합니다.
    blue-green 없이 단순 upsert — 컬렉션은 누적 생성됩니다.
    """
    from .minio_data import fetch_pre_application_report_from_minio

    fetch = fetch_pre_application_report_from_minio(patent_id)
    if not fetch.get("found"):
        raise HTTPException(
            status_code=404,
            detail=f"MinIO에서 report.json을 찾을 수 없습니다: {fetch.get('error')}",
        )

    report = fetch["report"]
    manifest = _index_pre_application_report(patent_id, report)

    return {
        "status": "indexed",
        "patent_id": patent_id,
        "collection": manifest["collection"],
        "document_count": manifest["document_count"],
        "source_key": fetch.get("source_key"),
        "indexed_at": manifest["indexed_at"],
    }


def pre_application_vectorstore_status(patent_id: str) -> dict[str, Any]:
    """pre-{patent_id} 컬렉션 상태를 반환합니다."""
    collection = pre_application_collection(patent_id)
    info = collection_info(collection)
    case_dir = _pre_application_case_dir(patent_id)
    manifest = _read_json(case_dir / "manifest.json") if case_dir.exists() else {}
    return {
        "patent_id": patent_id,
        "collection": collection,
        "exists": bool(info.get("exists")),
        "document_count": info.get("points_count", 0),
        "indexed_at": manifest.get("indexed_at"),
        "source_key": manifest.get("source_key"),
        "qdrant": info,
    }


def list_pre_application_vectorstores() -> list[dict[str, Any]]:
    """PRE_EVAL_ROOT 아래 pre_ 접두사 디렉터리를 스캔하여 각 컬렉션 상태를 반환합니다."""
    if not PRE_EVAL_ROOT.exists():
        return []
    results: list[dict[str, Any]] = []
    for d in sorted(PRE_EVAL_ROOT.iterdir(), reverse=True):
        if not d.is_dir() or not d.name.startswith("pre_"):
            continue
        patent_id = d.name[len("pre_"):]
        manifest = _read_json(d / "manifest.json")
        collection = pre_application_collection(patent_id)
        info = collection_info(collection)
        results.append({
            "patent_id": patent_id,
            "collection": collection,
            "exists": bool(info.get("exists")),
            "document_count": info.get("points_count", 0),
            "indexed_at": manifest.get("indexed_at"),
            "source_key": manifest.get("source_key"),
        })
    return results


def search_pre_application_vectorstore(patent_id: str, query: str, top_k: int = 8) -> dict[str, Any]:
    """pre-{patent_id} 컬렉션 검색."""
    collection = pre_application_collection(patent_id)
    if not collection_exists(collection):
        return {"query": query, "patent_id": patent_id, "collection": collection, "hit_count": 0, "hits": []}
    result = search_documents(collection, query, top_k=top_k)
    return {
        "query": query,
        "patent_id": patent_id,
        "collection": collection,
        "hit_count": result.get("hit_count", 0),
        "hits": result.get("hits", []),
        "embedding_provider": result.get("embedding_provider"),
    }
