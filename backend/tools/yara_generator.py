from __future__ import annotations
import json
from typing import Any
from .base import Tool
import security_ops

class YaraGenerator(Tool):
    name = "YaraGenerator"
    description = (
        "Generate a YARA rule from strings, behavior description, or sample bytes/path. "
        "Can optionally validate by scanning provided sample content/path when validate=true."
    )
    example = {"description": "Detect suspicious PowerShell downloader", "text": "powershell -enc ... http://bad", "name": "Suspicious_PS_Downloader"}

    async def run(self, description: str = "", text: str = "", path: str = "", name: str = "", author: str = "CyberOps", is_pe: bool = False, validate: bool = False, **_: Any) -> str:
        blob = text or description
        params = {"text": blob, "description": description, "name": name, "author": author, "is_pe": bool(is_pe)}
        if path:
            params["path"] = path
        try:
            gen = security_ops.run_action("yara_generate", allow_host=False, **params)
        except Exception as e:
            return f"ERROR: YARA generation failed: {e}"
        if validate and isinstance(gen, dict) and gen.get("rule"):
            try:
                scan_params = {"rule_text": gen.get("rule")}
                if path:
                    scan_params["path"] = path
                elif blob:
                    scan_params["text"] = blob
                if "path" in scan_params or "text" in scan_params:
                    gen["validation"] = security_ops.run_action("yara_scan", allow_host=False, **scan_params)
            except Exception as e:
                gen["validation_error"] = str(e)
        return json.dumps(gen, ensure_ascii=False, indent=2, default=str)
