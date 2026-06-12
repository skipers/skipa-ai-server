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
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.patent_valuation_graph import PatentValuationWorkflow, PatentValuationWorkflowOptions, default_similar_date_from
from apps.api.storage import object_storage
from core.paths import INPUT_SAMPLE_FILE, RESULTS_DIR, SAMPLE_INPUT_DIR
from core.report_payload import frontend_report_payload
from core.report_naming import safe_registration_number_from_result

OUTPUT_DIR = RESULTS_DIR
SERVER_DATA_DIR = Path(__file__).resolve().parents[4] / "data"


def _default_patent_prefix() -> str:
    return (os.getenv("MINIO_PATENT_PREFIX", "patents").strip("/") or "patents")


DEFAULT_INPUT_LIST_PREFIX = f"{_default_patent_prefix()}/"
DEFAULT_OUTPUT_KEY_TEMPLATE = f"{_default_patent_prefix()}/{{patent_id}}/reports/{{report_id}}/report.json"


@dataclass(frozen=True)
class InputSource:
    """로컬 파일과 MinIO 객체를 같은 workflow 입력 단위로 표현합니다."""

    backend: str
    label: str
    path: Path | None = None
    object_key: str | None = None


def parse_args() -> argparse.Namespace:
    """CLI 실행 범위와 입력 경로를 읽습니다."""
    parser = argparse.ArgumentParser(description="특허 가치평가 agentic workflow를 로컬에서 실행합니다.")
    parser.add_argument(
        "input_path",
        nargs="?",
        help=(
            "입력 JSON 파일, data/<등록번호> 디렉터리, data 루트, 또는 MinIO object key. "
            "생략하면 input_sample/parsed.json 테스트 데이터를 우선 실행합니다."
        ),
    )
    parser.add_argument(
        "--input-prefix",
        default=os.getenv("EVAL_LOGIC_INPUT_LIST_PREFIX", DEFAULT_INPUT_LIST_PREFIX),
        help="MinIO 입력 목록을 조회할 prefix입니다. 기본값: patents/",
    )
    parser.add_argument(
        "--output-key-template",
        default=os.getenv("EVAL_LOGIC_OUTPUT_OBJECT_KEY_TEMPLATE")
        or os.getenv("EVAL_LOGIC_REPORT_OBJECT_KEY_TEMPLATE")
        or DEFAULT_OUTPUT_KEY_TEMPLATE,
        help="MinIO 결과 저장 object key template입니다. 사용 가능 변수: registration_number, patent_id, report_id",
    )
    parser.add_argument("--patent-id", default=os.getenv("EVAL_LOGIC_PATENT_ID"), help="백엔드 patent ID")
    parser.add_argument("--report-id", default=os.getenv("EVAL_LOGIC_REPORT_ID"), help="백엔드 report ID")
    parser.add_argument(
        "--local-output",
        action="store_true",
        help="MinIO가 설정되어 있어도 결과를 로컬 파일에 저장합니다.",
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
        similar_date_from=default_similar_date_from(),
        similar_date_to="",
        similar_use_llm=choose(args.similar_use_llm, is_full),
        enable_pdf_metadata_extraction=False,
        rag_top_k=args.rag_top_k,
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_source_json(source: InputSource) -> dict[str, Any]:
    if source.backend == "minio":
        if not source.object_key:
            raise ValueError("MinIO 입력 object key가 없습니다.")
        payload = object_storage.get_json(source.object_key)
        if not isinstance(payload, dict):
            raise ValueError(f"MinIO 입력 JSON을 읽을 수 없습니다: {source.object_key}")
        return payload
    if not source.path:
        raise ValueError("로컬 입력 경로가 없습니다.")
    return load_json(source.path)


def _input_sources_from_paths(input_path: str | None = None) -> list[InputSource]:
    return [
        InputSource("local", str(path), path=path)
        for path in resolve_input_files(input_path)
    ]


def _input_prefix_candidates(prefix: str) -> list[str]:
    base_prefix = prefix.lstrip("/")
    storage_prefix = str(getattr(object_storage, "prefix", "") or "").strip("/")
    prefixes = [base_prefix]
    if storage_prefix and not base_prefix.startswith(f"{storage_prefix}/"):
        prefixes.append(f"{storage_prefix}/{base_prefix}")
    return list(dict.fromkeys(prefixes))


def _strip_storage_prefix(object_key: str) -> str:
    key = object_key.strip("/")
    storage_prefix = str(getattr(object_storage, "prefix", "") or "").strip("/")
    if storage_prefix and key.startswith(f"{storage_prefix}/"):
        return key[len(storage_prefix) + 1 :]
    return key


def _input_sources_from_minio(prefix: str) -> list[InputSource]:
    if not object_storage.enabled():
        return []

    object_keys: list[str] = []
    for candidate_prefix in _input_prefix_candidates(prefix):
        object_keys.extend(
            key
            for key in object_storage.list_object_keys(candidate_prefix)
            if key.endswith("/parsed.json")
        )
    return [
        InputSource("minio", key, object_key=key)
        for key in sorted(dict.fromkeys(object_keys))
    ]


def resolve_input_sources(input_path: str | None = None, input_prefix: str = DEFAULT_INPUT_LIST_PREFIX) -> list[InputSource]:
    if input_path:
        candidate = Path(input_path)
        if candidate.exists():
            return _input_sources_from_paths(input_path)
        if object_storage.enabled():
            return [InputSource("minio", input_path, object_key=input_path.strip("/"))]
        raise FileNotFoundError(f"입력 경로를 찾을 수 없습니다: {input_path}")

    if INPUT_SAMPLE_FILE.exists():
        return _input_sources_from_paths(str(INPUT_SAMPLE_FILE))

    minio_sources = _input_sources_from_minio(input_prefix)
    if minio_sources:
        return minio_sources

    return _input_sources_from_paths(None)


def resolve_input_files(input_path: str | None = None) -> list[Path]:
    def parsed_files_in_data_root(root: Path) -> list[Path]:
        files = sorted(root.glob(f"{_default_patent_prefix()}/*/parsed.json"))
        if files:
            return files
        return sorted(path for path in root.glob("*/parsed.json") if path.parent.name.startswith("10-"))

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

    if INPUT_SAMPLE_FILE.exists():
        return [INPUT_SAMPLE_FILE]

    files = parsed_files_in_data_root(SERVER_DATA_DIR)
    if not files:
        files = sorted(SAMPLE_INPUT_DIR.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"기본 입력 JSON을 찾을 수 없습니다: {SERVER_DATA_DIR}")
    return files


def output_path_for_result(
    source_path: Path,
    result: dict[str, Any],
    report_id: str | None = None,
) -> Path:
    return OUTPUT_DIR / safe_registration_number_from_result(result) / "report.json"


def _registration_number_from_result(result: dict[str, Any]) -> str:
    return safe_registration_number_from_result(result)


def output_key_for_result(source: InputSource, result: dict[str, Any], args: argparse.Namespace) -> str:
    if not args.report_id:
        raise ValueError("MinIO report.json 저장에는 --report-id가 필요합니다.")

    if source.backend == "minio" and source.object_key:
        source_key = _strip_storage_prefix(source.object_key)
        if source_key.endswith("/parsed.json"):
            return f"{source_key.rsplit('/', 1)[0]}/reports/{args.report_id}/report.json"

    registration_number = _registration_number_from_result(result)
    return args.output_key_template.format(
        registration_number=registration_number,
        patent_id=args.patent_id or registration_number,
        report_id=args.report_id,
    ).strip("/")


def save_result(source: InputSource, result: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if object_storage.enabled() and not args.local_output:
        object_key = output_key_for_result(source, result, args)
        stored = object_storage.put_json(object_key, frontend_report_payload(result))
        if stored:
            print(f"\n결과 저장: MinIO {stored.get('bucket')}/{stored.get('object_key')}")
            return stored
        raise RuntimeError("MinIO 결과 저장에 실패했습니다.")

    if source.path:
        out_path = output_path_for_result(source.path, result, report_id=args.report_id)
    else:
        out_path = OUTPUT_DIR / safe_registration_number_from_result(result) / "report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as file:
        json.dump(frontend_report_payload(result), file, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")
    return {"backend": "local", "path": str(out_path)}


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

    input_sources = resolve_input_sources(args.input_path, args.input_prefix)
    if not args.local_output:
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
    print(f"\n처리 대상 파일 수: {len(input_sources)}")
    for idx, source in enumerate(input_sources, 1):
        print(f"\n{'-' * 72}")
        print(f"[{idx}/{len(input_sources)}] {source.label}")
        print(f"{'-' * 72}")

        result = workflow.run(load_source_json(source))
        print_result_summary(result)

        save_result(source, result, args)

    total = time.time() - total_start
    print(f"\n{'=' * 72}")
    print(f"전체 실행 시간: {total:.2f}초")
    if object_storage.enabled() and not args.local_output:
        print(f"결과 저장소: MinIO bucket={getattr(object_storage, 'bucket', '-')}")
    else:
        print(f"결과 저장 폴더: {OUTPUT_DIR}")
    print(f"{'=' * 72}\n")


if __name__ == "__main__":
    main()
