"""Shared LLM helper tests (offline, mocked brain)."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import llm


def test_default_model_is_groq():
    assert llm.DEFAULT_MODEL == "openai/gpt-oss-120b"


def test_ask_uses_groq_and_returns_text(monkeypatch):
    import model_router

    class FakeBrain:
        async def ainvoke(self, messages, **kwargs):
            return SimpleNamespace(content="hello")

    monkeypatch.setattr(model_router.ROUTER, "resolve",
                        lambda *a, **k: ("groq", FakeBrain()))
    out = asyncio.run(llm.ask("hi"))
    assert out == "hello"


def test_ask_maps_unknown_model_to_default(monkeypatch):
    import model_router
    seen = {}

    class FakeBrain:
        async def ainvoke(self, messages, **kwargs):
            seen["messages"] = messages
            return SimpleNamespace(content="ok")

    monkeypatch.setattr(model_router.ROUTER, "resolve",
                        lambda *a, **k: ("groq", FakeBrain()))
    asyncio.run(llm.ask("hi", model="not-a-groq-model"))
    assert len(seen["messages"]) == 2


def test_ask_raises_without_brain(monkeypatch):
    import model_router
    monkeypatch.setattr(model_router.ROUTER, "resolve", lambda *a, **k: ("none", None))
    try:
        asyncio.run(llm.ask("hi"))
        assert False
    except RuntimeError:
        assert True
