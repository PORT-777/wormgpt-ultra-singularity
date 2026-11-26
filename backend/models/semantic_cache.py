"""Semantic answer cache using rag embeddings."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from external_apis.cache import cache as ttl_cache
from rag.embedder import embed
from rag.vector_store import VectorStore, store


@dataclass
class CachedResponse:
    response: str
    similarity: float
    saved_cost_estimate: float = 0.0


class SemanticCache:
    def __init__(self, vector_store: VectorStore | None = None,
                 threshold: float = 0.95, ttl_hours: int = 24):
        self.store = vector_store or store
        self.threshold = threshold
        self.ttl = ttl_hours * 3600

    async def get(self, query: str) -> CachedResponse | None:
        vec = (await embed([query]))[0]
        hits = self.store.search(vec, top_k=1)
        if not hits or hits[0].score <= self.threshold:
            return None
        meta = hits[0].chunk.metadata
        if time.time() > float(meta.get("expires", 0)):
            self.store.delete(hits[0].chunk.parent_doc_id)
            return None
        return CachedResponse(str(meta.get("response", "")), hits[0].score,
                              float(meta.get("cost", 0.0)))

    async def set(self, query: str, response: str, cost: float = 0.0) -> None:
        from rag.models import Chunk
        vec = (await embed([query]))[0]
        did = f"semantic:{abs(hash(query)):x}"
        chunk = Chunk(query, parent_doc_id=did, chunk_index=0,
                      metadata={"response": response, "cost": cost,
                                "expires": time.time() + self.ttl})
        chunk.embedding = vec
        self.store.upsert([chunk])
        ttl_cache.set(f"semantic:{query[:100]}", response)


semantic_cache = SemanticCache()
