"""LLM-as-judge response quality scorer."""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class QualityScore:
    faithfulness: float
    relevance: float
    coherence: float
    completeness: float
    conciseness: float
    overall: float
    flags: list[str]


def _toks(text: str) -> set[str]:
    return set(re.findall(r"\w+", str(text or "").lower()))


async def score_response(question: str, response: str,
                         context: list[str] | None = None) -> QualityScore:
    q, a = _toks(question), _toks(response)
    relevance = len(q & a) / (len(q) or 1)
    coherence = min(1.0, len(a) / 120.0)
    words = str(response or "").split()
    completeness = min(1.0, len(words) / 80.0)
    conciseness = 1.0 if len(words) < 300 else max(0.0, 1 - (len(words) - 300) / 700)
    if context:
        ctx = _toks(" ".join(context))
        faith = len(a & ctx) / (len(a) or 1)
    else:
        faith = 0.5
    scores = [min(1.0, x) for x in (faith, relevance, coherence, completeness, conciseness)]
    flags = []
    if faith < 0.3:
        flags.append("hallucination_risk")
    if relevance < 0.2:
        flags.append("off_topic")
    if len(words) < 10:
        flags.append("too_short")
    return QualityScore(*[round(s, 3) for s in scores],
                        overall=round(sum(scores) / len(scores), 3), flags=flags)
