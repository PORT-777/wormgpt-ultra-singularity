"""Vector-store abstraction with dense search and JSON persistence."""
from __future__ import annotations

import json, math
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

from .models import Chunk, RankedChunk


class VectorStoreBackend(str, Enum):
    CHROMA = "chroma"
    PGVECTOR = "pgvector"
    FAISS = "faiss"
    PINECONE = "pinecone"
    SUPABASE = "supabase"
    MEMORY = "memory"


def _cos(a, b):
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(x * y for x, y in zip(a[:n], b[:n]))
    na = math.sqrt(sum(x * x for x in a[:n])) or 1.0
    nb = math.sqrt(sum(y * y for y in b[:n])) or 1.0
    return dot / (na * nb)


def detect_backend() -> VectorStoreBackend:
    import os
    for name, env in ((VectorStoreBackend.PINECONE, "PINECONE_API_KEY"),
                      (VectorStoreBackend.SUPABASE, "SUPABASE_KEY"),
                      (VectorStoreBackend.CHROMA, "CHROMA_HOST")):
        if os.getenv(env):
            return name
    return VectorStoreBackend.MEMORY


class VectorStore:
    def __init__(self, backend: VectorStoreBackend | None = None):
        self.backend = backend or detect_backend()
        self._docs: Dict[str, List[Chunk]] = {}
        self._chunks: Dict[str, Chunk] = {}

    def upsert(self, chunks: List[Chunk]) -> int:
        for c in chunks:
            self._chunks[c.chunk_id] = c
            self._docs.setdefault(c.parent_doc_id, []).append(c)
        return len(chunks)

    def search(self, embedding: List[float], top_k: int = 5,
               filters: Dict[str, Any] | None = None) -> List[RankedChunk]:
        items = self._chunks.values()
        if filters:
            items = [c for c in items
                     if all(c.metadata.get(k) == v for k, v in filters.items())]
        scored = [RankedChunk(c, _cos(embedding, c.embedding),
                              dense_score=_cos(embedding, c.embedding))
                  for c in items]
        scored.sort(key=lambda r: -r.score)
        return scored[:top_k]

    def delete(self, doc_id: str) -> int:
        chunks = self._docs.pop(doc_id, [])
        for c in chunks:
            self._chunks.pop(c.chunk_id, None)
        return len(chunks)

    def list_documents(self) -> List[Dict[str, Any]]:
        return [{"doc_id": d, "chunks": len(c)} for d, c in self._docs.items()]

    def stats(self) -> Dict[str, Any]:
        return {"backend": self.backend.value, "chunks": len(self._chunks),
                "documents": len(self._docs)}

    def save(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({k: [c.__dict__ for c in v]
                                 for k, v in self._docs.items()}), encoding="utf-8")

    def load(self, path: str) -> None:
        p = Path(path)
        if not p.exists():
            return
        raw = json.loads(p.read_text(encoding="utf-8"))
        self._docs = {k: [Chunk(**c) for c in v] for k, v in raw.items()}
        self._chunks = {c.chunk_id: c for cs in self._docs.values() for c in cs}


store = VectorStore()
