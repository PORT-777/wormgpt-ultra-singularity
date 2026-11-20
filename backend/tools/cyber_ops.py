# backend/tools/cyber_ops.py
# Agent tool exposing the local CyberOps toolkit (96 deterministic actions):
# binary/PE/ELF/Mach-O analysis, IOC extraction, YARA/Sigma generation,
# MITRE mapping, log/timeline/PCAP analysis, host forensics, encoding/crypto
# helpers, threat-advisory scoring and report generation.
#
# Host paths are only reachable when the run has Full Access enabled
# (the same contextvar used by the other host-touching tools).

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

from .base import Tool, full_access

try:  # backend/ is on sys.path when the app runs normally
    import security_ops
except Exception:  # pragma: no cover - defensive path for odd launch dirs
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import security_ops  # type: ignore


def _dump(result: Dict[str, Any], limit: int = 24000) -> str:
    try:
        text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    except Exception:
        text = str(result)
    if len(text) > limit:
        text = text[:limit] + f"\n... [truncated {len(text) - limit} chars]"
    return text


class CyberOps(Tool):
    name = "CyberOps"
    description = (
        "Local cybersecurity/reverse-engineering toolkit (96 actions). "
        "Use for: file triage and hashes, PE/ELF/Mach-O analysis, IOC "
        "extraction/export, YARA/Sigma generation and scanning, MITRE "
        "mapping, log/timeline/PCAP analysis, email/LNK/prefetch/registry/"
        "browser/MFT/stego/firmware/APK/IPA forensics, secrets and IaC "
        "review, encoding/JWT/cert/hash helpers, threat-actor attribution, "
        "kill-chain/Diamond/STRIDE modelling, severity/patch scoring, and "
        "Markdown/JSON reports. Pass {'action': '<name>'} plus that "
        "action's parameters; use {'action': 'list'} to discover actions."
    )
    example = {
        "action": "pe",
        "path": "samples/unknown.exe",
        "extract": False,
    }

    async def run(self, action: str = "", **kwargs: Any) -> str:
        action = str(action or "").strip()
        lower = action.lower()
        if not lower or lower in ("list", "actions", "help"):
            caps = security_ops.capabilities()
            return _dump({"action_count": caps["action_count"],
                          "categories": caps["categories"],
                          "actions": caps["actions"]})
        if lower in ("capabilities", "capability", "info"):
            return _dump(security_ops.capabilities())

        allow_host = bool(full_access())
        try:
            result = security_ops.run_action(action, allow_host=allow_host, **kwargs)
        except FileNotFoundError as exc:
            return (f"ERROR: file not found: {exc}\n"
                    + ("Full Access is enabled." if allow_host else
                       "Paths are sandboxed to the workspace; enable Full Access "
                       "for arbitrary host paths."))
        except PermissionError as exc:
            return f"ERROR: access denied: {exc}"
        except ValueError as exc:
            return f"ERROR: {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            return f"ERROR: CyberOps action '{action}' failed: {type(exc).__name__}: {exc}"

        result.setdefault("host_access", allow_host)
        return _dump(result)
