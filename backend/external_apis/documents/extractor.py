"""Extract basic metadata and tables from text."""
from __future__ import annotations

import re
from typing import Any


def extract(text: str) -> dict[str, Any]:
    lines = [l for l in str(text or "").splitlines() if l.strip()]
    tables = [l for l in lines if l.count("|") >= 2]
    return {"lines": len(lines), "tables": tables[:20],
            "words": len(re.findall(r"\w+", str(text or "")))}
