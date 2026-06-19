"""Command line entrypoint for eval_logic RabbitMQ workers."""

from __future__ import annotations

import argparse
import logging
import sys
import threading
from pathlib import Path

for path in (Path(__file__).resolve().parents[1], Path(__file__).resolve().parents[3]):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from pre_application_valuation.worker import pre_evaluation_rabbit_worker
from workers.config import load_worker_config
from workers.patent_extract_worker import PatentExtractHandler
from workers.rabbitmq import RabbitWorker
from workers.report_worker import ReportGenerateHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run eval_logic RabbitMQ workers.")
    parser.add_argument(
        "--worker",
        choices=["report", "patent-extract", "pre-evaluation", "all"],
        default="all",
        help="Worker type to run.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    config = load_worker_config()

    if args.worker == "report":
        _report_worker(config).run_forever()
        return
    if args.worker == "patent-extract":
        _patent_extract_worker(config).run_forever()
        return
    if args.worker == "pre-evaluation":
        pre_evaluation_rabbit_worker(config).run_forever()
        return

    threads = [
        threading.Thread(
            target=_report_worker(config).run_forever,
            name="report-worker",
            daemon=False,
        ),
        threading.Thread(
            target=_patent_extract_worker(config).run_forever,
            name="patent-extract-worker",
            daemon=False,
        ),
        threading.Thread(
            target=pre_evaluation_rabbit_worker(config).run_forever,
            name="pre-evaluation-worker",
            daemon=False,
        ),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def _max_attempts(value: int) -> int | None:
    return value if value > 0 else None


def _report_worker(config) -> RabbitWorker:
    return RabbitWorker(
        config,
        config.report_queue,
        ReportGenerateHandler(config),
        max_attempts=_max_attempts(config.report_max_attempts),
        dlq_queue_name=config.report_dlq,
    )


def _patent_extract_worker(config) -> RabbitWorker:
    return RabbitWorker(
        config,
        config.patent_extract_queue,
        PatentExtractHandler(config),
        max_attempts=_max_attempts(config.patent_extract_max_attempts),
        dlq_queue_name=config.patent_extract_dlq,
    )


if __name__ == "__main__":
    main()
