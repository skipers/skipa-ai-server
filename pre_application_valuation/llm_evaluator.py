"""Checklist-driven LLM evaluator for pre-application valuation."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests

from .schemas import PreApplicationValuationRequest


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"
CHECKLIST_PATH = Path(__file__).resolve().parent / "resources" / "pre_application_checklist.md"


def evaluate_checklist(
    request: PreApplicationValuationRequest,
    diagnostics: dict[str, Any],
    ipc: dict[str, Any],
) -> dict[str, Any]:
    checklist = parse_checklist_markdown(CHECKLIST_PATH)
    model = load_env_value("OPENAI_PRE_APPLICATION_MODEL") or load_env_value("OPENAI_REPORT_MODEL") or load_env_value("OPENAI_MODEL") or DEFAULT_MODEL
    if load_env_value("PRE_APPLICATION_USE_LLM").lower() in {"0", "false", "no", "off"}:
        raise RuntimeError("사전가치평가 보고서는 LLM 평가가 필수입니다. PRE_APPLICATION_USE_LLM 값을 제거하거나 true로 설정하세요.")
    api_key = load_env_value("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("사전가치평가 보고서는 LLM 평가가 필수입니다. OPENAI_API_KEY가 필요합니다.")

    prompt = build_prompt(request, diagnostics, ipc, checklist)
    last_error: Exception | None = None
    try:
        for attempt in range(2):
            request_prompt = prompt
            if attempt and last_error is not None:
                request_prompt = (
                    f"{prompt}\n\n[이전 응답 오류]\n{last_error}\n"
                    "score_items는 반드시 체크리스트 1~12번을 모두 포함하고, 각 항목의 item_number를 정확히 입력하세요."
                )
            response = requests.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "model": model,
                    "temperature": 0.1,
                    "max_tokens": 5000,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a Korean patent attorney and early-stage IP strategy analyst. "
                                "Return only one valid JSON object that exactly follows the requested schema."
                            ),
                        },
                        {"role": "user", "content": request_prompt},
                    ],
                },
                timeout=60,
            )
            response.raise_for_status()
            parsed = parse_json_object(response.json()["choices"][0]["message"]["content"])
            try:
                return normalize_llm_result(parsed, checklist, model)
            except ValueError as exc:
                last_error = exc
                continue
    except Exception as exc:
        raise RuntimeError(f"사전가치평가 LLM 평가에 실패했습니다: {exc}") from exc
    raise RuntimeError(f"사전가치평가 LLM 평가에 실패했습니다: {last_error}")


def parse_checklist_markdown(path: Path = CHECKLIST_PATH) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    dimensions: list[dict[str, Any]] = []
    current_dim: dict[str, Any] | None = None
    current_item: dict[str, Any] | None = None
    dim_pattern = re.compile(r"^##\s+(.+?)\s+\((.+?)\)")
    item_pattern = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$")
    criteria_pattern = re.compile(r"^-\s+\*\*(.+?)\*\*:\s*(.+)$")

    def flush_item() -> None:
        nonlocal current_item
        if current_dim and current_item:
            current_item["description"] = " ".join(current_item.pop("_desc", [])).strip()
            current_dim["items"].append(current_item)
        current_item = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("# "):
            continue
        dim_match = dim_pattern.match(stripped)
        if dim_match:
            flush_item()
            current_dim = {"label": dim_match.group(1).strip(), "key": dim_match.group(2).strip(), "items": []}
            dimensions.append(current_dim)
            continue
        item_match = item_pattern.match(stripped)
        if item_match:
            flush_item()
            current_item = {
                "number": int(item_match.group(1)),
                "item": item_match.group(2).strip(),
                "_desc": [],
                "criteria": [],
            }
            continue
        if current_item is None:
            continue
        criteria_match = criteria_pattern.match(stripped)
        if criteria_match:
            current_item["criteria"].append({"level": criteria_match.group(1).strip(), "text": criteria_match.group(2).strip()})
        elif not stripped.startswith("---"):
            current_item["_desc"].append(stripped)
    flush_item()
    return dimensions


def build_prompt(
    request: PreApplicationValuationRequest,
    diagnostics: dict[str, Any],
    ipc: dict[str, Any],
    checklist: list[dict[str, Any]],
) -> str:
    checklist_text = format_checklist(checklist)
    claims_text = "\n".join(f"{index + 1}. {claim}" for index, claim in enumerate(request.claims)) or "청구항 미입력"
    return f"""
아래 출원 전 아이디어/특허 초안을 평가하세요. 이 평가는 등록 특허 재평가가 아니라 출원 전 권리화 전략 보고서입니다.

[중요 원칙]
1. 피인용, 심판이력, 등록 후 존속기간처럼 출원 전 입력에서 확인할 수 없는 지표를 평가 근거로 사용하지 마세요.
2. 실제 선행기술 검색을 수행하지 않았으므로 신규성/진보성을 확정하지 말고, 리스크 가설과 조사 필요도로 표현하세요.
3. 입력에 없는 실험 결과, 시장 수치, 고객사를 만들어내지 마세요.
4. 5점은 예외적으로만 부여하고, 근거가 부족하면 3점 이하로 보수 평가하세요.
5. '사전 가치평가'의 중심은 출원 전 비용을 투입할 만한 특허 후보인지, 어떤 조건에서 가치가 생기는지, 어떤 근거가 부족한지입니다.
6. 각 항목 reason에는 입력에서 확인한 근거와 부족한 근거를 함께 쓰세요.
7. 각 항목 next_actions는 출원 전 바로 수행할 수 있는 작업으로 작성하세요.
8. score_items는 반드시 체크리스트 1~12번을 모두 포함하세요. 누락, 병합, 이름 변경을 하지 마세요.

[입력]
특허명: {request.patent_name}
기술 설명:
{request.technology_description}

청구항:
{claims_text}

관련 사업: {request.related_business or "미입력"}
출원 예정 국가: {", ".join(request.target_countries) or "미입력"}

[로컬 진단값]
{json.dumps(diagnostics, ensure_ascii=False, indent=2)}

[기술분야 추정]
{json.dumps(ipc, ensure_ascii=False, indent=2)}

[평가 체크리스트]
{checklist_text}

[반환 형식]
반드시 아래 JSON object만 반환하세요.
{{
  "overall_opinion": "2~4문장 종합 의견",
  "score_items": [
    {{
      "item_number": 1,
      "dimension": "technology_readiness",
      "dimension_label": "기술 구체성",
      "item": "문제 정의 명확성",
      "score": 1,
      "reason": "구체 근거와 부족한 점",
      "risks": ["리스크"],
      "next_actions": ["보완 액션"]
    }}
  ],
  "key_risks": ["핵심 리스크"],
  "valuation_assessment": {{
    "value_grade": "high_pre_filing_value | promising_value_with_validation | conditional_value | low_value_until_refined",
    "value_summary": "출원 전 예상 가치와 그 이유를 3~5문장으로 구체 작성",
    "positive_value_drivers": ["가치를 높이는 입력 근거"],
    "value_constraints": ["가치를 제한하는 불확실성"],
    "evidence_needed": ["출원/투자 판단 전 추가 확보할 근거"]
  }},
  "commercialization_assessment": {{
    "target_market": "주요 적용 시장 또는 고객군",
    "expected_use_cases": ["구체 적용 시나리오"],
    "monetization_paths": ["제품 차별화/라이선스/비용절감 등 가치 실현 경로"],
    "market_validation_gaps": ["시장 검증 공백"]
  }},
  "next_actions": [
    {{"priority": "high", "action": "가장 먼저 할 일", "reason": "이유"}}
  ],
  "claim_strategy": {{
    "independent_claim_direction": "독립항 구성 방향",
    "dependent_claim_ideas": ["종속항 아이디어"],
    "avoidance_design_notes": ["회피설계 방지 메모"]
  }},
  "filing_strategy": {{
    "recommended_route": "국내 우선출원/PCT/개별국 등 예비 제안",
    "country_notes": ["국가 전략 메모"]
  }},
  "filing_investment_decision": {{
    "decision": "go_to_prior_art_search_and_drafting | revise_then_file | hold_for_value_validation | do_not_file_yet",
    "rationale": "출원 비용 투입 여부 판단 이유",
    "go_conditions": ["출원 진행 조건"],
    "stop_or_hold_conditions": ["보류 조건"],
    "recommended_next_sprint": ["1~2주 안에 수행할 보완 작업"]
  }},
  "limitations": ["평가 한계"]
}}
""".strip()


def format_checklist(checklist: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for dimension in checklist:
        blocks.append(f"## {dimension['label']} ({dimension['key']})")
        for item in dimension["items"]:
            criteria = "\n".join(f"- {criterion['level']}: {criterion['text']}" for criterion in item["criteria"])
            blocks.append(f"### {item['number']}. {item['item']}\n{item['description']}\n{criteria}")
    return "\n\n".join(blocks)


def normalize_llm_result(parsed: dict[str, Any], checklist: list[dict[str, Any]], model: str) -> dict[str, Any]:
    expected_by_number: dict[int, tuple[dict[str, Any], dict[str, Any]]] = {}
    expected_by_key: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    for dimension in checklist:
        for item in dimension["items"]:
            expected_by_number[int(item["number"])] = (dimension, item)
            expected_by_key[(item["item"], dimension["key"])] = (dimension, item)
    raw_items = parsed.get("score_items") if isinstance(parsed.get("score_items"), list) else []
    normalized_items: list[dict[str, Any]] = []
    used_numbers: set[int] = set()
    unmatched: list[str] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        item_name = str(raw.get("item") or "").strip()
        dimension_key = str(raw.get("dimension") or "").strip()
        match = expected_by_number.get(int_value(raw.get("item_number") or raw.get("number") or raw.get("checklist_number")))
        if not match:
            match = expected_by_key.get((item_name, dimension_key))
        if not match:
            unmatched.append(f"{dimension_key}/{item_name}".strip("/"))
            continue
        dimension, checklist_item = match
        item_number = int(checklist_item["number"])
        if item_number in used_numbers:
            continue
        used_numbers.add(item_number)
        score = clamp_score(raw.get("score"))
        normalized_items.append({
            "item_number": item_number,
            "item": checklist_item["item"],
            "dimension": dimension["key"],
            "dimension_label": dimension["label"],
            "score": score,
            "score_out_of_100": score * 20,
            "reason": str(raw.get("reason") or "").strip() or "LLM이 항목별 근거를 충분히 제공하지 않았습니다.",
            "risks": string_list(raw.get("risks")),
            "next_actions": string_list(raw.get("next_actions")),
            "method": "llm_pre_application_checklist",
            "confidence": "보통",
        })
    missing = [
        f"{number}. {item['item']}"
        for number, (_dimension, item) in sorted(expected_by_number.items())
        if number not in used_numbers
    ]
    if missing or unmatched:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if unmatched:
            details.append(f"unmatched={unmatched}")
        raise ValueError("LLM score_items did not match the required 12 checklist items: " + "; ".join(details))
    normalized_items.sort(key=lambda item: int(item["item_number"]))
    return {
        "source": "llm",
        "model": model,
        "overall_opinion": str(parsed.get("overall_opinion") or "").strip(),
        "score_items": normalized_items,
        "key_risks": string_list(parsed.get("key_risks")),
        "valuation_assessment": dict_value(parsed.get("valuation_assessment")),
        "commercialization_assessment": dict_value(parsed.get("commercialization_assessment")),
        "next_actions": normalize_actions(parsed.get("next_actions")),
        "claim_strategy": dict_value(parsed.get("claim_strategy")),
        "filing_strategy": dict_value(parsed.get("filing_strategy")),
        "filing_investment_decision": dict_value(parsed.get("filing_investment_decision")),
        "limitations": string_list(parsed.get("limitations")),
    }


def fallback_evaluation(
    checklist: list[dict[str, Any]],
    diagnostics: dict[str, Any],
    reason: str,
    model: str,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for dimension in checklist:
        for item in dimension["items"]:
            items.append(fallback_item(item, dimension, diagnostics))
    gaps = diagnostics.get("gaps") or []
    high_gaps = [gap["message"] for gap in gaps if gap.get("severity") == "high"]
    next_actions = [
        {"priority": "high", "action": gap["message"], "reason": "로컬 진단에서 높은 보완 필요성이 확인되었습니다."}
        for gap in gaps[:4]
    ]
    return {
        "source": "fallback",
        "model": model,
        "overall_opinion": "LLM 평가를 사용할 수 없어 로컬 진단값으로 사전 출원 준비도를 보수적으로 평가했습니다.",
        "score_items": items,
        "key_risks": high_gaps or ["LLM 평가와 선행기술 검색이 수행되지 않아 정밀 리스크 판단은 제한됩니다."],
        "valuation_assessment": {
            "value_grade": "conditional_value",
            "value_summary": (
                "현재 입력만으로는 출원 전 특허 가치를 조건부 수준으로 판단합니다. "
                "기술 구성과 청구항 초안은 일부 확인되지만, 선행기술 대비 차별성 및 사업적 가치 근거가 충분히 검증되지 않았습니다. "
                "정량 효과와 적용 고객 근거를 보강하면 출원 비용 투입 여부를 더 명확히 판단할 수 있습니다."
            ),
            "positive_value_drivers": ["기술 설명과 청구항 초안이 입력되어 기본 권리화 검토가 가능합니다."],
            "value_constraints": high_gaps or ["LLM 평가와 선행기술 검색이 수행되지 않아 가치 판단 신뢰도가 제한됩니다."],
            "evidence_needed": ["차별 포인트별 선행기술 검색 결과", "성능/비용 개선 정량 지표", "대표 고객군과 적용 시나리오"],
        },
        "commercialization_assessment": {
            "target_market": "입력된 관련 사업을 기준으로 한 초기 적용 시장",
            "expected_use_cases": ["관련 사업 내 파일럿 적용", "기존 제품/서비스의 기술 차별화 근거로 활용"],
            "monetization_paths": ["출원 포트폴리오 확보 후 제품 차별화", "공동사업 또는 라이선스 협상 자산화"],
            "market_validation_gaps": ["고객군, 구매 요인, 비용 절감 폭을 추가 검증해야 합니다."],
        },
        "next_actions": next_actions,
        "claim_strategy": {
            "independent_claim_direction": "핵심 입력, 처리, 출력 흐름을 하나의 독립항으로 정리하세요.",
            "dependent_claim_ideas": ["구체 알고리즘", "운영 환경", "데이터 조건", "예외 처리"],
            "avoidance_design_notes": ["기능적 표현만 남기지 말고 필수 구성요소 간 관계를 청구항에 반영하세요."],
        },
        "filing_strategy": {
            "recommended_route": "국내 우선출원 후 사업 국가가 확정되면 해외/PCT 전략을 재검토",
            "country_notes": ["현재 목표 국가 입력과 사업 적용처를 연결해 우선순위를 정해야 합니다."],
        },
        "filing_investment_decision": {
            "decision": "hold_for_value_validation",
            "rationale": "로컬 진단만으로는 출원 비용 투입 결정을 확정하기 어렵기 때문에 가치 근거 보강 후 재검토가 필요합니다.",
            "go_conditions": ["핵심 차별점이 선행기술과 구분됨", "정량 효과와 적용 고객 근거가 확보됨"],
            "stop_or_hold_conditions": high_gaps or ["가치 판단을 뒷받침할 외부 검증 근거가 부족합니다."],
            "recommended_next_sprint": ["청구항 보강", "간이 선행기술 검색", "사업 적용 시나리오와 정량 효과 정리"],
        },
        "limitations": [reason, "실제 선행기술 검색, 변리사 검토, 시장 데이터 검증은 수행되지 않았습니다."],
    }


def fallback_item(item: dict[str, Any], dimension: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, Any]:
    score = conservative_fallback_score(str(item["item"]), heuristic_score(str(item["item"]), diagnostics), diagnostics)
    return {
        "item": item["item"],
        "dimension": dimension["key"],
        "dimension_label": dimension["label"],
        "score": score,
        "score_out_of_100": score * 20,
        "reason": fallback_reason(str(item["item"]), diagnostics),
        "risks": fallback_risks(str(item["item"]), diagnostics),
        "next_actions": fallback_actions(str(item["item"]), diagnostics),
        "method": "local_pre_application_diagnostics",
        "confidence": "낮음",
    }


def heuristic_score(item_name: str, diagnostics: dict[str, Any]) -> int:
    text = diagnostics["text"]
    claims = diagnostics["claims"]
    strategy = diagnostics["strategy"]
    signals = diagnostics["signals"]
    if item_name == "문제 정의 명확성":
        return score_threshold(text["technology_description_chars"] + signals["problem_terms"] * 80, [800, 550, 320, 160])
    if item_name == "해결 수단의 구체성":
        useful_categories = [category for category in claims["categories"] if category != "기타"]
        return score_threshold(signals["mechanism_terms"] + len(useful_categories), [8, 6, 3, 1])
    if item_name == "차별 포인트 설득력":
        return score_threshold(signals["differentiation_terms"] + signals["effect_terms"], [7, 5, 3, 1])
    if item_name == "독립항 구성 가능성":
        return score_threshold(claims["independent_like_count"] + claims["count"], [8, 5, 3, 1])
    if item_name == "회피설계 리스크":
        return score_threshold(len(claims["categories"]) + claims["dependent_like_count"], [5, 4, 2, 1])
    if item_name == "선행기술 조사 필요도":
        return score_threshold(signals["differentiation_terms"] + signals["quantitative_terms"], [5, 4, 2, 1])
    if item_name == "적용 고객/사용처 명확성":
        return score_threshold(text["related_business_chars"] + signals["business_terms"] * 30, [240, 160, 90, 40])
    if item_name == "경제적 효과 설명력":
        return score_threshold(signals["effect_terms"] + signals["business_terms"] + signals["quantitative_terms"], [9, 6, 3, 1])
    if item_name == "도입 장벽과 실행 가능성":
        return score_threshold(signals["adoption_terms"] + signals["mechanism_terms"], [9, 6, 3, 1])
    if item_name == "명세서 보강 필요도":
        return score_threshold(text["technology_description_chars"] + claims["count"] * 90, [1200, 850, 520, 250])
    if item_name == "해외/우선권 전략 적합성":
        return score_threshold(strategy["target_country_count"] + int(strategy["has_overseas_target"]), [5, 4, 2, 1])
    if item_name == "다음 액션 명확성":
        return 4 if diagnostics.get("gaps") else 3
    return 3


def conservative_fallback_score(item_name: str, score: int, diagnostics: dict[str, Any]) -> int:
    # Local fallback is a smoke-test and development path, not a substitute for
    # item-level LLM review or prior-art research. Keep it deliberately modest.
    score = min(score, 4)
    has_high_gap = any(gap.get("severity") == "high" for gap in diagnostics.get("gaps") or [])
    if item_name in {"선행기술 조사 필요도", "회피설계 리스크"}:
        score = min(score, 3)
    if has_high_gap and item_name in {"문제 정의 명확성", "명세서 보강 필요도", "다음 액션 명확성"}:
        score = min(score, 3)
    return max(1, score)


def fallback_reason(item_name: str, diagnostics: dict[str, Any]) -> str:
    gap_count = len(diagnostics.get("gaps") or [])
    return f"로컬 진단 기준으로 '{item_name}'을 평가했습니다. 확인된 보완 갭은 {gap_count}개이며, LLM 정밀 평가는 수행되지 않았습니다."


def fallback_risks(item_name: str, diagnostics: dict[str, Any]) -> list[str]:
    gaps = diagnostics.get("gaps") or []
    return [str(gap.get("message")) for gap in gaps[:2]] or [f"{item_name}에 대한 정밀 판단은 LLM/전문가 검토가 필요합니다."]


def fallback_actions(item_name: str, diagnostics: dict[str, Any]) -> list[str]:
    gaps = diagnostics.get("gaps") or []
    if gaps:
        return [str(gap.get("message")) for gap in gaps[:2]]
    return [f"{item_name}을 뒷받침할 구체 근거를 명세서 초안에 추가하세요."]


def score_threshold(raw: int, thresholds: list[int]) -> int:
    for index, threshold in enumerate(thresholds):
        if raw >= threshold:
            return 5 - index
    return 1


def clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except Exception:
        score = 3
    return max(1, min(5, score))


def normalize_actions(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    actions: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, dict):
            action = str(item.get("action") or "").strip()
            if action:
                actions.append({
                    "priority": str(item.get("priority") or "medium").strip(),
                    "action": action,
                    "reason": str(item.get("reason") or "").strip(),
                })
        else:
            text = str(item).strip()
            if text:
                actions.append({"priority": "medium", "action": text, "reason": ""})
    return actions


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def int_value(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response is not a JSON object")
    return parsed


def load_env_value(key: str) -> str:
    value = os.environ.get(key)
    if value:
        return value.strip()
    for env_path in env_paths():
        loaded = read_env_file(env_path).get(key)
        if loaded:
            os.environ.setdefault(key, loaded)
            return loaded
    return ""


def env_paths() -> list[Path]:
    module_dir = Path(__file__).resolve().parent
    server_root = module_dir.parent
    return [
        server_root / ".env",
        server_root / "eval_logic" / ".env",
        server_root / "chatbot" / ".env",
    ]


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values
