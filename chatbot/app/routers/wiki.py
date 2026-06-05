"""Wiki audit API router source restoration."""

from __future__ import annotations

from fastapi import APIRouter

from ..agents.wiki_graph import run_wiki_audit_graph, wiki_audit_graph_mermaid
from ..schemas import AuditApplyRequest, WikiAgentRunRequest


router = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])


@router.post("/agent/run")
def agent_run(request: WikiAgentRunRequest) -> dict:
    return run_wiki_audit_graph(
        mode=request.mode,
        audit_id=request.audit_id,
        exclude_finding_ids=request.exclude_finding_ids,
        reviewer=request.reviewer,
        notes=request.notes,
        refresh_vectorstore=request.refresh_vectorstore,
    )


@router.get("/agent/mermaid")
def agent_mermaid() -> dict:
    return {"format": "mermaid", "diagram": wiki_audit_graph_mermaid()}


@router.post("/audit")
def audit() -> dict:
    return run_wiki_audit_graph(mode="audit").get("audit", {})


@router.get("/audit-review")
def review(audit_id: str | None = None) -> dict:
    return run_wiki_audit_graph(mode="review", audit_id=audit_id).get("review", {})


@router.post("/audit-apply")
def apply_review(request: AuditApplyRequest) -> dict:
    return run_wiki_audit_graph(
        mode="apply",
        audit_id=request.audit_id,
        exclude_finding_ids=request.exclude_finding_ids,
        reviewer=request.reviewer,
        notes=request.notes,
        refresh_vectorstore=request.refresh_vectorstore,
    ).get("apply_result", {})


@router.post("/audit-auto-refresh")
def auto_refresh() -> dict:
    return run_wiki_audit_graph(mode="auto_refresh", refresh_vectorstore=True).get("apply_result", {})
