"""LangGraph workflow for the patent-application assistant chatbot."""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any, TypedDict

from ..application_data import (
    application_index_status,
    cards_from_application_hits,
    preferred_application_hits,
    refresh_application_index,
    search_application_index,
)
from ..rag.config import ANSWER_MODEL, ANSWER_NUM_PREDICT, INTENT_MODEL, INTENT_NUM_PREDICT
from ..rag.llm import call_ollama


FOLLOWUP_TERMS = ("이거", "이것", "그거", "앞에서", "방금", "이전", "계속", "그 다음")


class ApplicationAgentState(TypedDict, total=False):
    query: str
    user_id: str | None
    chat_history: list[dict[str, Any]]
    top_k: int
    refresh_index: bool
    history_summary: str
    retrieval_query: str
    intent: dict[str, Any]
    retrieval: dict[str, Any]
    result: dict[str, Any]
    trace: list[dict[str, Any]]


def _trace(state: ApplicationAgentState, node: str, status: str, **extra: Any) -> list[dict[str, Any]]:
    trace = list(state.get("trace", []))
    item = {"node": node, "status": status, "at": datetime.now().isoformat(timespec="seconds")}
    item.update({key: value for key, value in extra.items() if value is not None})
    trace.append(item)
    return trace


def resolve_application_history(state: ApplicationAgentState) -> ApplicationAgentState:
    history = [item for item in state.get("chat_history") or [] if isinstance(item, dict)][-4:]
    parts = []
    for item in history:
        question = item.get("question") or item.get("query") or item.get("user")
        answer = item.get("answer") or item.get("assistant")
        if question:
            parts.append(f"Q: {question}")
        if answer:
            parts.append(f"A: {str(answer)[:500]}")
    history_summary = "\n".join(parts)
    query = state.get("query", "")
    retrieval_query = f"{history_summary}\n현재 질문: {query}" if history_summary and any(term in query for term in FOLLOWUP_TERMS) else query
    return {
        **state,
        "history_summary": history_summary,
        "retrieval_query": retrieval_query,
        "trace": _trace(state, "resolve_application_history", "success", history_count=len(history)),
    }


def _rule_application_intent(query: str) -> dict[str, Any]:
    text = query.lower()
    if any(term in text for term in ["거절", "의견제출", "보정", "통지서", "불복", "심판"]):
        intent = "rejection_response"
        source_plan = ["notice_forms", "examination_standard", "appeal"]
    elif any(term in text for term in ["선행기술", "kipris", "검색", "cpc", "ipc", "유사"]):
        intent = "prior_art_search"
        source_plan = ["kipris", "classification", "search_workflow"]
    elif any(term in text for term in ["명세서", "청구항", "청구범위", "작성", "권리범위"]):
        intent = "drafting_claims"
        source_plan = ["application_guide", "examination_standard", "strategy"]
    elif any(term in text for term in ["수수료", "비용", "감면", "등록료", "심사청구료"]):
        intent = "fees"
        source_plan = ["fee_guide", "official_forms"]
    elif any(term in text for term in ["서식", "특허고객번호", "인증서", "전자출원", "제출"]):
        intent = "forms_and_filing"
        source_plan = ["patent_customer_number", "certificate", "filing_forms"]
    elif any(term in text for term in ["전략", "사업화", "해외", "우선심사", "심사유예"]):
        intent = "application_strategy"
        source_plan = ["strategy", "examination_timing", "publication"]
    else:
        intent = "application_procedure"
        source_plan = ["application_guide", "process_checklist", "official_pack"]

    needs_table = any(term in text for term in ["표", "비교", "체크리스트", "단계", "정리"])
    needs_diagram = any(term in text for term in ["다이어그램", "흐름", "프로세스", "순서"])
    if needs_table and needs_diagram:
        answer_format = "table_and_diagram"
    elif needs_table:
        answer_format = "checklist_table"
    elif needs_diagram:
        answer_format = "diagram"
    else:
        answer_format = "guided_answer"
    return {
        "intent": intent,
        "source_plan": source_plan,
        "answer_format": answer_format,
        "needs_table": needs_table,
        "needs_diagram": needs_diagram,
        "method": "rule",
    }


def route_application_question(state: ApplicationAgentState) -> ApplicationAgentState:
    fallback = _rule_application_intent(state.get("query", ""))
    prompt = f"""You are a lightweight intent router for a Korean patent filing assistant.
Return JSON only with keys: intent, source_plan, answer_format, needs_table, needs_diagram.
Allowed intents: application_procedure, forms_and_filing, drafting_claims, prior_art_search, rejection_response, fees, application_strategy.
Question: {state.get("query", "")}
"""
    llm = call_ollama(prompt, model=INTENT_MODEL, num_predict=INTENT_NUM_PREDICT)
    intent = dict(fallback)
    if llm.get("ok"):
        match = re.search(r"\{.*\}", str(llm.get("text") or ""), flags=re.S)
        if match:
            try:
                parsed = json.loads(match.group(0))
                intent.update(
                    {
                        "intent": parsed.get("intent") or intent["intent"],
                        "source_plan": parsed.get("source_plan") or intent["source_plan"],
                        "answer_format": parsed.get("answer_format") or intent["answer_format"],
                        "needs_table": bool(parsed.get("needs_table", intent["needs_table"])),
                        "needs_diagram": bool(parsed.get("needs_diagram", intent["needs_diagram"])),
                        "method": "llm",
                    }
                )
            except json.JSONDecodeError:
                intent["llm_raw"] = str(llm.get("text") or "")[:400]
        else:
            intent["llm_raw"] = str(llm.get("text") or "")[:400]
    else:
        intent["llm_error"] = llm.get("error")
    return {**state, "intent": intent, "trace": _trace(state, "route_application_question", "success", intent=intent)}


def retrieve_application_context(state: ApplicationAgentState) -> ApplicationAgentState:
    if state.get("refresh_index"):
        refresh_application_index(force=True)
    status = application_index_status()
    if not status.get("index_exists"):
        refresh_application_index(force=True)
    top_k = int(state.get("top_k") or 6)
    intent = state.get("intent") or {}
    preferred_terms = _intent_preference_terms(str(intent.get("intent") or "application_procedure"))
    expanded_query = " ".join(
        [
            state.get("retrieval_query") or state.get("query", ""),
            " ".join(preferred_terms),
        ]
    )
    retrieval = search_application_index(expanded_query, top_k=max(top_k * 5, 20))
    merged_hits = _dedupe_hits(
        [*preferred_application_hits(preferred_terms, top_k=top_k * 2), *list(retrieval.get("hits") or [])]
    )
    hits = _rerank_hits_for_intent(merged_hits, intent)[:top_k]
    retrieval["hits"] = hits
    retrieval["hit_count"] = len(hits)
    retrieval["reranked_for_intent"] = (state.get("intent") or {}).get("intent")
    return {
        **state,
        "retrieval": retrieval,
        "trace": _trace(
            state,
            "retrieve_application_context",
            "success",
            hit_count=retrieval.get("hit_count", 0),
            mode=retrieval.get("mode"),
        ),
    }


def _intent_preference_terms(intent: str) -> list[str]:
    preferences = {
        "application_procedure": ["patent_application_process_guide", "official_sources", "SRC-001", "SRC-016", "출원가이드", "출원 절차"],
        "forms_and_filing": ["SRC-002", "SRC-003", "SRC-021", "특허고객번호", "인증서", "서식"],
        "drafting_claims": ["SRC-006", "SRC-017", "명세서", "청구항", "청구범위", "심사기준"],
        "prior_art_search": ["prior_art_search_workflow", "SRC-012", "SRC-013", "SRC-014", "KIPRIS", "CPC", "IPC"],
        "rejection_response": ["patent_rejection", "SRC-020", "SRC-021", "거절", "의견제출", "보정", "심판"],
        "fees": ["SRC-004", "SRC-010", "수수료", "등록료", "심사청구료", "감면"],
        "application_strategy": ["SRC-017", "SRC-019", "전략", "우선심사", "해외", "사업화"],
    }
    return preferences.get(intent, preferences["application_procedure"])


def _dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped = []
    for hit in hits:
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        key = f"{metadata.get('source_path')}:{metadata.get('chunk_index')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(hit)
    return deduped


def _rerank_hits_for_intent(hits: list[dict[str, Any]], intent: dict[str, Any]) -> list[dict[str, Any]]:
    terms = _intent_preference_terms(str(intent.get("intent") or "application_procedure"))

    def score(hit: dict[str, Any]) -> float:
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        haystack = " ".join(
            [
                str(metadata.get("file_name") or ""),
                str(metadata.get("relative_source_path") or ""),
                str(hit.get("page_content") or "")[:1200],
            ]
        ).lower()
        boost = 0.0
        for term in terms:
            if term.lower() in haystack:
                boost += 0.16
        if "download" not in str(metadata.get("relative_source_path") or "").lower():
            boost += 0.08
        return float(hit.get("score") or 0.0) + boost

    return sorted(hits, key=score, reverse=True)


def _context_for_prompt(hits: list[dict[str, Any]]) -> str:
    lines = []
    for index, hit in enumerate(hits, 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        lines.append(
            f"[A{index}] {metadata.get('file_name')} / {metadata.get('source_type')} / score={hit.get('score')}\n"
            f"{str(hit.get('page_content') or '')[:1400]}"
        )
    return "\n\n".join(lines) if lines else "No application official context found."


def _fallback_application_answer(query: str, intent: dict[str, Any], hits: list[dict[str, Any]]) -> str:
    intent_name = str(intent.get("intent") or "application_procedure")
    source_names = []
    for hit in hits:
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        name = metadata.get("file_name")
        if name and name not in source_names:
            source_names.append(str(name))
    source_line = ", ".join(source_names[:5]) or "공식 출원 자료팩"

    templates = {
        "application_procedure": [
            ("발명 정리", "해결하려는 문제, 핵심 구성, 효과, 적용 제품/서비스를 먼저 한 문장씩 정리합니다."),
            ("선행기술 검색", "KIPRIS와 CPC/IPC 키워드로 유사 특허를 찾고 차별점을 표시합니다."),
            ("출원 준비", "특허고객번호, 인증서, 출원인 정보, 명세서, 청구범위, 요약서, 도면을 준비합니다."),
            ("전자출원/수수료", "특허로에서 서류를 제출하고 출원료를 납부합니다."),
            ("심사청구", "출원 후 심사청구 여부와 시점을 정하고, 거절이유가 오면 의견서/보정서로 대응합니다."),
            ("등록", "특허결정 후 등록료를 납부하고 권리 유지 일정을 관리합니다."),
        ],
        "prior_art_search": [
            ("키워드 확장", "발명의 목적, 구성, 효과, 동의어, 영문 키워드를 나눠 검색식을 만듭니다."),
            ("분류 검색", "IPC/CPC를 함께 사용해 키워드 누락을 줄입니다."),
            ("유사문헌 선별", "청구항 구성요소와 가장 가까운 문헌을 우선순위로 둡니다."),
            ("차별점 정리", "신규성/진보성 주장에 쓸 차이를 표로 남깁니다."),
        ],
        "drafting_claims": [
            ("핵심 구성 추출", "발명의 필수 구성과 선택 구성을 분리합니다."),
            ("독립항 작성", "필수 구성만으로 넓게 쓰고, 효과가 드러나게 연결합니다."),
            ("종속항 작성", "구체 실시예, 재료, 수치범위, 동작 조건을 단계적으로 좁힙니다."),
            ("명세서 보강", "문제, 해결수단, 효과, 실시예, 변형예를 청구항과 맞춰 씁니다."),
        ],
        "rejection_response": [
            ("통지서 해석", "거절되는 청구항, 인용문헌, 거절유형, 제출기한을 먼저 분리합니다."),
            ("대응 방향 선택", "신규성/진보성은 차이점과 효과를 주장하고, 기재불비는 명세서/청구항을 보정합니다."),
            ("보정안 검토", "신규사항 추가 금지와 권리범위 축소 위험을 확인합니다."),
            ("의견서 제출", "주장 근거와 보정 전후 대비를 함께 제출합니다."),
            ("불복 검토", "최종 거절이면 거절결정불복심판과 비용/기한을 검토합니다."),
        ],
        "fees": [
            ("출원료", "출원 종류, 청구항 수, 전자/서면 여부를 기준으로 확인합니다."),
            ("심사청구료", "심사청구 시점과 청구항 수에 따라 별도로 계산합니다."),
            ("감면", "개인, 중소기업, 연구기관 등 감면 대상과 증빙서류를 확인합니다."),
            ("등록료", "특허결정 후 설정등록료와 이후 연차료 일정을 관리합니다."),
        ],
        "forms_and_filing": [
            ("특허고객번호", "출원인/대리인 식별을 위해 먼저 발급합니다."),
            ("인증서 등록", "전자출원 전 공동인증서 사용등록을 완료합니다."),
            ("서식 작성", "출원서, 명세서, 청구범위, 요약서, 도면, 위임장 등 필요 서식을 확인합니다."),
            ("제출 확인", "접수번호, 수수료 납부, 보정요구 통지를 확인합니다."),
        ],
        "application_strategy": [
            ("권리화 목적", "방어, 라이선스, 투자, 제품 보호 중 목적을 정합니다."),
            ("청구범위 전략", "넓은 독립항과 방어용 종속항을 함께 설계합니다."),
            ("심사 전략", "우선심사, 심사유예, 해외출원 우선권 일정을 검토합니다."),
            ("사업화 연결", "제품 출시, 논문 공개, 전시 공개 전에 출원 일정을 맞춥니다."),
        ],
    }
    steps = templates.get(intent_name, templates["application_procedure"])
    lines = [
        f"## 답변 방향: {intent_name}",
        "",
        "공식팩에서 찾은 근거를 기준으로 실행 순서 중심으로 정리했습니다.",
        "",
    ]
    if intent.get("answer_format") in {"checklist_table", "table_and_diagram"}:
        lines.extend(["| 확인 항목 | 해야 할 일 | 근거 |", "| --- | --- | --- |"])
        for title, action in steps:
            lines.append(f"| {title} | {action} | {source_line} |")
    else:
        for index, (title, action) in enumerate(steps, 1):
            lines.append(f"{index}. **{title}**: {action}")
    lines.extend(["", f"확인한 공식 자료: {source_line}"])
    if intent.get("needs_diagram") or intent.get("answer_format") == "table_and_diagram":
        lines.extend(
            [
                "",
                "```mermaid",
                "flowchart LR",
                "  A[발명 정리] --> B[선행기술 검색]",
                "  B --> C[명세서/청구항 작성]",
                "  C --> D[전자출원/수수료]",
                "  D --> E[심사청구/거절 대응]",
                "```",
            ]
        )
    return "\n".join(lines)


def answer_application_question(state: ApplicationAgentState) -> ApplicationAgentState:
    retrieval = state.get("retrieval") or {}
    hits = list(retrieval.get("hits") or [])
    intent = state.get("intent") or {}
    prompt = f"""당신은 한국 특허 출원을 도와주는 챗봇입니다.
반드시 제공된 공식팩 근거 안에서 답하고, 부족한 부분은 추가 확인이 필요하다고 말하세요.
질문 의도: {intent}
사용자 질문: {state.get("query", "")}
최근 대화:
{state.get("history_summary") or "-"}

공식팩 근거:
{_context_for_prompt(hits)}

답변 요구:
- 한국어로 구체적인 실행 순서를 제시합니다.
- 출원 절차, 거절 대응, 선행기술 검색, 서식/수수료 중 의도에 맞는 항목을 우선합니다.
- 표가 필요하면 Markdown 표를 포함합니다.
- 다이어그램이 필요하면 Mermaid flowchart를 포함합니다.
- 마지막에는 확인해야 할 공식 자료명을 짧게 적습니다.
"""
    llm = call_ollama(prompt, model=ANSWER_MODEL, num_predict=ANSWER_NUM_PREDICT)
    answer = llm.get("text") if llm.get("ok") else _fallback_application_answer(state.get("query", ""), intent, hits)
    result = {
        "query": state.get("query", ""),
        "patent_id": "patent_application",
        "answer": str(answer or ""),
        "source_cards": cards_from_application_hits(hits, query=state.get("query", "")),
        "metrics": {
            "engine": "patent_application_langgraph",
            "intent_agent": intent,
            "hit_count": retrieval.get("hit_count", 0),
            "llm_ok": bool(llm.get("ok")),
            "llm_error": llm.get("error"),
            "answer_format_plan": intent.get("answer_format"),
            "source_plan": intent.get("source_plan"),
        },
    }
    return {
        **state,
        "result": result,
        "trace": _trace(state, "answer_application_question", "success", source_count=len(result["source_cards"])),
    }


def finish_application_answer(state: ApplicationAgentState) -> ApplicationAgentState:
    result = dict(state.get("result") or {})
    metrics = dict(result.get("metrics") or {})
    trace = _trace(state, "finish_application_answer", "success")
    metrics["agent_trace"] = trace
    metrics["application_workflow"] = "history -> intent_router -> official_pack_retrieval -> guided_answer"
    metrics["answer_has_diagram"] = "```mermaid" in str(result.get("answer") or "")
    result["metrics"] = metrics
    return {**state, "result": result, "trace": trace}


def _sequential(state: ApplicationAgentState) -> ApplicationAgentState:
    state = resolve_application_history(state)
    state = route_application_question(state)
    state = retrieve_application_context(state)
    state = answer_application_question(state)
    return finish_application_answer(state)


def build_application_graph() -> Any:
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(ApplicationAgentState)
        graph.add_node("resolve_application_history", resolve_application_history)
        graph.add_node("route_application_question", route_application_question)
        graph.add_node("retrieve_application_context", retrieve_application_context)
        graph.add_node("answer_application_question", answer_application_question)
        graph.add_node("finish_application_answer", finish_application_answer)
        graph.set_entry_point("resolve_application_history")
        graph.add_edge("resolve_application_history", "route_application_question")
        graph.add_edge("route_application_question", "retrieve_application_context")
        graph.add_edge("retrieve_application_context", "answer_application_question")
        graph.add_edge("answer_application_question", "finish_application_answer")
        graph.add_edge("finish_application_answer", END)
        return graph.compile()
    except Exception:
        return None


APPLICATION_GRAPH = build_application_graph()


def run_application_agent(
    query: str,
    *,
    user_id: str | None = None,
    chat_history: list[dict[str, Any]] | None = None,
    top_k: int = 6,
    refresh_index: bool = False,
) -> dict[str, Any]:
    state: ApplicationAgentState = {
        "query": query,
        "user_id": user_id,
        "chat_history": chat_history or [],
        "top_k": top_k,
        "refresh_index": refresh_index,
        "trace": [],
    }
    final_state = APPLICATION_GRAPH.invoke(state) if APPLICATION_GRAPH is not None else _sequential(state)
    return dict(final_state.get("result") or {})


def application_graph_mermaid() -> str:
    if APPLICATION_GRAPH is not None:
        try:
            return APPLICATION_GRAPH.get_graph().draw_mermaid()
        except Exception:
            pass
    return """flowchart TD
  A[Patent Application Chat Request] --> B[resolve_application_history]
  B --> C[route_application_question / lightweight LLM intent]
  C --> D[retrieve_application_context / official pack vectorstore]
  D --> E[answer_application_question]
  E --> F[finish_application_answer]
  F --> G[Answer + source cards + metrics]
"""
