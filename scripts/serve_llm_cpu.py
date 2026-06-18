"""CPU-based OpenAI-compatible LLM chat server using transformers.

Downloads the model from HuggingFace on first run.
Works on any CPU; uses MPS on Apple Silicon if available.

Usage:
    python3 scripts/serve_llm_cpu.py \
        --model Qwen/Qwen2.5-0.5B-Instruct \
        --port 8000
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from collections.abc import Iterator
from typing import Any

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread

app = FastAPI(title="LLM CPU Server")
_model = None
_tokenizer = None
_model_name = ""
_device = "mps" if torch.backends.mps.is_available() else "cpu"


def load_model(model_name: str) -> None:
    global _model, _tokenizer, _model_name
    print(f"[llm-cpu] Loading {model_name} on {_device} ...")
    _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    _model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if _device != "cpu" else torch.float32,
        trust_remote_code=True,
        device_map=_device,
    ).eval()
    _model_name = model_name
    print(f"[llm-cpu] Ready on {_device}")


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = ""
    messages: list[Message]
    max_tokens: int | None = 512
    temperature: float | None = 0.7
    response_format: dict | None = None
    stream: bool = False


def _make_response(text: str, model: str) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@app.get("/health")
def health():
    return {"status": "ok", "model": _model_name, "device": _device}


@app.get("/v1/models")
def models():
    return {
        "object": "list",
        "data": [{"id": _model_name, "object": "model", "created": 0, "owned_by": "local"}],
    }


def _build_inputs(req: ChatRequest):
    want_json = (req.response_format or {}).get("type") == "json_object"
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    if want_json and not any("JSON" in m["content"] or "json" in m["content"] for m in messages):
        messages.insert(0, {"role": "system", "content": "You must respond with valid JSON only."})
    text_input = _tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return _tokenizer(text_input, return_tensors="pt").to(_device)


def _sse_chunk(delta: str, model: str, finish: bool = False) -> str:
    chunk = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {"content": delta} if not finish else {}, "finish_reason": "stop" if finish else None}],
    }
    return f"data: {json.dumps(chunk)}\n\n"


def _stream_response(req: ChatRequest) -> Iterator[str]:
    inputs = _build_inputs(req)
    streamer = TextIteratorStreamer(_tokenizer, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs = {
        **inputs,
        "max_new_tokens": req.max_tokens or 512,
        "temperature": req.temperature or 0.7,
        "do_sample": (req.temperature or 0.7) > 0,
        "pad_token_id": _tokenizer.eos_token_id,
        "streamer": streamer,
    }
    thread = Thread(target=_model.generate, kwargs=gen_kwargs)
    thread.start()
    for token in streamer:
        if token:
            yield _sse_chunk(token, _model_name)
    yield _sse_chunk("", _model_name, finish=True)
    yield "data: [DONE]\n\n"
    thread.join()


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest):
    if _model is None:
        raise HTTPException(500, "Model not loaded")

    if req.stream:
        return StreamingResponse(_stream_response(req), media_type="text/event-stream")

    inputs = _build_inputs(req)
    with torch.no_grad():
        output_ids = _model.generate(
            **inputs,
            max_new_tokens=req.max_tokens or 512,
            temperature=req.temperature or 0.7,
            do_sample=(req.temperature or 0.7) > 0,
            pad_token_id=_tokenizer.eos_token_id,
        )
    new_ids = output_ids[0][inputs["input_ids"].shape[1]:]
    generated = _tokenizer.decode(new_ids, skip_special_tokens=True).strip()
    return JSONResponse(_make_response(generated, _model_name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    load_model(args.model)
    uvicorn.run(app, host=args.host, port=args.port)
