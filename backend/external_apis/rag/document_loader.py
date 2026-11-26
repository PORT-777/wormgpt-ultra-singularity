"""Load text/markdown/HTML/PDF into plain text."""
from __future__ import annotations

import re
from pathlib import Path


def load(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    suffix = p.suffix.lower()
    if suffix in (".txt", ".md", ".py", ".json"):
        return p.read_text(encoding="utf-8", errors="replace")
    if suffix in (".html", ".htm"):
        raw = p.read_text(encoding="utf-8", errors="replace")
        return re.sub(r"<[^>]+>", " ", raw)
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            return "\n".join(page.extract_text() or "" for page in PdfReader(str(p)).pages)
        except ImportError:
            return "[pdf parser unavailable: pip install pypdf)"
    return p.read_text(encoding="utf-8", errors="replace")
