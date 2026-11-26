"""Optional Cohere rerank with lexical fallback."""
from __future__ import annotations


def rerank(query, results, top_k=5):
    return sorted(results, key=lambda c: -float(c.get("score", 0)))[:top_k]
