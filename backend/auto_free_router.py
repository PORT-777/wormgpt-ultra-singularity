"""Native local-auto/free routing engine (Kilo-inspired, independently implemented)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from model_catalog import ModelCatalogEntry, is_eligible_free
from free_eligibility import is_eligible


VIRTUAL_MODEL_ID = "local-auto/free"

_session_affinity: Dict[str, str] = {}


def resolve_candidates(catalog: List[ModelCatalogEntry], required_caps: List[str]) -> List[ModelCatalogEntry]:
    out = []
    for e in catalog:
        if not is_eligible_free(e) or not is_eligible(e):
            continue
        if all(c in (e.capabilities or []) for c in required_caps):
            out.append(e)
    return out


def select_model(catalog: List[ModelCatalogEntry], required_caps: List[str], session_id: Optional[str] = None) -> Optional[ModelCatalogEntry]:
    candidates = resolve_candidates(catalog, required_caps)
    if not candidates:
        return None
    # session affinity
    if session_id and session_id in _session_affinity:
        mid = _session_affinity[session_id]
        for c in candidates:
            if c.model_id == mid:
                return c
    # deterministic: sort by model_id then provider_id
    chosen = sorted(candidates, key=lambda x: (x.provider_id, x.model_id))[0]
    if session_id:
        _session_affinity[session_id] = chosen.model_id
    return chosen


def clear_affinity(session_id: str) -> None:
    _session_affinity.pop(session_id, None)
