"""OpenAI-compatible /v1/embeddings server for Qwen3-Embedding models.

Usage:
    python3 scripts/serve_embedding.py --model Qwen/Qwen3-Embedding-4B --port 8001
"""
from __future__ import annotations

import argparse
import time
import torch
from typing import Union

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModel


app = FastAPI(title="Embedding Server")
_model = None
_tokenizer = None
_model_name = ""
_device = "mps" if torch.backends.mps.is_available() else "cpu"


def _last_token_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
    if left_padding:
        return last_hidden_state[:, -1]
    sequence_lengths = attention_mask.sum(dim=1) - 1
    batch_size = last_hidden_state.shape[0]
    return last_hidden_state[torch.arange(batch_size, device=last_hidden_state.device), sequence_lengths]


def load_model(model_name: str) -> None:
    global _model, _tokenizer, _model_name
    print(f"[embedding] Loading {model_name} on {_device} ...")
    _tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    _model = AutoModel.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        trust_remote_code=True,
    ).to(_device).eval()
    _model_name = model_name
    print(f"[embedding] Ready on {_device}")


class EmbeddingRequest(BaseModel):
    input: Union[str, list[str]]
    model: str = ""
    encoding_format: str = "float"
    dimensions: int | None = None


@app.get("/health")
def health():
    return {"status": "ok", "model": _model_name, "device": _device}


@app.post("/v1/embeddings")
def embeddings(req: EmbeddingRequest):
    if _model is None:
        raise HTTPException(500, "Model not loaded")

    texts = [req.input] if isinstance(req.input, str) else req.input
    batch_dict = _tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=8192,
        return_tensors="pt",
    ).to(_device)

    with torch.no_grad():
        outputs = _model(**batch_dict)
    embeddings_tensor = _last_token_pool(outputs.last_hidden_state, batch_dict["attention_mask"])
    # L2 normalize
    norms = embeddings_tensor.norm(dim=-1, keepdim=True).clamp(min=1e-8)
    embeddings_tensor = embeddings_tensor / norms
    vectors = embeddings_tensor.float().cpu().tolist()

    data = [
        {"object": "embedding", "index": i, "embedding": vec}
        for i, vec in enumerate(vectors)
    ]
    return JSONResponse({
        "object": "list",
        "data": data,
        "model": _model_name,
        "usage": {"prompt_tokens": sum(len(t.split()) for t in texts), "total_tokens": sum(len(t.split()) for t in texts)},
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-Embedding-4B")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    load_model(args.model)
    uvicorn.run(app, host=args.host, port=args.port)
