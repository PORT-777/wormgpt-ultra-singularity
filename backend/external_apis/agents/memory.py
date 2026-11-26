"""Persistent agent memory (JSON file)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AgentMemory:
    def __init__(self, path="data/agent_memory.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def add(self, session, role, content):
        self.data.setdefault(session, []).append({"role": role, "content": str(content)[:4000]})
        self.path.write_text(json.dumps(self.data), encoding="utf-8")

    def recent(self, session, n=10):
        return self.data.get(session, [])[-n:]


memory = AgentMemory()
