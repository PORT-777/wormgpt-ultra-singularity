"""Pure-Python PDF text extraction (FlateDecode + text operators) — no deps."""

import re
import zlib
from typing import Any, Dict, List

from plugins_system.sdk import BasePlugin, PluginManifest, PluginTool
from plugins_system.registry import register_plugin


def _extract_pdf_text(data: bytes) -> str:
    text = data.decode("latin-1", errors="replace")

    # 1. Uncompress FlateDecode streams
    def _uncompress(match: re.Match) -> str:
        try:
            return zlib.decompress(match.group(1)).decode("latin-1", errors="replace")
        except Exception:
            return match.group(0)

    text = re.sub(r"stream\r?\n(.*?)\r?\nendstream", lambda m: _uncompress(m), text, flags=re.S)

    # 2. Strip binary garbage and PDF operators we don't care about
    text = re.sub(r"<<.*?>>", " ", text, flags=re.S)
    text = re.sub(r"\[(.*?)\]", " ", text, flags=re.S)

    # 3. Extract text between BT/ET blocks using the Tj / TJ operators
    pages: List[str] = []
    for bt in re.finditer(r"BT(.*?)ET", text, re.S):
        block = bt.group(1)
        chunks: List[str] = []
        for tj in re.finditer(r"\((?:\\.|[^()\\])*\)\s*Tj", block):
            s = tj.group(0)
            inner = s[s.index("(") + 1 : s.rindex(")")]
            inner = re.sub(r"\\.", lambda m: m.group(0)[1], inner)
            chunks.append(inner)
        # TJ arrays: [(a) (b) (-123) (c)] TJ
        for tj in re.finditer(r"\[(.*?)\]\s*TJ", block, re.S):
            arr = tj.group(1)
            for piece in re.finditer(r"\((?:\\.|[^()\\])*\)", arr):
                inner = piece.group(0)
                inner = inner[1:-1]
                inner = re.sub(r"\\.", lambda m: m.group(0)[1], inner)
                chunks.append(inner)
        if chunks:
            pages.append("".join(chunks))

    joined = "\n".join(pages)
    joined = re.sub(r"\s+", " ", joined)
    return joined.strip()


@register_plugin
class PdfReaderPlugin(BasePlugin):
    manifest = PluginManifest(
        id="pdfreader",
        name="PDF Reader",
        description="Extract text from PDF files with no external dependencies",
        long_description=(
            "A dependency-free PDF text extractor: parses the raw PDF, inflates "
            "FlateDecode streams, and recovers text from BT/ET blocks using the Tj "
            "and TJ operators. Works for most text PDFs; scanned/image PDFs are "
            "not supported."
        ),
        version="1.0.0",
        author="outcome",
        icon="📄",
        category="docs",
        tags=["docs", "pdf", "text-extraction", "documents"],
        auth_type="none",
        auth_config={},
        tools=[
            PluginTool(
                name="pdfreader.extract",
                display_name="Extract Text",
                description="Extract all text from a PDF (base64 or URL)",
                parameters={
                    "source": {"type": "string", "description": "base64-encoded PDF bytes"},
                    "max_chars": {"type": "integer", "description": "Default 20000"},
                },
            ),
        ],
        website_url="https://www.adobe.com/pdf",
        docs_url="https://www.adobe.com/devnet/pdf.html",
        is_free=True,
        is_official=True,
    )

    def _validate_credentials(self) -> bool:
        return True

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        import base64

        if tool_name != "pdfreader.extract":
            raise ValueError(f"Unknown tool: {tool_name}")

        raw = parameters.get("source", "")
        try:
            data = base64.b64decode(raw)
        except Exception as exc:
            return {"ok": False, "error": f"invalid base64: {exc}"}

        text = _extract_pdf_text(data)
        limit = int(parameters.get("max_chars") or 20000)
        return {
            "ok": True,
            "bytes": len(data),
            "chars": len(text),
            "text": text[:limit],
        }