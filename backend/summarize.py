"""Summarization helpers (extractive)."""
from __future__ import annotations

import re
from typing import List


def extractive(text: str, n_sentences: int = 3) -> str:
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sents) <= n_sentences:
        return text
    # score by length + position
    scored = []
    for i, s in enumerate(sents):
        score = len(s) + (10 if i < 3 else 0)
        scored.append((score, i, s))
    scored.sort(reverse=True)
    chosen = sorted(scored[:n_sentences], key=lambda x: x[1])
    return " ".join(s[2] for s in chosen)


def bullet_points(text: str, n: int = 5) -> List[str]:
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sents[:n] if s.strip()]
