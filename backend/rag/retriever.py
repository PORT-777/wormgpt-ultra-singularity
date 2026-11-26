"""Hybrid retrieval: dense + BM25 with RRF fusion, MMR and context expansion."""
from __future__ import annotations

import math, re
from collections import Counter
from typing import Any, Dict, List

from .models import Chunk, RankedChunk
from .vector_store import store


def bm25(query: str, chunks: List[Chunk], k1: float = 1.5, b: float = 0.75):
    tokens = re.findall(r"\w+", query.lower())
    docs = [re.findall(r"\w+", c.text.lower()) for c in chunks]
    if not docs:
        return []
    avg = sum(len(d) for d in docs) / len(docs) or 1
    df = Counter(t for d in docs for t in set(d))
    N = len(docs)
    scores = []
    for i, d in enumerate(docs):
        tf = Counter(d)
        s = 0.0
        for t in tokens:
            if not t:
                continue
            idf = math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * (tf[t] * (k1 + 1)) / (tf[t] + k1 * (1 - b + b * len(d) / avg))
        scores.append((s, chunks[i]))
    return scores


def reciprocal_rank_fusion(dense: List[RankedChunk], sparse: List[tuple], k: int = 60):
    scores: Dict[str, float] = {}
    mapping: Dict[str, RankedChunk] = {}
    for rank, r in enumerate(dense, 1):
        scores[r.chunk.chunk_id] = scores.get(r.chunk.chunk_id, 0) + 1 / (k + rank)
        mapping[r.chunk.chunk_id] = r
    for rank, (_, c) in enumerate(sparse, 1):
        scores[c.chunk_id] = scores.get(c.chunk_id, 0) + 1 / (k + rank)
        mapping.setdefault(c.chunk_id, RankedChunk(c, 0.0))
    out = []
    for cid, score in scores.items():
        r = mapping[cid]
        r.rrf_score = score
        r.score = score
        out.append(r)
    out.sort(key=lambda r: -r.score)
    return out


def mmr(results: List[RankedChunk], query_vec: List[float], lambda_: float = 0.7,
        top_k: int = 5) -> List[RankedChunk]:
    if not results:
        return []
    selected = [results[0]]
    remaining = results[1:]
    while remaining and len(selected) < top_k:
        def redundancy(c):
            return max((_cos(c.chunk.embedding, s.chunk.embedding)
                        for s in selected), default=0)
        best = max(remaining, key=lambda r: lambda_ * r.score - (1 - lambda_) * redundancy(r))
        selected.append(best)
        remaining.remove(best)
    return selected[:top_k]


def _cos(a, b):
    n = min(len(a), len(b))
    if not n:
        return 0.0
    dot = sum(x * y for x, y in zip(a[:n], b[:n]))
    return dot / ((math.sqrt(sum(x*x for x in a[:n])) or 1) *
                  (math.sqrt(sum(y*y for y in b[:n])) or 1))


def retrieve(query: str, embedding: List[float], top_k: int = 5,
             expand: bool = True, diverse: bool = True) -> List[RankedChunk]:
    all_chunks = list(store._chunks.values())
    dense = store.search(embedding, top_k * 3)
    sparse = bm25(query, all_chunks)[:top_k * 3]
    fused = reciprocal_rank_fusion(dense, sparse)
    if diverse:
        fused = mmr(fused, embedding, top_k=top_k)
    result = fused[:top_k]
    if expand:
        for r in result:
            r.metadata = getattr(r, "metadata", {})
            prev_c = store._chunks.get(r.chunk.prev_chunk_id or "")
            next_c = store._chunks.get(r.chunk.next_chunk_id or "")
            r.chunk.metadata["context_expansion"] = [
                c.text for c in (prev_c, next_c) if c]
    return result
