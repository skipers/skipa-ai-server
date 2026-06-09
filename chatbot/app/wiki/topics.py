"""Patent-to-topic classification for topic-based wiki vectorstore partitioning.

Wiki data is stored under DATA_ROOT/wiki/{topic_slug}/.

Classification order
--------------------
1. Predefined keyword map (_TOPIC_KEYWORDS) — exact substring match on title.
2. Existing dynamic topic folders in WIKI_ROOT — check folder name keywords
   against the title so previously auto-created topics can absorb new patents.
3. Derive a new topic slug from the title and create the folder on the fly.
   A folder is created only when nothing in steps 1-2 matched.

Predefined base topics (always available even before first web search):
  소프트웨어_IT  — Software, AI, networking, cloud, monitoring …
  반도체_전자    — Semiconductors, circuits, displays, sensors …
  화학_소재      — Chemicals, gases, materials, processes …
  바이오_의료    — Biotech, pharma, medical devices …
  기계_제조      — Mechanical, manufacturing, equipment …
  에너지_환경    — Energy, batteries, solar, environment …
  _general       — Last-resort fallback (only if title is empty/unclassifiable)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import PATENTS_ROOT, SHARED_PATENT_ROOT, WIKI_ROOT


# ---------------------------------------------------------------------------
# Predefined topic definitions
# ---------------------------------------------------------------------------

TOPIC_SLUGS: list[str] = [
    "소프트웨어_IT",
    "반도체_전자",
    "화학_소재",
    "바이오_의료",
    "기계_제조",
    "에너지_환경",
    "_general",
]

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "소프트웨어_IT": [
        "소프트웨어", "sw", "플랫폼", "네트워크", "서버", "클라우드", "인공지능", "ai",
        "딥러닝", "머신러닝", "데이터", "모니터링", "미들웨어", "통신", "인터페이스",
        "알고리즘", "보안", "앱", "어플리케이션", "데이터베이스", "api", "토폴로지",
        "병목", "스케줄", "프로세서", "컴퓨팅", "자연어처리", "nlp",
    ],
    "반도체_전자": [
        "반도체", "전자", "회로", "칩", "메모리", "dram", "nand", "플래시",
        "디스플레이", "led", "oled", "센서", "트랜지스터", "패키지", "집적",
        "웨이퍼", "마스크", "식각", "리소그래피", "cmp",
    ],
    "화학_소재": [
        "화학", "소재", "재료", "가스", "nf3", "산화", "환원", "촉매",
        "세정", "공정", "증착", "폴리머", "수지", "코팅", "흡착", "분리",
        "정제", "합성", "용매", "나노",
    ],
    "바이오_의료": [
        "바이오", "의료", "의약", "약물", "진단", "치료", "유전자", "세포",
        "단백질", "항체", "의기기", "헬스케어", "임상", "생물", "미생물",
        "백신", "바이러스", "효소",
    ],
    "기계_제조": [
        "기계", "제조", "설비", "장치", "부품", "모터", "베어링", "펌프",
        "밸브", "금형", "로봇", "자동화", "절삭", "가공", "조립", "프레스",
        "용접", "주조",
    ],
    "에너지_환경": [
        "에너지", "환경", "배터리", "태양광", "연료전지", "전력", "탄소",
        "충전", "방전", "전극", "전해질", "수소", "발전", "탈탄소",
    ],
}

# Korean words too generic to derive a useful topic slug from
_SKIP_WORDS: frozenset[str] = frozenset({
    "방법", "시스템", "장치", "및", "의", "을", "를", "이", "가", "에", "은", "는",
    "위한", "기반", "제어", "관리", "처리", "생성", "구조", "구현", "설비",
    "내", "이용", "사용", "수행", "동작", "적용", "이를", "관한", "하는",
    "위해", "통한", "포함", "포함하는",
})

_PATENT_TOPICS_FILE: Path = WIKI_ROOT / "_patent_topics.json"


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _load_topics_cache() -> dict[str, str]:
    if _PATENT_TOPICS_FILE.exists():
        try:
            data = json.loads(_PATENT_TOPICS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def _save_topics_cache(cache: dict[str, str]) -> None:
    _PATENT_TOPICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PATENT_TOPICS_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Topic slug derivation (used when no predefined/dynamic match found)
# ---------------------------------------------------------------------------

def _derive_slug_from_title(title: str) -> str:
    """Extract a filesystem-safe topic slug from a patent title.

    Picks the first two meaningful Korean/ASCII tokens from the title,
    joins them with '_', and trims to 30 chars.
    Returns '_general' when the title yields no usable tokens.
    """
    tokens = re.findall(r"[가-힣A-Za-z0-9]+", title)
    key = [t for t in tokens if t.lower() not in _SKIP_WORDS and len(t) >= 2]
    if not key:
        return "_general"
    slug = "_".join(key[:2])
    # Keep only word chars + Korean + underscore, strip leading/trailing _
    slug = re.sub(r"[^\w가-힣]", "", slug).strip("_")
    return slug[:30] or "_general"


def _existing_dynamic_slugs() -> list[str]:
    """Return topic slugs that exist as WIKI_ROOT subdirs but are not predefined."""
    if not WIKI_ROOT.exists():
        return []
    predefined = set(TOPIC_SLUGS)
    return [
        d.name
        for d in sorted(WIKI_ROOT.iterdir())
        if d.is_dir() and d.name not in predefined and not d.name.startswith("_")
    ]


def _matches_dynamic_slug(slug: str, title: str) -> bool:
    """True when any part of *slug* appears in the lowercased *title*."""
    lower = title.lower()
    for part in re.split(r"[_\-]", slug):
        if part and len(part) >= 2 and part.lower() in lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Classification — public API
# ---------------------------------------------------------------------------

def classify_title_to_topic(title: str) -> str:
    """Return the best-matching existing-or-new topic slug for *title*.

    Resolution order:
    1. Predefined keyword map.
    2. Existing dynamic topic folders already in WIKI_ROOT.
    3. Derive a new slug from the title (folder created by caller / on first use).
    """
    if not title:
        return "_general"

    lower = title.lower()

    # 1. Predefined keywords
    for topic, keywords in _TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return topic

    # 2. Existing dynamically-created folders
    for slug in _existing_dynamic_slugs():
        if _matches_dynamic_slug(slug, title):
            return slug

    # 3. Derive a new slug — folder will be created when data is first written
    return _derive_slug_from_title(title)


def get_patent_topic(patent_id: str) -> str:
    """Return the topic slug for *patent_id*, computing and caching if needed.

    Always re-evaluates if the cached value is '_general' so that a better
    topic can be assigned once the title is available.
    """
    if not patent_id or patent_id in {"_global", ""}:
        return "_general"

    cache = _load_topics_cache()
    cached = cache.get(patent_id)

    # Skip re-evaluation only when we already have a concrete non-general topic
    if cached and cached != "_general":
        return cached

    topic = _topic_from_patent_paths(patent_id)

    cache[patent_id] = topic
    _save_topics_cache(cache)
    return topic


def reclassify_all_patents() -> dict[str, str]:
    """Force re-classification of every patent and update the cache.

    Useful after adding new topic keyword rules or after the WIKI_ROOT gains
    new dynamic folders that may absorb previously '_general' patents.
    """
    cache: dict[str, str] = {}
    patent_ids: set[str] = set()
    if PATENTS_ROOT.exists():
        for patent_dir in sorted(PATENTS_ROOT.iterdir()):
            if patent_dir.is_dir() and not patent_dir.name.startswith("_"):
                patent_ids.add(patent_dir.name)
    if SHARED_PATENT_ROOT.exists():
        for patent_dir in sorted(SHARED_PATENT_ROOT.iterdir()):
            if not patent_dir.is_dir() or patent_dir.name.startswith("_") or patent_dir.name.startswith("."):
                continue
            if (patent_dir / "parsed.json").exists() or (patent_dir / "report.json").exists():
                patent_ids.add(patent_dir.name)
    for patent_id in sorted(patent_ids):
        cache[patent_id] = _topic_from_patent_paths(patent_id)
    _save_topics_cache(cache)
    return cache


def _title_from_json(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(data, dict):
        return ""
    direct = data.get("title")
    if direct:
        return str(direct)
    patent = data.get("normalized_patent") if isinstance(data.get("normalized_patent"), dict) else {}
    meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
    return str(meta.get("title") or patent.get("title") or "")


def _topic_from_patent_paths(patent_id: str) -> str:
    for path in [
        PATENTS_ROOT / patent_id / "manifest.json",
        PATENTS_ROOT / patent_id / "original" / "input" / "latest.json",
        SHARED_PATENT_ROOT / patent_id / "parsed.json",
    ]:
        title = _title_from_json(path)
        if title:
            return classify_title_to_topic(title)
    return "_general"


# ---------------------------------------------------------------------------
# Topic directory helpers
# ---------------------------------------------------------------------------

def topic_wiki_root(topic_slug: str) -> Path:
    return WIKI_ROOT / topic_slug


def topic_draft_dir(topic_slug: str) -> Path:
    return WIKI_ROOT / topic_slug / "web_search_data"


def topic_approved_md(topic_slug: str) -> Path:
    return WIKI_ROOT / topic_slug / "approved_context.md"


def topic_vectorstore_root(topic_slug: str) -> Path:
    return WIKI_ROOT / topic_slug / "qdrant"


def topic_draft_index_path(topic_slug: str) -> Path:
    return WIKI_ROOT / topic_slug / "draft_index.json"


def all_active_topic_slugs() -> list[str]:
    """Return every topic slug that has a web_search_data dir or approved_context.md."""
    if not WIKI_ROOT.exists():
        return []
    slugs = []
    for entry in sorted(WIKI_ROOT.iterdir()):
        if not entry.is_dir():
            continue
        if (entry / "web_search_data").exists() or (entry / "approved_context.md").exists():
            slugs.append(entry.name)
    return slugs
