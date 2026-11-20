from __future__ import annotations
import json
from typing import Any
from .base import Tool
import security_ops

class SigmaBuilder(Tool):
    name = "SigmaBuilder"
    description = (
        "Generate a Sigma detection rule from behavior/observed artifacts (text/logs) and optionally convert to SPL/KQL/EQL/AQL. "
        "Also supports validate/test/convert actions."
    )
    example = {"action": "generate", "text": "powershell.exe -enc ... downloading from http://example.com", "target": "all"}

    async def run(self, action: str = "generate", text: str = "", description: str = "", title: str = "", path: str = "", rule_text: str = "", target: str = "all", samples: Any = None, **_: Any) -> str:
        act = (action or "generate").lower().strip()
        try:
            if act in ("generate", "gen", "make"):
                params = {"text": text or description, "description": description or text, "title": title}
                if path: params["path"] = path
                res = security_ops.run_action("sigma_generate", allow_host=False, **params)
                if target and isinstance(res, dict) and res.get("rule"):
                    try:
                        res["conversions"] = security_ops.run_action("sigma_convert", allow_host=False, rule_text=res.get("rule"), target=target)
                    except Exception as e:
                        res["convert_error"] = str(e)
                return json.dumps(res, ensure_ascii=False, indent=2, default=str)
            if act == "convert":
                if not rule_text:
                    return "ERROR: rule_text is required for convert"
                res = security_ops.run_action("sigma_convert", allow_host=False, rule_text=rule_text, target=target)
                return json.dumps(res, ensure_ascii=False, indent=2, default=str)
            if act == "validate":
                if not rule_text:
                    return "ERROR: rule_text is required for validate"
                res = security_ops.run_action("sigma_validate", allow_host=False, rule_text=rule_text)
                return json.dumps(res, ensure_ascii=False, indent=2, default=str)
            if act == "test":
                if not rule_text:
                    return "ERROR: rule_text is required for test"
                res = security_ops.run_action("sigma_test", allow_host=False, rule_text=rule_text, samples=samples or [])
                return json.dumps(res, ensure_ascii=False, indent=2, default=str)
            return f"ERROR: unknown SigmaBuilder action '{action}'. Use generate|convert|validate|test"
        except Exception as e:
            return f"ERROR: SigmaBuilder failed: {e}"
