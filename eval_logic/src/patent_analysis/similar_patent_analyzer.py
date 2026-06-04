"""
Compare the target patent with collected similar patents.

This module intentionally separates deterministic similarity signals from LLM
wording. The deterministic scores are always produced. If OPENAI_API_KEY is
available and --use-llm is passed, a short comparison summary is added.

Usage:
    python3 similar_patent_analyzer.py
    python3 similar_patent_analyzer.py --use-llm
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
from core.paths import RUNTIME_ANALYSIS_DIR, ROOT_DIR, SAMPLE_DATA_DIR
from core.schemas import normalize_patent_input

if load_dotenv:
    load_dotenv(ROOT_DIR / ".env")


DEFAULT_TARGET = SAMPLE_DATA_DIR / "patent_input.json"
DEFAULT_DETAILS = SAMPLE_DATA_DIR / "similar_patent_details.json"
DEFAULT_OUTPUT = RUNTIME_ANALYSIS_DIR / "similar_patent_analysis.json"


def normalize_patent_id_for_path(value: str | None) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", str(value or "")).strip("_")


def target_output_candidates(patent_id: str, output_dir: Path) -> list[Path]:
    normalized = normalize_patent_id_for_path(patent_id)
    hyphen = normalized.replace("_", "-")
    return [
        output_dir / f"patent_{normalized}_output.json",
        output_dir / f"patent_{hyphen}_output.json",
    ]


def find_target_output(patent_id: str, output_dir: Path) -> Path:
    for path in target_output_candidates(patent_id, output_dir):
        if path.exists():
            return path
    return target_output_candidates(patent_id, output_dir)[0]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(text_value(item) for item in value)
    if isinstance(value, dict):
        preferred = []
        for key in ("description_summary", "abstract", "summary", "reason", "basis", "title"):
            if key in value:
                preferred.append(text_value(value.get(key)))
        if preferred:
            return " ".join(part for part in preferred if part)
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def normalize_patent_identifier(value: Any) -> str:
    text = re.sub(r"[^0-9A-Za-z]", "", str(value or ""))
    return text[2:] if text.startswith("KR") else text


def tokenize(value: Any) -> set[str]:
    text = normalize_text(value)
    tokens = re.findall(r"[0-9a-zA-Z가-힣]{2,}", text)
    stopwords = {"및", "또는", "하는", "있는", "기반", "방법", "시스템", "장치", "제공", "포함"}
    return {token for token in tokens if token not in stopwords}


def text_ratio(a: Any, b: Any) -> float:
    a_text = normalize_text(a)
    b_text = normalize_text(b)
    if not a_text or not b_text:
        return 0.0
    return SequenceMatcher(None, a_text, b_text).ratio()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def flatten_target_claims(claims: dict[str, Any]) -> str:
    texts = []
    for key in sorted(claims):
        value = claims[key]
        if isinstance(value, dict):
            texts.append(str(value.get("text", "")))
        else:
            texts.append(str(value))
    return " ".join(texts)


def flatten_detail_claims(claims: Any) -> str:
    if isinstance(claims, list):
        return " ".join(str(v) for v in claims)
    if isinstance(claims, dict):
        return flatten_target_claims(claims)
    return str(claims or "")


def claim_text_items(claims: Any) -> list[tuple[str, str]]:
    if isinstance(claims, dict):
        items = []
        for key in sorted(claims):
            value = claims[key]
            text = value.get("text", "") if isinstance(value, dict) else value
            items.append((str(key), str(text or "").strip()))
        return items
    if isinstance(claims, list):
        return [(str(index), str(value or "").strip()) for index, value in enumerate(claims, 1)]
    text = str(claims or "").strip()
    return [("claim", text)] if text else []


def is_deleted_claim(text: str) -> bool:
    return bool(re.search(r"^\s*\d+\.\s*삭제\s*$|^삭제\s*$", text))


def is_dependent_claim(text: str) -> bool:
    return bool(re.search(r"청구항\s*\d+\s*에\s*있어서|제\s*\d+\s*항\s*에\s*있어서", text))


def representative_claims(claims: Any, independent_hint: Any = None, limit: int = 3, char_limit: int = 2200) -> str:
    items = [(key, text) for key, text in claim_text_items(claims) if text and not is_deleted_claim(text)]
    if not items:
        return ""

    hinted_numbers = set()
    if isinstance(independent_hint, list):
        hinted_numbers = {str(value) for value in independent_hint}
    elif isinstance(independent_hint, int):
        hinted_numbers = {str(index) for index in range(1, independent_hint + 1)}
    elif isinstance(independent_hint, str):
        hinted_numbers = set(re.findall(r"\d+", independent_hint))

    selected: list[tuple[str, str]] = []
    for key, text in items:
        key_numbers = set(re.findall(r"\d+", key)) or set(re.findall(r"^\s*(\d+)\.", text))
        if hinted_numbers and key_numbers & hinted_numbers:
            selected.append((key, text))

    if not selected:
        selected = [(key, text) for key, text in items if not is_dependent_claim(text)]
    if not selected:
        selected = items[:limit]

    chunks = []
    used = 0
    for key, text in selected[:limit]:
        claim_no = next(iter(re.findall(r"\d+", key)), key)
        body = re.sub(r"\s+", " ", text).strip()
        chunk = f"[청구항 {claim_no}] {body}"
        if used + len(chunk) > char_limit:
            chunk = chunk[: max(0, char_limit - used - 3)] + "..."
        chunks.append(chunk)
        used += len(chunk)
        if used >= char_limit:
            break
    return "\n".join(chunks)


def parse_llm_json(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def polish_report_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    replacements = [
        ("중점을 둔다.", "중점을 둡니다."),
        ("하고자 한다.", "하고자 합니다."),
        ("수행한다.", "수행합니다."),
        ("집중한다.", "집중합니다."),
        ("포함한다.", "포함합니다."),
        ("포섭한다.", "포섭합니다."),
        ("나타낸다.", "나타냅니다."),
        ("다르다.", "다릅니다."),
        ("어렵다.", "어렵습니다."),
        ("보인다.", "보입니다."),
        ("있다.", "있습니다."),
        ("없다.", "없습니다."),
        ("수 있다.", "수 있습니다."),
        ("수 없다.", "수 없습니다."),
        ("중요하다.", "중요합니다."),
        ("권장된다.", "권장됩니다."),
    ]
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def remove_generic_maintenance_sentence(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", polish_report_text(text))
    generic_patterns = (
        "전략적 유지",
        "적용 가능성이 높",
        "중요한 가치",
        "추가 검토",
        "시장 수요를 반영",
    )
    filtered = [sentence for sentence in sentences if not any(pattern in sentence for pattern in generic_patterns)]
    return " ".join(filtered).strip() or polish_report_text(text)


def ipc_overlap(target_ipc: list[str], detail_ipc: list[str]) -> float:
    target = {str(v).replace(" ", "") for v in target_ipc if v}
    detail = {str(v).replace(" ", "") for v in detail_ipc if v}
    if not target or not detail:
        return 0.0
    exact = len(target & detail) / len(target | detail)
    prefix_matches = 0
    for left in target:
        for right in detail:
            if left[:4] and left[:4] == right[:4]:
                prefix_matches += 1
                break
    prefix = prefix_matches / max(len(target), len(detail))
    return max(exact, prefix * 0.7)


def top_common_keywords(target_text: str, detail_text: str, limit: int = 8) -> list[str]:
    common = tokenize(target_text) & tokenize(detail_text)
    weights = Counter()
    merged = normalize_text(target_text + " " + detail_text)
    for token in common:
        weights[token] = merged.count(token)
    return [token for token, _ in weights.most_common(limit)]


def risk_level(detail: dict[str, Any], overall_similarity: float) -> str:
    status = str(detail.get("legal_status", ""))
    citation = detail.get("citation_count") or 0
    try:
        citation = int(citation)
    except Exception:
        citation = 0
    if "소멸" in status:
        return "낮음"
    if overall_similarity >= 0.72 or citation >= 20:
        return "높음"
    if overall_similarity >= 0.45 or citation >= 8:
        return "보통"
    return "낮음"


def is_active_status(status: Any) -> bool:
    text = str(status or "")
    if not text or any(word in text for word in ("소멸", "거절", "취하", "포기", "무효")):
        return False
    return any(word in text for word in ("등록", "공개", "유지", "이전"))


def is_enforceable_status(status: Any) -> bool:
    text = str(status or "")
    if not text or any(word in text for word in ("소멸", "거절", "취하", "포기", "무효", "공개")):
        return False
    return any(word in text for word in ("등록", "유지", "이전"))


def is_transferred_status(status: Any) -> bool:
    text = str(status or "")
    return "이전" in text or "매각" in text


def status_group(status: Any) -> str:
    text = str(status or "")
    if any(word in text for word in ("등록", "유지", "이전")):
        return "registered_or_maintained"
    if any(word in text for word in ("공개", "심사")):
        return "published_or_pending"
    if any(word in text for word in ("거절", "소멸", "취하", "포기", "무효")):
        return "rejected_or_expired"
    return "other"


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def get_application_year(detail: dict[str, Any]) -> int | None:
    source_detail = detail.get("source_detail", {}) if isinstance(detail.get("source_detail"), dict) else detail
    source_candidate = source_detail.get("source_candidate", {}) if isinstance(source_detail.get("source_candidate"), dict) else {}
    for value in (
        source_candidate.get("application_year"),
        source_detail.get("application_year"),
        detail.get("application_year"),
        source_detail.get("application_date"),
        detail.get("application_date"),
    ):
        match = re.search(r"(19|20)\d{2}", str(value or ""))
        if match:
            return int(match.group(0))
    return None


def claim_count(detail: dict[str, Any]) -> int | None:
    claims = detail.get("claims")
    if isinstance(claims, list):
        count = len([claim for claim in claims if str(claim).strip()])
        return count if count else None
    if isinstance(claims, dict):
        return len(claims) if claims else None
    return None


def target_claim_count(target: dict[str, Any]) -> int:
    meta_count = target.get("meta", {}).get("total_claims")
    if meta_count is not None:
        return to_int(meta_count)
    claims = target.get("claims_text", {})
    return len(claims) if isinstance(claims, dict) else 0


def normalize_target_document(target: dict[str, Any]) -> dict[str, Any]:
    if isinstance(target.get("meta"), dict):
        return normalize_patent_input(target)
    summary_text = text_value(target.get("description_summary")) or ""
    if not summary_text:
        # New output JSON uses "summary" for score aggregates, not patent text.
        # Use LLM evaluation reasons as a weak textual fallback for comparison.
        summary_text = " ".join(text_value(item.get("reason") or item.get("basis")) for item in target.get("llm_scores", [])[:5])
    return normalize_patent_input({
        **target,
        "meta": {
            "title": target.get("title", ""),
            "application_number": target.get("application_number", ""),
            "registration_number": target.get("patent_id", ""),
            "publication_number": "",
            "application_date": target.get("application_date", ""),
            "legal_status": target.get("legal_status", ""),
            "ipc": target.get("ipc", []),
            "assignee": target.get("assignee", []),
        },
        "description_summary": summary_text,
        "claims_text": target.get("claims_text") or {},
    })


def is_target_patent(target: dict[str, Any], detail: dict[str, Any]) -> bool:
    target_meta = target.get("meta", {}) if isinstance(target.get("meta"), dict) else {}
    target_numbers = {
        normalize_patent_identifier(target_meta.get("application_number")),
        normalize_patent_identifier(target_meta.get("registration_number")),
        normalize_patent_identifier(target_meta.get("publication_number")),
        normalize_patent_identifier(target.get("patent_id")),
    }
    target_numbers = {number for number in target_numbers if number}
    detail_source = detail.get("source_candidate", {}) if isinstance(detail.get("source_candidate"), dict) else {}
    detail_numbers = {
        normalize_patent_identifier(detail.get("application_number")),
        normalize_patent_identifier(detail.get("patent_no")),
        normalize_patent_identifier(detail_source.get("application_number")),
        normalize_patent_identifier(detail_source.get("patent_no")),
    }
    detail_numbers = {number for number in detail_numbers if number}

    if target_numbers & detail_numbers:
        return True

    target_title = normalize_text(target_meta.get("title"))
    detail_title = normalize_text(detail.get("title"))
    return bool(target_title and detail_title and target_title == detail_title)


def classify_assignee(applicant: Any) -> str:
    text = str(applicant or "")
    if not text:
        return "unknown"
    if any(keyword in text for keyword in ("대학교", "연구원", "ETRI", "KIST", "한국전자통신연구원")):
        return "research_institute"
    if any(keyword in text for keyword in ("주식회사", "(주)", "㈜")):
        if any(keyword in text for keyword in ("삼성", "네이버", "카카오", "에스케이", "SK", "케이티", "KT", "엔씨소프트")):
            return "large_enterprise"
        return "sme_startup"
    if "개인" in text:
        return "individual"
    return "other"


def build_rule_summary(detail: dict[str, Any], signals: dict[str, float], keywords: list[str]) -> str:
    title = detail.get("title", "해당 특허")
    keyword_text = ", ".join(keywords[:4]) if keywords else "직접 중복 키워드 부족"
    return (
        f"{title}는 분석 대상 특허와 {keyword_text} 등의 표현과 기술 요소가 일부 겹칩니다. "
        f"권리 상태와 출원 시점을 함께 보면 동일 기술군 안에서 비교 검토할 필요가 있는 후보입니다."
    )


def infer_technical_analysis(target: dict[str, Any], detail: dict[str, Any], signals: dict[str, float], keywords: list[str]) -> dict[str, str]:
    target_meta = target.get("meta", {}) if isinstance(target.get("meta"), dict) else {}
    target_claims = target_claim_count(target)
    detail_claims = claim_count(detail)
    keyword_text = ", ".join(keywords[:6]) if keywords else "직접 중복 키워드가 많지 않음"
    target_ipc = {str(v).replace(" ", "") for v in target_meta.get("ipc", []) if v}
    detail_ipc = {str(v).replace(" ", "") for v in detail.get("ipc", []) if v}
    ipc_common = ", ".join(sorted(target_ipc & detail_ipc)) or "완전 동일 IPC는 제한적"

    if detail_claims is None:
        scope = f"대상 특허의 청구항 수는 {target_claims}개이나 비교 특허의 청구항 수가 충분히 수집되지 않아 범위의 넓고 좁음을 단정하기 어렵습니다."
    elif target_claims > detail_claims:
        scope = f"대상 특허는 청구항 수가 {target_claims}개로 비교 특허({detail_claims}개)보다 많아, 형식상 더 넓은 실시형태를 포섭할 가능성이 있습니다."
    elif target_claims < detail_claims:
        scope = f"비교 특허는 청구항 수가 {detail_claims}개로 대상 특허({target_claims}개)보다 많아, 세부 실시형태를 더 촘촘하게 나누어 권리화했을 가능성이 있습니다."
    else:
        scope = f"양 특허의 청구항 수가 모두 {target_claims}개 수준이어서, 단순 청구항 수 기준의 범위 차이는 크지 않습니다."

    return {
        "technical_overlap": (
            f"겹치는 축은 {keyword_text}입니다. IPC 기준으로는 {ipc_common} 항목이 확인되며, "
            "오디오북 제작·검수 또는 콘텐츠 처리 자동화라는 문제 영역에서 비교할 수 있습니다."
        ),
        "technical_difference": (
            "차이는 구현 초점에서 나타납니다. 대상 특허는 제작 참여자·보이스 스타일·품질 검수·보정까지 이어지는 제작 운영 흐름을 넓게 다루는 반면, "
            f"비교 특허는 '{detail.get('title', '해당 특허')}'의 명칭과 청구항에 드러난 특정 처리 단계에 더 집중합니다."
        ),
        "scope_comparison": scope,
        "technical_review_point": (
            f"정량 신호는 제목 {signals.get('title', 0):.2f}, 청구항 {signals.get('claims', 0):.2f}, IPC {signals.get('ipc', 0):.2f} 수준입니다. "
            "단순 유사도보다 독립항의 필수 구성요소가 실제로 겹치는지와 회피설계 가능성을 우선 확인해야 합니다."
        ),
    }


def call_llm(prompt: str, max_tokens: int = 450) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""
    try:
        import openai

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_REPORT_MODEL", "gpt-4o"),
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "system",
                    "content": "특허 비교 분석가입니다. 입력 근거에 기반해 한국어로 간결하게 답하세요.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"LLM 비교 요약 생략: {exc}")
        return ""


def compare_one(target: dict[str, Any], detail: dict[str, Any], use_llm: bool = False) -> dict[str, Any]:
    target_meta = target.get("meta", {})
    target_title = text_value(target_meta.get("title", ""))
    target_abstract = text_value(target.get("description_summary", ""))
    target_claims = flatten_target_claims(target.get("claims_text", {}))
    target_text = " ".join([target_title, target_abstract, target_claims])

    detail_title = text_value(detail.get("title", ""))
    detail_abstract = text_value(detail.get("abstract", ""))
    detail_claims = flatten_detail_claims(detail.get("claims", []))
    detail_text = " ".join([detail_title, detail_abstract, detail_claims])

    title_score = text_ratio(target_title, detail_title)
    abstract_score = jaccard(tokenize(target_abstract), tokenize(detail_abstract))
    claim_score = jaccard(tokenize(target_claims), tokenize(detail_claims)) if detail_claims else 0.0
    keyword_score = jaccard(tokenize(target_text), tokenize(detail_text))
    ipc_score = ipc_overlap(target_meta.get("ipc", []), detail.get("ipc", []))

    if claim_score:
        overall = 0.18 * title_score + 0.22 * abstract_score + 0.30 * claim_score + 0.15 * keyword_score + 0.15 * ipc_score
    else:
        overall = 0.25 * title_score + 0.30 * abstract_score + 0.25 * keyword_score + 0.20 * ipc_score

    signals = {
        "overall": round(overall, 4),
        "title": round(title_score, 4),
        "abstract": round(abstract_score, 4),
        "claims": round(claim_score, 4),
        "keywords": round(keyword_score, 4),
        "ipc": round(ipc_score, 4),
    }
    common_keywords = top_common_keywords(target_text, detail_text)
    technical_analysis = infer_technical_analysis(target, detail, signals, common_keywords)

    summary = build_rule_summary(detail, signals, common_keywords)
    if use_llm:
        prompt = f"""분석 대상 특허:
제목: {target_title}
요약: {target_abstract[:900]}
주요 청구항: {target_claims[:1200]}

비교 특허:
제목: {detail_title}
출원인: {detail.get('applicant', '')}
법적 상태: {detail.get('legal_status', '')}
요약: {detail_abstract[:900]}
청구항: {detail_claims[:1200]}

정량 신호:
{json.dumps(signals, ensure_ascii=False)}
공통 키워드: {common_keywords}

보고서에 넣을 비교 요약을 2문장으로 작성하세요. 공통점과 차이/위험을 모두 포함하세요."""
        summary = call_llm(prompt) or summary

    return {
        "rank": detail.get("rank"),
        "patent_no": detail.get("patent_no"),
        "application_number": detail.get("application_number"),
        "title": detail_title,
        "applicant": detail.get("applicant"),
        "legal_status": detail.get("legal_status"),
        "citation_count": detail.get("citation_count"),
        "similarity": signals,
        "comparison": {
            "risk_level": risk_level(detail, signals["overall"]),
            "common_keywords": common_keywords,
            "common_points": build_common_points(target_meta, detail, common_keywords),
            "differences": build_differences(target_meta, detail),
            "summary": summary,
            "technical_analysis": technical_analysis,
        },
        "source_detail": detail,
    }


def build_common_points(target_meta: dict[str, Any], detail: dict[str, Any], keywords: list[str]) -> list[str]:
    points = []
    overlap = set(str(v).replace(" ", "") for v in target_meta.get("ipc", [])) & set(
        str(v).replace(" ", "") for v in detail.get("ipc", [])
    )
    if overlap:
        points.append(f"동일 IPC 보유: {', '.join(sorted(overlap))}")
    if keywords:
        points.append(f"핵심 키워드 중복: {', '.join(keywords[:5])}")
    if detail.get("similarity_basis"):
        points.append(str(detail["similarity_basis"]))
    return points


def build_differences(target_meta: dict[str, Any], detail: dict[str, Any]) -> list[str]:
    differences = []
    target_applicant = ", ".join(target_meta.get("assignee", [])) if isinstance(target_meta.get("assignee"), list) else str(target_meta.get("assignee", ""))
    if detail.get("applicant") and target_applicant and detail.get("applicant") not in target_applicant:
        differences.append(f"출원인 상이: 대상={target_applicant}, 비교={detail.get('applicant')}")
    if detail.get("application_date") and target_meta.get("application_date") and detail.get("application_date") != target_meta.get("application_date"):
        differences.append(f"출원일 상이: 대상={target_meta.get('application_date')}, 비교={detail.get('application_date')}")
    if detail.get("legal_status"):
        differences.append(f"비교 특허 법적 상태: {detail.get('legal_status')}")
    return differences


def select_top_comparisons(analyses: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    active = [item for item in analyses if is_enforceable_status(item.get("legal_status"))]
    active.sort(
        key=lambda item: (
            item.get("similarity", {}).get("overall", 0),
            to_int(item.get("citation_count")),
        ),
        reverse=True,
    )
    selected = active[:limit]
    for index, item in enumerate(selected, 1):
        item["top_comparison_rank"] = index
        item["reason_selected"] = "등록/유지 중인 유사 특허 중 종합 유사도 상위"
    return selected


def build_ecosystem_summary(target: dict[str, Any], analyses: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(analyses)
    active = [item for item in analyses if is_active_status(item.get("legal_status"))]
    enforceable = [item for item in analyses if is_enforceable_status(item.get("legal_status"))]
    expired = [item for item in analyses if "소멸" in str(item.get("legal_status", ""))]
    transferred = [item for item in analyses if is_transferred_status(item.get("legal_status"))]
    status_counts = Counter(status_group(item.get("legal_status")) for item in analyses)
    citations = [to_int(item.get("citation_count")) for item in analyses if item.get("citation_count") is not None]
    claim_counts = [
        claim_count(item.get("source_detail", {}))
        for item in analyses
    ]
    claim_counts = [count for count in claim_counts if count is not None]
    years = [year for year in (get_application_year(item) for item in analyses) if year is not None]
    target_year = get_application_year({"source_detail": {"application_date": target.get("meta", {}).get("application_date")}})
    applicant_types = Counter(classify_assignee(item.get("applicant")) for item in analyses)

    return {
        "total_similar_patents": total,
        "active_count": len(active),
        "enforceable_count": len(enforceable),
        "expired_count": len(expired),
        "transferred_count": len(transferred),
        "published_or_pending_count": status_counts.get("published_or_pending", 0),
        "rejected_or_expired_count": status_counts.get("rejected_or_expired", 0),
        "other_status_count": status_counts.get("other", 0),
        "status_distribution": dict(Counter(str(item.get("legal_status") or "미상") for item in analyses)),
        "status_group_distribution": dict(status_counts),
        "active_ratio": round(len(active) / total, 3) if total else 0,
        "enforceable_ratio": round(len(enforceable) / total, 3) if total else 0,
        "avg_citation_count": round(sum(citations) / len(citations), 2) if citations else None,
        "max_citation_count": max(citations) if citations else None,
        "avg_claim_count": round(sum(claim_counts) / len(claim_counts), 2) if claim_counts else None,
        "target_claim_count": target_claim_count(target),
        "application_year_range": {
            "min": min(years) if years else None,
            "max": max(years) if years else None,
            "target": target_year,
        },
        "recent_application_ratio": round(sum(1 for year in years if year >= 2021) / len(years), 3) if years else None,
        "assignee_distribution": dict(applicant_types),
    }


def compare_target_position(target: dict[str, Any], ecosystem: dict[str, Any]) -> dict[str, Any]:
    target_citation = to_int(target.get("kipris_data", {}).get("cited_count"), 0)
    avg_citation = ecosystem.get("avg_citation_count")
    target_claims = ecosystem.get("target_claim_count")
    avg_claims = ecosystem.get("avg_claim_count")
    year_info = ecosystem.get("application_year_range", {})
    target_year = year_info.get("target")
    min_year = year_info.get("min")
    max_year = year_info.get("max")

    if avg_citation is None:
        citation_position = "비교 데이터 부족"
    elif target_citation > avg_citation:
        citation_position = "평균 이상"
    elif target_citation == avg_citation:
        citation_position = "평균 수준"
    else:
        citation_position = "평균 이하"

    if avg_claims is None:
        claim_scope_position = "유사 특허 청구항 수 데이터 필요"
    elif target_claims > avg_claims:
        claim_scope_position = "평균보다 넓은 편"
    elif target_claims == avg_claims:
        claim_scope_position = "평균 수준"
    else:
        claim_scope_position = "평균보다 좁은 편"

    if target_year is None or min_year is None:
        timing_position = "출원 시점 비교 데이터 부족"
    elif target_year <= min_year:
        timing_position = "선도형"
    elif max_year is not None and target_year >= max_year:
        timing_position = "후발형"
    else:
        timing_position = "중간 진입형"

    active_ratio = ecosystem.get("active_ratio", 0)
    if active_ratio >= 0.7 and timing_position in {"후발형", "중간 진입형"}:
        overall_position = "활성 생태계 내 방어형 특허"
    elif active_ratio >= 0.7:
        overall_position = "활성 생태계 내 선점형 특허"
    elif active_ratio <= 0.4:
        overall_position = "약화 가능 생태계 내 검토 필요 특허"
    else:
        overall_position = "중간 활성도 생태계 내 포지션 검토 특허"

    return {
        "target_citation_count": target_citation,
        "citation_position": citation_position,
        "claim_scope_position": claim_scope_position,
        "timing_position": timing_position,
        "status_position": target.get("meta", {}).get("legal_status", "-"),
        "overall_position": overall_position,
    }


def build_interpretation(ecosystem: dict[str, Any], target_position: dict[str, Any], top_comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    active_ratio = ecosystem.get("active_ratio", 0)
    enforceable_count = ecosystem.get("enforceable_count", 0)
    pending_count = ecosystem.get("published_or_pending_count", 0)
    rejected_count = ecosystem.get("rejected_or_expired_count", 0)
    avg_citation = ecosystem.get("avg_citation_count")
    avg_claims = ecosystem.get("avg_claim_count")
    top_avg_similarity = (
        sum(item.get("similarity", {}).get("overall", 0) for item in top_comparisons) / len(top_comparisons)
        if top_comparisons
        else 0
    )
    large_count = ecosystem.get("assignee_distribution", {}).get("large_enterprise", 0)

    competition_intensity = "높음" if large_count >= 3 or active_ratio >= 0.7 else "보통" if active_ratio >= 0.4 else "낮음"
    differentiation_risk = "높음" if top_avg_similarity >= 0.45 else "보통" if top_avg_similarity >= 0.2 else "낮음"
    invalidity_or_designaround_risk = "보통" if ecosystem.get("total_similar_patents", 0) >= 5 else "낮음"

    citation_text = "피인용 수 데이터는 아직 충분하지 않습니다" if avg_citation is None else f"평균 피인용 수는 {avg_citation}건입니다"
    claim_text = "청구항 수 비교 데이터는 제한적입니다" if avg_claims is None else f"유사 특허의 평균 청구항 수는 {avg_claims}개입니다"
    analysis_summary = (
        f"이번 표는 KIPRIS 유사도 상위 {ecosystem.get('total_similar_patents', 0)}건 전체를 보여주며, "
        f"그중 등록 또는 유지 상태의 권리는 {enforceable_count}건, 공개·심사 단계는 {pending_count}건, 거절·소멸 등 권리화되지 않았거나 종료된 건은 {rejected_count}건입니다. "
        f"{citation_text}이며, {claim_text}. "
        "따라서 이 섹션은 유사 특허가 많다는 사실 자체보다, 실제로 권리로 살아 있는 특허가 어느 정도인지와 상위 등록 특허들이 대상 특허의 독립항 구성요소를 얼마나 겹쳐 갖는지를 확인하는 용도로 보는 것이 적절합니다. "
        "상위 비교 특허의 청구항과 대상 특허의 구성요소가 동시에 포섭되는지 추가 확인할 필요가 있습니다."
    )

    return {
        "competition_intensity": competition_intensity,
        "differentiation_risk": differentiation_risk,
        "invalidity_or_designaround_risk": invalidity_or_designaround_risk,
        "analysis_summary": analysis_summary,
    }


def enhance_top_comparison_with_llm(target: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    detail = comparison.get("source_detail", {})
    target_title = text_value(target.get("meta", {}).get("title", ""))
    target_abstract = text_value(target.get("description_summary", ""))
    target_claims = flatten_target_claims(target.get("claims_text", {}))
    target_representative_claims = representative_claims(
        target.get("claims_text", {}),
        independent_hint=target.get("meta", {}).get("independent_claims"),
        limit=3,
        char_limit=2600,
    )
    detail_claims = flatten_detail_claims(detail.get("claims", []))
    detail_representative_claims = representative_claims(
        detail.get("claims", []),
        limit=3,
        char_limit=2600,
    )
    prompt = f"""분석 대상 특허:
제목: {target_title}
출원인: {target.get('meta', {}).get('assignee', '')}
IPC: {target.get('meta', {}).get('ipc', '')}
출원일: {target.get('meta', {}).get('application_date', '')}
전체 청구항 수: {target_claim_count(target)}
요약: {target_abstract[:900]}
독립항/주요 청구항:
{target_representative_claims or target_claims[:1600]}

상세 비교 특허:
제목: {comparison.get('title', '')}
출원인: {comparison.get('applicant', '')}
법적 상태: {comparison.get('legal_status', '')}
피인용 수: {comparison.get('citation_count', '')}
IPC: {detail.get('ipc', '')}
출원일: {detail.get('application_date', '')}
청구항 수: {claim_count(detail)}
요약: {detail.get('abstract', '')[:900]}
독립항/주요 청구항:
{detail_representative_claims or detail_claims[:1600]}

정량 신호:
{json.dumps(comparison.get('similarity', {}), ensure_ascii=False)}
공통점:
{json.dumps(comparison.get('comparison', {}).get('common_points', []), ensure_ascii=False)}
차이점:
{json.dumps(comparison.get('comparison', {}).get('differences', []), ensure_ascii=False)}

다음 JSON만 출력하세요. 마크다운 금지.
{{
  "summary": "2문장. 왜 중요한 비교 대상인지와 추가 확인할 기술적 쟁점",
  "technical_overlap": "기술적으로 겹치는 구성요소를 구체적으로 설명",
  "technical_difference": "구현 초점과 권리 포섭 방향의 차이를 구체적으로 설명",
  "scope_comparison": "청구항 수와 독립항 구성 기준으로 누가 더 넓거나 좁아 보이는지, 단정이 어려우면 그 이유",
  "technical_review_point": "청구범위와 차별성 관점에서 추가 확인할 기술적 쟁점"
}}"""
    llm_summary = call_llm(prompt, max_tokens=900)
    if llm_summary:
        parsed = parse_llm_json(llm_summary)
        if parsed is None:
            comparison["comparison"]["summary"] = polish_report_text(llm_summary)
        else:
            comparison["comparison"]["summary"] = polish_report_text(parsed.get("summary") or comparison["comparison"].get("summary"))
            comparison["comparison"]["technical_analysis"] = {
                **comparison["comparison"].get("technical_analysis", {}),
                **{k: polish_report_text(v) for k, v in parsed.items() if k != "summary" and isinstance(v, str)},
            }
        comparison["comparison"]["summary_method"] = "llm"
    return comparison


def fallback_analysis_summary(ecosystem: dict[str, Any], top_comparisons: list[dict[str, Any]]) -> str:
    total = ecosystem.get("total_similar_patents", 0)
    enforceable_count = ecosystem.get("enforceable_count", 0)
    pending_count = ecosystem.get("published_or_pending_count", 0)
    rejected_count = ecosystem.get("rejected_or_expired_count", 0)
    titles = [item.get("title", "비교 특허") for item in top_comparisons]
    top_text = ", ".join(titles[:3]) if titles else "상위 등록 특허"
    implications = [
        item.get("comparison", {}).get("technical_analysis", {}).get("technical_review_point", "")
        for item in top_comparisons
    ]
    implications = [text for text in implications if text]
    implication_text = " ".join(implications[:2])
    return polish_report_text(
        f"KIPRIS 유사도 상위 {total}건은 등록/유지 {enforceable_count}건, 공개/심사중 {pending_count}건, 거절/소멸 {rejected_count}건으로 구성되어 권리화된 비교 대상이 절반 수준입니다. "
        f"상위 등록 비교군은 {top_text}이며, 대상 특허와 오디오북 제작·검수 자동화 또는 콘텐츠 생성 자동화 축에서 겹칩니다. "
        f"{implication_text or '다만 비교 특허별 구현 초점이 달라 독립항 구성요소 단위의 차별성 확인이 필요합니다.'}"
    )


def enhance_interpretation_with_llm(target: dict[str, Any], ecosystem: dict[str, Any], interpretation: dict[str, Any], top_comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    target_title = target.get("meta", {}).get("title", "")
    target_claims = representative_claims(
        target.get("claims_text", {}),
        independent_hint=target.get("meta", {}).get("independent_claims"),
        limit=3,
        char_limit=1800,
    )
    comparison_digest = []
    for item in top_comparisons:
        analysis = item.get("comparison", {}).get("technical_analysis", {})
        detail = item.get("source_detail", {})
        comparison_digest.append(
            {
                "title": item.get("title"),
                "status": item.get("legal_status"),
                "kipris_similarity": detail.get("similarity_score") or item.get("similarity_score"),
                "citation_count": item.get("citation_count"),
                "claim_count": claim_count(detail),
                "summary": item.get("comparison", {}).get("summary"),
                "technical_overlap": analysis.get("technical_overlap"),
                "technical_difference": analysis.get("technical_difference"),
                "scope_comparison": analysis.get("scope_comparison"),
                "technical_review_point": analysis.get("technical_review_point"),
            }
        )

    prompt = f"""아래 실제 유사 특허 분석 결과를 바탕으로 보고서의 '유사 특허 분석' 표 아래에 들어갈 결론 문단을 작성하세요.
일반론이나 '확인해야 합니다' 같은 원론적 문장 위주로 쓰지 말고, 입력된 비교 결과에서 드러난 실제 내용을 요약하세요.

분석 대상 특허: {target_title}
대상 특허 독립항/주요 청구항:
{target_claims}

생태계 통계:
{json.dumps(ecosystem, ensure_ascii=False)}

상위 등록/유지 비교 특허 3건:
{json.dumps(comparison_digest, ensure_ascii=False, indent=2)}

요구사항:
- 4~5문장 한국어 문단
- 첫 문장은 반드시 "KIPRIS 유사도 상위 N건 중 등록/유지 A건, 공개/심사중 B건, 거절/소멸 C건..." 형태의 상태 분포 해석으로 시작
- 실제 비교 특허명 또는 기술 축을 2개 이상 언급
- 대상 특허가 어떤 점에서 겹치고 어떤 점에서 차별화되는지 요약
- 청구범위와 차별성 관점에서 추가 확인할 쟁점을 포함
- 문체는 반드시 "~합니다", "~입니다" 체로 통일
- "전략적 유지가 권장됩니다", "적용 가능성이 높습니다", "중요한 가치가 있습니다", "추가 검토가 필요합니다"처럼 입력 없이도 쓸 수 있는 일반론은 금지
- 마크다운 금지"""
    comment = call_llm(prompt, max_tokens=800)
    if comment:
        interpretation["analysis_summary"] = remove_generic_maintenance_sentence(comment)
        interpretation["analysis_summary_method"] = "llm"
    else:
        interpretation["analysis_summary"] = fallback_analysis_summary(ecosystem, top_comparisons)
        interpretation["analysis_summary_method"] = "rule"
    return interpretation


def analyze_similar_patents(
    target_path: Path = DEFAULT_TARGET,
    details_path: Path = DEFAULT_DETAILS,
    output_path: Path = DEFAULT_OUTPUT,
    use_llm: bool = False,
) -> dict[str, Any]:
    target = normalize_target_document(load_json(target_path))
    details_data = load_json(details_path)
    details = [
        detail
        for detail in details_data.get("patents", [])
        if not is_target_patent(target, detail)
    ]

    analyses = [compare_one(target, detail, use_llm=False) for detail in details]
    analyses.sort(key=lambda item: item["similarity"]["overall"], reverse=True)
    for index, item in enumerate(analyses, 1):
        item["analysis_rank"] = index

    ecosystem = build_ecosystem_summary(target, analyses)
    target_position = compare_target_position(target, ecosystem)
    top_comparisons = select_top_comparisons(analyses, limit=3)
    if use_llm and os.environ.get("OPENAI_API_KEY"):
        top_comparisons = [enhance_top_comparison_with_llm(target, item) for item in top_comparisons]
    interpretation = build_interpretation(ecosystem, target_position, top_comparisons)
    if use_llm and os.environ.get("OPENAI_API_KEY"):
        interpretation = enhance_interpretation_with_llm(target, ecosystem, interpretation, top_comparisons)
    else:
        interpretation["analysis_summary"] = fallback_analysis_summary(ecosystem, top_comparisons)
        interpretation["analysis_summary_method"] = "rule"
    llm_used = (
        any(
            item.get("comparison", {}).get("summary_method") == "llm"
            for item in top_comparisons
            if isinstance(item.get("comparison"), dict)
        )
        or interpretation.get("analysis_summary_method") == "llm"
    )

    output = {
        "meta": {
            "target_patent_id": target.get("patent_id"),
            "target_title": target.get("meta", {}).get("title"),
            "source_target": str(target_path),
            "source_details": str(details_path),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "llm_requested": use_llm,
            "llm_available": bool(os.environ.get("OPENAI_API_KEY")),
            "llm_used": llm_used,
            "top_comparison_rule": "등록/유지 중인 유사 특허 중 종합 유사도 상위 3개, 동점 시 피인용 수 우선",
        },
        "ecosystem_summary": ecosystem,
        "target_position": target_position,
        "top_comparisons": top_comparisons,
        "interpretation": interpretation,
        "similar_patents": analyses,
    }
    write_json(output_path, output)
    print(f"저장 완료: {output_path} ({len(analyses)}건)")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="분석 대상 특허와 유사 특허 비교")
    parser.add_argument("--patent-id", default=None, help="특허별 output 파일명에 사용할 ID")
    parser.add_argument("--output-dir", default=str(RUNTIME_ANALYSIS_DIR), help="--patent-id 사용 시 입출력 파일 디렉터리")
    parser.add_argument("--target", default=None, help="분석 대상 특허 JSON")
    parser.add_argument("--details", default=None, help="유사 특허 상세정보 JSON")
    parser.add_argument("--output", default=None, help="분석 결과 JSON")
    parser.add_argument("--use-llm", action="store_true", help="OPENAI_API_KEY가 있으면 LLM 비교 요약 생성")
    args = parser.parse_args()
    patent_id = normalize_patent_id_for_path(args.patent_id)
    output_dir = Path(args.output_dir)
    target_path = Path(args.target) if args.target else (
        find_target_output(patent_id, output_dir) if patent_id else DEFAULT_TARGET
    )
    details_path = Path(args.details) if args.details else (
        output_dir / f"similar_details_{patent_id}.json" if patent_id else DEFAULT_DETAILS
    )
    output_path = Path(args.output) if args.output else (
        output_dir / f"similar_analysis_{patent_id}.json" if patent_id else DEFAULT_OUTPUT
    )

    analyze_similar_patents(
        target_path=target_path,
        details_path=details_path,
        output_path=output_path,
        use_llm=args.use_llm,
    )


if __name__ == "__main__":
    main()
