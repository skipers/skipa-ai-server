#!/usr/bin/env python3
"""Preprocess chatbot data and rebuild local vectorstores.

Examples:
  scripts/preprocess_chatbot_data.sh
  scripts/preprocess_chatbot_data.sh --mode auto-audit
  scripts/preprocess_chatbot_data.sh --mode application-preprocess
  scripts/preprocess_chatbot_data.sh --mode application-feedback --opinion-file "data/patent_application_official_pack/downloads/특허거절의견서.pdf"
  scripts/preprocess_chatbot_data.sh --mode application-case --original-pdf "failed.pdf" --rejection-file "notice.pdf"
  scripts/preprocess_chatbot_data.sh --mode application-case-refresh --case-id "failed_20260604"
  scripts/preprocess_chatbot_data.sh --mode application-case-generate --case-id "failed_20260604"
  scripts/preprocess_chatbot_data.sh --mode visual-index
  scripts/preprocess_chatbot_data.sh --mode nightly-reindex
  scripts/preprocess_chatbot_data.sh --mode all
  scripts/preprocess_chatbot_data.sh --mode status
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _print_json(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Preprocess SKIPA chatbot data.")
    parser.add_argument(
        "--mode",
        choices=[
            "refresh",
            "auto-audit",
            "audit",
            "status",
            "normalize-wiki",
            "application-preprocess",
            "application-feedback",
            "application-case",
            "application-case-refresh",
            "application-case-generate",
            "application-case-report",
            "application-status",
            "visual-index",
            "nightly-reindex",
            "all",
        ],
        default="refresh",
        help=(
            "refresh=approved vectorstore rebuild, auto-audit=audit+auto exclude+refresh, "
            "audit=audit only, normalize-wiki=rewrite approved wiki markdown, "
            "application-preprocess=preprocess application pack, all=chatbot refresh+application preprocess, "
            "application-feedback=create rejection/opinion feedback HTML and refresh application index, "
            "visual-index=extract missing patent original visuals and upsert to Qdrant, "
            "nightly-reindex=auto-audit wiki and Qdrant refresh for every chatbot index, "
            "status=show status"
        ),
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Use raw documents instead of human-approved documents for refresh mode.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild for incremental modes such as visual-index.",
    )
    parser.add_argument("--title", default="특허거절의견서 기반 출원 피드백", help="Feedback report title.")
    parser.add_argument("--patent-id", default=None, help="Patent ID to connect with original/report data.")
    parser.add_argument("--opinion-file", default=None, help="Rejection opinion or office action PDF/document path.")
    parser.add_argument("--opinion-text", default=None, help="Inline rejection opinion text.")
    parser.add_argument("--source-report", default=None, help="Existing generated patent report path to connect.")
    parser.add_argument("--case-id", default=None, help="Patent application failed-case ID.")
    parser.add_argument("--original-pdf", default=None, help="Failed patent original PDF path for application-case mode.")
    parser.add_argument("--rejection-file", default=None, help="Optional rejection notice/reason file path for application-case mode.")
    parser.add_argument("--report-path", default=None, help="Generated re-evaluation report path to save into a failed case.")
    parser.add_argument("--report-text", default=None, help="Generated report text/markdown to save into a failed case.")
    parser.add_argument("--reviewer", default="cli", help="Feedback report reviewer name.")
    parser.add_argument("--notes", default=None, help="Optional notes for feedback metadata.")
    args = parser.parse_args()

    from chatbot.app.vectorstore import (
        auto_audit_apply_and_refresh,
        nightly_reindex_all,
        normalize_wiki_context_files,
        refresh_vectorstores,
        run_audit,
        vectorstore_status,
    )
    from chatbot.app.application_data import (
        application_external_status,
        application_index_status,
        create_failed_patent_case,
        create_application_feedback_report,
        failed_patent_case_index_status,
        generate_failed_patent_case_report,
        list_failed_patent_cases,
        preprocess_application_pack,
        refresh_failed_patent_case_index,
        save_failed_patent_case_report,
    )
    from chatbot.app.visual_data import build_missing_patent_visual_indexes, patent_visual_index_status

    if args.mode == "status":
        _print_json(
            {
                "status": "ok",
                "vectorstore": vectorstore_status(),
                "visual_vectorstore": patent_visual_index_status(),
                "application": application_index_status(),
                "application_external": application_external_status(),
            }
        )
        return 0
    if args.mode == "application-status":
        _print_json(
            {
                "status": "ok",
                "application": application_index_status(),
                "failed_patent_cases": list_failed_patent_cases(),
                "external": application_external_status(),
            }
        )
        return 0
    if args.mode == "nightly-reindex":
        _print_json(nightly_reindex_all())
        return 0
    if args.mode == "visual-index":
        _print_json(build_missing_patent_visual_indexes(force=args.force))
        return 0
    if args.mode == "application-preprocess":
        _print_json(preprocess_application_pack(refresh_index=True))
        return 0
    if args.mode == "application-feedback":
        _print_json(
            create_application_feedback_report(
                title=args.title,
                patent_id=args.patent_id,
                opinion_text=args.opinion_text,
                opinion_file_path=args.opinion_file,
                source_report_path=args.source_report,
                reviewer=args.reviewer,
                notes=args.notes,
                refresh_index=True,
            )
        )
        return 0
    if args.mode == "application-case":
        if not args.original_pdf:
            raise SystemExit("--original-pdf is required for --mode application-case")
        _print_json(
            create_failed_patent_case(
                case_id=args.case_id,
                title=args.title,
                original_pdf_path=args.original_pdf,
                rejection_reason_text=args.opinion_text,
                rejection_file_path=args.rejection_file,
                reviewer=args.reviewer,
                notes=args.notes,
                refresh_index=True,
            )
        )
        return 0
    if args.mode == "application-case-refresh":
        if not args.case_id:
            raise SystemExit("--case-id is required for --mode application-case-refresh")
        _print_json(refresh_failed_patent_case_index(args.case_id))
        return 0
    if args.mode == "application-case-generate":
        if not args.case_id:
            raise SystemExit("--case-id is required for --mode application-case-generate")
        _print_json(generate_failed_patent_case_report(args.case_id, title=args.title, refresh_index=True))
        return 0
    if args.mode == "application-case-report":
        if not args.case_id:
            raise SystemExit("--case-id is required for --mode application-case-report")
        _print_json(
            save_failed_patent_case_report(
                args.case_id,
                title=args.title,
                report_text=args.report_text,
                source_report_path=args.report_path,
                refresh_index=True,
            )
        )
        return 0
    if args.mode == "audit":
        _print_json(run_audit())
        return 0
    if args.mode == "normalize-wiki":
        _print_json(normalize_wiki_context_files())
        return 0
    if args.mode == "auto-audit":
        _print_json(auto_audit_apply_and_refresh(refresh_vectorstore=True))
        return 0
    if args.mode == "all":
        wiki_normalize = normalize_wiki_context_files()
        vectorstore = refresh_vectorstores(use_reviewed=not args.raw)
        application = preprocess_application_pack(refresh_index=True)
        _print_json(
            {
                "status": "preprocessed",
                "use_reviewed": not args.raw,
                "wiki_normalize": wiki_normalize,
                "vectorstore": vectorstore,
                "application": application,
            }
        )
        return 0

    wiki_normalize = normalize_wiki_context_files() if not args.raw else {"status": "skipped", "reason": "raw refresh"}
    result = refresh_vectorstores(use_reviewed=not args.raw)
    _print_json({"status": "preprocessed", "use_reviewed": not args.raw, "wiki_normalize": wiki_normalize, "result": result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
