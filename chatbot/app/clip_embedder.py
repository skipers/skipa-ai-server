"""CLIP/SigLIP image embedding for patent visual assets.

Provides image → vector and text → vector functions using CLIP ViT-B/32.
The model is loaded lazily and cached as a module-level singleton (thread-safe).
Falls back to None vectors gracefully if open_clip_torch is not installed.

Collection layout:
  skipa_patent_visuals (named vectors)
    text  : OpenAI text-embedding-3-large, dim=3072  (caption/context)
    image : CLIP ViT-B/32,                dim=512   (visual content)
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

# CLIP ViT-B/32 image/text embedding dimension
IMAGE_VECTOR_SIZE = 512

# Model name – override via CLIP_MODEL env var
_MODEL_NAME: str = os.getenv("CLIP_MODEL", "ViT-B-32")
_PRETRAINED: str = os.getenv("CLIP_PRETRAINED", "openai")

_lock = threading.Lock()
_model: Any = None
_preprocess: Any = None
_tokenize: Any = None
_device: str = "cpu"
_provider: str = "unloaded"


def _load() -> None:
    """Load the CLIP model into module-level singletons (called once)."""
    global _model, _preprocess, _tokenize, _device, _provider
    with _lock:
        if _provider != "unloaded":
            return  # already attempted
        try:
            import open_clip
            import torch

            # Apple Silicon MPS → GPU 가속
            if torch.backends.mps.is_available():
                _device = "mps"
            elif torch.cuda.is_available():
                _device = "cuda"
            else:
                _device = "cpu"

            _model, _, _preprocess = open_clip.create_model_and_transforms(
                _MODEL_NAME, pretrained=_PRETRAINED
            )
            _model = _model.to(_device).eval()
            _tokenize = open_clip.get_tokenizer(_MODEL_NAME)
            _provider = f"open_clip:{_MODEL_NAME}:{_PRETRAINED}:{_device}"
        except Exception as exc:
            _provider = f"unavailable:{exc}"


def is_available() -> bool:
    _load()
    return "unavailable" not in _provider and "unloaded" not in _provider


def provider_name() -> str:
    _load()
    return _provider


def embed_image(image_path: str | Path) -> list[float] | None:
    """Return a 512-dim CLIP image embedding. Returns None on any failure."""
    _load()
    if not is_available():
        return None
    try:
        import torch
        from PIL import Image

        img = Image.open(str(image_path)).convert("RGB")
        tensor = _preprocess(img).unsqueeze(0).to(_device)  # type: ignore[arg-type]
        with torch.no_grad():
            feat = _model.encode_image(tensor)  # type: ignore[union-attr]
            feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat[0].cpu().tolist()
    except Exception:
        return None


def embed_text(text: str) -> list[float] | None:
    """Return a 512-dim CLIP text embedding (for cross-modal image search).

    This lets you query the image vector space using natural language.
    """
    _load()
    if not is_available():
        return None
    try:
        import torch

        tokens = _tokenize([text]).to(_device)  # type: ignore[operator]
        with torch.no_grad():
            feat = _model.encode_text(tokens)  # type: ignore[union-attr]
            feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat[0].cpu().tolist()
    except Exception:
        return None


def embed_images_batch(image_paths: list[str | Path], batch_size: int = 16) -> list[list[float] | None]:
    """Batch-embed multiple images. Returns None for failed items."""
    _load()
    if not is_available():
        return [None] * len(image_paths)

    results: list[list[float] | None] = []
    try:
        import torch
        from PIL import Image

        for start in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[start : start + batch_size]
            tensors = []
            valid_idx: list[int] = []
            for i, p in enumerate(batch_paths):
                try:
                    img = Image.open(str(p)).convert("RGB")
                    tensors.append(_preprocess(img))  # type: ignore[arg-type]
                    valid_idx.append(i)
                except Exception:
                    pass

            if not tensors:
                results.extend([None] * len(batch_paths))
                continue

            batch_tensor = torch.stack(tensors).to(_device)
            with torch.no_grad():
                feats = _model.encode_image(batch_tensor)  # type: ignore[union-attr]
                feats = feats / feats.norm(dim=-1, keepdim=True)

            vecs = feats.cpu().tolist()
            batch_results: list[list[float] | None] = [None] * len(batch_paths)
            for j, idx in enumerate(valid_idx):
                batch_results[idx] = vecs[j]
            results.extend(batch_results)
    except Exception:
        results = [None] * len(image_paths)

    return results


def clip_status() -> dict[str, Any]:
    _load()
    return {
        "available": is_available(),
        "provider": _provider,
        "model": _MODEL_NAME,
        "pretrained": _PRETRAINED,
        "device": _device,
        "image_vector_size": IMAGE_VECTOR_SIZE,
    }
