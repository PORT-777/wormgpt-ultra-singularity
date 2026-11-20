"""Model arena: fan-out same prompt to multiple models, collect results."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Any, Callable, Optional

RUNS: Dict[str, dict] = {}


def create(prompt: str, model_ids: List[str]) -> dict:
    rid = uuid.uuid4().hex[:12]
    r = {"id": rid, "prompt": prompt, "model_ids": model_ids, "status": "pending",
         "started_at": None, "finished_at": None, "results": []}
    RUNS[rid] = r
    return r


def run(rid: str, runner: Callable) -> dict:
    r = RUNS.get(rid)
    if not r:
        return {"ok": False, "error": "not found"}
    r["status"] = "running"
    r["started_at"] = time.time()
    for mid in r["model_ids"]:
        t0 = time.time()
        try:
            out = runner(mid, r["prompt"])
            r["results"].append({"model_id": mid, "ok": True, "output": out,
                                 "latency_ms": int((time.time() - t0) * 1000),
                                 "error": None})
        except Exception as e:
            r["results"].append({"model_id": mid, "ok": False, "output": None,
                                 "latency_ms": int((time.time() - t0) * 1000),
                                 "error": str(e)})
    r["status"] = "completed"
    r["finished_at"] = time.time()
    return r


def get(rid: str) -> Dict[str, Any]:
    return RUNS.get(rid, {})


def list_all() -> List[dict]:
    return list(RUNS.values())


def pick_best(rid: str) -> Optional[dict]:
    r = RUNS.get(rid)
    if not r or not r["results"]:
        return None
    ok = [x for x in r["results"] if x["ok"]]
    if not ok:
        return None
    return min(ok, key=lambda x: x["latency_ms"])
