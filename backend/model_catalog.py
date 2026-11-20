"""Phase A: Unified model catalog data structures (ported concepts from OmniRoute)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FreeType(str, Enum):
    FREE_FOREVER = "FREE_FOREVER"
    RECURRING_FREE_TIER = "RECURRING_FREE_TIER"
    ONE_TIME_INITIAL = "ONE_TIME_INITIAL"
    TEMPORARY_PROMOTION = "TEMPORARY_PROMOTION"
    PAID = "PAID"
    UNKNOWN = "UNKNOWN"
    DISCONTINUED = "DISCONTINUED"


class ModelType(str, Enum):
    CHAT = "chat"
    IMAGE = "image"
    EMBEDDING = "embedding"
    AUDIO = "audio"
    VIDEO = "video"
    RERANKING = "reranking"
    OTHER = "other"


class ModelCatalogEntry(BaseModel):
    model_id: str
    canonical_model_id: str
    provider_id: str
    provider_display_name: str = ""
    model_display_name: str = ""
    model_type: ModelType = ModelType.CHAT
    capabilities: List[str] = Field(default_factory=list)
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    input_price: Optional[float] = None
    output_price: Optional[float] = None
    cached_input_price: Optional[float] = None
    currency: str = "USD"
    pricing_source: str = "unknown"
    free_type: FreeType = FreeType.UNKNOWN
    quota_pool_id: Optional[str] = None
    availability_status: str = "unknown"
    requires_api_key: bool = True
    requires_oauth: bool = False
    requires_account: bool = False
    requires_payment_method: bool = False
    region_restrictions: List[str] = Field(default_factory=list)
    terms_status: str = "unknown"
    last_verified_at: Optional[str] = None
    last_synced_at: Optional[str] = None
    catalog_data_source: str = "manual"


def is_eligible_free(entry: ModelCatalogEntry) -> bool:
    return entry.free_type in (FreeType.FREE_FOREVER, FreeType.RECURRING_FREE_TIER)
