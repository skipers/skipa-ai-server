"""
RAG 엔진: 검색 + GPT 기반 구조화 사업화 현황 생성.

개선 사항:
  - Query Expansion: LLM이 사용자 질문을 문서 검색에 최적화된 형태로 재작성
  - Multi-Query 병합: 원본 쿼리 + 확장 쿼리 검색 결과를 청크 ID 기준으로 중복 제거 후 병합
  - 사업화 신호 스코어링: 검색 문서에서 8가지 신호 탐지 → LLM 판단 보조
  - commercialization_status 필드: 사업화 여부를 파싱된 구조화 값으로 반환
"""
import json
import re

from .config import LLM_MODEL, TOP_K
from .vector_store import search
from providers.llm import request_json, request_text

# ── 사업화 신호 패턴 ───────────────────────────────────────────────────────────

_COMM_SIGNALS: dict[str, list[str]] = {
    "고객 사례": ["고객 사례", "도입 사례", "고객사", "case study", "도입 기업", "클라이언트"],
    "공식 제품·출시": ["서비스 소개", "제품 소개", "출시", "런칭", "상용", "공식 서비스"],
    "언론·보도": ["보도자료", "뉴스", "언론", "기사", "press release"],
    "파트너십·계약": ["파트너십", "mou", "협약", "제휴", "계약"],
    "가격·문의": ["가격", "요금", "도입 문의", "구매 문의"],
    "수상·인증": ["수상", "인증", "어워드", "award", "certification"],
    "운영 현황": ["운영 중", "서비스 중", "현재 제공"],
    "종료·중단 신호": ["서비스 종료", "중단", "deprecated", "discontinued"],
}


def _score_commercialization(docs: list[dict]) -> dict:
    """
    검색 문서에서 사업화 신호를 탐지하고 점수·요약 반환.

    Returns:
        {
            "score": float,         # 0~1 (0=신호 없음, 1=모든 신호 탐지)
            "detected": list[str],  # 탐지된 신호 범주
            "summary": str          # LLM 프롬프트 삽입용 요약
        }
    """
    combined = " ".join(d["text"] for d in docs).lower()
    detected: list[str] = []

    for category, patterns in _COMM_SIGNALS.items():
        if any(p.lower() in combined for p in patterns):
            detected.append(category)

    has_end = "종료·중단 신호" in detected
    positive = [d for d in detected if d != "종료·중단 신호"]
    score = min(len(positive) / max(len(_COMM_SIGNALS) - 1, 1), 1.0)
    if has_end:
        score = max(score - 0.3, 0.0)

    if not detected:
        summary = "명시적 사업화 신호 없음 — 문서 내용 전반을 근거로 LLM이 직접 판단"
    else:
        summary = f"탐지된 신호: {', '.join(detected)}"

    return {"score": round(score, 3), "detected": detected, "summary": summary}


# ── Query Expansion ───────────────────────────────────────────────────────────

_EXPANSION_SYSTEM = (
    "사용자 질문을 벡터 검색에 최적화된 형태로 재작성하세요. "
    "원본 질문의 핵심 의도를 유지하되, 제품명·기술 용어·동의어를 추가해 검색 범위를 넓히세요. "
    "재작성된 질문 한 문장만 출력하고 다른 설명은 하지 마세요."
)


def _expand_query(query: str) -> str:
    """LLM으로 검색 최적화 쿼리 생성."""
    return request_text(
        system_prompt=_EXPANSION_SYSTEM,
        user_prompt=query,
        model=LLM_MODEL,
        temperature=0.0,
        max_tokens=120,
    )


def _multi_query_retrieve(query: str, top_k: int) -> list[dict]:
    """
    원본 쿼리 + 확장 쿼리로 각각 검색 후 병합.
    같은 청크 ID가 양쪽에서 나오면 높은 점수를 유지.
    최종적으로 점수 내림차순 top_k 반환.
    """
    expanded = _expand_query(query)

    r1 = search(query, top_k=top_k)
    r2 = search(expanded, top_k=top_k) if expanded.lower() != query.lower() else []

    seen: dict[str, dict] = {}
    for doc in r1 + r2:
        cid = doc["id"]
        if cid not in seen or doc["score"] > seen[cid]["score"]:
            seen[cid] = doc

    return sorted(seen.values(), key=lambda d: d["score"], reverse=True)[:top_k]


# ── 프롬프트 ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """당신은 SK AX(SK AI X)의 제품/솔루션 전문가입니다.
제공된 참고 문서와 사업화 신호 분석 결과를 바탕으로 특허 기술의 사내 사업 활용 현황을 평가하세요.

반드시 하나의 JSON 객체만 반환하세요. 마크다운 표를 쓰지 마세요.

응답 형식:
{
  "commercialization_status": "진행 중|진행됨 (과거)|미진행|진행 추정|미진행 추정",
  "applied_business_service": "적용 가능하거나 확인된 사업/서비스. 불확실성을 나타내는 별도 접두어를 붙이지 않음",
  "business_application_history": "시기별 적용 이력 또는 확인 필요 사항",
  "customers_partners": "고객·파트너 또는 추정 고객군",
  "market_outlook": "관련 시장 현황과 전망 2~3문장",
  "summary": "특허 기술 특징, 사내 제조/스마트팩토리 솔루션과의 연결점, 적용 가능 업무, 현재 확인된 사업화 한계, 추가 확인 필요사항을 포함한 4~6문장",
  "commercialization_signals": ["탐지된 신호"]
}

답변 규칙:
1. 현재 기준 연도는 2026년이다. 각 참고문서에는 '문서 작성일'이 명시되어 있다.
2. 사업화 여부는 반드시 지정된 5가지 중 하나로 결정하며 "정보 없음"은 사용하지 않는다.
3. 직접 확인되지 않은 내용도 추정 표기를 접두어로 붙이지 말고, summary에서 문서 근거와 판단 한계를 자연스럽게 설명한다.
4. 모든 문자열 필드는 비워두지 않는다.
5. summary는 너무 짧게 쓰지 말고, 화면 설명 문단으로 바로 사용할 수 있게 350~650자 분량으로 작성한다.
6. 한국어로 답변한다."""


def _build_context(retrieved_docs: list[dict], comm_info: dict) -> str:
    lines = []
    for i, doc in enumerate(retrieved_docs, 1):
        pub = doc.get("published_at") or ""
        date_str = f" | 문서 작성일: {pub}" if pub else " | 문서 작성일: 미확인"
        lines.append(
            f"[참고문서 {i}] 제품: {doc['keyword']} | 출처: {doc['url']}{date_str}\n{doc['text']}"
        )

    signal_block = (
        f"\n\n[사업화 신호 분석]\n"
        f"- 신호 점수: {comm_info['score']} (0=신호 없음, 1=모든 신호 탐지)\n"
        f"- {comm_info['summary']}"
    )
    return "\n\n".join(lines) + signal_block


def _parse_commercialization_status(answer: str) -> str:
    parsed = _parse_answer_json(answer)
    if parsed.get("commercialization_status"):
        return str(parsed["commercialization_status"]).strip()
    match = re.search(r"\|\s*사업화 여부\s*\|\s*(.+?)\s*\|", answer)
    if match:
        return match.group(1).strip()
    return "판단 불가"


def _parse_answer_json(answer: str) -> dict:
    text = answer.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


# ── 메인 API ──────────────────────────────────────────────────────────────────

def ask(query: str, top_k: int = TOP_K) -> dict:
    """
    쿼리에 대해 RAG 기반 답변 반환.

    Returns:
        {
            "query": str,
            "answer": str,
            "sources": list[dict],
            "commercialization_status": str,
            "commercialization_signals": list[str]
        }
    """
    retrieved = _multi_query_retrieve(query, top_k)

    if not retrieved:
        return {
            "query": query,
            "answer": "관련 문서를 찾을 수 없습니다. 크롤링 및 인덱싱을 먼저 실행하세요.",
            "sources": [],
            "commercialization_status": "판단 불가",
            "commercialization_signals": [],
        }

    comm_info = _score_commercialization(retrieved)
    context   = _build_context(retrieved, comm_info)

    structured = request_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"[참고 문서 및 신호 분석]\n{context}\n\n[질문]\n{query}",
        model=LLM_MODEL,
        temperature=0.3,
        max_tokens=1024,
    )
    answer = json.dumps(structured, ensure_ascii=False)

    sources = [
        {
            "rank": i + 1,
            "keyword": d["keyword"],
            "title": d["title"],
            "url": d["url"],
            "score": round(d["score"], 4),
            "chunk_id": d["id"],
        }
        for i, d in enumerate(retrieved)
    ]

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "commercialization_status": structured.get("commercialization_status") or _parse_commercialization_status(answer),
        "applied_business_service": structured.get("applied_business_service") or "",
        "business_application_history": structured.get("business_application_history") or "",
        "customers_partners": structured.get("customers_partners") or "",
        "market_outlook": structured.get("market_outlook") or "",
        "summary": structured.get("summary") or "",
        "commercialization_signals": structured.get("commercialization_signals") or comm_info["detected"],
    }


def print_result(result: dict) -> None:
    print(f"\n{'=' * 70}")
    print(f"[질문] {result['query']}")
    print(f"\n{result['answer']}")

    status  = result.get("commercialization_status", "")
    signals = result.get("commercialization_signals", [])
    if status or signals:
        print(f"\n{'─' * 70}")
        print(f"[사업화 판단] {status}")
        if signals:
            print(f"[탐지 신호]  {', '.join(signals)}")

    print(f"\n{'─' * 70}")
    print("[참조 문서]")
    for s in result["sources"]:
        print(f"  {s['rank']}. [{s['keyword']}] {s['title']}  (유사도={s['score']})")
        print(f"     {s['url']}")
    print("=" * 70)


if __name__ == "__main__":
    sample_queries = [
        "AccuInsight+는 시장에서 어느 위치에 해당해?",
        "Aibril의 미래 시장 전망은 어떻게 돼?",
        "ChainZ의 사업성 및 시장성이 시간에 따라 어떻게 변화했어?",
    ]
    for q in sample_queries:
        result = ask(q)
        print_result(result)
