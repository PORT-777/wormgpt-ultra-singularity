"""Export traces to a local JSON file."""
from __future__ import annotations

import json
from pathlib import Path


def export(path: str = "data/traces.json") -> str:
    from .tracer import LLMTracer
    tracer = LLMTracer()
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    if Path("data/traces.jsonl").exists():
        for line in Path("data/traces.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    p.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return str(p)
