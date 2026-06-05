"""Render the patent valuation LangGraph workflow.

Usage:
  python src/apps/cli/visualize_agent_graph.py
  python src/apps/cli/visualize_agent_graph.py --output-dir data/runtime_artifacts/graphs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent.patent_valuation_graph import PatentValuationWorkflow
from core.paths import RUNTIME_GRAPH_DIR


DEFAULT_OUTPUT_DIR = RUNTIME_GRAPH_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the patent valuation LangGraph workflow.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to write graph files. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--name",
        default="patent_valuation_graph",
        help="Base file name for rendered graph files.",
    )
    parser.add_argument(
        "--skip-png",
        action="store_true",
        help="Only write Mermaid and ASCII graph files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    runner = PatentValuationWorkflow()._build_runner()
    if not hasattr(runner, "get_graph"):
        raise RuntimeError(
            "LangGraph runner was not created. Activate the project venv and ensure langgraph is installed."
        )

    graph = runner.get_graph()
    mermaid_path = output_dir / f"{args.name}.mmd"
    ascii_path = output_dir / f"{args.name}.txt"
    png_path = output_dir / f"{args.name}.png"

    mermaid_path.write_text(graph.draw_mermaid(), encoding="utf-8")
    print(f"Mermaid graph written: {mermaid_path}")

    try:
        ascii_path.write_text(graph.draw_ascii(), encoding="utf-8")
        print(f"ASCII graph written:   {ascii_path}")
    except Exception as exc:
        print(f"ASCII render skipped: {exc}")

    if args.skip_png:
        return

    try:
        graph.draw_mermaid_png(output_file_path=str(png_path))
        print(f"PNG graph written:     {png_path}")
    except Exception as exc:
        print(f"PNG render skipped: {exc}")
        print("You can still paste the .mmd file into https://mermaid.live/ or run with --skip-png.")


if __name__ == "__main__":
    main()
