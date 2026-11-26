"""Multi-format parser with graceful optional-dependency degradation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParsedDocument:
    text: str
    mime_type: str
    pages: list[str] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentParser:
    async def parse(self, source: str | bytes, mime_type: str) -> ParsedDocument:
        if isinstance(source, bytes):
            return await self._parse_bytes(source, mime_type)
        if isinstance(source, str) and "<" in source and ">" in source and mime_type == "text/html":
            return await self._parse_html(source)
        p = Path(source)
        suffix = p.suffix.lower()
        mime_type = mime_type or {
            ".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".html": "text/html", ".png": "image/png", ".jpg": "image/jpeg",
        }.get(suffix, "text/plain")
        if mime_type == "application/pdf":
            return await self._parse_pdf(p.read_bytes())
        if "wordprocessingml" in mime_type or suffix == ".docx":
            return await self._parse_docx(p.read_bytes())
        if "excel" in mime_type or suffix in (".xlsx", ".xls"):
            return await self._parse_xlsx(p.read_bytes())
        if mime_type == "text/html":
            return await self._parse_html(p.read_text(encoding="utf-8", errors="replace"))
        if mime_type.startswith("image/"):
            return await self._parse_image_ocr(p.read_bytes())
        return ParsedDocument(p.read_text(encoding="utf-8", errors="replace"), mime_type)

    async def _parse_bytes(self, data: bytes, mime: str) -> ParsedDocument:
        if mime == "application/pdf":
            return await self._parse_pdf(data)
        if "wordprocessingml" in mime:
            return await self._parse_docx(data)
        if "excel" in mime:
            return await self._parse_xlsx(data)
        if mime.startswith("image/"):
            return await self._parse_image_ocr(data)
        return ParsedDocument(data.decode("utf-8", "replace"), mime)

    async def _parse_pdf(self, data: bytes) -> ParsedDocument:
        text, pages = "", []
        try:
            from pdfminer.high_level import extract_text
            import io
            text = extract_text(io.BytesIO(data)) or ""
            pages = [p for p in text.split("\f") if p.strip()]
        except Exception:
            pass
        if not text.strip():
            from rag.ocr import ocr_image
            text = ocr_image(str(data))
        from .table_extractor import from_pdf
        return ParsedDocument(text, "application/pdf", pages=pages,
                              tables=from_pdf(data), metadata={"parser": "pdfminer"})

    async def _parse_docx(self, data: bytes) -> ParsedDocument:
        try:
            import io
            from docx import Document as Docx
            d = Docx(io.BytesIO(data))
            text = "\n".join(p.text for p in d.paragraphs)
            from .table_extractor import from_docx
            tables = from_docx(data)
        except Exception:
            text, tables = "", []
        return ParsedDocument(text, "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                              tables=tables, metadata={"parser": "python-docx"})

    async def _parse_xlsx(self, data: bytes) -> ParsedDocument:
        try:
            import io
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            lines = []
            for ws in wb.worksheets:
                lines.append(f"# {ws.title}")
                lines += [" | ".join("" if v is None else str(v) for v in row)
                          for row in ws.iter_rows(values_only=True)]
            text = "\n".join(lines)
        except Exception:
            text = ""
        return ParsedDocument(text, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              metadata={"parser": "openpyxl"})

    async def _parse_html(self, raw: str) -> ParsedDocument:
        try:
            from bs4 import BeautifulSoup
            text = BeautifulSoup(raw, "html.parser").get_text("\n")
        except ImportError:
            text = re.sub(r"<[^>]+>", " ", raw)
        return ParsedDocument(text, "text/html", metadata={"parser": "bs4"})

    async def _parse_image_ocr(self, data: bytes) -> ParsedDocument:
        import io, tempfile
        from rag.ocr import ocr_image
        text = ""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data))
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
                img.save(fh.name)
                text = ocr_image(fh.name)
        except Exception:
            pass
        return ParsedDocument(text, "image/png", metadata={"parser": "tesseract"})


parser = DocumentParser()
