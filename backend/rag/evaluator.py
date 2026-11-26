"""RAGAS-style evaluation of RAG responses."""
from __future__ import annotations

import re
from typing import List

from .models import RAGResponse, RAGEvalMetrics


def _claims(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text or "")) if s.strip()]


def evaluate(question: str, response: RAGResponse,
             context: List[str] | None = None,
             ground_truth: str | None = None) -> RAGEvalMetrics:
    ctx = context or [s.excerpt for s in response.sources]
    claims = _claims(response.answer)
    words = set(" ".join(ctx).lower().split())
    supported = sum(1 for c in claims if any(
        w in words for w in re.findall(r"\w+", c.lower()) if len(w) > 3))
    faith = supported / (len(claims) or 1)
    q = set(re.findall(r"\w+", question.lower()))
    a = set(re.findall(r"\w+", response.answer.lower()))
    relevance = len(q & a) / (len(q) or 1)
    precision = min(1.0, sum(1 for s in response.sources if s.excerpt) / (len(response.sources) or 1))
    recall = 0.0
    if ground_truth:
        gt = set(re.findall(r"\w+", ground_truth.lower()))
        recall = len(gt & set(" ".join(ctx).lower().split())) / (len(gt) or 1)
    return RAGEvalMetrics(faithfulness=round(min(1.0, faith), 3),
                          answer_relevance=round(min(1.0, relevance), 3),
                          context_precision=round(precision, 3),
                          context_recall=round(min(1.0, recall), 3),
                          hallucination_score=round(1 - min(1.0, faith), 3))
