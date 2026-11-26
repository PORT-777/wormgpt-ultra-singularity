"""Phase A — RAG pipeline tests (offline)."""
from __future__ import annotations

import asyncio

import pytest

from rag import chunker, document_loader, embedder, evaluator, generator, retriever
from rag.models import Chunk, Document, RAGResponse, RankedChunk, Source
from rag.pipeline import RAGPipeline
from rag.vector_store import VectorStore, VectorStoreBackend, detect_backend


def test_document_model_id():
    d = Document("hello", {"source_type": "txt"})
    assert d.doc_id and len(d.doc_id) == 16


def test_clean_text():
    assert document_loader.clean_text("a  b\n\n\n\nc") == "a b\n\nc"


def test_load_text(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello world", encoding="utf-8")
    d = document_loader.load(str(p))
    assert d.text == "hello world"
    assert d.metadata["word_count"] == 2


def test_load_json_flattens(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": {"b": 1}}', encoding="utf-8")
    d = document_loader.load_json(str(p))
    assert "a.b: 1" in d.text


def test_load_csv(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("x,y\n1,2\n", encoding="utf-8")
    d = document_loader.load_csv(str(p))
    assert d.metadata["row_count"] == 1 and "x, y" in d.text


def test_chunk_strategies():
    text = "# Title\npara one. para two. " * 20
    for s in chunker.ChunkStrategy:
        cs = chunker.chunk(text, size=120, overlap=20, strategy=s, doc_id="d")
        assert cs


def test_chunk_links_and_ids():
    cs = chunker.chunk("word " * 300, size=80, overlap=10, doc_id="d")
    assert cs[0].prev_chunk_id is None
    assert cs[0].next_chunk_id == cs[1].chunk_id
    assert len({c.chunk_id for c in cs}) == len(cs)


def test_auto_strategy_markdown():
    d = Document("# Heading\ntext", {"source_type": "markdown"})
    assert chunker.auto_strategy(d) == chunker.ChunkStrategy.MARKDOWN


def test_auto_strategy_code():
    d = Document("def f():\n    pass", {"source_type": "py"})
    assert chunker.auto_strategy(d) == chunker.ChunkStrategy.CODE


def test_embed_fallback_deterministic():
    a = asyncio.run(embedder.embed(["hello"]))
    b = asyncio.run(embedder.embed(["hello"]))
    assert a == b and len(a[0]) == 128


def test_vector_store_upsert_search():
    vs = VectorStore(VectorStoreBackend.MEMORY)
    chunks = [Chunk("alpha beta", embedding=[1, 0], parent_doc_id="d1", chunk_index=0),
              Chunk("gamma", embedding=[0, 1], parent_doc_id="d2", chunk_index=0)]
    vs.upsert(chunks)
    assert vs.search([1, 0], top_k=1)[0].chunk.text == "alpha beta"


def test_vector_store_delete():
    vs = VectorStore(VectorStoreBackend.MEMORY)
    vs.upsert([Chunk("x", parent_doc_id="d", chunk_index=0)])
    assert vs.delete("d") == 1 and vs.stats()["chunks"] == 0


def test_vector_store_save_load(tmp_path):
    vs = VectorStore(VectorStoreBackend.MEMORY)
    vs.upsert([Chunk("x", parent_doc_id="d", chunk_index=0)])
    p = tmp_path / "vs.json"
    vs.save(str(p))
    other = VectorStore(VectorStoreBackend.MEMORY)
    other.load(str(p))
    assert len(other.list_documents()) == 1


def test_detect_backend_default():
    assert isinstance(detect_backend(), VectorStoreBackend)


def test_bm25_scores():
    cs = [Chunk("the quick brown fox", parent_doc_id="d", chunk_index=0)]
    scores = retriever.bm25("quick fox", cs)
    assert scores[0][0] > 0


def test_rrf_fusion():
    c1 = Chunk("a", parent_doc_id="d", chunk_index=0)
    c2 = Chunk("b", parent_doc_id="e", chunk_index=0)
    dense = [RankedChunk(c1, 1.0), RankedChunk(c2, 0.5)]
    sparse = [(1.0, c2), (0.5, c1)]
    fused = retriever.reciprocal_rank_fusion(dense, sparse)
    assert fused[0].rrf_score > 0


def test_mmr_diversity():
    a = Chunk("a", embedding=[1, 0], parent_doc_id="d", chunk_index=0)
    b = Chunk("b", embedding=[0.99, 0.01], parent_doc_id="e", chunk_index=0)
    c = Chunk("c", embedding=[0, 1], parent_doc_id="f", chunk_index=0)
    out = retriever.mmr([RankedChunk(a, 0.9), RankedChunk(b, 0.8),
                         RankedChunk(c, 0.7)], [1, 0], top_k=2)
    assert len(out) == 2


def test_generator_prompt_has_citations():
    c = Chunk("The value is 42", parent_doc_id="d", chunk_index=0)
    p = generator.build_prompt("What is the value?", [RankedChunk(c, 1.0)])
    assert "[1]" in p and "42" in p


def test_evaluator_metrics_shape():
    r = RAGResponse(answer="The value is 42. It is final.",
                    sources=[Source(id="1", excerpt="value 42")])
    m = evaluator.evaluate("What is the value?", r)
    assert 0 <= m.faithfulness <= 1
    assert 0 <= m.hallucination_score <= 1


def test_pipeline_ingest_and_query(tmp_path):
    p = tmp_path / "doc.txt"
    p.write_text("The secret number is 42. " * 20, encoding="utf-8")
    pipe = RAGPipeline(VectorStore(VectorStoreBackend.MEMORY))
    n = asyncio.run(pipe.ingest(str(p)))
    assert n > 0
    r = asyncio.run(pipe.query("secret number"))
    assert isinstance(r, RAGResponse)


def test_pipeline_delete_and_stats(tmp_path):
    p = tmp_path / "doc.txt"
    p.write_text("hello", encoding="utf-8")
    pipe = RAGPipeline(VectorStore(VectorStoreBackend.MEMORY))
    pipe.ingest(str(p)) if False else asyncio.run(pipe.ingest(str(p)))
    assert pipe.stats()["documents"] >= 1
    doc_id = pipe.documents()[0]["doc_id"]
    assert pipe.delete(doc_id) >= 1
