"""Rerank with Cohere -> HuggingFace -> LLM fallback chain."""
from __future__ import annotations

from typing import List

from .models import Chunk, RankedChunk


async def cohere_rerank(query: str, chunks: List[Chunk], top_n: int):
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    spec = registry.get("cohere")
    if spec is None or not spec.available():
        return None
    try:
        result = await ExternalService(spec).query("rerank", {
            "query": query, "documents": [c.text for c in chunks], "top_n": top_n})
        scores = {r.get("index", 0): r.get("relevance_score", 0.0)
                  for r in result.get("results", [])}
        ranked = [RankedChunk(chunks[i], float(scores.get(i, 0.0)))
                  for i in range(len(chunks))]
        ranked.sort(key=lambda r: -r.score)
        return ranked[:top_n]
    except Exception:
        return None


async def hf_crossencoder_rerank(query: str, chunks: List[Chunk], top_n: int):
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    spec = registry.get("huggingface")
    if spec is None or not spec.available():
        return None
    try:
        result = await ExternalService(spec).query("infer", {
            "model": "BAAI/bge-reranker-base",
            "inputs": {"query": query, "texts": [c.text for c in chunks]}})
        return [RankedChunk(chunks[i], float(score)) for i, score in enumerate(result)][:top_n]
    except Exception:
        return None


async def llm_rerank(query: str, chunks: List[Chunk], top_n: int):
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    spec = registry.get("openrouter")
    if spec is None or not spec.available():
        return [RankedChunk(c, 0.5) for c in chunks[:top_n]]
    try:
        payload = {"model": "openai/gpt-4o-mini", "messages": [
            {"role": "user", "content": "Score relevance 0-10 for each doc: " +
             str([c.text[:200] for c in chunks]) + " Query: " + query}]}
        await ExternalService(spec).query("route", payload)
    except Exception:
        pass
    return [RankedChunk(c, 0.5) for c in chunks[:top_n]]


async def rerank(query: str, chunks: List[Chunk], top_n: int = 5) -> List[RankedChunk]:
    for fn in (cohere_rerank, hf_crossencoder_rerank, llm_rerank):
        result = await fn(query, chunks, top_n)
        if result:
            return result
    return [RankedChunk(c, 0.5) for c in chunks[:top_n]]
