from __future__ import annotations
import json
from typing import Any
from .base import Tool
import security_ops

class ThreatIntel(Tool):
    name = "ThreatIntel"
    description = (
        "Aggregate local threat-intel style enrichment from available inputs: extract IOCs, map to MITRE ATT&CK, "
        "build detection hints, and summarize reputation context guidance. Uses local security_ops knowledge (offline-safe)."
    )
    example = {"text": "powershell -enc ... contacted 1.2.3.4 and evil.example", "action": "enrich"}

    async def run(self, action: str = "enrich", text: str = "", path: str = "", query: str = "", **_: Any) -> str:
        act = (action or "enrich").lower().strip()
        try:
            src = {"text": text or query}
            if path: src = {"path": path}
            if act == "ioc" or act == "iocs":
                res = security_ops.run_action("iocs", allow_host=False, **src)
                return json.dumps(res, ensure_ascii=False, indent=2, default=str)
            if act == "mitre":
                res = security_ops.run_action("mitre", allow_host=False, **src)
                return json.dumps(res, ensure_ascii=False, indent=2, default=str)
            # enrich (default)
            blob = (text or query or "").strip()
            payload = {"path": path} if path else {"text": blob}
            iocs = {}
            mitre = {}
            try: iocs = security_ops.run_action("iocs", allow_host=False, **payload)
            except Exception as e: iocs = {"error": str(e)}
            try: mitre = security_ops.run_action("mitre", allow_host=False, **payload)
            except Exception as e: mitre = {"error": str(e)}
            res = {
                "ok": True,
                "source": path or "text",
                "iocs": iocs,
                "mitre": mitre,
                "reputation": {
                    "score_hint": "unknown (local/offline enrichment; connect external TI feeds/APIs for live reputation)",
                    "suggested_sources": ["abuse.ch", "AlienVault OTX", "VirusTotal", "MISP", "internal telemetry"],
                },
                "notes": "Local deterministic enrichment only; combine with external intel where available.",
            }
            return json.dumps(res, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            return f"ERROR: ThreatIntel failed: {e}"
