"""Export traces to a local JSON file."""
from __future__ import annotations

import json
from pathlib import Path

from .tracer import TRACES


def export(path="data/traces.json"):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(TRACES, indent=2), encoding="utf-8")
    return str(p)
