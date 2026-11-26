"""Semantic-ish answer cache keyed on normalized question."""
from __future__ import annotations

import re

from ..cache import cache


def normalize(text: str) -> str:
    return " ".join(re.findall(r"\w+", str(text or "").lower()))


async def answer(question, producer):
    key = "semantic:" + normalize(question)
    hit = cache.get(key)
    if hit is not None:
        return hit
    value = await producer(question)
    cache.set(key, value)
    return value
