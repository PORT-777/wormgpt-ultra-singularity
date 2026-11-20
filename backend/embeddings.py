"""Embedding helper (pluggable; falls back to hash-based pseudo-embeddings)."""
from __future__ import annotations

import hashlib
import math
from typing import List, Callable, Optional

_EMBED_FN: Optional[Callable[[str], List[float]]] = None
_DIM = 64


def set_embed_fn(fn: Callable[[str], List[float]]) -> None:
    global _EMBED_FN
    _EMBED_FN = fn


def embed(text: str) -> List[float]:
    if _EMBED_FN is not None:
        return _EMBED_FN(text)
    # Deterministic pseudo-embedding fallback
    h = hashlib.sha256(text.encode("utf-8", errors="replace")).digest()
    vec = [0.0] * _DIM
    for i in range(_DIM):
        vec[i] = (h[i % len(h)] / 255.0) * 2 - 1
    # normalize
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def semantic_search(query: str, docs: List[dict], text_key: str = "text",
                   k: int = 8) -> List[dict]:
    qv = embed(query)
    scored = []
    for d in docs:
        dv = embed(d.get(text_key, ""))
        scored.append((cosine(qv, dv), d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:k] if _ > 0] or [d for _, d in scored[:k]]
