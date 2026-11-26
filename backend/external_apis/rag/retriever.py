"""Hybrid retriever: vector similarity + keyword overlap."""
from __future__ import annotations

import re
from .vector_store import store


def retrieve(query, vector, top_k=5):
    candidates = store.search(vector, top_k * 2)
    terms = set(re.findall(r"\w+", str(query).lower()))
    for c in candidates:
        words = set(re.findall(r"\w+", c["text"].lower()))
        overlap = len(terms & words) / (len(terms) or 1)
        c["score"] = 0.7 * c["score"] + 0.3 * overlap
    candidates.sort(key=lambda c: -c["score"])
    return candidates[:top_k]
