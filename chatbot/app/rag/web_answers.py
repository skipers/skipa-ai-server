"""Optional web-search evidence for the chatbot agent."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .web_quality import web_result_relevance
from .config import (
    ENABLE_WEB_SEARCH,
    TAVILY_API_KEY,
    TAVILY_API_URL,
    WEB_SEARCH_API_KEY,
    WEB_SEARCH_API_URL,
    WEB_SEARCH_BLOCKLIST_DOMAINS,
    WEB_SEARCH_LIMIT,
    WEB_SEARCH_TIMEOUT,
)


def _valid_key(value: str | None) -> bool:
    return bool(value and value.strip() and not value.strip().upper().startswith("YOUR_"))


def _blocked(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == domain or host.endswith("." + domain) for domain in WEB_SEARCH_BLOCKLIST_DOMAINS)


def _normalize_results(query: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for item in items:
        url = str(item.get("url") or item.get("link") or "")
        if url and _blocked(url):
            continue
        title = str(item.get("title") or "web result")
        snippet = str(item.get("content") or item.get("snippet") or item.get("description") or "")
        relevance = web_result_relevance(
            query=query,
            title=title,
            snippet=snippet,
            url=url,
            provider=str(item.get("provider") or item.get("source") or ""),
        )
        if not relevance["relevant"]:
            continue
        results.append(
            {
                "title": title,
                "url": url or None,
                "snippet": snippet,
                "source_type": "WEB",
                "relevance": relevance,
            }
        )
    return results[:WEB_SEARCH_LIMIT]


def search_web(query: str) -> dict[str, Any]:
    if not ENABLE_WEB_SEARCH:
        return {"enabled": False, "provider": None, "results": [], "error": "web search disabled"}

    if WEB_SEARCH_API_URL:
        payload = {"query": query, "limit": WEB_SEARCH_LIMIT}
        headers = {"Content-Type": "application/json"}
        if WEB_SEARCH_API_KEY:
            headers["Authorization"] = f"Bearer {WEB_SEARCH_API_KEY}"
        try:
            request = Request(
                WEB_SEARCH_API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urlopen(request, timeout=WEB_SEARCH_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
            items = data.get("results") if isinstance(data, dict) else data
            return {"enabled": True, "provider": "custom", "results": _normalize_results(query, list(items or [])), "error": None}
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {"enabled": True, "provider": "custom", "results": [], "error": str(exc)}

    if _valid_key(TAVILY_API_KEY):
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": WEB_SEARCH_LIMIT,
            "include_answer": False,
            "search_depth": "advanced",
        }
        try:
            request = Request(
                TAVILY_API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=WEB_SEARCH_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
            return {
                "enabled": True,
                "provider": "tavily",
                "results": _normalize_results(query, list(data.get("results") or [])),
                "error": None,
            }
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {"enabled": True, "provider": "tavily", "results": [], "error": str(exc)}

    return {"enabled": True, "provider": None, "results": [], "error": "web search key not configured"}
