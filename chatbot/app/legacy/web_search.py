# -*- coding: utf-8 -*-

import hashlib
import html
import os
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from typing import Any, Dict, List, Tuple

import requests

try:
    from langchain_core.documents import Document
except Exception:  # pragma: no cover
    from langchain.docstore.document import Document


def now_ms() -> int:
    return int(time.time() * 1000)


def _hash(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]


def _strip_html(value: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", value or "", flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _decode_bing_url(url: str) -> str:
    parsed = urlparse(html.unescape(url or ""))
    if "bing.com" not in parsed.netloc or not parsed.path.startswith("/ck/"):
        return html.unescape(url or "")
    query = parse_qs(parsed.query)
    encoded = (query.get("u") or [""])[0]
    if encoded.startswith("a1"):
        try:
            import base64

            padded = encoded[2:] + "=" * ((4 - len(encoded[2:]) % 4) % 4)
            return base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8", errors="ignore")
        except Exception:
            return html.unescape(url or "")
    return unquote(encoded) if encoded else html.unescape(url or "")


def _blocked_domain(url: str) -> bool:
    blocked = [
        domain.strip().lower()
        for domain in os.getenv(
            "WEB_SEARCH_BLOCKLIST_DOMAINS",
            "namu.wiki,blog.naver.com,m.blog.naver.com,tistory.com,wikipedia.org,ko.wikipedia.org",
        ).split(",")
        if domain.strip()
    ]
    host = urlparse(url or "").netloc.lower()
    return any(host == domain or host.endswith("." + domain) for domain in blocked)


def _web_source_grade(url: str, title: str = "") -> Dict[str, str]:
    host = urlparse(url or "").netloc.lower()
    title_l = (title or "").lower()
    if not host:
        return {"grade": "LOW", "type": "미확인", "reason": "URL 확인 불가"}

    public_suffixes = (".go.kr", ".or.kr", ".re.kr", ".ac.kr", ".edu", ".gov")
    institution_keywords = ("kotra", "kisti", "kipris", "kipo", "kita", "stat", "data")
    news_keywords = ("news", "신문", "일보", "경제", "press", "daily")
    report_keywords = ("report", "research", "insight", "market", "industry", "analysis")

    if host.endswith(public_suffixes) or any(key in host for key in institution_keywords):
        return {"grade": "GOOD", "type": "공공/기관", "reason": "공공기관·학술·협회 계열 도메인"}
    if any(key in host for key in ("ieee", "acm", "springer", "sciencedirect", "nature")):
        return {"grade": "GOOD", "type": "논문/학술", "reason": "학술 출판·논문 도메인"}
    if any(key in host or key in title_l for key in news_keywords):
        return {"grade": "FAIR", "type": "뉴스", "reason": "뉴스/전문지 출처"}
    if any(key in host or key in title_l for key in report_keywords):
        return {"grade": "FAIR", "type": "산업/리포트", "reason": "산업 보고서·시장 분석 출처"}
    return {"grade": "FAIR", "type": "웹", "reason": "일반 웹 출처"}


def _question_needs_kipris(question: str) -> bool:
    q = (question or "").lower()
    return any(
        term in q
        for term in (
            "kipris",
            "키프리스",
            "유사 특허",
            "선행기술",
            "인용",
            "피인용",
            "특허 동향",
            "출원 동향",
            "경쟁 특허",
            "무효",
        )
    )


def _question_needs_kosis(question: str) -> bool:
    q = (question or "").lower()
    return any(
        term in q
        for term in (
            "kosis",
            "통계",
            "시장",
            "시장규모",
            "매출",
            "성장률",
            "산업",
            "동향",
            "수요",
        )
    )


def _compact_query(value: str, max_chars: int = 120) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    text = re.sub(r"\b(이|그|저)\s*특허\b", "특허", text)
    return text[:max_chars]


def _number_digits(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def _dedupe_rows(rows: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        key = (row.get("url") or row.get("link") or row.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def _bing_search(query: str, limit: int) -> List[Dict[str, str]]:
    resp = requests.get(
        "https://www.bing.com/search",
        params={"q": query, "count": max(limit, 5), "setlang": "ko-KR", "cc": "KR"},
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=int(os.getenv("WEB_SEARCH_TIMEOUT", "20")),
    )
    resp.raise_for_status()

    results: List[Dict[str, str]] = []
    blocks = re.split(r'<li class="b_algo"[^>]*>', resp.text)
    for block in blocks[1:]:
        if len(results) >= limit:
            break
        link_match = re.search(r"<h2[^>]*>.*?<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>.*?</h2>", block, flags=re.S | re.I)
        if not link_match:
            continue
        snippet_match = re.search(r"<p[^>]*>(.*?)</p>", block, flags=re.S | re.I)
        title = _strip_html(link_match.group(2))
        url = _decode_bing_url(link_match.group(1))
        snippet = _strip_html(snippet_match.group(1) if snippet_match else "")
        if not title or not url or url.startswith("javascript:") or _blocked_domain(url):
            continue
        results.append({"title": title, "snippet": snippet, "url": url})

    if results:
        return results

    seen_urls = set()
    for href, label in re.findall(r"<a[^>]+href=\"(https?://[^\"]+)\"[^>]*>(.*?)</a>", resp.text, flags=re.S | re.I):
        if len(results) >= limit:
            break
        title = _strip_html(label)
        url = _decode_bing_url(href)
        parsed = urlparse(url)
        if not title or len(title) < 8:
            continue
        if "bing.com" in parsed.netloc:
            continue
        if _blocked_domain(url):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        results.append({"title": title, "snippet": "", "url": url})
    return results


def _tavily_search(query: str, limit: int) -> List[Dict[str, Any]]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        return []

    blocked_domains = [
        domain.strip()
        for domain in os.getenv("WEB_SEARCH_BLOCKLIST_DOMAINS", "").split(",")
        if domain.strip()
    ]
    payload = {
        "query": query,
        "search_depth": os.getenv("TAVILY_SEARCH_DEPTH", "advanced"),
        "topic": os.getenv("TAVILY_TOPIC", "general"),
        "max_results": limit,
        "include_answer": False,
        "include_raw_content": False,
        "chunks_per_source": 1,
        "exclude_domains": blocked_domains,
    }
    resp = requests.post(
        os.getenv("TAVILY_API_URL", "https://api.tavily.com/search"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=int(os.getenv("WEB_SEARCH_TIMEOUT", "20")),
    )
    resp.raise_for_status()
    payload = resp.json()
    rows: List[Dict[str, Any]] = []
    for item in payload.get("results") or []:
        url = item.get("url") or ""
        if _blocked_domain(url):
            continue
        rows.append(
            {
                "title": item.get("title") or "Tavily 검색 결과",
                "snippet": item.get("content") or item.get("snippet") or "",
                "url": url,
                "provider": "Tavily",
                "provider_score": item.get("score"),
                "published_date": item.get("published_date"),
            }
        )
    return rows


def _kosis_search(question: str, patent_meta: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
    api_key = os.getenv("KOSIS_API_KEY", "").strip()
    if not api_key:
        return []

    primary_terms = " ".join(
        part
        for part in [
            patent_meta.get("tech_field") or "",
            patent_meta.get("business_field") or "",
            question,
        ]
        if part
    )

    candidate_queries: List[str] = []
    for term in (
        "물류" if "물류" in question else "",
        "반도체" if "반도체" in question else "",
        "운송" if any(word in question for word in ("물류", "운송", "배송")) else "",
        "제조업" if any(word in question for word in ("반도체", "제조", "공정")) else "",
        patent_meta.get("business_field"),
        patent_meta.get("tech_field"),
        _compact_query(primary_terms, 80),
    ):
        cleaned = _compact_query(str(term or ""), 40)
        if cleaned and cleaned not in candidate_queries:
            candidate_queries.append(cleaned)

    raw_rows: List[Dict[str, Any]] = []
    for search_name in candidate_queries:
        params = {
            "method": "getList",
            "apiKey": api_key,
            "format": "json",
            "jsonVD": "Y",
            "searchNm": search_name,
            "sort": "RANK",
            "startCount": "1",
            "resultCount": str(max(limit, 5)),
        }
        resp = requests.get(
            "https://kosis.kr/openapi/statisticsSearch.do",
            params=params,
            timeout=int(os.getenv("WEB_SEARCH_TIMEOUT", "20")),
        )
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict):
            found = payload.get("data") or payload.get("result") or payload.get("list") or []
            if not found and any(key in payload for key in ("TBL_NM", "STAT_NM")):
                found = [payload]
        elif isinstance(payload, list):
            found = payload
        else:
            found = []
        if found:
            raw_rows = found
            break

    rows: List[Dict[str, Any]] = []
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        title = item.get("TBL_NM") or item.get("STAT_NM") or item.get("MT_ATITLE") or "KOSIS 통계 검색 결과"
        period = " ~ ".join(part for part in [item.get("STRT_PRD_DE"), item.get("END_PRD_DE")] if part)
        snippet = " / ".join(
            str(part)
            for part in [
                item.get("ORG_NM"),
                item.get("STAT_NM"),
                item.get("MT_ATITLE"),
                item.get("CONTENTS"),
                f"수록기간 {period}" if period else "",
            ]
            if part
        )
        rows.append(
            {
                "title": title,
                "snippet": snippet,
                "url": item.get("LINK_URL") or item.get("TBL_VIEW_URL") or "https://kosis.kr",
                "provider": "KOSIS",
                "web_source_grade": "GOOD",
                "web_source_type": "공공통계",
                "web_source_reason": "KOSIS 국가통계포털 통합검색 API",
            }
        )
    return rows


def _kipris_citation_search(patent_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    api_key = os.getenv("KIPRIS_API_KEY", "").strip()
    if not api_key:
        return []

    application_number = _number_digits(str(patent_meta.get("application_number") or ""))
    if not application_number:
        return []

    service_url = "http://plus.kipris.or.kr/openapi/rest/CitationService/citationInfoV3"
    params = {"applicationNumber": application_number, "accessKey": api_key}
    resp = requests.get(
        service_url,
        params=params,
        timeout=int(os.getenv("WEB_SEARCH_TIMEOUT", "20")),
    )
    resp.raise_for_status()
    text = resp.text
    stripped = _strip_html(text)
    if not stripped:
        try:
            root = ET.fromstring(text.encode("utf-8"))
            stripped = " ".join((node.text or "").strip() for node in root.iter() if (node.text or "").strip())
        except Exception:
            stripped = ""
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if not stripped:
        return []

    safe_query = urlencode({"applicationNumber": application_number})
    return [
        {
            "title": f"KIPRIS 인용/선행기술 조회 - {patent_meta.get('registration_number') or application_number}",
            "snippet": stripped[:900],
            "url": f"https://plus.kipris.or.kr/portal/data/service/DBII_000000000000011/view.do?{safe_query}",
            "provider": "KIPRIS",
            "web_source_grade": "GOOD",
            "web_source_type": "공공/특허",
            "web_source_reason": "KIPRISPlus CitationService REST API",
        }
    ]


def _rows_to_documents(rows: List[Dict[str, Any]], patent_meta: Dict[str, Any], limit: int) -> List[Document]:
    docs: List[Document] = []
    for idx, row in enumerate(rows[:limit], start=1):
        title = row.get("title") or row.get("name") or "웹 검색 결과"
        snippet = row.get("snippet") or row.get("summary") or row.get("content") or row.get("description") or ""
        url = row.get("url") or row.get("link") or ""
        text = "\n".join(part for part in [title, snippet] if part).strip()
        if not text:
            continue
        grade = {
            "grade": row.get("web_source_grade"),
            "type": row.get("web_source_type"),
            "reason": row.get("web_source_reason"),
        }
        if not grade["grade"]:
            grade = _web_source_grade(url, title)

        provider = row.get("provider") or "WEB"
        provider_note = f"검색 공급자: {provider}"
        if row.get("provider_score") is not None:
            provider_note += f" / 공급자 점수: {row.get('provider_score')}"
        if row.get("published_date"):
            provider_note += f" / 게시일: {row.get('published_date')}"
        text = f"{text}\n{provider_note}"

        docs.append(
            Document(
                page_content=text,
                metadata={
                    "chunk_id": f"WEB:{provider}:{idx}:{_hash(url + text)}",
                    "patent_id": patent_meta.get("patent_id"),
                    "source_type": "WEB",
                    "page_no": None,
                    "section_title": "외부 웹 검색",
                    "source_url": url,
                    "title": title,
                    "file_name": url,
                    "text_hash": _hash(text),
                    "web_source_grade": grade["grade"],
                    "web_source_type": grade["type"],
                    "web_source_reason": grade["reason"],
                    "web_provider": provider,
                    "web_provider_score": row.get("provider_score"),
                    "published_date": row.get("published_date"),
                },
            )
        )
    return docs


def search_web_documents(
    patent_meta: Dict[str, Any],
    question: str,
    enabled: bool,
    api_url: str,
    api_key: str,
    limit: int = 5,
) -> Tuple[List[Document], int]:
    t0 = now_ms()
    if not enabled:
        return [], now_ms() - t0

    query = (
        f"{patent_meta.get('title', '')} "
        f"{patent_meta.get('application_number', '')} "
        f"{patent_meta.get('registration_number', '')} "
        f"{patent_meta.get('ipc_code', '')} "
        f"{question}"
    ).strip()

    rows: List[Dict[str, Any]] = []

    if _question_needs_kipris(question):
        try:
            rows.extend(_kipris_citation_search(patent_meta))
        except Exception:
            pass

    if _question_needs_kosis(question):
        try:
            rows.extend(_kosis_search(question, patent_meta, max(2, min(limit, 5))))
        except Exception:
            pass

    if api_url:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            resp = requests.post(
                api_url,
                headers=headers,
                json={"query": query, "limit": limit},
                timeout=int(os.getenv("WEB_SEARCH_TIMEOUT", "20")),
            )
            resp.raise_for_status()

            payload = resp.json()
            rows.extend(payload.get("results") or payload.get("items") or [])
        except Exception:
            pass
    else:
        try:
            rows.extend(_tavily_search(query, limit))
        except Exception:
            pass

    rows = _dedupe_rows(rows, limit)
    if rows:
        return _rows_to_documents(rows, patent_meta, limit), now_ms() - t0

    if os.getenv("ENABLE_WEB_SEARCH_FALLBACK", "true").lower() not in ("1", "true", "yes"):
        return [], now_ms() - t0

    results = _bing_search(query, limit)
    return _rows_to_documents(results, patent_meta, limit), now_ms() - t0
