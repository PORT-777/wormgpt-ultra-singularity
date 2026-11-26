"""Phase C — document intelligence tests (offline)."""
from __future__ import annotations

import asyncio

from documents.classifier import DocumentType, classify, classify_llm
from documents.parser import DocumentParser, ParsedDocument
from documents.table_extractor import Table, from_docx, from_html, from_pdf, from_xlsx


def test_table_markdown():
    t = Table(["a", "b"], [["1", "2"]])
    assert "| a | b |" in t.markdown and "| 1 | 2 |" in t.markdown


def test_table_csv():
    t = Table(["a", "b"], [["1", "2"]])
    assert "a,b" in t.csv and "1,2" in t.csv


def test_empty_table():
    assert Table().markdown == ""


def test_classifier_research():
    assert classify("Abstract methodology references") == DocumentType.RESEARCH_PAPER


def test_classifier_legal():
    assert classify("This agreement hereby states clause 1") == DocumentType.LEGAL_CONTRACT


def test_classifier_faq():
    assert classify("Q: what? A: this. frequently asked") == DocumentType.FAQ


def test_classifier_other():
    assert classify("random unrelated text") == DocumentType.OTHER


def test_classifier_cache():
    assert classify("hello", doc_id="d1") == classify("changed", doc_id="d1")


def test_classifier_llm_fallback():
    assert isinstance(asyncio.run(classify_llm("Abstract methodology references")), DocumentType)


def test_parse_text_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    d = asyncio.run(DocumentParser().parse(str(p), "text/plain"))
    assert d.text == "hello" and isinstance(d, ParsedDocument)


def test_parse_html():
    d = asyncio.run(DocumentParser().parse("<p>Hello <b>world</b></p>", "text/html"))
    assert "Hello" in d.text and "world" in d.text


def test_parse_bytes_text():
    d = asyncio.run(DocumentParser().parse(b"abc", "text/plain"))
    assert d.text == "abc"


def test_table_extractors_degrade():
    assert from_html("<table></table>") == []
    assert from_pdf(b"%PDF-1.4 broken") == []
    assert from_xlsx(b"broken") == []
    assert from_docx(b"broken") == []
