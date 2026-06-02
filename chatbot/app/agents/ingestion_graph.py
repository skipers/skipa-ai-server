"""LangGraph preprocessing and reindex workflow for restored RAG ingestion."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypedDict

from ..rag.legacy_adapter import (
    legacy_engine_status,
    reindex_business,
    reindex_global,
    reindex_patent,
)
from ..vectorstore import vectorstore_status


class IngestionState(TypedDict, total=False):
    scope: Literal["patent", "global", "business", "status"]
    patent_id: str | None
    force_rebuild: bool
    refresh_reviewed_vectorstore: bool
    result: dict[str, Any]
    trace: list[dict[str, Any]]
    errors: list[str]


def _trace(state: IngestionState, node: str, **extra: Any) -> list[dict[str, Any]]:
    trace = list(state.get("trace", []))
    trace.append({"node": node, "at": datetime.now().isoformat(timespec="seconds"), **extra})
    return trace


def inspect_request(state: IngestionState) -> IngestionState:
    status = legacy_engine_status()
    scope = state.get("scope") or "status"
    errors = list(state.get("errors", []))
    if scope == "patent" and not state.get("patent_id"):
        errors.append("patent scope requires patent_id")
    return {
        **state,
        "scope": scope,
        "errors": errors,
        "trace": _trace(state, "inspect_request", scope=scope, legacy_available=status["available"]),
    }


def run_reindex(state: IngestionState) -> IngestionState:
    if state.get("errors"):
        return {**state, "trace": _trace(state, "run_reindex", status="skipped")}

    scope = state.get("scope")
    force_rebuild = bool(state.get("force_rebuild", True))
    refresh_reviewed = bool(state.get("refresh_reviewed_vectorstore", False))
    if scope == "status":
        result = {"status": "OK", "legacy_engine": legacy_engine_status(), "vectorstore": vectorstore_status()}
    elif scope == "patent":
        result = reindex_patent(
            str(state.get("patent_id")),
            force_rebuild=force_rebuild,
            refresh_reviewed_vectorstore=refresh_reviewed,
        )
    elif scope == "global":
        result = reindex_global(force_rebuild=force_rebuild, refresh_reviewed_vectorstore=refresh_reviewed)
    elif scope == "business":
        result = reindex_business(force_rebuild=force_rebuild, refresh_reviewed_vectorstore=refresh_reviewed)
    else:
        result = {"status": "ERROR", "message": f"unsupported scope: {scope}"}
    return {**state, "result": result, "trace": _trace(state, "run_reindex", status=result.get("status"))}


def finish_ingestion(state: IngestionState) -> IngestionState:
    result = dict(state.get("result") or {})
    if state.get("errors"):
        result = {"status": "ERROR", "errors": state.get("errors", [])}
    result["agent_trace"] = state.get("trace", [])
    return {**state, "result": result, "trace": _trace(state, "finish_ingestion", status=result.get("status"))}


def _sequential(state: IngestionState) -> IngestionState:
    state = inspect_request(state)
    state = run_reindex(state)
    return finish_ingestion(state)


def build_ingestion_graph() -> Any:
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(IngestionState)
        graph.add_node("inspect_request", inspect_request)
        graph.add_node("run_reindex", run_reindex)
        graph.add_node("finish_ingestion", finish_ingestion)
        graph.set_entry_point("inspect_request")
        graph.add_edge("inspect_request", "run_reindex")
        graph.add_edge("run_reindex", "finish_ingestion")
        graph.add_edge("finish_ingestion", END)
        return graph.compile()
    except Exception:
        return None


INGESTION_GRAPH = build_ingestion_graph()


def run_ingestion_graph(
    *,
    scope: Literal["patent", "global", "business", "status"],
    patent_id: str | None = None,
    force_rebuild: bool = True,
    refresh_reviewed_vectorstore: bool = False,
) -> dict[str, Any]:
    state: IngestionState = {
        "scope": scope,
        "patent_id": patent_id,
        "force_rebuild": force_rebuild,
        "refresh_reviewed_vectorstore": refresh_reviewed_vectorstore,
        "trace": [],
        "errors": [],
    }
    final = INGESTION_GRAPH.invoke(state) if INGESTION_GRAPH is not None else _sequential(state)
    return dict(final.get("result") or {})


def ingestion_graph_mermaid() -> str:
    return """flowchart TD
  A[전처리/Reindex API] --> B[요청 검사]
  B --> C{대상 scope}

  C -- patent --> D[특허 1건 전처리]
  C -- global --> E[전체 특허 코어 index]
  C -- business --> F[공통 업무 index]
  C -- status --> G[현재 상태 조회]

  D --> H[원본 PDF/보고서 PDF/JSON chunk]
  E --> H
  F --> I[공통 업무 chunk]

  H --> J[코어 vectorstore refresh]
  I --> J
  J --> K{승인 wiki refresh?}
  K -- yes --> L[특허별 approved_context.md만 임베딩]
  K -- no --> M[wiki 유지]
  L --> N[Swagger/UI 결과 반환]
  M --> N
  G --> N
"""
