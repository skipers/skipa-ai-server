"""특허 가치 평가 OpenAI 에이전트

OpenAI function calling을 사용해 특허 평가 파이프라인을 오케스트레이션합니다.
에이전트가 자발적으로 중단하더라도 필수 4개 tool이 모두 실행되도록 강제합니다.

실행 흐름:
  1. validate_patent_input         - 입력 검증 및 정규화
  2. run_valuation_pipeline        - 자동 점수 + 시장 성장률 + LLM 43개 항목 평가
  3. run_similar_patent_analysis   - 유사 특허 비교 분석 (사전 계산 데이터 활용)
  4. build_json_report             - 구조화 JSON 보고서 생성 (6개 섹션)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agent.report_builder import build_structured_report
from core.paths import ARTIFACT_OUTPUT_DIR, SAMPLE_DATA_DIR
from services.valuation_service import PatentValuationOptions, PatentValuationService


_SYSTEM_PROMPT = """당신은 특허 가치 평가 전문 AI 에이전트입니다.
반드시 아래 4개 도구를 순서대로 모두 호출해야 합니다. 어떤 경우에도 중간에 멈추지 마세요.

필수 실행 순서 (절대 생략 불가):
1. validate_patent_input         : 입력 검증
2. run_valuation_pipeline        : 평가 파이프라인 실행
3. run_similar_patent_analysis   : 유사 특허 분석
4. build_json_report             : 최종 보고서 생성

build_json_report 호출 시 agent_analysis 필드에 아래 내용을 모두 포함하세요:
- 특허의 핵심 기술 가치 및 차별성
- 시장 진입 가능성 및 상업화 전망
- 유사 특허와의 경쟁 포지션 및 위험 요소
- 사내 프로젝트 적용 현황 및 활용 방향
- 투자·사업화 관점의 종합 의견 및 권고사항
"""

_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "validate_patent_input",
            "description": "특허 입력 데이터를 검증합니다. 필수 필드 존재 여부와 평가 가능 여부를 반환합니다.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_valuation_pipeline",
            "description": (
                "특허 가치 평가 파이프라인을 실행합니다. "
                "자동 점수, KOSIS 시장 성장률, LLM 43개 항목 평가를 수행합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "enable_llm": {"type": "boolean", "description": "LLM 평가 활성화 (기본 true)"},
                    "enable_market": {"type": "boolean", "description": "시장 성장률 조회 활성화 (기본 true)"},
                    "enable_business_rag": {"type": "boolean", "description": "사내 프로젝트 RAG 분석 (기본 true)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_similar_patent_analysis",
            "description": "유사 특허 비교 분석을 실행합니다. 사전 계산된 파일이 있으면 로드하고, 없으면 분석합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "use_llm": {"type": "boolean", "description": "LLM 기반 비교 요약 생성 (기본 false)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_json_report",
            "description": (
                "6개 섹션 구조화 JSON 보고서를 생성합니다. "
                "1.평가요약 2.상세점수 3.사내프로젝트 4.유사특허 5.추가확인 6.참고문헌"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_analysis": {
                        "type": "string",
                        "description": "에이전트 종합 분석 (기술가치, 시장전망, 경쟁포지션, 사업화 의견)",
                    }
                },
                "required": ["agent_analysis"],
            },
        },
    },
]

# 필수 실행 순서
_REQUIRED_STEPS = [
    "validate_patent_input",
    "run_valuation_pipeline",
    "run_similar_patent_analysis",
    "build_json_report",
]


def _normalize_id_for_path(patent_id: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", str(patent_id or "")).strip("_")


class PatentValuationAgent:
    """OpenAI function calling 기반 특허 가치 평가 에이전트"""

    def __init__(self, model: str | None = None) -> None:
        self._client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self._patent_data: dict[str, Any] | None = None
        self._evaluation_output: dict[str, Any] | None = None
        self._similar_analysis: dict[str, Any] | None = None
        self._final_report: dict[str, Any] | None = None
        self._called_steps: list[str] = []

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def run(self, patent_data: dict[str, Any]) -> dict[str, Any]:
        """특허 데이터를 받아 에이전트 루프를 실행하고 최종 보고서를 반환합니다."""
        self._patent_data = patent_data
        self._evaluation_output = None
        self._similar_analysis = None
        self._final_report = None
        self._called_steps = []

        patent_id = patent_data.get("patent_id") or (patent_data.get("meta") or {}).get("registration_number", "알 수 없음")
        title = (patent_data.get("meta") or {}).get("title") or patent_data.get("title", "알 수 없음")

        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    f"다음 특허를 평가하고 6개 섹션 보고서를 생성해주세요.\n"
                    f"특허 ID: {patent_id}\n특허명: {title}\n\n"
                    "반드시 4개 도구 전부 순서대로 실행하세요."
                ),
            }
        ]

        for iteration in range(20):
            # 아직 호출되지 않은 다음 필수 step 결정
            pending = [s for s in _REQUIRED_STEPS if s not in self._called_steps]

            if not pending:
                # 모든 필수 단계 완료
                break

            # 다음 tool을 강제로 지정
            next_tool = pending[0]
            forced_choice: Any = {"type": "function", "function": {"name": next_tool}}

            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=_TOOLS,
                tool_choice=forced_choice,
            )
            choice = response.choices[0]
            messages.append(choice.message.model_dump(exclude_none=True))

            if choice.message.tool_calls:
                for tool_call in choice.message.tool_calls:
                    name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    print(f"  [Agent] Tool 호출: {name}")
                    result = self._dispatch(name, args)
                    self._called_steps.append(name)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
            else:
                # tool_calls가 없으면 강제 재시도 없이 다음 루프에서 해당 tool 재강제
                pass

        return self._final_report or {}

    # ──────────────────────────────────────────
    # Tool dispatcher
    # ──────────────────────────────────────────

    def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "validate_patent_input":
            return self._tool_validate()
        if name == "run_valuation_pipeline":
            return self._tool_run_pipeline(
                enable_llm=args.get("enable_llm", True),
                enable_market=args.get("enable_market", True),
                enable_business_rag=args.get("enable_business_rag", True),
            )
        if name == "run_similar_patent_analysis":
            return self._tool_similar_analysis(use_llm=args.get("use_llm", False))
        if name == "build_json_report":
            return self._tool_build_report(args.get("agent_analysis", ""))
        return {"error": f"알 수 없는 tool: {name}"}

    # ──────────────────────────────────────────
    # Tool implementations
    # ──────────────────────────────────────────

    def _tool_validate(self) -> dict[str, Any]:
        from core.schemas import PatentEvaluationInput

        if not self._patent_data:
            return {"valid": False, "error": "데이터 없음"}
        try:
            req = PatentEvaluationInput.from_dict(self._patent_data)
            errors = req.validate()
            return {
                "valid": len(errors) == 0,
                "patent_id": req.patent_id,
                "title": req.title,
                "warnings": errors,
                "has_claims": bool(req.claims_text),
                "has_description": bool(req.description_summary),
                "has_market_data": bool(req.market_data),
                "has_kipris_data": bool(req.kipris_data),
            }
        except Exception as exc:
            return {"valid": False, "error": str(exc)}

    def _tool_run_pipeline(
        self,
        enable_llm: bool = True,
        enable_market: bool = True,
        enable_business_rag: bool = True,
    ) -> dict[str, Any]:
        if not self._patent_data:
            return {"status": "error", "error": "특허 데이터가 없습니다."}

        options = PatentValuationOptions(
            enable_auto=True,
            enable_llm=enable_llm,
            enable_market=enable_market,
            enable_evidence_collection=True,
            enable_pdf_metadata_extraction=True,
            enable_business_rag=enable_business_rag,
        )
        try:
            output = PatentValuationService(options).evaluate(self._patent_data)
            self._evaluation_output = output.to_dict()
            summary = self._evaluation_output.get("summary") or {}
            biz = ((self._evaluation_output.get("evidence") or {}).get("business_use") or {})
            return {
                "status": "success",
                "patent_id": self._evaluation_output.get("patent_id"),
                "auto_score_count": len(self._evaluation_output.get("auto_scores") or []),
                "llm_score_count": len(self._evaluation_output.get("llm_scores") or []),
                "market_growth": self._evaluation_output.get("market_growth"),
                "business_rag_status": biz.get("commercialization_status", "미확인"),
                "execution_time_seconds": summary.get("execution_time_seconds"),
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _tool_similar_analysis(self, use_llm: bool = False) -> dict[str, Any]:
        if not self._patent_data:
            return {"status": "error", "error": "특허 데이터가 없습니다."}

        patent_id = (
            self._patent_data.get("patent_id")
            or (self._patent_data.get("meta") or {}).get("registration_number")
            or ""
        )
        norm_id = _normalize_id_for_path(patent_id)

        # 1) 사전 계산 파일 탐색
        for suffix in [norm_id, norm_id.replace("_", "-")]:
            path = ARTIFACT_OUTPUT_DIR / f"similar_analysis_{suffix}.json"
            if path.exists():
                print(f"  [Agent] 유사 특허 분석 파일 로드: {path.name}")
                with path.open(encoding="utf-8") as f:
                    self._similar_analysis = json.load(f)
                return self._similar_summary()

        # 2) similar_details 파일 + target JSON으로 분석 실행
        details_path = next(
            (
                p
                for p in [
                    ARTIFACT_OUTPUT_DIR / f"similar_details_{norm_id}.json",
                    ARTIFACT_OUTPUT_DIR / f"similar_details_{norm_id.replace('_', '-')}.json",
                    SAMPLE_DATA_DIR / "similar_patent_details.json",
                ]
                if p.exists()
            ),
            None,
        )
        target_path = next(
            (
                p
                for p in [
                    ARTIFACT_OUTPUT_DIR / f"patent_{norm_id}_output.json",
                    ARTIFACT_OUTPUT_DIR / f"patent_{norm_id.replace('_', '-')}_output.json",
                    SAMPLE_DATA_DIR / "patent_input.json",
                ]
                if p.exists()
            ),
            None,
        )

        if details_path and target_path:
            try:
                from patent_analysis.similar_patent_analyzer import analyze_similar_patents

                out_path = ARTIFACT_OUTPUT_DIR / f"similar_analysis_{norm_id}.json"
                print(f"  [Agent] 유사 특허 분석 실행: {details_path.name}")
                self._similar_analysis = analyze_similar_patents(
                    target_path=target_path,
                    details_path=details_path,
                    output_path=out_path,
                    use_llm=use_llm,
                )
                return self._similar_summary()
            except Exception as exc:
                return {"status": "unavailable", "message": f"분석 실행 실패: {exc}"}

        print(f"  [Agent] 유사 특허 데이터 없음 (id={patent_id})")
        return {"status": "unavailable", "message": "유사 특허 분석 데이터가 없습니다."}

    def _similar_summary(self) -> dict[str, Any]:
        if not self._similar_analysis:
            return {"status": "unavailable"}
        eco = self._similar_analysis.get("ecosystem_summary") or {}
        interp = self._similar_analysis.get("interpretation") or {}
        top = self._similar_analysis.get("top_comparisons") or []
        return {
            "status": "success",
            "total_similar_patents": eco.get("total_similar_patents", 0),
            "active_count": eco.get("active_count", 0),
            "maintenance_signal": interp.get("maintenance_signal", ""),
            "competition_intensity": interp.get("competition_intensity", ""),
            "top_3_titles": [t.get("title", "") for t in top[:3]],
        }

    def _tool_build_report(self, agent_analysis: str) -> dict[str, Any]:
        if not self._evaluation_output:
            return {"status": "error", "error": "평가 결과 없음. run_valuation_pipeline 먼저 실행 필요."}
        report = build_structured_report(
            self._evaluation_output,
            similar_analysis=self._similar_analysis,
            agent_analysis=agent_analysis,
        )
        self._final_report = report
        s1 = report.get("section_1_summary") or {}
        return {
            "status": "success",
            "report_id": report.get("report_id"),
            "overall_score": s1.get("overall_score"),
            "overall_grade": s1.get("overall_grade"),
        }
