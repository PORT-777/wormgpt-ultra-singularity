"""Webhook integrations (SQLite-persisted)."""
from __future__ import annotations

import time
import uuid
import json
import urllib.request
from typing import List, Dict, Optional

import kv_store

MODULE = "webhooks"


def _load() -> List[dict]:
    return [e["value"] for e in kv_store.list_all(MODULE)]


def register(url: str, events: List[str] = None, secret: str = "") -> dict:
    wid = uuid.uuid4().hex[:12]
    w = {"id": wid, "url": url, "events": events or ["*"],
         "secret": secret, "created_at": time.time(), "failures": 0}
    kv_store.set(MODULE, wid, w)
    return w


def list_all() -> List[dict]:
    return _load()


def delete(wid: str) -> bool:
    return kv_store.delete(MODULE, wid)


def dispatch(event: str, payload: dict) -> List[dict]:
    results = []
    for w in _load():
        if "*" in w["events"] or event in w["events"]:
            try:
                data = json.dumps({"event": event, "payload": payload}).encode()
                req = urllib.request.Request(w["url"], data=data,
                                            headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    results.append({"id": w["id"], "ok": True, "status": resp.status})
            except Exception as e:
                w["failures"] = w.get("failures", 0) + 1
                kv_store.set(MODULE, w["id"], w)
                results.append({"id": w["id"], "ok": False, "error": str(e)})
    return results
