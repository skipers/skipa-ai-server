#!/usr/bin/env python3
"""Run business-user regression questions for the patent chatbots.

The default mode is intentionally practical for large batches: it runs the real
LangGraph nodes but skips network LLM/BERT calls so 200+200 questions can finish
in a local demo environment. Use ``--execution-mode full`` and
``--enable-bert-score`` for smaller, slower end-to-end quality checks.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
if (SCRIPT_PATH.parents[1] / "chatbot" / "app").exists():
    PROJECT_ROOT = SCRIPT_PATH.parents[1]
else:
    PROJECT_ROOT = SCRIPT_PATH.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ARTIFACT_ROOT = PROJECT_ROOT / "chatbot" / "data" / "artifacts" / "chatbot_business_tests"


def _normalize_output_dir(path: Path) -> Path:
    """Keep chatbot test artifacts under chatbot/data/artifacts.

    Older commands used PROJECT_ROOT/data/artifacts. Redirect that location so
    running old scripts does not recreate the root data/artifacts folder.
    """
    resolved = (PROJECT_ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    old_root = (PROJECT_ROOT / "data" / "artifacts").resolve()
    new_root = (PROJECT_ROOT / "chatbot" / "data" / "artifacts").resolve()
    try:
        suffix = resolved.relative_to(old_root)
    except ValueError:
        return resolved
    return new_root / suffix


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _write_jsonl(path: Path, item: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(item, ensure_ascii=False, default=_json_default) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _patch_expensive_optional_calls(*, enable_bert_score: bool, execution_mode: str) -> None:
    """Keep large batches from spending hours in optional model calls."""
    if not enable_bert_score:
        import chatbot.app.rag.evaluation as evaluation

        def _skip_bert(answer: str, evidence_text: str) -> dict[str, Any]:
            return {
                "available": False,
                "reason": "skipped by business batch test; rerun with --enable-bert-score for BERTScore",
                "fallback_metric": "semantic_answer_evidence_score",
            }

        evaluation._optional_bert_score = _skip_bert  # type: ignore[attr-defined]

    if execution_mode == "functional":
        import chatbot.app.agents.application_graph as application_graph
        import chatbot.app.rag.policy as policy

        def _skip_llm(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {
                "ok": False,
                "text": "",
                "error": "skipped by business functional batch; rerun with --execution-mode full",
            }

        policy.call_ollama = _skip_llm
        application_graph.call_ollama = _skip_llm


def _load_patents(limit: int | None = None) -> list[dict[str, Any]]:
    from chatbot.app.store import list_patents

    patents = [item for item in list_patents() if item.get("patent_id")]
    if limit:
        patents = patents[:limit]
    return patents


PATENT_QUESTION_TEMPLATES: list[tuple[str, str]] = [
    ("overview", "{title} 특허를 사업부 관점에서 5줄로 요약해줘"),
    ("overview", "{title}의 핵심 발명 포인트와 적용 제품을 알려줘"),
    ("original", "{title} 원문 기준으로 기술분야와 해결과제를 정리해줘"),
    ("original", "{title} 청구항에서 반드시 지켜야 할 핵심 구성을 알려줘"),
    ("original", "{title} 원문 PDF에서 실시예와 도면 흐름을 설명해줘"),
    ("report", "{title} 평가 보고서의 종합 점수와 세부 점수를 설명해줘"),
    ("report", "{title} 유지 판단 근거를 표로 알려줘"),
    ("report", "{title} 포기 또는 제각하면 안 되는 근거를 알려줘"),
    ("risk", "{title}의 권리 리스크와 회피설계 가능성을 정리해줘"),
    ("risk", "{title}에서 추가 확인해야 할 법적 리스크를 알려줘"),
    ("business", "{title}의 사업화 가능성과 현재 활용 가능성을 평가해줘"),
    ("business", "{title}를 사업부가 유지해야 할지 매각해야 할지 판단 근거를 줘"),
    ("market", "{title} 관련 최신 시장 동향이 필요한지 판단하고 근거를 알려줘"),
    ("market", "{title}의 시장성 판단을 최신 외부 정보까지 고려해서 알려줘"),
    ("comparison", "{title}와 유사 특허가 있으면 차이점을 비교해줘"),
    ("comparison", "{title}의 유사 특허 현황을 표로 정리해줘"),
    ("table", "{title}의 기술성 권리성 시장성을 표로 비교해줘"),
    ("diagram", "{title}의 RAG 판단 흐름을 다이어그램으로 보여줘"),
    ("diagram", "{title} 기술 구성 흐름을 다이어그램으로 설명해줘"),
    ("evidence", "{title} 답변 근거가 원문인지 보고서인지 구분해서 알려줘"),
    ("evidence", "{title} 관련 근거 파일 제목과 섹션명을 알려줘"),
    ("history", "{title}의 핵심 리스크만 이어서 알려줘"),
    ("history", "그럼 이 특허의 사업화 리스크만 이어서 표로 알려줘"),
    ("wiki", "{title} 관련 최신 외부 정보가 필요하면 wiki 먼저 확인해서 알려줘"),
    ("web", "{title} 관련 최근 뉴스나 시장 변화가 답변에 필요한지 알려줘"),
    ("report", "{title}의 유지/매각/제각 선택지를 의사결정 표로 만들어줘"),
    ("original", "{title} 발명의 효과와 기존 기술 대비 차별점을 알려줘"),
    ("risk", "{title}를 무효화 공격받을 때 취약할 수 있는 지점을 알려줘"),
    ("business", "{title}를 라이선싱 후보로 볼 수 있는지 판단해줘"),
    ("table", "{title} 근거 기반으로 사업부 액션아이템을 표로 정리해줘"),
    ("diagram", "{title}의 원문-보고서-답변 연결 구조를 다이어그램으로 보여줘"),
    ("comparison", "{title}를 전체 특허 포트폴리오 안에서 상대 비교해줘"),
    ("overview", "{title} 특허를 임원 보고용으로 한 문단으로 정리해줘"),
    ("report", "{title} 평가 보고서에서 가장 낮은 항목과 이유를 알려줘"),
    ("report", "{title} 평가 보고서에서 가장 높은 항목과 이유를 알려줘"),
    ("original", "{title} 원문에서 발명의 구성요소를 번호로 나눠줘"),
    ("evidence", "{title} 답변에서 신뢰도가 낮은 근거가 있으면 표시해줘"),
    ("market", "{title} 시장 규모나 경쟁 상황은 웹검색이 필요한지 판단해줘"),
    ("history", "앞에서 말한 유지 판단을 기준으로 다음 회의 질문 목록을 만들어줘"),
    ("business", "{title}를 사업부 PoC 후보로 볼 때 필요한 추가 데이터를 알려줘"),
]


APPLICATION_QUESTION_TEMPLATES: list[tuple[str, str]] = [
    ("application_procedure", "처음 특허 출원할 때 어떤 순서로 준비해야 해?"),
    ("application_procedure", "발명 아이디어가 있는데 출원 전에 무엇부터 정리해야 해?"),
    ("application_procedure", "제품 출시 전에 특허 출원을 준비하는 체크리스트를 표로 알려줘"),
    ("application_procedure", "처음 출원 절차를 다이어그램으로 보여줘"),
    ("forms_and_filing", "특허고객번호와 인증서는 어떤 순서로 준비해야 해?"),
    ("forms_and_filing", "전자출원에 필요한 서류와 준비물을 표로 알려줘"),
    ("forms_and_filing", "출원서, 명세서, 청구범위, 요약서, 도면 각각의 역할을 알려줘"),
    ("forms_and_filing", "공동출원일 때 추가로 확인할 서류가 뭐야?"),
    ("fees", "특허 출원 수수료와 심사청구료를 어떻게 확인해야 해?"),
    ("fees", "개인이나 중소기업 감면은 어떤 자료를 확인해야 해?"),
    ("fees", "출원료, 심사청구료, 등록료를 단계별 표로 정리해줘"),
    ("drafting_claims", "넓은 독립항과 방어용 종속항은 어떻게 설계해야 해?"),
    ("drafting_claims", "명세서 작성할 때 해결과제와 효과를 어떻게 써야 해?"),
    ("drafting_claims", "청구항 초안 검토 체크리스트를 만들어줘"),
    ("drafting_claims", "청구범위를 너무 좁게 쓰지 않으려면 무엇을 봐야 해?"),
    ("prior_art_search", "선행기술조사는 KIPRIS에서 어떤 순서로 해야 해?"),
    ("prior_art_search", "CPC와 IPC를 이용한 유사특허 검색 플로우를 알려줘"),
    ("prior_art_search", "신규성과 진보성 판단을 위한 검색 키워드 확장 방법을 알려줘"),
    ("prior_art_search", "선행기술 조사 결과를 표로 정리하는 양식을 만들어줘"),
    ("rejection_response", "거절의견서를 받으면 먼저 무엇을 확인해야 해?"),
    ("rejection_response", "거절이유가 신규성인지 진보성인지 구분하는 방법을 알려줘"),
    ("rejection_response", "의견서와 보정서를 준비할 때 신규사항 추가를 피하는 방법을 알려줘"),
    ("rejection_response", "출원 실패한 특허의 보고서를 만들고 수정 방향을 피드백하려면 어떤 흐름이야?"),
    ("rejection_response", "특허거절의견서.pdf 같은 의견서를 넣으면 어떤 기준으로 실패 요인을 분석해?"),
    ("application_strategy", "우선심사와 심사유예 중 어떤 전략을 선택해야 해?"),
    ("application_strategy", "해외출원 우선권 일정은 어떻게 잡아야 해?"),
    ("application_strategy", "사업화 목적의 특허 출원 전략을 표로 정리해줘"),
    ("application_strategy", "시장 동향과 경쟁사 정보를 반영한 출원 전략을 알려줘"),
    ("application_strategy", "투자 유치 전에 특허 권리화 전략을 어떻게 잡아야 해?"),
    ("history", "방금 말한 순서에서 선행기술조사만 더 자세히 설명해줘"),
    ("history", "그럼 이 절차를 우리 팀 액션아이템으로 바꿔줘"),
    ("history", "앞에서 말한 거절 대응 흐름을 다이어그램으로 다시 보여줘"),
    ("evidence", "답변 근거가 어떤 공식 자료에서 왔는지 제목별로 알려줘"),
    ("evidence", "출원팩 근거와 외부 검색 근거를 구분해서 알려줘"),
    ("report_connection", "출원 예정 특허를 평가 보고서 에이전트에 넣으면 어떤 결과를 받을 수 있어?"),
    ("report_connection", "출원 실패 특허 원문과 거절의견을 연결해서 피드백 보고서를 생성하는 흐름을 알려줘"),
    ("external", "KIPRIS, KOSIS, Tavily를 각각 언제 사용해야 해?"),
    ("external", "출원 전략에서 시장 통계가 필요하면 어떤 외부 경로를 써야 해?"),
    ("table_diagram", "특허 출원 준비부터 거절 대응까지 전체 흐름을 표와 다이어그램으로 알려줘"),
    ("table_diagram", "출원 챗봇이 어떤 데이터를 찾아 답변하는지 다이어그램으로 알려줘"),
]


def _build_patent_questions(count: int, patents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not patents:
        patents = [{"patent_id": None, "title": "선택 특허"}]
    questions = []
    for index in range(count):
        patent = patents[index % len(patents)]
        category, template = PATENT_QUESTION_TEMPLATES[index % len(PATENT_QUESTION_TEMPLATES)]
        title = patent.get("title") or patent.get("patent_id") or "선택 특허"
        question = template.format(title=title, patent_id=patent.get("patent_id"))
        chat_history: list[dict[str, Any]] = []
        if category == "history":
            chat_history = [
                {
                    "question": f"{title}의 유지 판단과 주요 리스크를 알려줘",
                    "answer": "앞선 답변에서는 평가 점수, 권리 리스크, 사업부 활용 가능성을 기준으로 봤습니다.",
                }
            ]
        if index % 17 == 0:
            question = f"{question} 근거 제목도 같이 표시해줘"
        questions.append(
            {
                "index": index + 1,
                "chatbot": "patent",
                "category": category,
                "patent_id": patent.get("patent_id"),
                "patent_title": title,
                "question": question,
                "chat_history": chat_history,
            }
        )
    return questions


def _build_application_questions(count: int) -> list[dict[str, Any]]:
    questions = []
    for index in range(count):
        category, question = APPLICATION_QUESTION_TEMPLATES[index % len(APPLICATION_QUESTION_TEMPLATES)]
        chat_history: list[dict[str, Any]] = []
        if category == "history":
            chat_history = [
                {
                    "question": "처음 특허 출원할 때 어떤 순서로 준비해야 해?",
                    "answer": "발명 정리, 선행기술조사, 청구항 설계, 서류 준비, 전자출원 순서로 진행합니다.",
                }
            ]
        if index % 19 == 0:
            question = f"{question} 근거 자료 제목도 같이 알려줘"
        questions.append(
            {
                "index": index + 1,
                "chatbot": "application",
                "category": category,
                "patent_id": "patent_application",
                "question": question,
                "chat_history": chat_history,
            }
        )
    return questions


def _source_titles(source_cards: list[dict[str, Any]]) -> list[str]:
    titles = []
    for card in source_cards:
        title = card.get("display_title") or card.get("title") or card.get("source_path") or card.get("label")
        if title and str(title) not in titles:
            titles.append(str(title))
    return titles[:8]


def _source_types(source_cards: list[dict[str, Any]]) -> list[str]:
    types = []
    for card in source_cards:
        source_type = card.get("source_type")
        if source_type and str(source_type) not in types:
            types.append(str(source_type))
    return types


def _record_result(
    *,
    item: dict[str, Any],
    result: dict[str, Any] | None,
    elapsed_sec: float,
    error: str | None = None,
) -> dict[str, Any]:
    result = result or {}
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    source_cards = result.get("source_cards") if isinstance(result.get("source_cards"), list) else []
    quality = metrics.get("answer_quality") if isinstance(metrics.get("answer_quality"), dict) else {}
    intent_agent = metrics.get("intent_agent") if isinstance(metrics.get("intent_agent"), dict) else {}
    trace = metrics.get("agent_trace") if isinstance(metrics.get("agent_trace"), list) else []
    answer = str(result.get("answer") or "")
    return {
        "index": item.get("index"),
        "chatbot": item.get("chatbot"),
        "category": item.get("category"),
        "question": item.get("question"),
        "patent_id": item.get("patent_id"),
        "patent_title": item.get("patent_title"),
        "success": error is None,
        "elapsed_sec": round(elapsed_sec, 3),
        "error": error,
        "answer": answer,
        "answer_preview": answer[:500],
        "answer_length": len(answer),
        "source_count": len(source_cards),
        "source_titles": _source_titles(source_cards),
        "source_types": _source_types(source_cards),
        "intent": intent_agent.get("intent"),
        "intent_method": intent_agent.get("method"),
        "source_plan": intent_agent.get("source_plan") or metrics.get("source_plan"),
        "answer_format": intent_agent.get("answer_format") or metrics.get("answer_format_plan"),
        "needs_web": intent_agent.get("needs_web") if "needs_web" in intent_agent else intent_agent.get("needs_external"),
        "engine": metrics.get("engine"),
        "answer_mode": metrics.get("answer_mode") or metrics.get("answer_strategy"),
        "quality": {
            "composite_score": quality.get("composite_score"),
            "grade": quality.get("grade"),
            "semantic_answer_evidence_score": quality.get("semantic_answer_evidence_score"),
            "keyword_answer_coverage": quality.get("keyword_answer_coverage"),
            "keyword_evidence_coverage": quality.get("keyword_evidence_coverage"),
            "bert_score": quality.get("bert_score"),
        },
        "trace_nodes": [step.get("node") for step in trace if isinstance(step, dict)],
        "metrics": metrics,
        "source_cards": source_cards,
    }


def _patent_source_types_from_intent(intent: dict[str, Any]) -> set[str]:
    from chatbot.app.vectorstore import CORE_SEARCH_SOURCE_TYPES

    plan = {str(item) for item in intent.get("source_plan") or []}
    source_types: set[str] = set()
    if {"reviewed_vectorstore", "global_patents"} & plan:
        source_types.update(CORE_SEARCH_SOURCE_TYPES)
    if "original" in plan:
        source_types.update({"ORIGINAL_PDF", "PATENT_INPUT_JSON"})
    if "report" in plan:
        source_types.update({"REPORT_PDF", "REPORT_JSON", "APPLICATION_FEEDBACK_REPORT"})
    return source_types or set(CORE_SEARCH_SOURCE_TYPES)


def _run_patent_retrieval_item(item: dict[str, Any], top_k: int) -> dict[str, Any]:
    from chatbot.app.rag.evaluation import answer_quality_metrics
    from chatbot.app.rag.policy import classify_intent
    from chatbot.app.rag.sources import cards_from_hits
    from chatbot.app.store import search_chunks

    intent = classify_intent(item["question"])
    source_types = _patent_source_types_from_intent(intent)
    search_result = search_chunks(
        item["question"],
        patent_id=item.get("patent_id"),
        source_types=source_types,
        top_k=top_k,
    )
    hits = list(search_result.get("hits") or [])
    source_cards = cards_from_hits(hits, query=item["question"])
    if source_cards:
        lines = [
            "## 근거 검색 기반 진단 답변",
            "",
            "이 레코드는 200문항 대량 검증용으로, 특허 챗봇의 의도 라우팅과 core vectorstore 근거 검색 결과를 확인합니다.",
            "",
            f"- 분류 의도: {intent.get('intent')}",
            f"- 답변 형식 계획: {intent.get('answer_format')}",
            f"- 검색 근거 수: {len(source_cards)}",
            "",
            "### 상위 근거",
        ]
        for index, card in enumerate(source_cards[:5], 1):
            title = card.get("display_title") or card.get("title") or card.get("label")
            snippet = " ".join(str(card.get("snippet") or "").split())[:240]
            lines.append(f"{index}. **{card.get('source_type')} / {title}**: {snippet}")
        answer = "\n".join(lines)
    else:
        answer = (
            "## 근거 검색 기반 진단 답변\n\n"
            "core vectorstore에서 직접 답변에 쓸 근거를 찾지 못했습니다. full graph에서는 wiki gate 또는 웹검색 fallback이 필요합니다."
        )
    retrieval_scores = [hit.get("score") for hit in hits if isinstance(hit.get("score"), (int, float))]
    metrics = {
        "engine": "patent_retrieval_diagnostic",
        "intent_agent": intent,
        "hit_count": len(hits),
        "mode": search_result.get("mode"),
        "documents_path": search_result.get("documents_path"),
        "source_plan": intent.get("source_plan"),
        "answer_format_plan": intent.get("answer_format"),
        "agent_trace": [
            {"node": "route_question", "status": "success", "intent": intent},
            {"node": "search_core_vectorstore", "status": "success", "hit_count": len(hits)},
            {"node": "build_diagnostic_answer", "status": "success", "source_count": len(source_cards)},
        ],
    }
    metrics["answer_quality"] = answer_quality_metrics(
        query=item["question"],
        answer=answer,
        source_cards=source_cards,
        retrieval_scores=retrieval_scores,
    )
    return {
        "query": item["question"],
        "patent_id": item.get("patent_id"),
        "answer": answer,
        "source_cards": source_cards,
        "metrics": metrics,
    }


def _run_patent_item(item: dict[str, Any], top_k: int, runner: str) -> dict[str, Any]:
    if runner == "retrieval":
        return _run_patent_retrieval_item(item, top_k=top_k)

    from chatbot.app.agents.graph import run_chat_agent

    return run_chat_agent(
        item["question"],
        patent_id=item.get("patent_id"),
        chat_history=item.get("chat_history") or [],
        top_k=top_k,
    )


def _run_application_item(item: dict[str, Any], top_k: int) -> dict[str, Any]:
    from chatbot.app.agents.application_graph import run_application_agent

    return run_application_agent(
        item["question"],
        chat_history=item.get("chat_history") or [],
        top_k=top_k,
    )


def _run_batch(
    *,
    items: list[dict[str, Any]],
    output_path: Path,
    top_k: int,
    patent_runner: str,
    progress_every: int,
) -> list[dict[str, Any]]:
    output_path.unlink(missing_ok=True)
    records = []
    started = time.perf_counter()
    for offset, item in enumerate(items, 1):
        call_started = time.perf_counter()
        try:
            if item["chatbot"] == "patent":
                result = _run_patent_item(item, top_k=top_k, runner=patent_runner)
            else:
                result = _run_application_item(item, top_k=top_k)
            record = _record_result(item=item, result=result, elapsed_sec=time.perf_counter() - call_started)
        except Exception as exc:
            record = _record_result(
                item=item,
                result=None,
                elapsed_sec=time.perf_counter() - call_started,
                error=f"{type(exc).__name__}: {exc}",
            )
        _write_jsonl(output_path, record)
        records.append(record)
        if offset == 1 or offset % progress_every == 0 or offset == len(items):
            elapsed = time.perf_counter() - started
            avg = elapsed / offset
            remaining = avg * (len(items) - offset)
            print(
                f"[{item['chatbot']}] {offset}/{len(items)} done "
                f"(success={sum(1 for row in records if row['success'])}, "
                f"elapsed={elapsed:.1f}s, eta={remaining:.1f}s)",
                flush=True,
            )
    return records


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    success_rows = [row for row in records if row.get("success")]
    elapsed_values = [float(row.get("elapsed_sec") or 0) for row in records]
    source_counts = [int(row.get("source_count") or 0) for row in success_rows]
    quality_scores = [
        float((row.get("quality") or {}).get("composite_score"))
        for row in success_rows
        if isinstance((row.get("quality") or {}).get("composite_score"), (int, float))
    ]
    return {
        "total": len(records),
        "success": len(success_rows),
        "failed": len(records) - len(success_rows),
        "avg_elapsed_sec": round(statistics.mean(elapsed_values), 3) if elapsed_values else 0,
        "p95_elapsed_sec": round(statistics.quantiles(elapsed_values, n=20)[-1], 3) if len(elapsed_values) >= 20 else None,
        "avg_source_count": round(statistics.mean(source_counts), 3) if source_counts else 0,
        "avg_quality_score": round(statistics.mean(quality_scores), 4) if quality_scores else None,
        "category_counts": dict(Counter(str(row.get("category")) for row in records)),
        "intent_counts": dict(Counter(str(row.get("intent")) for row in success_rows)),
        "answer_mode_counts": dict(Counter(str(row.get("answer_mode")) for row in success_rows)),
        "quality_grade_counts": dict(Counter(str((row.get("quality") or {}).get("grade")) for row in success_rows)),
        "source_type_counts": dict(Counter(source_type for row in success_rows for source_type in row.get("source_types") or [])),
        "errors": [
            {
                "index": row.get("index"),
                "chatbot": row.get("chatbot"),
                "category": row.get("category"),
                "question": row.get("question"),
                "error": row.get("error"),
            }
            for row in records
            if not row.get("success")
        ][:20],
    }


def _write_summary_md(path: Path, summary: dict[str, Any], output_dir: Path) -> None:
    patent = summary["patent"]
    application = summary["application"]
    lines = [
        "# Chatbot Business Batch Test Summary",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Execution mode: {summary['execution_mode']}",
        f"- Output directory: `{output_dir}`",
        "",
        "## Patent Chatbot",
        "",
        f"- Total / success / failed: {patent['total']} / {patent['success']} / {patent['failed']}",
        f"- Avg elapsed: {patent['avg_elapsed_sec']} sec",
        f"- Avg source count: {patent['avg_source_count']}",
        f"- Avg quality score: {patent['avg_quality_score']}",
        f"- Intent counts: `{json.dumps(patent['intent_counts'], ensure_ascii=False)}`",
        f"- Answer mode counts: `{json.dumps(patent['answer_mode_counts'], ensure_ascii=False)}`",
        "",
        "## Patent Application Chatbot",
        "",
        f"- Total / success / failed: {application['total']} / {application['success']} / {application['failed']}",
        f"- Avg elapsed: {application['avg_elapsed_sec']} sec",
        f"- Avg source count: {application['avg_source_count']}",
        f"- Avg quality score: {application['avg_quality_score']}",
        f"- Intent counts: `{json.dumps(application['intent_counts'], ensure_ascii=False)}`",
        f"- Answer mode counts: `{json.dumps(application['answer_mode_counts'], ensure_ascii=False)}`",
        "",
        "## Patent Application Chatbot Flow",
        "",
        "```mermaid",
        "flowchart TD",
        "  A[사용자 질문] --> B[최근 대화 이력 요약]",
        "  B --> C[가벼운 LLM 또는 룰 fallback 의도 라우팅]",
        "  C --> D{의도 유형}",
        "  D -->|출원 절차/서식/수수료| E[공식 출원팩 검색]",
        "  D -->|청구항/명세서| F[작성 가이드/심사기준 검색]",
        "  D -->|선행기술| G[KIPRIS/CPC/IPC 자료 검색]",
        "  D -->|거절/실패| H[거절의견서/피드백 리포트 검색]",
        "  D -->|전략/시장| I[전략 자료 + KOSIS/Tavily 보강]",
        "  E --> J[근거 카드 생성]",
        "  F --> J",
        "  G --> J",
        "  H --> J",
        "  I --> J",
        "  J --> K[LLM 답변 또는 guided template]",
        "  K --> L[표/다이어그램/체크리스트 형식화]",
        "  L --> M[품질 지표와 근거 제목 반환]",
        "```",
        "",
        "## Saved Files",
        "",
        "- `patent_questions.jsonl`",
        "- `application_questions.jsonl`",
        "- `patent_chat_results.jsonl`",
        "- `application_chat_results.jsonl`",
        "- `summary.json`",
        "- `summary.md`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 200-question business tests for patent chatbots.")
    parser.add_argument("--patent-count", type=int, default=200)
    parser.add_argument("--application-count", type=int, default=200)
    parser.add_argument("--patent-limit", type=int, default=None, help="Use only the first N patent folders.")
    parser.add_argument("--patent-top-k", type=int, default=4)
    parser.add_argument("--application-top-k", type=int, default=5)
    parser.add_argument(
        "--patent-runner",
        choices=["graph", "retrieval"],
        default="graph",
        help="graph runs the full patent chatbot; retrieval runs fast routing/vectorstore diagnostics.",
    )
    parser.add_argument(
        "--execution-mode",
        choices=["functional", "full"],
        default="functional",
        help="functional skips network LLM calls; full uses the live configured LLM.",
    )
    parser.add_argument("--enable-bert-score", action="store_true")
    parser.add_argument("--progress-every", type=int, default=20)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = _normalize_output_dir(args.output_dir or ARTIFACT_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S"))
    output_dir.mkdir(parents=True, exist_ok=True)

    _patch_expensive_optional_calls(enable_bert_score=args.enable_bert_score, execution_mode=args.execution_mode)

    patents = _load_patents(limit=args.patent_limit)
    patent_questions = _build_patent_questions(args.patent_count, patents)
    application_questions = _build_application_questions(args.application_count)

    patent_questions_path = output_dir / "patent_questions.jsonl"
    application_questions_path = output_dir / "application_questions.jsonl"
    patent_questions_path.unlink(missing_ok=True)
    application_questions_path.unlink(missing_ok=True)
    for item in patent_questions:
        _write_jsonl(patent_questions_path, item)
    for item in application_questions:
        _write_jsonl(application_questions_path, item)

    print(f"Output directory: {output_dir}", flush=True)
    print(f"Patent questions: {len(patent_questions)} / Application questions: {len(application_questions)}", flush=True)
    print(f"Execution mode: {args.execution_mode} / BERTScore enabled: {args.enable_bert_score}", flush=True)

    patent_records = _run_batch(
        items=patent_questions,
        output_path=output_dir / "patent_chat_results.jsonl",
        top_k=args.patent_top_k,
        patent_runner=args.patent_runner,
        progress_every=max(args.progress_every, 1),
    )
    application_records = _run_batch(
        items=application_questions,
        output_path=output_dir / "application_chat_results.jsonl",
        top_k=args.application_top_k,
        patent_runner=args.patent_runner,
        progress_every=max(args.progress_every, 1),
    )

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "execution_mode": args.execution_mode,
        "patent_runner": args.patent_runner,
        "bert_score_enabled": args.enable_bert_score,
        "output_dir": str(output_dir),
        "patents_used": [{"patent_id": item.get("patent_id"), "title": item.get("title")} for item in patents],
        "patent": _summarize(patent_records),
        "application": _summarize(application_records),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_summary_md(output_dir / "summary.md", summary, output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
