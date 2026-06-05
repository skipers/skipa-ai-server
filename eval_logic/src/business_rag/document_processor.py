"""
크롤링된 원본 문서를 RAG용 청크로 분할하고 메타데이터를 보강.

개선 사항:
  - 문장 경계 보존 청킹: 단어 수 기준이 아닌 문장 단위로 청크 구성
  - embed_text 필드 추가: 임베딩 시 [제품][제목] 메타데이터 프리픽스 포함 → 검색 정확도 향상
"""
import json
import re
import unicodedata
from pathlib import Path

from .config import RAW_DIR, PROCESSED_DIR, CHUNK_SIZE, CHUNK_OVERLAP


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def _sentence_aware_chunk(
    text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """
    문장 경계를 보존하는 청킹.
    마침표/개행 단위로 문장 분리 후 size(단어 수) 이내로 묶음.
    청크 간 overlap 단어를 앞 청크에서 이월해 문맥 연속성 유지.
    """
    # 문장 경계: 마침표·느낌표·물음표·한국어 마침표 뒤 공백, 또는 연속 개행
    sentences = re.split(r"(?<=[.!?。])\s+|\n{2,}", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list[str] = []
    buf: list[str] = []  # 현재 청크에 쌓인 단어 목록

    for sent in sentences:
        words = sent.split()
        if len(buf) + len(words) > size and buf:
            chunks.append(" ".join(buf))
            # 이전 청크 끝 overlap 단어를 다음 청크 시작에 이월
            buf = buf[-overlap:] if overlap else []
        buf.extend(words)

    if buf:
        chunks.append(" ".join(buf))

    return [c for c in chunks if c.strip()]


def _make_embed_text(keyword: str, title: str, chunk: str) -> str:
    """
    임베딩 전용 텍스트.
    메타데이터 프리픽스를 붙여 임베딩이 제품·문서 맥락을 인식하도록 함.
    """
    prefix = f"[제품: {keyword}] [제목: {title}]"
    return f"{prefix}\n{chunk}"


def process_documents(raw_docs: list[dict]) -> list[dict]:
    """원본 문서 리스트 → 청크 단위 문서 리스트 반환."""
    processed: list[dict] = []
    doc_id = 0

    for doc in raw_docs:
        full_text = _normalize(
            f"{doc.get('title', '')} {doc.get('description', '')} {doc.get('content', '')}"
        )
        if not full_text or len(full_text) < 50:
            continue

        keyword = doc.get("keyword", "")
        title = doc.get("title", "")
        chunks = _sentence_aware_chunk(full_text)

        for idx, chunk in enumerate(chunks):
            processed.append({
                "id": f"doc_{doc_id:04d}_chunk_{idx:03d}",
                "keyword": keyword,
                "url": doc.get("url", ""),
                "title": title,
                "chunk_index": idx,
                "total_chunks": len(chunks),
                "text": chunk,
                "embed_text": _make_embed_text(keyword, title, chunk),
                "published_at": doc.get("published_at", ""),
                "crawled_at": doc.get("crawled_at", ""),
            })
        doc_id += 1

    return processed


def load_and_process(raw_path: Path | None = None) -> list[dict]:
    if raw_path is None:
        raw_path = RAW_DIR / "all_documents.json"

    raw_docs = json.loads(raw_path.read_text(encoding="utf-8"))
    processed = process_documents(raw_docs)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "chunks.json"
    out_path.write_text(json.dumps(processed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"청크 {len(processed)}개 → {out_path}")
    return processed


if __name__ == "__main__":
    load_and_process()
