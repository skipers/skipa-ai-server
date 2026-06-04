#!/usr/bin/env python3
"""Preprocess chatbot data and rebuild local vectorstores.

Examples:
  scripts/preprocess_chatbot_data.sh
  scripts/preprocess_chatbot_data.sh --mode auto-audit
  scripts/preprocess_chatbot_data.sh --mode application-preprocess
  scripts/preprocess_chatbot_data.sh --mode application-feedback --opinion-file "data/patent_application_official_pack/downloads/특허거절의견서.pdf"
  scripts/preprocess_chatbot_data.sh --mode all
  scripts/preprocess_chatbot_data.sh --mode status
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
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
            "application-status",
            "all",
        ],
        default="refresh",
        help=(
            "refresh=approved vectorstore rebuild, auto-audit=audit+auto exclude+refresh, "
            "audit=audit only, normalize-wiki=rewrite approved wiki markdown, "
            "application-preprocess=preprocess application pack, all=chatbot refresh+application preprocess, "
            "application-feedback=create rejection/opinion feedback HTML and refresh application index, "
            "status=show status"
        ),
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Use raw documents instead of human-approved documents for refresh mode.",
    )
    parser.add_argument("--title", default="특허거절의견서 기반 출원 피드백", help="Feedback report title.")
    parser.add_argument("--patent-id", default=None, help="Patent ID to connect with original/report data.")
    parser.add_argument("--opinion-file", default=None, help="Rejection opinion or office action PDF/document path.")
    parser.add_argument("--opinion-text", default=None, help="Inline rejection opinion text.")
    parser.add_argument("--source-report", default=None, help="Existing generated patent report path to connect.")
    parser.add_argument("--reviewer", default="cli", help="Feedback report reviewer name.")
    parser.add_argument("--notes", default=None, help="Optional notes for feedback metadata.")
    args = parser.parse_args()

    from chatbot.app.vectorstore import (
        auto_audit_apply_and_refresh,
        normalize_wiki_context_files,
        refresh_vectorstores,
        run_audit,
        vectorstore_status,
    )
    from chatbot.app.application_data import (
        application_external_status,
        application_index_status,
        create_application_feedback_report,
        preprocess_application_pack,
    )

    if args.mode == "status":
        _print_json(
            {
                "status": "ok",
                "vectorstore": vectorstore_status(),
                "application": application_index_status(),
                "application_external": application_external_status(),
            }
        )
        return 0
    if args.mode == "application-status":
        _print_json({"status": "ok", "application": application_index_status(), "external": application_external_status()})
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
