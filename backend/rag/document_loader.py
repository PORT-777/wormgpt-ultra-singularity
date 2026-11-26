"""Multi-source document loading (optional deps degrade gracefully)."""
from __future__ import annotations

import csv, html, json, re
from pathlib import Path
from typing import Any

from .models import Document, now_iso

SUPPORTED_SOURCES = ["pdf", "docx", "pptx", "xlsx", "html", "markdown", "txt",
                     "url", "youtube", "github_repo", "audio", "image", "json", "csv"]


def clean_text(text: str) -> str:
    text = html.unescape(str(text or "")).replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _meta(source_type: str, name: str) -> dict[str, Any]:
    return {"source_type": source_type, "source_url": name,
            "created_at": now_iso(), "language": "und"}


def load_text(path: str) -> Document:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return Document(clean_text(text), {**_meta(p.suffix.lstrip(".") or "txt", str(p)),
                                       "word_count": len(text.split())})


def load_json(path: str) -> Document:
    data = json.loads(Path(path).read_text(encoding="utf-8", errors="replace"))
    def flatten(obj, prefix=""):
        out = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                out += flatten(v, f"{prefix}.{k}" if prefix else str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                out += flatten(v, f"{prefix}[{i}]")
        else:
            out.append(f"{prefix}: {obj}")
        return out
    return Document(clean_text("\n".join(flatten(data))),
                    {**_meta("json", str(path)), "word_count": len(flatten(data))})


def load_csv(path: str) -> Document:
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        return Document("", _meta("csv", str(path)))
    header = rows[0]
    lines = [", ".join(header)]
    lines += [", ".join(r) for r in rows[1:]]
    return Document(clean_text("\n".join(lines)),
                    {**_meta("csv", str(path)), "row_count": len(rows) - 1})


def load_html(path_or_url: str) -> Document:
    raw = Path(path_or_url).read_text(encoding="utf-8", errors="replace") \
        if not path_or_url.startswith("http") else ""
    try:
        from bs4 import BeautifulSoup
        text = BeautifulSoup(raw, "html.parser").get_text("\n")
    except ImportError:
        text = re.sub(r"<[^>]+>", " ", raw)
    return Document(clean_text(text), _meta("html", path_or_url))


def load_pdf(path: str) -> Document:
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(path) or ""
        pages = text.count("\f") + 1
    except ImportError:
        text, pages = "", 0
    if not text.strip():
        from .ocr import ocr_pdf
        text = ocr_pdf(path)
    return Document(clean_text(text.replace("\f", "\n")),
                    {**_meta("pdf", str(path)), "page_count": pages})


def load_docx(path: str) -> Document:
    try:
        from docx import Document as Docx
        d = Docx(path)
        text = "\n".join(p.text for p in d.paragraphs)
        tables = "\n".join(" | ".join(c.text for c in row.cells)
                            for t in d.tables for row in t.rows)
        text = text + "\n" + tables
    except ImportError:
        text = ""
    return Document(clean_text(text), _meta("docx", str(path)))


def load_pptx(path: str) -> Document:
    try:
        from pptx import Presentation
        pres = Presentation(path)
        text = "\n".join(shape.text for slide in pres.slides
                          for shape in slide.shapes if hasattr(shape, "text"))
    except ImportError:
        text = ""
    return Document(clean_text(text), {**_meta("pptx", str(path)),
                                       "page_count": len(pres.slides) if text else 0})


def load_xlsx(path: str) -> Document:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        lines = []
        for ws in wb.worksheets:
            lines.append(f"# {ws.title}")
            for row in ws.iter_rows(values_only=True):
                lines.append(" | ".join("" if v is None else str(v) for v in row))
        text = "\n".join(lines)
    except ImportError:
        text = ""
    return Document(clean_text(text), _meta("xlsx", str(path)))


def load(source: str) -> Document:
    """Load a local file by extension."""
    suffix = Path(source).suffix.lower().lstrip(".")
    loaders = {
        "pdf": load_pdf, "docx": load_docx, "pptx": load_pptx, "xlsx": load_xlsx,
        "html": load_html, "htm": load_html, "json": load_json, "csv": load_csv,
    }
    fn = loaders.get(suffix, load_text)
    return fn(source)
