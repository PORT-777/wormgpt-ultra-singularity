"""Phase B: Free eligibility classification engine (ported concepts)."""
from __future__ import annotations

from typing import Any, Dict

from model_catalog import FreeType, ModelCatalogEntry


def classify_free_type(metadata: Dict[str, Any]) -> FreeType:
    if metadata.get("discontinued"):
        return FreeType.DISCONTINUED
    free_type = metadata.get("free_type")
    if free_type in {e.value for e in FreeType}:
        return FreeType(free_type)
    if metadata.get("recurring_free") is True:
        return FreeType.RECURRING_FREE_TIER
    if metadata.get("free_forever") is True:
        return FreeType.FREE_FOREVER
    if metadata.get("one_time_credit") is True:
        return FreeType.ONE_TIME_INITIAL
    if metadata.get("temporary_promo") is True:
        return FreeType.TEMPORARY_PROMOTION
    if metadata.get("paid") is True:
        return FreeType.PAID
    return FreeType.UNKNOWN


def is_eligible(entry: ModelCatalogEntry) -> bool:
    return entry.free_type in (FreeType.FREE_FOREVER, FreeType.RECURRING_FREE_TIER)