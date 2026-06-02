#!/usr/bin/env python3
"""Preprocess chatbot data and rebuild local vectorstores.

Examples:
  scripts/preprocess_chatbot_data.sh
  scripts/preprocess_chatbot_data.sh --mode auto-audit
  scripts/preprocess_chatbot_data.sh --mode application-preprocess
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
            "application-status",
            "all",
        ],
        default="refresh",
        help=(
            "refresh=approved vectorstore rebuild, auto-audit=audit+auto exclude+refresh, "
            "audit=audit only, normalize-wiki=rewrite approved wiki markdown, "
            "application-preprocess=preprocess application pack, all=chatbot refresh+application preprocess, "
            "status=show status"
        ),
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Use raw documents instead of human-approved documents for refresh mode.",
    )
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
