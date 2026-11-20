"""Document processing pipeline: validation, extraction, chunking, metadata."""
from __future__ import annotations

import csv
import io
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional

MAX_BYTES = 50 * 1024 * 1024
ALLOWED = {".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".html"}


def validate(path: Path) -> Optional[str]:
    if not path.exists():
        return "file not found"
    if path.stat().st_size > MAX_BYTES:
        return "file too large"
    if path.suffix.lower() not in ALLOWED:
        return "unsupported file type"
    return None


def extract_text(path: Path) -> str:
    suf = path.suffix.lower()
    data = path.read_bytes()
    if suf in (".txt", ".md", ".json", ".html"):
        return data.decode("utf-8", errors="replace")
    if suf == ".csv":
        try:
            text = data.decode("utf-8", errors="replace")
            reader = csv.reader(io.StringIO(text))
            return "\n".join(" | ".join(row) for row in reader)
        except Exception:
            return data.decode("utf-8", errors="replace")
    if suf == ".docx":
        try:
            import zipfile
            import re
            z = zipfile.ZipFile(io.BytesIO(data))
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
            return re.sub(r"<[^>]+>", " ", xml)
        except Exception as e:
            return f"[docx extraction failed: {e}]"
    if suf == ".pdf":
        try:
            import PyPDF2  # type: ignore
            r = PyPDF2.PdfReader(io.BytesIO(data))
            return "\n".join(p.extract_text() or "" for p in r.pages)
        except Exception:
            try:
                import pdfplumber  # type: ignore
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    return "\n".join(p.extract_text() or "" for p in pdf.pages)
            except Exception as e:
                return f"[pdf extraction failed: {e}]"
    return ""


def chunk(text: str, size: int = 1000, overlap: int = 100) -> List[Dict]:
    out = []
    i = 0
    idx = 0
    n = len(text)
    while i < n:
        piece = text[i:i + size]
        out.append({"index": idx, "text": piece, "start": i, "end": min(i + size, n)})
        idx += 1
        i += size - overlap
        if i >= n:
            break
    return out


def process(path: Path) -> dict:
    err = validate(path)
    if err:
        return {"ok": False, "error": err}
    text = extract_text(path)
    chunks = chunk(text)
    return {"ok": True, "path": str(path), "chars": len(text),
            "chunks": len(chunks), "preview": text[:500], "chunk_list": chunks}
