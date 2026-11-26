"""Pluggable embeddings with a deterministic offline fallback."""
from __future__ import annotations

import hashlib
import math
import re
from typing import List


def _fallback(text: str) -> List[float]:
    vec = [0.0] * 128
    for token in re.findall(r"\w+", str(text).lower()):
        h = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16)
        vec[h % 128] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


async def embed(texts: List[str], provider: str = "fallback") -> List[List[float]]:
    items = [str(t) for t in texts]
    if provider == "fallback" or not items:
        return [_fallback(t) for t in items]
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    spec = registry.get(provider)
    if spec is None or not spec.available():
        return [_fallback(t) for t in items]
    try:
        result = await ExternalService(spec).query("embed", {"input": items})
        return [d.get("embedding", _fallback(t))
                for d, t in zip(result.get("data", []), items)]
    except Exception:
        return [_fallback(t) for t in items]
