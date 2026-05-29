"""특허 유지/포기 의사결정 agentic workflow CLI입니다.

FastAPI 엔드포인트와 같은 ``PatentDecisionWorkflow``를 로컬에서 실행합니다.

사용법:
  cd eval_logic
  python src/cli/run_agent.py samples/input/patent_10_1098864.json
  python src/cli/run_agent.py samples/input
  python src/cli/run_agent.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.patent_decision_graph import PatentDecisionWorkflow, PatentDecisionWorkflowOptions
from core.paths import ARTIFACT_OUTPUT_DIR, SAMPLE_INPUT_DIR

OUTPUT_DIR = ARTIFACT_OUTPUT_DIR / "reports"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def resolve_input_files(input_path: str | None = None) -> list[Path]:
    if input_path:
        candidate = Path(input_path)
        if not candidate.exists():
            raise FileNotFoundError(f"입력 경로를 찾을 수 없습니다: {input_path}")
        if candidate.is_file():
            return [candidate]
        if candidate.is_dir():
            files = sorted(candidate.glob("*.json"))
            if not files:
                raise FileNotFoundError(f"디렉터리에 JSON 파일이 없습니다: {input_path}")
            return files
        raise ValueError(f"지원하지 않는 입력 경로입니다: {input_path}")

    files = sorted(SAMPLE_INPUT_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"기본 입력 디렉터리에 JSON 파일이 없습니다: {SAMPLE_INPUT_DIR}")
    return files


def print_result_summary(result: dict[str, Any]) -> None:
    validation = result.get("validation") or {}
    decision = result.get("decision") or {}
    valuation = result.get("valuation") or {}
    market = valuation.get("market_growth") or {}

    print("=" * 72)
    print(f"특허: {validation.get('patent_id')} | {str(validation.get('title', ''))[:40]}")
    print(f"Workflow: {result.get('workflow_type')} | Status: {result.get('status')}")
    print("=" * 72)
    print(f"추천: {decision.get('recommendation_label')} ({decision.get('confidence')})")
    print(f"종합 평균: {decision.get('overall_average_score')}/5")
    print(f"요약: {decision.get('summary')}")

    if market:
        print("\n[시장]")
        print(f"  섹터: {market.get('sector')} ({market.get('c2_code')})")
        print(f"  점수: {market.get('score')}/5")

    risks = decision.get("risk_factors") or []
    if risks:
        print("\n[리스크]")
        for item in risks:
            print(f"  - {item}")

    actions = decision.get("recommended_actions") or []
    if actions:
        print("\n[추천 액션]")
        for item in actions:
            print(f"  - {item}")

    print("\n[노드 실행]")
    for node in result.get("node_trace") or []:
        print(
            f"  {node.get('node'):<24} {node.get('status'):<8} "
            f"{node.get('elapsed_seconds'):>6}s  {node.get('message', '')}"
        )


def main() -> None:
    total_start = time.time()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'=' * 72}")
    print(f"Agentic workflow 시작: {now}")
    print(f"{'=' * 72}")

    input_path = sys.argv[1] if len(sys.argv) > 1 else None
    input_files = resolve_input_files(input_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    workflow = PatentDecisionWorkflow(
        PatentDecisionWorkflowOptions(
            enable_market=False,
            enable_llm=False,
            enable_business_rag=False,
        )
    )

    print(f"\n처리 대상 파일 수: {len(input_files)}")
    for idx, source_path in enumerate(input_files, 1):
        print(f"\n{'-' * 72}")
        print(f"[{idx}/{len(input_files)}] {source_path.name}")
        print(f"{'-' * 72}")

        result = workflow.run(load_json(source_path))
        print_result_summary(result)

        out_path = OUTPUT_DIR / f"{source_path.stem}_agent_workflow.json"
        with out_path.open("w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
        print(f"\n결과 저장: {out_path}")

    total = time.time() - total_start
    print(f"\n{'=' * 72}")
    print(f"전체 실행 시간: {total:.2f}초")
    print(f"결과 저장 폴더: {OUTPUT_DIR}")
    print(f"{'=' * 72}\n")


if __name__ == "__main__":
    main()
