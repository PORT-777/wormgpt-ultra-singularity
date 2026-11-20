"""
Test fixtures :: fake LLM brains so the engine is tested without any
paid API call.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import storage
storage.init()


def chunk(text: str):
    return SimpleNamespace(content=text)


class FakeBrain:
    """Scripted replies served one per loop iteration."""
    def __init__(self, replies):
        self.replies = list(replies)

    def astream(self, messages, **_):
        async def _gen():
            text = self.replies.pop(0) if self.replies else ""
            yield chunk(text)
        return _gen()

    async def ainvoke(self, messages, **_):
        return chunk(self.replies.pop(0) if self.replies else "")
