"""Tests for the internal external-API subsystem (no real network calls)."""
from __future__ import annotations

import asyncio

import pytest

import external_apis as ex
from external_apis import TTLCache, ExternalService, registry
from external_apis.rag.chunker import chunk
from external_apis.eval.scorer import score
from external_apis.rate_limiter import RateLimiter
from external_apis.registry import ServiceSpec


def test_registry_covers_all_phases():
    specs = registry.all()
    assert len(specs) >= 40
    names = {s.name for s in specs}
    for expected in ("openai", "cohere", "huggingface", "wolfram", "clarifai",
                     "assemblyai", "openrouter", "edenai", "spamhunter",
                     "serpapi", "github", "coingecko", "limitreset",
                     "openrouter-models", "pollinations"):
        assert expected in names


def test_missing_key_disables_service(monkeypatch):
    spec = ServiceSpec(name="probe", category="test", base_url="https://example.test",
                       endpoints={"q": "{base}/q"}, key_env="PROBE_MISSING_KEY")
    monkeypatch.setattr(ex.config, "keys", {**ex.config.keys, "PROBE_MISSING_KEY": ""})
    assert spec.available() is False
    result = asyncio.run(ExternalService(spec).healthCheck())
    assert result["status"] == "degraded"


def test_query_uses_client_and_transform(monkeypatch):
    calls = []

    async def fake(method, url, **kw):
        calls.append((method, url, kw))
        return {"data": [{"embedding": [1, 2]}]}

    monkeypatch.setattr("external_apis.base.client.request", fake)
    spec = ServiceSpec(name="tf", category="test", base_url="https://api.test",
                       endpoints={"embed": "{base}/embed"}, method="POST")
    out = asyncio.run(ExternalService(spec).query("embed", {"input": "hi"}))
    assert out["data"][0]["embedding"] == [1, 2]
    assert calls[0][0] == "POST" and calls[0][1] == "https://api.test/embed"


def test_cache_roundtrip_and_expiry(monkeypatch):
    c = TTLCache(ttl=0.01, max_entries=4)
    c.set("k", {"v": 1})
    assert c.get("k") == {"v": 1}
    import time
    time.sleep(0.02)
    assert c.get("k") is None


def test_rate_limiter_blocks():
    limiter = RateLimiter(per_minute=2)
    assert limiter.allow("s") is True
    assert limiter.allow("s") is True
    assert limiter.allow("s") is False


def test_chunker_overlap_and_bounds():
    text = " paragraph one. " * 80
    parts = chunk(text, size=120, overlap=20)
    assert len(parts) > 2
    assert all(len(p) <= 140 for p in parts)


def test_scorer_shape():
    out = score("the invoice total is 42", "what is the total?", ["invoice total 42"])
    assert set(out) == {"faithfulness", "relevance", "coherence"}
    assert all(0.0 <= v <= 1.0 for v in out.values())


def test_internal_routes_fail_closed(monkeypatch):
    from fastapi.testclient import TestClient
    from external_apis.api import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    monkeypatch.setattr(ex.config, "internal_key", "")
    client = TestClient(app)
    assert client.get("/api/internal/services").status_code == 503
    monkeypatch.setattr(ex.config, "internal_key", "secret")
    assert client.get("/api/internal/services",
                      headers={"x-internal-key": "secret"}).status_code == 200
    assert client.get("/api/internal/services",
                      headers={"x-internal-key": "wrong"}).status_code == 401
