"""End-to-end RAG: ingest -> chunk -> embed -> store -> retrieve -> generate."""
from __future__ import annotations

from typing import Any

from . import chunker, document_loader, embedder, generator, reranker, retriever, vector_store


async def ingest(path, provider="fallback"):
    text = document_loader.load(path)
    chunks = chunker.chunk(text)
    vectors = await embedder.embed(chunks, provider)
    return vector_store.store.add(chunks, vectors, [{"source": str(path)}] * len(chunks))


async def query(question, top_k=5, provider="fallback"):
    vec = (await embedder.embed([question], provider))[0]
    hits = retriever.retrieve(question, vec, top_k)
    hits = reranker.rerank(question, hits, top_k)
    return {"prompt": generator.build_prompt(question, hits), "sources": hits}
