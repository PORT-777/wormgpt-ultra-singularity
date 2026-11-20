from __future__ import annotations
import json
from typing import Any, Dict
from .base import Tool
import security_ops

class IOCExtractor(Tool):
    name = "IOCExtractor"
    description = (
        "Extract and normalize IOCs from text/logs/data (IPs, domains, URLs, hashes, CVEs, emails, paths). "
        "Supports defanged formats (hxxp://, [.], (dot), [at]). Returns structured JSON."
    )
    example = {"text": "Contact admin[@]evil[.]com hxxps://bad.example/x sha256 ...", "defang": True}

    async def run(self, text: str = "", path: str = "", content: str = "", defang: bool = False, **_: Any) -> str:
        src_text = text or content
        if path and not src_text:
            src_text = path
            payload = {"path": path}
        elif path and src_text:
            payload = {"path": path}
        else:
            payload = {"text": src_text}
        try:
            res = security_ops.run_action("iocs", allow_host=False, **payload)
        except Exception as e:
            return f"ERROR: IOC extraction failed: {e}"
        if defang and isinstance(res, dict):
            def _df(s: str) -> str:
                return (s.replace("http://", "hxxp://").replace("https://", "hxxps://")
                         .replace(".", "[.]").replace("@", "[@]"))
            cats = res.get("categories") or {}
            if isinstance(cats, dict):
                for k, vals in list(cats.items()):
                    if isinstance(vals, list):
                        cats[k] = [_df(str(v)) for v in vals]
                res["categories"] = cats
                res["defanged"] = True
        return json.dumps(res, ensure_ascii=False, indent=2, default=str)
