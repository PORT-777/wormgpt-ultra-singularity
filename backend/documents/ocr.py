"""OCR wrapper delegating to rag.ocr."""
from __future__ import annotations


def available() -> bool:
    from rag.ocr import available as rag_available
    return rag_available()


def ocr_image(path: str) -> str:
    from rag.ocr import ocr_image as rag_ocr
    return rag_ocr(path)
