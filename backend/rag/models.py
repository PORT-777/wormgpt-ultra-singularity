"""Typed data models for the RAG pipeline."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _uid(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


@dataclass
class Document:
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    doc_id: str = ""

    def __post_init__(self):
        self.doc_id = self.doc_id or _uid(f"doc:{self.text[:200]}")


@dataclass
class Chunk:
    text: str
    chunk_id: str = ""
    parent_doc_id: str = ""
    chunk_index: int = 0
    prev_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
    section_title: str = ""
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)

    def __post_init__(self):
        self.chunk_id = self.chunk_id or _uid(f"{self.parent_doc_id}:{self.chunk_index}:{self.text}")


@dataclass
class RankedChunk:
    chunk: Chunk
    score: float
    dense_score: float = 0.0
    sparse_score: float = 0.0
    rrf_score: float = 0.0


@dataclass
class Source:
    id: str
    title: str = ""
    url: str = ""
    page: Optional[int] = None
    excerpt: str = ""


@dataclass
class RAGResponse:
    answer: str
    sources: List[Source] = field(default_factory=list)
    confidence: float = 0.0
    tokens_used: int = 0
    model_used: str = ""
    retrieval_time_ms: int = 0
    generation_time_ms: int = 0


@dataclass
class RAGEvalMetrics:
    faithfulness: float = 0.0
    answer_relevance: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    hallucination_score: float = 0.0


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
