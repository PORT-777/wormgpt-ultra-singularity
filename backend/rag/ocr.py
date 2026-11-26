"""OCR fallback via pytesseract (optional)."""
from __future__ import annotations


def available() -> bool:
    try:
        import pytesseract  # noqa: F401
        return True
    except ImportError:
        return False


def ocr_pdf(path: str) -> str:
    if not available():
        return ""
    try:
        import pytesseract
        from pdf2image import convert_from_path
        return "\n".join(pytesseract.image_to_string(p) for p in convert_from_path(path))
    except Exception:
        return ""


def ocr_image(path: str) -> str:
    if not available():
        return ""
    try:
        import pytesseract
        from PIL import Image
        return pytesseract.image_to_string(Image.open(path))
    except Exception:
        return ""
