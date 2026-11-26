"""Keyword-based document type classifier."""
from __future__ import annotations


RULES = {
    "invoice": ("invoice", "total", "vat"),
    "resume": ("resume", "cv", "experience"),
    "report": ("report", "findings", "summary"),
}


def classify(text: str) -> str:
    t = str(text or "").lower()
    for name, keys in RULES.items():
        if all(k in t for k in keys):
            return name
    return "general"
