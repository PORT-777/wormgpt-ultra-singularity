"""Workflow builder: nodes + edges, simple sequential executor."""
from __future__ import annotations

import time
import uuid
from typing import List, Dict, Optional, Any, Callable

WORKFLOWS: Dict[str, dict] = {}
RUNS: Dict[str, dict] = {}


def create(name: str, nodes: List[dict], edges: List[dict]) -> dict:
    wid = uuid.uuid4().hex[:12]
    w = {"id": wid, "name": name, "nodes": nodes, "edges": edges,
         "created_at": time.time()}
    WORKFLOWS[wid] = w
    return w


def get(wid: str) -> Optional[dict]:
    return WORKFLOWS.get(wid)


def list_all() -> List[dict]:
    return list(WORKFLOWS.values())


def delete(wid: str) -> bool:
    return WORKFLOWS.pop(wid, None) is not None


def _topo(nodes, edges):
    # Simple: sort by edge order; fallback to list order
    ids = [n["id"] for n in nodes]
    order = list(ids)
    # move nodes that are targets after sources
    changed = True
    while changed:
        changed = False
        for e in edges:
            s, t = e.get("source"), e.get("target")
            if s in order and t in order and order.index(s) > order.index(t):
                order.remove(t)
                order.insert(order.index(s) + 1, t)
                changed = True
    return [n for nid in order for n in nodes if n["id"] == nid]


def run(wid: str, handlers: Dict[str, Callable], initial: Any = None) -> dict:
    w = WORKFLOWS.get(wid)
    if not w:
        return {"ok": False, "error": "workflow not found"}
    rid = uuid.uuid4().hex[:12]
    run_rec = {"id": rid, "workflow_id": wid, "status": "running",
               "started_at": time.time(), "node_results": {}, "result": None}
    RUNS[rid] = run_rec
    ctx = initial
    try:
        for node in _topo(w["nodes"], w["edges"]):
            nid = node["id"]
            ntype = node.get("type", "ai")
            handler = handlers.get(ntype)
            if handler is None:
                run_rec["node_results"][nid] = {"ok": False, "error": f"no handler for {ntype}"}
                run_rec["status"] = "failed"
                return run_rec
            res = handler(node, ctx)
            run_rec["node_results"][nid] = res
            ctx = res.get("output", ctx) if isinstance(res, dict) else res
            if isinstance(res, dict) and not res.get("ok", True):
                run_rec["status"] = "failed"
                run_rec["result"] = res
                run_rec["finished_at"] = time.time()
                return run_rec
        run_rec["status"] = "completed"
        run_rec["result"] = ctx
    except Exception as e:
        run_rec["status"] = "failed"
        run_rec["error"] = str(e)
    run_rec["finished_at"] = time.time()
    return run_rec


def get_run(rid: str) -> Optional[dict]:
    return RUNS.get(rid)


def list_runs(wid: Optional[str] = None) -> List[dict]:
    out = list(RUNS.values())
    if wid:
        out = [r for r in out if r["workflow_id"] == wid]
    return out
