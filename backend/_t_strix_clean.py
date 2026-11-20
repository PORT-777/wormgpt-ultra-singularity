# -*- coding: utf-8 -*-
"""Strip the ORIGINAL strix frontmatter that survives inside pulled pack bodies."""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent / "skills_packs" / "strix"

# our injected frontmatter block
OURS = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
# the original strix metadata block (after our title line, anywhere near top)
SECOND = re.compile(r"^---\s*\n[\s\S]*?\n---\s*\n", re.MULTILINE)

cleaned = 0
for f in ROOT.rglob("*.md"):
    text = f.read_text(encoding="utf-8")
    m = OURS.match(text)
    if not m:
        continue
    head, body = text[:m.end()], text[m.end():]
    s = SECOND.search(body, 0, 600)
    if s and re.search(r"^name:\s*\w", s.group(0), re.MULTILINE):
        body = body[:s.start()] + body[s.end():]
        body = re.sub(r"\n{3,}", "\n\n", body)
        f.write_text(head + body, encoding="utf-8")
        cleaned += 1
print(f"cleaned secondary frontmatter from {cleaned} packs")
