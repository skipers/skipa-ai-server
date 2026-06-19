#!/usr/bin/env python3
"""Generate missing patent valuation reports into the local MinIO-shaped tree."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import traceback
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SERVER_ROOT = Path(__file__).resolve().parents[1]
EVAL_LOGIC_ROOT = SERVER_ROOT / "eval_logic"
EVAL_LOGIC_SRC = EVAL_LOGIC_ROOT / "src"
if str(EVAL_LOGIC_SRC) not in sys.path:
    sys.path.insert(0, str(EVAL_LOGIC_SRC))

import agent.patent_valuation_graph as valuation_graph
from agent.patent_valuation_graph import PatentValuationWorkflow
from core.env import load_runtime_env
from core.report_payload import frontend_report_payload
from services.report_generation_service import ReportGenerationOptions, build_workflow_options


@dataclass(frozen=True)
class PatentRow:
    patent_id: str
    title: str
    registration_number: str
    application_number: str
    publication_number: str
    announcement_number: str


def norm_no(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", unicodedata.normalize("NFKC", value or "")).upper()


def sort_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.isdigit() else (1, value)


def load_rows(list_csv: Path) -> list[PatentRow]:
    rows: list[PatentRow] = []
    with list_csv.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.reader(file):
            if not row or not row[0].strip():
                continue
            rows.append(
                PatentRow(
                    patent_id=row[0].strip(),
                    title=row[1].strip() if len(row) > 1 else "",
                    registration_number=row[2].strip() if len(row) > 2 else "",
                    application_number=row[3].strip() if len(row) > 3 else "",
                    publication_number=row[4].strip() if len(row) > 4 else "",
                    announcement_number=row[5].strip() if len(row) > 5 else "",
                )
            )
    return rows


def has_report(patents_dir: Path, patent_id: str) -> bool:
    return (patents_dir / patent_id / "reports" / patent_id / "report.json").is_file()


def missing_rows(rows: list[PatentRow], patents_dir: Path) -> list[PatentRow]:
    return sorted(
        [row for row in rows if not has_report(patents_dir, row.patent_id)],
        key=lambda row: sort_key(row.patent_id),
    )


def parse_ids(raw_values: list[str]) -> set[str]:
    values: set[str] = set()
    for raw in raw_values:
        for part in raw.split(","):
            value = part.strip()
            if value:
                values.add(value)
    return values


def select_targets(
    rows: list[PatentRow],
    patents_dir: Path,
    *,
    limit: int,
    offset: int,
    only_ids: set[str],
) -> list[PatentRow]:
    if only_ids:
        by_id = {row.patent_id: row for row in rows}
        missing = [by_id[patent_id] for patent_id in sorted(only_ids, key=sort_key) if patent_id in by_id]
        return [row for row in missing if not has_report(patents_dir, row.patent_id)]

    candidates = missing_rows(rows, patents_dir)
    if offset:
        candidates = candidates[offset:]
    if limit > 0:
        candidates = candidates[:limit]
    return candidates


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON top-level value must be an object: {path}")
    return payload


def save_report(target_path: Path, result: dict[str, Any]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    payload = frontend_report_payload(result)
    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def archive_report(reports_dir: Path | None, row: PatentRow, result: dict[str, Any]) -> str | None:
    if reports_dir is None:
        return None
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = result.get("report") if isinstance(result.get("report"), dict) else {}
    patent = report.get("patent") if isinstance(report.get("patent"), dict) else {}
    registration_number = (
        patent.get("registration_number")
        or row.registration_number
        or row.application_number
        or row.patent_id
    )
    archive_path = reports_dir / f"{registration_number}.json"
    save_report(archive_path, result)
    return str(archive_path.relative_to(SERVER_ROOT))


def write_manifest(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "records": records,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate missing report.json files under patents/{patentId}/reports/{patentId}."
    )
    parser.add_argument("--limit", type=int, default=40, help="Number of missing patents to process.")
    parser.add_argument("--offset", type=int, default=0, help="Offset within the sorted missing patent list.")
    parser.add_argument("--only-id", action="append", default=[], help="Specific patent ID(s), comma-separated allowed.")
    parser.add_argument("--profile", choices=["quick", "full"], default="full")
    parser.add_argument("--rag-top-k", type=int, default=None)
    parser.add_argument("--similar-max-pages", type=int, default=5)
    parser.add_argument("--similar-max-results", type=int, default=10)
    parser.add_argument(
        "--similar-collection-limit",
        type=int,
        default=None,
        help="Override the workflow's minimum KIPRIS detail collection limit.",
    )
    parser.add_argument("--similar-use-llm", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument(
        "--disable-similar",
        action="store_true",
        help="Skip KIPRIS similar-patent collection for fast local batch generation.",
    )
    parser.add_argument("--enable-market", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--enable-llm", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--enable-business-rag", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument(
        "--fail-on-validation-error",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Stop workflow before valuation if input validation fails. Default: false.",
    )
    parser.add_argument(
        "--archive-reports-2",
        action="store_true",
        help="Also write a registration-number copy under reports_2/.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_runtime_env()

    list_csv = SERVER_ROOT / "list.csv"
    patents_dir = SERVER_ROOT / "patents"
    rows = load_rows(list_csv)
    only_ids = parse_ids(args.only_id)
    targets = select_targets(
        rows,
        patents_dir,
        limit=args.limit,
        offset=args.offset,
        only_ids=only_ids,
    )

    print(f"total_patents={len(rows)}")
    print(f"missing_reports={len(missing_rows(rows, patents_dir))}")
    print(f"selected={len(targets)}")
    for row in targets:
        print(f"- {row.patent_id} {row.registration_number} {row.title}")

    if args.dry_run:
        return 0

    options = build_workflow_options(
        ReportGenerationOptions(
            profile=args.profile,
            enable_market=args.enable_market,
            enable_llm=args.enable_llm,
            enable_business_rag=args.enable_business_rag,
            similar_use_llm=args.similar_use_llm,
            rag_top_k=args.rag_top_k,
            local_output=True,
        )
    )
    options.similar_max_pages = args.similar_max_pages
    options.similar_max_results = args.similar_max_results
    options.fail_on_validation_error = args.fail_on_validation_error
    if args.similar_collection_limit is not None:
        valuation_graph.SIMILAR_PATENT_COLLECTION_LIMIT = max(0, args.similar_collection_limit)
    if args.disable_similar:
        options.enable_similar_analysis = False

    workflow = PatentValuationWorkflow(options)
    records: list[dict[str, Any]] = []
    manifest_path = SERVER_ROOT / "patents" / "_report_generation_manifest_latest.json"
    reports_dir = SERVER_ROOT / "reports_2" if args.archive_reports_2 else None

    for index, row in enumerate(targets, start=1):
        source_path = patents_dir / row.patent_id / "parsed.json"
        target_path = patents_dir / row.patent_id / "reports" / row.patent_id / "report.json"
        started = time.time()
        print(f"\n[{index}/{len(targets)}] start patent_id={row.patent_id} reg={row.registration_number}")
        record: dict[str, Any] = {
            "patent_id": row.patent_id,
            "report_id": row.patent_id,
            "registration_number": row.registration_number,
            "title": row.title,
            "source": str(source_path.relative_to(SERVER_ROOT)),
            "target": str(target_path.relative_to(SERVER_ROOT)),
            "status": "running",
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            if not source_path.is_file():
                raise FileNotFoundError(f"Missing parsed input: {source_path}")
            result = workflow.run(load_json(source_path))
            save_report(target_path, result)
            archive_path = archive_report(reports_dir, row, result)
            record.update(
                {
                    "status": "success",
                    "workflow_status": result.get("status"),
                    "archive": archive_path,
                    "elapsed_seconds": round(time.time() - started, 2),
                    "errors": result.get("errors") or [],
                }
            )
            print(
                f"[{index}/{len(targets)}] success patent_id={row.patent_id} "
                f"elapsed={record['elapsed_seconds']}s target={record['target']}"
            )
        except Exception as exc:
            record.update(
                {
                    "status": "failed",
                    "elapsed_seconds": round(time.time() - started, 2),
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
            print(f"[{index}/{len(targets)}] failed patent_id={row.patent_id}: {exc}", file=sys.stderr)
        records.append(record)
        write_manifest(manifest_path, records)

    success_count = sum(1 for record in records if record.get("status") == "success")
    failed_count = len(records) - success_count
    print(f"\ncompleted selected={len(records)} success={success_count} failed={failed_count}")
    print(f"manifest={manifest_path.relative_to(SERVER_ROOT)}")
    return 1 if failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
