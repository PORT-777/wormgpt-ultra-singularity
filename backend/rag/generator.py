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
    answer, model_used, tokens = "", "groq/openai/gpt-oss-120b", 0
    from llm import DEFAULT_MODEL, ask
    try:
        answer = await ask(prompt)
        tokens = len(answer.split())
        model_used = f"groq/{DEFAULT_MODEL}"
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
