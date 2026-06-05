"""샘플 특허로 보고서 신뢰도 검증을 빠르게 실행하는 CLI입니다."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SRC_DIR = Path(__file__).resolve().parents[2]
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.patent_valuation_graph import PatentValuationWorkflow, PatentValuationWorkflowOptions
from core.paths import SAMPLE_INPUT_DIR


def _sample_path(sample_name: str) -> Path:
    path = Path(sample_name)
    if path.exists():
        return path
    if not sample_name.endswith(".json"):
        sample_name = f"{sample_name}.json"
    return SAMPLE_INPUT_DIR / sample_name


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    verification = result.get("report_verification") or {}
    return {
        "status": result.get("status"),
        "reliability": verification.get("overall_reliability_score"),
        "grade": verification.get("reliability_grade"),
        "risk": verification.get("risk_level"),
        "human_review_required": verification.get("human_review_required"),
        "numeric_integrity": verification.get("numeric_integrity"),
        "issue_count": (verification.get("metrics") or {}).get("issue_count"),
        "issues": verification.get("issues") or [],
        "qa_in_report": bool((result.get("report") or {}).get("quality_assurance")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="샘플 특허 가치평가 보고서 신뢰도를 검증합니다.")
    parser.add_argument(
        "sample",
        nargs="?",
        default="patent_10_2925867.json",
        help="data/samples/input 아래 JSON 파일명 또는 직접 JSON 경로",
    )
    parser.add_argument("--llm", action="store_true", help="LLM 평가를 켭니다.")
    parser.add_argument("--rag", action="store_true", help="사업화 RAG 분석을 켭니다.")
    parser.add_argument("--similar", action="store_true", help="유사 특허 분석을 켭니다.")
    parser.add_argument("--market", action="store_true", help="KOSIS 시장 성장률 조회를 켭니다.")
    parser.add_argument("--full", action="store_true", help="LLM/RAG/유사특허/시장 분석을 모두 켭니다.")
    parser.add_argument("--raw", action="store_true", help="전체 workflow 결과를 출력합니다.")
    args = parser.parse_args()

    sample_path = _sample_path(args.sample)
    if not sample_path.exists():
        raise SystemExit(f"샘플 파일을 찾을 수 없습니다: {sample_path}")

    with sample_path.open(encoding="utf-8") as file:
        patent_data = json.load(file)

    full = bool(args.full)
    options = PatentValuationWorkflowOptions(
        enable_market=full or args.market,
        enable_auto=True,
        enable_llm=full or args.llm,
        enable_pdf_metadata_extraction=False,
        enable_business_rag=full or args.rag,
        enable_similar_analysis=full or args.similar,
        similar_use_llm=full,
        rag_top_k=5,
        fail_on_validation_error=False,
    )
    result = PatentValuationWorkflow(options).run(patent_data)
    payload = result if args.raw else _compact_result(result)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
