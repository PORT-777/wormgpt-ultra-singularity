"""Tool :: OCR (text extraction from images/scans).

Uses OpenCV + Tesseract when both are installed.  Degrades honestly: if a
dependency is missing the tool returns an actionable ERROR instead of a
fake result.
"""
from __future__ import annotations

import asyncio
from typing import Any

from .base import Tool


class OCR(Tool):
    name = "OCR"
    description = (
        "Extract text from an image or scanned document (Tesseract OCR, "
        "Arabic+English by default): {'path': 'scan.png', 'lang': 'ara+eng'}."
    )
    example = {"path": "scan.png", "lang": "ara+eng"}

    async def run(self, path: str = "", lang: str = "ara+eng",
                  **_: Any) -> str:
        if not path:
            return "ERROR: path required"
        try:
            lowered = str(path).lower().replace("\\", "/")
            if (len(lowered) > 2 and lowered[1] == ":") or \
                    lowered.startswith("/"):
                target = Tool.resolve_any(path)
            else:
                target = self.safe_path(path)
        except PermissionError as exc:
            return f"ERROR: denied — {exc}"
        except FileNotFoundError:
            return f"ERROR: no such file: {path}"

        def _ocr() -> str:
            try:
                import cv2
            except ImportError:
                return ("ERROR: OCR needs opencv-python "
                        "(pip install opencv-python)")
            try:
                import pytesseract
            except ImportError:
                return ("ERROR: OCR needs pytesseract + the tesseract binary "
                        "(pip install pytesseract; install tesseract-ocr)")
            img = cv2.imread(str(target))
            if img is None:
                return f"ERROR: cannot read image: {target.name}"
            try:
                text = pytesseract.image_to_string(img, lang=lang)
            except Exception as exc:
                return (f"ERROR: tesseract failed for lang={lang!r}: {exc} "
                        f"(is the '{lang}' traineddata installed?)")
            text = (text or "").strip()
            if not text:
                return "OCR: no text detected"
            return f"[ocr | {target.name} | {lang}]\n{text[:6000]}"

        return await asyncio.to_thread(_ocr)