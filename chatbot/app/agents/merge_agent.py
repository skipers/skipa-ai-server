"""Final answer merger node."""

from __future__ import annotations

from datetime import datetime

from .state import ChatAgentState


def _needs_diagram(state: ChatAgentState) -> bool:
    intent = state.get("intent") or {}
    query = state.get("query", "")
    return bool(intent.get("needs_diagram") or intent.get("answer_format") in {"diagram", "table_and_diagram"} or "다이어그램" in query)


def _append_diagram(answer: str, state: ChatAgentState) -> str:
    if "```mermaid" in answer or not _needs_diagram(state):
        return answer
    source_plan = (state.get("intent") or {}).get("source_plan") or []
    labels = " / ".join(source_plan[:4]) or "patent data"
    diagram = f"""

```mermaid
flowchart LR
  Q[질문] --> I[의도 파악]
  I --> S[{labels}]
  S --> R[RAG 검색]
  R --> A[답변 생성]
```
"""
    return answer.rstrip() + diagram


def finish_answer(state: ChatAgentState) -> ChatAgentState:
    result = dict(state.get("result") or {})
    result["answer"] = _append_diagram(str(result.get("answer") or ""), state)
    metrics = dict(result.get("metrics") or {})
    trace = list(state.get("trace", []))
    finish_trace = {"node": "finish_answer", "status": "success", "at": datetime.now().isoformat(timespec="seconds")}
    trace.append(finish_trace)
    metrics["agent_trace"] = trace
    metrics["chatbot_workflow"] = "history_context -> intent_agent -> wiki_retrieval -> web_search -> rag_answer -> response_enrichment"
    metrics["answer_has_diagram"] = "```mermaid" in str(result.get("answer") or "")
    result["metrics"] = metrics
    return {**state, "result": result, "trace": trace}
