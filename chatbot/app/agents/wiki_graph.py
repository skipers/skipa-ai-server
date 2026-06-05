"""LangGraph workflow for wiki/chatbot data audit and vectorstore refresh."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from ..vectorstore import (
    apply_human_review,
    audit_and_refresh_vectorstores,
    audit_review_report,
    auto_audit_apply_and_refresh,
    refresh_vectorstores,
    vectorstore_status,
)


WikiAgentMode = Literal["audit", "review", "apply", "auto_refresh", "refresh", "status"]


class WikiAgentState(TypedDict, total=False):
    mode: WikiAgentMode
    audit_id: str | None
    exclude_finding_ids: list[str] | None
    reviewer: str | None
    notes: str | None
    refresh_vectorstore: bool
    audit: dict[str, Any]
    review: dict[str, Any]
    apply_result: dict[str, Any]
    auto_refresh_result: dict[str, Any]
    refresh_result: dict[str, Any]
    vectorstore_status: dict[str, Any]
    route: str
    result: dict[str, Any]
    trace: list[dict[str, Any]]


def _trace(state: WikiAgentState, node: str, status: str, detail: str | None = None) -> list[dict[str, Any]]:
    trace = list(state.get("trace", []))
    item: dict[str, Any] = {
        "node": node,
        "status": status,
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    if detail:
        item["detail"] = detail
    trace.append(item)
    return trace


def route_request(state: WikiAgentState) -> WikiAgentState:
    mode = state.get("mode", "audit")
    if mode not in {"audit", "review", "apply", "auto_refresh", "refresh", "status"}:
        mode = "audit"
    return {**state, "route": mode, "trace": _trace(state, "route_request", "success", f"mode={mode}")}


def run_audit_node(state: WikiAgentState) -> WikiAgentState:
    audit = audit_and_refresh_vectorstores(refresh_vectorstore=bool(state.get("refresh_vectorstore", False)))
    return {**state, "audit": audit, "audit_id": audit.get("audit_id"), "trace": _trace(state, "run_audit", "success")}


def load_review_node(state: WikiAgentState) -> WikiAgentState:
    review = audit_review_report(audit_id=state.get("audit_id"))
    audit_id = review.get("audit", {}).get("audit_id") if isinstance(review.get("audit"), dict) else state.get("audit_id")
    return {**state, "review": review, "audit_id": audit_id, "trace": _trace(state, "load_review", "success")}


def apply_review_node(state: WikiAgentState) -> WikiAgentState:
    apply_result = apply_human_review(
        audit_id=state.get("audit_id"),
        exclude_finding_ids=state.get("exclude_finding_ids"),
        reviewer=state.get("reviewer"),
        notes=state.get("notes"),
        refresh_vectorstore=bool(state.get("refresh_vectorstore", True)),
    )
    return {
        **state,
        "apply_result": apply_result,
        "audit_id": apply_result.get("audit_id", state.get("audit_id")),
        "trace": _trace(state, "apply_review", "success"),
    }


def auto_refresh_node(state: WikiAgentState) -> WikiAgentState:
    result = auto_audit_apply_and_refresh(refresh_vectorstore=bool(state.get("refresh_vectorstore", True)))
    apply_result = result.get("apply_result", {})
    audit = result.get("audit", {})
    return {
        **state,
        "audit": audit,
        "audit_id": apply_result.get("audit_id", audit.get("audit_id", state.get("audit_id"))),
        "apply_result": apply_result,
        "auto_refresh_result": result,
        "trace": _trace(state, "auto_refresh", "success"),
    }


def refresh_vectorstore_node(state: WikiAgentState) -> WikiAgentState:
    refresh_result = refresh_vectorstores(use_reviewed=True)
    return {**state, "refresh_result": refresh_result, "trace": _trace(state, "refresh_vectorstore", "success")}


def collect_status_node(state: WikiAgentState) -> WikiAgentState:
    status = vectorstore_status()
    return {**state, "vectorstore_status": status, "trace": _trace(state, "collect_status", "success")}


def finish_node(state: WikiAgentState) -> WikiAgentState:
    mode = state.get("mode", "audit")
    result: dict[str, Any] = {
        "mode": mode,
        "audit_id": state.get("audit_id"),
        "trace": state.get("trace", []),
        "vectorstore_status": state.get("vectorstore_status"),
    }
    if "audit" in state:
        result["audit"] = state["audit"]
    if "review" in state:
        result["review"] = state["review"]
    if "apply_result" in state:
        result["apply_result"] = state["apply_result"]
    if "auto_refresh_result" in state:
        result["auto_refresh_result"] = state["auto_refresh_result"]
    if "refresh_result" in state:
        result["refresh_result"] = state["refresh_result"]
    return {**state, "result": result, "trace": _trace(state, "finish", "success")}


def _route(state: WikiAgentState) -> str:
    return state.get("route", "audit")


def build_wiki_audit_graph():
    graph = StateGraph(WikiAgentState)
    graph.add_node("route_request", route_request)
    graph.add_node("run_audit", run_audit_node)
    graph.add_node("load_review", load_review_node)
    graph.add_node("apply_review", apply_review_node)
    graph.add_node("auto_refresh", auto_refresh_node)
    graph.add_node("refresh_vectorstore", refresh_vectorstore_node)
    graph.add_node("collect_status", collect_status_node)
    graph.add_node("finish", finish_node)

    graph.set_entry_point("route_request")
    graph.add_conditional_edges(
        "route_request",
        _route,
        {
            "audit": "run_audit",
            "review": "load_review",
            "apply": "apply_review",
            "auto_refresh": "auto_refresh",
            "refresh": "refresh_vectorstore",
            "status": "collect_status",
        },
    )
    graph.add_edge("run_audit", "collect_status")
    graph.add_edge("load_review", "collect_status")
    graph.add_edge("apply_review", "collect_status")
    graph.add_edge("auto_refresh", "collect_status")
    graph.add_edge("refresh_vectorstore", "collect_status")
    graph.add_edge("collect_status", "finish")
    graph.add_edge("finish", END)
    return graph.compile()


WIKI_AUDIT_GRAPH = build_wiki_audit_graph()


def run_wiki_audit_graph(
    *,
    mode: WikiAgentMode = "audit",
    audit_id: str | None = None,
    exclude_finding_ids: list[str] | None = None,
    reviewer: str | None = None,
    notes: str | None = None,
    refresh_vectorstore: bool | None = None,
) -> dict[str, Any]:
    initial_state: WikiAgentState = {
        "mode": mode,
        "audit_id": audit_id,
        "exclude_finding_ids": exclude_finding_ids,
        "reviewer": reviewer,
        "notes": notes,
        "refresh_vectorstore": bool(refresh_vectorstore) if refresh_vectorstore is not None else mode in {"apply", "auto_refresh"},
        "trace": [],
    }
    state = WIKI_AUDIT_GRAPH.invoke(initial_state)
    result = state.get("result", {})
    result["trace"] = state.get("trace", result.get("trace", []))
    return result


def wiki_audit_graph_mermaid() -> str:
    return """flowchart TD
  A[Wiki/API 요청] --> B{실행 모드}

  B -- status --> C[현재 vectorstore 상태 조회]
  B -- audit --> D[특허별 wiki/승인 데이터 감사]
  B -- review --> E[사람 검토용 감사 Markdown 로드]
  B -- apply --> F[사람이 제외한 finding 적용]
  B -- auto_refresh --> G[주의/나쁜 데이터 자동 제외]
  B -- refresh --> H[승인 데이터만 standby slot 재생성]

  D --> I[감사 리포트 저장]
  E --> C
  F --> J[approved_context.md 재작성]
  G --> J
  J --> H
  H --> K[blue/green active_slot 전환]
  K --> W[특허별 wiki vectorstore 최신본 사용]
  I --> C
  W --> C
  C --> L[Swagger/UI 결과 반환]
"""
