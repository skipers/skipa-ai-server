"""Wiki audit agent compatibility helpers."""

from __future__ import annotations

from typing import Any

from .wiki_graph import run_wiki_audit_graph, wiki_audit_graph_mermaid


def run_wiki_agent(**kwargs: Any) -> dict[str, Any]:
    return run_wiki_audit_graph(**kwargs)


def wiki_workflow_mermaid() -> str:
    return wiki_audit_graph_mermaid()
