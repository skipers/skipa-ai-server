"""Service layer for pre-application valuation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from .diagnostics import build_diagnostics, estimate_ipc, keyword_summary
from .llm_evaluator import evaluate_checklist
from .report_builder import build_report
from .schemas import PreApplicationValuationRequest


def evaluate_pre_application(request: PreApplicationValuationRequest | dict[str, Any]) -> dict[str, Any]:
    parsed = request if isinstance(request, PreApplicationValuationRequest) else PreApplicationValuationRequest.model_validate(request)
    evaluated_at = datetime.now()
    diagnostics = build_diagnostics(parsed)
    ipc = estimate_ipc(parsed)
    keywords = keyword_summary(parsed)
    evaluation = evaluate_checklist(parsed, diagnostics, ipc)
    return build_report(
        evaluation_id=f"preval-{uuid4().hex[:12]}",
        evaluated_at=evaluated_at,
        request=parsed,
        diagnostics=diagnostics,
        ipc=ipc,
        keywords=keywords,
        evaluation=evaluation,
    )
