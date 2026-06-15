"""Patent chatbot RAG pipeline with intent, retrieval, web evidence, and LLM generation."""

from __future__ import annotations

import re
from typing import Any

from ..prompts import ANSWER_PROMPT
from .answer_utils import build_metrics, fallback_answer
from .config import ANSWER_LLM_TIMEOUT, ANSWER_MODEL, ANSWER_NUM_PREDICT, ANSWER_PROVIDER, ENABLE_QUERY_EXPANSION, ENABLE_RERANK
from .llm import call_ollama, call_openai_prompt
from .policy import classify_intent
from .quality import filter_usable_hits
from .retrieval import retrieve_local
from .sources import cards_from_hits, cards_from_web
from .text import format_hits_for_prompt
from .web_answers import search_web


def _format_web_for_prompt(results: list[dict[str, Any]]) -> str:
    if not results:
        return "No web evidence."
    lines = []
    for index, item in enumerate(results[:4], 1):
        lines.append(f"[W{index}] {item.get('title')}\n{item.get('snippet')}\n{item.get('url') or ''}")
    return "\n\n".join(lines)


_DETAIL_TERMS = ("자세하게", "자세히", "상세하게", "설명해줘", "알려줘", "보여줘", "설명해", "분석해", "풀어서")
_DEEP_DETAIL_TERMS = ("더 자세하게", "자세하게", "자세히", "상세하게", "구체적으로", "깊게", "분석해줘", "분석해", "전체적으로")
_BRIEF_TERMS = ("핵심만", "간단히", "짧게", "요약만", "한줄", "한 줄", "세 줄", "3줄")
# 단순 사실 확인 질문 → 반드시 1-2문장 brief 처리
_FACTUAL_TERMS = (
    # 수치/점수 질문
    "얼마인가", "얼마입니", "얼마나", "몇 개", "몇개", "몇 항", "몇가지", "몇 가지", "몇 점",
    # 인물/기관 질문
    "누구인가", "누구입니", "누가", "누구로",
    # 시간/장소 질문
    "언제인가", "언제입니", "어디인가", "어디입니", "어디에",
    # 메타데이터 질문
    "법적 상태", "출원인은", "발명명은", "출원일은", "등록일은", "상태는 무", "상태가 무",
    # 정의/식별 질문 (무엇인가, 무엇입니까 등)
    "무엇인가요", "무엇입니까", "무엇인지", "무엇으로",
    # 어떤 X인가 패턴
    "어떤 X인", "어떤가요", "어떠한가요", "어떤지",
    # 짧은 사실 확인 패턴
    "이름은", "이름이", "속한 분야", "속하는", "속한 산업", "몇 점인", "몇점인",
    "적용 분야", "산업군은", "섹터는", "카테고리는",
)
_TABLE_QUERY_TERMS = ("표로", "정리해줘", "표 정리", "비교해줘", "비교 분석")
_BULLET_QUERY_TERMS = ("목록", "청구항", "항목별", "핵심만", "리스트")
_DIAGRAM_QUERY_TERMS = ("다이어그램", "흐름도", "구조도", "flowchart", "흐름을")
_CHART_QUERY_TERMS = ("그래프", "차트", "도표", "추이", "비율", "분포", "성장률", "연도별")
_KNOWN_SECTION_HEADINGS = {
    "특허의 기본 정보 및 출원·등록 현황",
    "특허 기본 정보",
    "기술적 배경 및 해결하려는 문제",
    "기술적 배경 및 해결 과제",
    "기술적 배경",
    "해결하려는 문제",
    "핵심 구성 및 동작 방식",
    "시각화 및 비교 단계",
    "청구항 및 권리 범위",
    "주요 청구항 및 권리 범위",
    "기술적·사업적 평가 및 시장성",
    "평가 보고서 관점 및 시장성",
    "평가 결과 요약",
    "활용 포인트 및 리스크",
    "리스크 및 활용 포인트",
    "종합 의견",
    "한 줄 요약",
}


def _answer_depth(intent: dict[str, Any], *, query: str = "", patent_id: str | None = None) -> str:
    """Return brief | standard | detailed | deep for answer generation."""
    q = query.lower()
    intent_type = str(intent.get("intent") or "")
    explicitly_brief = any(term in q for term in _BRIEF_TERMS)
    explicitly_deep = any(term in q for term in _DEEP_DETAIL_TERMS)
    selected_patent_briefing = bool(
        patent_id
        and any(term in q for term in ("이 특허", "해당 특허", "그 특허", "특허에 대해서", "특허를"))
        and not explicitly_brief
    )
    if explicitly_brief and not explicitly_deep:
        return "brief"
    if selected_patent_briefing or (patent_id and explicitly_deep):
        return "deep"
    if intent_type in {"patent_report", "comparison"}:
        return "detailed"
    if intent_type == "patent_original":
        return "detailed"
    if intent.get("needs_table") or intent.get("needs_diagram"):
        return "detailed"
    if explicitly_deep:
        return "detailed"
    return "standard"


def _effective_top_k(requested_top_k: int, *, answer_depth: str) -> int:
    if answer_depth == "deep":
        return max(requested_top_k, 10)
    if answer_depth == "detailed":
        return max(requested_top_k, 8)
    if answer_depth == "standard":
        return max(requested_top_k, 6)
    return requested_top_k


def _looks_like_section_heading(line: str) -> bool:
    text = line.strip().strip("*")
    if text in _KNOWN_SECTION_HEADINGS:
        return True
    numbered = text
    if len(text) >= 4 and text[0].isdigit() and ". " in text[:5]:
        numbered = text.split(". ", 1)[1].strip()
    if numbered in _KNOWN_SECTION_HEADINGS:
        return True
    if len(numbered) > 34:
        return False
    if numbered.endswith((".", "다", "요", "니다", "음", ":", ";")):
        return False
    heading_terms = ("정보", "배경", "문제", "구성", "방식", "단계", "청구항", "권리", "평가", "시장성", "리스크", "포인트", "요약")
    return any(term in numbered for term in heading_terms)


def _format_answer_readably(answer: str, intent: dict[str, Any], *, answer_depth: str) -> str:
    """Normalize long model answers into UI-friendly Markdown."""
    text = str(answer or "").strip()
    if not text:
        return text
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    out: list[str] = []
    in_code = False
    for raw in lines:
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            out.append(raw)
            continue
        if in_code:
            out.append(raw)
            continue
        if not line:
            if out and out[-1] != "":
                out.append("")
            continue
        if line.startswith(("# ", "## ", "### ", "- ", "* ")) or line.startswith("|") or line.startswith(">"):
            out.append(line)
            continue
        if _looks_like_section_heading(line):
            heading = line
            if len(heading) >= 4 and heading[0].isdigit() and ". " in heading[:5]:
                heading = heading.split(". ", 1)[1].strip()
            if out and out[-1] != "":
                out.append("")
            out.append(f"## {heading}")
            out.append("")
            continue
        out.append(line)

    normalized = "\n".join(out).strip()
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    if answer_depth in {"deep", "detailed"} and "## " not in normalized:
        title = "상세 분석" if str(intent.get("intent") or "") != "patent_report" else "평가 분석"
        normalized = f"## {title}\n\n{normalized}"
    return normalized


def _build_format_instruction(
    intent: dict[str, Any],
    *,
    query: str = "",
    patent_id: str | None = None,
    answer_depth: str = "standard",
) -> str:
    """intent + query + patent_id 컨텍스트로 LLM 출력 포맷 지시문을 생성한다."""
    # brief 모드: 무조건 1-2문장 직접 답변 — 다른 포맷 지시 무시
    if answer_depth == "brief":
        return (
            "1-2문장으로 핵심 사실만 직접 답합니다. "
            "표·다이어그램·섹션 제목(##) 없이, "
            "질문에서 묻는 값·이름·상태·이유를 바로 서술합니다. "
            "근거 번호([1] 등) 생략 가능."
        )

    fmt = str(intent.get("answer_format") or "text").lower()
    needs_table = bool(intent.get("needs_table"))
    needs_diagram = bool(intent.get("needs_diagram"))
    focus = str(intent.get("focus") or "")
    intent_type = str(intent.get("intent") or "")
    q = query.lower()

    # 쿼리 키워드로 포맷 재보정 (LLM 분류보다 명시적 지시 우선)
    if any(t in q for t in _TABLE_QUERY_TERMS):
        fmt, needs_table = "table", True
    if any(t in q for t in _DIAGRAM_QUERY_TERMS):
        fmt, needs_diagram = "diagram", True
    if any(t in q for t in _CHART_QUERY_TERMS):
        fmt = "visual_summary" if needs_table or needs_diagram else "chart"
    if any(t in q for t in _BULLET_QUERY_TERMS) and not needs_table:
        fmt = "bullets"

    parts: list[str] = []

    if fmt == "visual_summary":
        parts.append(
            "답변에 가장 실용적인 시각 자료를 1-2개 선택하세요. "
            "점수·리스크·비교는 Markdown 표를 우선 사용하고, 수치 분포/연도별 추이는 Mermaid pie 또는 xychart를 사용하세요. "
            "절차·구조·데이터 흐름은 Mermaid flowchart를 사용하세요. "
            "위험도/실행 난이도처럼 2축 판단은 Mermaid quadrantChart 또는 2x2 표를 사용하세요."
        )
    elif fmt == "chart":
        parts.append(
            "근거에 실제 수치가 있으면 Mermaid 차트를 포함하세요. "
            "비율/점수 분포는 pie, 연도별 추이는 xychart를 사용하세요. "
            "수치가 부족하면 차트를 만들지 말고 Markdown 표로 대체하세요."
        )
    elif fmt == "table_and_diagram" or (needs_table and needs_diagram):
        parts.append("Markdown 표와 Mermaid flowchart 다이어그램을 순서대로 모두 포함하세요.")
    elif fmt == "table" or needs_table:
        parts.append(
            "반드시 Markdown 표(| 항목 | 내용 | 근거 |) 형식으로 정리하세요. "
            "표 아래 실무 권고 1-2줄을 추가하세요."
        )
    elif fmt == "diagram" or needs_diagram:
        parts.append(
            "기술 흐름·시스템 구성을 ```mermaid\\nflowchart TD\\n ... \\n``` 형식으로 표현하세요. "
            "블록 수는 5-8개로 유지하세요. "
            "노드 라벨에 소괄호 ( ) 는 절대 사용하지 마세요 — Mermaid 파싱 오류가 발생합니다. "
            "소괄호가 필요하면 대괄호 [ ] 로 감싸거나 생략하세요. "
            "예: 결함 이미지 생성[제1 생성단계] 또는 결함 이미지 생성_제1"
        )
    elif fmt == "bullets":
        parts.append("핵심 항목을 번호 목록(1. 2. 3.) 또는 불릿(- )으로 구조화해 나열하세요.")

    # 포맷 지시가 없으면 intent + 컨텍스트 기반 기본 구조 적용
    if not parts:
        if intent_type == "patent_report":
            parts.append(
                "평가 항목(권리성·시장성·사업성) → 점수 → 판단 근거 순으로 "
                "Markdown 표로 정리하고, 종합 의견과 리스크 해석을 추가하세요."
            )
        elif intent_type == "comparison":
            parts.append("비교 항목을 Markdown 표로 나란히 정리하세요.")
        elif intent_type == "patent_original" or (
            patent_id and any(t in q for t in _DETAIL_TERMS + ("이 특허", "특허를"))
        ):
            # 특허가 선택된 상태에서 상세/설명 요청 → 구조화 불릿
            parts.append(
                "다음 Markdown 섹션 구조를 사용해 구체적으로 답변하세요: "
                "## 한 줄 요약 → ## 특허 기본 정보 → ## 기술적 배경과 해결 과제 → "
                "## 핵심 구성과 동작 방식 → ## 청구항과 권리 범위 → ## 평가와 리스크 → ## 활용 포인트."
            )
        elif any(t in q for t in _DETAIL_TERMS):
            parts.append(
                "주요 항목을 번호 목록(1. 2. 3.)으로 나누어 각 항목을 2-3문장으로 설명하세요."
            )
        else:
            parts.append("핵심 결론을 먼저 말하고, 근거가 있는 항목을 3-5개로 나누어 답변하세요.")

    if answer_depth == "brief":
        parts.append(
            "답변 길이: 1-2문장으로 핵심 사실만 직접 답합니다. "
            "표·다이어그램·섹션 제목 없이, 구어체 없이, 질문에서 묻는 값·이름·상태를 바로 서술합니다."
        )
    elif answer_depth == "deep":
        parts.append(
            "답변 길이: 상세 분석 모드입니다. 짧게 요약하지 말고 최소 6개 섹션으로 충분히 설명하세요. "
            "각 섹션 제목은 반드시 `##`로 시작하고, 섹션마다 2-4문장으로 작성하세요. "
            "근거에 있는 수치·날짜·출원인·등록번호·평가점수·청구항 정보를 적극 활용하되, 질문과 직접 관련 없는 메타정보는 줄이세요."
        )
    elif answer_depth == "detailed":
        parts.append(
            "답변 길이: 상세 답변 모드입니다. 최소 4개 항목으로 나누고 각 항목을 2문장 이상 설명하세요."
        )
    else:
        parts.append(
            "답변 길이: 질문에 직접 관련된 핵심 사실을 3-5문장으로 답합니다. "
            "근거 범위 내에서 간결하게 정리하되, 질문과 관계없는 배경 설명은 생략합니다."
        )

    parts.append(
        "시각화 자유도: 표·다이어그램·차트는 질문 이해에 도움이 될 때만 자연스럽게 사용하세요. "
        "시각 자료를 넣었다면 바로 아래에 '해석:' 문장으로 무엇을 봐야 하는지 설명하세요."
    )

    return " ".join(parts)


def _source_type(card: dict[str, Any]) -> str:
    metadata = card.get("metadata") if isinstance(card.get("metadata"), dict) else {}
    return str(card.get("source_type") or metadata.get("source_type") or "").upper()


def _hybrid_result_allowed(
    result: dict[str, Any],
    *,
    source_types: set[str] | None,
    allow_web: bool,
    intent: dict[str, Any],
) -> tuple[bool, str | None]:
    # 특수 모드는 source_cards 없어도 통과: 명확화, 웹검색, 특허 검색, 선택 등
    answer_mode = str(result.get("metrics", {}).get("answer_mode") or "")
    _passthrough_modes = {
        "GLOBAL_CLARIFY", "GLOBAL_WEB_SEARCH", "ASK_CLARIFICATION",
        "PATENT_SELECTION", "GLOBAL_PATENT_DISCOVERY",
        "GLOBAL_PATENT_EVALUATION", "GLOBAL_CLARIFY_AMBIGUOUS",
        "GLOBAL_DEFINITION",
    }
    if answer_mode in _passthrough_modes:
        return True, None
    if not source_types:
        return True, None
    allowed = {item.upper() for item in source_types}
    if allow_web and intent.get("needs_web"):
        allowed.add("WEB")
    cards = [card for card in result.get("source_cards") or [] if isinstance(card, dict)]
    if not cards:
        return False, "no_source_cards"
    blocked = sorted({_source_type(card) or "UNKNOWN" for card in cards if (_source_type(card) or "UNKNOWN") not in allowed})
    if blocked:
        return False, f"blocked_source_types={','.join(blocked)}"
    return True, None


def answer_question(
    query: str,
    *,
    retrieval_query: str | None = None,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    top_k: int = 5,
    allow_web: bool = True,
    intent_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hybrid_retrieval_error: str | None = None
    hybrid_retrieval_rejected: str | None = None
    # 리트리벌에는 컨텍스트가 풍부한 retrieval_query를, LLM 프롬프트에는 원본 query를 사용
    search_query = retrieval_query or query
    intent = intent_override or classify_intent(query, selected_patent_id=patent_id)
    if patent_id and intent.get("needs_clarification"):
        intent = {
            **intent,
            "needs_clarification": False,
            "clarification_question": "",
            "search_scope": "internal",
            "reason": f"{intent.get('reason', '')} / patent_id provided by request",
        }
    if intent.get("needs_clarification"):
        question = str(intent.get("clarification_question") or "어떤 특허나 데이터 범위를 기준으로 답할까요?")
        return {
            "query": query,
            "patent_id": patent_id,
            "answer": question,
            "source_cards": [],
            "metrics": {
                "engine": "clarification_router",
                "intent_agent": intent,
                "answer_mode": "ASK_CLARIFICATION",
                "search_pass": False,
                "fallback_required": False,
            },
        }
    internal_only = intent.get("search_scope") == "internal" or (
        not intent.get("needs_web") and "web" not in set(intent.get("source_plan") or [])
    )
    # Qdrant is the single vector backend; compatibility adapters are not used
    # in the answer path.

    answer_depth = _answer_depth(intent, query=query, patent_id=patent_id)
    effective_top_k = _effective_top_k(top_k, answer_depth=answer_depth)
    local_result = retrieve_local(
        search_query,
        patent_id=patent_id,
        source_types=source_types,
        top_k=effective_top_k,
        rerank=False,                          # re-rank은 filter 이후에 적용
        use_query_expansion=ENABLE_QUERY_EXPANSION,
    )
    raw_local_hits = list(local_result.get("hits") or [])
    local_hits = filter_usable_hits(raw_local_hits, limit=effective_top_k)

    # Re-rank: filter_usable_hits 통과한 청크에만 적용
    if ENABLE_RERANK and local_hits:
        try:
            from ..reranker import rerank_hits
            local_hits = rerank_hits(search_query, local_hits, top_k=effective_top_k)
        except Exception as _e:
            pass  # 실패 시 원래 순서 유지
    local_result = {**local_result, "hits": local_hits, "raw_hit_count": len(raw_local_hits), "hit_count": len(local_hits)}

    needs_web = allow_web and not internal_only and bool(intent.get("needs_web") or len(local_hits) < 2)
    web_result = search_web(query) if needs_web else {"enabled": False, "provider": None, "results": [], "error": None}
    if not allow_web:
        web_result["skipped"] = True
        web_result["skip_reason"] = "disabled_by_agent_policy"
    elif len(local_hits) < 2 and not intent.get("needs_web"):
        web_result["fallback_reason"] = "local_evidence_insufficient"
    web_results = list(web_result.get("results") or [])

    format_instruction = _build_format_instruction(intent, query=query, patent_id=patent_id, answer_depth=answer_depth)
    chars_per_hit = 2400 if answer_depth == "deep" else 1900 if answer_depth == "detailed" else 1500
    prompt = ANSWER_PROMPT.format(
        query=query,
        format_instruction=format_instruction,
        local_context=format_hits_for_prompt(local_hits, limit=effective_top_k, chars_per_hit=chars_per_hit),
        web_context=_format_web_for_prompt(web_results),
    )

    if ANSWER_PROVIDER == "openai":
        llm_result = call_openai_prompt(
            prompt,
            model=ANSWER_MODEL,
            timeout=ANSWER_LLM_TIMEOUT,
            temperature=0.2,
        )
    else:
        # Ollama generate API requires a concrete num_predict. Keep it high for detailed answers.
        max_tokens = max(ANSWER_NUM_PREDICT, 4096 if answer_depth in {"deep", "detailed"} else 2000)
        llm_result = call_ollama(prompt, model=ANSWER_MODEL, num_predict=max_tokens, timeout=ANSWER_LLM_TIMEOUT)
    answer = (
        llm_result["text"]
        if llm_result.get("ok")
        else fallback_answer(query, local_hits=local_hits, web_results=web_results, llm_error=llm_result.get("error"))
    )
    answer = _format_answer_readably(str(answer), intent, answer_depth=answer_depth)
    source_cards = [
        *cards_from_hits(local_hits, query=query),
        *cards_from_web(web_results, start_index=len(local_hits) + 1, query=query),
    ]

    metrics = build_metrics(intent=intent, local_result=local_result, web_result=web_result, llm_result=llm_result, patent_id=patent_id)
    metrics["engine"] = "langgraph_lightweight_fallback"
    metrics["answer_provider"] = ANSWER_PROVIDER
    metrics["answer_depth"] = answer_depth
    metrics["effective_top_k"] = effective_top_k
    if hybrid_retrieval_error:
        metrics["hybrid_retrieval_error"] = hybrid_retrieval_error
    if hybrid_retrieval_rejected:
        metrics["hybrid_retrieval_rejected_reason"] = hybrid_retrieval_rejected

    return {
        "query": query,
        "patent_id": patent_id,
        "answer": answer,
        "source_cards": source_cards,
        "metrics": metrics,
    }
