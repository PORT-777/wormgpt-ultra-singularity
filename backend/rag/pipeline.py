"""End-to-end RAG pipeline."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from . import chunker, document_loader, embedder, evaluator, generator, reranker, retriever
from .models import Chunk, Document, RAGResponse, RAGEvalMetrics
from .vector_store import VectorStore, store


class RAGPipeline:
    def __init__(self, vector_store: VectorStore | None = None):
        self.store = vector_store or store

    async def ingest(self, source: str, *, strategy=None,
                     size: int = 512, overlap: int = 64,
                     metadata: Dict[str, Any] | None = None) -> int:
        from .ingestion_pipeline import ingest as load_any
        docs = await load_any(source, metadata)
        total = 0
        for doc in docs:
            strategy = strategy or chunker.auto_strategy(doc)
            chunks = chunker.chunk(doc.text, size=size, overlap=overlap,
                                   strategy=strategy, doc_id=doc.doc_id,
                                   metadata=doc.metadata)
            vectors = await embedder.embed([c.text for c in chunks])
            for c, v in zip(chunks, vectors):
                c.embedding = v
            total += self.store.upsert(chunks)
        return total

    async def query(self, question: str, top_k: int = 5,
                    expand: bool = True, diverse: bool = True) -> RAGResponse:
        start = time.perf_counter()
        vec = (await embedder.embed([question]))[0]
        hits = retriever.retrieve(question, vec, top_k, expand, diverse)
        ranked = await reranker.rerank(question, [h.chunk for h in hits], top_k)
        response = await generator.generate(question, ranked)
        response.retrieval_time_ms = int((time.perf_counter() - start) * 1000)
        return response

    async def search(self, question: str, top_k: int = 5):
        vec = (await embedder.embed([question]))[0]
        return retriever.retrieve(question, vec, top_k)

    async def evaluate(self, question: str, response: RAGResponse,
                       ground_truth: str | None = None) -> RAGEvalMetrics:
        return evaluator.evaluate(question, response, ground_truth=ground_truth)

    def stats(self):
        return self.store.stats()

    def documents(self):
        return self.store.list_documents()

    def delete(self, doc_id: str) -> int:
        return self.store.delete(doc_id)


pipeline = RAGPipeline()
