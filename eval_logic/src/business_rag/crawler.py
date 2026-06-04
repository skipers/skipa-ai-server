"""
SK AX 홈페이지 크롤러.
1차: 사이트맵(195개 URL) 전체 수집 + 키워드 매핑
2차: WordPress REST API 검색으로 미수집 제품 보완
"""
import json
import re
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

from .config import SKAX_BASE_URL, CRAWL_DELAY, RAW_DIR, PRODUCTS

BASE_URL = SKAX_BASE_URL.rstrip("/")
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
WP_SEARCH_API = f"{BASE_URL}/wp-json/wp/v2/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}

# 영문 제품명의 URL slug 힌트 (빠른 우선 매칭용)
KEYWORD_URL_HINTS: dict[str, list[str]] = {
    "DiFlow": ["diflow"],
    "nexcore": ["nexcore"],
    "TOMS": ["tms"],
    "ChainZ": ["chainz", "chain"],
    "Aibril": ["aibril"],
    "AKS": ["aks"],
    "WAU": ["wau"],
    "mTworks": ["atworks", "mtworks"],
    "Aiden": ["aiden"],
    "EAP": ["eap"],
    "AccuInsight+": ["accuinsight", "acculnsight"],
    "MarketCaster": ["marketcaster", "market-caster"],
    "iclue-tdmd": ["iclue", "tdmd"],
    "RE100": ["re100", "renewable"],
    "로보어드바이저": ["robo", "advisor", "로보어드"],
    "watz eye": ["watz", "eye"],
    "containment": ["containment"],
}


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_published_date(soup: BeautifulSoup) -> str:
    """HTML에서 페이지 발행일/수정일 추출 (YYYY-MM-DD). 없으면 빈 문자열."""
    # 1. Open Graph / article 메타 태그
    for prop in ("article:published_time", "article:modified_time", "og:updated_time"):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            return str(tag["content"])[:10]
    # 2. <time datetime="...">
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        return str(time_tag["datetime"])[:10]
    # 3. Schema.org itemprop
    for prop in ("datePublished", "dateModified"):
        tag = soup.find(attrs={"itemprop": prop})
        if tag:
            val = tag.get("datetime") or tag.get("content") or tag.get_text()
            if val:
                return str(val).strip()[:10]
    return ""


def _parse_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    title = _clean(soup.title.get_text()) if soup.title else ""
    meta_desc = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta:
        meta_desc = meta.get("content", "")

    published_at = _extract_published_date(soup)
    body_text = _clean(soup.get_text(separator=" "))
    return {
        "url": url,
        "title": title,
        "description": meta_desc,
        "content": body_text[:6000],
        "published_at": published_at,
    }


def _match_keywords(page: dict, products: list[str]) -> list[str]:
    """해당 페이지에 등장하는 제품 키워드 목록 반환."""
    haystack = (
        page["url"].lower() + " "
        + page["title"].lower() + " "
        + page["content"].lower()
    )
    matched = []
    for kw in products:
        kw_lower = kw.lower()
        # URL slug 힌트 우선 확인
        hints = KEYWORD_URL_HINTS.get(kw, [])
        url_hit = any(h in page["url"].lower() for h in hints)
        text_hit = kw_lower in haystack
        if url_hit or text_hit:
            matched.append(kw)
    return matched


# ── 사이트맵 파싱 ─────────────────────────────────────────────────────────────

def _fetch_sitemap_urls() -> list[str]:
    resp = requests.get(SITEMAP_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml-xml")
    urls = [loc.text.strip() for loc in soup.find_all("loc")]
    # 한국어 페이지 우선 (en/ 경로 마지막으로)
    ko_urls = [u for u in urls if "/en/" not in u]
    en_urls = [u for u in urls if "/en/" in u]
    return ko_urls + en_urls


# ── WordPress REST API 2차 보완 크롤링 ───────────────────────────────────────

def _wp_search_keyword(
    session: requests.Session,
    keyword: str,
    per_page: int = 10,
) -> list[dict]:
    """WP REST API로 키워드 검색 → 페이지 본문 수집."""
    search_term = keyword.replace("+", "").strip()
    params = {"search": search_term, "per_page": per_page, "type": "post"}
    try:
        resp = session.get(WP_SEARCH_API, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json()
    except Exception as e:
        print(f"  [WP API] {keyword} 검색 실패: {e}")
        return []

    docs: list[dict] = []
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    for item in items:
        url = item.get("url", "")
        if not url:
            continue
        try:
            page_resp = session.get(url, timeout=15)
            page_resp.raise_for_status()
        except Exception:
            continue

        page = _parse_page(page_resp.text, url)
        if len(page["content"]) < 80:
            continue

        docs.append({**page, "keyword": keyword, "crawled_at": ts})
        time.sleep(CRAWL_DELAY)

    return docs


# ── 메인 크롤링 ───────────────────────────────────────────────────────────────

def crawl_all_products(
    products: list[str] | None = None,
    *,
    use_playwright: bool = False,   # 사이트맵 방식에서는 불필요
) -> list[dict]:
    if products is None:
        products = PRODUCTS

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    print("사이트맵에서 URL 목록 수집 중...")
    all_urls = _fetch_sitemap_urls()
    print(f"  → {len(all_urls)}개 URL 발견\n")

    # 키워드별 문서 버킷
    keyword_docs: dict[str, list[dict]] = {kw: [] for kw in products}
    all_docs: list[dict] = []

    for i, url in enumerate(all_urls, 1):
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [{i}/{len(all_urls)}] 실패: {url} — {e}")
            time.sleep(CRAWL_DELAY)
            continue

        page = _parse_page(resp.text, url)
        if len(page["content"]) < 80:
            continue

        matched_kws = _match_keywords(page, products)
        if matched_kws:
            ts = __import__("time").strftime("%Y-%m-%dT%H:%M:%S")
            for kw in matched_kws:
                doc = {**page, "keyword": kw, "crawled_at": ts}
                keyword_docs[kw].append(doc)
                all_docs.append(doc)
            print(f"  [{i}/{len(all_urls)}] ✓ {url}")
            print(f"       → 키워드: {matched_kws}")
        else:
            if i % 20 == 0:
                print(f"  [{i}/{len(all_urls)}] ... (키워드 미매칭)")

        time.sleep(CRAWL_DELAY)

    # 2차 패스: 사이트맵에서 미수집된 제품을 WP REST API로 보완
    missing = [kw for kw, docs in keyword_docs.items() if not docs]
    if missing:
        print(f"\n=== 2차 패스: WP API 보완 ({len(missing)}개 키워드) ===")
        for kw in missing:
            print(f"\n[WP API] {kw} ...")
            wp_docs = _wp_search_keyword(session, kw)
            keyword_docs[kw].extend(wp_docs)
            all_docs.extend(wp_docs)
            print(f"  → {len(wp_docs)}개 문서 수집")

    # 키워드별 raw JSON 저장
    for kw, docs in keyword_docs.items():
        fname = re.sub(r'[^\w가-힣-]', '_', kw)
        path = RAW_DIR / f"{fname}.json"
        path.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
        status = f"{len(docs)}개 문서" if docs else "미수집"
        print(f"  [{kw}] {status} → {path.name}")

    # 전체 raw 저장
    all_path = RAW_DIR / "all_documents.json"
    all_path.write_text(json.dumps(all_docs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n총 {len(all_docs)}개 문서 (중복 포함) → {all_path}")

    # 수집 현황 요약
    print("\n=== 수집 현황 ===")
    for kw in products:
        cnt = len(keyword_docs.get(kw, []))
        mark = "✓" if cnt else "✗"
        print(f"  {mark} {kw}: {cnt}개")

    return all_docs


if __name__ == "__main__":
    crawl_all_products(PRODUCTS)
