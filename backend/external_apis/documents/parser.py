"""Parse supported documents to markdown-ish text."""
from __future__ import annotations

from pathlib import Path


def parse(path):
    from ..rag.document_loader import load
    return load(path)
