"""Unified provider adapter base + registry."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

PROVIDERS: Dict[str, "BaseProvider"] = {}


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def chat(self, messages: List[dict], model: str, **params) -> dict:
        ...

    @abstractmethod
    async def stream(self, messages: List[dict], model: str, **params) -> AsyncIterator[dict]:
        ...

    def supports(self, capability: str, model: str) -> bool:
        return False

    async def generate_image(self, prompt: str, **params) -> dict:
        raise NotImplementedError("image gen not supported")

    async def analyze_image(self, image_bytes: bytes, prompt: str, **params) -> dict:
        raise NotImplementedError("vision not supported")

    async def transcribe(self, audio_bytes: bytes, **params) -> str:
        raise NotImplementedError("stt not supported")

    async def synthesize(self, text: str, **params) -> bytes:
        raise NotImplementedError("tts not supported")


def register_provider(p: BaseProvider) -> None:
    PROVIDERS[p.name] = p


def get_provider(name: str) -> Optional[BaseProvider]:
    return PROVIDERS.get(name)


def list_providers() -> List[str]:
    return list(PROVIDERS.keys())


class MockProvider(BaseProvider):
    name = "mock"

    async def chat(self, messages, model, **params):
        last = messages[-1]["content"] if messages else ""
        return {"content": f"[mock:{model}] {last}", "usage": {"input": 10, "output": 20}}

    async def stream(self, messages, model, **params):
        r = await self.chat(messages, model, **params)
        yield {"type": "token", "data": r["content"]}
        yield {"type": "final", "data": r["content"]}

    def supports(self, capability, model):
        return capability in ("text", "streaming")


register_provider(MockProvider())
