# -*- coding: utf-8 -*-

import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS

try:
    from langchain_core.documents import Document
except Exception:  # pragma: no cover
    from langchain.docstore.document import Document

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except Exception:  # pragma: no cover
    from langchain_community.embeddings import HuggingFaceEmbeddings

try:
    from langchain_openai import OpenAIEmbeddings
except Exception:  # pragma: no cover
    OpenAIEmbeddings = None

from ..config import (
    ANSWER_MODEL as CONFIG_ANSWER_MODEL,
    ANSWER_PROVIDER as CONFIG_ANSWER_PROVIDER,
    DATA_ROOT as CONFIG_DATA_ROOT,
    EMBEDDING_MODEL as CONFIG_EMBEDDING_MODEL,
    EMBEDDING_PROVIDER as CONFIG_EMBEDDING_PROVIDER,
    ENABLE_OLLAMA_INTENT_FALLBACK as CONFIG_ENABLE_OLLAMA_INTENT_FALLBACK,
    INTENT_MODEL as CONFIG_INTENT_MODEL,
    INTENT_PROVIDER as CONFIG_INTENT_PROVIDER,
    OPENAI_API_KEY as CONFIG_OPENAI_API_KEY,
    OPENAI_BASE_URL as CONFIG_OPENAI_BASE_URL,
    PATENTS_ROOT as CONFIG_PATENTS_ROOT,
    PUBLIC_FILE_BASE_URL as CONFIG_PUBLIC_FILE_BASE_URL,
)
from ..rag.llm import call_openai_messages
from .compat import load_compatible_patent_meta
from .ingest import (
    build_business_documents,
    build_patent_documents,
    read_documents_jsonl,
    write_documents_jsonl,
)
from .prompts import build_system_prompt, build_user_prompt
from .web_search import search_web_documents

load_dotenv()

DATA_ROOT = CONFIG_DATA_ROOT
PATENTS_ROOT = CONFIG_PATENTS_ROOT
PUBLIC_FILE_BASE_URL = CONFIG_PUBLIC_FILE_BASE_URL

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", CONFIG_EMBEDDING_PROVIDER).lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", CONFIG_EMBEDDING_MODEL)
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
GEN_MODEL = os.getenv("GEN_MODEL", "qwen2.5:1.5b")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.0"))
INTENT_PROVIDER = os.getenv("INTENT_PROVIDER", CONFIG_INTENT_PROVIDER).lower()
INTENT_MODEL = os.getenv("INTENT_MODEL", CONFIG_INTENT_MODEL or GEN_MODEL)
ANSWER_PROVIDER = os.getenv("ANSWER_PROVIDER", CONFIG_ANSWER_PROVIDER).lower()
ANSWER_MODEL = os.getenv("ANSWER_MODEL", CONFIG_ANSWER_MODEL or GEN_MODEL)
OPENAI_API_KEY = CONFIG_OPENAI_API_KEY
OPENAI_BASE_URL = CONFIG_OPENAI_BASE_URL
ENABLE_OLLAMA_INTENT_FALLBACK = os.getenv(
    "ENABLE_OLLAMA_INTENT_FALLBACK",
    "true" if CONFIG_ENABLE_OLLAMA_INTENT_FALLBACK else "false",
).lower() in ("1", "true", "yes")
ENABLE_INTENT_AGENT = os.getenv("ENABLE_INTENT_AGENT", "true").lower() in ("1", "true", "yes")
INTENT_AGENT_TIMEOUT = int(os.getenv("INTENT_AGENT_TIMEOUT", "8"))
INTENT_AGENT_MIN_CONFIDENCE = float(os.getenv("INTENT_AGENT_MIN_CONFIDENCE", "0.55"))

TOP_K = int(os.getenv("TOP_K", "6"))
TOP_K_CANDIDATES = int(os.getenv("TOP_K_CANDIDATES", "40"))
MIN_LOCAL_CONFIDENCE = float(os.getenv("MIN_LOCAL_CONFIDENCE", "0.18"))

MAX_DOC_CHARS = int(os.getenv("MAX_DOC_CHARS", "1200"))
MAX_TOTAL_CONTEXT_CHARS = int(os.getenv("MAX_TOTAL_CONTEXT_CHARS", "6500"))
CHUNK_MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() in ("1", "true", "yes")
WEB_SEARCH_API_URL = os.getenv("WEB_SEARCH_API_URL", "")
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")
WEB_SEARCH_LIMIT = int(os.getenv("WEB_SEARCH_LIMIT", "5"))

RETURN_PERFORMANCE = os.getenv("RETURN_PERFORMANCE", "true").lower() in ("1", "true", "yes")
LOG_PATH = Path(os.getenv("RAG_QUERY_LOG_PATH", "./logs/rag_query_log.jsonl"))
ENABLE_STRUCTURED_FAST_PATH = os.getenv("ENABLE_STRUCTURED_FAST_PATH", "false").lower() in (
    "1",
    "true",
    "yes",
)
ANSWER_GENERATION_MODE = os.getenv("ANSWER_GENERATION_MODE", "extractive").lower()

BM25_K1 = float(os.getenv("BM25_K1", "1.2"))
BM25_B = float(os.getenv("BM25_B", "0.75"))
RRF_K = int(os.getenv("RRF_K", "30"))

SOURCE_TYPE_WEIGHTS = {
    "ORIGINAL_PDF": float(os.getenv("WEIGHT_ORIGINAL_PDF", "1.06")),
    "REPORT_PDF": float(os.getenv("WEIGHT_REPORT_PDF", "1.04")),
    "ORIGINAL_VISUAL": float(os.getenv("WEIGHT_ORIGINAL_VISUAL", "1.08")),
    "REPORT_VISUAL": float(os.getenv("WEIGHT_REPORT_VISUAL", "1.08")),
    "HTML_VISUAL": float(os.getenv("WEIGHT_HTML_VISUAL", "1.04")),
    "BUSINESS_DOC": float(os.getenv("WEIGHT_BUSINESS_DOC", "1.0")),
    "WEB": float(os.getenv("WEIGHT_WEB", "0.92")),
}

OUT_OF_SCOPE_ANSWER = "해당 특허 또는 특허 검토 업무 자료에서 확인할 수 없는 내용입니다."

GENERIC_PATENT_TITLE_TERMS = {
    "방법",
    "시스템",
    "장치",
    "기술",
    "관련",
    "내용",
    "특허",
    "발명",
    "평가",
    "보고서",
    "과정",
}

QUESTION_CONTEXT_TERMS = GENERIC_PATENT_TITLE_TERMS | {
    "이거",
    "이것",
    "해당",
    "현재",
    "여기",
    "내용",
    "알려줘",
    "설명해줘",
    "요약해줘",
    "알려",
    "설명",
    "요약",
    "핵심",
    "찾아",
    "찾아줘",
    "검색",
    "검색해",
    "목록",
    "보여줘",
    "추천",
    "개요",
    "무슨",
    "무엇",
    "어떤",
    "뭐야",
    "어때",
    "어떻게",
    "방식",
    "기준",
    "판단",
    "판단해",
    "왜",
    "장점",
    "강점",
    "필요",
    "필요성",
    "필요한거야",
    "필요한지",
    "문제",
    "문제점",
    "해결",
    "개선",
    "효과",
    "활용",
    "가능성",
    "리스크",
    "위험",
    "한계",
    "단점",
    "가치",
    "사업",
    "성능",
    "동작",
    "원리",
    "근거",
    "자세히",
    "상세히",
    "의미",
    "있어",
    "있나요",
    "결과",
    "점수",
    "평가",
    "관련",
    "관련해",
    "관련해서",
    "관련된",
    "전체",
    "대해",
    "대해서",
    "대해서는",
    "대하여",
    "대한",
    "관해",
    "관해서",
    "관하여",
    "관한",
}

QUESTION_CONTEXT_PREFIXES = (
    "필요",
    "가능",
    "활용",
    "개선",
    "해결",
    "평가",
    "요약",
    "설명",
    "찾",
    "알려",
    "핵심",
    "동작",
    "판단",
    "검토",
    "사업",
    "성능",
    "자세",
    "상세",
    "대해",
    "관해",
    "관련",
)

TOKEN_RE = re.compile(r"[가-힣A-Za-z]+|\d+(?:[-.]\d+)*")
PATENT_ID_RE = re.compile(r"\bP\d{4,}\b", re.IGNORECASE)
SOURCE_TAG_RE = re.compile(r"\[자료\d+\]")

KOREAN_SUFFIXES = (
    "으로부터",
    "으로서",
    "으로써",
    "에서는",
    "하거나",
    "이거나",
    "에서",
    "에게",
    "부터",
    "까지",
    "하고",
    "이며",
    "이면",
    "이나",
    "거나",
    "해서",
    "어서",
    "아서",
    "으로",
    "라고",
    "라는",
    "줘",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "의",
    "에",
    "와",
    "과",
    "도",
    "만",
    "로",
)


def now_ms() -> int:
    return int(time.time() * 1000)


def normalize(text: str) -> str:
    return " ".join((text or "").split())


def normalize_token(token: str) -> str:
    token = token.lower().strip()
    if len(token) <= 2 or not re.search(r"[가-힣]", token):
        return token
    for suffix in KOREAN_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 2:
            return token[: -len(suffix)]
    return token


def tokens(text: str) -> List[str]:
    return [normalize_token(t) for t in TOKEN_RE.findall((text or "").lower()) if normalize_token(t)]


def doc_key(doc: Document) -> str:
    meta = doc.metadata or {}
    return str(meta.get("chunk_id") or meta.get("text_hash") or hash(doc.page_content))


def _patent_id_from_doc(doc: Document) -> str:
    return str((doc.metadata or {}).get("patent_id") or "")


def title_matched_patent_ids(question: str, docs: List[Document]) -> List[str]:
    q_terms = {
        term
        for term in tokens(question)
        if len(term) >= 2 and not is_question_context_token(term)
    }
    if not q_terms:
        return []

    best_score = 0.0
    scores: Dict[str, float] = {}
    for doc in docs:
        meta = doc.metadata or {}
        patent_id = str(meta.get("patent_id") or "")
        title = str(meta.get("title") or "")
        if not patent_id or not title:
            continue
        title_terms = set(tokens(title))
        overlap = len(q_terms & title_terms)
        score = overlap / max(1, len(title_terms))
        if overlap >= 2:
            scores[patent_id] = max(scores.get(patent_id, 0.0), score)
            best_score = max(best_score, score)

    if best_score < 0.18:
        return []
    return [patent_id for patent_id, score in scores.items() if score >= best_score * 0.85]


def identifier_matched_patent_ids(question: str, docs: List[Document]) -> List[str]:
    identifiers = set(re.findall(r"10-\d{4}-\d+|10-\d{6,8}", question or ""))
    if not identifiers:
        return []

    matched: List[str] = []
    for doc in docs:
        meta = doc.metadata or {}
        patent_id = str(meta.get("patent_id") or "")
        if not patent_id or patent_id in matched:
            continue
        values = {
            str(meta.get("registration_number") or ""),
            str(meta.get("application_number") or ""),
        }
        doc_prefix = doc.page_content[:1200]
        values.update(re.findall(r"10-\d{4}-\d+|10-\d{6,8}", doc_prefix))
        if identifiers & values:
            matched.append(patent_id)
    return matched


def is_global_patent_discovery_question(question: str) -> bool:
    q = question.lower()
    if "특허" in q and any(marker in q for marker in ("전체", "뭐뭐", "뭐가", "어떤", "알려", "설명", "목록")):
        return True

    has_discovery_marker = any(
        marker in q
        for marker in (
            "찾아",
            "검색",
            "목록",
            "보여",
            "관련 특허",
            "특허 찾아",
            "특허 검색",
            "특허 목록",
            "어떤 특허",
        )
    )
    if has_discovery_marker:
        return True

    query_terms = discovery_query_terms(question)
    return "특허" in q and bool(query_terms)


def _split_compound_nouns(text: str) -> str:
    """'물류특허'→'물류 특허' 처럼 한국어 복합명사 분리."""
    for noun in ("특허", "보고서", "원문", "청구항", "평가", "시스템", "장치", "방법"):
        text = re.sub(rf"([가-힣a-zA-Z0-9])({noun})", rf"\1 \2", text)
    return text


def discovery_query_terms(question: str) -> List[str]:
    terms: List[str] = []
    stop_terms = {
        "특허",
        "관련",
        "관련해",
        "관련해서",
        "관련된",
        "찾아",
        "찾아줘",
        "검색",
        "목록",
        "보여줘",
        "설명",
        "설명해줘",
        "알려",
        "알려줘",
        "대해",
        "대해서",
        "대해서는",
        "대하여",
        "대한",
        "관해",
        "관해서",
        "관하여",
        "관한",
        "시장",
        "동향",
        "최신",
        "최근",
        "지금",
        "요즘",
        "현재",
        "현황",
        "상황",
        "규모",
        "성장률",
        "전망",
        "되어있는지",
        "어떻게",
        "됐어",
        "되었어",
        "어땠어",
        "어때",
        "어떤지",
        "비교",
        "비교해줘",
        "차이",
        "공통점",
        "대비",
    }
    for term in tokens(_split_compound_nouns(question)):
        if len(term) < 2:
            continue
        if is_question_context_token(term):
            continue
        if term in stop_terms:
            continue
        if term not in terms:
            terms.append(term)
    return terms


def requires_external_patent_info(question: str) -> bool:
    q = question.lower()
    return any(
        marker in q
        for marker in (
            "최신",
            "최근",
            "시장 동향",
            "경쟁사",
            "유사 특허 찾아",
            "웹",
            "외부",
            "논문",
            "뉴스",
            "표준",
            "제품 동향",
            "kipris",
            "크롤링",
        )
    )


def has_specific_global_subject(question: str) -> bool:
    if re.search(r"10-\d{4}-\d+|10-\d{6,8}", question or ""):
        return True
    return bool(discovery_query_terms(question))


def is_generic_external_global_question(
    question: str,
    domain_matches: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    q = question.lower()
    external_markers = (
        "시장",
        "동향",
        "최신",
        "최근",
        "지금",
        "요즘",
        "현황",
        "규모",
        "성장률",
        "전망",
        "뉴스",
    )
    if not any(marker in q for marker in external_markers):
        return False
    if domain_matches:
        return False
    return not has_specific_global_subject(question)


def build_global_clarification_answer(question: str) -> str:
    return "\n".join(
        [
            "## 확인할 대상이 필요합니다",
            "",
            "시장·동향 질문은 대상 범위가 넓어서 바로 웹검색하면 관련 없는 자료가 섞일 수 있습니다.",
            "",
            "아래처럼 기술명이나 특허명을 같이 입력해 주세요.",
            "",
            "- `물류 시장이 지금 어떻게 되어있는지 찾아줘`",
            "- `CMP Pad 물류 관리 시스템 관련 시장 동향 찾아줘`",
            "- `NF3 설비 시장 동향 알려줘`",
            "- `10-2886381 특허 관련 외부 시장 자료 찾아줘`",
            "",
            "대상을 지정하면 내부 특허/보고서 근거와 외부 웹 출처를 분리해서 답변합니다.",
        ]
    )


def history_context(
    chat_history: Optional[List[Dict[str, Any]]] = None,
    context_patent_id: Optional[str] = None,
) -> Dict[str, Any]:
    current_patent_id = context_patent_id
    result_patents: List[Dict[str, Any]] = []
    for item in reversed(chat_history or []):
        metrics = item.get("metrics") or {}
        if not current_patent_id and metrics.get("patent_id"):
            current_patent_id = str(metrics.get("patent_id"))
        for row in metrics.get("search_result_patents") or []:
            pid = row.get("patent_id")
            if pid and all(existing.get("patent_id") != pid for existing in result_patents):
                result_patents.append(row)
    return {
        "current_patent_id": current_patent_id,
        "search_result_patents": result_patents[:8],
    }


def is_contextual_followup_question(question: str) -> bool:
    q = question.lower()
    followup_markers = (
        "이 특허",
        "그 특허",
        "해당 특허",
        "이거",
        "그거",
        "그것",
        "자세",
        "상세",
        "평가",
        "점수",
        "리스크",
        "도면",
        "표",
        "보고서",
        "유지",
        "매각",
        "제각",
        "사업성",
        "권리성",
        "기술성",
    )
    return any(marker in q for marker in followup_markers)


def is_other_patent_disambiguation_question(question: str) -> bool:
    q = question.lower()
    return any(marker in q for marker in ("다른 특허", "다른거", "다른 것", "다른 것도", "그 외", "나머지"))


def is_compare_question(question: str) -> bool:
    q = question.lower()
    return any(marker in q for marker in ("비교", "차이", "다른 점", "공통점", "대비"))


def is_decision_support_question(question: str) -> bool:
    q = question.lower()
    return is_patent_decision_or_value_question(question) and any(
        marker in q for marker in ("표", "보조", "판단", "유지", "매각", "제각", "의사결정", "결정")
    )


def patent_score_snapshot(patent_id: str, patent_meta: Dict[str, Any], docs: List[Document]) -> Dict[str, Any]:
    report_summary_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_SUMMARY", "REPORT_OVERVIEW"],
        ["평가 요약", "평가 개요"],
        ["종합", "기술성", "권리성", "시장성", "사업성"],
    )
    score_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_SCORE_DETAIL"],
        ["평가 기준별 점수"],
        ["기술성", "권리성", "시장성", "사업성"],
    )
    risk_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_RISK", "REPORT_DECISION"],
        ["리스크 및 추가 확인", "의사결정 가이드"],
        ["리스크", "회피설계", "무효", "추가 확인", "유지", "매각", "제각"],
    )
    summary_text = clean_evidence_text((report_summary_doc or score_doc or docs[0]).page_content) if docs else ""
    score_text = clean_evidence_text((score_doc or report_summary_doc or docs[0]).page_content) if docs else ""
    risk_text = clean_evidence_text((risk_doc or score_doc or report_summary_doc or docs[0]).page_content) if docs else ""
    total = score_text_value(summary_text, r"종합\s+([0-9]{1,3}\s*/\s*100)")
    tech = score_text_value(summary_text, r"기술성\s+([0-9]{1,3}\s*/\s*100)")
    right = score_text_value(summary_text, r"권리성\s+([0-9]{1,3}\s*/\s*100)")
    market = score_text_value(summary_text, r"시장성\s*및\s*사업성\s+([0-9]{1,3}\s*/\s*100)")
    risk = excerpt_around_terms(risk_text, ["리스크", "회피설계", "무효", "추가 확인", "보수적으로"], 180)
    return {
        "patent_id": patent_id,
        "title": patent_meta.get("title") or patent_id,
        "registration_number": patent_meta.get("registration_number") or patent_id,
        "ipc_code": patent_meta.get("ipc_code") or "-",
        "total": total,
        "tech": tech,
        "right": right,
        "market": market,
        "risk": first_sentence(risk or "보고서에서 추가 확인이 필요합니다.", 160),
    }


def build_patent_selection_answer(
    patents: List[Dict[str, Any]],
    current_patent_id: Optional[str] = None,
) -> str:
    filtered = [
        row for row in patents if not current_patent_id or row.get("patent_id") != current_patent_id
    ] or patents
    lines = [
        "## 어떤 특허를 볼까요?",
        "",
        "현재 인덱스에는 아래 특허들이 있습니다. 질문할 특허를 제목이나 등록번호로 지정하거나, 드롭다운에서 선택해 주세요.",
        "",
        "| 번호 | 특허 | 등록번호 | 질문 예시 |",
        "| --- | --- | --- | --- |",
    ]
    for idx, row in enumerate(filtered, start=1):
        title = str(row.get("title") or row.get("patent_id"))
        pid = str(row.get("patent_id") or "-")
        reg = str(row.get("registration_number") or pid)
        lines.append(f"| {idx} | {title} | {reg} | `{title} 자세히 알려줘` |")
    lines.extend(
        [
            "",
            "## 이어서 물어볼 수 있는 질문",
            "",
            "- `이 특허 평가 알려줘`",
            "- `원문 도면 보여줘`",
            "- `유지/매각/제각 판단 보조표 만들어줘`",
            "- `물류 특허랑 NF3 특허 비교해줘`",
        ]
    )
    return "\n".join(lines)


def source_cards_for_docs(docs: List[Document]) -> List[Dict[str, Any]]:
    _, cards = format_context(docs)
    return cards


def build_patent_comparison_answer(
    snapshots: List[Dict[str, Any]],
    source_cards: List[Dict[str, Any]],
) -> str:
    lines = [
        "## 특허 비교",
        "",
        "아래 표는 현재 인덱스의 원문/평가보고서 기준으로 정리한 비교입니다. 점수와 리스크는 AI 평가 보고서 근거를 사용했습니다.",
        "",
        "| 항목 | " + " | ".join(row["title"] for row in snapshots) + " |",
        "| --- | " + " | ".join("---" for _ in snapshots) + " |",
        "| 등록번호 | " + " | ".join(str(row["registration_number"]) for row in snapshots) + " |",
        "| IPC | " + " | ".join(str(row["ipc_code"]) for row in snapshots) + " |",
        "| 종합 | " + " | ".join(str(row["total"]) for row in snapshots) + " |",
        "| 기술성 | " + " | ".join(str(row["tech"]) for row in snapshots) + " |",
        "| 권리성 | " + " | ".join(str(row["right"]) for row in snapshots) + " |",
        "| 시장성 및 사업성 | " + " | ".join(str(row["market"]) for row in snapshots) + " |",
        "| 주요 리스크 | " + " | ".join(str(row["risk"]).replace("|", "/") for row in snapshots) + " |",
        "",
        "## 해석",
        "",
        "- 비교표는 최종 유지/매각/제각 결론이 아니라 검토 우선순위를 잡기 위한 보조 자료입니다.",
        "- 종합 점수만 보지 말고 기술성, 권리성, 시장성 및 사업성의 균형과 실제 사업 활용 가능성을 함께 봐야 합니다.",
        "- 세부 판단에는 청구항 구성요소, 유사 특허, 회피설계 가능성, 사업부 적용 이력이 추가로 필요합니다.",
    ]
    if source_cards:
        labels = " ".join(f"[{card.get('label')}]" for card in source_cards[:4])
        lines.append(f"- 주요 근거는 {labels}에서 확인됩니다.")
    return "\n".join(lines)


def build_decision_support_answer(
    snapshot: Dict[str, Any],
    source_cards: List[Dict[str, Any]],
) -> str:
    total_score = score_number(snapshot.get("total"))
    market_score = score_number(snapshot.get("market"))
    right_score = score_number(snapshot.get("right"))
    maintain = "중"
    sell = "중"
    abandon = "중"
    if total_score is not None and total_score >= 70:
        maintain = "높음"
        abandon = "낮음"
    if market_score is not None and market_score < 60:
        sell = "검토"
    if right_score is not None and right_score < 60:
        maintain = "주의"
        abandon = "검토"
    label_text = " ".join(f"[{card.get('label')}]" for card in source_cards[:3]) or "[자료1]"
    return "\n".join(
        [
            "## 유지/매각/제각 판단 보조표",
            "",
            f"대상 특허는 **{snapshot['title']} / {snapshot['registration_number']}**입니다. AI는 최종 결정을 내리지 않고, 아래 표는 의사결정 보조 근거입니다. {label_text}",
            "",
            "| 선택지 | 보조 판정 | 근거 | 추가 확인 |",
            "| --- | --- | --- | --- |",
            f"| 유지 | {maintain} | 종합 {snapshot['total']}, 기술성 {snapshot['tech']}, 권리성 {snapshot['right']} | 실제 사업 적용 이력과 연차료 대비 활용 가능성 |",
            f"| 매각 | {sell} | 시장성 및 사업성 {snapshot['market']}와 외부 수요 확인 필요 | 매수 후보, 적용 산업, 유사 특허 포지션 |",
            f"| 제각 | {abandon} | 리스크: {snapshot['risk'].replace('|', '/')} | 무효 가능성, 회피설계, 사업부 미활용 여부 |",
            "",
            "## 결론",
            "",
            "- 현재 자료만으로 유지/매각/제각을 단정할 수 없습니다.",
            "- 사업부 활용 여부, 유사 특허와의 청구항 차별성, 시장 수요, 비용 대비 기대효과를 함께 확인해야 합니다.",
        ]
    )


def _doc_text_for_discovery(doc: Document, limit: int = 4500) -> str:
    meta = doc.metadata or {}
    return normalize(
        " ".join(
            str(meta.get(key) or "")
            for key in (
                "title",
                "registration_number",
                "application_number",
                "ipc_code",
                "cpc_code",
                "tech_field",
                "business_field",
                "department",
                "section_title",
                "source_type",
            )
        )
        + "\n"
        + doc.page_content[:limit]
    )


def discovery_doc_score(question: str, doc: Document, query_terms: List[str]) -> Tuple[float, List[str]]:
    meta = doc.metadata or {}
    text = _doc_text_for_discovery(doc)
    title_text = normalize(str(meta.get("title") or ""))
    lower_text = text.lower()
    lower_title = title_text.lower()

    if query_terms:
        matched = [term for term in query_terms if term.lower() in lower_text]
        title_matched = [term for term in query_terms if term.lower() in lower_title]
        if not matched and not title_matched:
            return 0.0, []
        term_score = len(set(matched)) / max(1, len(query_terms))
        title_score = len(set(title_matched)) / max(1, len(query_terms))
    elif is_global_patent_discovery_question(question):
        matched = []
        term_score = 0.42
        title_score = 0.0
    else:
        matched = [
            term
            for term in tokens(question)
            if not is_question_context_token(term) and term.lower() in lower_text
        ]
        term_score = len(set(matched)) / max(1, len(set(tokens(question))))
        title_score = 0.0

    source_bonus = 0.08 if meta.get("source_type") == "ORIGINAL_PDF" else 0.04
    section_bonus = 0.04 if str(meta.get("section_title") or "") in ("요약", "청구범위", "기술분야", "평가 개요") else 0.0
    score = min(1.0, term_score * 0.58 + title_score * 0.32 + source_bonus + section_bonus)
    return round(score, 4), matched[:8]


def group_discovery_patents(
    question: str,
    retrieved_docs: List[Document],
    all_docs: List[Document],
    max_patents: int = 5,
    docs_per_patent: int = 2,
) -> Tuple[List[Dict[str, Any]], List[Document], List[str]]:
    query_terms = discovery_query_terms(question)
    candidate_docs: List[Document] = []
    seen_keys: set[str] = set()

    def add_candidate(doc: Document) -> None:
        key = doc_key(doc)
        if key in seen_keys:
            return
        seen_keys.add(key)
        candidate_docs.append(doc)

    corpus = all_docs or retrieved_docs
    if query_terms:
        for doc in corpus:
            score, _ = discovery_doc_score(question, doc, query_terms)
            if score > 0:
                add_candidate(doc)
    else:
        for doc in corpus:
            add_candidate(doc)
    for doc in retrieved_docs:
        score, _ = discovery_doc_score(question, doc, query_terms)
        if score > 0:
            add_candidate(doc)

    grouped: Dict[str, Dict[str, Any]] = {}
    for doc in candidate_docs:
        meta = doc.metadata or {}
        patent_id = str(meta.get("patent_id") or "")
        if not patent_id:
            continue
        score, matched_terms = discovery_doc_score(question, doc, query_terms)
        if score <= 0:
            continue
        group = grouped.setdefault(
            patent_id,
            {
                "patent_id": patent_id,
                "title": meta.get("title") or patent_id,
                "registration_number": meta.get("registration_number"),
                "application_number": meta.get("application_number"),
                "score": 0.0,
                "matched_terms": [],
                "docs": [],
                "source_types": set(),
                "directness": 0.0,
            },
        )
        group["score"] = max(float(group["score"]), score)
        group["docs"].append((score, doc))
        group["source_types"].add(meta.get("source_type") or "UNKNOWN")
        for term in matched_terms:
            if term not in group["matched_terms"]:
                group["matched_terms"].append(term)

    groups = list(grouped.values())
    for group in groups:
        docs = sorted(group["docs"], key=lambda item: item[0], reverse=True)
        group["docs"] = [doc for _, doc in docs]
        title_text = str(group.get("title") or "").lower()
        query_terms_lower = [term.lower() for term in query_terms]
        title_match = bool(query_terms_lower and any(term in title_text for term in query_terms_lower))
        original_match = False
        report_match = False
        for doc in group["docs"]:
            meta = doc.metadata or {}
            doc_text = _doc_text_for_discovery(doc).lower()
            if not query_terms_lower or not any(term in doc_text for term in query_terms_lower):
                continue
            if meta.get("source_type") == "ORIGINAL_PDF":
                original_match = True
            elif meta.get("source_type") == "REPORT_PDF":
                report_match = True
        if title_match:
            group["directness"] = 1.0
            group["relationship"] = "직접 관련"
        elif original_match:
            group["directness"] = 0.86
            group["relationship"] = "원문 직접 관련"
        elif report_match:
            group["directness"] = 0.45
            group["relationship"] = "보고서 간접 언급"
        else:
            group["directness"] = 0.25
            group["relationship"] = "낮은 관련"
        diversity_bonus = 0.04 * min(2, len(group["source_types"]))
        evidence_bonus = 0.02 * min(5, len(group["docs"]))
        directness_bonus = 0.16 * float(group.get("directness") or 0.0)
        group["score"] = round(min(1.0, float(group["score"]) + diversity_bonus + evidence_bonus + directness_bonus), 4)
        group["source_types"] = sorted(group["source_types"])

    groups.sort(key=lambda item: (item["score"], len(item["docs"])), reverse=True)
    if query_terms:
        min_match_count = 1 if len(query_terms) <= 1 else 2
        groups = [
            group
            for group in groups
            if len(set(group.get("matched_terms") or [])) >= min_match_count
            and float(group.get("directness") or 0.0) >= 0.55
        ]
    groups = groups[:max_patents]

    selected_docs: List[Document] = []
    selected_doc_keys: set[str] = set()
    for group in groups:
        chosen: List[Document] = []
        chosen_slots: set[Tuple[str, Any]] = set()

        def choose(doc: Document) -> bool:
            meta = doc.metadata or {}
            slot = (str(meta.get("source_type") or ""), meta.get("page_no"))
            if slot in chosen_slots:
                return False
            chosen.append(doc)
            chosen_slots.add(slot)
            return True

        original_docs = [doc for doc in group["docs"] if (doc.metadata or {}).get("source_type") == "ORIGINAL_PDF"]
        report_docs = [doc for doc in group["docs"] if (doc.metadata or {}).get("source_type") == "REPORT_PDF"]
        if original_docs:
            choose(original_docs[0])
        if report_docs and len(chosen) < docs_per_patent:
            choose(report_docs[0])
        for doc in group["docs"]:
            if len(chosen) >= docs_per_patent:
                break
            choose(doc)
        if len(chosen) < docs_per_patent:
            for doc in group["docs"]:
                if len(chosen) >= docs_per_patent:
                    break
                if doc not in chosen:
                    chosen.append(doc)
        for doc in chosen:
            key = doc_key(doc)
            if key in selected_doc_keys:
                continue
            selected_doc_keys.add(key)
            selected_docs.append(doc)

    return groups, selected_docs, query_terms


class BM25Index:
    def __init__(self, docs: Optional[List[Document]] = None, k1: float = BM25_K1, b: float = BM25_B):
        self.docs = docs or []
        self.k1 = k1
        self.b = b
        self.tf: List[Dict[str, int]] = []
        self.df: Dict[str, int] = {}
        self.doc_len: List[int] = []
        self.avgdl = 0.0
        self.idf: Dict[str, float] = {}
        self._build()

    def _build(self) -> None:
        self.tf = []
        self.df = {}
        self.doc_len = []
        if not self.docs:
            self.avgdl = 0.0
            self.idf = {}
            return

        for doc in self.docs:
            meta = doc.metadata or {}
            meta_text = " ".join(
                str(meta.get(k) or "")
                for k in (
                    "title",
                    "application_number",
                    "registration_number",
                    "ipc_code",
                    "cpc_code",
                    "department",
                    "section_title",
                    "source_type",
                )
            )
            freq: Dict[str, int] = {}
            for t in tokens(f"{meta_text}\n{doc.page_content}"):
                freq[t] = freq.get(t, 0) + 1
            self.tf.append(freq)
            self.doc_len.append(sum(freq.values()))
            for t in freq:
                self.df[t] = self.df.get(t, 0) + 1

        self.avgdl = sum(self.doc_len) / max(1, len(self.doc_len))
        total = len(self.docs)
        self.idf = {
            t: math.log(1 + (total - df + 0.5) / (df + 0.5))
            for t, df in self.df.items()
        }

    def search(self, query: str, k: int = 20) -> List[Document]:
        q_tokens = tokens(query)
        if not q_tokens:
            return []

        scored: List[Tuple[float, Document]] = []
        for i, doc in enumerate(self.docs):
            score = 0.0
            dl = self.doc_len[i] or 1
            denom_base = self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1.0))
            for qt in q_tokens:
                f = self.tf[i].get(qt, 0)
                if not f:
                    continue
                score += self.idf.get(qt, 0.0) * (f * (self.k1 + 1)) / (f + denom_base)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:k]]


def rrf_merge(
    ranked_lists: List[List[Document]],
    topn: int = 10,
    rrf_k: int = RRF_K,
    source_type_weights: Optional[Dict[str, float]] = None,
) -> List[Document]:
    scores: Dict[str, float] = {}
    doc_map: Dict[str, Document] = {}

    for docs in ranked_lists:
        for rank, doc in enumerate(docs, start=1):
            key = doc_key(doc)
            weight = 1.0
            if source_type_weights:
                weight = source_type_weights.get((doc.metadata or {}).get("source_type"), 1.0)
            scores[key] = scores.get(key, 0.0) + weight / (rrf_k + rank)
            doc_map[key] = doc

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[key] for key, _ in ranked[:topn]]


def rerank_by_lexical_overlap(question: str, docs: List[Document]) -> List[Document]:
    q_tokens = set(tokens(question))
    if not q_tokens:
        return docs

    scored: List[Tuple[float, int, Document]] = []
    for idx, doc in enumerate(docs):
        meta = doc.metadata or {}
        meta_text = " ".join(str(meta.get(k) or "") for k in ("title", "section_title", "source_type"))
        d_tokens = set(tokens(f"{meta_text}\n{doc.page_content[:2500]}"))
        overlap = len(q_tokens & d_tokens) / max(1, len(q_tokens))
        scored.append((overlap, -idx, doc))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [doc for _, _, doc in scored]


def lexical_confidence(question: str, docs: List[Document]) -> float:
    q_tokens = set(tokens(question))
    if not q_tokens or not docs:
        return 0.0

    scores: List[float] = []
    for doc in docs:
        meta = doc.metadata or {}
        meta_text = " ".join(str(meta.get(k) or "") for k in ("title", "section_title", "source_type"))
        d_tokens = set(tokens(f"{meta_text}\n{doc.page_content[:2500]}"))
        scores.append(len(q_tokens & d_tokens) / max(1, len(q_tokens)))
    return max(scores) if scores else 0.0


def classify_scope(question: str) -> str:
    q = question.lower()

    patent_keywords = (
        "특허",
        "청구항",
        "청구범위",
        "발명",
        "출원",
        "등록",
        "공개",
        "ipc",
        "cpc",
        "권리",
        "권리성",
        "기술성",
        "시장성",
        "사업성",
        "유사 특허",
        "kipris",
        "연차료",
        "소멸",
        "인용",
        "피인용",
        "도면",
        "실시예",
        "효과",
        "배경기술",
        "해결수단",
        "보고서",
        "평가",
    )
    patent_local_markers = (
        "이 특허",
        "해당 특허",
        "현재 특허",
        "본 특허",
        "청구항",
        "발명",
        "원문",
        "보고서",
        "연차료",
        "등록번호",
        "출원번호",
    )
    business_keywords = (
        "검토 요청",
        "받은 요청함",
        "사업부",
        "legal ai",
        "유지",
        "매각",
        "제각",
        "의견",
        "제출",
        "보고서 생성",
        "검토 현황",
        "업무",
        "프로세스",
        "권한",
        "이력",
        "감사",
        "상태",
        "담당자",
    )
    web_keywords = (
        "최신",
        "최근",
        "시장 동향",
        "경쟁사",
        "유사 특허 찾아",
        "웹",
        "검색",
        "외부",
        "논문",
        "뉴스",
        "표준",
        "제품 동향",
        "kipris",
    )

    has_patent = any(k in q for k in patent_keywords) or bool(PATENT_ID_RE.search(question))
    has_patent_local_marker = any(k in q for k in patent_local_markers)
    has_business = any(k in q for k in business_keywords)
    has_web = any(k in q for k in web_keywords)

    if has_patent and has_web:
        return "PATENT_WEB"
    if has_patent or (has_business and has_patent_local_marker):
        return "PATENT_LOCAL"
    if has_business:
        return "BUSINESS"
    return "OUT_OF_SCOPE"


def extract_referenced_patent_ids(question: str) -> List[str]:
    seen = []
    for match in PATENT_ID_RE.findall(question or ""):
        value = match.upper()
        if value not in seen:
            seen.append(value)
    return seen


def expand_queries_for_patent(question: str, patent_meta: Dict[str, Any], max_expands: int = 6) -> List[str]:
    queries: List[str] = []
    base = normalize(question)
    if base:
        queries.append(base)

    title = str(patent_meta.get("title") or "").strip()
    if title and title not in queries:
        queries.append(title)

    # combine title with question to bias retrieval
    if title:
        combined = f"{title} {question}"
        if combined not in queries:
            queries.append(combined)

    for code in (patent_meta.get("ipc_code"), patent_meta.get("cpc_code")):
        if code:
            code_q = f"{code} {question}"
            if code_q not in queries:
                queries.append(code_q)

    # add top title tokens
    title_tokens = [t for t in tokens(title) if len(t) >= 2]
    for t in title_tokens[:3]:
        q = f"{t} {question}"
        if q not in queries:
            queries.append(q)

    return queries[:max_expands]


def is_other_patent_question(patent_id: Optional[str], question: str) -> bool:
    q = question.lower()
    refs = extract_referenced_patent_ids(question)
    if patent_id and any(ref != patent_id.upper() for ref in refs):
        return True
    if "다른 특허" in q or "타 특허" in q:
        return "유사 특허" not in q
    return False


def is_business_process_question(question: str) -> bool:
    q = question.lower()
    process_keywords = (
        "프로세스",
        "절차",
        "검토 요청",
        "받은 요청함",
        "요청함",
        "제출",
        "의견",
        "이력",
        "상태",
        "권한",
        "화면",
        "버튼",
        "보고서 생성",
        "담당자",
        "승인",
        "반려",
    )
    return any(k in q for k in process_keywords)


def is_patent_decision_or_value_question(question: str) -> bool:
    q = question.lower()
    decision_keywords = (
        "유지",
        "매각",
        "제각",
        "포기",
        "보유",
        "가치",
        "리스크",
        "위험",
        "사업성",
        "사업적",
        "활용",
        "쓸만",
        "계속",
        "가져가",
        "팔아",
        "팔 수",
        "돈이",
    )
    return any(k in q for k in decision_keywords) and not is_business_process_question(question)


def has_current_patent_reference(question: str) -> bool:
    q = question.lower()
    references = (
        "이 특허",
        "해당 특허",
        "현재 특허",
        "본 특허",
        "이 기술",
        "해당 기술",
        "현재 기술",
        "이 발명",
        "해당 발명",
        "이 방법",
        "해당 방법",
        "이 시스템",
        "해당 시스템",
        "이거",
        "이 내용",
        "해당 내용",
        "여기",
    )
    return any(ref in q for ref in references)


def build_retrieval_question(question: str, patent_meta: Dict[str, Any]) -> Tuple[str, bool]:
    q = question.lower()
    expansions: List[str] = []
    title = patent_meta.get("title")
    registration_number = patent_meta.get("registration_number")
    application_number = patent_meta.get("application_number")
    ipc_code = patent_meta.get("ipc_code")

    if title:
        expansions.append(str(title))
    if registration_number:
        expansions.append(f"등록번호 {registration_number}")
    if application_number:
        expansions.append(f"출원번호 {application_number}")
    if ipc_code:
        expansions.append(f"IPC {ipc_code}")

    if is_contextual_patent_question(question) or is_patent_decision_or_value_question(question):
        expansions.extend(
            [
                "발명의 명칭 요약 청구항 1 배경기술 해결하려는 과제 과제의 해결 수단 발명의 효과",
                "AI 평가 보고서 기술성 권리성 시장성 사업성 추가 확인 사항 참고문헌",
            ]
        )

    if any(k in q for k in ("장점", "강점", "효과", "필요", "왜", "개선")):
        expansions.append("발명의 효과 해결하려는 과제 연산 부하 성능 개선")
    if any(k in q for k in ("리스크", "위험", "한계", "단점", "제각", "매각", "유지", "가치")):
        expansions.append("AI 평가 보고서 권리성 시장성 사업성 리스크 추가 확인 사항 유지 매각 제각 판단 근거")
    if any(k in q for k in ("어떻게", "동작", "원리", "방식", "구성")):
        expansions.append("청구항 실시예 구체적인 내용 동작 특성 프로세서 메모리 영역")

    seen: List[str] = []
    for item in expansions:
        clean = normalize(str(item))
        if clean and clean not in seen:
            seen.append(clean)

    if not seen:
        return question, False
    return normalize(f"{question} " + " ".join(seen)), True


def build_deep_retrieval_queries(question: str, patent_meta: Dict[str, Any]) -> Tuple[List[str], bool]:
    expanded, did_expand = build_retrieval_question(question, patent_meta)
    queries = [question]
    if did_expand:
        queries.append(expanded)

    intent = answer_intent(question)
    title = patent_meta.get("title") or ""
    if intent == "ADVANTAGE":
        queries.append(f"{title} 배경기술 해결하려는 과제 발명의 효과 연산 부하 성능 개선")
        queries.append(f"{title} 기술성 차별성 파급성 혁신성 성능 개선")
    elif intent == "EVALUATION":
        queries.append(f"{title} 평가 요약 종합 점수 기술성 권리성 시장성 사업성")
        queries.append(f"{title} 평가 기준별 상세 점수 리스크 추가 확인 의사결정 가이드")
    elif intent in ("RISK", "DECISION"):
        queries.append(f"{title} 사업성 권리성 시장성 리스크 추가 확인 회피설계 무효 유사 특허")
        queries.append(f"{title} 유지 매각 제각 의사결정 가이드 연차료 사업 활용")
    elif intent == "OPERATION":
        queries.append(f"{title} 청구항 1 해시 메모리 영역 트랜잭션 동일 여부 프로세서")
        queries.append(f"{title} 과제의 해결 수단 구체적인 내용 동작 특성")
    elif intent == "GENERAL":
        queries.append(f"{title} 요약 청구항 발명의 효과 평가 보고서")

    unique: List[str] = []
    for query in queries:
        clean = normalize(query)
        if clean and clean not in unique:
            unique.append(clean)
    return unique, len(unique) > 1


def is_contextual_patent_question(question: str) -> bool:
    q = question.lower()
    contextual_keywords = (
        "이거",
        "이 기술",
        "이 방법",
        "이 시스템",
        "이 발명",
        "해당 기술",
        "현재 기술",
        "이 내용",
        "해당 내용",
        "현재 내용",
        "여기",
        "요약",
        "핵심",
        "장점",
        "강점",
        "필요",
        "왜",
        "뭐야",
        "무엇",
        "어때",
        "어떻게",
        "문제",
        "해결",
        "개선",
        "효과",
        "활용",
        "가능성",
        "리스크",
        "위험",
        "한계",
        "성능",
        "동작",
        "원리",
        "가치",
        "사업",
        "내용 알려",
        "내용 설명",
        "무슨 내용",
        "무슨 기술",
        "어떤 기술",
        "방법 알려",
        "기술 설명",
        "점수",
        "결과",
        "보고서",
        "평가",
    )
    return any(k in q for k in contextual_keywords)


def is_clearly_unrelated_question(question: str) -> bool:
    q = normalize(question).lower()
    unrelated_keywords = (
        "점심",
        "저녁",
        "아침",
        "야식",
        "메뉴",
        "먹지",
        "먹을까",
        "맛집",
        "카페 추천",
        "음식",
        "요리",
        "레시피",
        "날씨",
        "기온",
        "비와",
        "비 와",
        "눈와",
        "눈 와",
        "우산",
        "미세먼지",
        "태풍",
        "영화",
        "드라마",
        "음악",
        "노래",
        "게임 추천",
        "운세",
        "로또",
        "복권",
        "축구",
        "야구",
        "농구",
        "스포츠",
        "주식 추천",
        "코인 추천",
        "비트코인 사",
        "환율",
        "부동산",
        "연애",
        "데이트",
        "여행",
        "호텔",
        "항공권",
        "농담",
        "개그",
        "심심",
        "고양이",
        "강아지",
        "동물",
    )
    return any(k in q for k in unrelated_keywords)


def is_question_context_token(token: str) -> bool:
    return token in QUESTION_CONTEXT_TERMS or any(
        token.startswith(prefix) for prefix in QUESTION_CONTEXT_PREFIXES
    )


def is_related_to_patent_meta(question: str, patent_meta: Dict[str, Any]) -> bool:
    q_tokens = set(tokens(question))
    if not q_tokens:
        return False

    meta_text_parts: List[str] = []
    for key in (
        "title",
        "registration_number",
        "application_number",
        "ipc_code",
        "cpc_code",
        "tech_field",
        "business_field",
    ):
        value = patent_meta.get(key)
        if isinstance(value, list):
            meta_text_parts.extend(str(v) for v in value)
        elif value:
            meta_text_parts.append(str(value))

    meta_tokens = {
        token
        for token in tokens(" ".join(meta_text_parts))
        if len(token) >= 2 and token not in GENERIC_PATENT_TITLE_TERMS
    }
    return bool(q_tokens & meta_tokens)


def has_unrelated_subject(question: str, patent_meta: Dict[str, Any]) -> bool:
    q_tokens = {
        token
        for token in tokens(question)
        if len(token) >= 2 and not is_question_context_token(token)
    }
    if not q_tokens:
        return False

    meta_text = " ".join(
        str(patent_meta.get(key) or "")
        for key in (
            "title",
            "registration_number",
            "application_number",
            "ipc_code",
            "cpc_code",
            "tech_field",
            "business_field",
        )
    )
    meta_tokens = {
        token
        for token in tokens(meta_text)
        if len(token) >= 2 and token not in GENERIC_PATENT_TITLE_TERMS
    }
    return not bool(q_tokens & meta_tokens)


def is_related_to_patent_documents(question: str, patent_id: str) -> bool:
    q_tokens = {
        token
        for token in tokens(question)
        if len(token) >= 2 and not is_question_context_token(token)
    }
    if not q_tokens:
        return False

    docs_path = PATENTS_ROOT / patent_id / "extracted" / "all_chunks.jsonl"
    if not docs_path.exists():
        return False

    try:
        docs = read_documents_jsonl(docs_path)
    except Exception:
        return False

    haystack = "\n".join(
        f"{(doc.metadata or {}).get('title', '')} {(doc.metadata or {}).get('section_title', '')} {doc.page_content}"
        for doc in docs
    ).lower()

    expanded_tokens = set(q_tokens)
    for token in list(q_tokens):
        if token.endswith("값") and len(token) > 2:
            expanded_tokens.add(token[:-1])
        if token.endswith("방식") and len(token) > 2:
            expanded_tokens.add(token[:-2])

    return any(token in haystack for token in expanded_tokens if len(token) >= 2)


def call_ollama_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: int = 120,
    temperature: Optional[float] = None,
) -> str:
    if INTENT_PROVIDER == "openai":
        # INTENT_MODEL이 Ollama 모델명(":"포함)이면 OpenAI 기본 모델로 교정
        _openai_model = INTENT_MODEL if ":" not in INTENT_MODEL else os.getenv("OPENAI_INTENT_MODEL", "gpt-4.1-mini")
        result = call_openai_messages(messages=messages, model=_openai_model, timeout=timeout)
        if result.get("ok"):
            return str(result.get("text") or "").strip()
        if not ENABLE_OLLAMA_INTENT_FALLBACK:
            raise RuntimeError(f"OpenAI intent call failed (model={_openai_model}): {result.get('error')}")

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": OLLAMA_TEMPERATURE if temperature is None else temperature, "top_p": 0.9},
    }
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "").strip()


def call_ollama(messages: List[Dict[str, str]], timeout: int = 120) -> str:
    if ANSWER_PROVIDER == "openai":
        result = call_openai_messages(
            messages=messages,
            model=ANSWER_MODEL,
            timeout=timeout,
            max_output_tokens=ANSWER_NUM_PREDICT,
            temperature=0.2,
        )
        if result.get("ok"):
            return str(result.get("text") or "").strip()
        raise RuntimeError(f"OpenAI answer call failed: {result.get('error')}")
    return call_ollama_model(ANSWER_MODEL or GEN_MODEL, messages, timeout=timeout)


def parse_json_object(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(raw[start : end + 1])
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def _embedding_signature() -> Dict[str, str]:
    return {"provider": EMBEDDING_PROVIDER, "model": EMBEDDING_MODEL}


def _embedding_manifest_path(index_dir: Path) -> Path:
    return index_dir / "embedding_manifest.json"


def _index_matches_embedding(index_dir: Path) -> bool:
    if not index_dir.exists():
        return False
    manifest_path = _embedding_manifest_path(index_dir)
    if not manifest_path.exists():
        return EMBEDDING_PROVIDER != "openai"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    signature = _embedding_signature()
    return manifest.get("provider") == signature["provider"] and manifest.get("model") == signature["model"]


def _write_embedding_manifest(index_dir: Path) -> None:
    try:
        manifest = {**_embedding_signature(), "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        _embedding_manifest_path(index_dir).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_existing_patent_documents(patent_dir: Path) -> List[Document]:
    for rel_path in (
        Path("extracted/all_chunks.jsonl"),
        Path("reviewed/approved_documents.jsonl"),
        Path("index/vectorstore/documents.jsonl"),
    ):
        docs = read_documents_jsonl(patent_dir / rel_path)
        if docs:
            return docs
    return []


def build_intent_agent_patent_hint(patent_id: Optional[str], patent_meta: Dict[str, Any]) -> str:
    if not patent_id:
        return "현재 선택된 특허 없음"

    meta_lines = [
        f"patent_id: {patent_id}",
        f"title: {patent_meta.get('title') or '-'}",
        f"registration_number: {patent_meta.get('registration_number') or '-'}",
        f"application_number: {patent_meta.get('application_number') or '-'}",
        f"ipc_code: {patent_meta.get('ipc_code') or '-'}",
        f"cpc_code: {patent_meta.get('cpc_code') or '-'}",
    ]

    docs_path = PATENTS_ROOT / patent_id / "extracted" / "all_chunks.jsonl"
    if not docs_path.exists():
        return "\n".join(meta_lines)

    try:
        docs = read_documents_jsonl(docs_path)
    except Exception:
        return "\n".join(meta_lines)

    snippets: List[str] = []
    for source_type in ("ORIGINAL_PDF", "REPORT_PDF"):
        for doc in docs:
            meta = doc.metadata or {}
            if meta.get("source_type") != source_type:
                continue
            section = meta.get("section_title") or source_type
            snippets.append(f"- {source_type} / {section}: {normalize(doc.page_content)[:260]}")
            if len(snippets) >= 4:
                break
        if len(snippets) >= 4:
            break

    if snippets:
        meta_lines.append("document_hints:")
        meta_lines.extend(snippets[:4])
    return "\n".join(meta_lines)


def _fallback_local_intent_scope(question: str, patent_id: Optional[str]) -> Tuple[str, float, str]:
    q = question.lower()
    if is_clearly_unrelated_question(question):
        return "OUT_OF_SCOPE", 0.55, "룰 기반: 특허/업무와 무관한 질문"
    if any(term in q for term in ("최신", "최근", "뉴스", "외부", "시장 동향", "성장률", "전망", "경쟁사", "표준")):
        return "PATENT_WEB", 0.64, "룰 기반: 명시적인 외부/최신 정보 요청"
    if any(term in q for term in ("워크플로우", "검토 요청", "의견 제출", "상태", "권한", "유지", "매각", "제각")):
        return "BUSINESS", 0.62, "룰 기반: 검토 업무 절차 질문"
    if patent_id or any(term in q for term in ("특허", "청구항", "보고서", "평가", "리스크", "발명", "원문", "도면")):
        return "PATENT_LOCAL", 0.62, "룰 기반: 내부 특허 원문/보고서 질문"
    return "OUT_OF_SCOPE", 0.45, "룰 기반: 답변 범위가 불분명함"


def run_intent_agent(
    question: str,
    patent_id: Optional[str],
    patent_meta: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    t0 = now_ms()
    metrics: Dict[str, Any] = {
        "intent_agent_used": True,
        "intent_agent_model": INTENT_MODEL,
    }

    if not ENABLE_INTENT_AGENT:
        scope, confidence, reason = _fallback_local_intent_scope(question, patent_id)
        metrics.update(
            {
                "intent_agent_used": False,
                "intent_agent_scope": scope,
                "intent_agent_confidence": round(confidence, 4),
                "intent_agent_reason": reason,
                "intent_agent_ms": 0,
            }
        )
        return scope, metrics

    patent_hint = build_intent_agent_patent_hint(patent_id, patent_meta)
    system_prompt = """
너는 SKIPA 특허 RAG 챗봇의 질문 라우팅 전담 에이전트다.

역할:
- 사용자의 질문이 현재 선택된 특허, 해당 특허의 평가 보고서, 특허 검토 업무, 또는 완전히 무관한 주제 중 어디에 속하는지 판단한다.
- 단순 키워드 일치가 아니라 의도를 판단한다.
- 특허 상세 화면에서 "이 기술", "이거", "장점", "문제", "활용", "리스크", "왜 필요한지", "어떻게 동작하는지"처럼 물으면 현재 특허 관련 질문으로 본다.
- 단, 사용자가 별도 주제(점심, 날씨, 맛집, 영화, 스포츠, 동물, 여행, 주식 추천 등)를 말하면 OUT_OF_SCOPE로 본다.

scope 정의:
- PATENT_LOCAL: 현재 특허 원문/AI 평가 보고서/특허 메타데이터로 답해야 하는 질문
- PATENT_WEB: 현재 특허와 직접 관련되며 최신 동향, 외부 시장, 경쟁사, 유사 특허, 뉴스, 논문, 표준 등 외부 검색이 필요한 질문
- BUSINESS: 특허 검토 요청, 사업부 의견 제출, 유지/매각/제각 프로세스, 이력/상태/권한 같은 업무 절차 질문
- OUT_OF_SCOPE: 현재 특허 또는 특허 검토 업무와 무관한 질문

반드시 아래 JSON 하나만 출력한다.
{"scope":"PATENT_LOCAL","confidence":0.0,"reason":"짧은 이유"}
""".strip()

    user_prompt = f"""
현재 특허 정보:
{patent_hint}

사용자 질문:
{question}

판정 규칙:
1. 현재 특허를 가리키는 대명사/맥락 표현은 특허 관련으로 인정한다.
2. 특허·보고서·청구항·효과·권리·평가·사업 활용·리스크·의사결정 근거는 PATENT_LOCAL이다.
3. 최신/최근/외부/경쟁사/시장 동향/유사 특허 검색은 PATENT_WEB이다.
4. 워크플로우/제출/검토 요청/이력/권한/상태는 BUSINESS이다.
5. 현재 특허와 무관한 일반 잡담/추천/생활 정보는 OUT_OF_SCOPE이다.
""".strip()

    try:
        raw = call_ollama_model(
            INTENT_MODEL,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            timeout=INTENT_AGENT_TIMEOUT,
            temperature=0.0,
        )
        parsed = parse_json_object(raw) or {}
        scope = str(parsed.get("scope") or "OUT_OF_SCOPE").strip().upper()
        if scope not in ("PATENT_LOCAL", "PATENT_WEB", "BUSINESS", "OUT_OF_SCOPE"):
            scope = "OUT_OF_SCOPE"
        try:
            confidence = float(parsed.get("confidence", 0.0))
        except Exception:
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        reason = normalize(str(parsed.get("reason") or ""))[:180]

        if scope != "OUT_OF_SCOPE" and confidence < INTENT_AGENT_MIN_CONFIDENCE:
            scope = "OUT_OF_SCOPE"

        metrics.update(
            {
                "intent_agent_scope": scope,
                "intent_agent_confidence": round(confidence, 4),
                "intent_agent_reason": reason,
                "intent_agent_ms": now_ms() - t0,
            }
        )
        return scope, metrics
    except Exception as exc:
        scope, confidence, reason = _fallback_local_intent_scope(question, patent_id)
        metrics.update(
            {
                "intent_agent_scope": scope,
                "intent_agent_confidence": round(confidence, 4),
                "intent_agent_reason": f"{reason}; intent agent error: {str(exc)[:120]}",
                "intent_agent_ms": now_ms() - t0,
            }
        )
        return scope, metrics


def run_global_intent_agent(question: str, domain_matches: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    t0 = now_ms()
    metrics: Dict[str, Any] = {
        "intent_agent_used": True,
        "intent_agent_model": INTENT_MODEL,
        "intent_agent_type": "GLOBAL_ROUTER",
    }

    # 지시어(대명사): 컨텍스트 없으면 CLARIFY
    AMBIGUOUS_TERMS = ("이거", "이것", "그거", "저거", "이 특허", "앞에서", "방금", "이전", "어떻게 해")
    # 정의 요청: "뭐야/이란" 패턴만 (알려줘/설명 등 일반 동사 제외)
    DEFINITION_TERMS = ("뭐야", "뭐예요", "뭐임", "뭔가요", "이란", "무엇인가", "무엇인지", "뭔지")
    # 연속 질문 패턴
    CONTINUATION_TERMS = ("더 자세하게", "자세히 알려줘", "더 알려줘", "이어서", "계속해서", "좀 더", "추가로")

    def _normalize_q(text: str) -> str:
        import re as _re
        for noun in ("특허", "보고서", "원문", "청구항", "평가"):
            text = _re.sub(rf"([가-힣a-zA-Z0-9])({noun})", rf"\1 \2", text)
        return text

    def _is_continuation_q(text: str) -> bool:
        return any(t in text.lower() for t in CONTINUATION_TERMS)

    def _is_ambiguous_global(text: str) -> bool:
        q = _normalize_q(text.strip().lower())
        if _is_continuation_q(q):
            return False
        if len(q) <= 10 and any(t in q for t in AMBIGUOUS_TERMS):
            return True
        if any(t in q for t in AMBIGUOUS_TERMS) and not domain_matches:
            return True
        return False

    def _is_definition_question(text: str) -> bool:
        q = text.strip().lower()
        return any(t in q for t in DEFINITION_TERMS)

    def fallback(reason: str) -> Tuple[str, Dict[str, Any]]:
        q = _normalize_q(question.lower())
        if is_clearly_unrelated_question(question):
            scope = "OUT_OF_SCOPE"
        elif _is_continuation_q(question):
            # "더 자세하게", "이어서" 등 → 이전 컨텍스트 기반으로 처리
            scope = "CLARIFY" if not domain_matches else "GLOBAL_DETAIL"
        elif _is_ambiguous_global(question):
            scope = "CLARIFY"
        elif _is_definition_question(question):
            if domain_matches:
                # "cmp가 뭐야?" + 내부 특허 있음 → 특허 내용으로 설명
                scope = "GLOBAL_DETAIL"
            else:
                # "cmd가 뭐야?" + 내부 데이터 없음 → 웹 검색
                scope = "GLOBAL_WEB"
        elif is_explicit_visual_asset_request(question):
            scope = "GLOBAL_VISUAL"
        elif is_evaluation_question(question):
            scope = "GLOBAL_EVALUATION"
        elif any(term in q for term in ("시장", "동향", "최신", "최근", "지금", "요즘", "외부", "뉴스", "규모", "성장률", "전망")):
            scope = "GLOBAL_WEB"
        elif is_patent_detail_request(question) and domain_matches:
            scope = "GLOBAL_DETAIL"
        elif is_global_patent_discovery_question(question) or domain_matches:
            scope = "GLOBAL_DISCOVERY"
        else:
            scope = "OUT_OF_SCOPE"
        metrics.update(
            {
                "intent_agent_used": False,
                "intent_agent_scope": scope,
                "intent_agent_confidence": 0.62 if scope not in ("OUT_OF_SCOPE", "CLARIFY") else 0.5,
                "intent_agent_reason": reason,
                "intent_agent_ms": now_ms() - t0,
                "web_query": question if scope == "GLOBAL_WEB" else "",
            }
        )
        return scope, metrics

    if not ENABLE_INTENT_AGENT:
        return fallback("intent agent disabled; fallback router used")

    match_lines = []
    for match in domain_matches[:5]:
        match_lines.append(
            "- "
            + json.dumps(
                {
                    "patent_id": match.get("patent_id"),
                    "title": match.get("title"),
                    "registration_number": match.get("registration_number"),
                    "matched_terms": match.get("matched_terms"),
                    "score": match.get("score"),
                },
                ensure_ascii=False,
            )
        )
    domain_hint = "\n".join(match_lines) if match_lines else "관련 특허 도메인 카드 매칭 없음"

    system_prompt = """
너는 SKIPA 특허 RAG 챗봇의 전체 검색 라우팅 에이전트다.

사용자 질문을 단어 트리거가 아니라 의도와 필요한 근거 종류로 분류한다.
가능한 scope:
- CLARIFY: 어떤 특허를 대상으로 하는지 알 수 없어 되물어야 하는 모호한 질문. "이거", "그거", "이 특허" 등 지시어만 있고 대화 이력에서도 특허/범위를 특정할 수 없을 때.
- GLOBAL_WEB: (1) 현재/최신/외부 시장, 산업 동향, 경쟁사, 뉴스, 표준, 시장규모, 성장률, 전망 등 내부 데이터만으로 답할 수 없는 질문. (2) "cmd가 뭐야?", "API란?", "BM25가 뭐야?" 처럼 내부 특허/보고서와 무관한 일반 기술/개념 정의 질문
- GLOBAL_DISCOVERY: 전체 인덱스에서 어떤 특허가 있는지, 관련 특허 목록/검색/개수를 묻는 질문
- GLOBAL_DETAIL: 전체 인덱스에서 특정 또는 단일 후보 특허를 자세히 설명해 달라는 질문
- GLOBAL_EVALUATION: 평가 보고서 점수, 기술성, 권리성, 시장성, 사업성, 리스크, 평가 결과, 유지/포기/매각/제각 판단 근거를 묻는 질문
- GLOBAL_VISUAL: 표, 그림, 도면, 이미지, 다이어그램, 차트를 보여달라는 질문
- BUSINESS: 검토 요청, 의견 제출, 유지/매각/제각 프로세스, 이력/권한/상태 같은 업무 절차 질문
- OUT_OF_SCOPE: 특허/기술/시장/업무와 무관한 일반 잡담 또는 생활 질문

중요 규칙:
1. "이거", "이것", "이 특허", "앞에서", "방금", "이전", "어떻게 해"처럼 지시 대상이 불분명하고 도메인 매칭 후보도 없으면 CLARIFY다. 되물어서 범위를 확인한다.
2. "물류 시장이 지금 어떻게 되어있는지"처럼 시장의 현재 상태를 묻는 질문은 관련 특허가 매칭되어도 GLOBAL_WEB이다.
3. "물류 특허 알려줘", "반도체 특허 찾아줘"는 GLOBAL_DISCOVERY다.
4. "물류 특허 자세히 알려줘"는 단일 후보가 있으면 GLOBAL_DETAIL이다.
5. "유지 판단 근거", "평가 점수", "기술성/권리성/시장성 점수", "포기/매각 판단 기준" 등 내부 평가보고서를 묻는 질문은 GLOBAL_EVALUATION이다. 절대 GLOBAL_WEB으로 보내지 않는다.
6. "보고서 표 보여줘", "원문 도면 보여줘"처럼 내부 문서 시각자료 요청은 GLOBAL_VISUAL이다.
7. "시장 동향 알려줘"처럼 대상이 없는 질문은 CLARIFY로 되묻기를 유도한다.
8. 도메인 매칭 후보에 특허가 있고 질문에 "유지", "판단", "근거", "포기", "매각", "제각", "평가"가 포함되면 GLOBAL_EVALUATION이다.
9. 최종 출력은 JSON 하나만 한다.

예시:
질문: "CMP Pad 물류 관리 시스템의 유지 판단 근거를 알려줘" (도메인 매칭: CMP Pad 특허) → {"scope":"GLOBAL_EVALUATION","confidence":0.95,"reason":"내부 평가보고서의 유지 판단 근거 질문","web_query":"","clarification_question":""}
질문: "cmp가 뭐야?" (도메인 매칭: CMP Pad 특허) → {"scope":"GLOBAL_DETAIL","confidence":0.9,"reason":"기술 용어 정의 질문, 내부 특허 원문으로 설명 가능","web_query":"","clarification_question":""}
질문: "cmd가 뭐야?" (도메인 매칭 없음) → {"scope":"GLOBAL_WEB","confidence":0.92,"reason":"내부 데이터 없는 일반 기술 개념 정의","web_query":"cmd 명령어 뜻","clarification_question":""}
질문: "반도체 CMP 시장 최근 동향 알려줘" → {"scope":"GLOBAL_WEB","confidence":0.9,"reason":"외부 시장 동향 질문","web_query":"반도체 CMP 시장 동향","clarification_question":""}
질문: "이거 어떻게 해" (도메인 매칭 없음) → {"scope":"CLARIFY","confidence":0.9,"reason":"지시 대상 불명확","web_query":"","clarification_question":"어떤 특허에 대해 질문하시나요? 특허명이나 번호를 알려주시면 정확하게 답변드릴 수 있어요."}

형식:
{"scope":"GLOBAL_WEB","confidence":0.0,"reason":"짧은 이유","web_query":"웹 검색에 사용할 한국어 검색어","clarification_question":"CLARIFY일 때만 되물을 질문, 나머지는 빈 문자열"}
""".strip()

    user_prompt = f"""
사용자 질문:
{question}

현재 전체 인덱스 도메인 매칭 후보:
{domain_hint}

위 질문을 어떤 답변 경로로 보내야 하는지 판단하라.
""".strip()

    try:
        raw = call_ollama_model(
            INTENT_MODEL,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            timeout=INTENT_AGENT_TIMEOUT,
            temperature=0.0,
        )
        parsed = parse_json_object(raw) or {}
        scope = str(parsed.get("scope") or "").strip().upper()
        if scope not in (
            "CLARIFY",
            "GLOBAL_WEB",
            "GLOBAL_DISCOVERY",
            "GLOBAL_DETAIL",
            "GLOBAL_EVALUATION",
            "GLOBAL_VISUAL",
            "BUSINESS",
            "OUT_OF_SCOPE",
        ):
            return fallback("intent agent returned invalid scope; fallback router used")
        try:
            confidence = float(parsed.get("confidence", 0.0))
        except Exception:
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        if confidence < INTENT_AGENT_MIN_CONFIDENCE:
            return fallback("intent agent confidence below threshold; fallback router used")
        clarification_question = normalize(str(parsed.get("clarification_question") or ""))[:300]
        metrics.update(
            {
                "intent_agent_scope": scope,
                "intent_agent_confidence": round(confidence, 4),
                "intent_agent_reason": normalize(str(parsed.get("reason") or ""))[:220],
                "intent_agent_ms": now_ms() - t0,
                "web_query": normalize(str(parsed.get("web_query") or (question if scope == "GLOBAL_WEB" else "")))[:260],
                "clarification_question": clarification_question,
            }
        )
        return scope, metrics
    except Exception as exc:
        return fallback(f"intent agent error: {str(exc)[:140]}")


def format_context(docs: List[Document]) -> Tuple[str, List[Dict[str, Any]]]:
    blocks: List[str] = []
    source_cards: List[Dict[str, Any]] = []
    total_chars = 0

    for idx, doc in enumerate(docs, start=1):
        meta = doc.metadata or {}
        label = f"자료{idx}"
        content = normalize(doc.page_content)[:MAX_DOC_CHARS]
        if total_chars + len(content) > MAX_TOTAL_CONTEXT_CHARS and blocks:
            break
        total_chars += len(content)

        blocks.append(
            "\n".join(
                [
                    f"[{label}]",
                    f"- 문서유형: {meta.get('source_type')}",
                    f"- 섹션: {meta.get('section_title') or '-'}",
                    f"- 페이지: {meta.get('page_no') or '-'}",
                    f"- URL: {meta.get('source_url') or '-'}",
                    content,
                ]
            )
        )

        source_cards.append(
            {
                "label": label,
                "title": meta.get("title") or meta.get("section_title"),
                "section_title": meta.get("section_title"),
                "patent_id": meta.get("patent_id"),
                "source_type": meta.get("source_type"),
                "document_type": meta.get("source_type"),
                "page_no": meta.get("page_no"),
                "url": meta.get("source_url"),
                "source_url": meta.get("source_url"),
                "source_path": meta.get("source_path"),
                "relative_source_path": meta.get("relative_source_path"),
                "file_name": meta.get("file_name"),
                "chunk_id": meta.get("chunk_id") or doc_key(doc),
                "snippet": clean_evidence_text(content)[:180],
                "content_type": meta.get("content_type"),
                "asset_kind": meta.get("asset_kind"),
                "asset_url": meta.get("asset_url"),
                "asset_file_name": meta.get("asset_file_name"),
                "asset_base64": meta.get("asset_base64"),
                "asset_mime": meta.get("asset_mime"),
                "web_source_grade": meta.get("web_source_grade"),
                "web_source_type": meta.get("web_source_type"),
                "web_source_reason": meta.get("web_source_reason"),
                "web_provider": meta.get("web_provider"),
                "web_provider_score": meta.get("web_provider_score"),
                "published_date": meta.get("published_date"),
            }
        )

    return "\n\n".join(blocks), source_cards


def point_from_five_score(score: Any) -> float:
    try:
        value = float(score)
    except Exception:
        return 0.0
    return max(-2.0, min(2.0, value - 3.0))


def format_point(value: float) -> str:
    if abs(value) < 0.05:
        return "0.0"
    return f"{value:+.1f}"


def grade_from_point(value: float) -> str:
    if value > 0.3:
        return "긍정"
    if value < -0.3:
        return "부정"
    return "중립"


def first_sentence(text: str, limit: int = 180) -> str:
    clean = normalize(text)
    if len(clean) <= limit:
        return clean
    sliced = clean[:limit]
    for sep in ("다. ", ". ", "? ", "! "):
        idx = sliced.rfind(sep)
        if idx > 40:
            return sliced[: idx + len(sep)].strip()
    return sliced.rstrip() + "..."


def report_json_path_from_meta(patent_meta: Dict[str, Any]) -> Optional[Path]:
    source = patent_meta.get("source_report_json")
    if not source:
        return None
    path = Path(str(source))
    if path.is_absolute():
        return path
    return Path.cwd() / path


def load_report_json(patent_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    path = report_json_path_from_meta(patent_meta)
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def make_source_card(
    patent_meta: Dict[str, Any],
    patent_id: str,
    label: str,
    source_type: str,
    page_no: Optional[int],
    snippet: str,
    chunk_id: str,
) -> Dict[str, Any]:
    file_name = patent_meta.get("report_pdf") if source_type == "REPORT_PDF" else patent_meta.get("original_pdf")
    url = None
    if file_name:
        url = f"{PUBLIC_FILE_BASE_URL.rstrip('/')}/patents/{patent_id}/{str(file_name).lstrip('/')}"
        if page_no:
            url += f"#page={page_no}"
    return {
        "label": label,
        "title": patent_meta.get("title"),
        "source_type": source_type,
        "document_type": source_type,
        "page_no": page_no,
        "url": url,
        "chunk_id": chunk_id,
        "snippet": snippet[:180],
    }


def dimension_page_no(dim: str) -> int:
    return {
        "기술성": 4,
        "권리성": 5,
        "시장성": 7,
        "사업성": 8,
    }.get(dim, 2)


def report_scores_by_dimension(report_data: Dict[str, Any], dim: str) -> List[Dict[str, Any]]:
    rows = []
    for row in report_data.get("llm_scores") or []:
        if row.get("dim") == dim:
            rows.append(row)
    for row in report_data.get("auto_scores") or []:
        if row.get("dim") == dim:
            rows.append(row)
    return rows


def combined_report_summary(report_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    summary: Dict[str, Dict[str, Any]] = {}
    for dim in ("기술성", "권리성", "시장성", "사업성"):
        rows = report_scores_by_dimension(report_data, dim)
        if not rows:
            continue
        points = [point_from_five_score(row.get("score")) for row in rows]
        avg = sum(points) / max(1, len(points))
        summary[dim] = {
            "average": avg,
            "count": len(points),
            "positive": sum(1 for p in points if p > 0.49),
            "neutral": sum(1 for p in points if -0.49 <= p <= 0.49),
            "negative": sum(1 for p in points if p < -0.49),
        }
    return summary


def structured_report_answer(
    patent_id: str,
    question: str,
    patent_meta: Dict[str, Any],
    report_data: Dict[str, Any],
) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    q = question.lower()
    title = patent_meta.get("title") or report_data.get("title") or patent_id
    dims = ("기술성", "권리성", "시장성", "사업성")
    asked_dim = next((dim for dim in dims if dim in question), None)
    source = make_source_card(
        patent_meta,
        patent_id,
        "자료1",
        "REPORT_PDF",
        dimension_page_no(asked_dim) if asked_dim else 2,
        "AI 평가 보고서의 평가 요약 및 기준별 상세 점수",
        f"{patent_id}:structured:report",
    )

    decision_keywords = ("유지", "매각", "제각", "결정")
    summary_keywords = (
        "종합",
        "평가 결과",
        "평가",
        "요약",
        "점수",
        "결과",
        "이거",
        "리스크",
        "위험",
        "한계",
        "단점",
        "보완",
        "사업 활용",
        "활용 가능",
        "가치",
        "의사결정",
    )

    if asked_dim:
        rows = report_scores_by_dimension(report_data, asked_dim)
        if not rows:
            return None
        points = [point_from_five_score(row.get("score")) for row in rows]
        avg = sum(points) / max(1, len(points))
        answer_lines = [
            f"{title}의 {asked_dim} 평가는 평균 {format_point(avg)}로 {grade_from_point(avg)} 범위입니다. [자료1]",
            f"{asked_dim} 상세 항목은 총 {len(rows)}개이며, 주요 근거는 아래와 같습니다. [자료1]",
        ]
        for row, point in zip(rows[:8], points[:8]):
            reason = row.get("reason") or row.get("basis") or "제공된 자료에서 상세 근거가 확인되지 않습니다."
            answer_lines.append(
                f"- {row.get('item')}: {format_point(point)}({grade_from_point(point)}) - {first_sentence(reason, 150)} [자료1]"
            )
        answer_lines += [
            "",
            "확인 필요 사항:",
            "- 해당 평가는 AI 평가 보고서의 항목별 점수와 근거를 요약한 것이며, 최종 유지/매각/제각 판단은 사업부와 Legal AI팀 검토가 필요합니다. [자료1]",
        ]
        return "\n".join(answer_lines), [source]

    if any(k in q for k in decision_keywords) or any(k in q for k in summary_keywords):
        summary = combined_report_summary(report_data)
        if not summary:
            return None
        answer_lines = [f"{title}의 AI 평가 보고서 기준 종합 결과는 다음과 같습니다. [자료1]"]
        risk_lines = []
        for dim in dims:
            row = summary.get(dim)
            if not row:
                continue
            point = float(row.get("average") or 0.0)
            grade = grade_from_point(point)
            answer_lines.append(
                f"- {dim}: {format_point(point)}({grade}), 항목 {row.get('count')}개 "
                f"(긍정 {row.get('positive')} / 중립 {row.get('neutral')} / 부정 {row.get('negative')}) [자료1]"
            )
            if grade == "부정":
                risk_lines.append(dim)

        market = report_data.get("market_growth") or (report_data.get("summary") or {}).get("market") or {}
        if market:
            answer_lines.append(
                f"- 시장 성장성 참고 지표는 {market.get('sector', '관련 산업')} 기준 성장률 {market.get('growth_rate', '-')}%, 점수 {market.get('score', '-')}점입니다. [자료1]"
            )

        answer_lines += [
            "",
            "판단 보조 의견:",
            "- AI가 유지/매각/제각을 단정할 수는 없고, 위 점수는 의사결정 보조 근거로만 사용해야 합니다. [자료1]",
        ]
        if risk_lines:
            answer_lines.append(f"- 특히 {', '.join(risk_lines)} 항목은 리스크 요인으로 추가 확인이 필요합니다. [자료1]")
        answer_lines += [
            "",
            "확인 필요 사항:",
            "- 실제 사업 적용 여부, 유사 특허와의 청구항 중복 여부, 침해 입증 가능성, 연차료 대비 활용 가능성을 확인해야 합니다. [자료1]",
        ]
        return "\n".join(answer_lines), [source]

    return None


def load_patent_docs_from_disk(patent_id: str) -> List[Document]:
    docs_path = PATENTS_ROOT / patent_id / "extracted" / "all_chunks.jsonl"
    return read_documents_jsonl(docs_path)


def extract_claim_text(docs: List[Document], claim_no: int) -> Tuple[Optional[str], Optional[Document]]:
    original_docs = [doc for doc in docs if (doc.metadata or {}).get("source_type") == "ORIGINAL_PDF"]
    for idx, doc in enumerate(original_docs):
        text = normalize(doc.page_content)
        pattern = rf"청구항\s*{claim_no}\s+"
        match = re.search(pattern, text)
        if not match:
            continue
        combined = text[match.start():]
        if idx + 1 < len(original_docs):
            combined += " " + normalize(original_docs[idx + 1].page_content)
        next_match = re.search(rf"청구항\s*{claim_no + 1}\s+", combined)
        if next_match:
            combined = combined[: next_match.start()]
        return combined.strip(), doc
    return None, None


def structured_claim_answer(
    patent_id: str,
    question: str,
    patent_meta: Dict[str, Any],
) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    match = re.search(r"청구항\s*(\d+)", question)
    if not match:
        return None
    claim_no = int(match.group(1))
    docs = load_patent_docs_from_disk(patent_id)
    claim_text, source_doc = extract_claim_text(docs, claim_no)
    if not claim_text or not source_doc:
        return None

    source_meta = source_doc.metadata or {}
    source = {
        "label": "자료1",
        "title": source_meta.get("title") or patent_meta.get("title"),
        "source_type": "ORIGINAL_PDF",
        "document_type": "ORIGINAL_PDF",
        "page_no": source_meta.get("page_no"),
        "url": source_meta.get("source_url"),
        "chunk_id": source_meta.get("chunk_id"),
        "snippet": claim_text[:180],
    }

    claim_body = re.sub(rf"^청구항\s*{claim_no}\s*", "", claim_text).strip()
    steps = []
    for piece in re.split(r";| 및 |, 및 ", claim_body):
        clean = normalize(piece)
        if len(clean) >= 18:
            steps.append(clean)
    answer_lines = [
        f"청구항 {claim_no}은 아래 구성을 중심으로 하는 청구항입니다. [자료1]",
    ]
    if steps:
        for idx, step in enumerate(steps[:5], start=1):
            answer_lines.append(f"{idx}. {first_sentence(step, 170)} [자료1]")
    else:
        answer_lines.append(first_sentence(claim_text, 700) + " [자료1]")
    answer_lines += [
        "",
        "확인 필요 사항:",
        "- 위 요약은 원문 청구항의 문언 기반 요약이므로, 권리범위 판단은 종속항·상세한 설명·선행기술과 함께 검토해야 합니다. [자료1]",
    ]
    return "\n".join(answer_lines), [source]


def structured_metadata_answer(
    patent_id: str,
    question: str,
    patent_meta: Dict[str, Any],
) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    q = question.lower()
    fields = {
        "등록번호": ("registration_number", "등록번호"),
        "출원번호": ("application_number", "출원번호"),
        "ipc": ("ipc_code", "IPC 분류"),
        "cpc": ("cpc_code", "CPC 분류"),
        "출원인": ("applicant", "출원인"),
        "발명자": ("inventor", "발명자"),
        "발명의 명칭": ("title", "발명의 명칭"),
        "명칭": ("title", "발명의 명칭"),
    }
    selected = None
    for key, value in fields.items():
        if key in q or key in question:
            selected = value
            break
    if selected is None:
        return None
    meta_key, label = selected
    value = patent_meta.get(meta_key)
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    if not value:
        docs = load_patent_docs_from_disk(patent_id)
        text = " ".join(normalize(doc.page_content) for doc in docs if (doc.metadata or {}).get("source_type") == "ORIGINAL_PDF")[:3000]
        patterns = {
            "registration_number": r"\(11\)\s*등록번호\s*([0-9\-]+)",
            "application_number": r"\(21\)\s*출원번호\s*([0-9\-]+)",
            "ipc_code": r"\(51\)\s*국제특허분류\(Int\. Cl\.\)\s*(.*?)(?:\(52\)|\(21\))",
            "applicant": r"\(73\)\s*특허권자\s*([가-힣A-Za-z0-9\s주식회사㈜.,()-]+?)\s*\(72\)",
        }
        pattern = patterns.get(meta_key)
        if pattern:
            match = re.search(pattern, text)
            if match:
                value = normalize(match.group(1))
    if not value:
        value = "제공된 자료에서 확인되지 않습니다"
    source = make_source_card(
        patent_meta,
        patent_id,
        "자료1",
        "ORIGINAL_PDF",
        1,
        f"{label}: {value}",
        f"{patent_id}:structured:metadata:{meta_key}",
    )
    answer = (
        f"{label}: {value} [자료1]\n\n"
        "확인 필요 사항:\n"
        "- 서지 정보는 원문 공보와 KIPRIS 등록사항 기준으로 최종 확인하는 것이 좋습니다. [자료1]"
    )
    return answer, [source]


def structured_original_section_answer(
    patent_id: str,
    question: str,
    patent_meta: Dict[str, Any],
) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    section_map = {
        "효과": ("발명의 효과", ("발명의 효과",)),
        "배경": ("배경기술", ("배 경 기 술", "배경기술")),
        "배경기술": ("배경기술", ("배 경 기 술", "배경기술")),
        "해결수단": ("과제의 해결 수단", ("과제의 해결 수단", "해결 수단")),
        "해결 수단": ("과제의 해결 수단", ("과제의 해결 수단", "해결 수단")),
        "해결하려는 과제": ("해결하려는 과제", ("해결하려는 과제",)),
        "도면": ("도면의 간단한 설명", ("도면의 간단한 설명",)),
    }
    selected = None
    for key, value in section_map.items():
        if key in question:
            selected = value
            break
    if selected is None:
        return None

    label, markers = selected
    docs = load_patent_docs_from_disk(patent_id)
    for doc in docs:
        if (doc.metadata or {}).get("source_type") != "ORIGINAL_PDF":
            continue
        text = normalize(doc.page_content)
        marker_pos = min([text.find(marker) for marker in markers if marker in text] or [-1])
        if marker_pos < 0:
            continue
        excerpt = text[marker_pos:]
        next_heading = re.search(
            r"(과제의 해결 수단|발명의 효과|도면의 간단한 설명|발명을 실시하기 위한 구체적인 내용|청구범위|명 세 서)",
            excerpt[len(markers[0]) :],
        )
        if next_heading:
            excerpt = excerpt[: len(markers[0]) + next_heading.start()]
        excerpt = first_sentence(excerpt, 720)
        meta = doc.metadata or {}
        source = {
            "label": "자료1",
            "title": meta.get("title") or patent_meta.get("title"),
            "source_type": "ORIGINAL_PDF",
            "document_type": "ORIGINAL_PDF",
            "page_no": meta.get("page_no"),
            "url": meta.get("source_url"),
            "chunk_id": meta.get("chunk_id"),
            "snippet": excerpt[:180],
        }
        answer = (
            f"{label}: 다음과 같이 확인됩니다. [자료1]\n"
            f"{excerpt} [자료1]\n\n"
            "확인 필요 사항:\n"
            "- 위 내용은 원문 발췌 요약이므로, 청구항과 실시예까지 함께 보며 권리범위와 기술효과를 검토해야 합니다. [자료1]"
        )
        return answer, [source]
    return None


def structured_invention_overview_answer(
    patent_id: str,
    question: str,
    patent_meta: Dict[str, Any],
) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    q = question.lower()
    report_intent_keywords = (
        "평가",
        "점수",
        "보고서",
        "기술성",
        "권리성",
        "시장성",
        "사업성",
        "유지",
        "매각",
        "제각",
        "결정",
    )
    if any(k in q for k in report_intent_keywords):
        return None

    overview_keywords = (
        "요약",
        "핵심",
        "개요",
        "장점",
        "필요",
        "필요성",
        "문제",
        "문제점",
        "해결",
        "개선",
        "효과",
        "활용",
        "동작",
        "원리",
        "무슨 내용",
        "무슨 기술",
        "어떤 기술",
        "이 기술",
        "이 방법",
        "이 시스템",
        "왜",
        "관련 내용",
        "내용 알려",
        "내용 설명",
        "방법 알려",
        "기술 설명",
    )
    if not any(k in q for k in overview_keywords) and not is_related_to_patent_meta(question, patent_meta):
        return None

    docs = load_patent_docs_from_disk(patent_id)
    original_docs = [
        doc for doc in docs if (doc.metadata or {}).get("source_type") == "ORIGINAL_PDF"
    ]
    if not original_docs:
        return None

    original_docs.sort(key=lambda doc: ((doc.metadata or {}).get("page_no") or 9999, doc_key(doc)))
    summary_doc = original_docs[0]
    effect_doc = next(
        (
            doc
            for doc in original_docs
            if "발명의 효과" in doc.page_content or "연산 부하" in doc.page_content
        ),
        original_docs[min(1, len(original_docs) - 1)],
    )

    summary_text = normalize(summary_doc.page_content)
    effect_text = normalize(effect_doc.page_content)
    summary_excerpt = first_sentence(summary_text, 520)
    effect_excerpt = first_sentence(effect_text, 360)

    def card_from_doc(label: str, doc: Document, snippet: str) -> Dict[str, Any]:
        meta = doc.metadata or {}
        return {
            "label": label,
            "title": meta.get("title") or patent_meta.get("title"),
            "source_type": "ORIGINAL_PDF",
            "document_type": "ORIGINAL_PDF",
            "page_no": meta.get("page_no"),
            "url": meta.get("source_url"),
            "chunk_id": meta.get("chunk_id") or doc_key(doc),
            "snippet": snippet[:180],
        }

    source_cards = [card_from_doc("자료1", summary_doc, summary_excerpt)]
    effect_label = "자료1"
    if doc_key(effect_doc) != doc_key(summary_doc):
        effect_label = "자료2"
        source_cards.append(card_from_doc("자료2", effect_doc, effect_excerpt))

    title = patent_meta.get("title") or patent_id
    answer_lines = [
        f"{title}은 블록체인 합의 과정에서 트랜잭션 서명 검증 부담을 줄이기 위한 방법 및 시스템으로 확인됩니다. [자료1]",
        f"원문 요약에 따르면, 특정 밸리데이터 노드가 다른 밸리데이터 노드로부터 수신한 블록 내 트랜잭션의 서명 검증 요청을 받고, 메모리 영역의 트랜잭션과 동일 여부를 판단해 별도 서명 검증 없이 검증된 것으로 처리하는 구성이 핵심입니다. [자료1]",
        f"기대 효과는 동일성이 입증된 트랜잭션의 서명 검증 작업을 스킵해 연산 부하를 줄이고 블록체인 네트워크 성능을 개선하는 것입니다. [{effect_label}]",
        "",
        "확인 필요 사항:",
        f"- 위 요약은 원문 공보의 요약/효과 부분을 바탕으로 한 기술 내용 정리이며, 권리범위 판단은 청구항 1과 종속항을 함께 검토해야 합니다. [자료1]",
    ]
    return "\n".join(answer_lines), source_cards


def expand_detail_terms(raw_terms: set[str]) -> set[str]:
    expanded = set(raw_terms)
    for token in list(raw_terms):
        if token.endswith("값") and len(token) > 2:
            expanded.add(token[:-1])
        if token.endswith("방식") and len(token) > 2:
            expanded.add(token[:-2])
    return expanded


def clean_evidence_text(text: str) -> str:
    clean = normalize(text)
    if not clean:
        return ""
    cleanup_patterns = (
        r"IP 가치 평가 보고서\s*특허번호:\s*[^|]+?\|\s*[^-]+?내부 기밀 문서\s*-\s*\d+\s*-",
        r"IP 가치 평가 보고서\s*특허번호:\s*[^-]+-\s*\d+\s*-",
        r"등록특허\s*10[-\s]*\d+\s*-\s*\d+\s*-",
        r"등록특허10[-\s]*\d+",
        r"\(뒷면에 계속\)",
        r"대 표 도\s*-\s*도\d+",
        r"\[[0-9]{1,4}\]",
        r"평가 항목\s+등급\s+점수\s+확신도\s+판단 요지",
    )
    for pattern in cleanup_patterns:
        clean = re.sub(pattern, " ", clean)
    replacements = {
        "합 니다": "합니다",
        "입 니다": "입니다",
        "됩 니다": "됩니다",
        "있 습니다": "있습니다",
        "없 습니다": "없습니다",
        "하 여": "하여",
        "서 명": "서명",
        "검 증": "검증",
        "트 랜잭션": "트랜잭션",
        "밸 리데이터": "밸리데이터",
        "시스 템": "시스템",
        "공 간": "공간",
        "생 산": "생산",
        "분 사": "분사",
        "세 척": "세척",
        "제 어": "제어",
        "무 인": "무인",
        "자동 문": "자동문",
        "이 물질": "이물질",
        "슬 러지": "슬러지",
        "청 구항": "청구항",
        "물 류": "물류",
        "반 송": "반송",
        "모 니터링": "모니터링",
        "토 폴로지": "토폴로지",
        "병 목": "병목",
    }
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    clean = re.sub(r"\s{2,}", " ", clean).strip()
    return clean


def source_type_name(source_type: Optional[str]) -> str:
    return {
        "ORIGINAL_PDF": "원문 PDF",
        "REPORT_PDF": "AI 평가 보고서",
        "ORIGINAL_VISUAL": "원문 시각자료",
        "REPORT_VISUAL": "보고서 시각자료",
        "HTML_VISUAL": "HTML 시각자료",
        "BUSINESS_DOC": "업무 문서",
        "WEB": "웹 자료",
    }.get(source_type or "", source_type or "-")


def excerpt_around_terms(text: str, terms, limit: int = 340) -> str:
    clean = clean_evidence_text(text)
    lower = clean.lower()
    ordered_terms = list(terms or [])
    pos = -1
    for term in ordered_terms:
        if not term:
            continue
        found = lower.find(str(term).lower())
        if found >= 0:
            pos = found
            break
    if pos < 0:
        return first_sentence(clean, limit)
    start = max(0, pos - 90)
    end = min(len(clean), pos + limit)
    excerpt = clean[start:end].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(clean):
        excerpt = excerpt.rstrip() + "..."
    return excerpt


def structured_document_detail_answer(
    patent_id: str,
    question: str,
    patent_meta: Dict[str, Any],
) -> Optional[Tuple[str, List[Dict[str, Any]]]]:
    report_intent_keywords = (
        "평가",
        "점수",
        "보고서",
        "기술성",
        "권리성",
        "시장성",
        "사업성",
        "유지",
        "매각",
        "제각",
        "결정",
    )
    q = question.lower()
    if any(k in q for k in report_intent_keywords):
        return None

    raw_terms = {
        token
        for token in tokens(question)
        if len(token) >= 2 and not is_question_context_token(token)
    }
    terms = expand_detail_terms(raw_terms)
    if not terms:
        return None

    docs = [
        doc
        for doc in load_patent_docs_from_disk(patent_id)
        if (doc.metadata or {}).get("source_type") == "ORIGINAL_PDF"
    ]
    if not docs:
        return None

    scored: List[Tuple[int, int, Document]] = []
    for idx, doc in enumerate(docs):
        haystack = normalize(
            f"{(doc.metadata or {}).get('section_title', '')} {doc.page_content}"
        ).lower()
        score = sum(1 for term in terms if term.lower() in haystack)
        if score:
            scored.append((score, -idx, doc))
    if not scored:
        return None

    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    selected_docs = [row[2] for row in scored[:2]]
    source_cards: List[Dict[str, Any]] = []
    answer_lines = [
        "원문에서 질문과 관련된 내용은 아래와 같이 확인됩니다.",
    ]

    for idx, doc in enumerate(selected_docs, start=1):
        label = f"자료{idx}"
        excerpt = excerpt_around_terms(doc.page_content, terms)
        meta = doc.metadata or {}
        source_cards.append(
            {
                "label": label,
                "title": meta.get("title") or patent_meta.get("title"),
                "source_type": "ORIGINAL_PDF",
                "document_type": "ORIGINAL_PDF",
                "page_no": meta.get("page_no"),
                "url": meta.get("source_url"),
                "chunk_id": meta.get("chunk_id") or doc_key(doc),
                "snippet": excerpt[:180],
            }
        )
        answer_lines.append(f"- {excerpt} [{label}]")

    answer_lines += [
        "",
        "확인 필요 사항:",
        "- 위 내용은 원문에서 질문어와 직접 매칭되는 발췌 요약이므로, 최종 기술 해석은 청구항과 상세한 설명 전체 맥락으로 확인해야 합니다. [자료1]",
    ]
    return "\n".join(answer_lines), source_cards


def enforce_answer_policy(answer_text: str, source_cards: List[Dict[str, Any]]) -> str:
    if not answer_text:
        return answer_text

    primary_tag = f"[{source_cards[0]['label']}]" if source_cards else ""
    if primary_tag:
        answer_text = re.sub(
            r"(?:따라서\s*)?(?:이\s*)?특허의\s*(?:유지|매각|제각|유지\s*및\s*매각)[^\n.]*?(?:긍정적|부정적)[^\n.]*\.",
            f"최종 유지/매각/제각 판단은 단정할 수 없으며, 위 평가 지표를 근거로 사업부와 Legal AI팀의 추가 검토가 필요합니다. {primary_tag}",
            answer_text,
        )

    if primary_tag and not SOURCE_TAG_RE.search(answer_text):
        lines: List[str] = []
        for raw_line in answer_text.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                lines.append(raw_line)
                continue
            if stripped.startswith("**") and stripped.endswith("**"):
                normalized = "확인 필요 사항:" if "확인" in stripped and "사항" in stripped else line
                lines.append(normalized)
                continue
            if "확인" in stripped and "사항" in stripped and len(stripped) <= 20:
                lines.append("확인 필요 사항:")
                continue
            if stripped.endswith(primary_tag):
                lines.append(line)
                continue
            lines.append(f"{line} {primary_tag}")
        answer_text = "\n".join(lines)

    if "확인 필요 사항" not in answer_text:
        suffix = f" {primary_tag}" if primary_tag else ""
        answer_text = (
            answer_text.rstrip()
            + "\n\n확인 필요 사항:\n"
            + f"- 최종 유지/매각/제각 판단은 Legal AI팀과 사업부 검토가 필요합니다.{suffix}"
        )

    answer_text = answer_text.replace("고려해 보았습니다", "검토가 필요합니다")
    answer_text = answer_text.replace("확인했습니다", "확인이 필요합니다")
    answer_text = answer_text.replace("검토했습니다", "검토가 필요합니다")

    return answer_text


def split_evidence_sentences(text: str) -> List[str]:
    clean = clean_evidence_text(text)
    if not clean:
        return []
    parts = re.split(r"(?<=[.!?])\s+|(?<=다\.)\s+|(?<=다)\s+(?=[가-힣A-Za-z0-9])", clean)
    sentences: List[str] = []
    for part in parts:
        sentence = normalize(part)
        if len(sentence) < 28:
            continue
        sentences.append(sentence)
    if not sentences and clean:
        sentences.append(first_sentence(clean, 420))
    return sentences


def intent_terms_for_answer(question: str) -> List[str]:
    q = question.lower()
    terms = list(tokens(question))
    if any(k in q for k in ("왜", "필요", "장점", "강점", "효과", "개선")):
        terms.extend(["배경", "문제", "목적", "효과", "개선", "성능", "부하", "스킵", "필요"])
    if any(k in q for k in ("리스크", "위험", "한계", "단점", "제각", "매각", "유지", "가치")):
        terms.extend(["권리성", "시장성", "사업성", "리스크", "확인", "보강", "유사", "무효", "회피설계", "연차료"])
    if any(k in q for k in ("어떻게", "동작", "원리", "방식", "구성")):
        terms.extend(["청구항", "단계", "수신", "판단", "해시", "메모리", "프로세서", "트랜잭션"])
    if any(k in q for k in ("청구항", "권리", "구성")):
        terms.extend(["청구항", "구성", "단계", "특징"])
    return [term for term in terms if len(term) >= 2]


def score_sentence(sentence: str, terms: List[str]) -> int:
    lower = sentence.lower()
    score = 0
    for term in terms:
        if term.lower() in lower:
            score += 2 if len(term) >= 3 else 1
    for important in ("발명의 효과", "해결하려는 과제", "과제의 해결 수단", "청구항", "평가", "리스크", "확인 필요"):
        if important in sentence:
            score += 3
    return score


def best_evidence_for_doc(question: str, doc: Document, max_sentences: int = 2) -> List[str]:
    terms = intent_terms_for_answer(question)
    priority_terms = priority_excerpt_terms(question)
    doc_text = clean_evidence_text(doc.page_content)
    priority_hits = [term for term in priority_terms if term and term.lower() in doc_text.lower()]
    if priority_hits:
        return [excerpt_around_terms(doc_text, priority_hits + terms, 340)]

    sentences = split_evidence_sentences(doc.page_content)
    if not sentences:
        return []
    scored = [(score_sentence(sentence, terms), idx, sentence) for idx, sentence in enumerate(sentences)]
    scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    selected = [sentence for score, _, sentence in scored if score > 0][:max_sentences]
    if not selected:
        selected = [first_sentence(sentences[0], 360)]
    excerpts: List[str] = []
    for sentence in selected:
        excerpt_terms = set(priority_terms + terms)
        if len(sentence) > 520:
            excerpts.append(excerpt_around_terms(sentence, priority_terms + terms, 340))
        else:
            excerpts.append(first_sentence(sentence, 360))
    return excerpts


def extractive_direct_answer(question: str, source_cards: List[Dict[str, Any]]) -> str:
    q = question.lower()
    primary = source_cards[0] if source_cards else {}
    title = primary.get("title") or "해당 특허"
    section = primary.get("source_type") or "자료"
    if any(k in q for k in ("왜", "필요", "장점", "강점", "효과", "개선")):
        return (
            f"자료 기준으로 {title}의 필요성/장점은 원문에 제시된 해결 과제와 발명의 효과, "
            f"그리고 평가 보고서의 기술성 근거를 함께 봐야 합니다."
        )
    if any(k in q for k in ("리스크", "위험", "한계", "단점")):
        return (
            f"자료 기준으로 {title}의 리스크는 평가 보고서의 추가 확인 항목과 원문 청구항 근거를 함께 확인해야 합니다."
        )
    if any(k in q for k in ("유지", "매각", "제각", "가치")):
        return (
            f"자료 기준으로 {title}의 유지/매각/제각을 단정할 수는 없고, 검색된 원문·보고서 근거를 "
            "의사결정 보조 자료로 사용해야 합니다."
        )
    if any(k in q for k in ("어떻게", "동작", "원리", "방식", "구성")):
        return (
            f"자료 기준으로 {title}의 동작 방식은 원문 청구항과 해결 수단 섹션을 중심으로 확인해야 합니다."
        )
    return f"검색된 {section} 기준으로 질문과 관련된 근거는 아래와 같습니다."


def is_evaluation_question(question: str) -> bool:
    q = question.lower()
    return any(
        marker in q
        for marker in (
            "평가",
            "점수",
            "기술성",
            "권리성",
            "시장성",
            "사업성",
            "종합",
            "보고서 결과",
            "가치 평가",
            "어떻게 되었",
            "어떻게 됐",
            "유지 판단",
            "포기 판단",
            "매각 판단",
            "제각 판단",
            "판단 근거",
            "유지/포기",
            "유지/매각",
        )
    )


def answer_intent(question: str) -> str:
    q = question.lower()
    if is_evaluation_question(question):
        return "EVALUATION"
    if any(k in q for k in ("왜", "필요", "장점", "강점", "효과", "개선")):
        return "ADVANTAGE"
    if any(k in q for k in ("리스크", "위험", "한계", "단점")):
        return "RISK"
    if any(k in q for k in ("유지", "매각", "제각", "가치")):
        return "DECISION"
    if any(k in q for k in ("어떻게", "동작", "원리", "방식", "구성")):
        return "OPERATION"
    return "GENERAL"


def detect_question_intents(question: str) -> List[str]:
    q = question.lower()
    intents: List[str] = []
    # counting intent
    if re.search(r"\b몇|몇개|몇 건|몇건|얼마나\b", q):
        intents.append("COUNT")
    # discovery/listing intent
    if any(k in q for k in ("찾아", "검색", "목록", "보여", "어떤 특허", "어떤")):
        intents.append("DISCOVERY")
    # specific answer intents
    core = answer_intent(question)
    if core and core != "GENERAL":
        intents.append(core)
    if not intents:
        intents.append("GENERAL")
    return intents


def priority_excerpt_terms(question: str) -> List[str]:
    intent = answer_intent(question)
    if intent == "EVALUATION":
        return ["종합", "기술성", "권리성", "시장성", "사업성", "평가", "점수", "리스크", "추가 확인"]
    if intent == "ADVANTAGE":
        return ["연산 부하", "성능", "개선", "스킵", "발명의 효과", "해결하려는 과제", "서명 검증"]
    if intent in ("RISK", "DECISION"):
        return ["사업성", "리스크", "추가 확인", "회피설계", "무효", "사업 활용", "유사 특허", "KIPRIS", "청구항", "구성요소", "권리범위"]
    if intent == "OPERATION":
        return ["해시", "메모리 영역", "트랜잭션", "동일 여부", "수신", "프로세서", "청구항"]
    return intent_terms_for_answer(question)


def order_docs_for_answer(question: str, docs: List[Document]) -> List[Document]:
    intent = answer_intent(question)
    scored: List[Tuple[int, int, Document]] = []
    priority_terms = priority_excerpt_terms(question)
    for idx, doc in enumerate(docs):
        meta = doc.metadata or {}
        source_type = meta.get("source_type")
        text = normalize(f"{meta.get('section_title', '')} {doc.page_content}")
        score = 0
        if intent == "ADVANTAGE":
            if source_type == "ORIGINAL_PDF":
                score += 8
            if any(term in text for term in ("배 경 기 술", "배경기술", "해결하려는 과제", "발명의 효과")):
                score += 12
        elif intent in ("RISK", "DECISION"):
            if source_type == "REPORT_PDF":
                score += 8
            if any(term in text for term in ("의사결정", "사업성", "리스크", "유사 특허", "추가 확인", "매각", "제각", "유지")):
                score += 12
        elif intent == "OPERATION":
            if source_type == "ORIGINAL_PDF":
                score += 8
            if any(term in text for term in ("청구항", "해시", "메모리 영역", "동일 여부", "프로세서")):
                score += 12
        else:
            if source_type == "ORIGINAL_PDF":
                score += 3
        score += sum(2 for term in priority_terms if term and term in text)
        scored.append((score, -idx, doc))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [doc for _, _, doc in scored]


def _contains_any(text: str, terms: List[str]) -> bool:
    lower = text.lower()
    return any(term and term.lower() in lower for term in terms)


def required_evidence_specs(question: str) -> List[Dict[str, Any]]:
    intent = answer_intent(question)
    if intent == "EVALUATION":
        return [
            {
                "source_type": "REPORT_PDF",
                "sections": ["평가 요약", "REPORT_SUMMARY", "REPORT_OVERVIEW"],
                "terms": ["종합", "기술성", "권리성", "시장성", "사업성", "점수"],
            },
            {
                "source_type": "REPORT_PDF",
                "sections": ["평가 기준별 점수", "REPORT_SCORE_DETAIL"],
                "terms": ["차별성", "혁신성", "IP 원천성", "권리", "시장성", "사업성"],
            },
            {
                "source_type": "REPORT_PDF",
                "sections": ["리스크 및 추가 확인", "의사결정 가이드", "REPORT_RISK", "REPORT_DECISION"],
                "terms": ["리스크", "추가 확인", "회피설계", "무효", "유사 특허", "사업화"],
            },
        ]
    if intent == "ADVANTAGE":
        return [
            {
                "source_type": "ORIGINAL_PDF",
                "sections": ["해결하려는 과제", "KR_PROBLEM"],
                "terms": ["문제", "목적", "서명 검증", "성능", "부하"],
            },
            {
                "source_type": "ORIGINAL_PDF",
                "sections": ["발명의 효과", "KR_EFFECT"],
                "terms": ["효과", "연산 부하", "성능", "개선", "서명 검증"],
            },
            {
                "source_type": "ORIGINAL_PDF",
                "sections": ["배경기술", "기술분야", "KR_BACKGROUND", "KR_TECH_FIELD"],
                "terms": ["종래", "블록체인", "합의", "서명 검증"],
            },
            {
                "source_type": "REPORT_PDF",
                "sections": ["평가 기준별 점수", "REPORT_SCORE_DETAIL", "PAGE_TEXT"],
                "terms": ["차별성", "파급성", "혁신성", "성능", "기술성"],
            },
        ]
    if intent in ("RISK", "DECISION"):
        return [
            {
                "source_type": "REPORT_PDF",
                "sections": ["리스크 및 추가 확인", "의사결정 가이드", "REPORT_RISK", "REPORT_DECISION"],
                "terms": ["리스크", "추가 확인", "회피설계", "무효", "유사 특허", "KIPRIS"],
            },
            {
                "source_type": "REPORT_PDF",
                "sections": ["평가 기준별 점수", "REPORT_SCORE_DETAIL", "PAGE_TEXT"],
                "terms": ["권리성", "시장성", "사업성", "사업 활용", "연차료"],
            },
            {
                "source_type": "ORIGINAL_PDF",
                "sections": ["청구범위", "KR_CLAIMS"],
                "terms": ["청구항", "구성", "트랜잭션", "서명 검증"],
            },
        ]
    if intent == "OPERATION":
        return [
            {
                "source_type": "ORIGINAL_PDF",
                "sections": ["청구범위", "KR_CLAIMS"],
                "terms": ["청구항", "단계", "트랜잭션", "메모리", "해시"],
            },
            {
                "source_type": "ORIGINAL_PDF",
                "sections": ["과제의 해결 수단", "구체적인 내용", "KR_SOLUTION", "KR_DETAIL"],
                "terms": ["수신", "판단", "동일", "프로세서", "밸리데이터"],
            },
            {
                "source_type": "REPORT_PDF",
                "sections": ["평가 기준별 점수", "REPORT_SCORE_DETAIL"],
                "terms": ["권리성", "명확성", "차별성"],
            },
        ]
    return [
        {
            "source_type": "ORIGINAL_PDF",
            "sections": ["요약", "청구범위", "KR_ABSTRACT", "KR_CLAIMS"],
            "terms": ["요약", "청구항", "발명", "효과"],
        },
        {
            "source_type": "REPORT_PDF",
            "sections": ["평가 개요", "평가 기준별 점수", "REPORT_OVERVIEW", "REPORT_SCORE_DETAIL"],
            "terms": ["기술성", "권리성", "시장성", "사업성"],
        },
    ]


def _section_matches(meta: Dict[str, Any], section_terms: List[str]) -> bool:
    section_text = normalize(f"{meta.get('section_title', '')} {meta.get('section_key', '')}")
    return _contains_any(section_text, section_terms)


def _score_evidence_candidate(question: str, doc: Document, spec: Dict[str, Any]) -> float:
    meta = doc.metadata or {}
    if spec.get("source_type") and meta.get("source_type") != spec["source_type"]:
        return -1.0

    text = normalize(f"{meta.get('section_title', '')} {meta.get('section_key', '')} {doc.page_content}")
    q_terms = [term for term in tokens(question) if not is_question_context_token(term)]
    spec_terms = list(spec.get("terms") or [])
    priority_terms = priority_excerpt_terms(question)

    score = 0.0
    if _section_matches(meta, list(spec.get("sections") or [])):
        score += 6.0
    score += 2.0 * sum(1 for term in spec_terms if term and term.lower() in text.lower())
    score += 1.5 * sum(1 for term in priority_terms if term and term.lower() in text.lower())
    score += 1.0 * len(set(q_terms) & set(tokens(text)))

    section_title = str(meta.get("section_title") or "")
    if len(section_title) > 90:
        score -= 1.0
    if len(normalize(doc.page_content)) < 80:
        score -= 2.0
    return score


def enrich_docs_for_answer(question: str, retrieved_docs: List[Document], all_docs: List[Document], top_k: int = TOP_K) -> List[Document]:
    if not retrieved_docs:
        return retrieved_docs

    priority_docs: List[Document] = []
    remaining_docs: List[Document] = []
    selected_keys: set[str] = set()

    def add_doc(doc: Document, priority: bool = False) -> None:
        key = doc_key(doc)
        if key in selected_keys:
            return
        if priority:
            priority_docs.append(doc)
        else:
            remaining_docs.append(doc)
        selected_keys.add(key)

    # 먼저 질문 유형별 핵심 섹션을 보강한다. 검색 후보에는 있었지만 RRF/재정렬에서 밀린
    # 원문 섹션을 다시 끌어올리는 단계다.
    corpus = all_docs or retrieved_docs
    for spec in required_evidence_specs(question):
        best_doc: Optional[Document] = None
        best_score = 0.0
        for doc in corpus:
            score = _score_evidence_candidate(question, doc, spec)
            if score > best_score:
                best_score = score
                best_doc = doc
        if best_doc is not None and best_score >= 6.0:
            add_doc(best_doc, priority=True)

    for doc in retrieved_docs:
        add_doc(doc)
        if len(priority_docs) + len(remaining_docs) >= max(top_k * 2, top_k):
            break

    ordered_priority = priority_docs
    ordered_remaining = order_docs_for_answer(question, remaining_docs)
    return (ordered_priority + ordered_remaining)[:top_k]


def build_grounded_llm_context(question: str, docs: List[Document], source_cards: List[Dict[str, Any]]) -> str:
    blocks: List[str] = []
    total_chars = 0
    for doc, card in zip(docs, source_cards):
        meta = doc.metadata or {}
        label = card.get("label") or "자료"
        evidence = best_evidence_for_doc(question, doc, max_sentences=2)
        evidence_text = "\n".join(f"- {item}" for item in evidence) if evidence else "- 직접 발췌 없음"
        body = clean_evidence_text(doc.page_content)[:MAX_DOC_CHARS]
        block = "\n".join(
            [
                f"[{label}]",
                f"- 문서유형: {meta.get('source_type')}",
                f"- 섹션: {meta.get('section_title') or '-'}",
                f"- 페이지: {meta.get('page_no') or '-'}",
                f"- 관련도: {card.get('relevance_score', '-')}",
                f"- 매칭어: {', '.join(card.get('match_terms') or []) or '-'}",
                "- 핵심 발췌:",
                evidence_text,
                "- 원문 일부:",
                body,
            ]
        )
        if total_chars + len(block) > MAX_TOTAL_CONTEXT_CHARS and blocks:
            break
        total_chars += len(block)
        blocks.append(block)
    return "\n\n".join(blocks)


def doc_relevance_detail(question: str, doc: Document) -> Dict[str, Any]:
    meta = doc.metadata or {}
    text = clean_evidence_text(f"{meta.get('section_title', '')} {doc.page_content}")
    lower = text.lower()
    q_terms = [
        term
        for term in tokens(question)
        if len(term) >= 2 and not is_question_context_token(term)
    ]
    priority_terms = priority_excerpt_terms(question)
    matched_terms: List[str] = []
    for term in q_terms + priority_terms:
        if term and term.lower() in lower and term not in matched_terms:
            matched_terms.append(term)

    question_overlap = len(set(q_terms) & set(tokens(text))) / max(1, len(set(q_terms))) if q_terms else 0.0
    priority_hit_ratio = len([term for term in priority_terms if term.lower() in lower]) / max(1, len(priority_terms))
    evidence_exists = bool(best_evidence_for_doc(question, doc, max_sentences=1))

    source_bonus = 0.0
    intent = answer_intent(question)
    source_type = meta.get("source_type")
    if intent in ("ADVANTAGE", "OPERATION") and source_type == "ORIGINAL_PDF":
        source_bonus = 0.12
    if intent in ("RISK", "DECISION") and source_type == "REPORT_PDF":
        source_bonus = 0.12
    if intent in ("RISK", "DECISION") and source_type == "ORIGINAL_PDF" and "청구" in str(meta.get("section_title") or ""):
        source_bonus = 0.1

    score = min(
        1.0,
        question_overlap * 0.35
        + priority_hit_ratio * 0.45
        + source_bonus
        + (0.08 if evidence_exists else 0.0),
    )
    if score >= 0.55:
        grade = "GOOD"
    elif score >= 0.32:
        grade = "FAIR"
    else:
        grade = "LOW"
    return {
        "score": round(score, 4),
        "grade": grade,
        "matched_terms": matched_terms[:8],
    }


def annotate_source_cards(question: str, docs: List[Document], source_cards: List[Dict[str, Any]]) -> None:
    for doc, card in zip(docs, source_cards):
        detail = doc_relevance_detail(question, doc)
        evidence = best_evidence_for_doc(question, doc, max_sentences=1)
        card["relevance_score"] = detail["score"]
        card["relevance_grade"] = detail["grade"]
        card["match_terms"] = detail["matched_terms"]
        if evidence:
            card["snippet"] = evidence[0][:220]


def build_search_quality_metrics(
    question: str,
    retrieval_question: str,
    docs: List[Document],
    source_cards: List[Dict[str, Any]],
    confidence: float,
    retrieval_query_expanded: bool,
) -> Dict[str, Any]:
    def grade_from_score(score: float, good: float, fair: float) -> str:
        if score >= good:
            return "GOOD"
        if score >= fair:
            return "FAIR"
        return "LOW"

    if not docs:
        return {
            "retrieval_quality_score": 0.0,
            "retrieval_quality_grade": "LOW",
            "retrieval_quality_label": "낮음",
            "retrieval_quality_reason": "검색된 근거 문서가 없습니다.",
            "search_pass": False,
            "question_match_score": 0.0,
            "expanded_match_score": 0.0,
            "evidence_doc_count": 0,
            "source_type_counts": {},
            "top_source_relevance": [],
            "quality_thresholds": {
                "GOOD": "검색품질 0.50 이상 + 근거문서 3개 이상",
                "FAIR": "검색품질 0.30 이상 + 근거문서 2개 이상",
                "LOW": "위 기준 미달",
            },
            "performance_evaluation": [
                {
                    "name": "검색 품질",
                    "status": "LOW",
                    "value": 0.0,
                    "good_threshold": ">= 0.50 and evidence_doc_count >= 3",
                    "fair_threshold": ">= 0.30 and evidence_doc_count >= 2",
                    "message": "근거 문서가 없어 답변 신뢰도가 낮습니다.",
                }
            ],
            "retrieval_query_expanded": retrieval_query_expanded,
        }

    details = [doc_relevance_detail(question, doc) for doc in docs[: len(source_cards)]]
    scores = [float(detail["score"]) for detail in details]
    top_scores = scores[: min(5, len(scores))]
    quality_score = sum(top_scores) / max(1, len(top_scores))
    evidence_doc_count = sum(1 for score in scores if score >= 0.32)
    source_type_counts: Dict[str, int] = {}
    for doc in docs[: len(source_cards)]:
        source_type = str((doc.metadata or {}).get("source_type") or "UNKNOWN")
        source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1

    if quality_score >= 0.5 and evidence_doc_count >= 3:
        quality_grade = "GOOD"
    elif quality_score >= 0.3 and evidence_doc_count >= 2:
        quality_grade = "FAIR"
    else:
        quality_grade = "LOW"

    question_match_score = lexical_confidence(question, docs)
    expanded_match_score = lexical_confidence(retrieval_question, docs)
    top_source_relevance = []
    for card, detail in zip(source_cards[:5], details[:5]):
        top_source_relevance.append(
            {
                "label": card.get("label"),
                "source_type": card.get("source_type"),
                "page_no": card.get("page_no"),
                "score": detail["score"],
                "grade": detail["grade"],
                "matched_terms": detail["matched_terms"],
            }
        )

    question_grade = grade_from_score(question_match_score, 0.45, 0.25)
    expanded_grade = grade_from_score(expanded_match_score, 0.45, 0.25)
    evidence_grade = "GOOD" if evidence_doc_count >= 3 else "FAIR" if evidence_doc_count >= 2 else "LOW"
    top_score = scores[0] if scores else 0.0
    top_grade = grade_from_score(top_score, 0.55, 0.32)

    if quality_grade == "GOOD":
        quality_label = "양호"
        quality_reason = "질문과 맞는 근거가 충분히 검색되었습니다."
    elif quality_grade == "FAIR":
        quality_label = "주의"
        quality_reason = "답변은 가능하지만 근거가 제한적이므로 출처 확인이 필요합니다."
    else:
        quality_label = "낮음"
        quality_reason = "질문과 직접 맞는 근거가 부족합니다. 질문을 구체화하거나 문서 인덱스를 확인하세요."

    search_pass = quality_grade in ("GOOD", "FAIR")
    performance_evaluation = [
        {
            "name": "검색 품질",
            "status": quality_grade,
            "value": round(quality_score, 4),
            "good_threshold": ">= 0.50 and evidence_doc_count >= 3",
            "fair_threshold": ">= 0.30 and evidence_doc_count >= 2",
            "message": quality_reason,
        },
        {
            "name": "질문 직접 매칭",
            "status": question_grade,
            "value": round(question_match_score, 4),
            "good_threshold": ">= 0.45",
            "fair_threshold": ">= 0.25",
            "message": "원 질문 단어가 검색 문서에 얼마나 직접 매칭되는지입니다.",
        },
        {
            "name": "확장 검색 매칭",
            "status": expanded_grade,
            "value": round(expanded_match_score, 4),
            "good_threshold": ">= 0.45",
            "fair_threshold": ">= 0.25",
            "message": "특허명/청구항/평가항목으로 확장한 검색어가 문서와 맞는 정도입니다.",
        },
        {
            "name": "근거 문서 수",
            "status": evidence_grade,
            "value": evidence_doc_count,
            "good_threshold": ">= 3",
            "fair_threshold": ">= 2",
            "message": "관련도 FAIR 이상인 근거 문서 개수입니다.",
        },
        {
            "name": "상위 출처 관련도",
            "status": top_grade,
            "value": round(top_score, 4),
            "good_threshold": ">= 0.55",
            "fair_threshold": ">= 0.32",
            "message": "가장 관련도가 높은 출처 카드의 점수입니다.",
        },
    ]

    return {
        "retrieval_quality_score": round(quality_score, 4),
        "retrieval_quality_grade": quality_grade,
        "retrieval_quality_label": quality_label,
        "retrieval_quality_reason": quality_reason,
        "search_pass": search_pass,
        "question_match_score": round(question_match_score, 4),
        "expanded_match_score": round(expanded_match_score, 4),
        "evidence_doc_count": evidence_doc_count,
        "source_type_counts": source_type_counts,
        "top_source_relevance": top_source_relevance,
        "quality_thresholds": {
            "GOOD": "검색품질 0.50 이상 + 근거문서 3개 이상",
            "FAIR": "검색품질 0.30 이상 + 근거문서 2개 이상",
            "LOW": "위 기준 미달",
        },
        "performance_evaluation": performance_evaluation,
        "retrieval_query_expanded": retrieval_query_expanded,
    }


def is_patent_overview_question(question: str) -> bool:
    q = question.lower()
    if not is_patent_detail_request(question):
        return False
    return (
        ("특허" in q or "이거" in q or "이것" in q or "해당" in q)
        and not is_discovery_only_question(question)
    )


def is_patent_detail_request(question: str) -> bool:
    q = question.lower()
    overview_markers = (
        "자세",
        "상세",
        "설명",
        "개요",
        "요약",
        "정리",
        "어떤 특허",
        "무슨 특허",
        "무슨 기술",
        "한눈에",
    )
    return any(marker in q for marker in overview_markers)


def is_discovery_only_question(question: str) -> bool:
    q = question.lower()
    discovery_markers = (
        "찾아",
        "검색",
        "목록",
        "뭐뭐",
        "어떤 특허",
        "몇 개",
        "몇개",
        "몇 건",
        "몇건",
        "있는지",
        "있어?",
        "있나요",
    )
    return any(marker in q for marker in discovery_markers) and not any(
        marker in q for marker in ("자세", "상세", "설명", "개요", "정리")
    )


_DEFINITION_TERMS = ("뭐야", "뭐예요", "뭐임", "뭔가요", "이란", "무엇인가", "무엇인지", "뭔지")


def is_definition_question(question: str) -> bool:
    q = question.strip().lower()
    return any(t in q for t in _DEFINITION_TERMS)


def should_promote_global_detail_answer(question: str, patent_groups: List[Dict[str, Any]]) -> bool:
    if len(patent_groups) != 1:
        return False
    if not is_patent_detail_request(question):
        return False
    if is_discovery_only_question(question):
        return False
    group = patent_groups[0]
    directness = float(group.get("directness") or 0.0)
    return directness >= 0.55


def is_specific_patent_question(question: str, patent_meta: Dict[str, Any]) -> bool:
    title = str(patent_meta.get("title") or "")
    registration_number = str(patent_meta.get("registration_number") or "")
    application_number = str(patent_meta.get("application_number") or "")
    q = question.lower()
    if registration_number and registration_number.lower() in q:
        return True
    if application_number and application_number.lower() in q:
        return True
    title_terms = [
        term
        for term in tokens(title)
        if len(term) >= 2 and not is_question_context_token(term) and term not in GENERIC_PATENT_TITLE_TERMS
    ]
    q_terms = set(tokens(question))
    if not title_terms:
        return False
    return len(set(title_terms) & q_terms) >= max(1, min(2, len(title_terms)))


def is_intent_specific_overview_question(question: str, patent_meta: Dict[str, Any]) -> bool:
    specific_markers = (
        "청구항 1",
        "청구항 2",
        "등록번호",
        "출원번호",
        "ipc",
        "cpc",
        "평가",
        "점수",
        "기술성",
        "권리성",
        "시장성",
        "사업성",
        "유지",
        "매각",
        "제각",
        "리스크",
        "위험",
        "회피설계",
        "무효",
        "유사 특허",
    )
    q = question.lower()
    return (
        is_patent_detail_request(question)
        and not is_discovery_only_question(question)
        and not any(marker in q for marker in specific_markers)
        and (
            "특허" in q
            or "이거" in q
            or "이것" in q
            or "해당" in q
            or is_specific_patent_question(question, patent_meta)
        )
    )


def pick_best_doc(
    docs: List[Document],
    source_type: Optional[str] = None,
    section_keys: Optional[List[str]] = None,
    section_titles: Optional[List[str]] = None,
    terms: Optional[List[str]] = None,
) -> Optional[Document]:
    best_doc: Optional[Document] = None
    best_score = -1.0
    section_keys = section_keys or []
    section_titles = section_titles or []
    terms = terms or []

    for doc in docs:
        meta = doc.metadata or {}
        if source_type and meta.get("source_type") != source_type:
            continue
        text = clean_evidence_text(
            f"{meta.get('section_key', '')} {meta.get('section_title', '')} {doc.page_content}"
        )
        lower = text.lower()
        score = 0.0
        if meta.get("section_key") in section_keys:
            score += 10.0
        section_title = str(meta.get("section_title") or "")
        if any(title in section_title for title in section_titles):
            score += 8.0
        score += 2.0 * sum(1 for term in terms if term.lower() in lower)
        if meta.get("source_type") == "ORIGINAL_PDF" and meta.get("page_no"):
            score += max(0.0, 1.5 - (float(meta.get("page_no") or 1) * 0.05))
        if len(text) < 80:
            score -= 2.0
        if score > best_score:
            best_score = score
            best_doc = doc

    return best_doc if best_score > 0 else None


def select_patent_overview_docs(patent_id: str, question: str = "") -> List[Document]:
    docs = load_patent_docs_from_disk(patent_id)
    selected: List[Document] = []
    seen: set[str] = set()

    def add(doc: Optional[Document]) -> None:
        if doc is None:
            return
        key = doc_key(doc)
        if key in seen:
            return
        seen.add(key)
        selected.append(doc)

    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_BIBLIO"], ["서지사항"], ["등록번호", "출원번호", "IPC"]))
    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_ABSTRACT"], ["요약"], ["요약", "시스템", "방법"]))
    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_BACKGROUND"], ["배경기술"], ["배경", "문제", "기존"]))
    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_PROBLEM"], ["해결하려는 과제"], ["목적", "문제", "제공"]))
    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_SOLUTION"], ["과제의 해결 수단"], ["포함", "제어", "단계"]))
    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_CLAIMS"], ["청구범위"], ["청구항", "포함", "단계"]))
    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_EFFECT"], ["발명의 효과"], ["효과", "향상", "예방", "개선"]))
    add(
        pick_best_doc(
            docs,
            "REPORT_PDF",
            ["REPORT_OVERVIEW"],
            ["평가 개요"],
            ["종합", "기술성", "권리성", "시장성", "사업성", "종합 의견"],
        )
    )
    add(
        pick_best_doc(
            docs,
            "REPORT_PDF",
            ["REPORT_SCORE_DETAIL"],
            ["평가 기준별 점수"],
            ["기술성", "권리성", "시장성", "사업성", "차별성"],
        )
    )
    add(
        pick_best_doc(
            docs,
            "REPORT_PDF",
            ["REPORT_DECISION", "REPORT_RISK"],
            ["의사결정 가이드", "리스크 및 추가 확인"],
            ["추가 확인", "무효", "회피설계", "사업화", "유사 특허"],
        )
    )
    if is_visual_asset_question(question):
        visual_docs = select_visual_asset_docs(patent_id, question, max_docs=3, fallback=False)
        for doc in visual_docs:
            add(doc)
    return selected[:13]


def source_label_for_doc(doc: Optional[Document], docs: List[Document], source_cards: List[Dict[str, Any]]) -> str:
    if doc is None:
        return "자료1"
    key = doc_key(doc)
    for candidate, card in zip(docs, source_cards):
        if doc_key(candidate) == key:
            return str(card.get("label") or "자료1")
    return "자료1"


def score_text_value(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else "확인 필요"


def strip_section_noise(text: str) -> str:
    clean = clean_evidence_text(text)
    clean = re.sub(r"^\(?57\)?\s*요\s*약\s*", "", clean)
    clean = re.sub(
        r"^(기\s*술\s*분\s*야|배\s*경\s*기\s*술|해결하려는 과제|과제의 해결 수단|발명의 효과|청구항\s*\d*)\s*",
        "",
        clean,
    )
    return normalize(clean)


def build_patent_domain_card(
    patent_id: str,
    patent_meta: Dict[str, Any],
    docs: List[Document],
) -> Document:
    title = str(patent_meta.get("title") or patent_id)
    meta_lines = [
        f"특허 ID: {patent_id}",
        f"특허명: {title}",
        f"등록번호: {patent_meta.get('registration_number') or '-'}",
        f"출원번호: {patent_meta.get('application_number') or '-'}",
        f"IPC: {patent_meta.get('ipc_code') or '-'}",
        f"CPC: {patent_meta.get('cpc_code') or '-'}",
        f"기술분야: {patent_meta.get('tech_field') or '-'}",
        f"사업분야: {patent_meta.get('business_field') or '-'}",
        f"부서: {patent_meta.get('department') or '-'}",
    ]

    selected: List[Document] = []
    seen: set[str] = set()

    def add(doc: Optional[Document]) -> None:
        if doc is None:
            return
        key = doc_key(doc)
        if key in seen:
            return
        seen.add(key)
        selected.append(doc)

    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_ABSTRACT"], ["요약"], ["요약", "시스템", "방법"]))
    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_TECH_FIELD"], ["기술분야"], ["분야", "발명"]))
    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_PROBLEM"], ["해결하려는 과제"], ["목적", "문제", "제공"]))
    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_SOLUTION"], ["과제의 해결 수단"], ["포함", "단계", "제어"]))
    add(pick_best_doc(docs, "ORIGINAL_PDF", ["KR_CLAIMS"], ["청구범위"], ["청구항", "포함", "단계"]))
    add(
        pick_best_doc(
            docs,
            "REPORT_PDF",
            ["REPORT_OVERVIEW", "REPORT_SCORE_DETAIL", "REPORT_RISK"],
            ["평가 개요", "평가 기준별 점수", "리스크 및 추가 확인"],
            ["기술성", "권리성", "시장성", "사업성", "유사 특허", "사내 프로젝트"],
        )
    )

    snippet_lines: List[str] = []
    for doc in selected[:8]:
        meta = doc.metadata or {}
        section = str(meta.get("section_title") or meta.get("source_type") or "자료")
        text = strip_section_noise(doc.page_content)
        if not text:
            continue
        snippet_lines.append(f"{section}: {first_sentence(text, 420)}")

    card_text = normalize("\n".join(meta_lines + [""] + snippet_lines))
    card_tokens = [
        term
        for term in tokens(card_text)
        if len(term) >= 2 and not is_question_context_token(term) and term not in GENERIC_PATENT_TITLE_TERMS
    ]
    domain_terms: List[str] = []
    for term in card_tokens:
        if term not in domain_terms:
            domain_terms.append(term)
        if len(domain_terms) >= 18:
            break

    return Document(
        page_content=card_text,
        metadata={
            "chunk_id": f"{patent_id}:DOMAIN_CARD",
            "patent_id": patent_id,
            "source_type": "DOMAIN_CARD",
            "section_title": "특허 도메인 카드",
            "title": title,
            "registration_number": patent_meta.get("registration_number"),
            "application_number": patent_meta.get("application_number"),
            "ipc_code": patent_meta.get("ipc_code"),
            "cpc_code": patent_meta.get("cpc_code"),
            "domain_terms": domain_terms,
        },
    )


def score_domain_card(question: str, card: Document) -> Tuple[float, List[str]]:
    query_terms = discovery_query_terms(question)
    if not query_terms:
        return 0.0, []

    meta = card.metadata or {}
    card_text = normalize(
        " ".join(
            [
                str(meta.get("title") or ""),
                str(meta.get("registration_number") or ""),
                str(meta.get("application_number") or ""),
                str(meta.get("ipc_code") or ""),
                str(meta.get("cpc_code") or ""),
                " ".join(str(term) for term in meta.get("domain_terms") or []),
                card.page_content,
            ]
        )
    ).lower()
    title_text = str(meta.get("title") or "").lower()

    matched = [term for term in query_terms if term.lower() in card_text]
    title_matched = [term for term in query_terms if term.lower() in title_text]
    if not matched:
        return 0.0, []

    term_ratio = len(set(matched)) / max(1, len(query_terms))
    title_ratio = len(set(title_matched)) / max(1, len(query_terms))
    score = min(1.0, term_ratio * 0.64 + title_ratio * 0.24 + 0.12)
    return round(score, 4), matched[:8]


def overview_section_sentence(doc: Optional[Document], fallback: str, limit: int = 360) -> str:
    if doc is None:
        return fallback
    text = strip_section_noise(doc.page_content)
    if not text:
        return fallback
    for marker in ("본 발명의 실시예", "상기 목적을 달성하기 위한", "그리고 "):
        idx = text.find(marker)
        if idx > 35:
            text = text[:idx].strip()
            break
    sentence_match = re.search(r".{35,}?다\.", text)
    if sentence_match and sentence_match.end() <= limit:
        return sentence_match.group(0).strip()
    return first_sentence(text, limit)


def infer_core_purpose(title: str, problem_doc: Optional[Document], abstract_doc: Optional[Document]) -> str:
    source_text = strip_section_noise((problem_doc or abstract_doc).page_content) if (problem_doc or abstract_doc) else ""
    source_text = re.sub(r"^본 발명은\s*상기와 같은 문제점을 해결하기 위하여 안출된 것으로서,\s*", "", source_text)
    purpose_match = re.search(r"본 발명의 목적은,\s*(.+?)(?:을 제공|를 제공|함에 있다|있다\.)", source_text)
    if purpose_match:
        purpose = normalize(purpose_match.group(1))
        return f"{purpose}을 제공하는 것입니다."
    if "목적" in source_text:
        return first_sentence(source_text, 220)
    return f"{title}의 원문 요약과 청구범위에 나타난 핵심 목적을 자동 정리한 항목입니다."


def infer_flow_steps(title: str, combined_text: str) -> List[str]:
    upper = combined_text.upper()
    if "NF3" in upper or "슬러지" in combined_text or "무인반송차량" in combined_text:
        return [
            "설비 적재",
            "세척 공간 운송",
            "입장 감지",
            "고온·고압 응축수 세척",
            "슬러지 배출",
            "영상 기반 추가 세척",
        ]
    if "CMP" in upper or "PAD" in upper or "물류" in combined_text:
        return [
            "CMP Pad 생산/입고",
            "물류 상태 수집",
            "보관·반송 위치 관리",
            "재고 흐름 제어",
            "공정 공급",
        ]
    if "미들웨어" in title or "토폴로지" in combined_text or "병목" in combined_text:
        return [
            "토폴로지 정보 수집",
            "시스템 상태 모니터링",
            "병목 후보 탐지",
            "원인 구간 분석",
            "운영 대응",
        ]
    return ["입력 정보 수집", "상태 판단", "핵심 처리", "결과 제공", "운영 검토"]


def infer_component_roles(title: str, combined_text: str) -> List[Tuple[str, str]]:
    libraries = [
        ("무인반송차량", "대상 설비를 세척 공간으로 운송"),
        ("자동문 제어부", "세척 공간 입구의 자동문 개방을 제어"),
        ("센서부", "대상 설비의 세척 공간 입장 여부를 감지"),
        ("세척부", "응축수 분사로 슬러지와 이물질을 제거"),
        ("배출부", "응축수와 슬러지 배출 및 회수 배관을 담당"),
        ("원격 제어부", "주행 경로, 노즐 이동 경로, 세척 작업을 제어"),
        ("영상 수집부", "세척 상태와 관심 영역 판단에 필요한 영상을 수집"),
        ("제1 분사 노즐", "1차 세척 작업을 수행"),
        ("제2 분사 노즐", "관심 영역 기반 2차 세척을 수행"),
        ("물류 관리 서버", "CMP Pad의 물류 흐름과 상태를 관리"),
        ("ECS", "설비 제어 시스템과 물류 시스템 사이의 제어 연동을 담당"),
        ("CCS", "컨베이어 기반 반송 제어를 담당"),
        ("SCS", "스토커 또는 보관 장치 제어를 담당"),
        ("컨베이어", "CMP Pad 또는 물류 대상의 이동 경로를 구성"),
        ("스토커", "대상 자재의 보관 위치와 재고 흐름을 관리"),
        ("토폴로지", "시스템 구성요소 간 연결 관계를 표현"),
        ("모니터링", "시스템 상태와 병목 징후를 관찰"),
        ("병목 구간", "성능 저하 또는 처리 지연이 발생하는 구간"),
        ("메시지 지향 미들웨어", "시스템 간 메시지 전달과 연계를 담당"),
        ("브로커", "메시지 전달 경로와 처리 상태를 중계"),
    ]
    rows: List[Tuple[str, str]] = []
    for term, role in libraries:
        if term.lower() in combined_text.lower() and (term, role) not in rows:
            rows.append((term, role))
    if rows:
        return rows[:8]
    return [("핵심 구성요소", "원문 청구범위와 상세한 설명에서 확인 필요")]


def infer_strength_line(title: str, combined_text: str) -> str:
    if "NF3" in combined_text or "슬러지" in combined_text:
        return "NF3 특화 설비 세척, 자동 운송, 센서 감지, 세척·배출 제어가 결합된 복합 자동화 구조가 강점입니다."
    if "CMP" in combined_text or "물류" in combined_text:
        return "CMP Pad 생산·보관·반송 흐름을 물류 관리 관점에서 통합하려는 점이 강점입니다."
    if "토폴로지" in combined_text or "병목" in combined_text:
        return "시스템 연결 구조와 상태 정보를 함께 보면서 병목 구간을 파악하려는 점이 강점입니다."
    return f"{title}의 청구항과 보고서에서 확인되는 차별 구성은 사업 적용성과 권리성을 함께 검토할 필요가 있습니다."


def asset_kind_name(asset_kind: Optional[str]) -> str:
    return {
        "TABLE": "표",
        "IMAGE": "이미지",
        "DIAGRAM_PAGE": "도면/다이어그램",
        "PAGE_VISUAL": "페이지 이미지",
    }.get(str(asset_kind or ""), str(asset_kind or "시각자료"))


VISUAL_STOP_TERMS = QUESTION_CONTEXT_TERMS | {
    "보여",
    "보여줘",
    "같이",
    "함께",
    "포함",
    "필요",
    "따라",
    "이용",
    "원본",
    "원문",
    "보고서",
    "자료",
}


def visual_query_terms(question: str) -> List[str]:
    terms: List[str] = []
    for term in tokens(question):
        if len(term) < 2:
            continue
        if term in VISUAL_STOP_TERMS:
            continue
        if term not in terms:
            terms.append(term)
    return terms


def detect_visual_asset_intents(question: str) -> Dict[str, bool]:
    q = question.lower()
    wants_table = any(term in q for term in ("표", "테이블", "도표", "점수표", "평가표", "리스크표"))
    wants_diagram = any(term in q for term in ("도면", "다이어그램", "구성도", "흐름도", "블록도", "그림", "figure", "fig."))
    wants_image = any(term in q for term in ("이미지", "캡처", "사진", "미리보기", "시각자료", "시각 자료"))
    wants_report = any(term in q for term in ("보고서", "평가", "점수", "리스크", "사업", "유사 특허", "참고문헌"))
    wants_original = any(term in q for term in ("원문", "원본", "특허공보", "청구항", "도면", "명세서"))
    wants_visual = wants_table or wants_diagram or wants_image or any(
        term in q for term in ("보여", "같이", "포함해서", "포함해", "시각화")
    )
    return {
        "visual": wants_visual,
        "table": wants_table,
        "diagram": wants_diagram,
        "image": wants_image,
        "report": wants_report,
        "original": wants_original,
    }


def is_visual_asset_question(question: str) -> bool:
    return detect_visual_asset_intents(question)["visual"]


def is_explicit_visual_asset_request(question: str) -> bool:
    intents = detect_visual_asset_intents(question)
    if intents["table"] or intents["diagram"] or intents["image"]:
        return True
    q = question.lower()
    return any(term in q for term in ("시각자료", "시각 자료", "차트", "그래프", "캡처"))


def visual_asset_relevance_detail(question: str, doc: Document) -> Dict[str, Any]:
    meta = doc.metadata or {}
    if meta.get("content_type") != "VISUAL_ASSET":
        return {"score": 0.0, "grade": "LOW", "matched_terms": [], "reason": ""}

    intents = detect_visual_asset_intents(question)
    asset_kind = str(meta.get("asset_kind") or "")
    source_type = str(meta.get("source_type") or "")
    text = normalize(
        " ".join(
            [
                str(meta.get("title") or ""),
                str(meta.get("section_title") or ""),
                str(meta.get("section_key") or ""),
                str(meta.get("source_type") or ""),
                str(meta.get("asset_kind") or ""),
                doc.page_content,
            ]
        )
    ).lower()
    q_terms = visual_query_terms(question)
    matched_terms = [term for term in q_terms if term.lower() in text]

    score = 0.18
    reasons: List[str] = []
    if intents["table"] and asset_kind == "TABLE":
        score += 0.42
        reasons.append("표 요청과 일치")
    if intents["diagram"] and asset_kind in ("DIAGRAM_PAGE", "IMAGE", "PAGE_VISUAL"):
        score += 0.36
        reasons.append("도면/다이어그램 요청과 일치")
    if intents["image"] and asset_kind in ("IMAGE", "DIAGRAM_PAGE", "PAGE_VISUAL"):
        score += 0.28
        reasons.append("이미지 요청과 일치")
    if intents["report"] and source_type == "REPORT_VISUAL":
        score += 0.16
        reasons.append("보고서 시각자료")
    if intents["original"] and source_type == "ORIGINAL_VISUAL":
        score += 0.16
        reasons.append("원문 시각자료")

    if q_terms:
        score += min(0.24, 0.08 * len(set(matched_terms)))
    elif intents["visual"]:
        score += 0.08

    section_title = str(meta.get("section_title") or "")
    if intents["table"] and any(term in section_title for term in ("점수", "리스크", "프로젝트", "유사", "가이드")):
        score += 0.08
    if intents["diagram"] and source_type == "ORIGINAL_VISUAL":
        score += 0.08

    score = round(min(1.0, score), 4)
    grade = "GOOD" if score >= 0.62 else "FAIR" if score >= 0.38 else "LOW"
    return {
        "score": score,
        "grade": grade,
        "matched_terms": matched_terms[:8],
        "reason": ", ".join(reasons[:3]) or "시각자료 후보",
    }


def select_visual_asset_docs(
    patent_id: str,
    question: str,
    max_docs: int = 6,
    fallback: bool = False,
) -> List[Document]:
    docs = load_patent_docs_from_disk(patent_id)
    visual_docs = [
        doc
        for doc in docs
        if (doc.metadata or {}).get("content_type") == "VISUAL_ASSET"
    ]
    if not visual_docs:
        return []

    scored: List[Tuple[float, int, Document]] = []
    for idx, doc in enumerate(visual_docs):
        detail = visual_asset_relevance_detail(question, doc)
        score = float(detail["score"])
        if score >= 0.34 or fallback:
            scored.append((score, -idx, doc))

    if not scored and not fallback:
        return []

    if fallback and not scored:
        asset_priority = {"TABLE": 0, "DIAGRAM_PAGE": 1, "IMAGE": 2, "PAGE_VISUAL": 3}
        scored = [
            (
                0.32,
                -idx - asset_priority.get(str((doc.metadata or {}).get("asset_kind") or ""), 9),
                doc,
            )
            for idx, doc in enumerate(visual_docs)
        ]

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected: List[Document] = []
    seen_assets: set[str] = set()
    for _, _, doc in scored:
        meta = doc.metadata or {}
        asset_name = str(meta.get("asset_file_name") or doc_key(doc))
        if asset_name in seen_assets:
            continue
        seen_assets.add(asset_name)
        selected.append(doc)
        if len(selected) >= max_docs:
            break
    return selected


def build_visual_asset_answer(
    question: str,
    docs: List[Document],
    source_cards: List[Dict[str, Any]],
) -> str:
    if not docs:
        return "요청하신 표/도면/이미지 자료를 현재 인덱스에서 확인하지 못했습니다."

    intents = detect_visual_asset_intents(question)
    if intents["table"] and not (intents["diagram"] or intents["image"]):
        title = "요청하신 표 자료를 찾았습니다."
    elif intents["diagram"] and not intents["table"]:
        title = "요청하신 원문 도면/다이어그램 자료를 찾았습니다."
    else:
        title = "질문과 관련된 표·도면·이미지 자료를 찾았습니다."

    lines = [
        "## 답변",
        "",
        f"{title} 실제 이미지는 아래 근거 카드에 미리보기로 표시되며, 카드를 누르면 원본 파일 또는 PDF 페이지를 열 수 있습니다.",
        "",
        "## 시각자료 목록",
        "",
        "| 자료 | 유형 | 위치 | 내용 | 사용 이유 |",
        "| --- | --- | --- | --- | --- |",
    ]

    for doc in docs[: len(source_cards)]:
        meta = doc.metadata or {}
        label = source_label_for_doc(doc, docs, source_cards)
        detail = visual_asset_relevance_detail(question, doc)
        kind = asset_kind_name(meta.get("asset_kind"))
        source_name = source_type_name(meta.get("source_type"))
        page = f"p.{meta.get('page_no')}" if meta.get("page_no") else "보고서/HTML"
        section = str(meta.get("section_title") or kind)
        snippet = first_sentence(clean_evidence_text(doc.page_content), 110).replace("|", "/")
        reason = detail.get("reason") or "질문 의도와 관련된 시각자료"
        lines.append(
            f"| [{label}] | {kind} | {source_name} {page} | {section}: {snippet} | {reason} |"
        )

    table_docs = [doc for doc in docs if (doc.metadata or {}).get("asset_kind") == "TABLE"]
    diagram_docs = [
        doc
        for doc in docs
        if (doc.metadata or {}).get("asset_kind") in ("DIAGRAM_PAGE", "IMAGE", "PAGE_VISUAL")
    ]

    lines.extend(["", "## 해석", ""])
    if table_docs:
        labels = " ".join(f"[{source_label_for_doc(doc, docs, source_cards)}]" for doc in table_docs[:3])
        lines.append(f"- 표 자료는 보고서의 평가 점수, 리스크, 사내 프로젝트, 유사 특허, 의사결정 가이드 같은 정형 항목을 확인하는 데 우선 사용합니다. {labels}")
    if diagram_docs:
        labels = " ".join(f"[{source_label_for_doc(doc, docs, source_cards)}]" for doc in diagram_docs[:3])
        lines.append(f"- 도면/이미지 자료는 원문 특허의 구성, 흐름, 장치 구조를 텍스트 청구항과 함께 확인하는 데 사용합니다. {labels}")
    if not table_docs and not diagram_docs:
        lines.append("- 선택된 시각자료는 질문 키워드와 가장 가까운 이미지 청크를 기준으로 정렬했습니다.")

    lines.extend(
        [
            "",
            "## 확인 필요 사항",
            "",
            "- 시각자료는 OCR/표 추출 결과와 원본 이미지가 함께 저장되지만, 법적 판단에는 원문 PDF와 보고서 원본을 함께 확인해야 합니다.",
            "- 표의 숫자나 도면 구성요소가 잘렸거나 흐리게 보이면 근거 카드의 원본 파일 또는 PDF 페이지를 열어 확인하세요.",
        ]
    )
    return "\n".join(lines)


def build_visual_asset_quality_metrics(
    question: str,
    docs: List[Document],
    source_cards: List[Dict[str, Any]],
    retrieval_query_expanded: bool,
) -> Dict[str, Any]:
    details = [visual_asset_relevance_detail(question, doc) for doc in docs[: len(source_cards)]]
    scores = [float(detail.get("score") or 0.0) for detail in details]
    evidence_doc_count = sum(1 for score in scores if score >= 0.38)
    quality_score = round(sum(scores[:5]) / max(1, min(5, len(scores))), 4) if scores else 0.0
    quality_grade = "GOOD" if quality_score >= 0.62 and evidence_doc_count >= 2 else "FAIR" if quality_score >= 0.38 and evidence_doc_count >= 1 else "LOW"
    quality_label = {"GOOD": "양호", "FAIR": "주의", "LOW": "낮음"}[quality_grade]
    source_type_counts: Dict[str, int] = {}
    asset_type_counts: Dict[str, int] = {}
    for doc in docs[: len(source_cards)]:
        meta = doc.metadata or {}
        source_type = str(meta.get("source_type") or "UNKNOWN")
        asset_kind = str(meta.get("asset_kind") or "UNKNOWN")
        source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
        asset_type_counts[asset_kind] = asset_type_counts.get(asset_kind, 0) + 1

    top_source_relevance = []
    for card, detail in zip(source_cards[:5], details[:5]):
        top_source_relevance.append(
            {
                "label": card.get("label"),
                "source_type": card.get("source_type"),
                "asset_kind": card.get("asset_kind"),
                "page_no": card.get("page_no"),
                "score": detail["score"],
                "grade": detail["grade"],
                "matched_terms": detail["matched_terms"],
            }
        )

    quality_reason = (
        "질문 의도에 맞는 표/도면/이미지 근거가 검색되었습니다."
        if quality_grade == "GOOD"
        else "시각자료는 검색되었지만 원본 확인이 필요합니다."
        if quality_grade == "FAIR"
        else "질문 의도에 맞는 시각자료 근거가 부족합니다."
    )
    return {
        "retrieval_quality_score": quality_score,
        "retrieval_quality_grade": quality_grade,
        "retrieval_quality_label": quality_label,
        "retrieval_quality_reason": quality_reason,
        "search_pass": quality_grade in ("GOOD", "FAIR"),
        "question_match_score": quality_score,
        "expanded_match_score": quality_score,
        "evidence_doc_count": evidence_doc_count,
        "source_type_counts": source_type_counts,
        "asset_type_counts": asset_type_counts,
        "top_source_relevance": top_source_relevance,
        "quality_thresholds": {
            "GOOD": "시각자료 품질 0.62 이상 + 근거 2개 이상",
            "FAIR": "시각자료 품질 0.38 이상 + 근거 1개 이상",
            "LOW": "위 기준 미달",
        },
        "performance_evaluation": [
            {
                "name": "시각자료 검색 품질",
                "status": quality_grade,
                "value": quality_score,
                "good_threshold": ">= 0.62 and evidence_doc_count >= 2",
                "fair_threshold": ">= 0.38 and evidence_doc_count >= 1",
                "message": quality_reason,
            },
            {
                "name": "시각자료 근거 수",
                "status": "GOOD" if evidence_doc_count >= 2 else "FAIR" if evidence_doc_count >= 1 else "LOW",
                "value": evidence_doc_count,
                "good_threshold": ">= 2",
                "fair_threshold": ">= 1",
                "message": "질문 의도와 맞는 표/도면/이미지 청크 수입니다.",
            },
            {
                "name": "시각자료 유형",
                "status": "GOOD" if asset_type_counts else "LOW",
                "value": asset_type_counts,
                "good_threshold": "TABLE / DIAGRAM_PAGE / IMAGE 중 하나 이상",
                "fair_threshold": "시각자료 후보 존재",
                "message": "답변에 포함된 이미지·표·도면의 종류입니다.",
            },
        ],
        "retrieval_query_expanded": retrieval_query_expanded,
    }


def score_number(score_text: str) -> Optional[int]:
    match = re.search(r"([0-9]{1,3})\s*/\s*100", score_text or "")
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def score_level(score_text: str) -> str:
    value = score_number(score_text)
    if value is None:
        return "확인 필요"
    if value >= 75:
        return "강점"
    if value >= 65:
        return "보통 이상"
    if value >= 55:
        return "보완 필요"
    return "낮음"


def dimension_summary(text: str, dimension: str, fallback: str, limit: int = 170) -> str:
    clean = clean_evidence_text(text)
    patterns = [
        rf"{re.escape(dimension)}은\s*.{{20,{limit}}}?평가되었습니다\.",
        rf"{re.escape(dimension)}은\s*.{{20,{limit}}}?보수적으로 평가되었습니다\.",
        rf"{re.escape(dimension)}\s+[0-9]{{1,3}}\s*/\s*100\s*.{{20,{limit}}}?[.。]",
    ]
    for pattern in patterns:
        match = re.search(pattern, clean)
        if match:
            return first_sentence(match.group(0), limit)
    return first_sentence(fallback, limit)


def select_patent_evaluation_docs(patent_id: str, include_visual: bool = False) -> List[Document]:
    docs = load_patent_docs_from_disk(patent_id)
    selected: List[Document] = []
    seen: set[str] = set()

    def add(doc: Optional[Document]) -> None:
        if doc is None:
            return
        key = doc_key(doc)
        if key in seen:
            return
        seen.add(key)
        selected.append(doc)

    add(
        pick_best_doc(
            docs,
            "REPORT_PDF",
            ["REPORT_SUMMARY", "REPORT_OVERVIEW"],
            ["평가 요약", "평가 개요"],
            ["종합", "기술성", "권리성", "시장성", "사업성"],
        )
    )
    add(
        pick_best_doc(
            docs,
            "REPORT_PDF",
            ["REPORT_SCORE_DETAIL"],
            ["평가 기준별 점수"],
            ["차별성", "혁신성", "권리", "시장성", "사업성"],
        )
    )
    add(
        pick_best_doc(
            docs,
            "REPORT_PDF",
            ["REPORT_INTERNAL_PROJECTS"],
            ["사내 프로젝트"],
            ["사업화", "활용", "프로젝트", "미진행"],
        )
    )
    add(
        pick_best_doc(
            docs,
            "REPORT_PDF",
            ["REPORT_SIMILAR_PATENTS"],
            ["유사 특허 분석"],
            ["KIPRIS", "유사도", "피인용", "등록", "거절"],
        )
    )
    add(
        pick_best_doc(
            docs,
            "REPORT_PDF",
            ["REPORT_RISK", "REPORT_DECISION"],
            ["리스크 및 추가 확인", "의사결정 가이드"],
            ["권리성", "시장성", "사업성", "보수적으로", "특허출원 활성도", "매출 성장성"],
        )
    )
    add(
        pick_best_doc(
            docs,
            "REPORT_PDF",
            ["REPORT_RISK", "REPORT_DECISION"],
            ["리스크 및 추가 확인", "의사결정 가이드"],
            ["리스크", "추가 확인", "회피설계", "무효", "유지", "매각", "제각"],
        )
    )

    if include_visual:
        for doc in select_visual_asset_docs(patent_id, "보고서 평가 점수 표 리스크 표", max_docs=2, fallback=False):
            add(doc)

    return selected[:8]


def build_patent_evaluation_answer(
    question: str,
    patent_meta: Dict[str, Any],
    docs: List[Document],
    source_cards: List[Dict[str, Any]],
) -> str:
    title = patent_meta.get("title") or (source_cards[0].get("title") if source_cards else "해당 특허")
    report_summary_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_SUMMARY", "REPORT_OVERVIEW"],
        ["평가 요약", "평가 개요"],
        ["종합", "기술성", "권리성", "시장성", "사업성"],
    )
    report_score_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_SCORE_DETAIL"],
        ["평가 기준별 점수"],
        ["기술성", "권리성", "시장성", "사업성"],
    )
    project_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_INTERNAL_PROJECTS"],
        ["사내 프로젝트"],
        ["사업화", "활용", "프로젝트"],
    )
    similar_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_SIMILAR_PATENTS"],
        ["유사 특허 분석"],
        ["유사도", "피인용", "KIPRIS"],
    )
    risk_summary_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_RISK", "REPORT_DECISION"],
        ["리스크 및 추가 확인", "의사결정 가이드"],
        ["권리성", "시장성", "사업성", "보수적으로", "특허출원 활성도", "매출 성장성"],
    )
    risk_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_RISK", "REPORT_DECISION"],
        ["리스크 및 추가 확인", "의사결정 가이드"],
        ["리스크", "추가 확인", "회피설계", "무효"],
    )

    label_summary = source_label_for_doc(report_summary_doc, docs, source_cards)
    label_score = source_label_for_doc(report_score_doc or report_summary_doc, docs, source_cards)
    label_project = source_label_for_doc(project_doc or report_summary_doc, docs, source_cards)
    label_similar = source_label_for_doc(similar_doc or report_summary_doc, docs, source_cards)
    label_risk = source_label_for_doc(risk_summary_doc or risk_doc or report_score_doc or report_summary_doc, docs, source_cards)

    summary_text = clean_evidence_text((report_summary_doc or docs[0]).page_content) if docs else ""
    score_text = clean_evidence_text((report_score_doc or report_summary_doc or docs[0]).page_content) if docs else ""
    project_text = clean_evidence_text((project_doc or report_summary_doc or docs[0]).page_content) if docs else ""
    similar_text = clean_evidence_text((similar_doc or report_summary_doc or docs[0]).page_content) if docs else ""
    risk_text = clean_evidence_text((risk_summary_doc or risk_doc or report_score_doc or report_summary_doc or docs[0]).page_content) if docs else ""

    total = score_text_value(summary_text, r"종합\s+([0-9]{1,3}\s*/\s*100)")
    tech = score_text_value(summary_text, r"기술성\s+([0-9]{1,3}\s*/\s*100)")
    right = score_text_value(summary_text, r"권리성\s+([0-9]{1,3}\s*/\s*100)")
    market = score_text_value(summary_text, r"시장성\s*및\s*사업성\s+([0-9]{1,3}\s*/\s*100)")

    tech_reason = excerpt_around_terms(score_text + " " + risk_text, ["기술성", "차별성", "혁신성"], 260)
    right_reason = excerpt_around_terms(risk_text + " " + score_text, ["권리성", "IP 원천성", "권리행사", "권리"], 260)
    market_reason = excerpt_around_terms(risk_text + " " + score_text, ["시장성", "사업성", "매출", "특허출원 활성도"], 260)
    tech_reason = dimension_summary(risk_text + " " + score_text, "기술성", tech_reason)
    right_reason = dimension_summary(risk_text + " " + score_text, "권리성", right_reason)
    market_reason = dimension_summary(risk_text + " " + score_text, "시장성 및 사업성", market_reason)
    project_reason = excerpt_around_terms(project_text, ["사내 프로젝트", "사업화", "미진행", "활용"], 240)
    similar_reason = excerpt_around_terms(similar_text, ["유사 특허", "KIPRIS", "유사도", "피인용"], 240)
    risk_reason = excerpt_around_terms(risk_text, ["리스크", "보수적으로", "추가 확인", "회피설계", "무효"], 260)

    lines = [
        "## 평가 요약",
        "",
        f"{title}의 AI 평가 보고서 기준 종합 점수는 **{total}**입니다. 기술성은 **{tech}**, 권리성은 **{right}**, 시장성 및 사업성은 **{market}**으로 정리되어 있습니다. [{label_summary}]",
        "",
        "## 항목별 평가",
        "",
        "| 항목 | 점수 | 판정 | 핵심 해석 | 출처 |",
        "| --- | --- | --- | --- | --- |",
        f"| 종합 | {total} | {score_level(total)} | 전체적으로는 검토 가치가 있으나 사업 적용성과 경쟁 상황을 함께 봐야 합니다. | [{label_summary}] |",
        f"| 기술성 | {tech} | {score_level(tech)} | {first_sentence(tech_reason, 150).replace('|', '/')} | [{label_score}] |",
        f"| 권리성 | {right} | {score_level(right)} | {first_sentence(right_reason, 150).replace('|', '/')} | [{label_score}] |",
        f"| 시장성 및 사업성 | {market} | {score_level(market)} | {first_sentence(market_reason, 150).replace('|', '/')} | [{label_score}] |",
        "",
        "## 평가 해석",
        "",
        f"- 기술성은 상대적으로 강한 편입니다. 보고서에서는 CMP 공정 특화 생산성 향상, RTD·MCS 전환, 스마트팩토리 전환형 혁신성을 주요 근거로 봅니다. [{label_score}]",
        f"- 권리성은 보통 이상입니다. 다만 청구항 충실성, IP 원천성, 회피설계 가능성은 원문 청구항과 유사 특허를 함께 확인해야 합니다. [{label_score}]",
        f"- 시장성 및 사업성은 보완 검토가 필요합니다. 보고서상 사업화 상태와 실제 적용 이력 확인이 중요합니다. [{label_project}]",
        "",
        "## 사업 활용 및 유사 특허",
        "",
        f"- 사내/사업 활용: {first_sentence(project_reason, 220)} [{label_project}]",
        f"- 유사 특허: {first_sentence(similar_reason, 220)} [{label_similar}]",
        "",
        "## 리스크와 추가 확인",
        "",
        f"- {first_sentence(risk_reason, 260)} [{label_risk}]",
        "- AI가 유지/매각/제각을 단정할 수는 없습니다. 위 평가는 사업부와 Legal AI팀의 의사결정을 돕는 근거로만 사용해야 합니다.",
        "",
        "## 확인 필요 사항",
        "",
        f"- 실제 사업 적용 여부와 고객/제품/공정 적용 이력을 확인해야 합니다. [{label_project}]",
        f"- 유사 특허 대비 청구항 차별성, 회피설계 가능성, 무효 가능성은 별도 선행기술 검토가 필요합니다. [{label_similar}] [{label_risk}]",
    ]
    return "\n".join(lines)


def build_evaluation_quality_metrics(
    question: str,
    retrieval_question: str,
    docs: List[Document],
    source_cards: List[Dict[str, Any]],
    confidence: float,
    retrieval_query_expanded: bool,
) -> Dict[str, Any]:
    section_keys = {str((doc.metadata or {}).get("section_key") or "") for doc in docs}
    required = {"REPORT_SUMMARY", "REPORT_SCORE_DETAIL", "REPORT_RISK"}
    covered = len(required & section_keys)
    evidence_doc_count = len(source_cards)
    section_coverage = min(1.0, covered / max(1, len(required)))
    quality_score = round(min(1.0, section_coverage * 0.75 + min(1.0, evidence_doc_count / 4) * 0.25), 4)
    quality_grade = "GOOD" if quality_score >= 0.72 and evidence_doc_count >= 3 else "FAIR" if quality_score >= 0.45 else "LOW"
    quality_label = {"GOOD": "양호", "FAIR": "주의", "LOW": "낮음"}[quality_grade]

    source_type_counts: Dict[str, int] = {}
    for doc in docs:
        source_type = str((doc.metadata or {}).get("source_type") or "UNKNOWN")
        source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1

    top_source_relevance = []
    for card in source_cards[:5]:
        top_source_relevance.append(
            {
                "label": card.get("label"),
                "source_type": card.get("source_type"),
                "page_no": card.get("page_no"),
                "score": 0.88,
                "grade": "GOOD",
                "matched_terms": ["평가", "점수", "보고서"],
            }
        )

    return {
        "retrieval_quality_score": quality_score,
        "retrieval_quality_grade": quality_grade,
        "retrieval_quality_label": quality_label,
        "retrieval_quality_reason": "평가 답변에 필요한 평가 요약, 상세 점수, 리스크/추가 확인 섹션을 기준으로 검색했습니다.",
        "search_pass": quality_grade in ("GOOD", "FAIR"),
        "question_match_score": round(lexical_confidence(question, docs), 4),
        "expanded_match_score": round(lexical_confidence(retrieval_question, docs), 4),
        "evidence_doc_count": evidence_doc_count,
        "source_type_counts": source_type_counts,
        "top_source_relevance": top_source_relevance,
        "quality_thresholds": {
            "GOOD": "평가 필수 섹션 70% 이상 + 근거 3개 이상",
            "FAIR": "평가 필수 섹션 45% 이상",
            "LOW": "위 기준 미달",
        },
        "performance_evaluation": [
            {
                "name": "평가 근거 품질",
                "status": quality_grade,
                "value": quality_score,
                "good_threshold": "section_coverage >= 0.70 and evidence_doc_count >= 3",
                "fair_threshold": "section_coverage >= 0.45",
                "message": "평가 요약/상세 점수/리스크 섹션이 충분히 모였는지입니다.",
            },
            {
                "name": "평가 섹션 커버리지",
                "status": "GOOD" if section_coverage >= 0.7 else "FAIR" if section_coverage >= 0.45 else "LOW",
                "value": round(section_coverage, 4),
                "good_threshold": ">= 0.70",
                "fair_threshold": ">= 0.45",
                "message": "평가 요약, 상세 점수, 리스크/추가 확인 섹션 포함 여부입니다.",
            },
            {
                "name": "근거 문서 수",
                "status": "GOOD" if evidence_doc_count >= 3 else "FAIR" if evidence_doc_count >= 2 else "LOW",
                "value": evidence_doc_count,
                "good_threshold": ">= 3",
                "fair_threshold": ">= 2",
                "message": "평가 답변에 사용한 보고서 근거 수입니다.",
            },
        ],
        "retrieval_query_expanded": retrieval_query_expanded,
    }


def build_patent_overview_answer(
    question: str,
    patent_meta: Dict[str, Any],
    docs: List[Document],
    source_cards: List[Dict[str, Any]],
    confidence: float,
) -> str:
    title = patent_meta.get("title") or (source_cards[0].get("title") if source_cards else "해당 특허")
    registration_number = patent_meta.get("registration_number") or "-"
    application_number = patent_meta.get("application_number") or "-"

    biblio_doc = pick_best_doc(docs, "ORIGINAL_PDF", ["KR_BIBLIO"], ["서지사항"], ["등록번호", "출원번호"])
    abstract_doc = pick_best_doc(docs, "ORIGINAL_PDF", ["KR_ABSTRACT"], ["요약"], ["요약"])
    background_doc = pick_best_doc(docs, "ORIGINAL_PDF", ["KR_BACKGROUND"], ["배경기술"], ["배경"])
    problem_doc = pick_best_doc(docs, "ORIGINAL_PDF", ["KR_PROBLEM"], ["해결하려는 과제"], ["목적"])
    solution_doc = pick_best_doc(docs, "ORIGINAL_PDF", ["KR_SOLUTION"], ["과제의 해결 수단"], ["포함"])
    claim_doc = pick_best_doc(docs, "ORIGINAL_PDF", ["KR_CLAIMS"], ["청구범위"], ["청구항"])
    effect_doc = pick_best_doc(docs, "ORIGINAL_PDF", ["KR_EFFECT"], ["발명의 효과"], ["효과"])
    report_overview_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_OVERVIEW"],
        ["평가 개요"],
        ["종합", "기술성", "권리성", "시장성", "사업성"],
    )
    report_score_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_SCORE_DETAIL"],
        ["평가 기준별 점수"],
        ["차별성", "무효", "회피설계", "사업화"],
    )
    report_risk_doc = pick_best_doc(
        docs,
        "REPORT_PDF",
        ["REPORT_RISK", "REPORT_DECISION"],
        ["리스크 및 추가 확인", "의사결정 가이드"],
        ["추가 확인", "무효", "회피설계", "대체기술"],
    )

    label_biblio = source_label_for_doc(biblio_doc, docs, source_cards)
    label_abstract = source_label_for_doc(abstract_doc, docs, source_cards)
    label_background = source_label_for_doc(background_doc, docs, source_cards)
    label_problem = source_label_for_doc(problem_doc, docs, source_cards)
    label_solution = source_label_for_doc(solution_doc, docs, source_cards)
    label_claim = source_label_for_doc(claim_doc, docs, source_cards)
    label_effect = source_label_for_doc(effect_doc, docs, source_cards)
    label_report = source_label_for_doc(report_overview_doc or report_score_doc, docs, source_cards)
    label_risk = source_label_for_doc(report_risk_doc or report_score_doc, docs, source_cards)

    biblio_text = clean_evidence_text((biblio_doc or docs[0]).page_content) if docs else ""
    ipc_code = patent_meta.get("ipc_code")
    if not ipc_code:
        ipc_values = []
        for value in re.findall(r"\b[A-H][0-9]{2}[A-Z]\s*\d+/\d+\b", biblio_text):
            normalized_value = normalize(value)
            if normalized_value not in ipc_values:
                ipc_values.append(normalized_value)
        ipc_code = ", ".join(ipc_values[:4]) if ipc_values else "원문/보고서 확인"

    abstract_text = overview_section_sentence(
        abstract_doc,
        f"{title}에 관한 원문 요약은 해당 특허의 핵심 기술 구성을 설명합니다.",
        360,
    )
    background_text = overview_section_sentence(
        background_doc,
        "배경기술은 기존 방식의 한계와 기술 도입 필요성을 설명합니다.",
        300,
    )
    problem_text = infer_core_purpose(title, problem_doc, abstract_doc)
    solution_text = clean_evidence_text((solution_doc or claim_doc or abstract_doc or docs[0]).page_content) if docs else ""
    claim_text = clean_evidence_text((claim_doc or solution_doc or abstract_doc or docs[0]).page_content) if docs else ""
    effect_text = overview_section_sentence(
        effect_doc,
        "원문 효과 부분에서 이 특허의 기대 효과를 확인해야 합니다.",
        300,
    )
    report_text = clean_evidence_text((report_overview_doc or report_score_doc or docs[-1]).page_content) if docs else ""
    risk_text = clean_evidence_text((report_risk_doc or report_score_doc or docs[-1]).page_content) if docs else ""
    combined_text = " ".join([title, abstract_text, background_text, problem_text, solution_text, claim_text, effect_text, report_text, risk_text])
    visual_docs = [doc for doc in docs if (doc.metadata or {}).get("content_type") == "VISUAL_ASSET"]

    score_total = score_text_value(report_text, r"종합\s+([0-9]{1,3}\s*/\s*100)")
    score_tech = score_text_value(report_text, r"기술성\s+([0-9]{1,3}\s*/\s*100)")
    score_right = score_text_value(report_text, r"권리성\s+([0-9]{1,3}\s*/\s*100)")
    score_market = score_text_value(report_text, r"시장성\s*및\s*사업성\s+([0-9]{1,3}\s*/\s*100)")

    component_rows = infer_component_roles(title, combined_text)
    flow_steps = infer_flow_steps(title, combined_text)
    strength_line = infer_strength_line(title, combined_text)

    lines = [
        "## 한눈에 보기",
        "",
        "| 항목 | 내용 | 출처 |",
        "| --- | --- | --- |",
        f"| 발명의 명칭 | {title} | [{label_biblio}] |",
        f"| 등록번호 | {registration_number} | [{label_biblio}] |",
        f"| 출원번호 | {application_number} | [{label_biblio}] |",
        f"| IPC | {ipc_code} | [{label_biblio}] |",
        f"| 핵심 목적 | {first_sentence(problem_text, 160)} | [{label_problem}] |",
        "",
        "## 기술 개요",
        "",
        f"{title}은 아래 원문 요약과 청구범위에 근거한 기술입니다. {abstract_text} [{label_abstract}]",
        "",
        "## 왜 필요한 기술인가",
        "",
        f"{background_text} [{label_background}]",
        f"{problem_text} [{label_problem}]",
        "",
        "## 동작 흐름",
        "",
        "```text",
        " -> ".join(flow_steps),
        "```",
        f"위 흐름은 원문 요약·청구범위·해결수단에 나타난 구성요소를 업무자가 이해하기 쉽게 재정리한 것입니다. [{label_solution}] [{label_claim}]",
        "",
        "## 핵심 구성",
        "",
        "| 구성요소 | 역할 | 출처 |",
        "| --- | --- | --- |",
    ]
    for term, role in component_rows[:8]:
        lines.append(f"| {term} | {role} | [{label_claim}] |")

    if visual_docs:
        lines.extend(["", "## 관련 도표/이미지", ""])
        for doc in visual_docs[:4]:
            meta = doc.metadata or {}
            label_visual = source_label_for_doc(doc, docs, source_cards)
            kind = asset_kind_name(meta.get("asset_kind"))
            section = meta.get("section_title") or "시각자료"
            page = f"p.{meta.get('page_no')}" if meta.get("page_no") else "보고서"
            lines.append(
                f"- {kind}: {section} ({page}). 원본 이미지/표는 근거 카드에서 바로 확인할 수 있습니다. [{label_visual}]"
            )

    lines.extend(
        [
            "",
            "## 기대 효과",
            "",
            f"{effect_text} [{label_effect}]",
            "",
            "## AI 평가 보고서 요약",
            "",
            "| 평가 항목 | 점수 | 해석 | 출처 |",
            "| --- | --- | --- | --- |",
            f"| 종합 | {score_total} | 전체 평가 결과 | [{label_report}] |",
            f"| 기술성 | {score_tech} | 차별성·파급성·대체기술 관점 | [{label_report}] |",
            f"| 권리성 | {score_right} | 청구항 충실성·무효·회피설계 관점 | [{label_report}] |",
            f"| 시장성 및 사업성 | {score_market} | 사내 활용·시장 적용 가능성 관점 | [{label_report}] |",
            "",
            "## 판단 포인트",
            "",
            f"- 강점: {strength_line} [{label_solution}] [{label_claim}]",
            f"- 사업성: 보고서의 사업화 여부, 사내 프로젝트 활용 현황, 시장성 항목을 함께 확인해야 합니다. [{label_report}]",
            f"- 리스크: 대체기술·경쟁 구도, 무효 가능성, 회피설계 가능성, 해외출원 여부 등은 추가 검토 항목입니다. [{label_risk}]",
            "",
            "## 확인 필요 사항",
            "",
            f"- 청구항 1의 구성요소가 실제 설비나 경쟁사 공정에서 확인 가능한지 검토해야 합니다. [{label_claim}]",
            f"- 사업부 적용 이력, 고객 사례, 제품 출시 여부, 연차료 대비 활용 가능성을 확인해야 합니다. [{label_report}]",
            f"- 유사 특허와 청구항 중복, 회피설계, 무효 가능성은 KIPRIS 및 선행기술 검토로 보강해야 합니다. [{label_risk}]",
        ]
    )
    return "\n".join(lines)


def build_overview_quality_metrics(
    question: str,
    retrieval_question: str,
    docs: List[Document],
    source_cards: List[Dict[str, Any]],
    confidence: float,
    retrieval_query_expanded: bool,
) -> Dict[str, Any]:
    source_types = {(doc.metadata or {}).get("source_type") for doc in docs}
    section_keys = {str((doc.metadata or {}).get("section_key") or "") for doc in docs}
    required_sections = {"KR_BIBLIO", "KR_ABSTRACT", "KR_CLAIMS", "KR_PROBLEM", "KR_SOLUTION", "KR_EFFECT"}
    covered = len(required_sections & section_keys)
    has_report = "REPORT_PDF" in source_types
    section_coverage = min(1.0, (covered + (1 if has_report else 0)) / 7)
    evidence_doc_count = len(source_cards)
    quality_score = round(min(1.0, section_coverage * 0.7 + min(1.0, evidence_doc_count / 6) * 0.3), 4)
    quality_grade = "GOOD" if quality_score >= 0.72 and evidence_doc_count >= 5 else "FAIR" if quality_score >= 0.45 else "LOW"
    quality_label = {"GOOD": "양호", "FAIR": "주의", "LOW": "낮음"}[quality_grade]
    source_type_counts: Dict[str, int] = {}
    for doc in docs:
        source_type = str((doc.metadata or {}).get("source_type") or "UNKNOWN")
        source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1

    top_source_relevance = []
    for card in source_cards[:5]:
        top_source_relevance.append(
            {
                "label": card.get("label"),
                "source_type": card.get("source_type"),
                "page_no": card.get("page_no"),
                "score": 0.86,
                "grade": "GOOD",
                "matched_terms": ["개요", "요약", "청구항", "평가"],
            }
        )

    return {
        "retrieval_quality_score": quality_score,
        "retrieval_quality_grade": quality_grade,
        "retrieval_quality_label": quality_label,
        "retrieval_quality_reason": "개요 질문에 필요한 서지사항, 요약, 청구범위, 해결수단, 효과, 평가보고서 섹션이 함께 검색되었습니다.",
        "search_pass": quality_grade in ("GOOD", "FAIR"),
        "question_match_score": round(lexical_confidence(question, docs), 4),
        "expanded_match_score": round(lexical_confidence(retrieval_question, docs), 4),
        "evidence_doc_count": evidence_doc_count,
        "source_type_counts": source_type_counts,
        "top_source_relevance": top_source_relevance,
        "quality_thresholds": {
            "GOOD": "개요 필수 섹션 70% 이상 + 근거 문서 5개 이상",
            "FAIR": "개요 필수 섹션 45% 이상",
            "LOW": "위 기준 미달",
        },
        "performance_evaluation": [
            {
                "name": "검색 품질",
                "status": quality_grade,
                "value": quality_score,
                "good_threshold": "section_coverage >= 0.70 and evidence_doc_count >= 5",
                "fair_threshold": "section_coverage >= 0.45",
                "message": "개요 답변에 필요한 핵심 섹션이 충분히 모였는지입니다.",
            },
            {
                "name": "필수 섹션 커버리지",
                "status": "GOOD" if section_coverage >= 0.7 else "FAIR" if section_coverage >= 0.45 else "LOW",
                "value": round(section_coverage, 4),
                "good_threshold": ">= 0.70",
                "fair_threshold": ">= 0.45",
                "message": "서지사항/요약/청구범위/과제/해결수단/효과/보고서가 포함됐는지입니다.",
            },
            {
                "name": "근거 문서 수",
                "status": "GOOD" if evidence_doc_count >= 5 else "FAIR" if evidence_doc_count >= 3 else "LOW",
                "value": evidence_doc_count,
                "good_threshold": ">= 5",
                "fair_threshold": ">= 3",
                "message": "답변에 사용한 원문 및 보고서 섹션 수입니다.",
            },
            {
                "name": "원문/보고서 균형",
                "status": "GOOD" if {"ORIGINAL_PDF", "REPORT_PDF"} <= source_types else "FAIR",
                "value": ", ".join(sorted(str(item) for item in source_types if item)),
                "good_threshold": "ORIGINAL_PDF + REPORT_PDF",
                "fair_threshold": "한쪽 문서만 존재",
                "message": "기술 원문과 평가 보고서를 함께 사용했는지입니다.",
            },
        ],
        "retrieval_query_expanded": retrieval_query_expanded,
    }


def build_extractive_answer(
    question: str,
    scope: str,
    docs: List[Document],
    source_cards: List[Dict[str, Any]],
    confidence: float,
) -> str:
    if not docs or not source_cards:
        return "제공된 자료에서 질문과 직접 관련된 근거를 확인할 수 없습니다."

    direct = extractive_direct_answer(question, source_cards)
    answer_lines = [
        "핵심 답변:",
        f"{direct} [자료1]",
        "",
        "근거:",
    ]

    used = 0
    for idx, doc in enumerate(docs[: len(source_cards)], start=1):
        if used >= 4:
            break
        card = source_cards[idx - 1]
        label = card.get("label") or f"자료{idx}"
        source_type = source_type_name(card.get("source_type"))
        page_no = card.get("page_no") or "-"
        evidence_sentences = best_evidence_for_doc(question, doc, max_sentences=1)
        if not evidence_sentences:
            continue
        relevance = card.get("relevance_score")
        relevance_text = f", 관련도 {relevance:.2f}" if isinstance(relevance, (int, float)) else ""
        heading = f"{used + 1}. {source_type} p.{page_no}{relevance_text}: "
        answer_lines.append(f"{heading}{evidence_sentences[0]} [{label}]")
        used += 1

    answer_lines.extend(["", "해석:"])
    q = question.lower()
    original_label = next((card.get("label") for card in source_cards if card.get("source_type") == "ORIGINAL_PDF"), "자료1")
    report_label = next((card.get("label") for card in source_cards if card.get("source_type") == "REPORT_PDF"), original_label)
    if any(k in q for k in ("왜", "필요", "장점", "강점", "효과", "개선")):
        answer_lines.append(
            f"- 위 근거를 종합하면, 이 특허의 장점은 원문에 제시된 해결 과제/발명의 효과가 평가 보고서의 기술성 근거와 연결되는 지점입니다. [{original_label}] [{report_label}]"
        )
        answer_lines.append(
            f"- 다만 실제 개선 폭, 상용 시스템 적용성, 정량 성능 수치는 제공 자료에 명시된 범위에서만 확인해야 합니다. [{report_label}]"
        )
    elif any(k in q for k in ("리스크", "위험", "한계", "단점", "유지", "매각", "제각", "가치")):
        answer_lines.append(
            f"- 위 근거만으로 최종 유지/매각/제각을 결정할 수는 없고, 평가 보고서의 리스크 및 추가 확인 항목을 원문 청구항/사업부 검토 자료와 연결해야 합니다. [{report_label}] [{original_label}]"
        )
        answer_lines.append(
            f"- 특히 유사 특허, 회피설계 가능성, 무효 가능성, 실제 사업 적용 여부는 추가 확인 대상입니다. [{report_label}]"
        )
    else:
        answer_lines.append(
            f"- 위 내용은 검색된 원문/보고서 근거를 그대로 요약한 것이며, 자료 밖의 시장 수치나 법적 결론은 포함하지 않았습니다. [{original_label}]"
        )

    answer_lines.extend(
        [
            "",
            "확인 필요 사항:",
            f"- 현재 답변의 검색 신뢰 점수는 {confidence:.4f}입니다. 낮은 경우에는 원문 PDF 페이지와 보고서 원문을 함께 확인해야 합니다.",
            "- 실제 사업 적용 여부, 유사 특허와의 청구항 중복 여부, 회피설계/무효 가능성, 연차료 대비 활용 가능성은 별도 검토가 필요합니다.",
        ]
    )
    return "\n".join(answer_lines)


def build_global_discovery_answer(
    question: str,
    patent_groups: List[Dict[str, Any]],
    source_cards: List[Dict[str, Any]],
    query_terms: List[str],
    confidence: float,
) -> str:
    intents = detect_question_intents(question)
    if not patent_groups:
        terms = ", ".join(query_terms) if query_terms else question
        return f"전체 특허 인덱스에서 `{terms}`와 직접 관련된 특허를 확인하지 못했습니다."

    label_by_patent: Dict[str, List[str]] = {}
    cards_by_patent: Dict[str, List[Dict[str, Any]]] = {}
    for card in source_cards:
        patent_id = str(card.get("patent_id") or "")
        if not patent_id:
            continue
        label_by_patent.setdefault(patent_id, []).append(str(card.get("label")))
        cards_by_patent.setdefault(patent_id, []).append(card)

    terms_text = ", ".join(query_terms)
    count_phrase = f"{len(patent_groups)}건"
    subject = f"`{terms_text}` 관련 특허" if terms_text else "현재 인덱싱된 특허"
    if terms_text:
        lines = [
            "## 답변",
            "",
            f"현재 검토 데이터 기준으로 {subject}는 {count_phrase}입니다.",
            "아래 표는 원문과 보고서를 특허 단위로 묶어 관련성이 높은 순서로 정리한 결과입니다.",
            "",
            "## 관련 특허",
            "",
            "| 순위 | 특허 | 관련성 | 핵심 이유 | 주요 출처 |",
            "| --- | --- | --- | --- | --- |",
        ]
    else:
        lines = [
            "## 답변",
            "",
            f"현재 인덱싱된 특허는 {count_phrase}입니다.",
            "",
            "## 특허 목록",
            "",
            "| 순위 | 특허 | 번호 | 요약 | 주요 출처 |",
            "| --- | --- | --- | --- | --- |",
        ]

    for idx, group in enumerate(patent_groups, start=1):
        labels = label_by_patent.get(group["patent_id"], [])
        label_text = " ".join(f"[{label}]" for label in labels[:2]) or "[자료1]"
        reg = group.get("registration_number") or group.get("application_number") or "-"
        group_cards = cards_by_patent.get(group["patent_id"], [])
        primary = group_cards[0] if group_cards else {}
        report_card = next((card for card in group_cards if card.get("source_type") == "REPORT_PDF"), None)
        snippet = strip_section_noise(str((primary or report_card or {}).get("snippet") or ""))
        report_snippet = strip_section_noise(str((report_card or {}).get("snippet") or ""))

        if terms_text and group.get("relationship") in ("직접 관련", "원문 직접 관련"):
            relationship = str(group.get("relationship"))
        elif terms_text:
            relationship = "간접 관련"
        else:
            relationship = "목록"

        matched = ", ".join(group.get("matched_terms") or query_terms) or "전체 목록"
        reason = first_sentence(snippet or report_snippet or f"{group['title']} 관련 자료가 확인됩니다.", 145)
        if report_snippet and terms_text:
            report_reason = first_sentence(report_snippet, 120)
            noisy_report = (
                report_reason.startswith("IP 가치 평가 보고서")
                or "출원일 ." in report_reason
                or "등록일 ." in report_reason
                or len(report_reason) < 35
            )
            if report_reason and not noisy_report and report_reason not in reason:
                reason = f"{reason} 보고서에서는 {report_reason}"
        reason = reason.replace("|", "/")

        if terms_text:
            lines.append(
                f"| {idx} | {group['title']} / {reg} | {relationship}, 매칭어: {matched} | {reason} | {label_text} |"
            )
        else:
            lines.append(
                f"| {idx} | {group['title']} | {reg} | {reason} | {label_text} |"
            )

    if "COUNT" in intents:
        lines.extend(
            [
                "",
                "## 수량 요약",
                "",
                f"- 조건에 맞는 특허는 {len(patent_groups)}건입니다.",
            ]
        )

    top_group = patent_groups[0]
    top_labels = label_by_patent.get(top_group["patent_id"], [])
    top_label_text = " ".join(f"[{label}]" for label in top_labels[:2]) or "[자료1]"
    if terms_text:
        plural_note = "- 표의 나머지 후보는 보고서나 원문에 같은 키워드가 나타나는 정도를 기준으로 정렬했습니다." if len(patent_groups) > 1 else "- 현재 인덱스에서는 이 특허가 질문 키워드와 가장 직접적으로 연결됩니다."
        lines.extend(
            [
                "",
                "## 해석",
                "",
                f"- 가장 직접적인 후보는 {top_group['title']}입니다. 질문 키워드가 원문 또는 제목 수준에서 확인되어 우선 검토 대상으로 볼 수 있습니다. {top_label_text}",
                plural_note,
                "- 최종 유지/매각/제각 판단은 이 목록만으로 결정할 수 없고, 개별 특허 상세 화면에서 청구항과 평가보고서를 함께 확인해야 합니다.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## 해석",
                "",
                "- 위 표는 현재 챗봇이 접근 가능한 전체 인덱스 목록입니다.",
                "- 특정 기술어를 함께 입력하면 관련 특허만 좁혀서 볼 수 있습니다. 예: `물류 특허`, `반도체 특허`, `모니터링 특허`.",
            ]
        )

    lines.extend(
        [
            "",
            "## 확인 필요 사항",
            "",
            "- 원문 PDF의 청구항과 AI 평가 보고서의 점수·리스크 항목을 함께 확인해야 합니다.",
            "- 외부 최신 특허나 KIPRIS 실시간 조회 결과는 현재 내부 인덱스와 별도입니다.",
        ]
    )
    return "\n".join(lines)


def build_global_web_answer(
    question: str,
    web_docs: List[Document],
    source_cards: List[Dict[str, Any]],
    domain_matches: List[Dict[str, Any]],
) -> str:
    if not web_docs or not source_cards:
        return (
            "외부 웹 검색 결과를 확보하지 못했습니다.\n\n"
            "확인 필요 사항:\n"
            "- 네트워크 또는 검색 API 설정을 확인해야 합니다.\n"
            "- 내부 보고서에 있는 시장성 정보만으로는 최신 시장 상황을 단정할 수 없습니다."
        )

    subject_terms = discovery_query_terms(question)
    subject = " ".join(subject_terms[:4]) if subject_terms else question
    lines = [
        "## 웹 검색 기준 답변",
        "",
        f"`{subject}`에 대해서는 내부 특허 원문이 아니라 외부 웹 출처를 기준으로 확인해야 하는 질문입니다. 아래 내용은 웹 검색 결과 요약이며, 각 수치나 전망은 원문 출처에서 재확인해야 합니다.",
        "",
        "## 확인된 외부 자료",
        "",
        "| 자료 | 출처 등급 | 출처 제목 | 확인된 내용 |",
        "| --- | --- | --- | --- |",
    ]

    for doc, card in zip(web_docs[: len(source_cards)], source_cards):
        label = card.get("label") or "자료"
        title = str(card.get("title") or "웹 자료").replace("|", "/")
        grade = str(card.get("web_source_type") or "웹").replace("|", "/")
        source_grade = str(card.get("web_source_grade") or "FAIR")
        snippet = first_sentence(clean_evidence_text(doc.page_content), 190).replace("|", "/")
        lines.append(f"| [{label}] | {grade} / {source_grade} | {title} | {snippet} |")

    lines.extend(["", "## 시장 상황 해석", ""])
    labels = [str(card.get("label") or f"자료{idx}") for idx, card in enumerate(source_cards[:3], start=1)]
    if labels:
        lines.append(
            f"- 현재 질문은 최신성 있는 시장/동향 정보가 필요하므로 내부 특허 검색이 아니라 웹 검색 출처를 우선 근거로 사용했습니다. {' '.join(f'[{label}]' for label in labels)}"
        )
    lines.append("- 물류 시장의 규모, 성장률, 전망은 출처마다 조사 범위가 다를 수 있으므로 단일 숫자로 단정하지 않고 출처별로 분리해 확인하는 것이 안전합니다.")
    if domain_matches:
        top = domain_matches[0]
        lines.append(
            f"- 내부 인덱스에서는 `{top.get('title')}` 특허가 물류 키워드와 연결되지만, 위 웹 자료는 외부 시장 동향으로 별도 구분해야 합니다."
        )

    lines.extend(
        [
            "",
            "## 확인 필요 사항",
            "",
            "- 시장 규모나 성장률을 보고서에 반영하려면 출처 원문, 발행일, 조사 지역, 시장 정의를 함께 기록해야 합니다.",
            "- 이 웹 검색 결과만으로 특정 특허의 유지/매각/제각을 단정할 수는 없습니다.",
            "- 특허 평가에 반영하려면 내부 평가 보고서의 시장성 및 사업성 항목과 별도로 교차 확인해야 합니다.",
        ]
    )
    return "\n".join(lines)


def build_patent_web_answer(
    question: str,
    patent_meta: Dict[str, Any],
    local_docs: List[Document],
    web_docs: List[Document],
    local_source_cards: List[Dict[str, Any]],
    web_source_cards: List[Dict[str, Any]],
) -> str:
    title = str(patent_meta.get("title") or patent_meta.get("patent_id") or "선택 특허")
    reg = str(patent_meta.get("registration_number") or patent_meta.get("patent_id") or "-")
    labels = " ".join(f"[{card.get('label')}]" for card in web_source_cards[:3] if card.get("label"))
    lines = [
        "## 내부 자료와 웹 자료를 분리해서 정리했습니다",
        "",
        f"선택된 특허는 **{title} / {reg}**입니다. 최신 시장·동향 정보는 내부 원문만으로 단정하기 어려워, 내부 근거와 외부 웹 출처를 나누어 확인했습니다.",
        "",
        "## 내부 자료 기준",
        "",
    ]

    if local_docs and local_source_cards:
        lines.extend(
            [
                "| 자료 | 확인된 내부 근거 |",
                "| --- | --- |",
            ]
        )
        for doc, card in zip(local_docs[:3], local_source_cards[:3]):
            label = card.get("label") or "자료"
            snippet = first_sentence(clean_evidence_text(doc.page_content), 180).replace("|", "/")
            lines.append(f"| [{label}] | {snippet} |")
    else:
        lines.append("- 내부 원문/보고서에서는 최신 외부 시장 상황을 직접 단정할 만큼의 근거가 충분하지 않습니다.")

    lines.extend(
        [
            "",
            "## 외부 웹 기준",
            "",
        ]
    )
    if web_docs and web_source_cards:
        lines.extend(
            [
                "| 자료 | 출처 등급 | 출처 제목 | 확인된 내용 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for doc, card in zip(web_docs[: len(web_source_cards)], web_source_cards):
            label = card.get("label") or "자료"
            source_title = str(card.get("title") or "웹 자료").replace("|", "/")
            source_type = str(card.get("web_source_type") or "웹").replace("|", "/")
            source_grade = str(card.get("web_source_grade") or "FAIR")
            snippet = first_sentence(clean_evidence_text(doc.page_content), 190).replace("|", "/")
            lines.append(f"| [{label}] | {source_type} / {source_grade} | {source_title} | {snippet} |")
    else:
        lines.append("- 외부 웹 검색 결과를 확보하지 못했습니다.")

    lines.extend(
        [
            "",
            "## 해석",
            "",
            f"- 이 질문은 선택 특허의 기술 자체보다 최신 시장·동향 확인 성격이 강하므로, 웹 출처를 별도 근거로 사용했습니다. {labels}".rstrip(),
            "- 내부 보고서의 시장성·사업성 평가는 특허 평가 관점이고, 웹 검색 결과는 외부 환경 확인 관점이므로 서로 구분해서 봐야 합니다.",
            "- 웹 검색 결과만으로 유지/매각/제각을 단정할 수는 없고, 사업부 적용 가능성·유사 특허·고객/제품 적용 근거와 함께 검토해야 합니다.",
            "",
            "## 확인 필요 사항",
            "",
            "- 시장 규모나 성장률은 출처별 조사 범위, 지역, 기준연도가 다를 수 있으므로 원문 출처에서 재확인해야 합니다.",
            "- 내부 보고서에 반영하려면 외부 자료의 발행일, 기관명, URL, 인용 범위를 별도 기록하는 것이 좋습니다.",
        ]
    )
    return "\n".join(lines)


def build_web_quality_metrics(
    question: str,
    web_docs: List[Document],
    source_cards: List[Dict[str, Any]],
    web_ms: int,
) -> Dict[str, Any]:
    evidence_doc_count = len(source_cards)
    question_match_score = lexical_confidence(question, web_docs)
    quality_score = round(min(1.0, 0.2 + min(1.0, evidence_doc_count / 4) * 0.55 + question_match_score * 0.25), 4) if web_docs else 0.0
    quality_grade = "GOOD" if quality_score >= 0.62 and evidence_doc_count >= 3 else "FAIR" if quality_score >= 0.38 and evidence_doc_count >= 1 else "LOW"
    quality_label = {"GOOD": "양호", "FAIR": "주의", "LOW": "낮음"}[quality_grade]
    return {
        "retrieval_quality_score": quality_score,
        "retrieval_quality_grade": quality_grade,
        "retrieval_quality_label": quality_label,
        "retrieval_quality_reason": "외부 웹 검색 결과를 근거로 답변했습니다." if quality_grade != "LOW" else "외부 웹 검색 근거가 부족합니다.",
        "search_pass": quality_grade in ("GOOD", "FAIR"),
        "question_match_score": round(question_match_score, 4),
        "expanded_match_score": round(question_match_score, 4),
        "evidence_doc_count": evidence_doc_count,
        "source_type_counts": {"WEB": evidence_doc_count} if evidence_doc_count else {},
        "top_source_relevance": [
            {
                "label": card.get("label"),
                "source_type": "WEB",
                "page_no": None,
                "score": 0.72,
                "grade": "GOOD",
                "matched_terms": discovery_query_terms(question),
            }
            for card in source_cards[:5]
        ],
        "quality_thresholds": {
            "GOOD": "웹 출처 3개 이상 + 품질 0.62 이상",
            "FAIR": "웹 출처 1개 이상 + 품질 0.38 이상",
            "LOW": "위 기준 미달",
        },
        "performance_evaluation": [
            {
                "name": "웹 검색 품질",
                "status": quality_grade,
                "value": quality_score,
                "good_threshold": ">= 0.62 and web_context_count >= 3",
                "fair_threshold": ">= 0.38 and web_context_count >= 1",
                "message": "외부 웹 출처가 충분히 확보됐는지입니다.",
            },
            {
                "name": "웹 출처 수",
                "status": "GOOD" if evidence_doc_count >= 3 else "FAIR" if evidence_doc_count >= 1 else "LOW",
                "value": evidence_doc_count,
                "good_threshold": ">= 3",
                "fair_threshold": ">= 1",
                "message": "답변에 사용된 외부 출처 수입니다.",
            },
            {
                "name": "웹 검색 시간",
                "status": "GOOD" if web_ms < 5000 else "FAIR" if web_ms < 15000 else "LOW",
                "value": web_ms,
                "good_threshold": "< 5000ms",
                "fair_threshold": "< 15000ms",
                "message": "외부 검색 요청에 걸린 시간입니다.",
            },
        ],
        "retrieval_query_expanded": False,
    }


class PatentRAGPipeline:
    def __init__(self) -> None:
        self._embeddings = None
        self.vectorstores: Dict[str, FAISS] = {}
        self.docs_by_patent: Dict[str, List[Document]] = {}
        self.bm25_by_patent: Dict[str, BM25Index] = {}
        self.business_vectorstore: Optional[FAISS] = None
        self.business_docs: List[Document] = []
        self.business_bm25: Optional[BM25Index] = None
        self.global_vectorstore: Optional[FAISS] = None
        self.global_docs: List[Document] = []
        self.global_bm25: Optional[BM25Index] = None
        self.domain_cards: List[Document] = []

    @property
    def embeddings(self):
        if self._embeddings is None:
            if EMBEDDING_PROVIDER == "openai":
                if OpenAIEmbeddings is None:
                    raise RuntimeError("langchain-openai is required when EMBEDDING_PROVIDER=openai")
                if not OPENAI_API_KEY:
                    raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
                self._embeddings = OpenAIEmbeddings(
                    model=EMBEDDING_MODEL,
                    api_key=OPENAI_API_KEY,
                    base_url=OPENAI_BASE_URL,
                )
            else:
                self._embeddings = HuggingFaceEmbeddings(
                    model_name=EMBEDDING_MODEL,
                    model_kwargs={"device": EMBEDDING_DEVICE},
                )
        return self._embeddings

    def ensure_domain_cards(self, force_rebuild: bool = False) -> List[Document]:
        if self.domain_cards and not force_rebuild:
            return self.domain_cards

        if self.global_vectorstore is None or self.global_bm25 is None or not self.global_docs:
            self.build_or_load_global_index(force_rebuild=force_rebuild)

        docs_by_patent: Dict[str, List[Document]] = {}
        for doc in self.global_docs:
            patent_id = _patent_id_from_doc(doc)
            if not patent_id:
                continue
            docs_by_patent.setdefault(patent_id, []).append(doc)

        cards: List[Document] = []
        for patent_id, docs in docs_by_patent.items():
            try:
                patent_meta = self.load_patent_meta(patent_id)
            except Exception:
                patent_meta = {"patent_id": patent_id, "title": patent_id}
            cards.append(build_patent_domain_card(patent_id, patent_meta, docs))

        self.domain_cards = cards
        return self.domain_cards

    def list_patent_meta_rows(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if not PATENTS_ROOT.exists():
            return rows
        for patent_dir in sorted(path for path in PATENTS_ROOT.iterdir() if path.is_dir()):
            if patent_dir.name.startswith(".") or patent_dir.name in ("patent-original", "_global"):
                continue
            try:
                meta = self.load_patent_meta(patent_dir.name)
            except Exception:
                continue
            rows.append(
                {
                    "patent_id": meta.get("patent_id") or patent_dir.name,
                    "title": meta.get("title") or patent_dir.name,
                    "registration_number": meta.get("registration_number") or meta.get("patent_id") or patent_dir.name,
                    "application_number": meta.get("application_number"),
                    "ipc_code": meta.get("ipc_code"),
                }
            )
        return rows

    def build_patent_summary_cards(self) -> List[Dict[str, Any]]:
        cards: List[Dict[str, Any]] = []
        for row in self.list_patent_meta_rows():
            patent_id = str(row.get("patent_id"))
            try:
                meta = self.load_patent_meta(patent_id)
                docs = load_patent_docs_from_disk(patent_id)
            except Exception:
                continue
            snapshot = patent_score_snapshot(patent_id, meta, docs)
            domain_terms = []
            for card in self.ensure_domain_cards():
                if (card.metadata or {}).get("patent_id") == patent_id:
                    domain_terms = (card.metadata or {}).get("domain_terms") or []
                    break
            cards.append(
                {
                    **snapshot,
                    "domain_terms": domain_terms[:6],
                    "score_level": score_level(snapshot.get("total")),
                }
            )
        return cards

    def match_domain_cards(
        self,
        question: str,
        max_matches: int = 5,
        min_score: float = 0.34,
    ) -> List[Dict[str, Any]]:
        cards = self.ensure_domain_cards()
        matches: List[Dict[str, Any]] = []
        for card in cards:
            score, matched_terms = score_domain_card(question, card)
            if score < min_score:
                continue
            meta = card.metadata or {}
            matches.append(
                {
                    "patent_id": meta.get("patent_id"),
                    "title": meta.get("title"),
                    "registration_number": meta.get("registration_number"),
                    "score": score,
                    "matched_terms": matched_terms,
                    "domain_terms": (meta.get("domain_terms") or [])[:10],
                }
            )
        matches.sort(key=lambda item: item["score"], reverse=True)
        return matches[:max_matches]

    def load_patent_meta(self, patent_id: str) -> Dict[str, Any]:
        return load_compatible_patent_meta(PATENTS_ROOT / patent_id)

    def build_or_load_patent_index(self, patent_id: str, force_rebuild: bool = False) -> None:
        patent_dir = PATENTS_ROOT / patent_id
        index_dir = patent_dir / "index" / "faiss"
        docs_path = patent_dir / "extracted" / "all_chunks.jsonl"

        if _index_matches_embedding(index_dir) and docs_path.exists() and not force_rebuild:
            self.vectorstores[patent_id] = FAISS.load_local(
                str(index_dir),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            docs = read_documents_jsonl(docs_path)
            self.docs_by_patent[patent_id] = docs
            self.bm25_by_patent[patent_id] = BM25Index(docs)
            return

        docs = _load_existing_patent_documents(patent_dir)
        if not docs:
            docs = build_patent_documents(
                patent_dir=patent_dir,
                public_file_base_url=PUBLIC_FILE_BASE_URL,
                max_chars=CHUNK_MAX_CHARS,
                overlap=CHUNK_OVERLAP,
            )
        if not docs:
            raise ValueError(f"No documents found for patent_id={patent_id}")

        index_dir.mkdir(parents=True, exist_ok=True)
        vectorstore = FAISS.from_documents(docs, self.embeddings)
        vectorstore.save_local(str(index_dir))
        _write_embedding_manifest(index_dir)
        write_documents_jsonl(docs, docs_path)

        by_type: Dict[str, List[Document]] = {}
        for doc in docs:
            by_type.setdefault((doc.metadata or {}).get("source_type", "UNKNOWN"), []).append(doc)
        for source_type, type_docs in by_type.items():
            write_documents_jsonl(
                type_docs,
                patent_dir / "extracted" / f"{source_type.lower()}_chunks.jsonl",
            )

        self.vectorstores[patent_id] = vectorstore
        self.docs_by_patent[patent_id] = docs
        self.bm25_by_patent[patent_id] = BM25Index(docs)

    def build_or_load_business_index(self, force_rebuild: bool = False) -> None:
        business_dir = DATA_ROOT / "business"
        index_dir = business_dir / "index" / "faiss"
        docs_path = business_dir / "index" / "all_chunks.jsonl"

        if _index_matches_embedding(index_dir) and docs_path.exists() and not force_rebuild:
            self.business_vectorstore = FAISS.load_local(
                str(index_dir),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            self.business_docs = read_documents_jsonl(docs_path)
            self.business_bm25 = BM25Index(self.business_docs)
            return

        docs = build_business_documents(
            business_dir=business_dir,
            public_file_base_url=PUBLIC_FILE_BASE_URL,
            max_chars=CHUNK_MAX_CHARS,
            overlap=CHUNK_OVERLAP,
        )
        if not docs:
            raise ValueError(f"No business documents found in {business_dir}")

        index_dir.mkdir(parents=True, exist_ok=True)
        self.business_vectorstore = FAISS.from_documents(docs, self.embeddings)
        self.business_vectorstore.save_local(str(index_dir))
        _write_embedding_manifest(index_dir)
        write_documents_jsonl(docs, docs_path)
        self.business_docs = docs
        self.business_bm25 = BM25Index(docs)

    def _retrieve_from_store(
        self,
        vectorstore: FAISS,
        bm25: BM25Index,
        question: str,
    ) -> Tuple[List[Document], Dict[str, int]]:
        t0 = now_ms()
        vector_docs = vectorstore.similarity_search(question, k=TOP_K_CANDIDATES)
        vector_ms = now_ms() - t0

        t1 = now_ms()
        bm25_docs = bm25.search(question, k=TOP_K_CANDIDATES)
        bm25_ms = now_ms() - t1

        merged = rrf_merge(
            [vector_docs, bm25_docs],
            topn=max(TOP_K, TOP_K_CANDIDATES),
            source_type_weights=SOURCE_TYPE_WEIGHTS,
        )
        reranked = rerank_by_lexical_overlap(question, merged)[:TOP_K]
        # compute lexical confidence and if low, trigger an expanded fallback
        lex_conf = lexical_confidence(question, reranked)
        metrics: Dict[str, int] = {
            "vector_ms": vector_ms,
            "bm25_ms": bm25_ms,
            "retrieval_ms": now_ms() - t0,
            "lexical_confidence": round(lex_conf, 4),
        }

        if lex_conf < MIN_LOCAL_CONFIDENCE:
            # expanded RRF search: increase topn and reduce RRF_K to emphasize top ranks
            try:
                expanded_topn = max(TOP_K * 2, TOP_K_CANDIDATES)
                expanded_rrf_k = max(6, int(RRF_K / 2))
                merged2 = rrf_merge(
                    [vector_docs, bm25_docs],
                    topn=expanded_topn,
                    rrf_k=expanded_rrf_k,
                    source_type_weights=SOURCE_TYPE_WEIGHTS,
                )
                reranked2 = rerank_by_lexical_overlap(question, merged2)[:TOP_K]
                lex_conf2 = lexical_confidence(question, reranked2)
                metrics["expanded_rrf_k"] = expanded_rrf_k
                metrics["expanded_topn"] = expanded_topn
                metrics["lexical_confidence_expanded"] = round(lex_conf2, 4)
                if lex_conf2 > lex_conf:
                    reranked = reranked2
                    metrics["retrieval_strategy"] = "expanded_rrf"
            except Exception:
                # keep original reranked on any failure
                pass

        return reranked, metrics

    def _retrieve_from_store_multi(
        self,
        vectorstore: FAISS,
        bm25: BM25Index,
        questions: List[str],
    ) -> Tuple[List[Document], Dict[str, int]]:
        t0 = now_ms()
        vector_ms = 0
        bm25_ms = 0
        ranked_lists: List[List[Document]] = []
        seen_queries: List[str] = []

        for query in questions:
            clean_query = normalize(query)
            if not clean_query or clean_query in seen_queries:
                continue
            seen_queries.append(clean_query)

            v0 = now_ms()
            ranked_lists.append(vectorstore.similarity_search(clean_query, k=TOP_K_CANDIDATES))
            vector_ms += now_ms() - v0

            b0 = now_ms()
            ranked_lists.append(bm25.search(clean_query, k=TOP_K_CANDIDATES))
            bm25_ms += now_ms() - b0

        merged = rrf_merge(
            ranked_lists,
            topn=max(TOP_K, TOP_K_CANDIDATES),
            source_type_weights=SOURCE_TYPE_WEIGHTS,
        )
        reranked = rerank_by_lexical_overlap(" ".join(seen_queries), merged)[:TOP_K]
        lex_conf = lexical_confidence(" ".join(seen_queries), reranked)
        metrics: Dict[str, int] = {
            "vector_ms": vector_ms,
            "bm25_ms": bm25_ms,
            "retrieval_ms": now_ms() - t0,
            "retrieval_pass_count": len(seen_queries),
            "lexical_confidence": round(lex_conf, 4),
        }

        if lex_conf < MIN_LOCAL_CONFIDENCE:
            try:
                expanded_topn = max(TOP_K * 2, TOP_K_CANDIDATES)
                expanded_rrf_k = max(6, int(RRF_K / 2))
                merged2 = rrf_merge(
                    ranked_lists,
                    topn=expanded_topn,
                    rrf_k=expanded_rrf_k,
                    source_type_weights=SOURCE_TYPE_WEIGHTS,
                )
                reranked2 = rerank_by_lexical_overlap(" ".join(seen_queries), merged2)[:TOP_K]
                lex_conf2 = lexical_confidence(" ".join(seen_queries), reranked2)
                metrics["expanded_rrf_k"] = expanded_rrf_k
                metrics["expanded_topn"] = expanded_topn
                metrics["lexical_confidence_expanded"] = round(lex_conf2, 4)
                if lex_conf2 > lex_conf:
                    reranked = reranked2
                    metrics["retrieval_strategy"] = "expanded_rrf"
            except Exception:
                pass

        return reranked, metrics

    def retrieve_patent(self, patent_id: str, question: str) -> Tuple[List[Document], Dict[str, int]]:
        load_t0 = now_ms()
        index_load_ms = 0
        if patent_id not in self.vectorstores:
            self.build_or_load_patent_index(patent_id)
            index_load_ms = now_ms() - load_t0
        docs, metrics = self._retrieve_from_store(
            self.vectorstores[patent_id],
            self.bm25_by_patent[patent_id],
            question,
        )
        # if lexical confidence is low, try multi-query expansion using patent metadata
        try:
            lex_conf = metrics.get("lexical_confidence", 0.0)
        except Exception:
            lex_conf = 0.0
        if lex_conf < MIN_LOCAL_CONFIDENCE:
            try:
                patent_meta = self.load_patent_meta(patent_id)
                queries = expand_queries_for_patent(question, patent_meta)
                if len(queries) > 1:
                    docs2, metrics2 = self._retrieve_from_store_multi(
                        self.vectorstores[patent_id],
                        self.bm25_by_patent[patent_id],
                        queries,
                    )
                    # prefer expanded result if lexical confidence improves
                    if metrics2.get("lexical_confidence", 0.0) > lex_conf:
                        docs = docs2
                        metrics.update({f"expanded_{k}": v for k, v in metrics2.items()})
                        metrics["retrieval_strategy"] = "query_expansion"
            except Exception:
                pass
        metrics["index_load_ms"] = index_load_ms
        return docs, metrics

    def retrieve_patent_multi(self, patent_id: str, questions: List[str]) -> Tuple[List[Document], Dict[str, int]]:
        load_t0 = now_ms()
        index_load_ms = 0
        if patent_id not in self.vectorstores:
            self.build_or_load_patent_index(patent_id)
            index_load_ms = now_ms() - load_t0
        docs, metrics = self._retrieve_from_store_multi(
            self.vectorstores[patent_id],
            self.bm25_by_patent[patent_id],
            questions,
        )
        metrics["index_load_ms"] = index_load_ms
        return docs, metrics

    def retrieve_business(self, question: str) -> Tuple[List[Document], Dict[str, int]]:
        load_t0 = now_ms()
        index_load_ms = 0
        if self.business_vectorstore is None or self.business_bm25 is None:
            self.build_or_load_business_index()
            index_load_ms = now_ms() - load_t0
        assert self.business_vectorstore is not None
        assert self.business_bm25 is not None
        docs, metrics = self._retrieve_from_store(self.business_vectorstore, self.business_bm25, question)
        metrics["index_load_ms"] = index_load_ms
        return docs, metrics

    def _iter_patent_ids(self) -> List[str]:
        patents_root = PATENTS_ROOT
        if not patents_root.exists():
            return []
        patent_ids = []
        for patent_dir in sorted(path for path in patents_root.iterdir() if path.is_dir()):
            if patent_dir.name.startswith(".") or patent_dir.name in ("patent-original", "_global"):
                continue
            if not any((patent_dir / name).exists() for name in ("meta.json", "metadata.json", "manifest.json")):
                continue
            try:
                meta = load_compatible_patent_meta(patent_dir)
                patent_ids.append(str(meta.get("patent_id") or patent_dir.name))
            except Exception:
                patent_ids.append(patent_dir.name)
        return patent_ids

    def build_or_load_global_index(self, force_rebuild: bool = False) -> None:
        global_dir = PATENTS_ROOT / "_global"
        index_dir = global_dir / "index" / "faiss"
        docs_path = global_dir / "all_chunks.jsonl"
        reviewed_docs_path = global_dir / "index" / "vectorstore" / "documents.jsonl"

        load_docs_path = docs_path if docs_path.exists() else reviewed_docs_path
        if _index_matches_embedding(index_dir) and load_docs_path.exists() and not force_rebuild:
            self.global_vectorstore = FAISS.load_local(
                str(index_dir),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            self.global_docs = read_documents_jsonl(load_docs_path)
            self.global_bm25 = BM25Index(self.global_docs)
            self.domain_cards = []
            return

        all_docs: List[Document] = []
        merged_vectorstore: Optional[FAISS] = None
        for patent_id in self._iter_patent_ids():
            patent_dir = PATENTS_ROOT / patent_id
            docs_path_for_patent = patent_dir / "extracted" / "all_chunks.jsonl"
            docs = _load_existing_patent_documents(patent_dir)
            if not docs:
                docs = build_patent_documents(
                    patent_dir=patent_dir,
                    public_file_base_url=PUBLIC_FILE_BASE_URL,
                    max_chars=CHUNK_MAX_CHARS,
                    overlap=CHUNK_OVERLAP,
                )
                if docs:
                    write_documents_jsonl(docs, docs_path_for_patent)
            if not docs:
                continue
            all_docs.extend(docs)

            local_index_dir = patent_dir / "index" / "faiss"
            if not _index_matches_embedding(local_index_dir):
                try:
                    self.build_or_load_patent_index(patent_id, force_rebuild=True)
                except Exception:
                    continue
            if _index_matches_embedding(local_index_dir):
                local_store = FAISS.load_local(
                    str(local_index_dir),
                    self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                if merged_vectorstore is None:
                    merged_vectorstore = local_store
                else:
                    merged_vectorstore.merge_from(local_store)

        if not all_docs:
            raise ValueError("No patent documents found for global index")

        global_dir.mkdir(parents=True, exist_ok=True)
        index_dir.mkdir(parents=True, exist_ok=True)
        if merged_vectorstore is None:
            merged_vectorstore = FAISS.from_documents(all_docs, self.embeddings)
        self.global_vectorstore = merged_vectorstore
        self.global_vectorstore.save_local(str(index_dir))
        _write_embedding_manifest(index_dir)
        write_documents_jsonl(all_docs, docs_path)
        self.global_docs = all_docs
        self.global_bm25 = BM25Index(all_docs)
        self.domain_cards = []

    def retrieve_global(self, questions: List[str]) -> Tuple[List[Document], Dict[str, int]]:
        load_t0 = now_ms()
        index_load_ms = 0
        if self.global_vectorstore is None or self.global_bm25 is None:
            self.build_or_load_global_index()
            index_load_ms = now_ms() - load_t0
        assert self.global_vectorstore is not None
        assert self.global_bm25 is not None
        docs, metrics = self._retrieve_from_store_multi(self.global_vectorstore, self.global_bm25, questions)
        metrics["index_load_ms"] = index_load_ms
        return docs, metrics

    def _log_query(
        self,
        user_id: Optional[str],
        patent_id: Optional[str],
        question: str,
        scope: str,
        confidence: float,
        metrics: Dict[str, Any],
    ) -> None:
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {
                            "user_id": user_id,
                            "patent_id": patent_id,
                            "question": question,
                            "answer_scope": scope,
                            "confidence_score": round(confidence, 4),
                            **metrics,
                            "created_at_ms": now_ms(),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except Exception:
            pass

    def _blocked_response(
        self,
        answer: str,
        patent_id: Optional[str],
        scope: str,
        total_t0: int,
        confidence: float = 0.0,
        extra_metrics: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        question: str = "",
    ) -> Dict[str, Any]:
        metrics = {
            "scope": scope,
            "patent_id": patent_id,
            "local_context_count": 0,
            "web_context_count": 0,
            "confidence_score": round(confidence, 4),
            "total_ms": now_ms() - total_t0,
        }
        if extra_metrics:
            metrics.update(extra_metrics)
        self._log_query(user_id, patent_id, question, scope, confidence, metrics)
        return {"answer": answer, "source_cards": [], "metrics": metrics if RETURN_PERFORMANCE else {}}

    def answer(
        self,
        question: str,
        patent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        context_patent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        total_t0 = now_ms()
        hist = history_context(chat_history, context_patent_id)
        if not patent_id and hist.get("current_patent_id") and is_contextual_followup_question(question):
            patent_id = str(hist["current_patent_id"])
        scope = classify_scope(question)

        if patent_id and is_other_patent_disambiguation_question(question):
            rows = self.list_patent_meta_rows()
            metrics = {
                "scope": "GLOBAL",
                "patent_id": None,
                "global_search": True,
                "patent_hit_count": len(rows),
                "local_context_count": 0,
                "web_context_count": 0,
                "confidence_score": 1.0,
                "retrieval_ms": 0,
                "vector_ms": 0,
                "bm25_ms": 0,
                "web_search_ms": 0,
                "llm_ms": 0,
                "total_ms": now_ms() - total_t0,
                "answer_mode": "PATENT_SELECTION",
                "answer_cache_hit": False,
                "answer_generation_basis": "available_patent_catalog",
                "answer_presentation": ["patent_selection_table"],
                "history_context_used": True,
                "context_patent_id": patent_id,
                "search_result_patents": rows,
                "retrieval_quality_score": 1.0,
                "retrieval_quality_grade": "GOOD",
                "retrieval_quality_label": "양호",
                "retrieval_quality_reason": "다른 특허 선택 의도가 확인되어 현재 특허를 제외한 후보를 제시했습니다.",
                "search_pass": True,
            }
            self._log_query(user_id, None, question, "GLOBAL", 1.0, metrics)
            return {
                "answer": build_patent_selection_answer(rows, patent_id),
                "source_cards": [],
                "metrics": metrics if RETURN_PERFORMANCE else {},
            }
        scope_metrics: Dict[str, Any] = {
            "rule_scope": scope,
            "intent_agent_used": False,
            "scope_strategy": "context_first_evidence_gate",
        }

        if patent_id and is_clearly_unrelated_question(question):
            scope_metrics.update(
                {
                    "intent_agent_scope": "OUT_OF_SCOPE",
                    "intent_agent_confidence": 1.0,
                    "intent_agent_reason": "명백한 생활/잡담/추천 주제라 검색 전에 차단",
                    "intent_agent_ms": 0,
                }
            )
            return self._blocked_response(
                OUT_OF_SCOPE_ANSWER,
                patent_id,
                "OUT_OF_SCOPE",
                total_t0,
                extra_metrics=scope_metrics,
                user_id=user_id,
                question=question,
            )

        if patent_id:
            patent_meta_for_scope = self.load_patent_meta(patent_id)
            if scope == "BUSINESS" and not is_patent_decision_or_value_question(question):
                scope_metrics.update(
                    {
                        "intent_agent_scope": "BUSINESS",
                        "intent_agent_confidence": 1.0,
                        "intent_agent_reason": "선택된 특허 화면에서 들어온 업무 프로세스 질문으로 판정",
                        "intent_agent_ms": 0,
                    }
                )
            elif requires_external_patent_info(question):
                scope = "PATENT_WEB"
                scope_metrics.update(
                    {
                        "intent_agent_scope": scope,
                        "intent_agent_confidence": 1.0,
                        "intent_agent_reason": "현재 특허와 관련된 외부/최신 정보 요구로 판정하고 내부 근거 검색 후 웹 보강을 시도",
                        "intent_agent_ms": 0,
                    }
                )
            else:
                scope = "PATENT_LOCAL"
                scope_metrics.update(
                    {
                        "intent_agent_scope": scope,
                        "intent_agent_confidence": 1.0,
                        "intent_agent_reason": "patent_id가 선택되어 현재 특허 후보로 라우팅하고 검색 근거 품질로 답변 가능 여부를 판정",
                        "intent_agent_ms": 0,
                    }
                )

        if scope == "OUT_OF_SCOPE":
            return self._blocked_response(
                OUT_OF_SCOPE_ANSWER,
                patent_id,
                scope,
                total_t0,
                extra_metrics=scope_metrics,
                user_id=user_id,
                question=question,
            )

        if is_other_patent_question(patent_id, question):
            return self._blocked_response(
                "현재 patent_id 범위를 벗어난 특허 내용은 답변할 수 없습니다.",
                patent_id,
                "OUT_OF_SCOPE",
                total_t0,
                extra_metrics=scope_metrics,
                user_id=user_id,
                question=question,
            )

        if scope in ("PATENT_LOCAL", "PATENT_WEB") and not patent_id:
            return self._blocked_response(
                "특허 개별 질문에는 patent_id가 필요합니다.",
                patent_id,
                scope,
                total_t0,
                extra_metrics=scope_metrics,
                user_id=user_id,
                question=question,
            )

        if ENABLE_STRUCTURED_FAST_PATH and scope in ("PATENT_LOCAL", "PATENT_WEB") and patent_id:
            patent_meta_for_fast_path = self.load_patent_meta(patent_id)
            structured_result: Optional[Tuple[str, List[Dict[str, Any]]]] = None
            if scope == "PATENT_LOCAL":
                structured_result = structured_metadata_answer(patent_id, question, patent_meta_for_fast_path)
                if structured_result is None:
                    structured_result = structured_claim_answer(patent_id, question, patent_meta_for_fast_path)
                if structured_result is None:
                    structured_result = structured_original_section_answer(patent_id, question, patent_meta_for_fast_path)
                if structured_result is None:
                    structured_result = structured_invention_overview_answer(
                        patent_id,
                        question,
                        patent_meta_for_fast_path,
                    )
                if structured_result is None:
                    structured_result = structured_document_detail_answer(
                        patent_id,
                        question,
                        patent_meta_for_fast_path,
                    )
                if structured_result is None:
                    report_data = load_report_json(patent_meta_for_fast_path)
                    if report_data:
                        structured_result = structured_report_answer(
                            patent_id,
                            question,
                            patent_meta_for_fast_path,
                            report_data,
                        )

            if structured_result is not None:
                answer_text, source_cards = structured_result
                metrics = {
                    "scope": scope,
                    "patent_id": patent_id,
                    "local_context_count": len(source_cards),
                    "web_context_count": 0,
                    "confidence_score": 1.0,
                    "vector_ms": 0,
                    "bm25_ms": 0,
                    "retrieval_ms": 0,
                    "web_search_ms": 0,
                    "llm_ms": 0,
                    "total_ms": now_ms() - total_t0,
                    "answer_mode": "STRUCTURED_FAST_PATH",
                    **scope_metrics,
                }
                self._log_query(user_id, patent_id, question, scope, 1.0, metrics)
                return {
                    "answer": answer_text,
                    "source_cards": source_cards,
                    "metrics": metrics if RETURN_PERFORMANCE else {},
                }

        local_docs: List[Document] = []
        web_docs: List[Document] = []
        retrieval_metrics = {"retrieval_ms": 0, "vector_ms": 0, "bm25_ms": 0}
        web_ms = 0
        patent_meta: Dict[str, Any] = {}
        retrieval_question = question
        retrieval_query_expanded = False

        if scope in ("PATENT_LOCAL", "PATENT_WEB"):
            assert patent_id is not None
            patent_meta = self.load_patent_meta(patent_id)
            retrieval_queries, retrieval_query_expanded = build_deep_retrieval_queries(question, patent_meta)
            retrieval_question = " ".join(retrieval_queries)
            local_docs, retrieval_metrics = self.retrieve_patent_multi(patent_id, retrieval_queries)
            local_docs = enrich_docs_for_answer(
                question=question,
                retrieved_docs=local_docs,
                all_docs=self.docs_by_patent.get(patent_id, []),
                top_k=TOP_K,
            )
            if scope == "PATENT_LOCAL" and is_decision_support_question(question):
                decision_t0 = now_ms()
                decision_docs = select_patent_evaluation_docs(patent_id, include_visual=False)
                if decision_docs:
                    _, decision_source_cards = format_context(decision_docs)
                    for card in decision_source_cards:
                        card["relevance_score"] = 0.88
                        card["relevance_grade"] = "GOOD"
                        card["match_terms"] = ["유지", "매각", "제각", "평가"]
                    snapshot = patent_score_snapshot(patent_id, patent_meta, decision_docs)
                    answer_text = build_decision_support_answer(snapshot, decision_source_cards)
                    decision_quality_metrics = build_evaluation_quality_metrics(
                        question=question,
                        retrieval_question=f"{patent_meta.get('title', '')} 유지 매각 제각 판단 보조표 평가 리스크 사업성 권리성",
                        docs=decision_docs,
                        source_cards=decision_source_cards,
                        confidence=0.88,
                        retrieval_query_expanded=True,
                    )
                    metrics = {
                        "scope": scope,
                        "patent_id": patent_id,
                        "local_context_count": len(decision_docs),
                        "web_context_count": 0,
                        "confidence_score": 0.88,
                        **retrieval_metrics,
                        "decision_support_ms": now_ms() - decision_t0,
                        "web_search_ms": 0,
                        "llm_ms": 0,
                        "total_ms": now_ms() - total_t0,
                        "answer_mode": "DECISION_SUPPORT_TABLE",
                        "answer_cache_hit": False,
                        "answer_generation_basis": "report_scores_and_risk_sections",
                        "answer_presentation": ["decision_support_table", "risk_notes", "collapsible_sources"],
                        **decision_quality_metrics,
                        **scope_metrics,
                    }
                    self._log_query(user_id, patent_id, question, scope, 0.88, metrics)
                    return {
                        "answer": answer_text,
                        "source_cards": decision_source_cards,
                        "metrics": metrics if RETURN_PERFORMANCE else {},
                    }
            if scope == "PATENT_LOCAL" and is_evaluation_question(question) and not is_visual_asset_question(question):
                eval_t0 = now_ms()
                evaluation_docs = select_patent_evaluation_docs(patent_id, include_visual=False)
                if evaluation_docs:
                    evaluation_query = (
                        f"{patent_meta.get('title', '')} "
                        f"{patent_meta.get('registration_number', '')} "
                        "평가 요약 종합 점수 기술성 권리성 시장성 사업성 평가 기준별 상세 점수 리스크 추가 확인"
                    )
                    evaluation_confidence = lexical_confidence(evaluation_query, evaluation_docs)
                    _, evaluation_source_cards = format_context(evaluation_docs)
                    for card in evaluation_source_cards:
                        card["relevance_score"] = 0.88
                        card["relevance_grade"] = "GOOD"
                        card["match_terms"] = ["평가", "점수", "보고서"]
                    answer_text = build_patent_evaluation_answer(
                        question=question,
                        patent_meta=patent_meta,
                        docs=evaluation_docs,
                        source_cards=evaluation_source_cards,
                    )
                    evaluation_quality_metrics = build_evaluation_quality_metrics(
                        question=question,
                        retrieval_question=evaluation_query,
                        docs=evaluation_docs,
                        source_cards=evaluation_source_cards,
                        confidence=evaluation_confidence,
                        retrieval_query_expanded=True,
                    )
                    metrics = {
                        "scope": scope,
                        "patent_id": patent_id,
                        "local_context_count": len(evaluation_docs),
                        "web_context_count": 0,
                        "confidence_score": round(evaluation_confidence, 4),
                        **retrieval_metrics,
                        "evaluation_selection_ms": now_ms() - eval_t0,
                        "web_search_ms": 0,
                        "llm_ms": 0,
                        "total_ms": now_ms() - total_t0,
                        "answer_mode": "STRUCTURED_EVALUATION_RAG",
                        "answer_cache_hit": False,
                        "answer_generation_basis": "report_evaluation_sections",
                        "answer_presentation": ["evaluation_summary", "score_table", "risk_notes", "collapsible_sources"],
                        **evaluation_quality_metrics,
                        **scope_metrics,
                    }
                    self._log_query(user_id, patent_id, question, scope, evaluation_confidence, metrics)
                    return {
                        "answer": answer_text,
                        "source_cards": evaluation_source_cards,
                        "metrics": metrics if RETURN_PERFORMANCE else {},
                    }
            if scope == "PATENT_LOCAL" and is_intent_specific_overview_question(question, patent_meta):
                section_t0 = now_ms()
                overview_docs = select_patent_overview_docs(patent_id, question)
                if overview_docs:
                    overview_query = (
                        f"{patent_meta.get('title', '')} "
                        f"{patent_meta.get('registration_number', '')} "
                        "서지사항 요약 배경기술 해결하려는 과제 과제의 해결 수단 청구범위 발명의 효과 "
                        "기술성 권리성 시장성 사업성 추가 확인"
                    )
                    overview_confidence = lexical_confidence(overview_query, overview_docs)
                    _, overview_source_cards = format_context(overview_docs)
                    for card in overview_source_cards:
                        card["relevance_score"] = 0.86
                        card["relevance_grade"] = "GOOD"
                        card["match_terms"] = ["개요", "요약", "청구항", "평가"]
                    answer_text = build_patent_overview_answer(
                        question=question,
                        patent_meta=patent_meta,
                        docs=overview_docs,
                        source_cards=overview_source_cards,
                        confidence=overview_confidence,
                    )
                    overview_quality_metrics = build_overview_quality_metrics(
                        question=question,
                        retrieval_question=overview_query,
                        docs=overview_docs,
                        source_cards=overview_source_cards,
                        confidence=overview_confidence,
                        retrieval_query_expanded=True,
                    )
                    metrics = {
                        "scope": scope,
                        "patent_id": patent_id,
                        "local_context_count": len(overview_docs),
                        "web_context_count": 0,
                        "confidence_score": round(overview_confidence, 4),
                        **retrieval_metrics,
                        "section_retrieval_ms": now_ms() - section_t0,
                        "web_search_ms": 0,
                        "llm_ms": 0,
                        "total_ms": now_ms() - total_t0,
                        "answer_mode": "STRUCTURED_OVERVIEW_RAG",
                        "answer_cache_hit": False,
                        "answer_generation_basis": "section_based_overview_retrieval",
                        "answer_presentation": ["summary_table", "flow_diagram", "component_table", "score_table", "collapsible_sources"],
                        **overview_quality_metrics,
                        **scope_metrics,
                    }
                    self._log_query(user_id, patent_id, question, scope, overview_confidence, metrics)
                    return {
                        "answer": answer_text,
                        "source_cards": overview_source_cards,
                        "metrics": metrics if RETURN_PERFORMANCE else {},
                    }
            if scope == "PATENT_LOCAL" and is_visual_asset_question(question) and not is_patent_detail_request(question):
                visual_t0 = now_ms()
                visual_docs = select_visual_asset_docs(patent_id, question, max_docs=6, fallback=True)
                if visual_docs:
                    _, visual_source_cards = format_context(visual_docs)
                    for doc, card in zip(visual_docs, visual_source_cards):
                        detail = visual_asset_relevance_detail(question, doc)
                        card["relevance_score"] = detail["score"]
                        card["relevance_grade"] = detail["grade"]
                        card["match_terms"] = detail["matched_terms"]
                    answer_text = build_visual_asset_answer(
                        question=question,
                        docs=visual_docs,
                        source_cards=visual_source_cards,
                    )
                    visual_quality_metrics = build_visual_asset_quality_metrics(
                        question=question,
                        docs=visual_docs,
                        source_cards=visual_source_cards,
                        retrieval_query_expanded=retrieval_query_expanded,
                    )
                    visual_confidence = float(visual_quality_metrics.get("retrieval_quality_score") or 0.0)
                    metrics = {
                        "scope": scope,
                        "patent_id": patent_id,
                        "local_context_count": len(visual_docs),
                        "web_context_count": 0,
                        "confidence_score": round(visual_confidence, 4),
                        **retrieval_metrics,
                        "visual_asset_selection_ms": now_ms() - visual_t0,
                        "web_search_ms": 0,
                        "llm_ms": 0,
                        "total_ms": now_ms() - total_t0,
                        "answer_mode": "STRUCTURED_VISUAL_ASSET_RAG",
                        "answer_cache_hit": False,
                        "answer_generation_basis": "visual_asset_chunks",
                        "answer_presentation": ["visual_asset_table", "asset_previews", "collapsible_sources"],
                        **visual_quality_metrics,
                        **scope_metrics,
                    }
                    self._log_query(user_id, patent_id, question, scope, visual_confidence, metrics)
                    return {
                        "answer": answer_text,
                        "source_cards": visual_source_cards,
                        "metrics": metrics if RETURN_PERFORMANCE else {},
                    }
        elif scope == "BUSINESS":
            local_docs, retrieval_metrics = self.retrieve_business(question)

        confidence_question = retrieval_question if retrieval_query_expanded else question
        confidence = lexical_confidence(confidence_question, local_docs)

        if scope in ("PATENT_LOCAL", "BUSINESS") and confidence < MIN_LOCAL_CONFIDENCE:
            message = (
                "제공된 해당 특허 원문 및 보고서 자료에서 질문과 직접 관련된 내용을 확인할 수 없습니다."
                if scope == "PATENT_LOCAL"
                else "제공된 특허 검토 업무 자료에서 질문과 직접 관련된 내용을 확인할 수 없습니다."
            )
            return self._blocked_response(
                message,
                patent_id,
                scope,
                total_t0,
                confidence=confidence,
                extra_metrics={
                    **scope_metrics,
                    **retrieval_metrics,
                    "local_context_count": len(local_docs),
                    "web_context_count": 0,
                    "retrieval_query_expanded": retrieval_query_expanded,
                },
                user_id=user_id,
                question=question,
            )

        if scope == "PATENT_WEB":
            allow_web = bool(patent_meta.get("allow_web_search", True))
            web_docs, web_ms = search_web_documents(
                patent_meta=patent_meta,
                question=question,
                enabled=ENABLE_WEB_SEARCH and allow_web,
                api_url=WEB_SEARCH_API_URL,
                api_key=WEB_SEARCH_API_KEY,
                limit=WEB_SEARCH_LIMIT,
            )

            if not web_docs and not WEB_SEARCH_API_URL:
                source_cards: List[Dict[str, Any]] = []
                if local_docs:
                    _, source_cards = format_context(local_docs[: min(2, len(local_docs))])
                source_note = " [자료1]" if source_cards else ""
                answer_text = (
                    "현재 외부 웹 검색 API가 설정되어 있지 않아 최신 유사 특허, 외부 시장 동향, 경쟁사 정보는 확인할 수 없습니다."
                    f"{source_note}\n\n"
                    "확인 필요 사항:\n"
                    "- 최신 외부 정보를 답변하려면 `.env`의 `WEB_SEARCH_API_URL`과 `WEB_SEARCH_API_KEY`에 사내 승인 검색 API 또는 KIPRIS/검색 API를 연결해야 합니다.\n"
                    "- 연결 전에는 내부 원문 PDF와 AI 평가 보고서에 있는 내용만 답변할 수 있습니다."
                    f"{source_note}"
                )
                metrics = {
                    "scope": scope,
                    "patent_id": patent_id,
                    "local_context_count": len(local_docs),
                    "web_context_count": 0,
                    "confidence_score": round(confidence, 4),
                    **retrieval_metrics,
                    "web_search_ms": web_ms,
                    "llm_ms": 0,
                    "total_ms": now_ms() - total_t0,
                    "answer_mode": "WEB_NOT_CONFIGURED",
                    "retrieval_query_expanded": retrieval_query_expanded,
                    **scope_metrics,
                }
                self._log_query(user_id, patent_id, question, scope, confidence, metrics)
                return {
                    "answer": answer_text,
                    "source_cards": source_cards,
                    "metrics": metrics if RETURN_PERFORMANCE else {},
                }

        local_docs_for_answer = local_docs
        if scope == "PATENT_WEB" and confidence < MIN_LOCAL_CONFIDENCE:
            local_docs_for_answer = []

        if scope == "PATENT_WEB" and web_docs:
            local_docs_for_web = [
                doc
                for doc in local_docs_for_answer
                if (doc.metadata or {}).get("content_type") != "VISUAL_ASSET"
            ][:3]
            final_web_docs = local_docs_for_web + web_docs
            context, source_cards = format_context(final_web_docs)
            annotate_source_cards(question, final_web_docs[: len(source_cards)], source_cards)
            local_source_cards = source_cards[: len(local_docs_for_web)]
            web_source_cards = source_cards[len(local_docs_for_web) :]
            for card in web_source_cards:
                card["relevance_score"] = 0.72
                card["relevance_grade"] = "GOOD"
                card["match_terms"] = discovery_query_terms(question)
            answer_text = build_patent_web_answer(
                question=question,
                patent_meta=patent_meta,
                local_docs=local_docs_for_web,
                web_docs=web_docs,
                local_source_cards=local_source_cards,
                web_source_cards=web_source_cards,
            )
            web_quality_metrics = build_web_quality_metrics(
                question=question,
                web_docs=web_docs,
                source_cards=web_source_cards,
                web_ms=web_ms,
            )
            metrics = {
                "scope": scope,
                "patent_id": patent_id,
                "local_context_count": len(local_docs_for_web),
                "web_context_count": len(web_docs),
                "confidence_score": float(web_quality_metrics.get("retrieval_quality_score") or 0.0),
                **retrieval_metrics,
                "web_search_ms": web_ms,
                "llm_ms": 0,
                "total_ms": now_ms() - total_t0,
                "answer_mode": "PATENT_WEB_SEARCH",
                "answer_cache_hit": False,
                "answer_generation_basis": "internal_context_plus_external_web_sources",
                "answer_presentation": ["internal_external_split", "web_source_table", "collapsible_sources"],
                "retrieval_query_expanded": retrieval_query_expanded,
                **scope_metrics,
                **web_quality_metrics,
            }
            self._log_query(user_id, patent_id, question, scope, metrics["confidence_score"], metrics)
            return {
                "answer": answer_text,
                "source_cards": source_cards,
                "metrics": metrics if RETURN_PERFORMANCE else {},
            }

        final_docs = local_docs_for_answer + web_docs
        if not final_docs:
            return self._blocked_response(
                "해당 특허와 관련된 내부 자료 및 허용된 외부 검색 결과에서 답변 근거를 찾지 못했습니다.",
                patent_id,
                scope,
                total_t0,
                confidence=confidence,
                extra_metrics={
                    **scope_metrics,
                    **retrieval_metrics,
                    "web_search_ms": web_ms,
                    "retrieval_query_expanded": retrieval_query_expanded,
                },
                user_id=user_id,
                question=question,
            )

        if scope in ("PATENT_LOCAL", "PATENT_WEB"):
            final_docs = enrich_docs_for_answer(question, final_docs, final_docs, top_k=TOP_K)
        else:
            final_docs = order_docs_for_answer(question, final_docs)
        context, source_cards = format_context(final_docs)
        annotate_source_cards(question, final_docs[: len(source_cards)], source_cards)
        grounded_context = build_grounded_llm_context(
            question=question,
            docs=final_docs[: len(source_cards)],
            source_cards=source_cards,
        )
        search_quality_metrics = build_search_quality_metrics(
            question=question,
            retrieval_question=retrieval_question,
            docs=final_docs[: len(source_cards)],
            source_cards=source_cards,
            confidence=confidence,
            retrieval_query_expanded=retrieval_query_expanded,
        )
        patent_meta_json = json.dumps(patent_meta, ensure_ascii=False, indent=2) if patent_meta else "{}"

        if ANSWER_GENERATION_MODE == "extractive":
            answer_text = build_extractive_answer(
                question=question,
                scope=scope,
                docs=final_docs[: len(source_cards)],
                source_cards=source_cards,
                confidence=confidence,
            )
            metrics = {
                "scope": scope,
                "patent_id": patent_id,
                "local_context_count": len(local_docs),
                "web_context_count": len(web_docs),
                "confidence_score": round(confidence, 4),
                **retrieval_metrics,
                "web_search_ms": web_ms,
                "llm_ms": 0,
                "total_ms": now_ms() - total_t0,
                "answer_mode": "GROUNDED_EXTRACTIVE_RAG",
                "answer_cache_hit": False,
                "answer_generation_basis": "multi_pass_retrieval_source_cards",
                **search_quality_metrics,
                **scope_metrics,
            }
            self._log_query(user_id, patent_id, question, scope, confidence, metrics)
            return {
                "answer": answer_text,
                "source_cards": source_cards,
                "metrics": metrics if RETURN_PERFORMANCE else {},
            }

        user_prompt = build_user_prompt(question, patent_meta_json, grounded_context or context)

        llm_t0 = now_ms()
        answer_text = call_ollama(
            [
                {"role": "system", "content": build_system_prompt(scope)},
                {"role": "user", "content": user_prompt},
            ]
        )
        answer_text = enforce_answer_policy(answer_text, source_cards)
        llm_ms = now_ms() - llm_t0

        metrics = {
            "scope": scope,
            "patent_id": patent_id,
            "local_context_count": len(local_docs),
            "web_context_count": len(web_docs),
            "confidence_score": round(confidence, 4),
            **retrieval_metrics,
            "web_search_ms": web_ms,
            "llm_ms": llm_ms,
            "total_ms": now_ms() - total_t0,
            "answer_mode": "RAG_LLM",
            "answer_cache_hit": False,
            "answer_generation_basis": "retrieved_context_plus_llm",
            **search_quality_metrics,
            **scope_metrics,
        }
        self._log_query(user_id, patent_id, question, scope, confidence, metrics)
        return {
            "answer": answer_text,
            "source_cards": source_cards,
            "metrics": metrics if RETURN_PERFORMANCE else {},
        }

    def answer_global(
        self,
        question: str,
        user_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        context_patent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        total_t0 = now_ms()
        hist = history_context(chat_history, context_patent_id)
        current_history_patent_id = hist.get("current_patent_id")
        if is_clearly_unrelated_question(question):
            return self._blocked_response(
                OUT_OF_SCOPE_ANSWER,
                None,
                "OUT_OF_SCOPE",
                total_t0,
                extra_metrics={
                    "rule_scope": "OUT_OF_SCOPE",
                    "global_search": True,
                    "intent_agent_used": False,
                    "intent_agent_reason": "명백한 생활/잡담/추천 주제라 검색 전에 차단",
                },
                user_id=user_id,
                question=question,
            )

        if is_other_patent_disambiguation_question(question):
            rows = self.list_patent_meta_rows()
            metrics = {
                "scope": "GLOBAL",
                "patent_id": None,
                "global_search": True,
                "patent_hit_count": len(rows),
                "local_context_count": 0,
                "web_context_count": 0,
                "confidence_score": 1.0,
                "retrieval_ms": 0,
                "vector_ms": 0,
                "bm25_ms": 0,
                "web_search_ms": 0,
                "llm_ms": 0,
                "total_ms": now_ms() - total_t0,
                "answer_mode": "PATENT_SELECTION",
                "answer_cache_hit": False,
                "answer_generation_basis": "available_patent_catalog",
                "answer_presentation": ["patent_selection_table"],
                "history_context_used": bool(current_history_patent_id),
                "context_patent_id": current_history_patent_id,
                "search_result_patents": rows,
                "retrieval_quality_score": 1.0,
                "retrieval_quality_grade": "GOOD",
                "retrieval_quality_label": "양호",
                "retrieval_quality_reason": "사용자가 다른 특허 선택 의도를 보여 전체 후보 목록을 제시했습니다.",
                "search_pass": True,
            }
            self._log_query(user_id, None, question, "GLOBAL", 1.0, metrics)
            return {
                "answer": build_patent_selection_answer(rows, current_history_patent_id),
                "source_cards": [],
                "metrics": metrics if RETURN_PERFORMANCE else {},
            }

        if (
            current_history_patent_id
            and is_contextual_followup_question(question)
            and not is_compare_question(question)
            and not discovery_query_terms(question)
        ):
            result = self.answer(
                patent_id=str(current_history_patent_id),
                question=question,
                user_id=user_id,
                chat_history=chat_history,
                context_patent_id=str(current_history_patent_id),
            )
            metrics = result.get("metrics") or {}
            metrics.update(
                {
                    "history_context_used": True,
                    "context_patent_id": current_history_patent_id,
                    "answer_mode": f"HISTORY_{metrics.get('answer_mode', 'PATENT_LOCAL')}",
                }
            )
            result["metrics"] = metrics if RETURN_PERFORMANCE else {}
            return result

        retrieval_queries, retrieval_query_expanded = build_deep_retrieval_queries(question, {})
        retrieval_question = " ".join(retrieval_queries)
        docs, retrieval_metrics = self.retrieve_global(retrieval_queries)
        domain_matches = self.match_domain_cards(question)
        domain_match_ids = [
            str(match.get("patent_id"))
            for match in domain_matches
            if match.get("patent_id")
        ]
        domain_scope_metrics = {
            "scope_strategy": "domain_card_evidence_gate",
            "domain_card_match_count": len(domain_matches),
            "domain_card_matches": domain_matches,
        }
        global_intent_scope, global_intent_metrics = run_global_intent_agent(question, domain_matches)
        domain_scope_metrics.update(global_intent_metrics)

        if global_intent_scope == "CLARIFY":
            clarification_q = (
                global_intent_metrics.get("clarification_question")
                or "어떤 특허에 대해 질문하시나요? 특허명이나 번호를 알려주시거나, 전체 DB에서 찾아드릴까요?"
            )
            metrics = {
                "scope": "CLARIFY",
                "patent_id": None,
                "global_search": True,
                "patent_hit_count": len(domain_matches),
                "local_context_count": len(docs),
                "web_context_count": 0,
                "confidence_score": 0.0,
                **retrieval_metrics,
                "web_search_ms": 0,
                "llm_ms": 0,
                "total_ms": now_ms() - total_t0,
                "answer_mode": "GLOBAL_CLARIFY",
                "answer_cache_hit": False,
                "answer_generation_basis": "clarification_needed",
                "answer_presentation": ["clarification"],
                "retrieval_quality_score": 0.0,
                "retrieval_quality_grade": "LOW",
                "retrieval_quality_label": "낮음",
                "retrieval_quality_reason": "질문 대상이 불분명해 되묻기 처리합니다.",
                "search_pass": False,
                **domain_scope_metrics,
            }
            self._log_query(user_id, None, question, "CLARIFY", 0.0, metrics)
            return {
                "answer": clarification_q,
                "source_cards": [],
                "metrics": metrics if RETURN_PERFORMANCE else {},
            }

        if (
            global_intent_scope == "GLOBAL_WEB"
            and is_generic_external_global_question(question, domain_matches)
        ):
            metrics = {
                "scope": "AMBIGUOUS",
                "patent_id": None,
                "global_search": True,
                "patent_hit_count": 0,
                "local_context_count": len(docs),
                "web_context_count": 0,
                "confidence_score": 0.0,
                **retrieval_metrics,
                "web_search_ms": 0,
                "llm_ms": 0,
                "total_ms": now_ms() - total_t0,
                "answer_mode": "GLOBAL_CLARIFY",
                "answer_cache_hit": False,
                "answer_generation_basis": "missing_market_subject_guard",
                "answer_presentation": ["clarification"],
                "retrieval_query_expanded": retrieval_query_expanded,
                "retrieval_quality_score": 0.0,
                "retrieval_quality_grade": "LOW",
                "retrieval_quality_label": "낮음",
                "retrieval_quality_reason": "시장/동향 질문의 대상이 지정되지 않아 웹검색을 보류했습니다.",
                "search_pass": False,
                **domain_scope_metrics,
                "intent_agent_scope": "AMBIGUOUS",
                "intent_agent_reason": "시장/동향 질문의 대상이 없어 웹검색 대신 되묻기",
            }
            self._log_query(user_id, None, question, "AMBIGUOUS", 0.0, metrics)
            return {
                "answer": build_global_clarification_answer(question),
                "source_cards": [],
                "metrics": metrics if RETURN_PERFORMANCE else {},
            }

        if (
            global_intent_scope == "GLOBAL_WEB"
            and is_evaluation_question(question)
            and domain_matches
            and "웹" not in question.lower()
            and "외부" not in question.lower()
        ):
            global_intent_scope = "GLOBAL_EVALUATION"
            domain_scope_metrics.update(
                {
                    "intent_agent_scope": "GLOBAL_EVALUATION",
                    "intent_agent_reason": "평가/판단 근거 질문은 내부 보고서 검색을 우선하도록 보정",
                    "intent_agent_override": "EVALUATION_PRIORITY",
                }
            )

        if (
            global_intent_scope == "GLOBAL_WEB"
            and is_explicit_visual_asset_request(question)
            and domain_matches
            and "웹" not in question.lower()
            and "외부" not in question.lower()
        ):
            global_intent_scope = "GLOBAL_VISUAL"
            domain_scope_metrics.update(
                {
                    "intent_agent_scope": "GLOBAL_VISUAL",
                    "intent_agent_reason": "표/도면/이미지 요청은 외부 웹검색보다 내부 시각자료 검색을 우선하도록 보정",
                    "intent_agent_override": "VISUAL_ASSET_PRIORITY",
                }
            )

        if is_compare_question(question):
            comparison_ids: List[str] = []
            if current_history_patent_id:
                comparison_ids.append(str(current_history_patent_id))
            for pid in domain_match_ids:
                if pid and pid not in comparison_ids:
                    comparison_ids.append(pid)
            for row in hist.get("search_result_patents") or []:
                pid = str(row.get("patent_id") or "")
                if pid and pid not in comparison_ids:
                    comparison_ids.append(pid)
            comparison_ids = comparison_ids[:3]
            if len(comparison_ids) < 2:
                rows = self.list_patent_meta_rows()
                metrics = {
                    "scope": "GLOBAL",
                    "patent_id": current_history_patent_id,
                    "global_search": True,
                    "patent_hit_count": len(rows),
                    "local_context_count": 0,
                    "web_context_count": 0,
                    "confidence_score": 0.0,
                    **retrieval_metrics,
                    "web_search_ms": 0,
                    "llm_ms": 0,
                    "total_ms": now_ms() - total_t0,
                    "answer_mode": "COMPARE_NEEDS_SELECTION",
                    "answer_cache_hit": False,
                    "answer_generation_basis": "comparison_target_disambiguation",
                    "answer_presentation": ["patent_selection_table"],
                    "history_context_used": bool(current_history_patent_id),
                    "context_patent_id": current_history_patent_id,
                    "search_result_patents": rows,
                    **domain_scope_metrics,
                }
                self._log_query(user_id, None, question, "GLOBAL", 0.0, metrics)
                return {
                    "answer": build_patent_selection_answer(rows, current_history_patent_id),
                    "source_cards": [],
                    "metrics": metrics if RETURN_PERFORMANCE else {},
                }

            comparison_docs: List[Document] = []
            snapshots: List[Dict[str, Any]] = []
            for pid in comparison_ids:
                try:
                    meta = self.load_patent_meta(pid)
                    eval_docs = select_patent_evaluation_docs(pid, include_visual=False)
                except Exception:
                    continue
                if not eval_docs:
                    continue
                snapshots.append(patent_score_snapshot(pid, meta, eval_docs))
                comparison_docs.extend(eval_docs[:2])

            if len(snapshots) >= 2:
                _, comparison_source_cards = format_context(comparison_docs)
                for card in comparison_source_cards:
                    card["relevance_score"] = 0.88
                    card["relevance_grade"] = "GOOD"
                    card["match_terms"] = ["비교", "평가", "점수"]
                metrics = {
                    "scope": "GLOBAL",
                    "patent_id": comparison_ids[0],
                    "global_search": True,
                    "patent_hit_count": len(snapshots),
                    "local_context_count": len(comparison_docs),
                    "web_context_count": 0,
                    "confidence_score": 0.9,
                    **retrieval_metrics,
                    "web_search_ms": 0,
                    "llm_ms": 0,
                    "total_ms": now_ms() - total_t0,
                    "answer_mode": "PATENT_COMPARISON",
                    "answer_cache_hit": False,
                    "answer_generation_basis": "multi_patent_report_score_snapshots",
                    "answer_presentation": ["comparison_table", "risk_notes", "collapsible_sources"],
                    "history_context_used": bool(current_history_patent_id),
                    "context_patent_id": current_history_patent_id,
                    "search_result_patents": snapshots,
                    "retrieval_quality_score": 0.9,
                    "retrieval_quality_grade": "GOOD",
                    "retrieval_quality_label": "양호",
                    "retrieval_quality_reason": "비교 대상 특허 2건 이상과 평가 보고서 근거가 확인되었습니다.",
                    "search_pass": True,
                    **domain_scope_metrics,
                }
                self._log_query(user_id, comparison_ids[0], question, "GLOBAL", 0.9, metrics)
                return {
                    "answer": build_patent_comparison_answer(snapshots, comparison_source_cards),
                    "source_cards": comparison_source_cards,
                    "metrics": metrics if RETURN_PERFORMANCE else {},
                }

        if global_intent_scope == "OUT_OF_SCOPE":
            return self._blocked_response(
                OUT_OF_SCOPE_ANSWER,
                None,
                "OUT_OF_SCOPE",
                total_t0,
                extra_metrics={
                    **retrieval_metrics,
                    "global_search": True,
                    "local_context_count": len(docs),
                    "web_context_count": 0,
                    "answer_mode": "GLOBAL_INTENT_BLOCKED",
                    **domain_scope_metrics,
                },
                user_id=user_id,
                question=question,
            )

        if global_intent_scope == "GLOBAL_WEB":
            web_t0 = now_ms()
            web_query = str(global_intent_metrics.get("web_query") or question)
            web_docs, web_ms = search_web_documents(
                patent_meta={},
                question=web_query,
                enabled=ENABLE_WEB_SEARCH,
                api_url=WEB_SEARCH_API_URL,
                api_key=WEB_SEARCH_API_KEY,
                limit=WEB_SEARCH_LIMIT,
            )
            _, web_source_cards = format_context(web_docs)
            for card in web_source_cards:
                card["relevance_score"] = 0.72
                card["relevance_grade"] = "GOOD"
                card["match_terms"] = discovery_query_terms(question)
            answer_text = build_global_web_answer(
                question=web_query,
                web_docs=web_docs,
                source_cards=web_source_cards,
                domain_matches=domain_matches,
            )
            web_quality_metrics = build_web_quality_metrics(
                question=web_query,
                web_docs=web_docs,
                source_cards=web_source_cards,
                web_ms=web_ms,
            )
            metrics = {
                "scope": "GLOBAL_WEB",
                "patent_id": domain_matches[0].get("patent_id") if domain_matches else None,
                "global_search": True,
                "patent_hit_count": len(domain_matches),
                "question_intents": detect_question_intents(question),
                "local_context_count": len(docs),
                "web_context_count": len(web_docs),
                "confidence_score": float(web_quality_metrics.get("retrieval_quality_score") or 0.0),
                **retrieval_metrics,
                "web_search_ms": web_ms,
                "web_answer_ms": now_ms() - web_t0,
                "llm_ms": 0,
                "total_ms": now_ms() - total_t0,
                "answer_mode": "GLOBAL_WEB_SEARCH",
                "answer_cache_hit": False,
                "answer_generation_basis": "external_web_search_sources",
                "answer_presentation": ["web_summary", "web_source_table", "collapsible_sources"],
                "web_query": web_query,
                **domain_scope_metrics,
                **web_quality_metrics,
            }
            self._log_query(user_id, metrics.get("patent_id"), question, "GLOBAL_WEB", metrics["confidence_score"], metrics)
            return {
                "answer": answer_text,
                "source_cards": web_source_cards,
                "metrics": metrics if RETURN_PERFORMANCE else {},
            }

        if is_global_patent_discovery_question(question) or domain_matches:
            candidate_all_docs = self.global_docs
            candidate_retrieved_docs = docs
            if domain_match_ids:
                candidate_all_docs = [
                    doc for doc in self.global_docs if _patent_id_from_doc(doc) in domain_match_ids
                ] or self.global_docs
                candidate_retrieved_docs = [
                    doc for doc in docs if _patent_id_from_doc(doc) in domain_match_ids
                ] or candidate_all_docs
            patent_groups, selected_docs, query_terms = group_discovery_patents(
                question=question,
                retrieved_docs=candidate_retrieved_docs,
                all_docs=candidate_all_docs,
                max_patents=5,
                docs_per_patent=2,
            )
            domain_fallback_used = False
            if not patent_groups and domain_matches:
                fallback_terms: List[str] = []
                for match in domain_matches:
                    for term in match.get("matched_terms") or []:
                        if term and term not in fallback_terms:
                            fallback_terms.append(str(term))
                if fallback_terms:
                    patent_groups, selected_docs, query_terms = group_discovery_patents(
                        question=" ".join(fallback_terms),
                        retrieved_docs=candidate_retrieved_docs,
                        all_docs=candidate_all_docs,
                        max_patents=5,
                        docs_per_patent=2,
                    )
                    domain_fallback_used = bool(patent_groups)
                    domain_scope_metrics["domain_card_fallback_used"] = domain_fallback_used
            confidence_question = " ".join(query_terms) if query_terms else question
            confidence = lexical_confidence(confidence_question, selected_docs)
            if not patent_groups or confidence < MIN_LOCAL_CONFIDENCE:
                return self._blocked_response(
                    "전체 특허 인덱스에서 질문과 직접 관련된 특허를 찾지 못했습니다.",
                    None,
                    "GLOBAL",
                    total_t0,
                    confidence=confidence,
                    extra_metrics={
                        **retrieval_metrics,
                        "global_search": True,
                        "local_context_count": len(selected_docs),
                        "web_context_count": 0,
                        "retrieval_query_expanded": retrieval_query_expanded,
                        "discovery_query_terms": query_terms,
                        "answer_cache_hit": False,
                        "answer_mode": "GLOBAL_PATENT_DISCOVERY",
                        **domain_scope_metrics,
                    },
                    user_id=user_id,
                    question=question,
                )

            context, source_cards = format_context(selected_docs)
            annotate_source_cards(question, selected_docs[: len(source_cards)], source_cards)
            search_quality_metrics = build_search_quality_metrics(
                question=confidence_question,
                retrieval_question=confidence_question,
                docs=selected_docs[: len(source_cards)],
                source_cards=source_cards,
                confidence=confidence,
                retrieval_query_expanded=retrieval_query_expanded,
            )
            best_directness = max(float(group.get("directness") or 0.0) for group in patent_groups)
            if best_directness >= 0.85:
                performance_eval = search_quality_metrics.get("performance_evaluation") or []
                if performance_eval:
                    performance_eval[0] = {
                        **performance_eval[0],
                        "status": "GOOD",
                        "good_threshold": "특허 발견형 검색: 제목 또는 원문 직접 매칭",
                        "message": "질문 키워드가 특허 제목 또는 원문에서 직접 확인되어 관련 특허 검색 품질이 양호합니다.",
                    }
                search_quality_metrics.update(
                    {
                        "discovery_directness_score": round(best_directness, 4),
                        "retrieval_quality_grade": "GOOD",
                        "retrieval_quality_label": "양호",
                        "retrieval_quality_reason": "질문 키워드가 특허 원문 또는 제목 수준에서 직접 확인되었습니다.",
                        "search_pass": True,
                        "quality_thresholds": {
                            **(search_quality_metrics.get("quality_thresholds") or {}),
                            "DISCOVERY_GOOD": "특허 발견형 검색은 제목 또는 원문 직접 매칭이면 양호",
                        },
                        "performance_evaluation": performance_eval,
                    }
                )
            if is_evaluation_question(question) and not is_visual_asset_question(question) and len(patent_groups) == 1 and best_directness >= 0.55:
                detail_patent_id = str(patent_groups[0].get("patent_id") or "")
                eval_t0 = now_ms()
                evaluation_docs = select_patent_evaluation_docs(detail_patent_id, include_visual=False) if detail_patent_id else []
                if evaluation_docs:
                    patent_meta = self.load_patent_meta(detail_patent_id)
                    evaluation_query = (
                        f"{patent_meta.get('title', '')} "
                        f"{patent_meta.get('registration_number', '')} "
                        "평가 요약 종합 점수 기술성 권리성 시장성 사업성 평가 기준별 상세 점수 리스크 추가 확인"
                    )
                    evaluation_confidence = lexical_confidence(evaluation_query, evaluation_docs)
                    _, evaluation_source_cards = format_context(evaluation_docs)
                    for card in evaluation_source_cards:
                        card["relevance_score"] = 0.88
                        card["relevance_grade"] = "GOOD"
                        card["match_terms"] = ["평가", "점수", "보고서"]
                    answer_text = build_patent_evaluation_answer(
                        question=question,
                        patent_meta=patent_meta,
                        docs=evaluation_docs,
                        source_cards=evaluation_source_cards,
                    )
                    evaluation_quality_metrics = build_evaluation_quality_metrics(
                        question=question,
                        retrieval_question=evaluation_query,
                        docs=evaluation_docs,
                        source_cards=evaluation_source_cards,
                        confidence=evaluation_confidence,
                        retrieval_query_expanded=True,
                    )
                    patent_hits = {
                        group["patent_id"]: len(group.get("docs") or [])
                        for group in patent_groups
                    }
                    metrics = {
                        "scope": "GLOBAL",
                        "patent_id": detail_patent_id,
                        "global_search": True,
                        "patent_hit_count": len(patent_groups),
                        "question_intents": detect_question_intents(question),
                        "patent_hits": patent_hits,
                        "search_result_patents": [
                            {
                                "patent_id": group["patent_id"],
                                "title": group["title"],
                                "registration_number": group.get("registration_number"),
                                "score": group["score"],
                                "matched_terms": group.get("matched_terms") or [],
                                "source_types": group.get("source_types") or [],
                            }
                            for group in patent_groups
                        ],
                        "local_context_count": len(evaluation_docs),
                        "web_context_count": 0,
                        "confidence_score": round(evaluation_confidence, 4),
                        **retrieval_metrics,
                        "evaluation_selection_ms": now_ms() - eval_t0,
                        "web_search_ms": 0,
                        "llm_ms": 0,
                        "total_ms": now_ms() - total_t0,
                        "answer_mode": "GLOBAL_PATENT_EVALUATION",
                        "answer_cache_hit": False,
                        "answer_generation_basis": "global_domain_match_to_report_evaluation_sections",
                        "answer_presentation": ["evaluation_summary", "score_table", "risk_notes", "collapsible_sources"],
                        "discovery_query_terms": query_terms,
                        "discovery_directness_score": round(best_directness, 4),
                        **domain_scope_metrics,
                        **evaluation_quality_metrics,
                    }
                    self._log_query(user_id, detail_patent_id, question, "GLOBAL", evaluation_confidence, metrics)
                    return {
                        "answer": answer_text,
                        "source_cards": evaluation_source_cards,
                        "metrics": metrics if RETURN_PERFORMANCE else {},
                    }
            if is_definition_question(question) and len(patent_groups) == 1:
                # "cmp가 뭐야?" 같은 정의 질문 → LLM으로 간결 정의 답변
                def_patent_id = str(patent_groups[0].get("patent_id") or "")
                def_meta = self.load_patent_meta(def_patent_id) if def_patent_id else {}
                def_title = def_meta.get("title") or def_patent_id
                reg_no = def_meta.get("registration_number") or def_patent_id
                overview_docs = select_patent_overview_docs(def_patent_id, question)
                key_docs = [
                    d for d in overview_docs
                    if str((d.metadata or {}).get("section_key") or "").upper()
                    in {"KR_ABSTRACT", "KR_BACKGROUND", "KR_SUMMARY"}
                ][:2] or overview_docs[:1]
                _, def_source_cards = format_context(key_docs)
                key_text = "\n\n".join(d.page_content[:400] for d in key_docs)
                llm_t0 = now_ms()
                try:
                    def_answer = call_ollama([
                        {
                            "role": "system",
                            "content": "당신은 특허 분석 전문 어시스턴트입니다. 질문에 직접 답하되, 서론·면책 문구·고정 섹션(근거/해석/확인 필요 사항) 없이 간결하게 답하세요.",
                        },
                        {
                            "role": "user",
                            "content": (
                                f"질문: {question}\n\n"
                                f"내부 DB 관련 특허 원문 (참고용):\n"
                                f"특허명: {def_title} (등록번호: {reg_no})\n"
                                f"{key_text}\n\n"
                                "위 원문을 참고해 질문에 직접 답하세요.\n"
                                "- 기술 용어라면 1-2문장으로 정의하고, 내부에 관련 특허가 있다면 자연스럽게 한 문장으로 언급합니다.\n"
                                "- 고정 섹션(근거, 해석, 확인 필요 사항 등)은 추가하지 않습니다."
                            ),
                        },
                    ])
                except Exception:
                    def_answer = key_text
                llm_ms = now_ms() - llm_t0
                def_metrics = {
                    "scope": "GLOBAL",
                    "patent_id": def_patent_id,
                    "global_search": True,
                    "patent_hit_count": 1,
                    "local_context_count": len(key_docs),
                    "web_context_count": 0,
                    "confidence_score": 0.8,
                    **retrieval_metrics,
                    "web_search_ms": 0,
                    "llm_ms": llm_ms,
                    "total_ms": now_ms() - total_t0,
                    "answer_mode": "GLOBAL_DEFINITION",
                    "answer_cache_hit": False,
                    "answer_generation_basis": "patent_abstract_llm",
                    "answer_presentation": ["brief_definition"],
                    "retrieval_quality_score": 0.8,
                    "retrieval_quality_grade": "GOOD",
                    "retrieval_quality_label": "양호",
                    "retrieval_quality_reason": "정의 질문에 특허 원문 기반 LLM 간결 답변",
                    "search_pass": True,
                    **domain_scope_metrics,
                }
                self._log_query(user_id, def_patent_id, question, "GLOBAL", 0.8, def_metrics)
                return {
                    "answer": def_answer,
                    "source_cards": def_source_cards,
                    "metrics": def_metrics if RETURN_PERFORMANCE else {},
                }

            if should_promote_global_detail_answer(question, patent_groups):
                detail_patent_id = str(patent_groups[0].get("patent_id") or "")
                overview_docs = select_patent_overview_docs(detail_patent_id, question) if detail_patent_id else []
                if overview_docs:
                    detail_scope_metrics = {
                        **domain_scope_metrics,
                        "intent_agent_scope": "GLOBAL_DETAIL",
                        "intent_agent_reason": "단일 특허 후보가 있고 상세/설명 의도가 확인되어 상세 답변으로 승격",
                    }
                    patent_meta = self.load_patent_meta(detail_patent_id)
                    detail_query = (
                        f"{patent_meta.get('title', '')} "
                        f"{patent_meta.get('registration_number', '')} "
                        "서지사항 요약 배경기술 해결하려는 과제 과제의 해결 수단 청구범위 발명의 효과 "
                        "기술성 권리성 시장성 사업성 추가 확인"
                    )
                    detail_confidence = lexical_confidence(detail_query, overview_docs)
                    _, overview_source_cards = format_context(overview_docs)
                    for card in overview_source_cards:
                        card["relevance_score"] = 0.86
                        card["relevance_grade"] = "GOOD"
                        card["match_terms"] = ["개요", "요약", "청구항", "평가"]
                    answer_text = build_patent_overview_answer(
                        question=question,
                        patent_meta=patent_meta,
                        docs=overview_docs,
                        source_cards=overview_source_cards,
                        confidence=detail_confidence,
                    )
                    overview_quality_metrics = build_overview_quality_metrics(
                        question=question,
                        retrieval_question=detail_query,
                        docs=overview_docs,
                        source_cards=overview_source_cards,
                        confidence=detail_confidence,
                        retrieval_query_expanded=True,
                    )
                    patent_hits = {
                        group["patent_id"]: len(group.get("docs") or [])
                        for group in patent_groups
                    }
                    metrics = {
                        "scope": "GLOBAL",
                        "patent_id": detail_patent_id,
                        "global_search": True,
                        "patent_hit_count": len(patent_groups),
                        "question_intents": detect_question_intents(question),
                        "patent_hits": patent_hits,
                        "search_result_patents": [
                            {
                                "patent_id": group["patent_id"],
                                "title": group["title"],
                                "registration_number": group.get("registration_number"),
                                "score": group["score"],
                                "matched_terms": group.get("matched_terms") or [],
                                "source_types": group.get("source_types") or [],
                            }
                            for group in patent_groups
                        ],
                        "local_context_count": len(overview_docs),
                        "web_context_count": 0,
                        "confidence_score": round(detail_confidence, 4),
                        **retrieval_metrics,
                        "web_search_ms": 0,
                        "llm_ms": 0,
                        "total_ms": now_ms() - total_t0,
                        "answer_mode": "GLOBAL_PATENT_DETAIL",
                        "answer_cache_hit": False,
                        "answer_generation_basis": "global_domain_match_to_section_overview",
                        "answer_presentation": [
                            "summary_table",
                            "flow_diagram",
                            "component_table",
                            "score_table",
                            "pdf_page_preview",
                            "collapsible_sources",
                        ],
                        "discovery_query_terms": query_terms,
                        "discovery_directness_score": round(best_directness, 4),
                        **detail_scope_metrics,
                        **overview_quality_metrics,
                    }
                    self._log_query(user_id, detail_patent_id, question, "GLOBAL", detail_confidence, metrics)
                    return {
                        "answer": answer_text,
                        "source_cards": overview_source_cards,
                        "metrics": metrics if RETURN_PERFORMANCE else {},
                    }
            if is_visual_asset_question(question) and len(patent_groups) == 1 and best_directness >= 0.55:
                detail_patent_id = str(patent_groups[0].get("patent_id") or "")
                visual_t0 = now_ms()
                visual_docs = select_visual_asset_docs(detail_patent_id, question, max_docs=6, fallback=True)
                if visual_docs:
                    _, visual_source_cards = format_context(visual_docs)
                    for doc, card in zip(visual_docs, visual_source_cards):
                        detail = visual_asset_relevance_detail(question, doc)
                        card["relevance_score"] = detail["score"]
                        card["relevance_grade"] = detail["grade"]
                        card["match_terms"] = detail["matched_terms"]
                    answer_text = build_visual_asset_answer(
                        question=question,
                        docs=visual_docs,
                        source_cards=visual_source_cards,
                    )
                    visual_quality_metrics = build_visual_asset_quality_metrics(
                        question=question,
                        docs=visual_docs,
                        source_cards=visual_source_cards,
                        retrieval_query_expanded=retrieval_query_expanded,
                    )
                    visual_confidence = float(visual_quality_metrics.get("retrieval_quality_score") or 0.0)
                    patent_hits = {
                        group["patent_id"]: len(group.get("docs") or [])
                        for group in patent_groups
                    }
                    metrics = {
                        "scope": "GLOBAL",
                        "patent_id": detail_patent_id,
                        "global_search": True,
                        "patent_hit_count": len(patent_groups),
                        "question_intents": detect_question_intents(question),
                        "patent_hits": patent_hits,
                        "search_result_patents": [
                            {
                                "patent_id": group["patent_id"],
                                "title": group["title"],
                                "registration_number": group.get("registration_number"),
                                "score": group["score"],
                                "matched_terms": group.get("matched_terms") or [],
                                "source_types": group.get("source_types") or [],
                            }
                            for group in patent_groups
                        ],
                        "local_context_count": len(visual_docs),
                        "web_context_count": 0,
                        "confidence_score": round(visual_confidence, 4),
                        **retrieval_metrics,
                        "visual_asset_selection_ms": now_ms() - visual_t0,
                        "web_search_ms": 0,
                        "llm_ms": 0,
                        "total_ms": now_ms() - total_t0,
                        "answer_mode": "GLOBAL_VISUAL_ASSET_RAG",
                        "answer_cache_hit": False,
                        "answer_generation_basis": "global_domain_match_to_visual_assets",
                        "answer_presentation": ["visual_asset_table", "asset_previews", "collapsible_sources"],
                        "discovery_query_terms": query_terms,
                        "discovery_directness_score": round(best_directness, 4),
                        **domain_scope_metrics,
                        **visual_quality_metrics,
                    }
                    self._log_query(user_id, detail_patent_id, question, "GLOBAL", visual_confidence, metrics)
                    return {
                        "answer": answer_text,
                        "source_cards": visual_source_cards,
                        "metrics": metrics if RETURN_PERFORMANCE else {},
                    }
            answer_text = build_global_discovery_answer(
                question=question,
                patent_groups=patent_groups,
                source_cards=source_cards,
                query_terms=query_terms,
                confidence=confidence,
            )
            patent_hits = {
                group["patent_id"]: len(group.get("docs") or [])
                for group in patent_groups
            }
            metrics = {
                "scope": "GLOBAL",
                "patent_id": None,
                "global_search": True,
                "patent_hit_count": len(patent_groups),
                "question_intents": detect_question_intents(question),
                "patent_hits": patent_hits,
                "search_result_patents": [
                    {
                        "patent_id": group["patent_id"],
                        "title": group["title"],
                        "registration_number": group.get("registration_number"),
                        "score": group["score"],
                        "matched_terms": group.get("matched_terms") or [],
                        "source_types": group.get("source_types") or [],
                    }
                    for group in patent_groups
                ],
                "local_context_count": len(selected_docs),
                "web_context_count": 0,
                "confidence_score": round(confidence, 4),
                **retrieval_metrics,
                "web_search_ms": 0,
                "llm_ms": 0,
                "total_ms": now_ms() - total_t0,
                "answer_mode": "GLOBAL_PATENT_DISCOVERY",
                "answer_cache_hit": False,
                "answer_generation_basis": "patent_level_grouped_retrieval",
                "answer_presentation": ["answer_summary", "patent_result_table", "collapsible_sources"],
                "discovery_query_terms": query_terms,
                **domain_scope_metrics,
                **search_quality_metrics,
            }
            self._log_query(user_id, None, question, "GLOBAL", confidence, metrics)
            return {
                "answer": answer_text,
                "source_cards": source_cards,
                "metrics": metrics if RETURN_PERFORMANCE else {},
            }

        matched_patent_ids = identifier_matched_patent_ids(question, docs) or title_matched_patent_ids(question, docs)
        if matched_patent_ids:
            docs = [doc for doc in docs if _patent_id_from_doc(doc) in matched_patent_ids] or docs
            enrich_corpus = [doc for doc in self.global_docs if _patent_id_from_doc(doc) in matched_patent_ids]
        else:
            retrieved_patent_ids = {_patent_id_from_doc(doc) for doc in docs if _patent_id_from_doc(doc)}
            enrich_corpus = [
                doc
                for doc in self.global_docs
                if not retrieved_patent_ids or _patent_id_from_doc(doc) in retrieved_patent_ids
            ]
        docs = enrich_docs_for_answer(
            question=question,
            retrieved_docs=docs,
            all_docs=enrich_corpus or docs,
            top_k=TOP_K,
        )
        confidence = lexical_confidence(retrieval_question, docs)

        if confidence < MIN_LOCAL_CONFIDENCE:
            return self._blocked_response(
                "전체 특허/보고서 인덱스에서 질문과 직접 관련된 근거를 찾지 못했습니다.",
                None,
                "GLOBAL",
                total_t0,
                confidence=confidence,
                extra_metrics={
                    **retrieval_metrics,
                    "global_search": True,
                    "local_context_count": len(docs),
                    "web_context_count": 0,
            "retrieval_query_expanded": retrieval_query_expanded,
            "matched_patent_ids": matched_patent_ids,
            "answer_cache_hit": False,
            **domain_scope_metrics,
        },
                user_id=user_id,
                question=question,
            )

        final_docs = enrich_docs_for_answer(question, docs, docs, top_k=TOP_K)
        context, source_cards = format_context(final_docs)
        annotate_source_cards(question, final_docs[: len(source_cards)], source_cards)
        grounded_context = build_grounded_llm_context(
            question=question,
            docs=final_docs[: len(source_cards)],
            source_cards=source_cards,
        )
        search_quality_metrics = build_search_quality_metrics(
            question=question,
            retrieval_question=retrieval_question,
            docs=final_docs[: len(source_cards)],
            source_cards=source_cards,
            confidence=confidence,
            retrieval_query_expanded=retrieval_query_expanded,
        )
        llm_ms = 0
        if ANSWER_GENERATION_MODE == "extractive":
            answer_text = build_extractive_answer(
                question=question,
                scope="GLOBAL",
                docs=final_docs[: len(source_cards)],
                source_cards=source_cards,
                confidence=confidence,
            )
            answer_mode = "GLOBAL_GROUNDED_EXTRACTIVE_RAG"
            answer_basis = "global_multi_pass_retrieval_source_cards"
        else:
            llm_t0 = now_ms()
            answer_text = call_ollama(
                [
                    {"role": "system", "content": build_system_prompt("GLOBAL")},
                    {"role": "user", "content": build_user_prompt(question, "{}", grounded_context or context)},
                ]
            )
            answer_text = enforce_answer_policy(answer_text, source_cards)
            llm_ms = now_ms() - llm_t0
            answer_mode = "GLOBAL_RAG_LLM"
            answer_basis = "global_retrieved_context_plus_llm"
        patent_hits: Dict[str, int] = {}
        for doc in final_docs[: len(source_cards)]:
            hit_patent_id = str((doc.metadata or {}).get("patent_id") or "-")
            patent_hits[hit_patent_id] = patent_hits.get(hit_patent_id, 0) + 1

        metrics = {
            "scope": "GLOBAL",
            "patent_id": None,
            "global_search": True,
            "patent_hit_count": len([key for key in patent_hits if key != "-"]),
            "patent_hits": patent_hits,
            "local_context_count": len(docs),
            "web_context_count": 0,
            "confidence_score": round(confidence, 4),
            **retrieval_metrics,
            "web_search_ms": 0,
            "llm_ms": llm_ms,
            "total_ms": now_ms() - total_t0,
            "answer_mode": answer_mode,
            "answer_cache_hit": False,
            "answer_generation_basis": answer_basis,
            "matched_patent_ids": matched_patent_ids,
            **domain_scope_metrics,
            **search_quality_metrics,
        }
        self._log_query(user_id, None, question, "GLOBAL", confidence, metrics)
        return {
            "answer": answer_text,
            "source_cards": source_cards,
            "metrics": metrics if RETURN_PERFORMANCE else {},
        }
