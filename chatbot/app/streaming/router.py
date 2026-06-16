"""Public SSE streaming endpoints for chatbot answers."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..schemas import PreEvalChatRequest, ReEvalChatRequest
from .service import stream_pre_eval_chat_events, stream_re_eval_chat_events
from .sse import STREAMING_HEADERS


router = APIRouter(tags=["streaming"])


@router.post(
    "/api/v1/patents/{patent_id}/chat/stream",
    summary="[Streaming] 재평가 챗봇 답변",
    description=(
        "재평가 특허 챗봇 답변을 Server-Sent Events(text/event-stream)로 반환합니다. "
        "이벤트 순서는 metadata → source_cards → delta* → done 또는 error 입니다."
    ),
    responses={200: {"content": {"text/event-stream": {}}}},
)
def stream_re_eval_chat(patent_id: str, request: ReEvalChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_re_eval_chat_events(
            patent_id=patent_id,
            question=request.question,
            user_id=request.user_id,
            chat_history=[item.model_dump(exclude_none=True) for item in request.chat_history],
            top_k=5,
        ),
        media_type="text/event-stream",
        headers=STREAMING_HEADERS,
    )


@router.post(
    "/api/v1/pre-eval/cases/{case_id}/chat/stream",
    summary="[Streaming] 사전평가 챗봇 답변",
    description=(
        "사전평가 보고서 기반 챗봇 답변을 Server-Sent Events(text/event-stream)로 반환합니다. "
        "이벤트 순서는 metadata → source_cards → delta* → done 또는 error 입니다."
    ),
    responses={200: {"content": {"text/event-stream": {}}}},
)
def stream_pre_eval_chat(case_id: str, request: PreEvalChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_pre_eval_chat_events(
            case_id=case_id,
            question=request.question,
            user_id=request.user_id,
            chat_history=[item.model_dump(exclude_none=True) for item in request.chat_history],
            top_k=request.top_k,
        ),
        media_type="text/event-stream",
        headers=STREAMING_HEADERS,
    )

