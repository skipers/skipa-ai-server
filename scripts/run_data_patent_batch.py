"""Batch parse and re-evaluate PDFs under ``skipa-ai-server/data``.

Expected layout:

  data/
    10-1959619/
      patent.pdf

Outputs:

  data/<registration_number>/parsed.json
  data/<registration_number>/report.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


SERVER_ROOT = Path(__file__).resolve().parents[1]
EVAL_SRC = SERVER_ROOT / "eval_logic" / "src"
if str(EVAL_SRC) not in sys.path:
    sys.path.insert(0, str(EVAL_SRC))

from agent.patent_valuation_graph import PatentValuationWorkflow, PatentValuationWorkflowOptions
from services.evidence_collection_service import PatentMetadataExtractionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="data/<등록번호>/patent.pdf를 파싱하고 풀옵션 재평가 보고서를 생성합니다."
    )
    parser.add_argument(
        "--data-root",
        default=str(SERVER_ROOT / "data"),
        help="등록번호별 폴더가 들어 있는 루트. 기본값: skipa-ai-server/data",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="특정 등록번호만 처리합니다. 여러 번 지정 가능.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="parsed.json과 report.json이 모두 있으면 건너뜁니다.",
    )
    return parser.parse_args()


def find_patent_dirs(data_root: Path, only: list[str]) -> list[Path]:
    if not data_root.exists():
        raise FileNotFoundError(f"data root를 찾을 수 없습니다: {data_root}")
    allow = set(only)
    patent_dirs = []
    for path in sorted(data_root.iterdir()):
        if not path.is_dir():
            continue
        if allow and path.name not in allow:
            continue
        if (path / "patent.pdf").exists():
            patent_dirs.append(path)
    if not patent_dirs:
        raise FileNotFoundError(f"처리할 patent.pdf가 없습니다: {data_root}")
    return patent_dirs


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_workflow() -> PatentValuationWorkflow:
    options = PatentValuationWorkflowOptions(
        enable_market=True,
        enable_auto=True,
        enable_llm=True,
        enable_pdf_metadata_extraction=True,
        enable_business_rag=True,
        enable_similar_analysis=True,
        similar_use_llm=True,
        rag_top_k=5,
        fail_on_validation_error=True,
        enable_human_review=False,
    )
    return PatentValuationWorkflow(options)


def payload_for_workflow(parsed: dict[str, Any], pdf_path: Path) -> dict[str, Any]:
    normalized = parsed.get("normalized_patent")
    if not isinstance(normalized, dict):
        raise ValueError("parsed result에 normalized_patent가 없습니다.")
    payload = dict(normalized)
    payload["source_pdf"] = str(pdf_path)
    return payload


def process_one(
    patent_dir: Path,
    metadata_service: PatentMetadataExtractionService,
    workflow: PatentValuationWorkflow,
) -> dict[str, Any]:
    started = time.time()
    pdf_path = patent_dir / "patent.pdf"
    parsed_path = patent_dir / "parsed.json"
    report_path = patent_dir / "report.json"

    parsed = metadata_service.extract_from_pdf(pdf_path)
    parsed["batch_metadata"] = {
        "registration_dir": patent_dir.name,
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
        "parser": "PatentMetadataExtractionService.extract_from_pdf",
    }
    write_json(parsed_path, parsed)

    result = workflow.run(payload_for_workflow(parsed, pdf_path))
    result.setdefault("artifacts", {})
    result["artifacts"].update(
        {
            "source_pdf_path": str(pdf_path),
            "parsed_json_path": str(parsed_path),
            "report_json_path": str(report_path),
        }
    )
    write_json(report_path, result)

    return {
        "registration_dir": patent_dir.name,
        "status": result.get("status"),
        "parsed_json": str(parsed_path),
        "report_json": str(report_path),
        "elapsed_seconds": round(time.time() - started, 2),
        "errors": result.get("errors") or [],
    }


def main() -> None:
    args = parse_args()
    data_root = Path(args.data_root).expanduser().resolve()
    patent_dirs = find_patent_dirs(data_root, args.only)
    metadata_service = PatentMetadataExtractionService()
    workflow = build_workflow()
    summaries = []
    failed = []

    print(f"data root: {data_root}")
    print(f"targets: {len(patent_dirs)}")
    print("options: market/auto/llm/pdf_metadata/business_rag/similar/similar_llm 모두 활성화")

    for index, patent_dir in enumerate(patent_dirs, 1):
        parsed_path = patent_dir / "parsed.json"
        report_path = patent_dir / "report.json"
        if args.skip_existing and parsed_path.exists() and report_path.exists():
            print(f"[{index}/{len(patent_dirs)}] {patent_dir.name} skip-existing")
            continue

        print(f"\n[{index}/{len(patent_dirs)}] {patent_dir.name}")
        try:
            summary = process_one(patent_dir, metadata_service, workflow)
            summaries.append(summary)
            print(
                f"  done status={summary['status']} "
                f"elapsed={summary['elapsed_seconds']}s"
            )
            print(f"  parsed: {summary['parsed_json']}")
            print(f"  report: {summary['report_json']}")
            if summary["errors"]:
                print(f"  workflow errors: {summary['errors']}")
        except Exception as exc:
            failure = {
                "registration_dir": patent_dir.name,
                "error": str(exc),
                "elapsed_seconds": None,
            }
            failed.append(failure)
            print(f"  failed: {exc}")

    batch_summary = {
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "data_root": str(data_root),
        "target_count": len(patent_dirs),
        "success_count": len(summaries),
        "failed_count": len(failed),
        "results": summaries,
        "failures": failed,
    }
    summary_path = data_root / "batch_summary.json"
    write_json(summary_path, batch_summary)
    print(f"\nsummary: {summary_path}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
