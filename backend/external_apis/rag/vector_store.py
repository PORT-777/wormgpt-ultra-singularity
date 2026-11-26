"""In-memory vector store with cosine similarity and JSON persistence."""
from __future__ import annotations

import json, math
from pathlib import Path
from typing import Any


def _cos(a, b):
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class VectorStore:
    def __init__(self):
        self.items: list[dict[str, Any]] = []

    def add(self, docs, vectors, metadatas=None):
        for i, (doc, vec) in enumerate(zip(docs, vectors)):
            self.items.append({"text": doc, "vector": vec,
                               "meta": (metadatas or [{}] * len(docs))[i]})
        return len(self.items)

    def search(self, vector, top_k=5):
        scored = [(_cos(vector, it["vector"]), it) for it in self.items]
        scored.sort(key=lambda x: -x[0])
        return [{"score": s, "text": it["text"], "meta": it["meta"]}
                for s, it in scored[:top_k]]

    def save(self, path):
        Path(path).write_text(json.dumps(self.items), encoding="utf-8")

    def load(self, path):
        p = Path(path)
        if p.exists():
            self.items = json.loads(p.read_text(encoding="utf-8"))


store = VectorStore()
