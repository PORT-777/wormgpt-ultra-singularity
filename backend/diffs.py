"""Artifact diff: compare two versions."""
from __future__ import annotations

import difflib
from typing import Dict


def diff_text(a: str, b: str) -> dict:
    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)
    diff = list(difflib.unified_diff(a_lines, b_lines, fromfile="v1", tofile="v2"))
    return {"diff": "".join(diff), "added": sum(1 for l in diff if l.startswith("+") and not l.startswith("+++")),
            "removed": sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))}


def diff_artifact_versions(versions: list, v1: int, v2: int) -> dict:
    c1 = next((v["content"] for v in versions if v["version"] == v1), "")
    c2 = next((v["content"] for v in versions if v["version"] == v2), "")
    return diff_text(c1, c2)
