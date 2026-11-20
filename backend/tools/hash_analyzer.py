from __future__ import annotations
import json, re
from typing import Any
from .base import Tool
import security_ops

_HASH_TYPES = [
    (r"^[a-fA-F0-9]{32}$", "MD5"),
    (r"^[a-fA-F0-9]{40}$", "SHA1"),
    (r"^[a-fA-F0-9]{64}$", "SHA256"),
    (r"^[a-fA-F0-9]{128}$", "SHA512"),
]
_SSDEEP_RE = re.compile(r"^\d+:[A-Za-z0-9/+]+:[A-Za-z0-9/+]+$")

class HashAnalyzer(Tool):
    name = "HashAnalyzer"
    description = (
        "Analyze file hashes or compute hashes from file/text/bytes. Accepts MD5/SHA1/SHA256/SHA512/SSDEEP. "
        "Returns hash type, computed hashes (when input is content/path), and lookup guidance (no external DB query)."
    )
    example = {"hash": "44d88612fea8a8f36de82e1278abb02f"}

    async def run(self, hash: str = "", path: str = "", text: str = "", data: str = "", **_: Any) -> str:
        out: dict = {"ok": True}
        try:
            if path or text or data:
                params = {}
                if path: params["path"] = path
                elif data: params["base64"] = data
                else: params["text"] = text
                res = security_ops.run_action("hashes", allow_host=False, **params)
                out.update(res if isinstance(res, dict) else {"result": res})
                # infer from computed values
                h = out.get("hashes") or out
                for k in ("md5","sha1","sha256","sha512","ssdeep"):
                    if k in h and not out.get("hash_type"):
                        out["hash_type"] = k.upper()
            hv = (hash or "").strip()
            if hv:
                htype = "unknown"
                for rx, name in _HASH_TYPES:
                    if re.match(rx, hv): htype = name; break
                if htype == "unknown" and _SSDEEP_RE.match(hv):
                    htype = "SSDEEP"
                out["input_hash"] = hv
                out["hash_type"] = htype
                out["threat_lookup_guidance"] = {
                    "providers": ["VirusTotal", "MalwareBazaar/abuse.ch", "AlienVault OTX", "Hybrid Analysis", "internal TI"],
                    "note": "No external reputation API queried by default in this environment; use available intel connectors/tools or provide scan results to enrich.",
                }
            if not out.get("hash_type") and not path and not text and not data:
                return "ERROR: provide hash and/or path/text/data"
            return json.dumps(out, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            return f"ERROR: HashAnalyzer failed: {e}"
