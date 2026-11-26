"""Advanced chunking strategies with rich chunk metadata."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List

from .models import Chunk


class ChunkStrategy(str, Enum):
    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    MARKDOWN = "markdown"
    CODE = "code"
    SENTENCE = "sentence"
    SLIDING = "sliding"


def auto_strategy(doc) -> ChunkStrategy:
    name = str(getattr(doc, "metadata", {}).get("source_type", "")).lower()
    text = getattr(doc, "text", "") or ""
    if name in ("pdf", "docx", "pptx", "xlsx"):
        return ChunkStrategy.RECURSIVE
    if name in ("markdown", "md") or text.lstrip().startswith("#"):
        return ChunkStrategy.MARKDOWN
    if name in ("py", "ts", "js", "cpp", "c", "java", "go", "rs"):
        return ChunkStrategy.CODE
    if len(text) < 4000:
        return ChunkStrategy.SENTENCE
    return ChunkStrategy.SLIDING


def _split_recursive(text, size, overlap):
    parts, buf = [], ""
    seps = ["\n\n", "\n", ". ", " "]
    for para in re.split(r"(\n\n|\n)", text):
        if len(buf) + len(para) <= size:
            buf += para
        else:
            if buf.strip():
                parts.append(buf.strip())
            buf = para
    if buf.strip():
        parts.append(buf.strip())
    out = []
    for part in parts:
        while len(part) > size:
            cut = part.rfind(" ", 0, size)
            cut = cut if cut > size // 2 else size
            out.append(part[:cut].strip())
            part = part[max(0, cut - overlap):]
        if part.strip():
            out.append(part.strip())
    return out


def _split_markdown(text, size):
    sections, title, buf = [], "", []
    for line in text.splitlines():
        if line.startswith("#"):
            if buf:
                sections.append((title, "\n".join(buf)))
            title, buf = line.strip(), []
        else:
            buf.append(line)
    if buf:
        sections.append((title, "\n".join(buf)))
    out = []
    for title, body in sections:
        for part in _split_recursive(body, size, 0):
            out.append((title, part))
    return out


def _split_code(text, size):
    pattern = r"(?m)^(?:class |def |async def |function |interface |export )"
    idx = [m.start() for m in re.finditer(pattern, text)]
    if not idx:
        return [(None, p) for p in _split_recursive(text, size, 0)]
    chunks, start = [], 0
    for i in idx[1:] + [len(text)]:
        block = text[start:i]
        for part in _split_recursive(block, size, 0):
            chunks.append((block.splitlines()[0][:80], part))
        start = i
    return chunks


def _split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def chunk(text: str, size: int = 512, overlap: int = 64,
          strategy: ChunkStrategy = ChunkStrategy.RECURSIVE,
          doc_id: str = "", metadata: Dict[str, Any] | None = None) -> List[Chunk]:
    metadata = metadata or {}
    pairs: List[tuple] = []
    if strategy == ChunkStrategy.MARKDOWN:
        pairs = _split_markdown(text, size)
    elif strategy == ChunkStrategy.CODE:
        pairs = _split_code(text, size)
    elif strategy in (ChunkStrategy.SENTENCE, ChunkStrategy.SEMANTIC):
        buf = ""
        for s in _split_sentences(text):
            if len(buf) + len(s) <= size:
                buf += s + " "
            else:
                if buf.strip():
                    pairs.append((None, buf.strip()))
                buf = s + " "
        if buf.strip():
            pairs.append((None, buf.strip()))
    elif strategy == ChunkStrategy.SLIDING:
        for i in range(0, len(text), max(1, size - overlap)):
            pairs.append((None, text[i:i + size]))
    else:
        pairs = [(None, p) for p in _split_recursive(text, size, overlap)]

    chunks = [Chunk(text=t, parent_doc_id=doc_id, chunk_index=i,
                    section_title=title or "", prev_chunk_id=None,
                    next_chunk_id=None, page_number=metadata.get("page_number"),
                    metadata=metadata)
              for i, (title, t) in enumerate(pairs) if t]
    for i, c in enumerate(chunks):
        c.prev_chunk_id = chunks[i - 1].chunk_id if i else None
        c.next_chunk_id = chunks[i + 1].chunk_id if i + 1 < len(chunks) else None
    return chunks
