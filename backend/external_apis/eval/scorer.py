"""Heuristic response scoring (faithfulness/relevance/coherence)."""
from __future__ import annotations

import re


def score(answer: str, question: str, sources: list[str] | None = None):
    a = set(re.findall(r"\w+", str(answer or "").lower()))
    q = set(re.findall(r"\w+", str(question or "").lower()))
    relevance = len(a & q) / (len(q) or 1)
    src = set(" ".join(sources or []).lower().split())
    faith = len(a & src) / (len(a) or 1) if sources else 0.5
    words = len(a)
    coherence = min(1.0, words / 120.0)
    return {"faithfulness": round(faith, 3), "relevance": round(min(1.0, relevance), 3),
            "coherence": round(coherence, 3)}
