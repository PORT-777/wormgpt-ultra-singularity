"""Knowledge base (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional

import kv_store

KB_MOD = "knowledge_bases"
FILES_MOD = "kb_files"
CHUNKS_MOD = "kb_chunks"


def _load_kbs() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(KB_MOD)]


def create(name: str, owner: str = "default", description: str = "") -> dict:
    kid = uuid.uuid4().hex[:12]
    kb = {"id": kid, "name": name, "owner": owner, "description": description,
          "created_at": time.time(), "file_ids": []}
    kv_store.set(KB_MOD, kid, kb, owner=owner)
    return kb


def get(kid: str) -> Optional[dict]:
    return kv_store.get(KB_MOD, kid)


def list_all(owner: Optional[str] = None) -> List[dict]:
    out = _load_kbs()
    if owner:
        out = [k for k in out if k["owner"] == owner]
    return out


def delete(kid: str) -> bool:
    # delete kb + files + chunks
    for f in kv_store.list_all(FILES_MOD):
        if f["value"].get("kb_id") == kid:
            kv_store.delete(FILES_MOD, f["key"])
    for c in kv_store.list_all(CHUNKS_MOD):
        if c["value"].get("kb_id") == kid:
            kv_store.delete(CHUNKS_MOD, c["key"])
    return kv_store.delete(KB_MOD, kid)


def add_file(kid: str, file_id: str, path: str, chunks: List[dict]) -> bool:
    if not kv_store.get(KB_MOD, kid):
        return False
    kb = kv_store.get(KB_MOD, kid)
    kb["file_ids"].append(file_id)
    kv_store.set(KB_MOD, kid, kb, owner=kb["owner"])
    kv_store.set(FILES_MOD, f"{kid}:{file_id}", {"kb_id": kid, "file_id": file_id, "path": path})
    for i, c in enumerate(chunks):
        kv_store.set(CHUNKS_MOD, f"{kid}:{file_id}:{i}", {"kb_id": kid, "file_id": file_id, "path": path, **c})
    return True


def search(kid: str, query: str, k: int = 8) -> List[dict]:
    ql = query.lower()
    chunks = [e["value"] for e in kv_store.list_all(CHUNKS_MOD)]
    chunks = [c for c in chunks if c.get("kb_id") == kid]
    scored = []
    for ch in chunks:
        text = ch.get("text", "")
        score = text.lower().count(ql) if ql else 0
        for w in ql.split():
            if w and w in text.lower():
                score += 1
        if score > 0 or not ql:
            scored.append((score, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]


def files(kid: str) -> List[dict]:
    return [e["value"] for e in kv_store.list_all(FILES_MOD) if e["value"].get("kb_id") == kid]


def remove_file(kid: str, file_id: str) -> bool:
    kv_store.delete(FILES_MOD, f"{kid}:{file_id}")
    for c in kv_store.list_all(CHUNKS_MOD):
        if c["value"].get("kb_id") == kid and c["value"].get("file_id") == file_id:
            kv_store.delete(CHUNKS_MOD, c["key"])
    kb = kv_store.get(KB_MOD, kid)
    if kb:
        kb["file_ids"] = [f for f in kb["file_ids"] if f != file_id]
        kv_store.set(KB_MOD, kid, kb, owner=kb["owner"])
    return True
