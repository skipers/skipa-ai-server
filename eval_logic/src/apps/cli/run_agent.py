"""특허 가치평가 보고서 agentic workflow CLI입니다.

FastAPI 엔드포인트와 같은 ``PatentValuationWorkflow``를 로컬에서 실행합니다.

사용법:
  cd eval_logic
  python src/apps/cli/run_agent.py data/samples/input/patent_10_1098864.json
  python src/apps/cli/run_agent.py data/samples/input
  python src/apps/cli/run_agent.py
"""

from __future__ import annotations

import json
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.patent_valuation_graph import PatentValuationWorkflow, PatentValuationWorkflowOptions
from core.paths import RUNTIME_REPORT_DIR, SAMPLE_INPUT_DIR
from core.report_naming import safe_report_filename_from_result

OUTPUT_DIR = RUNTIME_REPORT_DIR
SERVER_DATA_DIR = Path(__file__).resolve().parents[4] / "data"


def parse_args() -> argparse.Namespace:
    """CLI 실행 범위와 입력 경로를 읽습니다."""
    parser = argparse.ArgumentParser(description="특허 가치평가 agentic workflow를 로컬에서 실행합니다.")
    parser.add_argument(
        "input_path",
        nargs="?",
        help=(
            "입력 JSON 파일, data/<등록번호> 디렉터리, 또는 data 루트. "
            "생략하면 skipa-ai-server/data/*/parsed.json 전체를 실행합니다."
        ),
    )
    parser.add_argument(
        "--profile",
        choices=["quick", "full"],
        default="full",
        help="full: 전체 평가 실행, quick: 시장/LLM/RAG만 줄인 실행. 유사 특허 KIPRIS 크롤러는 항상 실행합니다.",
    )
    parser.add_argument("--enable-market", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--enable-llm", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--enable-business-rag", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--similar-use-llm", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--rag-top-k", type=int, default=None)
    return parser.parse_args()


def build_workflow_options(args: argparse.Namespace) -> PatentValuationWorkflowOptions:
    """프로필 기본값 위에 사용자가 직접 지정한 옵션을 덮어씁니다.

    유사 특허 분석은 재평가 보고서 필수 섹션이므로 항상 KIPRIS 크롤러로 실행합니다.
    """
    is_full = args.profile == "full"

    def choose(value: bool | None, default: bool) -> bool:
        return default if value is None else value

    return PatentValuationWorkflowOptions(
        enable_market=choose(args.enable_market, is_full),
        enable_llm=choose(args.enable_llm, is_full),
        enable_business_rag=choose(args.enable_business_rag, is_full),
        enable_similar_analysis=True,
        similar_use_kipris_crawler=True,
        similar_force_refresh=True,
        similar_max_pages=5,
        similar_max_results=10,
        similar_date_from="2015-01-01",
        similar_date_to="",
        similar_use_llm=choose(args.similar_use_llm, is_full),
        enable_pdf_metadata_extraction=False,
        rag_top_k=args.rag_top_k,
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def resolve_input_files(input_path: str | None = None) -> list[Path]:
    def parsed_files_in_data_root(root: Path) -> list[Path]:
        return sorted(
            path
            for path in root.glob("*/parsed.json")
            if path.parent.name.startswith("10-")
        )

    if input_path:
        candidate = Path(input_path)
        if not candidate.exists():
            raise FileNotFoundError(f"입력 경로를 찾을 수 없습니다: {input_path}")
        if candidate.is_file():
            return [candidate]
        if candidate.is_dir():
            if (candidate / "parsed.json").exists():
                return [candidate / "parsed.json"]
            files = parsed_files_in_data_root(candidate)
            if not files:
                files = sorted(candidate.glob("*.json"))
            if not files:
                raise FileNotFoundError(f"디렉터리에 JSON 파일이 없습니다: {input_path}")
            return files
        raise ValueError(f"지원하지 않는 입력 경로입니다: {input_path}")

    files = parsed_files_in_data_root(SERVER_DATA_DIR)
    if not files:
        files = sorted(SAMPLE_INPUT_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"기본 입력 JSON을 찾을 수 없습니다: {SERVER_DATA_DIR}")
    return files


def output_path_for_result(source_path: Path, result: dict[str, Any]) -> Path:
    if source_path.name == "parsed.json" and source_path.parent.name.startswith("10-"):
        return source_path.parent / "report.json"
    return OUTPUT_DIR / safe_report_filename_from_result(result)


def print_result_summary(result: dict[str, Any]) -> None:
    validation = result.get("validation") or {}
    valuation = result.get("valuation") or {}
    report_summary = ((result.get("report") or {}).get("section_1_summary") or {})
    market = valuation.get("market_growth") or {}
    scores = (valuation.get("auto_scores") or []) + (valuation.get("llm_scores") or [])
    score_values = [float(item["score"]) for item in scores if isinstance(item.get("score"), (int, float))]
    average = report_summary.get("overall_score")
    if not isinstance(average, (int, float)):
        average = round(sum(score_values) / len(score_values), 2) if score_values else 0.0

    print("=" * 72)
    print(f"특허: {validation.get('patent_id')} | {str(validation.get('title', ''))[:40]}")
    print(f"Workflow: {result.get('workflow_type')} | Status: {result.get('status')}")
    print("=" * 72)
    print(f"종합 평균: {average}/5")
    print(f"평가 항목 수: {len(scores)}")

    if market:
        print("\n[시장]")
        print(f"  섹터: {market.get('sector')} ({market.get('c2_code')})")
        print(f"  점수: {market.get('score')}/5")

    low_items = [item for item in scores if isinstance(item.get("score"), (int, float)) and item["score"] <= 2]
    if low_items:
        print("\n[추가 확인 항목]")
        for item in low_items:
            print(f"  - {item.get('item')}: {item.get('score')}/5")

    print("\n[노드 실행]")
    for node in result.get("node_trace") or []:
        print(
            f"  {node.get('node'):<24} {node.get('status'):<8} "
            f"{node.get('elapsed_seconds'):>6}s  {node.get('message', '')}"
        )


def main() -> None:
    args = parse_args()
    total_start = time.time()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'=' * 72}")
    print(f"Agentic workflow 시작: {now}")
    print(f"{'=' * 72}")

    input_files = resolve_input_files(args.input_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    options = build_workflow_options(args)
    workflow = PatentValuationWorkflow(options)

    print(f"\n실행 프로필: {args.profile}")
    print(
        "활성 기능: "
        f"market={options.enable_market}, "
        f"llm={options.enable_llm}, "
        f"business_rag={options.enable_business_rag}, "
        f"similar={options.enable_similar_analysis}, "
        f"similar_kipris_crawler={options.similar_use_kipris_crawler}, "
        f"similar_refresh={options.similar_force_refresh}, "
        f"similar_llm={options.similar_use_llm}, "
        f"pdf_metadata={options.enable_pdf_metadata_extraction}"
    )
    print(f"\n처리 대상 파일 수: {len(input_files)}")
    for idx, source_path in enumerate(input_files, 1):
        print(f"\n{'-' * 72}")
        print(f"[{idx}/{len(input_files)}] {source_path.name}")
        print(f"{'-' * 72}")

        result = workflow.run(load_json(source_path))
        print_result_summary(result)

        out_path = output_path_for_result(source_path, result)
        out_path.parent.mkdir(parents=True, exist_ok=True)
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
