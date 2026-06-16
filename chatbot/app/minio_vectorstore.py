"""MinIO-based vectorstore builder for patents and pre-evaluations.

MinIO 경로값을 받아서 해당 데이터를 다운로드·전처리·임베딩·Qdrant 업서트까지
한 번에 처리합니다. 기존 컬렉션이 있으면 먼저 삭제 후 재생성합니다.

MinIO 디렉터리 구조
-------------------
특허:
    skipa/patents/{id}/
        parsed.json          ← normalized_patent, brief_summary, keywords
        original.pdf         ← 원본 PDF (시각 자료 텍스트 추출용)
        reports/
            1/report.json    ← {"report": {...}}  (숫자 클수록 최신)
            2/report.json
            ...

사전 평가:
    skipa/pre-evaluations/{id}/
        report.json          ← {schema_version, evaluation_id, patent_title, ...}
                                (input.json은 인덱싱하지 않음)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MinIO client
# ---------------------------------------------------------------------------

def _boto3_client():
    """Return a boto3 S3 client pointed at MinIO."""
    try:
        import boto3
        from botocore.client import Config
    except ImportError as exc:
        raise RuntimeError("boto3 is required: pip install boto3") from exc
    from .config import MINIO_ACCESS_KEY, MINIO_BUCKET, MINIO_ENDPOINT, MINIO_SECRET_KEY  # noqa: F401
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


def _bucket() -> str:
    from .config import MINIO_BUCKET
    return MINIO_BUCKET


def _get_json(client, key: str) -> dict[str, Any]:
    """Download and parse a JSON object from MinIO. Returns {} on error."""
    try:
        obj = client.get_object(Bucket=_bucket(), Key=key)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("MinIO get_json failed for %s: %s", key, exc)
        return {}


def _list_subdirs(client, prefix: str) -> list[str]:
    """Return immediate child prefixes under prefix (delimiter='/')."""
    prefix = prefix.rstrip("/") + "/"
    result = client.list_objects_v2(Bucket=_bucket(), Prefix=prefix, Delimiter="/")
    return [p["Prefix"] for p in result.get("CommonPrefixes", [])]


def _normalize_minio_prefix(path: str, default_prefix: str) -> str:
    """
    Normalize caller-supplied path to a MinIO prefix ending with '/'.

    Accepts:
      '1'               → '{default_prefix}/1/'
      'patents/1'       → 'patents/1/'
      'patents/1/'      → 'patents/1/'
    """
    path = path.strip().strip("/")
    if not path:
        raise ValueError("minio_path must not be empty")
    # If path doesn't contain '/' it's a bare ID — prepend default_prefix
    if "/" not in path:
        path = f"{default_prefix}/{path}"
    return path.rstrip("/") + "/"


# ---------------------------------------------------------------------------
# Patent helpers
# ---------------------------------------------------------------------------

def _latest_report_key(client, base_prefix: str) -> str | None:
    """Return the key of the latest report.json (highest numeric subdir)."""
    reports_prefix = base_prefix.rstrip("/") + "/reports/"
    subdirs = _list_subdirs(client, reports_prefix)
    if not subdirs:
        return None
    # Extract numeric suffix from each subdir prefix and pick the max
    def _num(prefix: str) -> int:
        name = prefix.rstrip("/").split("/")[-1]
        try:
            return int(name)
        except ValueError:
            return -1
    best = max(subdirs, key=_num)
    key = best.rstrip("/") + "/report.json"
    # Verify it actually exists
    try:
        client.head_object(Bucket=_bucket(), Key=key)
        return key
    except Exception:
        return None


def _patent_id_from_parsed(parsed: dict[str, Any]) -> str | None:
    """Extract registration_number from parsed.json."""
    patent = parsed.get("normalized_patent") if isinstance(parsed.get("normalized_patent"), dict) else {}
    meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
    return meta.get("registration_number") or None


def _patent_id_from_prefix(base_prefix: str) -> str:
    """Use the MinIO folder name as the patent id (patents/1/ -> 1)."""
    return base_prefix.rstrip("/").split("/")[-1]


# ---------------------------------------------------------------------------
# Document builders
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")


def _doc_id(patent_id: str, suffix: str) -> str:
    return hashlib.sha1(f"{patent_id}:{suffix}".encode()).hexdigest()[:16]


def _make_doc(patent_id: str, text: str, section: str, base_meta: dict[str, Any]) -> dict[str, Any] | None:
    t = str(text or "").strip()
    if len(t) < 30:
        return None
    return {
        "doc_id": _doc_id(patent_id, section),
        "page_content": t[:20000],
        "metadata": {**base_meta, "section_title": section},
    }


def _minio_report_to_docs(patent_id: str, report_inner: dict[str, Any], *, source_key: str | None = None) -> list[dict[str, Any]]:
    """Convert MinIO report schema → indexable chunks.

    MinIO report schema (inside {"report": {...}}):
      patent.title, patent.registration_number
      summary.overall_opinion, summary.dimension_cards[].{label, summary}
      evaluation.dimensions[].{key, label, summary, items[].{name, judgment_summary, judgment_basis}}
    """
    docs: list[dict[str, Any]] = []
    patent_meta = report_inner.get("patent") if isinstance(report_inner.get("patent"), dict) else {}
    title = patent_meta.get("title") or patent_id
    summary_block = report_inner.get("summary") if isinstance(report_inner.get("summary"), dict) else {}
    eval_block = report_inner.get("evaluation") if isinstance(report_inner.get("evaluation"), dict) else {}

    base_meta = {
        "patent_id": patent_id,
        "source_type": "SHARED_REPORT",
        "title": title,
        "file_name": "report.json",
        "relative_source_path": f"minio/{source_key}" if source_key else f"minio/patents/{patent_id}/report.json",
    }
    header = f"[특허번호: {patent_id}] [{title}]\n"

    # ── 종합 의견 ────────────────────────────────────────────────────────────
    opinion = summary_block.get("overall_opinion") or ""
    grade = summary_block.get("overall_grade") or ""
    score = summary_block.get("overall_score_out_of_100") or ""
    if opinion:
        text = f"{header}종합 등급: {grade} / {score}점\n{opinion}"
        d = _make_doc(patent_id, text, "종합의견", base_meta)
        if d:
            docs.append(d)

    # ── dimension_cards 요약 ─────────────────────────────────────────────────
    cards = summary_block.get("dimension_cards") if isinstance(summary_block.get("dimension_cards"), list) else []
    for card in cards:
        label = card.get("label") or card.get("key") or ""
        card_score = card.get("score_out_of_100") or ""
        card_grade = card.get("grade") or ""
        card_summary = card.get("summary") or ""
        if card_summary:
            text = f"{header}{label} 평가 [{card_grade} / {card_score}점]\n{card_summary}"
            d = _make_doc(patent_id, text, f"차원요약_{label}", base_meta)
            if d:
                docs.append(d)

    # ── evaluation.dimensions 상세 ───────────────────────────────────────────
    dimensions = eval_block.get("dimensions") if isinstance(eval_block.get("dimensions"), list) else []
    for dim in dimensions:
        dim_label = dim.get("label") or dim.get("key") or ""
        dim_summary = dim.get("summary") or ""
        items = dim.get("items") if isinstance(dim.get("items"), list) else []

        # dimension 요약 청크
        if dim_summary:
            text = f"{header}{dim_label} 평가 요약\n{dim_summary}"
            d = _make_doc(patent_id, text, f"차원상세_{dim_label}", base_meta)
            if d:
                docs.append(d)

        # 항목별 판단 근거 청크 (평가의 핵심 증거)
        for item in items:
            name = item.get("name") or ""
            j_summary = item.get("judgment_summary") or ""
            j_basis = item.get("judgment_basis") or ""
            if j_summary or j_basis:
                parts = [f"{header}{dim_label} / {name}"]
                if j_summary:
                    parts.append(f"판단 요약: {j_summary}")
                if j_basis:
                    parts.append(f"판단 근거: {j_basis}")
                text = "\n".join(parts)
                d = _make_doc(patent_id, text, f"평가항목_{dim_label}_{name}", base_meta)
                if d:
                    docs.append(d)

    # ── similar_patents ──────────────────────────────────────────────────────
    similar = report_inner.get("similar_patents") if isinstance(report_inner.get("similar_patents"), list) else []
    if similar:
        lines = [f"{header}유사 특허 분석"]
        for sp in similar[:10]:
            if not isinstance(sp, dict):
                continue
            num = sp.get("registration_number") or sp.get("publication_number") or ""
            sp_title = sp.get("title") or ""
            diff = sp.get("differentiation_summary") or sp.get("similarity_reason") or ""
            if sp_title or diff:
                lines.append(f"- {num} {sp_title}: {diff}")
        if len(lines) > 1:
            d = _make_doc(patent_id, "\n".join(lines), "유사특허분석", base_meta)
            if d:
                docs.append(d)

    # ── risks ────────────────────────────────────────────────────────────────
    risks = report_inner.get("risks") if isinstance(report_inner.get("risks"), list) else []
    if risks:
        lines = [f"{header}권리 리스크"]
        for r in risks:
            if isinstance(r, dict):
                lines.append(f"- {r.get('description') or r.get('title') or ''}")
            elif isinstance(r, str):
                lines.append(f"- {r}")
        if len(lines) > 1:
            d = _make_doc(patent_id, "\n".join(lines), "권리리스크", base_meta)
            if d:
                docs.append(d)

    return docs


def _pre_eval_report_to_docs(
    case_id: str,
    report: dict[str, Any],
    *,
    source_key: str | None = None,
    source_path: str | None = None,
) -> list[dict[str, Any]]:
    """Convert pre-evaluation MinIO report → indexable chunks.

    input.json은 포함하지 않습니다 (사용자 요청).
    """
    docs: list[dict[str, Any]] = []
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    input_summary = report.get("input_summary") if isinstance(report.get("input_summary"), dict) else {}
    evaluation_id = str(report.get("evaluation_id") or "")
    pre_evaluation_id = str(metadata.get("pre_evaluation_id") or case_id)
    title = report.get("patent_title") or input_summary.get("title") or case_id
    base_meta = {
        "case_id": case_id,
        "pre_evaluation_id": pre_evaluation_id,
        "evaluation_id": evaluation_id,
        "source_type": "PRE_EVAL_REPORT",
        "patent_title": title,
        "schema_version": report.get("schema_version") or "",
        "file_name": "report.json",
    }
    if source_key:
        base_meta["source_path"] = f"s3://{_bucket()}/{source_key}"
        base_meta["relative_source_path"] = f"minio/{source_key}"
    elif source_path:
        base_meta["source_path"] = source_path
    header_bits = [f"사전평가 Case ID: {case_id}"]
    if evaluation_id:
        header_bits.append(f"평가 ID: {evaluation_id}")
    header_bits.append(str(title))
    header = "[" + "] [".join(header_bits) + "]\n"

    def _render(value: Any, *, indent: int = 0, max_items: int = 40) -> str:
        pad = "  " * indent
        if value is None:
            return ""
        if isinstance(value, (str, int, float, bool)):
            return str(value).strip()
        if isinstance(value, dict):
            lines: list[str] = []
            for key, child in value.items():
                rendered = _render(child, indent=indent + 1, max_items=max_items)
                if not rendered:
                    continue
                if isinstance(child, (dict, list)):
                    lines.append(f"{pad}- {key}:")
                    lines.append(rendered)
                else:
                    lines.append(f"{pad}- {key}: {rendered}")
            return "\n".join(lines)
        if isinstance(value, list):
            lines = []
            for item in value[:max_items]:
                rendered = _render(item, indent=indent + 1, max_items=max_items)
                if not rendered:
                    continue
                if isinstance(item, dict):
                    lines.append(f"{pad}-")
                    lines.append(rendered)
                else:
                    lines.append(f"{pad}- {rendered}")
            return "\n".join(lines)
        return str(value).strip()

    def _doc(text: str, section: str) -> dict[str, Any] | None:
        t = str(text or "").strip()
        if len(t) < 20:
            return None
        h = hashlib.sha1(f"{case_id}:{section}:{t}".encode()).hexdigest()[:12]
        return {
            "doc_id": f"{case_id}_{h}",
            "page_content": t[:20000],
            "metadata": {**base_meta, "section_title": section},
        }

    def _add_section(key: str, label: str, section: str | None = None, *, limit: int = 6000) -> None:
        value = report.get(key)
        rendered = _render(value)
        if not rendered:
            return
        d = _doc(f"{header}{label}\n{rendered[:limit]}", section or label)
        if d:
            docs.append(d)

    # 새 v3 보고서 구조의 주요 섹션을 먼저 청크화합니다.
    for key, label in [
        ("input_summary", "입력 요약"),
        ("executive_summary", "평가 요약"),
        ("valuation_assessment", "사전 가치평가"),
        ("commercialization_assessment", "사업화 가치"),
        ("readiness", "출원 준비도"),
        ("claim_strategy", "권리화 전략"),
        ("prior_art_search_plan", "선행기술 조사 계획"),
        ("filing_strategy", "출원 전략"),
        ("filing_investment_decision", "출원 투자 판단"),
        ("next_actions", "보완 액션"),
        ("limitations", "평가 한계"),
    ]:
        _add_section(key, label)

    diagnostics_parts = {
        "diagnostics": report.get("diagnostics"),
        "ai_classification": report.get("ai_classification"),
        "keywords": report.get("keywords"),
        "frontend_summary": report.get("frontend_summary"),
    }
    rendered_diagnostics = _render(diagnostics_parts)
    if rendered_diagnostics:
        d = _doc(f"{header}진단 및 분류\n{rendered_diagnostics[:6000]}", "진단 및 분류")
        if d:
            docs.append(d)

    # 종합 평가
    overall = report.get("overall") if isinstance(report.get("overall"), dict) else {}
    if overall.get("comment"):
        text = (
            f"{header}종합 등급: {overall.get('grade','?')} / {overall.get('score_out_of_100','?')}점\n"
            f"{overall['comment']}"
        )
        d = _doc(text, "종합평가")
        if d:
            docs.append(d)

    # executive_summary
    exec_sum = report.get("executive_summary")
    if exec_sum and isinstance(exec_sum, dict):
        for k, v in exec_sum.items():
            if isinstance(v, str) and len(v) > 20:
                d = _doc(f"{header}{k}\n{v}", f"요약_{k}")
                if d:
                    docs.append(d)
    elif isinstance(exec_sum, str) and len(exec_sum) > 20:
        d = _doc(f"{header}{exec_sum}", "요약")
        if d:
            docs.append(d)

    # llm_comment (strengths, risks)
    llm = report.get("llm_comment") if isinstance(report.get("llm_comment"), dict) else {}
    if llm.get("overall_comment"):
        d = _doc(f"{header}LLM 종합 의견\n{llm['overall_comment']}", "LLM종합의견")
        if d:
            docs.append(d)
    strengths = llm.get("strengths") or []
    if strengths:
        d = _doc(f"{header}강점\n" + "\n".join(f"- {s}" for s in strengths if s), "강점")
        if d:
            docs.append(d)
    risks = llm.get("risks") or []
    if risks:
        d = _doc(f"{header}리스크\n" + "\n".join(f"- {r}" for r in risks if r), "리스크")
        if d:
            docs.append(d)

    # dimensions
    dims = report.get("dimensions") if isinstance(report.get("dimensions"), list) else []
    for dim in dims:
        if not isinstance(dim, dict):
            continue
        label = dim.get("label") or dim.get("key") or ""
        dim_sum = dim.get("summary") or dim.get("comment") or ""
        items = dim.get("items") if isinstance(dim.get("items"), list) else []
        if dim_sum:
            d = _doc(f"{header}{label} 평가\n{dim_sum}", f"차원_{label}")
            if d:
                docs.append(d)
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or ""
            comment = item.get("comment") or item.get("judgment") or ""
            if comment:
                d = _doc(f"{header}{label} / {name}\n{comment}", f"항목_{label}_{name}")
                if d:
                    docs.append(d)

    # score_items
    score_items = report.get("score_items") if isinstance(report.get("score_items"), list) else []
    for item in score_items:
        if not isinstance(item, dict):
            continue
        dim = item.get("dimension") or ""
        name = item.get("name") or ""
        comment = item.get("comment") or item.get("judgment_summary") or ""
        if comment:
            d = _doc(f"{header}{dim} / {name}\n{comment}", f"점수항목_{name}")
            if d:
                docs.append(d)

    if not docs:
        fallback = json.dumps(report, ensure_ascii=False)
        d = _doc(f"{header}전체 보고서\n{fallback[:12000]}", "전체 보고서")
        if d:
            docs.append(d)
    return docs


# ---------------------------------------------------------------------------
# PDF visual text extraction
# ---------------------------------------------------------------------------

def _extract_pdf_text_docs(
    pdf_path: Path,
    patent_id: str,
    work_dir: Path,
) -> list[dict[str, Any]]:
    """Extract text from PDF visual pages and return as plain text chunks.

    Uses existing extract_pdf_visual_documents (legacy ingest).
    Returns list of doc dicts ready for upsert_documents.
    Errors are caught and logged — never raises (to protect the caller's upsert).
    """
    try:
        from .legacy.ingest import extract_pdf_visual_documents, MAX_VISUAL_ASSETS_PER_DOCUMENT
    except ImportError as exc:
        logger.warning("PDF visual extraction unavailable: %s", exc)
        return []

    try:
        raw_docs = extract_pdf_visual_documents(
            pdf_path=pdf_path,
            patent_dir=work_dir,
            patent_id=patent_id,
            source_document_type="ORIGINAL_PDF",
            public_file_base_url="/files/shared",
            file_name_for_url="original.pdf",
            meta={"patent_id": patent_id, "title": patent_id},
            max_assets=MAX_VISUAL_ASSETS_PER_DOCUMENT,
        )
    except Exception as exc:
        logger.warning("extract_pdf_visual_documents failed for %s: %s", patent_id, exc)
        return []

    docs: list[dict[str, Any]] = []
    for raw in raw_docs:
        page_content = str(getattr(raw, "page_content", "") or "").strip()
        if not page_content or len(page_content) < 30:
            continue
        metadata = dict(getattr(raw, "metadata", {}) or {})
        metadata.update({
            "patent_id": patent_id,
            "source_type": "ORIGINAL_VISUAL",
            "file_name": "original.pdf",
            "relative_source_path": f"minio/patents/original.pdf",
        })
        chunk_id = metadata.get("chunk_id") or _doc_id(
            patent_id, f"visual:{metadata.get('page_no')}:{metadata.get('asset_kind')}:{len(page_content)}"
        )
        docs.append({
            "doc_id": str(chunk_id),
            "page_content": page_content,
            "metadata": metadata,
        })
    return docs


# ---------------------------------------------------------------------------
# Main public functions
# ---------------------------------------------------------------------------

def build_patent_vectorstore_from_minio(minio_path: str) -> dict[str, Any]:
    """MinIO 경로를 받아 특허 per-patent 벡터스토어를 (재)생성합니다.

    처리 순서:
      1. parsed.json 다운로드 (있으면 텍스트 청크 생성)
      2. 최신 reports/{N}/report.json 다운로드 (N 최대값)
      3. original.pdf 다운로드 → PDF 시각 텍스트 추출
      4. 모든 청크를 skipa_patent_doc_{folder_id}에 upsert (recreate=True → 기존 삭제)

    Args:
        minio_path: 'patents/1', '1', 'patents/1/' 등을 모두 수용
    """
    client = _boto3_client()
    base_prefix = _normalize_minio_prefix(minio_path, "patents")
    patent_id = _patent_id_from_prefix(base_prefix)
    started_at = datetime.now().isoformat(timespec="seconds")

    # ── 1. parsed.json ────────────────────────────────────────────────────────
    parsed_key = base_prefix + "parsed.json"
    parsed = _get_json(client, parsed_key)
    text_docs: list[dict[str, Any]] = []
    registration_number: str | None = None
    if parsed:
        registration_number = _patent_id_from_parsed(parsed)
        from .shared_data import _parsed_to_docs
        text_docs = _parsed_to_docs(patent_id, parsed)
        logger.info("parsed.json → %d chunks for %s", len(text_docs), patent_id)
    else:
        logger.warning("No parsed.json for %s (prefix: %s); report/PDF chunks will still be indexed", patent_id, base_prefix)

    # ── 2. latest report.json ─────────────────────────────────────────────────
    report_key = _latest_report_key(client, base_prefix)
    report_docs: list[dict[str, Any]] = []
    report_version: str | None = None
    if report_key:
        report_raw = _get_json(client, report_key)
        if report_raw:
            from .shared_data import _report_to_docs

            report_docs = _report_to_docs(patent_id, report_raw)
            for doc in report_docs:
                metadata = dict(doc.get("metadata") or {})
                metadata.update(
                    {
                        "source_path": f"s3://{_bucket()}/{report_key}",
                        "relative_source_path": f"minio/{report_key}",
                        "file_name": "report.json",
                    }
                )
                doc["metadata"] = metadata
            report_version = report_key.split("/")[-2]  # e.g. '1', '2'
            logger.info("report.json (v%s) → %d chunks for %s", report_version, len(report_docs), patent_id)
    else:
        logger.warning("No reports/ found for %s (prefix: %s)", patent_id, base_prefix)

    # ── 3. original.pdf → PDF 시각 텍스트 ────────────────────────────────────
    pdf_docs: list[dict[str, Any]] = []
    pdf_key = base_prefix + "original.pdf"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        pdf_local = tmp_path / "original.pdf"
        try:
            client.download_file(Bucket=_bucket(), Key=pdf_key, Filename=str(pdf_local))
            pdf_docs = _extract_pdf_text_docs(pdf_local, patent_id, tmp_path)
            logger.info("original.pdf → %d visual text chunks for %s", len(pdf_docs), patent_id)
        except Exception as exc:
            logger.warning("PDF download/extraction failed for %s: %s", patent_id, exc)

    # ── 4. upsert (기존 컬렉션 삭제 포함) ────────────────────────────────────
    all_docs = text_docs + report_docs + pdf_docs
    if not all_docs:
        raise RuntimeError(f"청크가 하나도 생성되지 않았습니다: {patent_id}")

    from .qdrant_store import patent_collection, upsert_documents
    coll = patent_collection(patent_id)
    result = upsert_documents(
        coll,
        all_docs,
        collection_scope="patent",
        recreate=True,
        extra_payload={"patent_id": patent_id, "source": "minio"},
    )

    return {
        "status": "built",
        "patent_id": patent_id,
        "registration_number": registration_number,
        "collection": coll,
        "minio_path": base_prefix,
        "parsed_chunks": len(text_docs),
        "report_chunks": len(report_docs),
        "pdf_chunks": len(pdf_docs),
        "total_chunks": len(all_docs),
        "report_version": report_version,
        "started_at": started_at,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_provider": result.get("embedding_provider"),
        "embedding_error": result.get("embedding_error"),
    }


def build_pre_eval_vectorstore_from_minio(minio_path: str) -> dict[str, Any]:
    """MinIO 경로를 받아 사전평가 벡터스토어를 (재)생성합니다.

    처리 순서:
      1. report.json 다운로드 (input.json은 인덱싱하지 않음)
      2. report 청크 생성
      3. pre-{case_id} 컬렉션에 upsert (recreate=True → 기존 삭제)

    Args:
        minio_path: 'pre-evaluations/1', '1', 'pre-evaluations/1/' 등을 모두 수용
    """
    client = _boto3_client()
    base_prefix = _normalize_minio_prefix(minio_path, "pre-evaluations")
    started_at = datetime.now().isoformat(timespec="seconds")

    report_key = base_prefix + "report.json"
    report = _get_json(client, report_key)
    if not report:
        raise FileNotFoundError(f"MinIO에서 report.json을 찾을 수 없습니다: {report_key}")

    case_id = base_prefix.rstrip("/").split("/")[-1]
    docs = _pre_eval_report_to_docs(case_id, report, source_key=report_key)
    if not docs:
        raise RuntimeError(f"청크가 하나도 생성되지 않았습니다: {case_id}")

    from .qdrant_store import pre_application_collection, upsert_documents
    coll = pre_application_collection(case_id)
    result = upsert_documents(
        coll,
        docs,
        collection_scope=f"pre_application:{case_id}",
        recreate=True,
        extra_payload={"case_id": case_id, "pre_evaluation_id": case_id, "source": "minio"},
    )

    return {
        "status": "built",
        "case_id": case_id,
        "eval_id": case_id,
        "evaluation_id": report.get("evaluation_id"),
        "patent_title": report.get("patent_title"),
        "collection": coll,
        "minio_path": base_prefix,
        "total_chunks": len(docs),
        "started_at": started_at,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_provider": result.get("embedding_provider"),
        "embedding_error": result.get("embedding_error"),
    }


def list_minio_patents(client=None) -> list[str]:
    """Return MinIO path prefixes for all patents (e.g. ['patents/1/', 'patents/2/'])."""
    c = client or _boto3_client()
    return _list_subdirs(c, "patents/")


def list_minio_pre_evals(client=None) -> list[str]:
    """Return MinIO path prefixes for all pre-evaluations."""
    c = client or _boto3_client()
    return _list_subdirs(c, "pre-evaluations/")
