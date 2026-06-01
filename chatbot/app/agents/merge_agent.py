"""Final answer merger node."""

from __future__ import annotations

from datetime import datetime

from .state import ChatAgentState


def finish_answer(state: ChatAgentState) -> ChatAgentState:
    result = dict(state.get("result") or {})
    metrics = dict(result.get("metrics") or {})
    metrics["agent_trace"] = state.get("trace", [])
    result["metrics"] = metrics
    trace = list(state.get("trace", []))
    trace.append({"node": "finish_answer", "status": "success", "at": datetime.now().isoformat(timespec="seconds")})
    return {**state, "result": result, "trace": trace}
