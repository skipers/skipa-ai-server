"""FastAPI endpoint for pre-application valuation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query

from .schemas import PreApplicationValuationRequest, SavedValuationResponse
from .service import evaluate_pre_application
from .storage import DEFAULT_OUTPUT_DIR, save_result


app = FastAPI(
    title="SKIPA Pre-Application Valuation API",
    description="출원 전 아이디어/특허의 기술성, 권리성, 사업성을 사전 평가합니다.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/v1/pre-application-valuations/evaluate",
    response_model=SavedValuationResponse,
    tags=["pre-application-valuation"],
)
def evaluate(
    request: PreApplicationValuationRequest,
    save: bool = Query(default=True, description="결과 JSON 파일 저장 여부"),
) -> dict[str, Any]:
    result = evaluate_pre_application(request)
    output_path = ""
    if save:
        path = save_result(result, DEFAULT_OUTPUT_DIR)
        result.setdefault("artifacts", {})
        result["artifacts"]["output_path"] = str(path)
        output_path = str(path)
    return {"status": "success", "output_path": output_path, "result": result}


@app.get("/api/v1/pre-application-valuations/latest", tags=["pre-application-valuation"])
def latest() -> dict[str, Any]:
    latest_path = DEFAULT_OUTPUT_DIR / "latest.json"
    if not latest_path.exists():
        return {"status": "empty", "result": None}
    return {"status": "success", "output_path": str(latest_path), "result": _read_json(latest_path)}


def _read_json(path: Path) -> dict[str, Any]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {"value": payload}
