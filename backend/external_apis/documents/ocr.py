"""OCR wrapper around tesseract when available."""
from __future__ import annotations

import shutil, subprocess


def ocr(path: str) -> dict:
    if not shutil.which("tesseract"):
        return {"status": "degraded", "reason": "tesseract not installed"}
    try:
        out = subprocess.run(["tesseract", path, "stdout"], capture_output=True,
                             text=True, timeout=120)
        return {"status": "ok", "text": out.stdout[:20000]}
    except Exception as exc:
        return {"status": "degraded", "reason": str(exc)[:200]}
