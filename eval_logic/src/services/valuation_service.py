"""특허 가치 평가 서비스 레이어입니다.

프로토타입은 오케스트레이션 로직을 ``run_pipeline.py``에 직접 두었습니다.
실험 단계에서는 편했지만, 실제 서버 코드는 CLI, HTTP 핸들러, 백그라운드
작업자, 향후 에이전트에서 재사용할 수 있는 서비스 객체가 필요합니다. 이
모듈은 그 오케스트레이션 경계를 담당합니다.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from evaluation.auto_score import calc_auto_scores
from evaluation.kosis_growth_fetcher import get_growth_score_from_json
from core.schemas import (
    EvaluationStepResult,
    PatentEvaluationInput,
    PatentEvaluationOutput,
    ScoreItem,
    normalize_patent_input,
)


@dataclass(slots=True)
class PatentValuationOptions:
    """가치 평가 파이프라인 실행 옵션입니다.

    ``enable_llm``과 ``enable_market``을 통해 운영 환경과 테스트 환경에서 같은
    서비스를 사용할 수 있습니다. 예를 들어 단위 테스트에서는 LLM 호출을 끄고,
    전체 보고서 작업에서는 모든 단계를 켤 수 있습니다.
    """

    enable_market: bool = True
    enable_auto: bool = True
    enable_llm: bool = True
    enable_evidence_collection: bool = True
    enable_pdf_metadata_extraction: bool = True
    enable_business_rag: bool = False
    rag_top_k: int | None = None
    fail_on_validation_error: bool = True


def summarize_scores(scores: list[ScoreItem]) -> dict[str, Any]:
    """1~5점 평가 항목을 평가 차원별로 묶어 요약합니다.

    보고서 레이어는 각 차원의 합계, 항목 수, 평균을 필요로 합니다. 이 계산을
    서비스 레이어에 두면 CLI, API, 보고서 생성 흐름에서 요약 로직을 중복으로
    구현하지 않아도 됩니다.
    """
    dim_scores: dict[str, list[float]] = {}
    for score in scores:
        dim_scores.setdefault(score.dim, []).append(float(score.score))

    total = sum(sum(values) for values in dim_scores.values())
    count = sum(len(values) for values in dim_scores.values())
    return {
        "by_dimension": {
            dim: {
                "total": sum(values),
                "count": len(values),
                "average": round(sum(values) / len(values), 2) if values else 0,
            }
            for dim, values in dim_scores.items()
        },
        "total": total,
        "count": count,
        "average": round(total / count, 2) if count else 0,
    }


def collect_unique_sources(scores: list[ScoreItem]) -> list[dict[str, Any]]:
    """LLM 점수 항목에서 인용한 웹 출처를 URL 기준으로 중복 제거해 수집합니다."""
    seen_urls: set[str] = set()
    sources: list[dict[str, Any]] = []
    for score in scores:
        for source in score.sources:
            url = str(source.get("url") or "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources.append(source)
    return sources


class PatentValuationService:
    """특허 가치 평가 요청 1건을 실행하는 애플리케이션 서비스입니다.

    단계 순서:
    1. PDF/RAG 기반 보조 자료 수집으로 입력을 보강합니다.
    2. 입력을 정규화하고 검증합니다.
    3. 자동 점수에서 사용하므로 시장 성장률 데이터를 먼저 조회/도출합니다.
    4. 규칙 기반 자동 점수 계산기를 실행합니다.
    5. API 키와 텍스트 필드가 있으면 LLM 점수 생성을 실행합니다.
    6. 보고서와 API 응답에서 사용할 표준 출력 스키마를 만듭니다.
    """

    def __init__(self, options: PatentValuationOptions | None = None) -> None:
        self.options = options or PatentValuationOptions()

    def evaluate(self, data: dict[str, Any], input_file: str | None = None) -> PatentEvaluationOutput:
        """원본 특허 JSON 딕셔너리를 평가하고 타입이 있는 출력 객체를 반환합니다."""
        pipeline_start = time.time()
        data = normalize_patent_input(data)
        evidence: dict[str, Any] = {}
        evidence_steps: list[EvaluationStepResult] = []
        if self.options.enable_evidence_collection:
            data, evidence, evidence_steps = self._run_evidence_collection_stage(data)

        request = PatentEvaluationInput.from_dict(data)
        errors = request.validate()
        if errors and self.options.fail_on_validation_error:
            raise ValueError("; ".join(errors))

        patent = request.to_legacy_dict()
        output = PatentEvaluationOutput(
            patent_id=request.patent_id,
            title=request.title,
            evidence=evidence,
            input_file=input_file,
        )
        output.steps.extend(evidence_steps)
        if errors:
            output.summary["validation_warnings"] = errors

        if self.options.enable_market:
            self._run_market_stage(patent, output)
        else:
            fallback = {"score": 3, "fallback": True, "skipped": True}
            patent["market_growth"] = fallback
            output.market_growth = fallback
            output.steps.append(EvaluationStepResult("market_growth", "skipped", 0, "시장 성장률 단계 비활성화"))

        if self.options.enable_auto:
            self._run_auto_stage(patent, output)
        else:
            output.steps.append(EvaluationStepResult("auto_scores", "skipped", 0, "자동 점수 단계 비활성화"))

        if self.options.enable_llm:
            self._run_llm_stage(patent, output)
        else:
            output.steps.append(EvaluationStepResult("llm_scores", "skipped", 0, "LLM 평가 단계 비활성화"))

        output.summary["market"] = {
            "score": (output.market_growth or {}).get("score"),
            "growth_rate": (output.market_growth or {}).get("growth_rate"),
            "sector": (output.market_growth or {}).get("sector"),
            "c2_code": (output.market_growth or {}).get("c2_code"),
        }
        if evidence.get("business_use"):
            business_use = evidence["business_use"]
            output.summary["business_use"] = {
                "status": business_use.get("commercialization_status"),
                "signal_count": len(business_use.get("commercialization_signals") or []),
                "source_count": len(business_use.get("sources") or []),
            }
        output.summary["execution_time_seconds"] = round(time.time() - pipeline_start, 2)
        return output

    def _run_evidence_collection_stage(
        self,
        data: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], list[EvaluationStepResult]]:
        """PDF 원문/RAG 보조 자료 수집을 실행하고 평가 입력을 보강합니다."""
        try:
            from services.evidence_collection_service import EvidenceCollectionOptions, EvidenceCollectionService

            service = EvidenceCollectionService(
                EvidenceCollectionOptions(
                    enable_pdf_metadata_extraction=self.options.enable_pdf_metadata_extraction,
                    enable_business_rag=self.options.enable_business_rag,
                    rag_top_k=self.options.rag_top_k,
                )
            )
            enriched_data, evidence, steps = service.collect(data)
            return enriched_data, evidence.to_dict(), steps
        except Exception as exc:
            return (
                dict(data),
                {"errors": [f"보조 자료 수집 단계 초기화 실패: {exc}"]},
                [EvaluationStepResult("evidence_collection", "error", 0, "보조 자료 수집 초기화 실패", str(exc))],
            )

    def _run_market_stage(self, patent: dict[str, Any], output: PatentEvaluationOutput) -> None:
        """KOSIS/산업 성장률 조회를 실행하고 오류 시 대체값 메타데이터를 남깁니다."""
        start = time.time()
        try:
            market_growth = get_growth_score_from_json(patent)
            status = "fallback" if market_growth.get("fallback") else "success"
            output.market_growth = market_growth
            patent["market_growth"] = market_growth
            output.steps.append(
                EvaluationStepResult(
                    "market_growth",
                    status,
                    time.time() - start,
                    "KOSIS 시장 성장률 조회 완료",
                )
            )
        except Exception as exc:
            fallback = {
                "error": str(exc),
                "score": 3,
                "growth_rate": None,
                "sector": None,
                "c2_code": None,
                "fallback": True,
            }
            output.market_growth = fallback
            patent["market_growth"] = fallback
            output.steps.append(
                EvaluationStepResult("market_growth", "error", time.time() - start, "기본값 3점 적용", str(exc))
            )

    def _run_auto_stage(self, patent: dict[str, Any], output: PatentEvaluationOutput) -> None:
        """정형 특허 데이터 기반의 규칙 점수 계산기를 실행합니다."""
        start = time.time()
        raw_scores = calc_auto_scores(patent)
        output.auto_scores = [ScoreItem.from_dict(score) for score in raw_scores]
        output.summary["auto"] = summarize_scores(output.auto_scores)
        has_error = any(score.method == "error" for score in output.auto_scores)
        output.steps.append(
            EvaluationStepResult(
                "auto_scores",
                "fallback" if has_error else "success",
                time.time() - start,
                f"자동 점수 {len(output.auto_scores)}개 산출",
            )
        )

    def _run_llm_stage(self, patent: dict[str, Any], output: PatentEvaluationOutput) -> None:
        """인증 정보와 원문 텍스트가 있을 때만 LLM 평가를 실행합니다."""
        start = time.time()
        has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
        has_llm_fields = bool(patent.get("description_summary") or patent.get("claims_text"))
        if not has_openai_key or not has_llm_fields:
            reason = "OPENAI_API_KEY 없음 또는 LLM 평가에 필요한 필드(description_summary/claims_text) 부족"
            output.summary["llm_skipped"] = reason
            output.steps.append(EvaluationStepResult("llm_scores", "skipped", time.time() - start, reason))
            return

        try:
            # 지연 import를 사용해 서비스 생성 비용을 낮추고, 호출자가 LLM 단계를
            # 비활성화했을 때 LLM 전용 리소스가 로드되지 않도록 합니다.
            from evaluation.llm_evaluator import evaluate_all

            raw_scores = evaluate_all(patent)
            output.llm_scores = [ScoreItem.from_dict(score) for score in raw_scores]
            output.summary["llm"] = summarize_scores(output.llm_scores)
            output.llm_sources = collect_unique_sources(output.llm_scores)
            output.steps.append(
                EvaluationStepResult(
                    "llm_scores",
                    "success",
                    time.time() - start,
                    f"LLM 점수 {len(output.llm_scores)}개 산출",
                )
            )
        except Exception as exc:
            output.summary["llm_error"] = str(exc)
            output.steps.append(
                EvaluationStepResult("llm_scores", "error", time.time() - start, "LLM 평가 실패", str(exc))
            )
