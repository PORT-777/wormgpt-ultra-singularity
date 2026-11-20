"""Data analysis helpers for CSV/JSON tabular data."""
from __future__ import annotations

import csv
import io
import json
from typing import List, Dict, Any


def parse_csv(text: str) -> List[Dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def summarize_rows(rows: List[Dict[str, Any]]) -> dict:
    if not rows:
        return {"rows": 0, "columns": []}
    cols = list(rows[0].keys())
    out = {"rows": len(rows), "columns": cols, "stats": {}}
    for c in cols:
        vals = [r.get(c) for r in rows]
        numeric = []
        for v in vals:
            try:
                numeric.append(float(v))
            except (TypeError, ValueError):
                pass
        if numeric:
            out["stats"][c] = {
                "min": min(numeric), "max": max(numeric),
                "mean": sum(numeric) / len(numeric), "count": len(numeric),
            }
        else:
            from collections import Counter
            out["stats"][c] = {"unique": len(set(vals)),
                               "top": Counter(vals).most_common(3)}
    return out


def filter_rows(rows: List[Dict], column: str, op: str, value: Any) -> List[Dict]:
    out = []
    for r in rows:
        v = r.get(column)
        try:
            v = float(v)
            value = float(value)
        except (TypeError, ValueError):
            pass
        if op == "==" and v == value:
            out.append(r)
        elif op == "!=" and v != value:
            out.append(r)
        elif op == ">" and v > value:
            out.append(r)
        elif op == "<" and v < value:
            out.append(r)
        elif op == "contains" and str(value).lower() in str(v).lower():
            out.append(r)
    return out
