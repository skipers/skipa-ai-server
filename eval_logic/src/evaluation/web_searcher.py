"""LLM 평가용 웹 근거 검색 어댑터입니다.

LLM 평가가 일반론으로 흐르지 않도록 항목별 웹 근거를 수집합니다. 이 모듈은
검색 쿼리 생성, 도메인 필터링, 중복 제거, 신뢰도 정렬까지만 담당하고 실제
점수 판단은 ``llm_evaluator``가 수행합니다.

특허 평가 근거 웹 검색 모듈

Tavily API를 사용해 뉴스·논문 등 공신력 있는 자료에서 근거를 검색.
TAVILY_API_KEY 환경변수가 없으면 빈 리스트를 반환해 자연스럽게 대체 처리합니다.

[변경사항]
- 항목별 검색 전략을 3가지로 분리:
    WEB_SEARCH  : Tavily 검색 필수 (시장 데이터 등)
    CLAIMS_ONLY : claims_text + JSON 내부 판단, 웹서치 없음
    HYBRID      : 웹서치 + claims 병행
- 4개 차원 템플릿 → 35개 항목별 개별 쿼리 템플릿으로 교체
- search_patent_evidence() 시그니처 변경:
    (patent_title, dim) → (patent_title, item, ipc, ipc_desc)
"""

from __future__ import annotations

import os
import requests
from urllib.parse import urlparse
from core.env import load_runtime_env
from core.paths import ROOT_DIR

load_runtime_env()

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TAVILY_URL = "https://api.tavily.com/search"
SEARCH_TIMEOUT = 15


# ──────────────────────────────────────────
# 도메인 신뢰도 정책 (3단계)  ← 기존과 동일
# ──────────────────────────────────────────
TRUSTED_DOMAINS: set[str] = {
    "kipo.go.kr", "kipris.or.kr",
    "kisti.re.kr", "scienceon.kisti.re.kr",
    "kiip.re.kr", "kisdi.re.kr", "kiet.re.kr",
    "ntis.go.kr", "kotra.or.kr", "nia.or.kr",
    "innopolis.or.kr", "rne.or.kr",
    "etnews.com", "zdnet.co.kr", "bloter.net", "itleader.co.kr",
    "yna.co.kr", "yonhapnews.co.kr",
    "chosun.com", "donga.com", "hankyung.com", "mk.co.kr", "sedaily.com",
    "dt.co.kr", "mediapen.com", "sisajournal-e.com", "thebigdata.co.kr",
    "bizwatch.co.kr", "mstoday.co.kr", "greened.kr", "100ssd.co.kr",
    "cio.com",
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com",
    "techcrunch.com", "wired.com", "theverge.com", "arstechnica.com",
    "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "nature.com",
    "science.org", "ieee.org", "acm.org", "springer.com",
    "sciencedirect.com", "researchgate.net",
    "fortunebusinessinsights.com", "gminsights.com",
    "sphericalinsights.com", "straitsresearch.com",
    "marketsandmarkets.com", "grandviewresearch.com",
    "patents.google.com",
}

BLOCKED_DOMAINS: set[str] = {
    "blog.naver.com", "tistory.com", "brunch.co.kr",
    "medium.com", "tilnote.io", "yeoreum.me",
    "jaenung.net", "odiro.ai", "service.odiro.ai", "dubsmart.ai",
    "v.daum.net", "n.news.naver.com",
}

BLOCKED_PATH_PATTERNS: tuple[str, ...] = (
    "/blog/", "/board/", "/community/", "/qna/", "/post/",
    "/user/", "/member/",
)


# ──────────────────────────────────────────
# 검색 전략 분류
# ──────────────────────────────────────────
# 웹 검색    : Tavily 검색으로 외부 데이터 필요
# 청구항 전용 : 청구항·JSON 내부 텍스트만으로 판단 → 웹서치 불필요
# 혼합        : 웹서치 + 청구항 병행

SEARCH_STRATEGY: dict[str, str] = {
    # ── 기술성 (5개) ──
    "차별성 및 파급성":        "hybrid",
    "혁신성 및 개척성":        "hybrid",
    "대체기술 및 경쟁성":      "web_search",
    "기술 모방 및 회피설계 난이도": "claims_only",
    "전망성":                  "web_search",
    "모방 및 회피설계 난이도": "claims_only",

    # ── 권리성 (10개) ──
    "IP 원천성":                 "web_search",
    "무효 가능성":               "claims_only",
    "회피설계 용이성":           "claims_only",
    "권리범위 적절성":           "claims_only",
    "권리의 구성요소":           "claims_only",
    "권리의 추상성":             "claims_only",
    "권리의 충실성":             "claims_only",
    "권리행사 제한 가능성":      "claims_only",
    "IP 포트폴리오 구축 적절성": "claims_only",
    "침해 발견 및 입증 용이성":  "claims_only",

    # ── 시장성 (6개) ──
    "IP 시장적합성":      "web_search",
    "시장집중도":         "web_search",
    "특허출원 활성도":    "web_search",
    "고객의 지불의지":    "hybrid",
    "고객에 미치는 영향": "hybrid",
    "경쟁사 반응":        "web_search",

    # ── 사업성 (6개) ──
    "기술 사업화 환경":      "hybrid",
    "예상 시장 점유율":      "web_search",
    "생산 및 서비스 용이성": "hybrid",
    "매출 성장성":           "web_search",
    "경제적 수명":           "hybrid",
    "타제품에 미치는 영향":  "claims_only",
}


# ──────────────────────────────────────────
# 항목별 검색 기간 (Tavily 일수 파라미터)
# 시장·경쟁 동향 항목: 730일(2년) — 오래된 점유율·경쟁 구도는 평가 왜곡
# 기술 추세·구조적 항목: 1825일(5년) — 연구개발 흐름·수명주기는 장기 추세로 판단
# ──────────────────────────────────────────
ITEM_SEARCH_DAYS: dict[str, int] = {
    # 시장·경쟁 동향 (2년)
    "차별성 및 파급성":    730,
    "혁신성 및 개척성":    730,
    "대체기술 및 경쟁성":  730,
    "IP 시장적합성":       730,
    "시장집중도":          730,
    "고객의 지불의지":     730,
    "고객에 미치는 영향":  730,
    "경쟁사 반응":         730,
    "기술 사업화 환경":    730,
    "예상 시장 점유율":    730,
    "생산 및 서비스 용이성": 730,
    "매출 성장성":         730,
    # 기술 추세·구조적 항목 (5년)
    "전망성":          1825,
    "IP 원천성":       1825,
    "특허출원 활성도": 1825,
    "경제적 수명":     1825,
}


def get_search_strategy(item: str) -> str:
    """항목명으로 검색 전략을 반환합니다. 미등록 항목은 혼합 전략으로 대체합니다."""
    return SEARCH_STRATEGY.get(item, "hybrid")


def get_search_days(item: str) -> int:
    """항목명으로 검색 기간(일수)을 반환합니다. 미등록 항목은 730일입니다."""
    return ITEM_SEARCH_DAYS.get(item, 730)


# ──────────────────────────────────────────
# 항목별 Tavily 쿼리 템플릿
# {title}   : 특허 제목
# {ipc}     : IPC 코드 (예: G06Q30/06)
# {ipc_desc}: IPC 설명 (예: 전자상거래)
# ──────────────────────────────────────────
_ITEM_QUERY_TEMPLATES: dict[str, list[str]] = {

    # ── 기술성 ──
    "차별성 및 파급성": [
        "{ipc_desc} 기술 차별화 경쟁우위 비교",
        "{ipc_desc} 기술 파급효과 활용 분야",
    ],
    "혁신성 및 개척성": [
        "{ipc_desc} 혁신기술 동향 개량",
        "{ipc_desc} 기술 혁신 문제 해결 사례",
    ],
    "대체기술 및 경쟁성": [
        "{ipc_desc} 대체기술 솔루션 경쟁",
        "{ipc_desc} 경쟁기술 주요 기업 현황",
    ],
    "전망성": [
        "{ipc_desc} R&D 투자 연구개발 동향",
    ],

    # ── 권리성 ──
    "IP 원천성": [
        "{ipc} 원천특허 선행기술 현황",
    ],

    # ── 시장성 ──
    "IP 시장적합성": [
        "{ipc_desc} 특허 라이선스 분쟁 사례",
    ],
    "시장집중도": [
        "{ipc_desc} 시장 점유율 주요 기업",
    ],
    "특허출원 활성도": [
        "{ipc} 특허 출원 동향 최근 5년",
    ],
    "고객의 지불의지": [
        "{ipc_desc} 고객 프리미엄 지불 의향",
    ],
    "고객에 미치는 영향": [
        "{ipc_desc} 기술 도입 고객 효익 만족",
    ],
    "경쟁사 반응": [
        "{ipc_desc} 경쟁사 시장점유율 변화 추이",
        "{ipc_desc} 경쟁사 가격 전략 특허 대응",
    ],

    # ── 사업성 ──
    "기술 사업화 환경": [
        "{ipc_desc} 사업화 규제 법제도 환경",
    ],
    "예상 시장 점유율": [
        "{ipc_desc} 시장점유율 선두기업 현황",
    ],
    "생산 및 서비스 용이성": [
        "{ipc_desc} 생산 설비 원부자재 조달",
    ],
    "매출 성장성": [
        "{ipc_desc} 매출 성장률 전망",
    ],
    "경제적 수명": [
        "{ipc_desc} 제품 경제적 수명 주기",
    ],
}


def _build_queries(item: str, title: str, ipc: str, ipc_desc: str, assignee: str = "") -> list[str]:
    """항목명을 기반으로 Tavily에 전달할 쿼리 목록을 생성합니다."""
    templates = _ITEM_QUERY_TEMPLATES.get(item)
    if not templates:
        templates = [
            f"{title} {item} 동향",
            f"{ipc_desc} {item}",
        ]
    return [
        t.format(title=title, ipc=ipc, ipc_desc=ipc_desc, assignee=assignee)
        for t in templates
    ]


# ──────────────────────────────────────────
# 내부 유틸
# ──────────────────────────────────────────
def _classify_domain(url: str) -> tuple[int, str]:
    if not url:
        return (3, "url 없음")
    try:
        parsed = urlparse(url)
    except Exception:
        return (3, "url 파싱 실패")

    netloc = parsed.netloc.lower().lstrip("www.")
    path   = parsed.path.lower()

    for blocked in BLOCKED_DOMAINS:
        if netloc == blocked or netloc.endswith("." + blocked):
            return (3, f"차단 도메인: {blocked}")

    for pattern in BLOCKED_PATH_PATTERNS:
        if pattern in path:
            return (3, f"차단 경로: {pattern}")

    for trusted in TRUSTED_DOMAINS:
        if netloc == trusted or netloc.endswith("." + trusted):
            return (1, f"신뢰 도메인: {trusted}")

    return (2, f"중립: {netloc}")


def _call_tavily(query: str, max_results: int, days: int = 730) -> list[dict]:
    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "days": days,
            "include_answer": False,
            "include_raw_content": False,
        }
        resp = requests.post(TAVILY_URL, json=payload, timeout=SEARCH_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("results") is None:
            print(f"  [웹검색 경고] '{query[:40]}' → 결과 없음")
        return data.get("results", [])
    except Exception as e:
        print(f"  [웹검색 오류] Tavily 호출 실패: {e}")
        return []


def _deduplicate_and_rank(raw: list[dict], max_results: int) -> list[dict]:
    """URL 중복 제거 → 도메인 신뢰도·Tavily 점수 순 정렬 → 상위 N개 반환.

    블로그/커뮤니티성 결과는 평가 근거로 사용하기 어렵기 때문에 제외합니다.
    남은 결과는 신뢰 도메인을 우선하고, 같은 등급 안에서는 Tavily 관련도
    점수가 높은 순서로 정렬합니다.
    """
    seen: set[str] = set()
    classified: list[tuple[int, float, dict]] = []
    blocked_count = 0

    for r in raw:
        url = r.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)

        tier, _ = _classify_domain(url)
        if tier == 3:
            blocked_count += 1
            continue

        tavily_score = float(r.get("score", 0))
        classified.append((
            tier,
            -tavily_score,
            {
                "title":          r.get("title", ""),
                "url":            url,
                "snippet":        (r.get("content") or "")[:400],
                "published_date": r.get("published_date") or "",
                "tier":           tier,
            },
        ))

    classified.sort(key=lambda x: (x[0], x[1]))

    if blocked_count:
        print(f"  [웹검색] 차단 도메인 {blocked_count}건 제외")

    result = [item for _, _, item in classified[:max_results]]

    if result:
        t1 = sum(1 for u in result if u.get("tier") == 1)
        t2 = len(result) - t1
        print(f"  [웹검색] 신뢰 {t1}건 + 중립 {t2}건 = {len(result)}건")

    for u in result:
        u.pop("tier", None)

    return result


# ──────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────
def search_patent_evidence(
    patent_title: str,
    item: str,
    ipc: str = "",
    ipc_desc: str = "",
    assignee: str = "",
    max_results: int = 5,
) -> list[dict]:
    """
    항목별 검색 전략에 따라 Tavily 검색 수행.

    인자:
        patent_title : 특허 제목 (JSON meta.title)
        item         : 평가 항목명 (예: "시장 성장성", "회피설계 용이성")
        ipc          : IPC 코드 (예: "G06Q30/06")
        ipc_desc     : IPC 설명 (예: "전자상거래")
        assignee     : 출원인명 (예: "에스케이 주식회사") — 특별한 인정 항목에서 활용
        max_results  : 반환할 최대 결과 수

    반환:
        웹 검색 / 혼합  → [{title, url, snippet, published_date}] 최대 max_results개
        청구항 전용     → []  (웹검색 불필요 항목임을 호출부에서 인지)
    """
    # 항목별로 외부 검색 필요성이 다릅니다. 예를 들어 권리범위/회피설계는
    # 청구항 자체가 핵심 근거이고, 시장집중도/경쟁사 반응은 외부 자료가
    # 필요합니다. 이 분기를 통해 비용과 노이즈를 줄입니다.
    strategy = get_search_strategy(item)

    # 청구항 전용: 웹서치 하지 않음
    if strategy == "claims_only":
        print(f"  [웹검색 스킵] '{item}' → claims_only 항목 (청구항 텍스트로 판단)")
        return []

    # TAVILY_API_KEY가 없으면 빈 결과로 자연스럽게 대체 처리
    if not TAVILY_API_KEY:
        return []

    days    = get_search_days(item)
    queries = _build_queries(item, patent_title, ipc, ipc_desc, assignee)
    print(f"  [웹검색] '{item}' → 최근 {days}일 이내")
    raw: list[dict] = []
    for q in queries:
        raw.extend(_call_tavily(q, max_results=2, days=days))

    results = _deduplicate_and_rank(raw, max_results)

    # Save to shared wiki (PROJECT_ROOT/data/wiki/{topic}/)
    if results:
        try:
            _save_to_wiki(patent_title, item, queries, results)
        except Exception as _wiki_err:
            print(f"  [Wiki 저장 스킵] {_wiki_err}")

    return results


def _save_to_wiki(patent_title: str, item: str, queries: list[str], results: list[dict]) -> None:
    """eval_logic 웹검색 결과를 chatbot의 공유 wiki에 저장합니다."""
    import sys
    from pathlib import Path
    from datetime import datetime

    # chatbot 모듈 경로 추가
    project_root = ROOT_DIR.parent if ROOT_DIR.name == "eval_logic" else ROOT_DIR.parent
    chatbot_app = project_root / "chatbot" / "app"
    if not chatbot_app.exists():
        return

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from chatbot.app.wiki.topics import classify_title_to_topic, topic_draft_dir
    from chatbot.app.vectorstore import auto_approve_web_draft

    topic = classify_title_to_topic(patent_title)
    draft_dir = topic_draft_dir(topic)
    draft_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    draft_path = draft_dir / f"eval_logic_{stamp}.md"
    lines = [
        "# eval_logic Web Search Draft",
        f"- Patent: {patent_title}",
        f"- Item: {item}",
        f"- Topic: {topic}",
        f"- Queries: {', '.join(queries)}",
        "",
    ]
    for idx, r in enumerate(results, 1):
        lines.extend([f"### {idx}. {r.get('title','')}", f"- URL: {r.get('url','')}", "", str(r.get("content") or r.get("snippet", "")), ""])
    draft_path.write_text("\n".join(lines), encoding="utf-8")

    # web results를 chatbot 형식으로 변환
    chat_results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content") or r.get("snippet", ""),
            "relevance": {"score": float(r.get("score", 0.5)), "matched_terms": []},
        }
        for r in results
    ]
    auto_approve_web_draft(
        f"_eval_{patent_title[:20]}",
        draft_path=str(draft_path),
        query=f"{patent_title} {item}",
        results=chat_results,
        topic_override=topic,
    )


def needs_web_search(item: str) -> bool:
    """호출부에서 웹서치 필요 여부를 사전에 확인할 때 사용."""
    return get_search_strategy(item) != "claims_only"
