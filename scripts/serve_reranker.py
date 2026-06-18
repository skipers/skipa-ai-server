"""OpenAI-style /v1/rerank server for Qwen3-Reranker models.

Usage:
    python3 scripts/serve_reranker.py --model Qwen/Qwen3-Reranker-4B --port 8003
"""
from __future__ import annotations

import argparse
import torch

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM


app = FastAPI(title="Reranker Server")
_model = None
_tokenizer = None
_model_name = ""
_yes_id: int = -1
_no_id: int = -1
# cpu avoids MPS index-out-of-bounds on vocab logits; MPS used for embedding layers
_device = "cpu"

_PREFIX = "<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n<|im_start|>user\n"
_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"


def load_model(model_name: str) -> None:
    global _model, _tokenizer, _model_name, _yes_id, _no_id
    print(f"[reranker] Loading {model_name} on {_device} ...")
    _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True, padding_side="left")
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token
    _model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float32,
        trust_remote_code=True,
    ).to(_device).eval()
    _yes_id = _tokenizer.convert_tokens_to_ids("yes")
    _no_id = _tokenizer.convert_tokens_to_ids("no")
    _model_name = model_name
    print(f"[reranker] Ready on {_device} | yes_id={_yes_id} no_id={_no_id}")


def _format_input(query: str, document: str, instruction: str = "") -> str:
    instr = instruction or "Given a web search query, retrieve relevant passages that answer the query"
    return (
        f"{_PREFIX}"
        f"<Instruct>: {instr}\n"
        f"<Query>: {query}\n"
        f"<Document>: {document}"
        f"{_SUFFIX}"
    )


class RerankRequest(BaseModel):
    query: str
    documents: list[str]
    model: str = ""
    instruction: str = ""
    top_n: int | None = None


@app.get("/health")
def health():
    return {"status": "ok", "model": _model_name, "device": _device}


@app.post("/v1/rerank")
def rerank(req: RerankRequest):
    if _model is None:
        raise HTTPException(500, "Model not loaded")

    inputs_text = [_format_input(req.query, doc, req.instruction) for doc in req.documents]
    inputs = _tokenizer(
        inputs_text,
        padding=True,
        truncation=True,
        max_length=8192,
        return_tensors="pt",
        add_special_tokens=False,
    ).to(_device)

    with torch.no_grad():
        outputs = _model(**inputs)
    # last-token logits over full vocab, then pick yes/no
    last_logits = outputs.logits[:, -1, :]  # (batch, vocab)
    pair_logits = last_logits[:, [_no_id, _yes_id]]
    scores = torch.softmax(pair_logits, dim=-1)[:, 1].cpu().tolist()

    results = [
        {"index": i, "document": doc, "relevance_score": float(scores[i])}
        for i, doc in enumerate(req.documents)
    ]
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    if req.top_n:
        results = results[: req.top_n]

    return JSONResponse({"model": _model_name, "results": results})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-Reranker-4B")
    parser.add_argument("--port", type=int, default=8003)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    load_model(args.model)
    uvicorn.run(app, host=args.host, port=args.port)
