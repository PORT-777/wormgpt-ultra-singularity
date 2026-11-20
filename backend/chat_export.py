"""Chat export: conversation -> markdown/json."""
from __future__ import annotations

import json
from typing import List, Dict


def to_markdown(messages: List[Dict], title: str = "Conversation") -> str:
    lines = [f"# {title}", ""]
    for m in messages:
        role = m.get("role", "user").capitalize()
        content = m.get("content", "")
        lines.append(f"## {role}")
        lines.append("")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


def to_json(messages: List[Dict], meta: dict = None) -> str:
    return json.dumps({"meta": meta or {}, "messages": messages}, indent=2, ensure_ascii=False)


def to_text(messages: List[Dict]) -> str:
    out = []
    for m in messages:
        out.append(f"{m.get('role','user').upper()}: {m.get('content','')}")
    return "\n\n".join(out)
