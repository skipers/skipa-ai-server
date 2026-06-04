"""HTML IP 가치 평가 보고서 생성기입니다.

이 모듈은 현재 렌더링 어댑터 역할을 합니다. 표준 평가 output JSON과 선택적인
프로젝트/유사 특허 산출물을 읽어 독립 실행형 HTML 보고서를 생성합니다. 이
파일은 점수 산정 규칙을 소유하지 않습니다. 향후 의사결정 로직은
서비스/워크플로우 모듈에 두고, 이 파일에는 구조화된 입력만 전달해야 합니다.

사용 예:
    python report_generator.py
    python report_generator.py --input-json ./output/patent_10-2886381_output.json --output-dir ./report
    python report_generator.py --no-llm
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from core.paths import ARTIFACT_OUTPUT_DIR, ARTIFACT_REPORT_DIR, ROOT_DIR

if load_dotenv:
    load_dotenv(ROOT_DIR / ".env")


DEFAULT_OUTPUT_JSONS = [
    ARTIFACT_OUTPUT_DIR / "patent_10-2886381_output.json",
    ARTIFACT_OUTPUT_DIR / "patent_10-2893083_output.json",
    ARTIFACT_OUTPUT_DIR / "patent_10-2762042_output.json",
]


SYSTEM_PROMPT = """당신은 IP(특허) 가치 평가 전문가입니다.
작성 원칙:
- 전문적이고 객관적인 한국어
- 사업부 의사결정자 대상
- 과장하지 말고 입력 데이터에 근거
- 마크다운 없이 순수 문단만 출력"""


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def fmt_date(value: Any) -> str:
    if not value:
        return "-"
    return str(value).replace("-", ".")


def join_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value or "-")


def truncate(value: Any, limit: int = 90) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "..."


def score_to_100(avg_score: float | int | None) -> int:
    """보고서 점수 척도(-2..+2)를 프로토타입 척도(0..100)로 변환합니다."""
    if avg_score is None:
        return 0
    return round(max(0, min(100, (float(avg_score) + 2) / 4 * 100)))


def item_score_to_5(score: float | int | None) -> int:
    """보고서 항목 점수 척도(-2..+2)를 1..5 배지 점수로 변환합니다."""
    if score is None:
        return 3
    return round(max(1, min(5, float(score) + 3)))


def conf_class(confidence: str) -> str:
    if confidence == "높음":
        return "conf-high"
    if confidence == "보통":
        return "conf-mid"
    return "conf-low"


def status_class(status: Any) -> str:
    text = str(status or "")
    if any(word in text for word in ("소멸", "거절", "취하", "포기", "무효")):
        return "status-expired"
    return "status-keep"


def status_label(status: Any) -> str:
    text = str(status or "-")
    return "유지" if "유지" in text or "등록" in text else text


def display_value(value: Any, missing: str = "-") -> str:
    return missing if value in (None, "") else str(value)


def clean_applicant_name(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if "더보기" not in text and "닫기" not in text:
        return text or "-"
    first, _, rest = text.partition("더보기")
    rest = rest.replace("닫기", "").strip()
    first = first.strip()
    return f"{first} 외 {rest}" if first and rest else first or rest or "-"


def source_candidate_for(patent: dict[str, Any]) -> dict[str, Any]:
    source_detail = patent.get("source_detail", {}) if isinstance(patent.get("source_detail"), dict) else {}
    return source_detail.get("source_candidate", {}) if isinstance(source_detail.get("source_candidate"), dict) else {}


def source_detail_for(patent: dict[str, Any]) -> dict[str, Any]:
    return patent.get("source_detail", {}) if isinstance(patent.get("source_detail"), dict) else {}


def application_number_for(patent: dict[str, Any]) -> str:
    source_detail = source_detail_for(patent)
    source_candidate = source_candidate_for(patent)
    return (
        patent.get("application_number")
        or source_detail.get("application_number")
        or source_candidate.get("application_number")
        or "-"
    )


def kipris_similarity_text(patent: dict[str, Any]) -> str:
    source_detail = source_detail_for(patent)
    source_candidate = source_candidate_for(patent)
    value = patent.get("similarity_score") or source_candidate.get("similarity_score") or source_detail.get("similarity_score")
    if value in (None, ""):
        return "-"
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def citation_count_text(patent: dict[str, Any]) -> str:
    source_detail = source_detail_for(patent)
    source_candidate = source_candidate_for(patent)
    value = patent.get("citation_count")
    if value in (None, ""):
        value = source_detail.get("citation_count")
    if value in (None, ""):
        value = source_candidate.get("citation_count")
    if value in (None, ""):
        return "미수집"
    return str(value)


def application_date_text(patent: dict[str, Any]) -> str:
    source_detail = source_detail_for(patent)
    source_candidate = source_candidate_for(patent)
    return display_value(
        patent.get("application_date")
        or source_detail.get("application_date")
        or source_candidate.get("application_date")
    )


def sentence_from_points(points: list[Any], fallback: str) -> str:
    texts = [str(point).strip() for point in points if str(point).strip()]
    if not texts:
        return fallback
    cleaned = []
    for text in texts[:3]:
        text = text.replace("더보기", " 외 ").replace("닫기", "")
        text = re.sub(r"\s+", " ", text).strip()
        if text.startswith("핵심 키워드 중복:"):
            content = text.split(":", 1)[1].strip()
            text = f"주요 표현과 기능 요소({content})가 겹쳐 동일한 문제 영역을 다루는 후보로 볼 수 있습니다."
        elif text.startswith("동일 IPC 보유:"):
            content = text.split(":", 1)[1].strip()
            text = f"동일하거나 가까운 IPC 분류({content})를 공유해 기술 분류상 인접성이 확인됩니다."
        elif text.startswith("KIPRIS 특화검색 유사도"):
            content = text.replace("KIPRIS 특화검색 유사도", "", 1).strip()
            text = f"KIPRIS 검색 유사도는 {content}입니다."
        elif text.startswith("출원인 상이:"):
            content = text.split(":", 1)[1].strip()
            text = f"출원인은 서로 다릅니다({content}). 권리 보유 주체가 달라 사업적 이해관계도 별도로 봐야 합니다."
        elif text.startswith("출원일 상이:"):
            content = text.split(":", 1)[1].strip()
            text = f"출원 시점은 서로 다릅니다({content}). 따라서 선후관계와 후속 개량 여부를 함께 검토해야 합니다."
        elif text.startswith("비교 특허 법적 상태:"):
            content = text.split(":", 1)[1].strip()
            text = f"비교 특허의 현재 상태는 {content}입니다."
        if not text.endswith((".", "다", "요")):
            text += "입니다."
        cleaned.append(text)
    return " ".join(cleaned)


def report_tone(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    replacements = [
        ("중점을 둔다", "중점을 둡니다"),
        ("초점을 맞추고 있다", "초점을 맞추고 있습니다"),
        ("주안점을 둔다", "주안점을 둡니다"),
        ("수행한다", "수행합니다"),
        ("집중한다", "집중합니다"),
        ("포함한다", "포함합니다"),
        ("포섭한다", "포섭합니다"),
        ("제공한다", "제공합니다"),
        ("나타낸다", "나타냅니다"),
        ("시사한다", "시사할 수 있습니다"),
        ("다르다", "다릅니다"),
        ("가능하다", "가능합니다"),
        ("어렵다", "어렵습니다"),
        ("대상이다", "대상입니다"),
        ("근거를 제공한다", "근거를 제공합니다"),
        ("결정해야 한다", "판단할 수 있습니다"),
        ("확인해야 한다", "확인할 수 있습니다"),
        ("가치가 있을 수 있다", "가치가 있을 수 있습니다"),
        ("포섭될 수 있다", "포섭될 수 있습니다"),
        ("수행합니다는 점", "수행한다는 점"),
        ("기틀이 될 것이다", "근거가 될 수 있습니다"),
        ("기틀이 될 것입니다", "근거가 될 수 있습니다"),
        ("기술적 차이점이 유지 여부를 판단하는 데 중요한 실마리가 될 수 있습니다", "기술적 차이점은 유지 가능성을 검토할 때 참고할 수 있는 요소로 보입니다"),
        ("유지 판단에서는", "유지 가능성 검토에서는"),
        ("유지 여부를 판단하는 데", "유지 가능성을 검토할 때"),
        ("판단하는 데", "검토할 때"),
        ("판단해야 합니다", "판단할 수 있습니다"),
        ("판단해야 하며", "판단할 수 있으며"),
        ("결정해야 합니다", "판단할 수 있습니다"),
        ("결정해야 하며", "판단할 수 있으며"),
        ("확인해야 합니다", "확인할 수 있습니다"),
        ("확인해야 하며", "확인할 수 있으며"),
        ("검토해야 합니다", "검토할 수 있습니다"),
        ("검토해야 하며", "검토할 수 있으며"),
        ("검토해야 한다", "검토할 수 있습니다"),
        ("검토해야 하다", "검토할 수 있습니다"),
        ("고려해야 합니다", "고려할 수 있습니다"),
        ("고려해야 하며", "고려할 수 있으며"),
        ("고려해야 한다", "고려할 수 있습니다"),
        ("고려해야 하다", "고려할 수 있습니다"),
        ("등록이 필요하며", "등록 확보가 유리할 수 있으며"),
        ("전략 수립이 필요합니다", "전략 수립에 참고할 수 있습니다"),
        ("추가 분석이 필요합니다", "추가 분석이 유용할 수 있습니다"),
        ("추가 출원 검토가 필요합니다", "추가 출원을 검토할 수 있습니다"),
        ("별도 확인이 필요합니다", "별도 확인이 유용할 수 있습니다"),
        ("필요가 있습니다", "필요할 수 있습니다"),
        ("필요합니다", "필요할 수 있습니다"),
        ("요구됩니다", "요구될 수 있습니다"),
        ("요구되며", "요구될 수 있으며"),
        ("요구될 것입니다", "요구될 수 있습니다"),
        ("요구될 것입니다", "요구될 수 있습니다"),
        ("재검토가 요구될 수 있으며", "재검토 여지가 있으며"),
        ("재검토가 요구될 수 있습니다", "재검토 여지가 있습니다"),
        ("중요합니다", "중요하게 작용할 수 있습니다"),
        ("중요하다", "중요하게 작용할 수 있습니다"),
        ("명확히 해 두는 것이 좋습니다", "명확히 해 둘 수 있습니다"),
        ("입증하는 것이 필요합니다", "입증하는 방향을 검토할 수 있습니다"),
        ("보완할 필요가 있습니다", "보완할 여지가 있습니다"),
        ("유지할 가치가 있습니다", "유지 가치가 있는 것으로 보입니다"),
        ("유지할 가치가 높습니다", "유지 가치가 높은 것으로 보입니다"),
        ("되어야 할 것입니다", "될 수 있습니다"),
        ("해야 할 것입니다", "할 수 있습니다"),
        ("해야 합니다", "할 수 있습니다"),
        ("해야 하며", "할 수 있으며"),
        ("해야 한다", "할 수 있습니다"),
        ("해야 하다", "할 수 있습니다"),
        ("관리한다", "관리합니다"),
    ]
    for source, target in replacements:
        text = text.replace(source, target)
    return text


def call_llm(user_prompt: str, max_tokens: int = 900) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""

    try:
        import openai

        client = openai.OpenAI(api_key=api_key)
        res = client.chat.completions.create(
            model=os.environ.get("OPENAI_REPORT_MODEL", "gpt-4o"),
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (res.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"LLM 요약 생성 생략: {exc}")
        return ""


def render_ref_list(refs: list[dict[str, str]]) -> str:
    rows = []
    for index, ref in enumerate(refs, 1):
        text = f"{ref['title']}, {ref['src']}." if ref.get("src") else f"{ref['title']}."
        if ref.get("url"):
            body = f'<a href="{esc(ref["url"])}" target="_blank" class="ref-link">{esc(text)}</a>'
        else:
            body = esc(text)
        rows.append(f'    <li><span class="ref-num">[{index}]</span> {body}</li>')
    return "\n".join(rows)


def render_evidence_links(sources: list[dict[str, str]], prefix: str = "근거") -> str:
    rows = []
    seen = set()
    for index, source in enumerate(sources, 1):
        title = str(source.get("title") or "-").strip()
        url = str(source.get("url") or "").strip()
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        if url:
            body = f'<a class="evidence-link" href="{esc(url)}" target="_blank">{esc(title)}</a>'
        else:
            body = f'<span class="evidence-link">{esc(title)}</span>'
        rows.append(f'<li>{body}</li>')
    if not rows:
        return '<div class="detail-text">근거 자료 없음</div>'
    return f'<ol class="evidence-list">{"".join(rows)}</ol>'


OUTPUT_DIMENSION_ORDER = ["기술성", "권리성", "시장성 및 사업성", "사업성"]
OUTPUT_CARD_COLORS = {
    "종합": "#111827",
    "기술성": "#1a6e3c",
    "권리성": "#7a6a00",
    "시장성 및 사업성": "#8b1a1a",
    "사업성": "#1a5c7a",
}


def score_5_to_100(score: float | int | None) -> int:
    if score is None:
        return 0
    return round(max(0, min(100, float(score) / 5 * 100)))


def output_score_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(data.get("auto_scores") or []) + list(data.get("llm_scores") or [])


def output_dimension_order(data: dict[str, Any]) -> list[str]:
    dims = {item.get("dim", "기타") for item in output_score_items(data)}
    ordered = [dim for dim in OUTPUT_DIMENSION_ORDER if dim in dims]
    ordered.extend(sorted(dim for dim in dims if dim not in ordered))
    return ordered


def output_dimension_summary(data: dict[str, Any]) -> dict[str, dict[str, float | int]]:
    summary: dict[str, dict[str, float | int]] = {}
    for item in output_score_items(data):
        dim = str(item.get("dim") or "기타")
        score = item.get("score")
        if not isinstance(score, (int, float)):
            continue
        bucket = summary.setdefault(dim, {"total": 0.0, "count": 0, "average": 0.0})
        bucket["total"] = float(bucket["total"]) + float(score)
        bucket["count"] = int(bucket["count"]) + 1
    for bucket in summary.values():
        count = int(bucket["count"])
        bucket["average"] = round(float(bucket["total"]) / count, 2) if count else 0.0
    return summary


def output_overall_average(data: dict[str, Any]) -> float:
    items = [item for item in output_score_items(data) if isinstance(item.get("score"), (int, float))]
    if not items:
        return 0.0
    return round(sum(float(item["score"]) for item in items) / len(items), 2)


def output_grade(avg: float) -> str:
    if avg >= 4.2:
        return "우수"
    if avg >= 3.5:
        return "양호"
    if avg >= 2.8:
        return "보통"
    return "보완 필요"


def method_label(method: Any) -> str:
    text = str(method or "-")
    labels = {
        "auto": "자동산출",
        "auto_kosis": "자동산출(KOSIS)",
        "llm": "LLM 분석",
    }
    return labels.get(text, text)


def output_item_basis(item: dict[str, Any]) -> str:
    return report_tone(item.get("reason") or item.get("basis") or "-")


def output_item_summary(item: dict[str, Any]) -> str:
    return report_tone(
        item.get("judgement_summary")
        or item.get("judgment_summary")
        or item.get("summary")
        or truncate(item.get("reason") or item.get("basis") or "-", 50)
    )


def output_sources_for_item(item: dict[str, Any]) -> list[dict[str, str]]:
    refs = []
    for source in item.get("sources") or []:
        if not isinstance(source, dict):
            continue
        refs.append(
            {
                "title": str(source.get("title") or "-").strip(),
                "url": str(source.get("url") or "").strip(),
                "src": str(source.get("published_date") or "").strip(),
                "snippet": str(source.get("snippet") or "").strip(),
            }
        )
    return refs


def render_output_item_source_detail(item: dict[str, Any]) -> str:
    parts = []
    kipris_evidence = str(item.get("kipris_evidence") or "").strip()
    if kipris_evidence:
        parts.append(
            f"""<div class="detail-label">KIPRIS 근거</div>
      <div class="detail-text">{esc(report_tone(kipris_evidence))}</div>"""
        )

    sources = output_sources_for_item(item)
    if sources:
        parts.append(
            f"""<div class="detail-label">출처</div>
      {render_evidence_links(sources, prefix="출처")}"""
        )
    else:
        parts.append("""<div class="detail-label">출처</div>
      <div class="detail-text">별도 출처 없음</div>""")
    return "\n      ".join(parts)


def strongest_and_weakest_items(data: dict[str, Any], limit: int = 4) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = [item for item in output_score_items(data) if isinstance(item.get("score"), (int, float))]
    strongest = sorted(items, key=lambda item: float(item.get("score", 0)), reverse=True)[:limit]
    weakest = sorted(items, key=lambda item: float(item.get("score", 0)))[:limit]
    return strongest, weakest


def output_market_sentence(data: dict[str, Any]) -> str:
    market = data.get("market_growth") or {}
    if not isinstance(market, dict) or not market:
        return "시장 성장 데이터는 포함되어 있지 않습니다."
    sector = market.get("sector", "-")
    growth = market.get("growth_rate")
    score = market.get("score")
    if isinstance(growth, (int, float)):
        return f"{sector}의 5년 평균 성장률은 {growth:.2f}%이며, 시장 성장성 점수는 {score}/5입니다."
    return f"{sector} 기준 시장 성장성 점수는 {score}/5입니다."


def output_competition_sentence(data: dict[str, Any]) -> str:
    comp = data.get("kipris_competition") or {}
    if not isinstance(comp, dict) or not comp:
        return "KIPRIS 경쟁 출원인 표본 데이터는 포함되어 있지 않습니다."
    sampling = comp.get("sampling") or {}
    dist = comp.get("applicant_distribution") or {}
    competitors = dist.get("top_competitors") or {}
    top = ", ".join(f"{name}({count}건)" for name, count in list(competitors.items())[:3])
    rank = dist.get("input_applicant_rank")
    share = dist.get("input_applicant_share")
    sample_size = sampling.get("sample_size") or dist.get("sample_size")
    population = sampling.get("total_population") or dist.get("total_population")
    prefix = f"동일 IPC 등록 표본 {sample_size}건"
    if population:
        prefix += f"(전체 검색 {population}건)"
    if rank:
        prefix += f"에서 대상 출원인은 {rank}위, 표본 점유율 {share}%입니다"
    if top:
        prefix += f". 주요 경쟁 출원인은 {top}입니다."
    else:
        prefix += "."
    return prefix


def dimension_reason_sentence(dim: str, data: dict[str, Any], dim_summary: dict[str, dict[str, float | int]]) -> str:
    items = [item for item in output_score_items(data) if item.get("dim") == dim and isinstance(item.get("score"), (int, float))]
    if not items:
        return f"{dim}은 평가 항목이 없어 별도 판단이 어렵습니다."
    avg = float(dim_summary.get(dim, {}).get("average", 0))
    strong = sorted(items, key=lambda item: float(item.get("score", 0)), reverse=True)[0]
    weak = sorted(items, key=lambda item: float(item.get("score", 0)))[0]
    if strong is weak:
        return (
            f"{dim}은 {avg:.2f}/5점으로, {strong.get('item')}({strong.get('score')}/5)이 "
            f"'{summary_without_ellipsis(output_item_summary(strong))}' 근거로 평가되었습니다."
        )
    return (
        f"{dim}은 {avg:.2f}/5점이며, {strong.get('item')}({strong.get('score')}/5)은 "
        f"'{summary_without_ellipsis(output_item_summary(strong))}' 근거로 점수를 끌어올렸고, "
        f"{weak.get('item')}({weak.get('score')}/5)은 '{summary_without_ellipsis(output_item_summary(weak))}' 근거로 보수적으로 평가되었습니다."
    )


def summary_without_ellipsis(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text.rstrip(".…")


def first_sentences(value: Any, limit: int = 2) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected = [sentence for sentence in sentences if sentence][:limit]
    return " ".join(selected) or text


def project_summary_sentence(project: dict[str, Any]) -> str:
    if not project:
        return "사내 프로젝트 연계 데이터는 아직 포함되어 있지 않아 사업화 현황은 별도 확인이 필요합니다."
    status = project.get("commercialization_status") or "-"
    service = project.get("applied_business_service") or project.get("query") or "-"
    summary = project.get("summary") or ""
    return f"사내 프로젝트 현황은 '{service}'에 대해 사업화 여부가 '{status}'입니다. {summary}"


def similar_summary_sentence(similar_analysis: dict[str, Any]) -> str:
    if not similar_analysis:
        return "유사 특허 분석 데이터는 아직 포함되어 있지 않아 경쟁 권리 분포는 별도 확인이 필요합니다."
    ecosystem = similar_analysis.get("ecosystem_summary", {}) if isinstance(similar_analysis.get("ecosystem_summary"), dict) else {}
    total = ecosystem.get("total_similar_patents", 0)
    enforceable = ecosystem.get("enforceable_count", 0)
    pending = ecosystem.get("published_or_pending_count", 0)
    rejected = ecosystem.get("rejected_or_expired_count", 0)
    avg_citation = ecosystem.get("avg_citation_count")
    comment = first_sentences(similar_analysis.get("interpretation", {}).get("decision_comment", ""), limit=2)
    citation_text = "평균 피인용 수는 미수집입니다" if avg_citation is None else f"평균 피인용 수는 {avg_citation}건입니다"
    return (
        f"유사 특허는 상위 {total}건 중 등록/유지 {enforceable}건, 공개/심사중 {pending}건, "
        f"거절/소멸 {rejected}건으로 구성되며, {citation_text}. {comment}"
    )


def fallback_output_overall_summary(data: dict[str, Any], project: dict[str, Any] | None = None, similar_analysis: dict[str, Any] | None = None) -> str:
    dim_summary = output_dimension_summary(data)
    dims = output_dimension_order(data)
    overall = output_overall_average(data)
    dim_sentences = " ".join(dimension_reason_sentence(dim, data, dim_summary) for dim in dims)
    paragraphs = [
        f"{data.get('title', '-')}의 종합 평균 점수는 {overall:.2f}/5로 {output_grade(overall)} 수준입니다. {dim_sentences}",
        project_summary_sentence(project or {}),
        similar_summary_sentence(similar_analysis or {}),
    ]
    return "\n\n".join(report_tone(paragraph) for paragraph in paragraphs)


def render_overall_summary(summary: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", str(summary or "")) if part.strip()]
    if not paragraphs:
        return ""
    return "\n".join(f"<p>{esc(paragraph)}</p>" for paragraph in paragraphs)


def generate_output_overall_summary(data: dict[str, Any], project: dict[str, Any], similar_analysis: dict[str, Any], use_llm: bool) -> str:
    fallback = fallback_output_overall_summary(data, project, similar_analysis)
    if not use_llm:
        return fallback

    dim_summary = output_dimension_summary(data)
    strongest, weakest = strongest_and_weakest_items(data, limit=5)
    brief = {
        "patent_id": data.get("patent_id"),
        "title": data.get("title"),
        "dimension_summary": dim_summary,
        "overall_average": output_overall_average(data),
        "strong_items": strongest,
        "weak_items": weakest,
        "market_growth": data.get("market_growth"),
        "project_status": project,
        "similar_patent_analysis": {
            "ecosystem_summary": similar_analysis.get("ecosystem_summary", {}),
            "top_comparisons": similar_analysis.get("top_comparisons", [])[:3],
            "interpretation": similar_analysis.get("interpretation", {}),
        },
    }
    prompt = f"""아래 output JSON 기반 평가 결과를 보고, HTML 보고서의 '종합 의견' 문단을 작성하세요.

{json.dumps(brief, ensure_ascii=False, indent=2)}

요구사항:
- 기준별 점수, 사내 프로젝트 현황, 유사 특허 분석을 각각 별도 문단으로 나누어 총 3문단으로 작성하세요.
- 전체 6~8문장
- 기술성, 권리성, 시장성 및 사업성 점수가 왜 그렇게 나왔는지 구체 항목명과 수치를 포함하세요.
- 사내 프로젝트 활용 현황과 사업화 여부를 반드시 언급하세요.
- 유사 특허 분석의 등록/유지, 공개/심사중, 거절/소멸 분포와 상위 비교 특허의 의미를 반드시 언급하세요.
- 일반론 금지. 위 데이터에 있는 항목과 수치만 근거로 쓰세요.
- 문체는 반드시 '~합니다', '~입니다' 체로 통일하세요.
- 마크다운 금지."""
    return report_tone(call_llm(prompt, max_tokens=1200) or fallback)


def render_output_score_cards(data: dict[str, Any]) -> str:
    dim_summary = output_dimension_summary(data)
    cards = []
    overall = output_overall_average(data)
    card_values = [("종합", overall)] + [(dim, float(dim_summary[dim]["average"])) for dim in output_dimension_order(data)]
    for label, avg in card_values:
        value = score_5_to_100(avg)
        color = OUTPUT_CARD_COLORS.get(label, "#374151")
        cards.append(
            f"""      <div class="score-card" style="--card-color:{color}">
        <div class="score-card-label">{esc(label)}</div>
        <div class="score-card-value">{value}<span class="score-card-denom"> / 100</span></div>
        <div class="score-card-bar"><div class="score-card-bar-inner" style="width:{value}%"></div></div>
      </div>"""
        )
    return "\n".join(cards)


def render_output_eval_blocks(data: dict[str, Any]) -> str:
    dim_summary = output_dimension_summary(data)
    blocks = []
    for index, dim in enumerate(output_dimension_order(data), 1):
        items = [item for item in output_score_items(data) if item.get("dim") == dim]
        avg = float(dim_summary.get(dim, {}).get("average", 0))
        rows = []
        for row_index, item in enumerate(items, 1):
            score = item.get("score", "-")
            detail_id = f"eval-{index}-{row_index}"
            rows.append(
                f"""      <tr class="data-row" data-detail="{detail_id}">
        <td style="font-weight:750;">{esc(item.get("item", "-"))}</td>
        <td><span class="score-pill score-{esc(score)}">{esc(score)}/5</span></td>
        <td>{esc(method_label(item.get("method")))}</td>
        <td>{esc(output_item_summary(item))}</td>
        <td><button class="toggle-btn" id="btn-{detail_id}" type="button">▶</button></td>
      </tr>
      <tr class="detail-row" id="row-{detail_id}">
        <td colspan="5">
          <div class="detail-content" id="{detail_id}">
            <div class="detail-label">판단 근거</div>
            <div class="detail-text">{esc(output_item_basis(item))}</div>
            {render_output_item_source_detail(item)}
          </div>
        </td>
      </tr>"""
            )
        blocks.append(
            f"""  <div class="eval-block">
    <div class="eval-block-header"><span class="eval-block-title">3.{index} {esc(dim)}</span><span class="eval-block-score">{score_5_to_100(avg)} / 100</span></div>
    <table class="eval-table">
      <thead><tr><th style="width:180px">평가 항목</th><th style="width:72px">점수</th><th style="width:105px">산출 방식</th><th>판단 요지</th><th style="width:32px"></th></tr></thead>
      <tbody>
{chr(10).join(rows)}
      </tbody>
    </table>
  </div>"""
        )
    return "\n\n".join(blocks)


def project_file_for(data: dict[str, Any], input_path: Path) -> Path:
    patent_id = str(data.get("patent_id") or input_path.stem.replace("patent_", "").replace("_output", ""))
    normalized = patent_id.replace("-", "_")
    return input_path.parent / f"project_{normalized}.json"


def load_project_data(data: dict[str, Any], input_path: Path) -> dict[str, Any]:
    path = project_file_for(data, input_path)
    if path.exists():
        project = load_json(path)
        project["_source_path"] = path.as_posix()
        return project
    return {}


def similar_file_for(data: dict[str, Any], input_path: Path) -> Path:
    patent_id = str(data.get("patent_id") or input_path.stem.replace("patent_", "").replace("_output", ""))
    normalized = patent_id.replace("-", "_")
    return input_path.parent / f"similar_analysis_{normalized}.json"


def load_similar_analysis(data: dict[str, Any], input_path: Path) -> dict[str, Any]:
    path = similar_file_for(data, input_path)
    if path.exists():
        analysis = load_json(path)
        analysis["_source_path"] = path.as_posix()
        return analysis
    return {}


def render_output_project_summary(project: dict[str, Any]) -> str:
    if not project:
        return """    <div class="project-summary-list">
      <a class="project-summary-card" href="#sec2">
        <div>
          <div class="project-summary-name">사내 프로젝트 연계 데이터 없음</div>
          <div class="project-summary-dept">output JSON에 프로젝트 RAG 결과 미포함</div>
        </div>
        <span class="project-status status-done">미수집</span>
      </a>
    </div>"""

    service = project.get("applied_business_service") or project.get("query") or "-"
    status = project.get("commercialization_status") or "-"
    sources = project.get("sources") or []
    return f"""    <div class="project-summary-list">
      <a class="project-summary-card" href="#sec2">
        <div>
          <div class="project-summary-name">{esc(service)}</div>
          <div class="project-summary-dept">{esc(project.get("summary", "-"))}</div>
        </div>
        <span class="project-status status-done">{esc(status)}</span>
      </a>
    </div>"""


def build_project_narrative(project: dict[str, Any]) -> str:
    status = project.get("commercialization_status") or "-"
    service = project.get("applied_business_service") or project.get("query") or "-"
    history = project.get("business_application_history") or "-"
    customers = project.get("customers_partners") or "-"
    summary = project.get("summary") or ""
    market_outlook = project.get("market_outlook") or ""
    signals = [str(signal).strip() for signal in project.get("commercialization_signals") or [] if str(signal).strip()]
    sources = []
    for source in project.get("sources") or []:
        if not isinstance(source, dict):
            continue
        title = str(source.get("title") or "").strip()
        if title and title not in sources:
            sources.append(title)

    parts = [
        f"RAG 검색 결과, 이 특허와 연결되는 사내 활용 영역은 '{service}'이며 사업화 상태는 '{status}'입니다.",
    ]
    if summary:
        parts.append(summary)
    if history != "-" or customers != "-":
        parts.append(f"사업 적용 이력은 '{history}', 고객·파트너는 '{customers}'로 확인됩니다.")
    if signals:
        parts.append(f"사업화 신호는 {', '.join(signals[:4])}입니다.")
    if market_outlook:
        parts.append(market_outlook)
    if sources:
        parts.append(f"근거 문서로는 {', '.join(sources[:3])} 등이 사용되었습니다.")
    return report_tone(" ".join(parts))


def render_output_project_section(project: dict[str, Any]) -> str:
    if not project:
        return """  <div class="empty-state">
    <div class="empty-state-title">사내 프로젝트 연계 데이터 없음</div>
    <div class="empty-state-desc">현재 output JSON에는 사내 프로젝트 RAG 검색 결과가 포함되어 있지 않습니다. 프로젝트 연계 결과가 제공되면 동일 섹션에 카드 형태로 렌더링됩니다.</div>
  </div>"""

    signals = project.get("commercialization_signals") or []
    signal_text = ", ".join(str(signal) for signal in signals) if signals else "-"
    rows = [
        ("사업화 여부", project.get("commercialization_status")),
        ("적용 사업·서비스", project.get("applied_business_service")),
        ("사업 적용 이력", project.get("business_application_history")),
        ("고객·파트너", project.get("customers_partners")),
        ("사업화 신호", signal_text),
    ]
    table_rows = "\n".join(
        f"""      <tr><th style="width:150px">{esc(label)}</th><td>{esc(value or "-")}</td></tr>"""
        for label, value in rows
    )
    source_links = []
    seen_sources = set()
    for source in project.get("sources") or []:
        title = str(source.get("title") or "-").strip()
        url = str(source.get("url") or "").strip()
        source_key = (title, url)
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        source_links.append({"title": title, "url": url})
    sources_html = render_evidence_links(source_links, prefix="근거")
    project_narrative = build_project_narrative(project)

    return f"""  <table class="patent-table" style="margin-bottom:16px;">
    <tbody>
{table_rows}
    </tbody>
  </table>
  <div class="project-card">
    <div class="project-name">요약 설명</div>
    <div class="project-desc" style="margin-bottom:0;">{esc(project_narrative)}</div>
  </div>
  <div class="project-card">
    <div class="project-name">근거 자료</div>
    <div class="project-desc" style="margin-bottom:0;">{sources_html}</div>
  </div>"""


def similar_metric(item: dict[str, Any], key: str, missing: str = "-") -> str:
    value = item.get(key)
    if value in (None, ""):
        source = item.get("source_detail", {}) if isinstance(item.get("source_detail"), dict) else {}
        candidate = source.get("source_candidate", {}) if isinstance(source.get("source_candidate"), dict) else {}
        value = source.get(key) or candidate.get(key)
    return missing if value in (None, "") else str(value)


def kipris_similarity_for(item: dict[str, Any]) -> str:
    value = kipris_similarity_value(item)
    if value is None:
        return "-"
    return f"{value:.2f}"


def kipris_similarity_value(item: dict[str, Any]) -> float | None:
    source = item.get("source_detail", {}) if isinstance(item.get("source_detail"), dict) else {}
    candidate = source.get("source_candidate", {}) if isinstance(source.get("source_candidate"), dict) else {}
    similarity = item.get("similarity", {}) if isinstance(item.get("similarity"), dict) else {}
    value = (
        item.get("similarity_score")
        or source.get("similarity_score")
        or candidate.get("similarity_score")
        or similarity.get("kipris")
    )
    if value in (None, ""):
        basis = item.get("similarity_basis") or source.get("similarity_basis") or candidate.get("similarity_basis")
        match = re.search(r"\d+(?:\.\d+)?", str(basis or ""))
        value = match.group(0) if match else None
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def sort_by_kipris_similarity(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            kipris_similarity_value(item) is None,
            -(kipris_similarity_value(item) or -1),
            item.get("analysis_rank") or item.get("rank") or 999,
        ),
    )


def application_year_for_similar(item: dict[str, Any]) -> str:
    for value in (
        similar_metric(item, "application_year", ""),
        similar_metric(item, "application_date", ""),
    ):
        match = re.search(r"(19|20)\d{2}", str(value or ""))
        if match:
            return match.group(0)
    return "-"


def citation_text(value: Any) -> str:
    return "미수집" if value in (None, "") else str(value)


def render_output_similar_summary(analysis: dict[str, Any]) -> str:
    if not analysis:
        return """    <div class="patent-summary-wrap">
      <div class="patent-summary-stats">
        <div class="patent-summary-stat"><span class="patent-summary-num" style="color:var(--accent)">-</span><span class="patent-summary-label">분석 대상</span></div>
        <div class="patent-summary-stat"><span class="patent-summary-num" style="color:var(--positive)">-</span><span class="patent-summary-label">등록/유지</span></div>
        <div class="patent-summary-stat"><span class="patent-summary-num" style="color:var(--neutral)">-</span><span class="patent-summary-label">공개/심사중</span></div>
        <div class="patent-summary-stat"><span class="patent-summary-num" style="color:var(--text-muted)">-</span><span class="patent-summary-label">거절/소멸</span></div>
      </div>
      <div style="padding:14px 18px;font-size:13px;color:var(--text-secondary);border-top:1px solid var(--border);line-height:1.7;">
        output JSON에는 유사 특허 상위 10건의 권리상태 분포 데이터가 포함되어 있지 않습니다.
      </div>
    </div>"""

    ecosystem = analysis.get("ecosystem_summary", {}) if isinstance(analysis.get("ecosystem_summary"), dict) else {}
    total = ecosystem.get("total_similar_patents", 0)
    enforceable = ecosystem.get("enforceable_count", 0)
    pending = ecosystem.get("published_or_pending_count", 0)
    rejected = ecosystem.get("rejected_or_expired_count", 0)
    avg_citation = ecosystem.get("avg_citation_count")
    ratio = ecosystem.get("enforceable_ratio")
    ratio_text = f"{round(float(ratio) * 100)}%" if isinstance(ratio, (int, float)) else "-"
    avg_citation_text = "-" if avg_citation is None else str(avg_citation)
    return f"""    <div class="patent-summary-wrap">
      <div class="patent-summary-stats">
        <div class="patent-summary-stat"><span class="patent-summary-num" style="color:var(--accent)">{esc(total)}</span><span class="patent-summary-label">분석 대상</span></div>
        <div class="patent-summary-stat"><span class="patent-summary-num" style="color:var(--positive)">{esc(enforceable)}</span><span class="patent-summary-label">등록/유지</span></div>
        <div class="patent-summary-stat"><span class="patent-summary-num" style="color:var(--neutral)">{esc(pending)}</span><span class="patent-summary-label">공개/심사중</span></div>
        <div class="patent-summary-stat"><span class="patent-summary-num" style="color:var(--text-muted)">{esc(rejected)}</span><span class="patent-summary-label">거절/소멸</span></div>
        <div class="patent-summary-stat"><span class="patent-summary-num" style="color:var(--neutral)">{esc(avg_citation_text)}</span><span class="patent-summary-label">평균 피인용 수</span></div>
      </div>
      <div style="padding:14px 18px;font-size:13px;color:var(--text-secondary);border-top:1px solid var(--border);line-height:1.7;">
        유사 특허 상위 {esc(total)}건 중 {esc(ratio_text)}가 등록/유지 중입니다.
      </div>
    </div>"""


def render_similar_comparison_cards(analysis: dict[str, Any]) -> str:
    cards = []
    for display_rank, item in enumerate(sort_by_kipris_similarity(analysis.get("top_comparisons") or []), 1):
        comparison = item.get("comparison", {}) if isinstance(item.get("comparison"), dict) else {}
        technical = comparison.get("technical_analysis", {}) if isinstance(comparison.get("technical_analysis"), dict) else {}
        title = item.get("title") or "-"
        status = status_label(item.get("legal_status"))
        applicant = clean_applicant_name(item.get("applicant"))
        application_number = item.get("application_number") or similar_metric(item, "application_number")
        citation = citation_text(item.get("citation_count"))
        summary = comparison.get("summary") or "-"
        overlap = technical.get("technical_overlap") or "-"
        difference = technical.get("technical_difference") or "-"
        scope = technical.get("scope_comparison") or "-"
        implication = technical.get("maintenance_implication") or "-"
        cards.append(
            f"""  <div class="project-card">
    <div class="project-card-top">
      <div>
        <div class="project-name">#{esc(display_rank)} {esc(title)}</div>
        <div class="comparison-meta">
          <span>{esc(applicant)}</span>
          <span>{esc(status)}</span>
          <span>출원번호 {esc(application_number)}</span>
          <span>피인용 {esc(citation)}</span>
        </div>
      </div>
      <span class="project-status status-done">유사도 {esc(kipris_similarity_for(item))}</span>
    </div>
    <div class="project-desc">{esc(report_tone(summary))}</div>
    <div class="project-detail"><b>기술적으로 겹치는 부분:</b> {esc(report_tone(overlap))}<br><b>기술적 차이:</b> {esc(report_tone(difference))}<br><b>청구범위 관점:</b> {esc(report_tone(scope))}<br><b>유지 판단 시사점:</b> {esc(report_tone(implication))}</div>
  </div>"""
        )
    return "\n".join(cards)


def render_similar_patent_rows(analysis: dict[str, Any]) -> str:
    rows = []
    patents = sort_by_kipris_similarity(analysis.get("similar_patents") or [])
    for item in patents:
        status = status_label(item.get("legal_status"))
        rows.append(
            f"""      <tr>
        <td>{esc(item.get("application_number") or similar_metric(item, "application_number"))}</td>
        <td>{esc(item.get("title", "-"))}</td>
        <td>{esc(clean_applicant_name(item.get("applicant")))}</td>
        <td>{esc(application_year_for_similar(item))}</td>
        <td>{esc(kipris_similarity_for(item))}</td>
        <td>{esc(citation_text(item.get("citation_count")))}</td>
        <td><span class="{status_class(item.get("legal_status"))}">{esc(status)}</span></td>
      </tr>"""
        )
    return "\n".join(rows)


def render_output_similar_section(analysis: dict[str, Any]) -> str:
    if not analysis:
        return """  <div class="empty-state">
    <div class="empty-state-title">유사 특허 상세 데이터 없음</div>
    <div class="empty-state-desc">현재 output JSON에는 유사 특허 상위 10건 목록과 상위 3건 비교 분석 결과가 포함되어 있지 않습니다. 해당 데이터가 output 구조에 추가되면 기존 유사 특허 분석 섹션에 그대로 렌더링할 수 있습니다.</div>
  </div>"""

    ecosystem = analysis.get("ecosystem_summary", {}) if isinstance(analysis.get("ecosystem_summary"), dict) else {}
    total = ecosystem.get("total_similar_patents", len(analysis.get("similar_patents") or []))
    enforceable = ecosystem.get("enforceable_count", 0)
    rejected = ecosystem.get("rejected_or_expired_count", 0)
    avg_citation = ecosystem.get("avg_citation_count")
    avg_citation_text = "-" if avg_citation is None else str(avg_citation)
    comment = analysis.get("interpretation", {}).get("decision_comment") or "유사 특허 분석 결과가 생성되었으나 결론 문단은 비어 있습니다."
    return f"""  <div class="sec4-stat-row">
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--accent)">{esc(total)}</span><span class="sec4-stat-label">분석 대상</span></div>
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--positive)">{esc(enforceable)}</span><span class="sec4-stat-label">등록/유지</span></div>
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--text-muted)">{esc(rejected)}</span><span class="sec4-stat-label">거절/소멸</span></div>
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--neutral)">{esc(avg_citation_text)}</span><span class="sec4-stat-label">평균 피인용 수</span></div>
  </div>
{render_similar_comparison_cards(analysis)}
  <table class="patent-table">
    <thead><tr><th>출원번호</th><th>특허명</th><th>출원인</th><th>출원연도</th><th>KIPRIS 유사도</th><th>피인용 수</th><th>상태</th></tr></thead>
    <tbody>
{render_similar_patent_rows(analysis)}
    </tbody>
  </table>
  <div class="opinion-box" style="margin-top:16px;">{esc(report_tone(comment))}</div>"""


def render_output_confirm_items(data: dict[str, Any]) -> str:
    _, weakest = strongest_and_weakest_items(data, limit=6)
    items = []
    for item in weakest:
        reason = output_item_basis(item)
        items.append(
            f"""  <div class="confirm-item">
    <div class="confirm-item-title">{esc(item.get("item", "-"))} <span>{esc(item.get("dim", "-"))} · {esc(item.get("score", "-"))}/5</span></div>
    <div class="confirm-item-desc">{esc(reason)}</div>
  </div>"""
        )
    if not items:
        return '<div class="confirm-item"><div class="confirm-item-title">추가 확인 필요 항목 없음</div><div class="confirm-item-desc">현재 평가 데이터 기준 추가 확인 필요 항목이 없습니다.</div></div>'
    return "\n".join(items)


def render_output_market_section(data: dict[str, Any]) -> str:
    market = data.get("market_growth") or {}
    if not isinstance(market, dict) or not market:
        return '<div class="empty-state"><div class="empty-state-title">시장 성장 데이터 없음</div><div class="empty-state-desc">output JSON에 market_growth가 포함되어 있지 않습니다.</div></div>'
    rows = []
    values = [row.get("값") for row in market.get("data", []) if isinstance(row, dict) and isinstance(row.get("값"), (int, float))]
    max_value = max(values) if values else 0
    for row in market.get("data", []) or []:
        year = row.get("연도", "-")
        value = row.get("값")
        width = round(float(value) / max_value * 100) if isinstance(value, (int, float)) and max_value else 0
        value_text = f"{float(value):,.0f}" if isinstance(value, (int, float)) else "-"
        rows.append(
            f"""      <tr>
        <td>{esc(year)}</td>
        <td>{esc(value_text)}</td>
        <td><div class="score-card-bar"><div class="score-card-bar-inner" style="width:{width}%"></div></div></td>
      </tr>"""
        )
    return f"""  <div class="sec4-stat-row">
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--accent)">{esc(market.get("score", "-"))}</span><span class="sec4-stat-label">시장 성장성 점수</span></div>
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--positive)">{esc(market.get("growth_rate", "-"))}%</span><span class="sec4-stat-label">5년 평균 성장률</span></div>
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--neutral)">{esc(market.get("c2_code", "-"))}</span><span class="sec4-stat-label">{esc(market.get("sector", "-"))}</span></div>
  </div>
  <p style="font-size:13px;color:var(--text-secondary);margin-bottom:14px;">{esc(output_market_sentence(data))} 데이터 매핑 근거는 {esc(market.get("source_field", "-"))}입니다.</p>
  <table class="patent-table">
    <thead><tr><th style="width:90px">연도</th><th style="width:160px">값</th><th>상대 규모</th></tr></thead>
    <tbody>
{chr(10).join(rows)}
    </tbody>
  </table>"""


def render_output_competition_section(data: dict[str, Any]) -> str:
    comp = data.get("kipris_competition") or {}
    if not isinstance(comp, dict) or not comp:
        return '<div class="empty-state"><div class="empty-state-title">KIPRIS 경쟁 표본 데이터 없음</div><div class="empty-state-desc">이 output JSON에는 kipris_competition 결과가 포함되어 있지 않습니다.</div></div>'
    sampling = comp.get("sampling") or {}
    dist = comp.get("applicant_distribution") or {}
    rows = []
    for name, count in list((dist.get("top_competitors") or {}).items())[:10]:
        rows.append(f"      <tr><td>{esc(name)}</td><td>{esc(count)}건</td></tr>")
    return f"""  <div class="sec4-stat-row">
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--accent)">{esc(sampling.get("total_population", "-"))}</span><span class="sec4-stat-label">전체 검색 건수</span></div>
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--positive)">{esc(sampling.get("sample_size", dist.get("sample_size", "-")))}</span><span class="sec4-stat-label">등록 표본</span></div>
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--neutral)">{esc(dist.get("input_applicant_rank", "-"))}</span><span class="sec4-stat-label">대상 출원인 순위</span></div>
    <div class="sec4-stat"><span class="sec4-stat-num" style="color:var(--text-muted)">{esc(dist.get("input_applicant_share", "-"))}%</span><span class="sec4-stat-label">대상 출원인 점유율</span></div>
  </div>
  <div class="opinion-box" style="margin-bottom:16px;">{esc(output_competition_sentence(data))}</div>
  <table class="patent-table">
    <thead><tr><th>주요 경쟁 출원인</th><th style="width:120px">등록 표본 건수</th></tr></thead>
    <tbody>
{chr(10).join(rows)}
    </tbody>
  </table>"""


def build_output_refs(
    data: dict[str, Any],
    today_str: str,
    project: dict[str, Any] | None = None,
    similar_analysis: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for source in data.get("llm_sources") or []:
        if not isinstance(source, dict):
            continue
        title = str(source.get("title") or "").strip()
        url = str(source.get("url") or "").strip()
        if not title or (title, url) in seen:
            continue
        refs.append({"title": title, "src": str(source.get("published_date") or "").strip(), "url": url})
        seen.add((title, url))
    for source in (project or {}).get("sources") or []:
        if not isinstance(source, dict):
            continue
        title = str(source.get("title") or "").strip()
        url = str(source.get("url") or "").strip()
        if not title or (title, url) in seen:
            continue
        refs.append({"title": title, "src": "사내 프로젝트 RAG 근거", "url": url})
        seen.add((title, url))
    if similar_analysis:
        title = f"KIPRIS 유사 특허 분석 결과: {similar_analysis.get('meta', {}).get('target_patent_id', data.get('patent_id', '-'))}"
        if (title, "") not in seen:
            refs.append({"title": title, "src": "", "url": ""})
    return refs


def output_filename_for(data: dict[str, Any]) -> str:
    patent_id = re.sub(r"[^0-9A-Za-z가-힣-]+", "-", str(data.get("patent_id") or "report")).strip("-")
    return f"ip_valuation_report_{patent_id}.html"


def generate_report_from_output_json(
    input_json: str | Path,
    output_path: str | Path | None = None,
    output_dir: str | Path = ARTIFACT_REPORT_DIR,
    use_llm: bool = True,
) -> Path:
    """평가 output JSON 1개를 독립 실행형 HTML 파일로 렌더링합니다.

    기존 프로토타입 산출물이 계속 동작하도록 프로젝트/유사 특허 산출물을 파일명
    규칙으로 로드합니다. 실제 서버로 이동할 때는 보고서 생성 서비스가 관련
    데이터셋을 명시적으로 전달하는 구조가 좋습니다.
    """
    input_path = Path(input_json)
    data = load_json(input_path)
    today_str = date.today().strftime("%Y.%m.%d")
    project = load_project_data(data, input_path)
    similar_analysis = load_similar_analysis(data, input_path)
    input_meta: dict[str, Any] = {}
    linked_input = data.get("input_file")
    if linked_input:
        linked_path = Path(str(linked_input))
        if linked_path.exists():
            input_meta = load_json(linked_path)

    meta = input_meta.get("meta", {}) if isinstance(input_meta.get("meta"), dict) else {}
    legal = input_meta.get("legal", {}) if isinstance(input_meta.get("legal"), dict) else {}
    title = data.get("title") or meta.get("title") or "-"
    patent_id = data.get("patent_id") or input_meta.get("patent_id") or "-"
    application_date = meta.get("application_date") or "-"
    registration_date = meta.get("registration_date") or legal.get("registration_date") or "-"
    ipc = join_list(meta.get("ipc", []))
    description = input_meta.get("description_summary") or "입력 특허 전문 요약 데이터가 output JSON에 포함되어 있지 않습니다."
    overall_summary = generate_output_overall_summary(data, project, similar_analysis, use_llm=use_llm)
    refs = build_output_refs(data, today_str, project, similar_analysis)
    output = Path(output_path) if output_path else Path(output_dir) / output_filename_for(data)
    output.parent.mkdir(parents=True, exist_ok=True)

    html_text = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IP 가치 평가 보고서 - 제{esc(patent_id)}호</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=DM+Mono:wght@400;500&display=swap');
  :root {{
    --bg:#f3f6f9; --surface:#ffffff; --surface2:#f6f7f9; --border:#e5e7eb; --table-border:#d9dee7;
    --text-primary:#111827; --text-secondary:#4b5563; --text-muted:#6b7280;
    --accent:#111827; --accent-light:#f6f8fb; --positive:#166534; --positive-bg:#ecfdf3;
    --neutral:#854d0e; --neutral-bg:#fffbeb; --negative:#991b1b; --negative-bg:#fef2f2;
    --shadow:0 1px 2px rgba(17,24,39,0.05);
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Noto Sans KR',sans-serif; background:var(--bg); color:var(--text-primary); font-size:13px; line-height:1.7; }}
  .report-header {{ background:var(--surface); padding:28px 32px 24px; border:1px solid var(--border); border-radius:14px; box-shadow:var(--shadow); }}
  .report-meta {{ font-size:12px; color:var(--text-muted); margin-bottom:8px; font-weight:800; }}
  .report-title {{ font-size:20px; font-weight:850; letter-spacing:-0.02em; margin-bottom:4px; }}
  .report-subtitle {{ font-size:12px; color:var(--text-muted); margin-bottom:22px; }}
  .report-info-row {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
  .report-info-item {{ display:flex; flex-direction:column; gap:4px; padding:12px; border:1px solid var(--border); border-radius:10px; background:var(--surface2); min-width:0; }}
  .report-info-label {{ font-size:11px; color:var(--text-muted); font-weight:800; }}
  .report-info-value {{ font-size:12px; font-weight:750; color:var(--text-primary); overflow-wrap:anywhere; }}
  .toc-bar {{ background:rgba(255,255,255,0.96); border:1px solid var(--border); border-radius:12px; margin-top:12px; padding:0 10px; display:flex; position:sticky; top:0; z-index:100; overflow-x:auto; box-shadow:var(--shadow); }}
  .toc-item {{ padding:12px 10px; font-size:12px; font-weight:750; color:var(--text-muted); cursor:pointer; border-bottom:2px solid transparent; transition:all 0.15s; white-space:nowrap; text-decoration:none; }}
  .toc-item:hover {{ color:var(--text-primary); border-bottom-color:#9ca3af; }}
  .report-body {{ max-width:none; margin:0 auto; padding:12px 0; }}
  .section {{ margin-bottom:18px; padding:22px; border:1px solid var(--border); border-radius:14px; background:var(--surface); box-shadow:var(--shadow); }}
  .section-header {{ display:flex; align-items:baseline; gap:10px; margin-bottom:20px; padding-bottom:12px; border-bottom:1px solid var(--border); }}
  .section-num {{ font-family:'DM Mono',monospace; font-size:11px; color:var(--text-muted); font-weight:700; letter-spacing:0.08em; }}
  .section-title {{ font-size:17px; font-weight:850; letter-spacing:-0.01em; }}
  .subsection {{ margin-bottom:28px; }}
  .subsection:last-child {{ margin-bottom:0; }}
  .subsection-title {{ font-size:13px; font-weight:800; color:var(--text-primary); letter-spacing:0; margin-bottom:14px; }}
  .score-cards {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
  .score-card {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:18px 16px 16px; display:flex; flex-direction:column; gap:10px; position:relative; overflow:hidden; }}
  .score-card-label {{ font-size:11px; font-weight:700; color:var(--text-muted); letter-spacing:0.08em; }}
  .score-card-value {{ font-size:26px; font-weight:800; font-family:'DM Mono',monospace; color:var(--card-color,var(--accent)); line-height:1; }}
  .score-card-denom {{ font-size:13px; font-weight:400; color:var(--text-muted); }}
  .score-card-bar {{ height:4px; background:#e5e7eb; border-radius:2px; overflow:hidden; }}
  .score-card-bar-inner {{ height:100%; border-radius:2px; background:var(--card-color,var(--accent)); }}
  .project-summary-list {{ display:flex; flex-direction:column; gap:8px; }}
  .project-summary-card {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 18px; display:flex; align-items:center; justify-content:space-between; gap:16px; text-decoration:none; color:inherit; }}
  .project-summary-name {{ font-size:14px; font-weight:700; margin-bottom:2px; }}
  .project-summary-dept {{ font-size:12px; color:var(--text-muted); }}
  .patent-summary-wrap {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; overflow:hidden; }}
  .patent-summary-stats {{ display:flex; gap:0; border-bottom:1px solid var(--border); }}
  .patent-summary-stat {{ flex:1; padding:14px 18px; display:flex; flex-direction:column; gap:2px; border-right:1px solid var(--border); }}
  .patent-summary-stat:last-child {{ border-right:none; }}
  .patent-summary-num {{ font-size:24px; font-weight:700; font-family:'DM Mono',monospace; line-height:1; }}
  .patent-summary-label {{ font-size:11px; color:var(--text-muted); }}
  .opinion-box {{ background:var(--accent-light); border:1px solid var(--border); border-left:3px solid #6b7280; border-radius:10px; padding:16px 18px; font-size:14px; line-height:1.85; }}
  .opinion-box p {{ margin:0 0 12px; }}
  .opinion-box p:last-child {{ margin-bottom:0; }}
  .project-card {{ background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px 18px; margin-bottom:12px; }}
  .project-card-top {{ display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:12px; }}
  .project-name {{ font-size:15px; font-weight:800; line-height:1.45; margin-bottom:6px; }}
  .project-desc {{ font-size:13px; color:var(--text-primary); line-height:1.75; margin-bottom:10px; }}
  .project-detail {{ font-size:12px; color:var(--text-secondary); line-height:1.7; padding-top:10px; border-top:1px solid var(--border); }}
  .comparison-meta {{ display:flex; flex-wrap:wrap; gap:6px; font-size:12px; color:var(--text-secondary); }}
  .comparison-meta span {{ padding:3px 7px; background:var(--surface2); border:1px solid var(--border); border-radius:6px; line-height:1.4; }}
  .project-status {{ font-size:11px; font-weight:700; letter-spacing:0.06em; padding:4px 10px; border-radius:20px; white-space:nowrap; }}
  .status-done {{ background:var(--surface2); color:var(--text-muted); }}
  .eval-block {{ margin-bottom:32px; }}
  .eval-block-header {{ background:#374151; color:#fff; padding:10px 14px; border:1px solid #374151; border-bottom:0; border-radius:10px 10px 0 0; display:flex; justify-content:space-between; align-items:center; }}
  .eval-block-title {{ font-size:13px; font-weight:700; }}
  .eval-block-score {{ font-family:'DM Mono',monospace; font-size:17px; font-weight:700; }}
  .eval-table {{ width:100%; border-collapse:collapse; border:1px solid var(--border); border-top:none; background:var(--surface); }}
  .eval-table thead tr {{ background:#f9fafb; }}
  .eval-table th {{ padding:9px 14px; text-align:left; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-muted); border-bottom:1px solid var(--border); }}
  .eval-table td {{ padding:10px 14px; vertical-align:top; border-bottom:1px solid var(--border); font-size:12px; }}
  .eval-table tr.data-row {{ cursor:pointer; transition:background 0.1s; }}
  .eval-table tr.data-row:hover {{ background:var(--surface2); }}
  .eval-table tr.detail-row {{ display:none; }}
  .eval-table tr.detail-row.open {{ display:table-row; }}
  .eval-table tr.detail-row td {{ padding:0; border-bottom:1px solid var(--border); }}
  .toggle-btn {{ background:none; border:none; cursor:pointer; color:var(--text-muted); font-size:12px; padding:2px 4px; transition:transform 0.2s; display:inline-block; }}
  .toggle-btn.open {{ transform:rotate(90deg); }}
  .detail-content {{ display:none; padding:18px 22px; background:var(--accent-light); border-top:1px solid var(--border); }}
  .detail-content.open {{ display:block; }}
  .detail-label {{ font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:var(--text-muted); margin-bottom:6px; margin-top:14px; font-family:'DM Mono',monospace; }}
  .detail-label:first-child {{ margin-top:0; }}
  .detail-text {{ font-size:12px; color:var(--text-primary); line-height:1.85; white-space:pre-wrap; }}
  .score-pill {{ display:inline-block; font-family:'DM Mono',monospace; font-size:12px; font-weight:700; padding:3px 9px; border-radius:5px; white-space:nowrap; }}
  .score-5 {{ background:#e8f5ed; color:#1a6e3c; }}
  .score-4 {{ background:#eef5e8; color:#3a6e1a; }}
  .score-3 {{ background:#fdf8e1; color:#7a6a00; }}
  .score-2 {{ background:#fdeaea; color:#8b1a1a; }}
  .score-1 {{ background:#f5e0e0; color:#6e1a1a; }}
  .sec4-stat-row {{ display:flex; background:var(--surface); border:1px solid var(--border); border-radius:10px; overflow:hidden; margin-bottom:16px; }}
  .sec4-stat {{ flex:1; padding:16px 20px; display:flex; flex-direction:column; gap:2px; border-right:1px solid var(--border); min-width:0; }}
  .sec4-stat:last-child {{ border-right:none; }}
  .sec4-stat-num {{ font-size:26px; font-weight:700; font-family:'DM Mono',monospace; line-height:1; overflow-wrap:anywhere; }}
  .sec4-stat-label {{ font-size:11px; color:var(--text-muted); overflow-wrap:anywhere; }}
  .patent-table {{ width:100%; border-collapse:collapse; background:var(--surface); border:1px solid var(--table-border); }}
  .patent-table th {{ padding:10px 14px; text-align:left; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-muted); background:var(--surface2); border:1px solid var(--table-border); }}
  .patent-table td {{ padding:11px 14px; font-size:13px; border:1px solid var(--table-border); vertical-align:middle; }}
  .status-keep {{ color:var(--positive); font-weight:700; font-size:11px; white-space:nowrap; }}
  .status-expired {{ color:var(--text-muted); font-size:11px; white-space:nowrap; }}
  .confirm-item {{ background:var(--surface); border:1px solid var(--border); border-left:3px solid var(--negative); border-radius:0 8px 8px 0; padding:14px 18px; margin-bottom:10px; }}
  .confirm-item-title {{ font-size:13px; font-weight:700; margin-bottom:4px; }}
  .confirm-item-title span {{ color:var(--text-muted); font-weight:400; font-size:12px; margin-left:8px; }}
  .confirm-item-desc {{ font-size:13px; color:var(--text-secondary); line-height:1.65; }}
  .empty-state {{ background:var(--surface); border:1px dashed var(--border); border-radius:10px; padding:24px; }}
  .empty-state-title {{ font-size:14px; font-weight:800; margin-bottom:4px; }}
  .empty-state-desc {{ font-size:12px; color:var(--text-secondary); }}
  .evidence-list {{ list-style:decimal; display:flex; flex-direction:column; gap:5px; margin:0; padding-left:18px; }}
  .evidence-list li {{ margin:0; padding-left:2px; color:var(--text-muted); }}
  .evidence-link {{ color:#315f8d; text-decoration:underline; text-underline-offset:3px; font-size:12px; font-weight:400; line-height:1.55; overflow-wrap:anywhere; }}
  .evidence-link:hover {{ color:#244a72; }}
  .ref-list {{ list-style:none; }}
  .ref-list li {{ padding:10px 0; border-bottom:1px solid var(--border); font-size:13px; color:var(--text-secondary); display:flex; gap:10px; align-items:flex-start; }}
  .ref-num {{ font-family:'DM Mono',monospace; font-size:11px; font-weight:500; color:var(--text-muted); min-width:34px; padding-top:1px; }}
  .ref-link {{ font-size:12px; color:#315f8d; text-decoration:underline; text-underline-offset:3px; font-weight:400; }}
  .ref-link:hover {{ color:#244a72; }}
  .footnote-bar {{ border-top:1px solid var(--border); margin-top:12px; padding-top:12px; font-size:11px; color:var(--text-muted); display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; }}
  @media (max-width:760px) {{
    .report-header {{ padding:28px 20px 24px; }}
    .report-body {{ padding:24px 16px 12px; }}
    .report-info-row, .score-cards {{ grid-template-columns:1fr; }}
    .patent-summary-stats, .sec4-stat-row {{ flex-direction:column; }}
  }}
</style>
</head>
<body>
<div class="report-header">
  <div class="report-meta">IP 가치 평가 보고서 · Legal AI1팀</div>
  <div class="report-title">{esc(title)}</div>
  <div class="report-subtitle">특허번호 제{esc(patent_id)}호</div>
  <div class="report-info-row">
    <div class="report-info-item"><span class="report-info-label">출원일</span><span class="report-info-value">{esc(fmt_date(application_date))}</span></div>
    <div class="report-info-item"><span class="report-info-label">등록일</span><span class="report-info-value">{esc(fmt_date(registration_date))}</span></div>
    <div class="report-info-item"><span class="report-info-label">IPC 분류</span><span class="report-info-value">{esc(ipc)}</span></div>
    <div class="report-info-item"><span class="report-info-label">평가 기준일</span><span class="report-info-value">{esc(today_str)}</span></div>
  </div>
</div>

<nav class="toc-bar">
  <a class="toc-item" href="#sec1">1. 평가 요약</a>
  <a class="toc-item" href="#sec2">2. 기준별 점수</a>
  <a class="toc-item" href="#sec3">3. 사내 프로젝트</a>
  <a class="toc-item" href="#sec4">4. 유사 특허</a>
  <a class="toc-item" href="#sec5">5. 추가 확인</a>
  <a class="toc-item" href="#sec6">6. 참고문헌</a>
</nav>

<div class="report-body">
<section class="section" id="sec1">
  <div class="section-header"><span class="section-num">01</span><span class="section-title">평가 요약</span></div>
  <div class="subsection">
    <div class="subsection-title">1.1 종합 점수</div>
    <div class="score-cards">
{render_output_score_cards(data)}
    </div>
  </div>
  <div class="subsection">
    <div class="subsection-title">1.2 사내 프로젝트 활용 현황</div>
{render_output_project_summary(project)}
  </div>
  <div class="subsection">
    <div class="subsection-title">1.3 유사 특허 현황</div>
{render_output_similar_summary(similar_analysis)}
  </div>
  <div class="subsection">
    <div class="subsection-title">1.4 종합 의견</div>
    <div class="opinion-box">{render_overall_summary(overall_summary)}</div>
  </div>
</section>

<section class="section" id="sec2">
  <div class="section-header"><span class="section-num">02</span><span class="section-title">평가 기준별 상세 점수</span></div>
{render_output_eval_blocks(data)}
</section>

<section class="section" id="sec3">
  <div class="section-header"><span class="section-num">03</span><span class="section-title">사내 프로젝트 활용 현황</span></div>
{render_output_project_section(project)}
</section>

<section class="section" id="sec4">
  <div class="section-header"><span class="section-num">04</span><span class="section-title">유사 특허 분석</span></div>
{render_output_similar_section(similar_analysis)}
</section>

<section class="section" id="sec5">
  <div class="section-header"><span class="section-num">05</span><span class="section-title">추가 확인 필요 사항</span></div>
  <p style="font-size:13px;color:var(--text-muted);margin-bottom:16px;">점수가 낮은 평가 항목에서 자동 추출했습니다. 사업부 자체 자료와의 교차 검토를 권장합니다.</p>
{render_output_confirm_items(data)}
</section>

<section class="section" id="sec6">
  <div class="section-header"><span class="section-num">06</span><span class="section-title">참고문헌</span></div>
  <ul class="ref-list">
{render_ref_list(refs)}
  </ul>
</section>

<div class="footnote-bar">
  <span>본 보고서는 공개 데이터 및 AI 분석에 기반하며, 최종 의사결정은 사업부 판단에 따릅니다.</span>
  <span>평가 기준일: {esc(today_str)}</span>
</div>
</div>
<script>
document.querySelectorAll('.eval-table tr.data-row').forEach(row => {{
  row.addEventListener('click', event => {{
    if (event.target.closest('a')) return;
    const detailId = row.dataset.detail;
    const detail = document.getElementById(detailId);
    const detailRow = document.getElementById(`row-${{detailId}}`);
    const btn = document.getElementById(`btn-${{detailId}}`);
    const open = detail.classList.contains('open');
    detail.classList.toggle('open', !open);
    detailRow.classList.toggle('open', !open);
    btn.classList.toggle('open', !open);
  }});
}});
</script>
</body>
</html>
"""
    output.write_text(html_text, encoding="utf-8")
    print(f"HTML 보고서 생성 완료: {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="HTML IP 가치 평가 보고서 생성")
    parser.add_argument(
        "--input-json",
        nargs="+",
        default=[str(path) for path in DEFAULT_OUTPUT_JSONS],
        help="평가 output JSON 파일 경로. 생략하면 기본 3개 특허 보고서를 생성합니다.",
    )
    parser.add_argument("--output-dir", default=str(ARTIFACT_REPORT_DIR), help="HTML을 저장할 디렉터리")
    parser.add_argument("--output", default=None, help="단일 input-json 사용 시 생성할 HTML 파일 경로")
    parser.add_argument("--no-llm", action="store_true", help="LLM 종합 의견 생성 없이 규칙 기반 요약 사용")
    args = parser.parse_args()

    for input_json in args.input_json:
        output_path = args.output if len(args.input_json) == 1 and args.output else None
        generate_report_from_output_json(
            input_json=input_json,
            output_path=output_path,
            output_dir=args.output_dir,
            use_llm=not args.no_llm,
        )


if __name__ == "__main__":
    main()
