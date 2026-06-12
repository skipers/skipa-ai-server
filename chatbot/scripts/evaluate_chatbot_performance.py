#!/usr/bin/env python3
"""Comprehensive performance evaluation for the SKIPA chatbot stack.

The script is intentionally read-mostly: it checks MinIO/Qdrant connectivity,
data coverage, vectorstore health, API latency, retrieval latency, and a small
set of end-to-end chat answers. It writes JSON and Markdown artifacts under
``chatbot/data/artifacts/chatbot_performance_eval``.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any, Callable


SCRIPT_PATH = Path(__file__).resolve()
PROJECT_ROOT = SCRIPT_PATH.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ARTIFACT_ROOT = PROJECT_ROOT / "chatbot" / "data" / "artifacts" / "chatbot_performance_eval"
SECRET_KEY_PARTS = ("SECRET", "TOKEN", "PASSWORD", "AUTHORIZATION")


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _prepare_env() -> None:
    for path in (PROJECT_ROOT / ".env", PROJECT_ROOT / "chatbot" / ".env", PROJECT_ROOT / "eval_logic" / ".env"):
        _load_env(path)
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    # This script performs explicit status checks. Avoid accidental startup sync
    # if a TestClient or imported app enters FastAPI lifespan in the future.
    os.environ.setdefault("MINIO_SYNC_ON_STARTUP", "false")
    os.environ.setdefault("REINDEX_INITIAL_DELAY_SECONDS", "86400")


def _redact(value: Any, key: str = "") -> Any:
    upper_key = key.upper()
    looks_like_key = (
        upper_key in {"KEY", "APIKEY", "API_KEY", "ACCESSKEY", "ACCESS_KEY", "SECRETKEY", "SECRET_KEY"}
        or upper_key.endswith("_KEY")
        or upper_key.endswith(" API KEY")
        or "API_KEY" in upper_key
        or "ACCESS_KEY" in upper_key
        or "SECRET_KEY" in upper_key
    )
    if looks_like_key or any(part in upper_key for part in SECRET_KEY_PARTS):
        return "***set***" if value else ""
    if isinstance(value, dict):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item, key) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _timed(name: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        ok = True
        error = None
    except Exception as exc:  # noqa: BLE001 - evaluation must keep running.
        result = None
        ok = False
        error = f"{type(exc).__name__}: {exc}"
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {"name": name, "ok": ok, "elapsed_ms": elapsed_ms, "error": error, "result": _redact(result)}


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    index = (len(ordered) - 1) * pct
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return round(ordered[lower] * (1 - fraction) + ordered[upper] * fraction, 2)


def _latency_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(row["elapsed_ms"]) for row in rows if row.get("ok")]
    if not values:
        return {"count": 0, "avg_ms": None, "p50_ms": None, "p95_ms": None, "max_ms": None}
    return {
        "count": len(values),
        "avg_ms": round(statistics.mean(values), 2),
        "p50_ms": _percentile(values, 0.50),
        "p95_ms": _percentile(values, 0.95),
        "max_ms": round(max(values), 2),
    }


def _compact_source_card(card: dict[str, Any]) -> dict[str, Any]:
    metadata = card.get("metadata") if isinstance(card.get("metadata"), dict) else {}
    return {
        "title": card.get("title") or card.get("display_title") or metadata.get("section_title"),
        "source_type": card.get("source_type") or metadata.get("source_type"),
        "patent_id": metadata.get("patent_id"),
        "retrieval_score": metadata.get("retrieval_score"),
        "snippet": str(card.get("snippet") or "")[:500],
    }


def _compact_hit(hit: dict[str, Any]) -> dict[str, Any]:
    metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
    return {
        "patent_id": hit.get("patent_id") or metadata.get("patent_id"),
        "score": hit.get("score"),
        "rrf_score": hit.get("rrf_score"),
        "source_type": metadata.get("source_type"),
        "section_title": metadata.get("section_title"),
        "file_name": metadata.get("file_name"),
        "excerpt": str(hit.get("excerpt") or hit.get("page_content") or "")[:500],
    }


def _patch_optional_quality_costs() -> None:
    import chatbot.app.rag.evaluation as evaluation

    def _skip_bert(answer: str, evidence_text: str) -> dict[str, Any]:
        return {
            "available": False,
            "reason": "skipped by chatbot performance evaluation to avoid model download/runtime noise",
            "fallback_metric": "semantic_answer_evidence_score",
        }

    evaluation._optional_bert_score = _skip_bert  # type: ignore[attr-defined]


def _select_sample_patents(patents: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    preferred = [
        item for item in patents
        if item.get("patent_id")
        and item.get("title")
        and str(item.get("title")) != str(item.get("patent_id"))
        and (item.get("has_report") or item.get("has_latest_report"))
    ]
    fallback = [item for item in patents if item.get("patent_id")]
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in preferred + fallback:
        pid = str(item.get("patent_id"))
        if pid in seen:
            continue
        seen.add(pid)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def _data_coverage(patents: list[dict[str, Any]]) -> dict[str, Any]:
    def has(item: dict[str, Any], *keys: str) -> bool:
        return any(bool(item.get(key)) for key in keys)

    report_status = Counter()
    invalid_validation_count = 0
    report_paths_scanned = 0
    from chatbot.app.config import SHARED_PATENT_ROOT

    for item in patents:
        pid = str(item.get("patent_id") or "")
        report_path = SHARED_PATENT_ROOT / pid / "report.json"
        if not report_path.exists():
            continue
        report_paths_scanned += 1
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception:
            report_status["unreadable"] += 1
            continue
        status = str(data.get("status") or "unknown")
        report_status[status] += 1
        validation = data.get("validation") if isinstance(data.get("validation"), dict) else {}
        if validation and validation.get("valid") is False:
            invalid_validation_count += 1

    chunk_counts = [int(item.get("chunk_count") or 0) for item in patents]
    total = len(patents)
    return {
        "patent_count": total,
        "has_input_count": sum(1 for item in patents if has(item, "has_parsed", "has_latest_input")),
        "has_report_count": sum(1 for item in patents if has(item, "has_report", "has_latest_report")),
        "has_pdf_count": sum(1 for item in patents if has(item, "has_pdf", "has_latest_pdf")),
        "has_qdrant_flag_count": sum(1 for item in patents if has(item, "has_qdrant_vectorstore", "has_local_vectorstore")),
        "chunk_count_total": sum(chunk_counts),
        "chunk_count_avg": round(statistics.mean(chunk_counts), 2) if chunk_counts else 0,
        "chunk_count_max": max(chunk_counts) if chunk_counts else 0,
        "report_paths_scanned": report_paths_scanned,
        "report_status_counts": dict(report_status),
        "invalid_validation_count": invalid_validation_count,
        "coverage_ratios": {
            "input": round(sum(1 for item in patents if has(item, "has_parsed", "has_latest_input")) / total, 4) if total else 0,
            "report": round(sum(1 for item in patents if has(item, "has_report", "has_latest_report")) / total, 4) if total else 0,
            "pdf": round(sum(1 for item in patents if has(item, "has_pdf", "has_latest_pdf")) / total, 4) if total else 0,
        },
    }


def _collection_snapshot() -> dict[str, Any]:
    from chatbot.app.qdrant_store import (
        application_collection,
        bluegreen_collection_status,
        bluegreen_patent_alias,
        bluegreen_wiki_alias,
        collection_info,
        patent_collection,
        patent_visuals_collection,
        shared_patents_collection,
        wiki_collection,
    )

    patent_alias = bluegreen_patent_alias()
    wiki_alias = bluegreen_wiki_alias()
    collections = {
        "shared_patents": shared_patents_collection(),
        "patent_global": patent_collection(None),
        "patent_live": patent_alias,
        "patent_visuals": patent_visuals_collection(),
        "wiki_global": wiki_collection(None),
        "wiki_live": wiki_alias,
        "application": application_collection(),
    }
    info = {label: collection_info(name) for label, name in collections.items()}
    return {
        "collections": collections,
        "info": info,
        "bluegreen": {
            "patent": bluegreen_collection_status(patent_alias, f"{patent_alias}_green", f"{patent_alias}_blue"),
            "wiki": bluegreen_collection_status(wiki_alias, f"{wiki_alias}_green", f"{wiki_alias}_blue"),
        },
    }


def _api_checks() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        from fastapi.testclient import TestClient
        from chatbot.app.main import app
    except Exception as exc:  # noqa: BLE001
        return [], {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    client = TestClient(app)
    checks: list[tuple[str, str]] = [
        ("root", "/"),
        ("config", "/api/v1/chatbot/config"),
        ("qdrant_status", "/api/v1/chatbot/qdrant/status"),
        ("minio_status", "/api/v1/chatbot/minio/status"),
        ("patents", "/api/v1/chatbot/patents"),
        ("vectorstore_status", "/api/v1/chatbot/vectorstore/status"),
        ("visual_status", "/api/v1/chatbot/visual-vectorstore/status"),
        ("pre_eval_vectorstores", "/api/v1/pre-eval/vectorstore/status"),
    ]
    rows = []
    for name, path in checks:
        started = time.perf_counter()
        try:
            response = client.get(path)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            rows.append(
                {
                    "name": name,
                    "path": path,
                    "ok": 200 <= response.status_code < 400,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                    "top_level_keys": sorted(body.keys())[:30] if isinstance(body, dict) else [],
                    "count": body.get("count") if isinstance(body, dict) else None,
                    "error": None if 200 <= response.status_code < 400 else str(body)[:500],
                }
            )
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "name": name,
                    "path": path,
                    "ok": False,
                    "status_code": None,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return rows, {"ok": True, "error": None}


def _build_search_cases(sample_patents: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = [
        {
            "name": "global_core_search",
            "patent_id": None,
            "query": "반도체 소재 후보물질 물성예측 관련 특허의 핵심 차별점",
            "top_k": 6,
        },
        {
            "name": "global_report_decision",
            "patent_id": None,
            "query": "유지 판단과 시장성 평가 근거가 있는 특허를 찾아줘",
            "top_k": 6,
        },
    ]
    for index, item in enumerate(sample_patents[: max(1, limit)]):
        pid = str(item.get("patent_id"))
        title = str(item.get("title") or pid)
        cases.extend(
            [
                {
                    "name": f"patent_original_natural_{index + 1}",
                    "patent_id": pid,
                    "query": f"{title} 기술분야와 해결과제를 원문 기준으로 정리",
                    "top_k": 6,
                },
                {
                    "name": f"patent_report_natural_{index + 1}",
                    "patent_id": pid,
                    "query": f"{title} 평가 보고서의 권리성 시장성 사업성 근거",
                    "top_k": 6,
                },
                {
                    "name": f"patent_original_id_anchor_{index + 1}",
                    "patent_id": pid,
                    "query": f"{pid} {title} 기술분야 해결과제",
                    "top_k": 6,
                },
                {
                    "name": f"patent_report_id_anchor_{index + 1}",
                    "patent_id": pid,
                    "query": f"{pid} {title} 평가 보고서 권리성 시장성 사업성",
                    "top_k": 6,
                },
            ]
        )
    return cases[:limit]


def _run_search_benchmarks(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from chatbot.app.store import search_chunks

    rows = []
    for case in cases:
        timed = _timed(
            case["name"],
            search_chunks,
            case["query"],
            patent_id=case.get("patent_id"),
            source_types=None,
            top_k=int(case.get("top_k") or 6),
        )
        result = timed.get("result") or {}
        hits = result.get("hits") if isinstance(result, dict) else []
        scores = [
            float(hit.get("score"))
            for hit in hits or []
            if isinstance(hit, dict) and isinstance(hit.get("score"), (int, float))
        ]
        rows.append(
            {
                "name": case["name"],
                "query": case["query"],
                "patent_id": case.get("patent_id"),
                "ok": bool(timed.get("ok")),
                "elapsed_ms": timed.get("elapsed_ms"),
                "error": timed.get("error"),
                "mode": result.get("mode") if isinstance(result, dict) else None,
                "collection": result.get("collection") if isinstance(result, dict) else None,
                "hit_count": result.get("hit_count") if isinstance(result, dict) else 0,
                "embedding_provider": result.get("embedding_provider") if isinstance(result, dict) else None,
                "embedding_error": result.get("embedding_error") if isinstance(result, dict) else None,
                "score_avg": round(statistics.mean(scores), 4) if scores else None,
                "hits": [_compact_hit(hit) for hit in (hits or [])[:5] if isinstance(hit, dict)],
            }
        )
    return rows


def _build_chat_cases(sample_patents: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    if sample_patents:
        first = sample_patents[0]
        first_pid = str(first.get("patent_id"))
        first_title = str(first.get("title") or first_pid)
        cases.append(
            {
                "name": "selected_patent_natural_deep_dive",
                "patent_id": first_pid,
                "question": f"{first_title} 특허를 사업부 관점에서 자세하게 평가해줘",
            }
        )
    if len(sample_patents) > 1:
        second = sample_patents[1]
        second_pid = str(second.get("patent_id"))
        second_title = str(second.get("title") or second_pid)
        cases.append(
            {
                "name": "selected_patent_id_anchor_decision_table",
                "patent_id": second_pid,
                "question": f"{second_pid} {second_title} 평가 보고서 기준 유지 매각 제각 판단을 표로 정리해줘",
            }
        )
    cases.append(
        {
            "name": "global_portfolio_summary",
            "patent_id": None,
            "question": "전체 특허 DB 기준으로 사업화 리스크가 큰 유형을 근거와 함께 설명해줘",
        }
    )
    return cases[:limit]


def _run_chat_benchmarks(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from chatbot.app.agents.graph import run_chat_agent

    rows = []
    for case in cases:
        timed = _timed(
            case["name"],
            run_chat_agent,
            case["question"],
            patent_id=case.get("patent_id"),
            top_k=6,
        )
        result = timed.get("result") or {}
        metrics = result.get("metrics") if isinstance(result, dict) and isinstance(result.get("metrics"), dict) else {}
        quality = metrics.get("answer_quality") if isinstance(metrics.get("answer_quality"), dict) else {}
        source_cards = result.get("source_cards") if isinstance(result, dict) else []
        rows.append(
            {
                "name": case["name"],
                "question": case["question"],
                "patent_id": case.get("patent_id"),
                "ok": bool(timed.get("ok")) and bool(result),
                "elapsed_ms": timed.get("elapsed_ms"),
                "error": timed.get("error"),
                "answer_length": len(str(result.get("answer") or "")) if isinstance(result, dict) else 0,
                "answer_preview": str(result.get("answer") or "")[:1200] if isinstance(result, dict) else "",
                "source_count": len(source_cards or []),
                "hit_count": metrics.get("hit_count"),
                "llm_used": metrics.get("llm_used"),
                "llm_model": metrics.get("llm_model"),
                "llm_error": metrics.get("llm_error"),
                "answer_depth": metrics.get("answer_depth"),
                "intent": (metrics.get("intent_agent") or {}).get("intent") if isinstance(metrics.get("intent_agent"), dict) else None,
                "quality": {
                    key: quality.get(key)
                    for key in (
                        "composite_score",
                        "composite_v2",
                        "grade",
                        "grade_v2",
                        "retrieval_mean_score",
                        "faithfulness",
                        "answer_relevance",
                        "context_precision",
                        "context_recall_approx",
                        "semantic_answer_evidence_score",
                        "keyword_evidence_coverage",
                    )
                },
                "source_cards": [
                    _compact_source_card(card)
                    for card in (source_cards or [])[:5]
                    if isinstance(card, dict)
                ],
            }
        )
    return rows


def _run_visual_probe(sample_patent_id: str | None) -> dict[str, Any]:
    from chatbot.app.visual_data import patent_visual_index_status, search_patent_visuals

    status = _timed("visual_status", patent_visual_index_status)
    search = _timed(
        "visual_search",
        search_patent_visuals,
        "도면 흐름 구성 표 이미지",
        patent_id=sample_patent_id,
        top_k=3,
    )
    result = search.get("result") if isinstance(search.get("result"), dict) else {}
    return {
        "status": status,
        "search": {
            **{k: v for k, v in search.items() if k != "result"},
            "mode": result.get("mode") if isinstance(result, dict) else None,
            "collection": result.get("collection") if isinstance(result, dict) else None,
            "hit_count": result.get("hit_count") if isinstance(result, dict) else 0,
            "text_hit_count": result.get("text_hit_count") if isinstance(result, dict) else None,
            "image_hit_count": result.get("image_hit_count") if isinstance(result, dict) else None,
            "clip_provider": result.get("clip_provider") if isinstance(result, dict) else None,
            "embedding_provider": result.get("embedding_provider") if isinstance(result, dict) else None,
            "hits": [_compact_hit(hit) for hit in (result.get("hits") or [])[:3]] if isinstance(result, dict) else [],
        },
    }


def _run_pre_eval_probe() -> dict[str, Any]:
    from chatbot.app.pre_eval_data import (
        list_pre_application_vectorstores,
        list_pre_eval_cases,
        search_pre_eval_vectorstore,
    )

    cases_timed = _timed("pre_eval_cases", list_pre_eval_cases)
    pre_app_timed = _timed("pre_application_vectorstores", list_pre_application_vectorstores)
    cases = cases_timed.get("result") if isinstance(cases_timed.get("result"), list) else []
    search_result = None
    if cases:
        case_id = str(cases[0].get("case_id") or "")
        search_result = _timed(
            "pre_eval_search",
            search_pre_eval_vectorstore,
            case_id,
            "종합 점수 개선 권고사항",
            top_k=5,
        )
        result = search_result.get("result") if isinstance(search_result.get("result"), dict) else {}
        search_result = {
            **{k: v for k, v in search_result.items() if k != "result"},
            "case_id": case_id,
            "collection": result.get("collection") if isinstance(result, dict) else None,
            "hit_count": result.get("hit_count") if isinstance(result, dict) else 0,
            "embedding_provider": result.get("embedding_provider") if isinstance(result, dict) else None,
            "hits": [_compact_hit(hit) for hit in (result.get("hits") or [])[:5]] if isinstance(result, dict) else [],
        }
    return {
        "legacy_cases": cases_timed,
        "pre_application_vectorstores": pre_app_timed,
        "search": search_result,
    }


def _score_area(evaluation: dict[str, Any]) -> dict[str, Any]:
    infra = evaluation["infrastructure"]
    qdrant_ok = bool((infra["qdrant"].get("result") or {}).get("connected"))
    minio_ok = bool((infra["minio"].get("result") or {}).get("connected"))
    data = evaluation["data_coverage"]
    ratios = data.get("coverage_ratios") or {}
    collections = evaluation["qdrant_collections"]["info"]
    patent_bg = evaluation["qdrant_collections"]["bluegreen"]["patent"]
    wiki_bg = evaluation["qdrant_collections"]["bluegreen"]["wiki"]
    patent_live_docs = 0
    if patent_bg.get("active_color") == "green":
        patent_live_docs = int((patent_bg.get("green") or {}).get("document_count") or 0)
    elif patent_bg.get("active_color") == "blue":
        patent_live_docs = int((patent_bg.get("blue") or {}).get("document_count") or 0)
    wiki_live_docs = 0
    if wiki_bg.get("active_color") == "green":
        wiki_live_docs = int((wiki_bg.get("green") or {}).get("document_count") or 0)
    elif wiki_bg.get("active_color") == "blue":
        wiki_live_docs = int((wiki_bg.get("blue") or {}).get("document_count") or 0)
    collection_values = [
        collections.get("shared_patents", {}).get("exists") and (collections.get("shared_patents", {}).get("points_count") or 0) > 0,
        collections.get("patent_visuals", {}).get("exists") and (collections.get("patent_visuals", {}).get("points_count") or 0) > 0,
        collections.get("application", {}).get("exists") and (collections.get("application", {}).get("points_count") or 0) > 0,
        patent_live_docs > 0,
        wiki_live_docs > 0,
    ]
    searches = evaluation["retrieval_benchmarks"]
    search_success = sum(1 for row in searches if row.get("ok") and int(row.get("hit_count") or 0) > 0)
    chats = evaluation["chat_benchmarks"]
    chat_success = sum(1 for row in chats if row.get("ok") and int(row.get("source_count") or 0) > 0)
    quality_scores = [
        float(row.get("quality", {}).get("composite_v2"))
        for row in chats
        if isinstance(row.get("quality"), dict) and isinstance(row.get("quality", {}).get("composite_v2"), (int, float))
    ]
    visual_status = evaluation["visual_probe"]["status"].get("result") or {}
    visual_search = evaluation["visual_probe"]["search"] or {}
    visual_qdrant_docs = int((visual_status.get("qdrant") or {}).get("points_count") or 0)
    visual_candidates = int(visual_status.get("candidate_count") or 0)
    visual_indexed = int(visual_status.get("indexed_manifest_count") or 0)
    visual_coverage = (visual_indexed / visual_candidates) if visual_candidates else 0.0
    visual_search_ok = int(visual_search.get("hit_count") or 0) > 0
    pre_eval = evaluation["pre_eval_probe"]["legacy_cases"].get("result") or []
    pre_app = evaluation["pre_eval_probe"]["pre_application_vectorstores"].get("result") or []

    scores = {
        "infrastructure": 1.0 if qdrant_ok and minio_ok else 0.5 if qdrant_ok or minio_ok else 0.0,
        "data": round((float(ratios.get("input") or 0) + float(ratios.get("report") or 0) + float(ratios.get("pdf") or 0)) / 3, 4),
        "vectorstore": round(sum(1 for value in collection_values if value) / len(collection_values), 4),
        "retrieval": round(search_success / len(searches), 4) if searches else 0.0,
        "chat": round((chat_success / len(chats)) * (statistics.mean(quality_scores) if quality_scores else 0.5), 4) if chats else None,
        "visual": round(
            (0.50 if visual_qdrant_docs > 0 else 0.0)
            + (0.30 * min(visual_coverage, 1.0))
            + (0.20 if visual_search_ok else 0.0),
            4,
        ),
        "pre_eval": round((0.70 if pre_eval else 0.0) + (0.30 if pre_app else 0.0), 4),
    }
    weighted_items = [(scores["infrastructure"], 0.18), (scores["data"], 0.16), (scores["vectorstore"], 0.20), (scores["retrieval"], 0.20), (scores["visual"], 0.10), (scores["pre_eval"], 0.06)]
    if scores["chat"] is not None:
        weighted_items.append((scores["chat"], 0.10))
    total_weight = sum(weight for _, weight in weighted_items)
    overall = round(sum(score * weight for score, weight in weighted_items) / total_weight, 4) if total_weight else 0
    return {"area_scores": scores, "overall_score": overall}


def _status_label(score: float | None) -> str:
    if score is None:
        return "not_run"
    if score >= 0.85:
        return "good"
    if score >= 0.65:
        return "watch"
    if score > 0:
        return "risk"
    return "blocked"


def _write_markdown(evaluation: dict[str, Any], path: Path) -> None:
    score = evaluation["score"]
    infra = evaluation["infrastructure"]
    minio = infra["minio"].get("result") or {}
    qdrant = infra["qdrant"].get("result") or {}
    data = evaluation["data_coverage"]
    api_summary = evaluation["api_latency_summary"]
    search_summary = evaluation["retrieval_latency_summary"]
    chat_summary = evaluation["chat_latency_summary"]
    area_scores = score["area_scores"]
    collections = evaluation["qdrant_collections"]
    visual_status = evaluation["visual_probe"]["status"].get("result") or {}
    pre_eval_cases = evaluation["pre_eval_probe"]["legacy_cases"].get("result") or []
    pre_app = evaluation["pre_eval_probe"]["pre_application_vectorstores"].get("result") or []

    lines = [
        "# Chatbot Performance Evaluation",
        "",
        f"- Run ID: `{evaluation['run_id']}`",
        f"- Evaluated at: `{evaluation['evaluated_at']}`",
        f"- Output JSON: `{evaluation['json_path']}`",
        f"- Python: `{evaluation['environment']['python']}` / Platform: `{evaluation['environment']['platform']}`",
        "",
        "## Executive scorecard",
        "",
        "| Area | Score | Status | Notes |",
        "| --- | ---: | --- | --- |",
    ]
    notes = {
        "infrastructure": f"Qdrant connected={qdrant.get('connected')}, MinIO connected={minio.get('connected')}",
        "data": f"{data.get('patent_count')} patents; parsed/report/pdf ratios {data.get('coverage_ratios')}",
        "vectorstore": "Shared, live, wiki, visual, application collection coverage",
        "retrieval": f"{sum(1 for r in evaluation['retrieval_benchmarks'] if r.get('ok') and int(r.get('hit_count') or 0) > 0)}/{len(evaluation['retrieval_benchmarks'])} searches returned hits",
        "chat": f"{len(evaluation['chat_benchmarks'])} sampled end-to-end chat calls",
        "visual": f"visual collection docs={(visual_status.get('qdrant') or {}).get('points_count')}",
        "pre_eval": f"legacy cases={len(pre_eval_cases)}, pre-application vectorstores={len(pre_app)}",
    }
    for area, value in area_scores.items():
        shown = "-" if value is None else f"{value:.4f}"
        lines.append(f"| {area} | {shown} | {_status_label(value)} | {notes.get(area, '')} |")
    lines.extend(
        [
            f"| **overall** | **{score['overall_score']:.4f}** | **{_status_label(score['overall_score'])}** | weighted composite |",
            "",
            "## Infrastructure",
            "",
            f"- Qdrant: connected `{qdrant.get('connected')}`, collections `{qdrant.get('collection_count')}`, URL `{qdrant.get('url')}`",
            f"- MinIO: connected `{minio.get('connected')}`, remote objects `{minio.get('remote_object_count')}`, remote size `{minio.get('remote_size_bytes')}`, local patents `{minio.get('local_patent_count')}`, backend `{minio.get('backend')}`",
            f"- MinIO note: `{minio.get('boto3_error') or 'boto3 available or not needed'}`",
            "",
            "## Data Coverage",
            "",
            f"- Patent count: `{data.get('patent_count')}`",
            f"- Input/report/pdf counts: `{data.get('has_input_count')}` / `{data.get('has_report_count')}` / `{data.get('has_pdf_count')}`",
            f"- Chunk total/avg/max: `{data.get('chunk_count_total')}` / `{data.get('chunk_count_avg')}` / `{data.get('chunk_count_max')}`",
            f"- Report statuses: `{data.get('report_status_counts')}`; invalid validation count `{data.get('invalid_validation_count')}`",
            "",
            "## Qdrant Collections",
            "",
            "| Label | Collection | Exists | Points | Status |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for label, info in collections["info"].items():
        lines.append(
            f"| {label} | `{info.get('collection')}` | {info.get('exists')} | {info.get('points_count')} | {info.get('status') or info.get('error', '')} |"
        )
    lines.extend(
        [
            "",
            f"- Patent blue-green active: `{collections['bluegreen']['patent'].get('active_collection')}` / color `{collections['bluegreen']['patent'].get('active_color')}`",
            f"- Wiki blue-green active: `{collections['bluegreen']['wiki'].get('active_collection')}` / color `{collections['bluegreen']['wiki'].get('active_color')}`",
            "",
            "## API Latency",
            "",
            f"- Summary: `{api_summary}`",
            "",
            "| Endpoint | Status | Latency ms | Error |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for row in evaluation["api_checks"]:
        lines.append(f"| `{row.get('path')}` | {row.get('status_code')} | {row.get('elapsed_ms')} | {row.get('error') or ''} |")
    lines.extend(
        [
            "",
            "## Retrieval Benchmarks",
            "",
            f"- Summary: `{search_summary}`",
            "",
            "| Case | Patent | Hits | Mode | Latency ms | Score avg |",
            "| --- | --- | ---: | --- | ---: | ---: |",
        ]
    )
    for row in evaluation["retrieval_benchmarks"]:
        lines.append(
            f"| {row.get('name')} | `{row.get('patent_id')}` | {row.get('hit_count')} | {row.get('mode')} | {row.get('elapsed_ms')} | {row.get('score_avg')} |"
        )
    lines.extend(
        [
            "",
            "## Chat Benchmarks",
            "",
            f"- Summary: `{chat_summary}`",
            "",
            "| Case | Patent | Sources | LLM | Composite v2 | Faithfulness | Latency ms |",
            "| --- | --- | ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for row in evaluation["chat_benchmarks"]:
        quality = row.get("quality") or {}
        lines.append(
            f"| {row.get('name')} | `{row.get('patent_id')}` | {row.get('source_count')} | {row.get('llm_used')} | {quality.get('composite_v2')} | {quality.get('faithfulness')} | {row.get('elapsed_ms')} |"
        )
    lines.extend(
        [
            "",
            "## Visual And Pre-Eval",
            "",
            f"- Visual status: candidates `{visual_status.get('candidate_count')}`, indexed manifests `{visual_status.get('indexed_manifest_count')}`, pending `{visual_status.get('pending_reindex_count')}`, qdrant docs `{(visual_status.get('qdrant') or {}).get('points_count')}`",
            f"- Visual search: `{evaluation['visual_probe']['search']}`",
            f"- Pre-eval legacy case count: `{len(pre_eval_cases)}`",
            f"- Pre-application vectorstore count: `{len(pre_app)}`",
            "",
            "## Main Findings",
            "",
        ]
    )
    findings = []
    if minio.get("connected") and qdrant.get("connected"):
        findings.append("MinIO and Qdrant are both connected through the active local port-forward sessions.")
    if minio.get("remote_object_count") is not None and data.get("patent_count"):
        findings.append(
            f"MinIO `patent/` currently exposes {minio.get('remote_object_count')} objects, while the local cache exposes {data.get('patent_count')} patents; treat MinIO as a subset or verify prefix/sync scope before relying on it as the only source of truth."
        )
    if minio.get("boto3_error"):
        findings.append("Local chatbot venv is missing boto3, so MinIO status used AWS CLI fallback. Production image requirements include boto3, but local reproducibility should be tightened.")
    if data.get("invalid_validation_count"):
        findings.append(f"{data.get('invalid_validation_count')} report.json files have validation.valid=false; this lowers answer quality because report chunks can contain partial_success/error metadata.")
    if collections["bluegreen"]["patent"].get("active_color") == "none":
        findings.append("Patent live blue-green alias is not active; searches fall back to shared/global collections.")
    else:
        patent_bg = collections["bluegreen"]["patent"]
        active_color = patent_bg.get("active_color")
        active_slot = patent_bg.get(active_color) if isinstance(active_color, str) else None
        if isinstance(active_slot, dict) and int(active_slot.get("document_count") or 0) == 0:
            findings.append("Patent live blue-green alias is active but its active slot has 0 documents; current search succeeds by falling back to the shared patent collection.")
    if (visual_status.get("qdrant") or {}).get("points_count") and visual_status.get("pending_reindex_count"):
        findings.append("Visual collection has data, but some patent visual manifests are pending or errored; visual RAG coverage is partial.")
    if not evaluation["chat_benchmarks"]:
        findings.append("End-to-end chat generation was skipped by option, so chat latency/quality score is not included.")
    for item in findings:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- BERTScore was skipped to avoid model download/runtime noise; lexical/semantic lightweight metrics were still computed.",
            "- This is a sampled performance evaluation, not a high-concurrency load test.",
            "- The script does not mutate MinIO, Qdrant, or local patent data.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    _prepare_env()
    _patch_optional_quality_costs()

    from chatbot.app.minio_data import minio_patent_status
    from chatbot.app.qdrant_store import qdrant_status
    from chatbot.app.store import list_patents
    from chatbot.app.vectorstore import vectorstore_status

    output_dir = args.output_dir or (ARTIFACT_ROOT / _now_id())
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = output_dir.name
    patents_timed = _timed("list_patents", list_patents)
    patents = patents_timed.get("result") if isinstance(patents_timed.get("result"), list) else []
    sample_patents = _select_sample_patents(patents, max(args.search_limit, args.chat_limit, 3))
    sample_patent_id = str(sample_patents[0].get("patent_id")) if sample_patents else None

    infrastructure = {
        "qdrant": _timed("qdrant_status", qdrant_status),
        "minio": _timed("minio_patent_status", minio_patent_status),
    }
    api_checks, api_meta = _api_checks()
    search_cases = _build_search_cases(sample_patents, args.search_limit)
    retrieval_benchmarks = _run_search_benchmarks(search_cases)
    chat_benchmarks = [] if args.skip_chat else _run_chat_benchmarks(_build_chat_cases(sample_patents, args.chat_limit))

    evaluation: dict[str, Any] = {
        "run_id": run_id,
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        "environment": {
            "python": sys.version.split()[0],
            "executable": sys.executable,
            "platform": platform.platform(),
            "project_root": str(PROJECT_ROOT),
            "qdrant_url": os.getenv("QDRANT_URL"),
            "minio_endpoint": os.getenv("MINIO_ENDPOINT"),
            "minio_bucket": os.getenv("MINIO_BUCKET"),
            "openai_answer_model": os.getenv("OPENAI_ANSWER_MODEL"),
            "openai_intent_model": os.getenv("OPENAI_INTENT_MODEL"),
            "openai_embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL"),
        },
        "inputs": {
            "search_limit": args.search_limit,
            "chat_limit": args.chat_limit,
            "skip_chat": args.skip_chat,
            "sample_patents": [
                {"patent_id": item.get("patent_id"), "title": item.get("title")}
                for item in sample_patents[:10]
            ],
        },
        "infrastructure": infrastructure,
        "patents_load": patents_timed,
        "data_coverage": _data_coverage(patents),
        "qdrant_collections": _collection_snapshot(),
        "vectorstore_status": _redact(vectorstore_status()),
        "api_checks": api_checks,
        "api_meta": api_meta,
        "api_latency_summary": _latency_summary(api_checks),
        "retrieval_benchmarks": retrieval_benchmarks,
        "retrieval_latency_summary": _latency_summary(retrieval_benchmarks),
        "chat_benchmarks": chat_benchmarks,
        "chat_latency_summary": _latency_summary(chat_benchmarks),
        "visual_probe": _run_visual_probe(sample_patent_id),
        "pre_eval_probe": _run_pre_eval_probe(),
    }
    json_path = output_dir / "performance_evaluation.json"
    md_path = output_dir / "performance_evaluation.md"
    evaluation["json_path"] = str(json_path)
    evaluation["markdown_path"] = str(md_path)
    evaluation["score"] = _score_area(evaluation)

    json_path.write_text(json.dumps(_redact(evaluation), ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    _write_markdown(evaluation, md_path)
    return evaluation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate chatbot performance across MinIO, Qdrant, RAG, chat, visual, and pre-eval.")
    parser.add_argument("--search-limit", type=int, default=8, help="Number of retrieval benchmark cases to run.")
    parser.add_argument("--chat-limit", type=int, default=3, help="Number of end-to-end chat cases to run.")
    parser.add_argument("--skip-chat", action="store_true", help="Skip end-to-end LLM chat generation.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Custom output directory.")
    return parser.parse_args()


def main() -> None:
    evaluation = run(parse_args())
    score = evaluation["score"]
    print(json.dumps({
        "run_id": evaluation["run_id"],
        "overall_score": score["overall_score"],
        "area_scores": score["area_scores"],
        "json_path": evaluation["json_path"],
        "markdown_path": evaluation["markdown_path"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
