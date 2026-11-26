"""Compose multi-step internal pipelines from intent."""
from __future__ import annotations


STEPS = {
    "research": ["enrich", "serpapi", "rag", "generate"],
    "code": ["enrich", "coder", "validate"],
    "summarize": ["enrich", "rag", "summarize-ai"],
}


def compose(intent: str):
    return STEPS.get(intent, ["enrich", "generate"])
