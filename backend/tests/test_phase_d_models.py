"""Phase D — model management tests (offline)."""
from __future__ import annotations

import asyncio

from models.fallback import DEFAULT_FALLBACK_CHAIN, AllModelsFailedError, call_with_fallback
from models.monitor import EVENTS, record, summary
from models.registry import MODEL_CATALOG, ModelSpec, catalog, provider_available
from models.router import RoutingStrategy, detect_task, route_request
from models.semantic_cache import SemanticCache, CachedResponse


def test_catalog_size():
    assert len(MODEL_CATALOG) >= 10


def test_catalog_shapes():
    c = catalog()
    assert all("provider" in v and "context" in v for v in c.values())


def test_model_spec():
    s = ModelSpec("openai", 128000, 0.001, 0.002, ("code",), "fast")
    assert s.context == 128000 and "code" in s.strengths


def test_provider_available_boolean():
    assert isinstance(provider_available("openai"), bool)


def test_detect_task_code():
    assert detect_task("write a python function") == "code"


def test_detect_task_vision():
    assert detect_task("analyze this image") == "vision"


def test_detect_task_long_context():
    assert detect_task("x" * 21000) == "long-context"


def test_route_request_strategies():
    for s in RoutingStrategy:
        sel = asyncio.run(route_request("hello", strategy=s))
        assert sel.name and sel.reason


def test_route_request_filters_context():
    sel = asyncio.run(route_request("hi", required_context=2_000_000))
    assert sel.name


def test_route_request_free_only():
    sel = asyncio.run(route_request("hi", max_cost_per_1k=0.0))
    assert sel.name


def test_default_fallback_chain():
    assert len(DEFAULT_FALLBACK_CHAIN) >= 4


def test_fallback_all_fail(monkeypatch):
    import models.fallback as fb
    monkeypatch.setattr(fb, "provider_available", lambda p: False)
    try:
        asyncio.run(call_with_fallback("hi", ["nonexistent"]))
        assert False
    except AllModelsFailedError:
        assert True


def test_monitor_record_and_summary():
    before = len(EVENTS)
    record("test-model", 12, 5, 3, True, 0.001)
    s = summary()
    assert s["calls"] == before + 1
    assert "test-model" in s["by_model"]


def test_semantic_cache_roundtrip():
    sc = SemanticCache()
    asyncio.run(sc.set("what is 42", "the answer", 0.002))
    hit = asyncio.run(sc.get("what is 42"))
    assert isinstance(hit, CachedResponse)
    assert hit.response == "the answer"


def test_semantic_cache_miss():
    sc = SemanticCache()
    assert asyncio.run(sc.get("totally unrelated query xyz")) is None
