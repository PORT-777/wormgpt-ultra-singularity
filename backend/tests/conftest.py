"""
Test fixtures :: fake LLM brains so the engine is tested without any
paid API call.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

# Keep the suite hermetic. The shipped backend/.env points DATABASE_URL at
# Supabase PostgreSQL, but psycopg2 is not a test dependency; dotenv runs with
# override=False, so setting these before importing any project module wins.
# Set TEST_USE_REAL_DB=1 to exercise a real database on purpose.
if os.getenv("TEST_USE_REAL_DB") != "1":
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["STORAGE_BACKEND"] = "local"

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
