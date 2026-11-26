"""Grounded answer generation with numbered citations."""
from __future__ import annotations

import time
from typing import List

from .models import RAGResponse, RankedChunk, Source

GENERATION_PROMPT = """You are a precise AI assistant. Answer the question using ONLY the provided context.
For every claim, cite the source using [1], [2], etc.
If the context does not contain the answer, say "I don't have enough information."

Context:
{context}

Question: {question}

Answer with citations:"""


def build_prompt(question: str, results: List[RankedChunk]) -> str:
    context = "\n\n".join(f"[{i+1}] {r.chunk.text}" for i, r in enumerate(results))
    return GENERATION_PROMPT.format(context=context, question=question)


async def generate(question: str, results: List[RankedChunk], model: str = "auto") -> RAGResponse:
    import time as _t
    start = _t.perf_counter()
    prompt = build_prompt(question, results)
    answer, model_used, tokens = "", model, 0
    from external_apis.base import ExternalService
    from external_apis.registry import registry
    spec = registry.get("openrouter")
    if spec is None or not spec.available():
        spec = registry.get("openai")
    if spec is not None and spec.available():
        try:
            result = await ExternalService(spec).query(
                "route" if spec.name == "openrouter" else "chat",
                {"model": "openai/gpt-4o-mini", "messages": [
                    {"role": "user", "content": prompt}]})
            answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            tokens = int(result.get("usage", {}).get("total_tokens", 0))
            model_used = result.get("model", model)
        except Exception as exc:
            answer = f"[generation unavailable: {type(exc).__name__}]"
    sources = [Source(id=r.chunk.chunk_id,
                      title=r.chunk.section_title or r.chunk.metadata.get("source_type", ""),
                      url=str(r.chunk.metadata.get("source_url", "")),
                      page=r.chunk.page_number, excerpt=r.chunk.text[:160])
               for r in results]
    confidence = sum(r.score for r in results) / (len(results) or 1)
    return RAGResponse(answer=answer or "I don't have enough information.",
                       sources=sources, confidence=round(min(1.0, confidence), 3),
                       tokens_used=tokens, model_used=model_used,
                       retrieval_time_ms=0,
                       generation_time_ms=int((_t.perf_counter() - start) * 1000))
