"""SKIPA 특허 유지/포기 의사결정 AI Backend API입니다."""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agent.patent_decision_graph import PatentDecisionWorkflow, PatentDecisionWorkflowOptions
from api.job_store import create_job, get_job, set_completed, set_failed, set_running
from api.schemas import (
    BusinessRagToolRequest,
    PatentDecisionOptionsRequest,
    PatentDecisionRequest,
    PatentDecisionResponse,
    PatentReportRequest,
    PatentToolRequest,
    ReportJobResponse,
    ReportJobResultResponse,
    ReportJobStatusResponse,
)
from core.paths import (
    API_TEST_EXTRACTED_INPUT_DIR,
    API_TEST_INPUT_UPLOAD_DIR,
    API_TEST_PDF_UPLOAD_DIR,
    API_TEST_REPORT_OUTPUT_DIR,
    ARTIFACT_UPLOAD_DIR,
    SAMPLE_INPUT_DIR,
)
from core.schemas import normalize_patent_input
from evaluation.auto_score import calc_auto_scores
from evaluation.kosis_growth_fetcher import get_growth_score_from_json
from evaluation.llm_evaluator import evaluate_all
from services.evidence_collection_service import (
    BusinessUseRagService,
    PatentMetadataExtractionService,
)


app = FastAPI(
    title="SKIPA AI Server API",
    description=(
        "특허 가치 평가, 추가 자료 수집, agentic workflow 기반 유지/포기 "
        "의사결정 보조 보고서 생성 API"
    ),
    version="0.2.0",
)


def _model_to_dict(model: Any) -> dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _safe_name(value: str, fallback: str = "patent") -> str:
    cleaned = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", str(value or "")).strip("._")
    return cleaned or fallback


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _write_json_file(path: Path, data: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _patent_id_from_payload(patent: dict[str, Any]) -> str:
    patent = normalize_patent_input(patent)
    meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
    return str(
        patent.get("patent_id")
        or meta.get("registration_number")
        or meta.get("application_number")
        or "patent"
    )


def _save_api_test_input_payload(filename: str, payload: dict[str, Any]) -> str:
    stem = _safe_name(Path(filename).stem)
    path = API_TEST_INPUT_UPLOAD_DIR / f"{_timestamp()}_{stem}.json"
    return _write_json_file(path, payload)


def _save_uploaded_pdf(file: UploadFile, directory: Path) -> Path:
    original_name = Path(file.filename or "patent.pdf").name
    safe_name = _safe_name(original_name, fallback="patent.pdf")
    content_type = (file.content_type or "").lower()
    looks_like_pdf = safe_name.lower().endswith(".pdf") or content_type == "application/pdf"
    if not looks_like_pdf:
        raise HTTPException(
            status_code=400,
            detail=(
                "PDF 파일만 업로드할 수 있습니다. "
                f"filename={original_name!r}, content_type={file.content_type!r}"
            ),
        )
    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"

    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / f"{_timestamp()}_{safe_name}"
    file.file.seek(0)
    with dest.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return dest


def _save_extracted_patent_input(source_pdf: str, patent: dict[str, Any]) -> str:
    patent_id = _safe_name(_patent_id_from_payload(patent))
    pdf_stem = _safe_name(Path(source_pdf).stem)
    path = API_TEST_EXTRACTED_INPUT_DIR / f"{_timestamp()}_{patent_id}_{pdf_stem}.json"
    return _write_json_file(path, patent)


def _save_api_test_report_result(job_id: str, result: dict[str, Any]) -> str:
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    patent_id = _safe_name(str(validation.get("patent_id") or "patent"))
    path = API_TEST_REPORT_OUTPUT_DIR / f"{_timestamp()}_{patent_id}_{job_id}.json"
    saved = {
        "job_id": job_id,
        "saved_at": datetime.now().isoformat(),
        "result": result,
    }
    return _write_json_file(path, saved)


def _extract_normalized_patent_from_result(result: dict[str, Any]) -> dict[str, Any] | None:
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    candidates = [
        evidence,
        result.get("valuation", {}).get("evidence") if isinstance(result.get("valuation"), dict) else {},
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        metadata = candidate.get("patent_metadata")
        if not isinstance(metadata, dict):
            continue
        normalized = metadata.get("normalized_patent")
        if isinstance(normalized, dict):
            return normalized
    return None


def _read_uploaded_json(file: UploadFile) -> dict[str, Any]:
    """Swagger 파일 업로드로 받은 JSON을 dict로 파싱합니다."""
    safe_name = Path(file.filename or "patent.json").name
    if not safe_name.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="JSON 파일만 업로드할 수 있습니다.")

    try:
        raw = file.file.read()
        if not raw:
            raise ValueError("파일 내용이 비어 있습니다.")
        payload = json.loads(raw.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="JSON 파일은 UTF-8 인코딩이어야 합니다.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"JSON 파싱 실패: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON 최상위 값은 object여야 합니다.")
    return payload


def _extract_patent_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """업로드 JSON을 서비스용 patent payload로 정규화합니다.

    - {"patent": {...}} 형태면 patent 값을 사용합니다.
    - {"patent_data": {...}} 형태면 patent_data 값을 사용합니다.
    - 그 외에는 업로드된 JSON 전체를 특허 입력으로 간주합니다.
    """
    return normalize_patent_input(payload)


def _run_workflow_for_json(patent: dict[str, Any]) -> dict[str, Any]:
    """서비스용 기본 workflow입니다. PDF 추출만 제외하고 내부 도구를 기본 실행합니다."""
    patent = normalize_patent_input(patent)
    options = PatentDecisionWorkflowOptions(
        enable_market=True,
        enable_auto=True,
        enable_llm=True,
        enable_pdf_metadata_extraction=False,
        enable_business_rag=True,
        enable_similar_analysis=True,
        similar_use_llm=True,
        rag_top_k=5,
        fail_on_validation_error=True,
    )
    return PatentDecisionWorkflow(options).run(patent)


def _run_workflow_for_pdf(source_pdf: str) -> dict[str, Any]:
    """서비스용 PDF 입력 workflow입니다."""
    options = PatentDecisionWorkflowOptions(
        enable_market=True,
        enable_auto=True,
        enable_llm=True,
        enable_pdf_metadata_extraction=True,
        enable_business_rag=True,
        enable_similar_analysis=True,
        similar_use_llm=True,
        rag_top_k=5,
        fail_on_validation_error=True,
    )
    result = PatentDecisionWorkflow(options).run({"source_pdf": source_pdf})
    normalized = _extract_normalized_patent_from_result(result)
    if normalized:
        extracted_path = _save_extracted_patent_input(source_pdf, normalized)
        result.setdefault("artifacts", {})
        result["artifacts"]["extracted_input_path"] = extracted_path
    return result


def _execute_and_store(job_id: str, runner: Any, save_report_output: bool = True) -> None:
    set_running(job_id)
    try:
        result = runner()
        if save_report_output:
            output_path = _save_api_test_report_result(job_id, result)
            result.setdefault("artifacts", {})
            result["artifacts"]["report_output_path"] = output_path
        set_completed(job_id, result)
    except Exception as exc:
        set_failed(job_id, str(exc))


def _job_urls(job_id: str) -> tuple[str, str]:
    return f"/api/v1/reports/{job_id}/status", f"/api/v1/reports/{job_id}/result"


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# ─────────────────────────────────────────────
# 서비스용 Report Job API
# ─────────────────────────────────────────────


@app.post(
    "/api/v1/reports/patent-maintenance/from-json",
    response_model=ReportJobResponse,
    tags=["reports"],
)
def create_patent_report_from_json(request: PatentReportRequest) -> dict[str, Any]:
    """특허 JSON 입력으로 유지/포기 의사결정 보고서 Job을 생성합니다.

    Swagger 테스트 편의를 위해 현재 구현은 요청 시점에 동기 실행 후 완료된
    Job을 저장합니다. API 모양은 비동기 Job API 형태를 유지합니다.
    """
    payload = _model_to_dict(request)
    input_path = _save_api_test_input_payload("request_body.json", payload)
    job_id = create_job("patent-maintenance-json", payload)
    _execute_and_store(job_id, lambda: _run_workflow_for_json(request.patent))
    job = get_job(job_id) or {}
    result = job.get("result") or {}
    status_url, result_url = _job_urls(job_id)
    return {
        "job_id": job_id,
        "status": job.get("status", "unknown"),
        "message": "특허 유지/포기 보고서 생성 Job이 처리되었습니다.",
        "status_url": status_url,
        "result_url": result_url,
        "input_path": input_path,
        "output_path": (result.get("artifacts") or {}).get("report_output_path"),
    }


@app.post(
    "/api/v1/reports/patent-maintenance/from-json-file",
    response_model=ReportJobResponse,
    tags=["reports"],
)
def create_patent_report_from_json_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """특허 JSON 파일 업로드로 유지/포기 의사결정 보고서 Job을 생성합니다.

    ``samples/input`` 아래 샘플처럼 특허 JSON 자체를 업로드해도 되고,
    ``{"patent": {...}}`` 또는 ``{"patent_data": {...}}`` 형태도 허용합니다.
    """
    payload = _read_uploaded_json(file)
    input_path = _save_api_test_input_payload(file.filename or "patent.json", payload)
    patent = _extract_patent_payload(payload)
    job_id = create_job(
        "patent-maintenance-json-file",
        {
            "filename": Path(file.filename or "patent.json").name,
            "input_path": input_path,
            "patent": patent,
        },
    )
    _execute_and_store(job_id, lambda: _run_workflow_for_json(patent))
    job = get_job(job_id) or {}
    result = job.get("result") or {}
    status_url, result_url = _job_urls(job_id)
    return {
        "job_id": job_id,
        "status": job.get("status", "unknown"),
        "message": "JSON 파일 기반 특허 유지/포기 보고서 생성 Job이 처리되었습니다.",
        "status_url": status_url,
        "result_url": result_url,
        "input_path": input_path,
        "output_path": (result.get("artifacts") or {}).get("report_output_path"),
    }


@app.post(
    "/api/v1/reports/patent-maintenance/from-pdf",
    response_model=ReportJobResponse,
    tags=["reports"],
)
def create_patent_report_from_pdf(file: UploadFile = File(...)) -> dict[str, Any]:
    """특허 PDF 파일 업로드로 유지/포기 의사결정 보고서 Job을 생성합니다."""
    dest = _save_uploaded_pdf(file, ARTIFACT_UPLOAD_DIR)

    job_id = create_job("patent-maintenance-pdf", {"source_pdf": str(dest)})
    _execute_and_store(job_id, lambda: _run_workflow_for_pdf(str(dest)))
    job = get_job(job_id) or {}
    result = job.get("result") or {}
    artifacts = result.get("artifacts") or {}
    status_url, result_url = _job_urls(job_id)
    return {
        "job_id": job_id,
        "status": job.get("status", "unknown"),
        "message": "PDF 기반 특허 유지/포기 보고서 생성 Job이 처리되었습니다.",
        "status_url": status_url,
        "result_url": result_url,
        "input_path": artifacts.get("extracted_input_path"),
        "output_path": artifacts.get("report_output_path"),
    }


@app.get("/api/v1/reports/{job_id}", response_model=ReportJobStatusResponse, tags=["reports"])
def get_report_job(job_id: str) -> dict[str, Any]:
    return get_report_job_status(job_id)


@app.get("/api/v1/reports/{job_id}/status", response_model=ReportJobStatusResponse, tags=["reports"])
def get_report_job_status(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job을 찾을 수 없습니다: {job_id}")
    result = job.get("result") or {}
    node_trace = result.get("node_trace") or []
    current_node = node_trace[-1]["node"] if node_trace else None
    progress = min(int(len(node_trace) / 6 * 100), 100) if node_trace else 0
    return {
        "job_id": job_id,
        "status": job.get("status", "unknown"),
        "current_node": current_node,
        "progress": progress,
        "node_trace": node_trace,
        "errors": job.get("errors") or [],
    }


@app.get("/api/v1/reports/{job_id}/result", response_model=ReportJobResultResponse, tags=["reports"])
def get_report_job_result(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job을 찾을 수 없습니다: {job_id}")
    result = job.get("result") or {}
    return {
        "job_id": job_id,
        "status": job.get("status", "unknown"),
        "decision": result.get("decision"),
        "report": result.get("report"),
        "workflow": {
            "type": result.get("workflow_type"),
            "elapsed_seconds": result.get("elapsed_seconds"),
            "node_trace": result.get("node_trace") or [],
        },
        "artifacts": result.get("artifacts"),
        "errors": job.get("errors") or [],
    }


# ─────────────────────────────────────────────
# 개발/디버그용 통합 API
# ─────────────────────────────────────────────


@app.post("/api/v1/dev/patent-decision/evaluate", response_model=PatentDecisionResponse, tags=["dev"])
def dev_evaluate_patent_decision(request: PatentDecisionRequest) -> dict[str, Any]:
    """옵션을 직접 제어하는 개발/디버그용 동기 평가 API입니다."""
    try:
        option_dict = _model_to_dict(request.options)
        options = PatentDecisionWorkflowOptions.from_dict(option_dict)
        return PatentDecisionWorkflow(options).run(normalize_patent_input(request.patent_data))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/api/v1/dev/patent-decision/evaluate-sample/{sample_name}",
    response_model=PatentDecisionResponse,
    tags=["dev"],
)
def dev_evaluate_sample_patent(
    sample_name: str,
    options: PatentDecisionOptionsRequest | None = None,
) -> dict[str, Any]:
    """``samples/input`` 아래 샘플 JSON 파일을 옵션과 함께 실행합니다."""
    safe_name = Path(sample_name).name
    if not safe_name.endswith(".json"):
        safe_name = f"{safe_name}.json"
    sample_path = SAMPLE_INPUT_DIR / safe_name
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail=f"샘플 파일을 찾을 수 없습니다: {safe_name}")

    with sample_path.open(encoding="utf-8") as file:
        patent_data = json.load(file)
    option_dict = _model_to_dict(options) if options else {
        "enable_market": True,
        "enable_auto": True,
        "enable_llm": True,
        "enable_pdf_metadata_extraction": False,
        "enable_business_rag": True,
        "enable_similar_analysis": True,
        "similar_use_llm": True,
        "rag_top_k": 5,
        "fail_on_validation_error": True,
    }
    return PatentDecisionWorkflow(PatentDecisionWorkflowOptions.from_dict(option_dict)).run(
        normalize_patent_input(patent_data)
    )


# 기존 경로는 하위 호환용으로 유지합니다.
@app.post("/api/v1/patent-decision/evaluate", response_model=PatentDecisionResponse, tags=["legacy"])
def legacy_evaluate_patent_decision(request: PatentDecisionRequest) -> dict[str, Any]:
    return dev_evaluate_patent_decision(request)


@app.post(
    "/api/v1/patent-decision/evaluate-sample/{sample_name}",
    response_model=PatentDecisionResponse,
    tags=["legacy"],
)
def legacy_evaluate_sample_patent(sample_name: str) -> dict[str, Any]:
    return dev_evaluate_sample_patent(sample_name)


# ─────────────────────────────────────────────
# 기능별 Tool API
# ─────────────────────────────────────────────


@app.post("/api/v1/tools/patent-metadata", tags=["tools"])
def tool_extract_patent_metadata(file: UploadFile = File(...)) -> dict[str, Any]:
    """PDF 원문 파일 업로드로 특허 메타데이터를 추출합니다."""
    try:
        pdf_path = _save_uploaded_pdf(file, API_TEST_PDF_UPLOAD_DIR)
        result = PatentMetadataExtractionService().extract_from_pdf(pdf_path)
        result["uploaded_pdf_path"] = str(pdf_path)
        normalized = result.get("normalized_patent")
        if isinstance(normalized, dict):
            result["extracted_input_path"] = _save_extracted_patent_input(str(pdf_path), normalized)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/tools/business-rag", tags=["tools"])
def tool_business_rag(request: BusinessRagToolRequest) -> dict[str, Any]:
    """제품/사업화 현황 RAG 추정을 실행합니다."""
    try:
        return BusinessUseRagService().estimate(normalize_patent_input(request.patent), query=request.query, top_k=request.top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/tools/market-growth", tags=["tools"])
def tool_market_growth(request: PatentToolRequest) -> dict[str, Any]:
    """KOSIS/KSIC 기반 시장 성장률 점수를 조회합니다."""
    try:
        return get_growth_score_from_json(normalize_patent_input(request.patent))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/tools/auto-score", tags=["tools"])
def tool_auto_score(request: PatentToolRequest) -> dict[str, Any]:
    """규칙 기반 자동 평가 점수를 계산합니다."""
    try:
        return {"scores": calc_auto_scores(normalize_patent_input(request.patent))}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/tools/llm-evaluation", tags=["tools"])
def tool_llm_evaluation(request: PatentToolRequest) -> dict[str, Any]:
    """LLM 기반 43개 평가 항목을 실행합니다."""
    try:
        return {"scores": evaluate_all(normalize_patent_input(request.patent))}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/tools/similar-patents", tags=["tools"])
def tool_similar_patents(request: PatentToolRequest) -> dict[str, Any]:
    """현재 보유한 유사 특허 분석 파일을 조회하거나 분석을 시도합니다."""
    try:
        workflow = PatentDecisionWorkflow(
            PatentDecisionWorkflowOptions(
                enable_market=False,
                enable_auto=True,
                enable_llm=False,
                enable_pdf_metadata_extraction=False,
                enable_business_rag=False,
                enable_similar_analysis=True,
                similar_use_llm=False,
                fail_on_validation_error=False,
            )
        )
        result = workflow.run(normalize_patent_input(request.patent))
        return {"similar_analysis": result.get("similar_analysis"), "errors": result.get("errors") or []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
