"""Document type classification with LLM fallback and caching."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any


class DocumentType(str, Enum):
    RESEARCH_PAPER = "research_paper"
    LEGAL_CONTRACT = "legal_contract"
    FINANCIAL_REPORT = "financial_report"
    TECHNICAL_DOCS = "technical_docs"
    NEWS_ARTICLE = "news_article"
    TUTORIAL = "tutorial"
    FAQ = "faq"
    MEETING_NOTES = "meeting_notes"
    RESUME = "resume"
    OTHER = "other"


RULES = {
    DocumentType.RESEARCH_PAPER: ("abstract", "methodology", "references"),
    DocumentType.LEGAL_CONTRACT: ("agreement", "hereby", "clause"),
    DocumentType.FINANCIAL_REPORT: ("revenue", "profit", "fiscal"),
    DocumentType.TECHNICAL_DOCS: ("install", "configuration", "api"),
    DocumentType.NEWS_ARTICLE: ("reported", "according to", "yesterday"),
    DocumentType.TUTORIAL: ("step 1", "in this guide", "example"),
    DocumentType.FAQ: ("q:", "a:", "frequently asked"),
    DocumentType.MEETING_NOTES: ("attendees", "action items", "minutes"),
    DocumentType.RESUME: ("experience", "education", "skills"),
}

_CACHE: dict[str, DocumentType] = {}


def classify(text: str, doc_id: str = "") -> DocumentType:
    if doc_id and doc_id in _CACHE:
        return _CACHE[doc_id]
    t = str(text or "")[:2000].lower()
    found = DocumentType.OTHER
    for dtype, keys in RULES.items():
        if all(k in t for k in keys):
            found = dtype
            break
    if doc_id:
        _CACHE[doc_id] = found
    return found


async def classify_llm(text: str) -> DocumentType:
    from llm import ask
    try:
        content = await ask(
            f"Classify as one of {[e.value for e in DocumentType]}: {text[:500]}",
            system="Reply with only one of the listed document types.")
        for dtype in DocumentType:
            if dtype.value in content.lower():
                return dtype
    except Exception:
        pass
    return classify(text)
