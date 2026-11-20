# backend/security_api.py
# HTTP surface for the CyberOps toolkit.
#
#   GET  /api/security/capabilities  -> toolkit metadata + action catalogue
#   GET  /api/security/actions       -> action list only
#   POST /api/security/run           -> execute one action
#
# Requests are ALWAYS sandboxed to config.WORKSPACE_DIR: the HTTP surface
# never sets allow_host=True (only the in-process agent tool can do that,
# and only in Full Access mode).

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:  # backend/ is normally on sys.path
    import security_ops
except Exception:  # pragma: no cover - defensive path for odd launch dirs
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import security_ops  # type: ignore

log = logging.getLogger("security_api")

router = APIRouter(prefix="/api/security", tags=["security"])


class RunRequest(BaseModel):
    action: str = Field(min_length=1, description="Action name, e.g. 'pe' or 'iocs'")
    params: Dict[str, Any] = Field(default_factory=dict,
                                   description="Action parameters")
    # Accept flattened parameters too: {"action":"iocs","text":"..."}
    model_config = {"extra": "allow"}


@router.get("/capabilities")
async def capabilities() -> Dict[str, Any]:
    """Return toolkit metadata, optional dependencies and the action catalogue."""
    return security_ops.capabilities()


@router.get("/actions")
async def actions() -> Dict[str, Any]:
    """Return the action catalogue (no handlers)."""
    rows = security_ops.list_actions()
    return {"count": len(rows), "actions": rows}


@router.post("/run")
async def run(req: RunRequest) -> Dict[str, Any]:
    """Execute one CyberOps action inside the workspace sandbox."""
    payload: Dict[str, Any] = {k: v for k, v in req.model_dump().items()
                               if k not in ("action", "params")}
    payload.update(req.params or {})
    try:
        result = security_ops.run_action(req.action, allow_host=False, **payload)
    except FileNotFoundError as exc:
        raise HTTPException(404, f"file not found: {exc}") from exc
    except PermissionError as exc:
        raise HTTPException(403, f"access denied: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("security action failed: %s", req.action)
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc
    result.setdefault("sandboxed", True)
    return result


@router.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "action_count": len(security_ops.ACTIONS)}


@router.get("/mitre/catalog")
async def mitre_catalog() -> Dict[str, Any]:
    """Return MITRE ATT&CK tactic/technique catalog for matrix UI."""
    try:
        from security_ops.knowledge import TACTIC_ORDER, TECHNIQUES
        by_t: Dict[str, list] = {}
        for t in TECHNIQUES or []:
            tac = t.get("tactic") or "Other"
            by_t.setdefault(tac, []).append({
                "id": t.get("id"),
                "name": t.get("name"),
                "description": t.get("description", ""),
            })
        ordered = list(TACTIC_ORDER) if TACTIC_ORDER else list(by_t.keys())
        return {"ok": True, "tactics": ordered, "by_tactic": {k: by_t.get(k, []) for k in ordered}, "count": len(TECHNIQUES or [])}
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
