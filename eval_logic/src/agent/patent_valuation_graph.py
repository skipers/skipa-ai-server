"""특허 가치평가 보고서 생성용 agentic workflow입니다.

이 모듈은 기존 서비스 파이프라인을 LangGraph 스타일의 상태 기반 노드로
감싼 오케스트레이션 레이어입니다. ``langgraph``가 설치된 환경에서는
StateGraph로 실행하고, 설치되지 않은 환경에서는 같은 노드를 순차 실행하는
fallback runner를 사용합니다.

구조:
- supervisor: 전체 상태를 점검하고 다음 실행 노드를 결정
- worker nodes: evidence, validation, valuation, similar patents, report
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from agent.report_builder import build_structured_report
from core.paths import (
    KIPRIS_CACHE_DIR,
    KIPRIS_CRAWLING_DIR,
    KIPRIS_OUTPUT_DIR,
    LEGACY_SRC_DIR,
    RUNTIME_ANALYSIS_DIR,
)
from core.schemas import PatentEvaluationInput, normalize_patent_input
from services.evidence_collection_service import EvidenceCollectionOptions, EvidenceCollectionService
from services.report_verification_service import ReportVerificationService
from services.valuation_service import PatentValuationOptions, PatentValuationService


class PatentValuationState(TypedDict, total=False):
    """워크플로우 노드들이 공유하는 상태입니다."""

    patent_data: dict[str, Any]
    options: dict[str, Any]
    validation: dict[str, Any]
    evidence: dict[str, Any]
    valuation: dict[str, Any]
    similar_analysis: dict[str, Any] | None
    report: dict[str, Any]
    report_verification: dict[str, Any]
    human_reviews: list[dict[str, Any]]
    human_review_abort: bool
    human_review_pending: dict[str, Any]
    supervisor_reviews_done: list[str]
    next_node: str
    node_trace: list[dict[str, Any]]
    errors: list[str]
    started_at: float
    completed_at: float


@dataclass(slots=True)
class PatentValuationWorkflowOptions:
    """agentic workflow 실행 옵션입니다."""

    enable_market: bool = True
    enable_auto: bool = True
    enable_llm: bool = False
    enable_pdf_metadata_extraction: bool = False
    enable_business_rag: bool = False
    enable_similar_analysis: bool = True
    similar_use_kipris_crawler: bool = True
    similar_force_refresh: bool = True
    similar_max_pages: int = 5
    similar_max_results: int = 10
    similar_date_from: str = "2015-01-01"
    similar_date_to: str = ""
    similar_use_llm: bool = False
    rag_top_k: int | None = None
    fail_on_validation_error: bool = True
    enable_human_review: bool = False
    human_review_low_score_threshold: float = 2.8

    def __post_init__(self) -> None:
        self.enable_pdf_metadata_extraction = False
        self.enable_similar_analysis = True
        self.similar_use_kipris_crawler = True
        self.similar_force_refresh = True

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PatentValuationWorkflowOptions":
        raw = data or {}
        return cls(
            enable_market=bool(raw.get("enable_market", True)),
            enable_auto=bool(raw.get("enable_auto", True)),
            enable_llm=bool(raw.get("enable_llm", False)),
            enable_pdf_metadata_extraction=False,
            enable_business_rag=bool(raw.get("enable_business_rag", False)),
            enable_similar_analysis=True,
            similar_use_kipris_crawler=True,
            similar_force_refresh=True,
            similar_max_pages=int(raw.get("similar_max_pages", 5)),
            similar_max_results=int(raw.get("similar_max_results", 10)),
            similar_date_from=str(raw.get("similar_date_from", "2015-01-01") or ""),
            similar_date_to=str(raw.get("similar_date_to", "") or ""),
            similar_use_llm=bool(raw.get("similar_use_llm", False)),
            rag_top_k=raw.get("rag_top_k"),
            fail_on_validation_error=bool(raw.get("fail_on_validation_error", True)),
            enable_human_review=bool(raw.get("enable_human_review", False)),
            human_review_low_score_threshold=float(raw.get("human_review_low_score_threshold", 2.8)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enable_market": self.enable_market,
            "enable_auto": self.enable_auto,
            "enable_llm": self.enable_llm,
            "enable_pdf_metadata_extraction": self.enable_pdf_metadata_extraction,
            "enable_business_rag": self.enable_business_rag,
            "enable_similar_analysis": self.enable_similar_analysis,
            "similar_use_kipris_crawler": self.similar_use_kipris_crawler,
            "similar_force_refresh": self.similar_force_refresh,
            "similar_max_pages": self.similar_max_pages,
            "similar_max_results": self.similar_max_results,
            "similar_date_from": self.similar_date_from,
            "similar_date_to": self.similar_date_to,
            "similar_use_llm": self.similar_use_llm,
            "rag_top_k": self.rag_top_k,
            "fail_on_validation_error": self.fail_on_validation_error,
            "enable_human_review": self.enable_human_review,
            "human_review_low_score_threshold": self.human_review_low_score_threshold,
        }


def _normalize_id_for_path(patent_id: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", str(patent_id or "")).strip("_")


def _append_trace(state: PatentValuationState, node: str, status: str, start: float, message: str = "") -> None:
    trace = state.setdefault("node_trace", [])
    trace.append(
        {
            "node": node,
            "status": status,
            "elapsed_seconds": round(time.time() - start, 2),
            "message": message,
        }
    )


def _append_error(state: PatentValuationState, message: str) -> None:
    state.setdefault("errors", []).append(message)


def _append_human_review(state: PatentValuationState, review: dict[str, Any]) -> None:
    state.setdefault("human_reviews", []).append(review)


def _score_average(scores: list[dict[str, Any]]) -> float:
    values = [float(item["score"]) for item in scores if isinstance(item.get("score"), (int, float))]
    return round(sum(values) / len(values), 2) if values else 0.0


def _dimension_balanced_average(scores: list[dict[str, Any]]) -> float:
    """항목 수가 많은 차원이 종합 점수를 과도하게 좌우하지 않도록 차원 평균을 균등 반영합니다."""
    by_dimension: dict[str, list[float]] = {}
    for item in scores:
        if isinstance(item.get("score"), (int, float)):
            by_dimension.setdefault(str(item.get("dim") or "unknown"), []).append(float(item["score"]))
    averages = [sum(values) / len(values) for values in by_dimension.values() if values]
    return round(sum(averages) / len(averages), 2) if averages else 0.0


def _strip_legacy_decision_fields(value: Any) -> Any:
    """과거 유사특허 캐시에 남은 유지/포기 권고 필드를 응답에서 제거합니다."""
    legacy_keys = {
        "decision_comment",
        "decision_comment_method",
        "maintenance_signal",
        "maintenance_implication",
    }
    if isinstance(value, dict):
        return {
            key: _strip_legacy_decision_fields(item)
            for key, item in value.items()
            if key not in legacy_keys
        }
    if isinstance(value, list):
        return [_strip_legacy_decision_fields(item) for item in value]
    return value


def _title_for_kipris_search(patent_data: dict[str, Any]) -> str:
    meta = patent_data.get("meta") if isinstance(patent_data.get("meta"), dict) else {}
    return str(
        patent_data.get("title")
        or meta.get("title")
        or patent_data.get("description_summary")
        or patent_data.get("patent_id")
        or ""
    ).strip()


def _write_runtime_patent_input(patent_data: dict[str, Any], norm_id: str) -> Path:
    RUNTIME_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = RUNTIME_ANALYSIS_DIR / f"patent_{norm_id}_input.json"
    with target_path.open("w", encoding="utf-8") as file:
        json.dump(patent_data, file, ensure_ascii=False, indent=2)
    return target_path


def _ensure_legacy_crawling_imports() -> None:
    legacy_path = str(LEGACY_SRC_DIR)
    if legacy_path not in sys.path:
        sys.path.append(legacy_path)


def _valid_kipris_analysis(path: Path, norm_id: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as file:
            analysis = json.load(file)
    except Exception:
        return None
    meta = analysis.get("meta") if isinstance(analysis, dict) else {}
    if not isinstance(meta, dict):
        return None
    analyzed_id = _normalize_id_for_path(str(meta.get("target_patent_id") or ""))
    source_search = meta.get("source_search") if isinstance(meta.get("source_search"), dict) else {}
    if analyzed_id != norm_id or source_search.get("method") != "legacy_kipris_crawler":
        return None
    if not analysis.get("similar_patents"):
        return None
    return analysis


def _load_last_valid_kipris_analysis(norm_id: str, warning: str) -> dict[str, Any] | None:
    for path in [
        RUNTIME_ANALYSIS_DIR / f"similar_analysis_{norm_id}.json",
        RUNTIME_ANALYSIS_DIR / f"similar_analysis_{norm_id.replace('_', '-')}.json",
        KIPRIS_OUTPUT_DIR / f"similar_analysis_{norm_id}.json",
        KIPRIS_OUTPUT_DIR / f"similar_analysis_{norm_id.replace('_', '-')}.json",
    ]:
        analysis = _valid_kipris_analysis(path, norm_id)
        if analysis:
            meta = analysis.setdefault("meta", {})
            meta["source_search_warning"] = warning
            meta["source_search_reused_after_failure"] = True
            return analysis
    return None


def _collect_kipris_similar_details(
    patent_data: dict[str, Any],
    norm_id: str,
    *,
    max_pages: int,
    max_results: int,
    date_from: str,
    date_to: str,
) -> tuple[Path, Path]:
    _ensure_legacy_crawling_imports()

    from crawling.kipris import search_similar_patents
    from crawling.similar_patent_collector import collect_similar_patent_details

    keyword = _title_for_kipris_search(patent_data)
    if not keyword:
        raise ValueError("KIPRIS 유사 특허 검색어를 만들 수 없습니다.")

    target_path = _write_runtime_patent_input(patent_data, norm_id)
    refs_path = KIPRIS_OUTPUT_DIR / f"similar_refs_{norm_id}.json"
    details_path = KIPRIS_OUTPUT_DIR / f"similar_details_{norm_id}.json"
    csv_path = KIPRIS_CRAWLING_DIR / f"kipris_results_{norm_id}.csv"
    cache_dir = KIPRIS_CACHE_DIR / "kipris" / norm_id
    for directory in {KIPRIS_OUTPUT_DIR, KIPRIS_CRAWLING_DIR, cache_dir, RUNTIME_ANALYSIS_DIR}:
        directory.mkdir(parents=True, exist_ok=True)

    records = search_similar_patents(
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        max_pages=max_pages,
        headless=True,
        output_csv=str(csv_path),
        output_json=str(refs_path),
        max_results=max_results,
        target_json=str(target_path),
    )
    if not records or not refs_path.exists():
        raise RuntimeError("KIPRIS 유사도 검색 결과를 수집하지 못했습니다.")

    details = collect_similar_patent_details(
        candidates_path=refs_path,
        output_path=details_path,
        cache_dir=cache_dir,
        limit=max_results,
        use_cache=True,
    )
    if not details.get("patents"):
        raise RuntimeError("KIPRIS 유사 특허 상세 데이터를 생성하지 못했습니다.")

    return target_path, details_path


def _load_or_run_similar_analysis(
    patent_data: dict[str, Any],
    *,
    use_llm: bool,
    max_pages: int,
    max_results: int,
    date_from: str,
    date_to: str,
) -> dict[str, Any] | None:
    patent_data = normalize_patent_input(patent_data)
    patent_id = patent_data.get("patent_id") or (patent_data.get("meta") or {}).get("registration_number") or ""
    norm_id = _normalize_id_for_path(patent_id)
    if not norm_id:
        raise ValueError("유사 특허 분석에는 patent_id 또는 등록번호가 필요합니다.")

    try:
        target_path, details_path = _collect_kipris_similar_details(
            patent_data,
            norm_id,
            max_pages=max_pages,
            max_results=max_results,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as exc:
        existing = _load_last_valid_kipris_analysis(norm_id, str(exc))
        if existing:
            return _strip_legacy_decision_fields(existing)
        raise

    from patent_analysis.similar_patent_analyzer import analyze_similar_patents

    out_path = RUNTIME_ANALYSIS_DIR / f"similar_analysis_{norm_id}.json"
    analysis = analyze_similar_patents(
        target_path=target_path,
        details_path=details_path,
        output_path=out_path,
        use_llm=use_llm,
    )
    meta = analysis.setdefault("meta", {})
    analyzed_id = _normalize_id_for_path(str(meta.get("target_patent_id") or ""))
    if analyzed_id != norm_id:
        raise RuntimeError(
            f"KIPRIS 유사 특허 분석 대상 불일치: expected={norm_id}, actual={analyzed_id or '-'}"
        )
    meta["source_search"] = {
        "source": "KIPRIS",
        "method": "legacy_kipris_crawler",
        "candidate_details": str(details_path),
        "target_input": str(target_path),
        "force_refresh": True,
        "max_pages": max_pages,
        "max_results": max_results,
        "date_range": {"from": date_from, "to": date_to},
    }
    with out_path.open("w", encoding="utf-8") as file:
        json.dump(analysis, file, ensure_ascii=False, indent=2)
    return _strip_legacy_decision_fields(analysis)


def _valuation_analysis_text(valuation: dict[str, Any]) -> str:
    all_scores = (valuation.get("auto_scores") or []) + (valuation.get("llm_scores") or [])
    average = _dimension_balanced_average(all_scores)
    low_items = [
        str(item.get("item"))
        for item in all_scores
        if isinstance(item.get("score"), (int, float)) and item.get("score") <= 2
    ]
    market = valuation.get("market_growth") or {}
    return (
        f"종합 평균 점수는 {average}/5입니다. "
        f"시장 섹터는 {market.get('sector') or '미분류'}이며, "
        f"2점 이하 추가 확인 항목은 {', '.join(low_items) if low_items else '없음'}입니다."
    )


class PatentValuationWorkflow:
    """특허 가치평가 보고서 agentic workflow 실행기입니다."""

    def __init__(self, options: PatentValuationWorkflowOptions | None = None) -> None:
        self.options = options or PatentValuationWorkflowOptions()
        self._checkpointer: Any | None = None

    def run(self, patent_data: dict[str, Any], thread_id: str | None = None) -> dict[str, Any]:
        state: PatentValuationState = {
            "patent_data": normalize_patent_input(patent_data),
            "options": self.options.to_dict(),
            "human_reviews": [],
            "human_review_abort": False,
            "supervisor_reviews_done": [],
            "node_trace": [],
            "errors": [],
            "started_at": time.time(),
        }
        runner = self._build_runner()
        config = self._invoke_config(thread_id)
        final_state = runner.invoke(state, config=config) if config else runner.invoke(state)
        final_state["completed_at"] = time.time()
        return self._to_response(final_state)

    def resume(self, thread_id: str, human_response: dict[str, Any]) -> dict[str, Any]:
        """중단된 HITL workflow를 사람 응답으로 재개합니다.

        ``human_response`` 예:
        {"action": "approve", "reviewer": "ip-team", "comment": "근거 확인 완료"}
        {"action": "abort", "reviewer": "ip-team", "comment": "입력 자료 보완 필요"}
        """
        try:
            from langgraph.types import Command
        except Exception as exc:
            raise RuntimeError("LangGraph가 설치된 환경에서만 resume을 사용할 수 있습니다.") from exc

        runner = self._build_runner()
        config = self._invoke_config(thread_id)
        if not config:
            raise RuntimeError("Human review resume에는 thread_id가 필요합니다.")

        final_state = runner.invoke(Command(resume=human_response), config=config)
        final_state["completed_at"] = time.time()
        return self._to_response(final_state)

    def _build_runner(self) -> Any:
        try:
            from langgraph.graph import END, StateGraph

            graph = StateGraph(PatentValuationState)
            graph.add_node("supervisor", self._supervisor)
            graph.add_node("validate_input", self._validate_input)
            graph.add_node("collect_evidence", self._collect_evidence)
            graph.add_node("run_valuation", self._run_valuation)
            graph.add_node("analyze_similar_patents", self._analyze_similar_patents)
            graph.add_node("build_report", self._build_report)
            graph.add_node("verify_report", self._verify_report)
            graph.set_entry_point("supervisor")
            graph.add_conditional_edges(
                "supervisor",
                self._route_from_supervisor,
                {
                    "collect_evidence": "collect_evidence",
                    "validate_input": "validate_input",
                    "run_valuation": "run_valuation",
                    "analyze_similar_patents": "analyze_similar_patents",
                    "build_report": "build_report",
                    "verify_report": "verify_report",
                    "end": END,
                },
            )
            graph.add_edge("collect_evidence", "supervisor")
            graph.add_edge("validate_input", "supervisor")
            graph.add_edge("run_valuation", "supervisor")
            graph.add_edge("analyze_similar_patents", "supervisor")
            graph.add_edge("build_report", "supervisor")
            graph.add_edge("verify_report", "supervisor")
            compile_kwargs = {}
            if self.options.enable_human_review:
                compile_kwargs["checkpointer"] = self._get_checkpointer()
            return graph.compile(**compile_kwargs)
        except Exception:
            return _SequentialWorkflowRunner(self)

    def _supervisor(self, state: PatentValuationState) -> PatentValuationState:
        """전체 workflow 상태를 점검하고 다음 worker node를 결정합니다."""
        start = time.time()
        next_node = self._decide_next_node(state)
        state["next_node"] = next_node
        _append_trace(state, "supervisor", "success", start, f"next={next_node}")
        return state

    def _decide_next_node(self, state: PatentValuationState) -> str:
        if state.get("human_review_abort"):
            return "end"
        if "report" in state and "report_verification" in state:
            return "end"
        if "report" in state:
            return "verify_report"
        if "evidence" not in state:
            return "collect_evidence"

        self._supervise_evidence(state)
        if state.get("human_review_abort"):
            return "end"

        if "validation" not in state:
            return "validate_input"

        self._supervise_validation(state)
        if state.get("human_review_abort"):
            return "end"
        validation = state.get("validation") or {}
        if not validation.get("valid") and self.options.fail_on_validation_error:
            return "end"

        if "valuation" not in state:
            return "run_valuation"

        self._supervise_valuation(state)
        if state.get("human_review_abort"):
            return "end"

        if self.options.enable_similar_analysis and "similar_analysis" not in state:
            return "analyze_similar_patents"

        if self.options.enable_similar_analysis:
            self._supervise_similar_patents(state)
            if state.get("human_review_abort"):
                return "end"

        return "build_report"

    def _route_from_supervisor(self, state: PatentValuationState) -> str:
        return state.get("next_node") or "end"

    def _get_checkpointer(self) -> Any:
        if self._checkpointer is None:
            from langgraph.checkpoint.memory import InMemorySaver

            self._checkpointer = InMemorySaver()
        return self._checkpointer

    def _invoke_config(self, thread_id: str | None) -> dict[str, Any] | None:
        if not self.options.enable_human_review:
            return None
        return {"configurable": {"thread_id": thread_id or f"patent-valuation-{int(time.time() * 1000)}"}}

    def _validate_input(self, state: PatentValuationState) -> PatentValuationState:
        start = time.time()
        try:
            request = PatentEvaluationInput.from_dict(state["patent_data"])
            errors = request.validate()
            state["validation"] = {
                "valid": not errors,
                "errors": errors,
                "patent_id": request.patent_id,
                "title": request.title,
                "has_claims": bool(request.claims_text),
                "has_description": bool(request.description_summary),
                "has_market_data": bool(request.market_data),
                "has_kipris_data": bool(request.kipris_data),
            }
            status = "success" if not errors else "error"
            _append_trace(state, "validate_input", status, start, "; ".join(errors))
        except Exception as exc:
            state["validation"] = {"valid": False, "errors": [str(exc)]}
            _append_error(state, str(exc))
            _append_trace(state, "validate_input", "error", start, str(exc))
        return state

    def _collect_evidence(self, state: PatentValuationState) -> PatentValuationState:
        start = time.time()
        try:
            service = EvidenceCollectionService(
                EvidenceCollectionOptions(
                    enable_pdf_metadata_extraction=self.options.enable_pdf_metadata_extraction,
                    enable_business_rag=self.options.enable_business_rag,
                    rag_top_k=self.options.rag_top_k,
                )
            )
            enriched, evidence, steps = service.collect(state["patent_data"])
            state["patent_data"] = enriched
            state["evidence"] = evidence.to_dict()
            for error in evidence.errors:
                _append_error(state, error)
            status = "error" if evidence.errors else "success"
            _append_trace(state, "collect_evidence", status, start, f"{len(steps)}개 세부 단계 실행")
        except Exception as exc:
            message = f"collect_evidence 실패: {exc}"
            state["evidence"] = {"errors": [message]}
            _append_error(state, message)
            _append_trace(state, "collect_evidence", "error", start, str(exc))
        return state

    def _run_valuation(self, state: PatentValuationState) -> PatentValuationState:
        start = time.time()
        try:
            service = PatentValuationService(
                PatentValuationOptions(
                    enable_market=self.options.enable_market,
                    enable_auto=self.options.enable_auto,
                    enable_llm=self.options.enable_llm,
                    enable_evidence_collection=False,
                    fail_on_validation_error=False,
                )
            )
            output = service.evaluate(state["patent_data"]).to_dict()
            if state.get("evidence"):
                output["evidence"] = state["evidence"]
            state["valuation"] = output
            _append_trace(state, "run_valuation", "success", start, "가치 평가 완료")
        except Exception as exc:
            message = f"run_valuation 실패: {exc}"
            state["valuation"] = {"errors": [message], "auto_scores": [], "llm_scores": []}
            _append_error(state, message)
            _append_trace(state, "run_valuation", "error", start, str(exc))
        return state

    def _analyze_similar_patents(self, state: PatentValuationState) -> PatentValuationState:
        start = time.time()
        try:
            state["similar_analysis"] = _load_or_run_similar_analysis(
                state["patent_data"],
                use_llm=self.options.similar_use_llm,
                max_pages=self.options.similar_max_pages,
                max_results=self.options.similar_max_results,
                date_from=self.options.similar_date_from,
                date_to=self.options.similar_date_to,
            )
            status = "success" if state.get("similar_analysis") else "skipped"
            _append_trace(state, "analyze_similar_patents", status, start, "유사 특허 분석 처리 완료")
        except Exception as exc:
            state["similar_analysis"] = None
            _append_error(state, f"analyze_similar_patents 실패: {exc}")
            _append_trace(state, "analyze_similar_patents", "error", start, str(exc))
        return state

    def _build_report(self, state: PatentValuationState) -> PatentValuationState:
        start = time.time()
        try:
            valuation = state.get("valuation") or {}
            report = build_structured_report(
                valuation,
                similar_analysis=state.get("similar_analysis"),
                evaluation_analysis=_valuation_analysis_text(valuation),
            )
            report["workflow"] = {
                "type": "langgraph" if self._has_langgraph() else "sequential_fallback",
                "node_trace": state.get("node_trace") or [],
                "errors": state.get("errors") or [],
                "human_reviews": state.get("human_reviews") or [],
            }
            state["report"] = report
            _append_trace(state, "build_report", "success", start, "보고서 생성 완료")
        except Exception as exc:
            message = f"build_report 실패: {exc}"
            state["report"] = {
                "error": message,
                "workflow": {
                    "type": "langgraph" if self._has_langgraph() else "sequential_fallback",
                    "node_trace": state.get("node_trace") or [],
                    "errors": state.get("errors") or [],
                    "human_reviews": state.get("human_reviews") or [],
                },
            }
            _append_error(state, message)
            _append_trace(state, "build_report", "error", start, str(exc))
        return state

    def _verify_report(self, state: PatentValuationState) -> PatentValuationState:
        start = time.time()
        try:
            service = ReportVerificationService()
            verification = service.verify(
                state.get("report") or {},
                state.get("valuation") or {},
                similar_analysis=state.get("similar_analysis"),
            )
            state["report_verification"] = verification
            if isinstance(state.get("report"), dict):
                state["report"]["quality_assurance"] = verification
                workflow = state["report"].setdefault("workflow", {})
                if isinstance(workflow, dict):
                    workflow["report_verification"] = {
                        "overall_reliability_score": verification.get("overall_reliability_score"),
                        "reliability_grade": verification.get("reliability_grade"),
                        "risk_level": verification.get("risk_level"),
                        "human_review_required": verification.get("human_review_required"),
                    }
            status = "flagged" if verification.get("human_review_required") else "success"
            _append_trace(
                state,
                "verify_report",
                status,
                start,
                str(verification.get("summary") or "보고서 신뢰도 검증 완료"),
            )
            if verification.get("human_review_required"):
                _append_human_review(
                    state,
                    {
                        "node": "verify_report",
                        "severity": "high" if verification.get("risk_level") == "high_risk" else "medium",
                        "reason": verification.get("summary") or "보고서 신뢰도 검증에서 사람 검토가 필요합니다.",
                        "status": "flagged",
                        "details": verification,
                    },
                )
        except Exception as exc:
            message = f"verify_report 실패: {exc}"
            state["report_verification"] = {
                "schema_version": "report-verification/v1",
                "overall_reliability_score": 0.0,
                "reliability_grade": "D",
                "risk_level": "high_risk",
                "human_review_required": True,
                "numeric_integrity": "unknown",
                "issues": [
                    {
                        "code": "verification_error",
                        "severity": "critical",
                        "message": message,
                        "location": "verify_report",
                    }
                ],
                "summary": "보고서 신뢰도 검증 중 오류가 발생했습니다.",
            }
            _append_error(state, message)
            _append_trace(state, "verify_report", "error", start, str(exc))
        return state

    def _supervisor_review_once(
        self,
        state: PatentValuationState,
        key: str,
        severity: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        done = state.setdefault("supervisor_reviews_done", [])
        if key in done:
            return
        done.append(key)
        self._human_review_gate(
            state,
            node=f"supervisor:{key}",
            severity=severity,
            reason=reason,
            details=details,
        )

    def _supervise_evidence(self, state: PatentValuationState) -> None:
        evidence = state.get("evidence") or {}
        errors = evidence.get("errors") or []
        if errors:
            self._supervisor_review_once(
                state,
                key="evidence",
                severity="high",
                reason="증거 수집 단계에서 오류가 발생했습니다.",
                details={"errors": errors},
            )

    def _supervise_validation(self, state: PatentValuationState) -> None:
        validation = state.get("validation") or {}
        errors = validation.get("errors") or []
        if not validation.get("valid", False):
            self._supervisor_review_once(
                state,
                key="validation",
                severity="high",
                reason="입력 검증에 실패했습니다.",
                details={"errors": errors, "validation": validation},
            )

    def _supervise_valuation(self, state: PatentValuationState) -> None:
        valuation = state.get("valuation") or {}
        all_scores = (valuation.get("auto_scores") or []) + (valuation.get("llm_scores") or [])
        average = _dimension_balanced_average(all_scores)
        market = valuation.get("market_growth") or {}
        low_items = [
            item
            for item in all_scores
            if isinstance(item.get("score"), (int, float)) and item.get("score") <= 2
        ]

        reasons: list[str] = []
        if not all_scores:
            reasons.append("평가 점수가 생성되지 않았습니다.")
        if average and average < self.options.human_review_low_score_threshold:
            reasons.append(
                f"종합 평균 {average}/5가 검토 기준 "
                f"{self.options.human_review_low_score_threshold}/5 미만입니다."
            )
        if len(low_items) >= 3:
            reasons.append("2점 이하 취약 항목이 3개 이상입니다.")
        if market.get("fallback"):
            reasons.append("시장 성장률 데이터가 fallback으로 산출되었습니다.")

        if reasons:
            self._supervisor_review_once(
                state,
                key="valuation",
                severity="medium",
                reason=" ".join(reasons),
                details={
                    "average_score": average,
                    "low_score_count": len(low_items),
                    "market_growth": market,
                    "low_score_items": low_items[:10],
                },
            )

    def _supervise_similar_patents(self, state: PatentValuationState) -> None:
        if state.get("similar_analysis"):
            return
        self._supervisor_review_once(
            state,
            key="similar_patents",
            severity="medium",
            reason="유사 특허 분석 결과가 없어 경쟁/차별화 판단 신뢰도가 낮습니다.",
            details={"similar_analysis": None},
        )

    def _human_review_gate(
        self,
        state: PatentValuationState,
        node: str,
        severity: str = "none",
        reason: str = "",
        details: dict[str, Any] | None = None,
    ) -> PatentValuationState:
        start = time.time()
        if not reason:
            _append_trace(state, node, "skipped", start, "사람 검토 조건 없음")
            return state
        if not self.options.enable_human_review:
            _append_trace(state, node, "flagged", start, reason)
            _append_human_review(
                state,
                {
                    "node": node,
                    "severity": severity,
                    "reason": reason,
                    "status": "flagged",
                    "details": details or {},
                },
            )
            return state

        try:
            from langgraph.types import interrupt
        except Exception:
            _append_trace(state, node, "flagged", start, "LangGraph interrupt 사용 불가: " + reason)
            return state

        review_request = {
            "node": node,
            "severity": severity,
            "reason": reason,
            "details": details or {},
            "expected_response": {
                "action": "approve | abort",
                "reviewer": "검토자 이름 또는 팀",
                "comment": "검토 의견",
                "updates": "선택. state에 병합할 보정 dict",
            },
        }
        state["human_review_pending"] = review_request
        response = interrupt(review_request)
        review = self._apply_human_review_response(state, node, review_request, response)
        _append_human_review(state, review)
        _append_trace(state, node, review["status"], start, review.get("comment", ""))
        return state

    def _apply_human_review_response(
        self,
        state: PatentValuationState,
        node: str,
        request: dict[str, Any],
        response: Any,
    ) -> dict[str, Any]:
        if not isinstance(response, dict):
            response = {"action": "approve", "comment": str(response)}

        action = str(response.get("action") or "approve").lower()
        if action not in {"approve", "abort"}:
            action = "approve"

        updates = response.get("updates")
        if isinstance(updates, dict):
            self._deep_merge_state(state, updates)

        if action == "abort":
            state["human_review_abort"] = True
            _append_error(state, f"{node} 사람 검토에서 workflow 중단: {response.get('comment', '')}")

        state.pop("human_review_pending", None)
        return {
            "node": node,
            "severity": request.get("severity"),
            "reason": request.get("reason"),
            "status": "approved" if action == "approve" else "aborted",
            "reviewer": response.get("reviewer"),
            "comment": response.get("comment", ""),
            "updates_applied": isinstance(updates, dict),
        }

    def _deep_merge_state(self, state: PatentValuationState, updates: dict[str, Any]) -> None:
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(state.get(key), dict):
                state[key] = self._deep_merge_dict(dict(state[key]), value)  # type: ignore[literal-required]
            else:
                state[key] = value  # type: ignore[literal-required]

    def _deep_merge_dict(self, base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._deep_merge_dict(dict(base[key]), value)
            else:
                base[key] = value
        return base

    def _has_langgraph(self) -> bool:
        try:
            import langgraph  # noqa: F401

            return True
        except Exception:
            return False

    def _to_response(self, state: PatentValuationState) -> dict[str, Any]:
        elapsed = round((state.get("completed_at") or time.time()) - state.get("started_at", time.time()), 2)
        interrupts = self._serialize_interrupts(state.get("__interrupt__"))  # type: ignore[typeddict-item]
        report_verification = state.get("report_verification") or {}
        if interrupts:
            status = "needs_human_review"
        elif report_verification.get("human_review_required"):
            status = "needs_human_review"
        elif state.get("report") and not state.get("errors"):
            status = "success"
        else:
            status = "partial_success"
        return {
            "status": status,
            "workflow_type": "langgraph" if self._has_langgraph() else "sequential_fallback",
            "elapsed_seconds": elapsed,
            "validation": state.get("validation"),
            "valuation": state.get("valuation"),
            "similar_analysis": state.get("similar_analysis"),
            "report": state.get("report"),
            "report_verification": report_verification or None,
            "human_reviews": state.get("human_reviews") or [],
            "human_review_pending": state.get("human_review_pending"),
            "interrupts": interrupts,
            "node_trace": state.get("node_trace") or [],
            "errors": state.get("errors") or [],
        }

    def _serialize_interrupts(self, interrupts: Any) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for item in interrupts or []:
            serialized.append(
                {
                    "id": getattr(item, "id", None),
                    "value": getattr(item, "value", item),
                }
            )
        return serialized


class _SequentialWorkflowRunner:
    """LangGraph 미설치 환경에서 supervisor loop를 실행하는 fallback runner입니다."""

    def __init__(self, workflow: PatentValuationWorkflow) -> None:
        self.workflow = workflow

    def invoke(self, state: PatentValuationState) -> PatentValuationState:
        for _ in range(30):
            state = self.workflow._supervisor(state)
            next_node = state.get("next_node")
            if next_node == "end":
                return state
            if next_node == "collect_evidence":
                state = self.workflow._collect_evidence(state)
            elif next_node == "validate_input":
                state = self.workflow._validate_input(state)
            elif next_node == "run_valuation":
                state = self.workflow._run_valuation(state)
            elif next_node == "analyze_similar_patents":
                state = self.workflow._analyze_similar_patents(state)
            elif next_node == "build_report":
                state = self.workflow._build_report(state)
            elif next_node == "verify_report":
                state = self.workflow._verify_report(state)
            else:
                _append_error(state, f"슈퍼바이저가 알 수 없는 next_node를 반환했습니다: {next_node}")
                return state
        _append_error(state, "슈퍼바이저 반복 한도를 초과했습니다.")
        return state
