"""Provider health probe: ping provider base URLs."""
from __future__ import annotations

import time
from typing import Dict

import httpx


def probe(url: str, timeout: float = 5.0) -> dict:
    t0 = time.time()
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=True)
        return {"ok": r.status_code < 500, "status": r.status_code,
                "latency_ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        return {"ok": False, "status": None, "error": str(e),
                "latency_ms": int((time.time() - t0) * 1000)}


def probe_many(urls: Dict[str, str]) -> dict:
    return {name: probe(url) for name, url in urls.items()}
