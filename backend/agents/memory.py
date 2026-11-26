"""Short-term, working and long-term agent memory."""
from __future__ import annotations

import json
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rag.models import Document
from rag.vector_store import VectorStore


@dataclass
class Turn:
    role: str
    content: str
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentMemory:
    def __init__(self, path: str = "data/agent_memory.json",
                 store: VectorStore | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.short_term: deque[Turn] = deque(maxlen=20)
        self.working: dict[str, Any] = {}
        self.store = store or VectorStore()
        self._persisted: dict[str, Any] = json.loads(
            self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    async def remember(self, session_id: str, content: str, user_id: str = "default"):
        from rag.embedder import embed
        self.short_term.append(Turn("memory", content[:4000]))
        summary = content[:400]
        vec = (await embed([summary]))[0]
        mid = f"memory:{session_id}:{uuid.uuid4().hex[:8]}"
        doc = Document(summary, {"session_id": session_id, "user_id": user_id,
                                 "timestamp": datetime.now(timezone.utc).isoformat()},
                       doc_id=mid)
        doc.embedding = vec
        self.store.upsert([doc])
        self._persisted[mid] = doc.metadata
        self.path.write_text(json.dumps(self._persisted), encoding="utf-8")

    async def recall(self, query: str, user_id: str = "default", top_k: int = 3):
        from rag.embedder import embed
        vec = (await embed([query]))[0]
        return self.store.search(vec, top_k=top_k, filters={"user_id": user_id})

    def add_turn(self, role: str, content: str):
        self.short_term.append(Turn(role, content))

    def recent(self, n: int = 10) -> list[Turn]:
        return list(self.short_term)[-n:]

    def clear(self, user_id: str):
        for mid, meta in list(self._persisted.items()):
            if meta.get("user_id") == user_id:
                self.store.delete(mid)
                self._persisted.pop(mid, None)
        self.path.write_text(json.dumps(self._persisted), encoding="utf-8")


memory = AgentMemory()
