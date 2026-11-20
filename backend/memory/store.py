"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Long-Term Memory store (RAG)

ChromaDB persistent vector store with a JSON-file fallback so the
platform never hard-fails when chromadb isn't installed.

What gets stored
----------------
- Completed task summaries (task + final answer + route)
- Facts the agent learned during tasks
Before every new task the engine recalls the top-k relevant memories
and injects them as context -> the agent "remembers" weeks-old files,
commands and conversations.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import List, Optional

import configs as config

log = logging.getLogger("memory")

# --------------------------------------------------------------------------- #
#  Backend resolution
# --------------------------------------------------------------------------- #
try:
    import chromadb  # type: ignore

    _client = chromadb.PersistentClient(path=str(config.MEMORY_DIR / "chroma"))
    # Chroma collection names must be 3-512 chars, [a-zA-Z0-9._-], start/end alnum.
    _coll = _client.get_or_create_collection("port777_memory")
    _CHROMA = True
except Exception as exc:  # pragma: no cover
    _CHROMA = False
    log.warning("ChromaDB unavailable (%s) -> JSON memory fallback", exc)
    _STORE = config.MEMORY_DIR / "memory_fallback.json"


# answers containing any of these are poison: memorizing a refusal
# trains future answers to refuse. Never store them.
_POISON_MARKERS = ()

def remember(text: str, kind: str = "fact", meta: Optional[dict] = None) -> str:
    """Store a memory (deduplicated by content hash) and return its id."""
    low = text.lower()
    if any(m in low for m in _POISON_MARKERS):
        log.info("memory: blocked storing refusal/noise (%d chars)", len(text))
        return ""
    doc_id = hashlib.sha1(f"{kind}:{text}".encode()).hexdigest()[:16]
    metadata = {"kind": kind, "ts": time.time(), **(meta or {})}

    if _CHROMA:
        _coll.upsert(ids=[doc_id], documents=[text], metadatas=[metadata])
    else:
        items = _load_json()
        items[doc_id] = {"text": text, **metadata}
        _save_json(items)
    return doc_id


def remember_task(task: str, answer: str, route: str = "") -> Optional[str]:
    """Called by the engine after every completed run."""
    if not config.MEMORY_ENABLED:
        return None
    return remember(
        f"Task: {task.strip()[:500]}\nResult: {answer[:1200].strip()}",
        kind="task",
        meta={"route": route},
    )


def recall(query: str, k: int = 3) -> List[dict]:
    """Semantic recall (chroma) or scored substring recall (fallback)."""
    if not config.MEMORY_ENABLED:
        return []
    if _CHROMA:
        res = _coll.query(query_texts=[query], n_results=k)
        return [
            {"text": doc, **meta}
            for doc, meta in zip(
                res.get("documents", [[]])[0],
                res.get("metadatas", [[]])[0],
            )
        ]

    ql = query.lower().split()
    scored = []
    for _id, item in _load_json().items():
        score = sum(1 for w in ql if w in item["text"].lower())
        if score:
            scored.append((score, {"id": _id, **item}))
    scored.sort(key=lambda s: -s[0])
    return [s[1] for s in scored[:k]]


def recent(k: int = 8) -> List[dict]:
    if _CHROMA:
        res = _coll.get(include=["documents", "metadatas"])
        rows = [{"id": _id, "text": d, **m}
                for _id, d, m in zip(res["ids"], res["documents"], res["metadatas"])]
        rows.sort(key=lambda r: -r.get("ts", 0))
        return rows[:k]
    items = sorted(_load_json().items(), key=lambda kv: -kv[1].get("ts", 0))
    return [{"id": _id, **item} for _id, item in items[:k]]


def wipe() -> int:
    if _CHROMA:
        got = _coll.get()
        n = len(got["ids"])
        _coll.delete(ids=got["ids"])
        return n
    n = len(_load_json())
    _save_json({})
    return n


def engine_name() -> str:
    return "chromadb" if _CHROMA else "json-fallback"


def memory_status() -> dict:
    """Lightweight status for UI/diagnostics (no content dump)."""
    try:
        files_chunks = None
        coll = _files_coll()
        if coll is not None:
            try:
                files_chunks = int(coll.count())
            except Exception:
                files_chunks = None
        state_file = config.MEMORY_DIR / "index_state.json"
        last_index_ts = None
        if state_file.exists():
            try:
                last_index_ts = float(state_file.read_text(encoding="utf-8").strip() or 0)
            except Exception:
                last_index_ts = None
        return {
            "enabled": bool(config.MEMORY_ENABLED),
            "file_index_enabled": bool(config.FILE_INDEX_ENABLED),
            "engine": engine_name(),
            "workspace_dir": str(config.WORKSPACE_DIR),
            "memory_dir": str(config.MEMORY_DIR),
            "indexed_file_chunks": files_chunks,
            "last_index_ts": last_index_ts,
            "text_suffixes": sorted(TEXT_SUFFIXES),
        }
    except Exception as exc:
        eng = "chromadb" if _CHROMA else "json-fallback"
        return {
            "enabled": bool(getattr(config, "MEMORY_ENABLED", False)),
            "file_index_enabled": bool(getattr(config, "FILE_INDEX_ENABLED", False)),
            "engine": eng,
            "error": f"{type(exc).__name__}: {exc}",
        }


# ========================================================================= #
#  Deep memory: live RAG index of workspace FILES (content, not names)
# ========================================================================= #
TEXT_SUFFIXES = {".txt", ".md", ".py", ".js", ".json", ".csv", ".html",
                 ".css", ".yaml", ".yml", ".ini", ".log", ".xml", ".rst"}
_FILES_COLLECTION = None


def _files_coll():
    global _FILES_COLLECTION
    if not _CHROMA:
        return None
    if _FILES_COLLECTION is None:
        _FILES_COLLECTION = _client.get_or_create_collection("port777_files")
    return _FILES_COLLECTION


def index_workspace() -> int:
    """Index text files inside WORKSPACE_DIR into the vector store.

    Incremental: only files with mtime newer than the last sweep get
    (re-)chunked + upserted. Returns number of chunks indexed.
    """
    coll = _files_coll() if config.FILE_INDEX_ENABLED else None
    if coll is None:
        return 0

    state_file = config.MEMORY_DIR / "index_state.json"
    last_ts = 0.0
    if state_file.exists():
        try:
            last_ts = float(state_file.read_text().strip() or 0)
        except ValueError:
            last_ts = 0.0
    now = time.time()

    candidates = []
    for f in config.WORKSPACE_DIR.rglob("*"):
        if not (f.is_file() and f.suffix.lower() in TEXT_SUFFIXES):
            continue
        if f.stat().st_size > 400_000:          # skip huge files
            continue
        if "chroma" in f.parts or "memory_data" in f.parts:
            continue
        try:
            if f.stat().st_mtime > last_ts:
                candidates.append(f)
        except OSError:
            continue
        if len(candidates) >= config.INDEX_MAX_FILES:
            break

    chunks = 0
    for f in candidates:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(f.relative_to(config.WORKSPACE_DIR))
        # paragraph-ish chunking
        paras, buf = [], ""
        for para in text.split("\n\n"):
            buf = (buf + "\n\n" + para) if buf else para
            if len(buf) >= config.INDEX_CHUNK:
                paras.append(buf[: config.INDEX_CHUNK])
                buf = ""
        if buf.strip():
            paras.append(buf)
        if not paras:
            continue
        n = len(paras)
        coll.upsert(
            ids=[hashlib.sha1(f"{rel}#{i}".encode()).hexdigest()[:16]
                 for i in range(n)],
            documents=[p for p in paras],
            metadatas=[{"path": rel, "kind": "file", "ts": now}
                       for _ in paras],
        )
        chunks += len(paras)

    state_file.write_text(str(now))
    return chunks


def recall_files(query: str, k: int = 3) -> List[dict]:
    """Semantic search over the indexed workspace files."""
    coll = _files_coll()
    if coll is None:
        return []
    res = coll.query(query_texts=[query], n_results=k)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    return [{"text": d, **m} for d, m in zip(docs, metas)]



# --------------------------------------------------------------------------- #
#  JSON fallback helpers
# --------------------------------------------------------------------------- #
def _load_json() -> dict:
    if not _STORE.exists():
        return {}
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(items: dict) -> None:
    Path(_STORE).write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
