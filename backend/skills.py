"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Skill packs â€” the agent's SAFE self-extension axis v8.

Two pack formats (both in backend/skills_packs/):
  1. *.yaml  â€” original pack style (name/description/instructions).
  2. *.md    â€” SKILL.md style (superpowers/mattpocock): YAML frontmatter
               between `---` fences, then a markdown body.

Frontmatter keys:
  name          pack name (default: file stem)
  description   one-line purpose
  trigger_when  list (or comma string) of keywords -> model-invoked:
                pack is injected ONLY when the task matches. Omit or set
                `always: true` for always-on packs.
  always        true => always injected regardless of task.

Design boundary (intentional, unchanged): packs are PLAYBOOK PROMPTS the
agent follows. They never cause refusals â€” they add method, not limits.
Code/behavior changes still go through ProposalChange (human-approved).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import configs as config

log = logging.getLogger("skills")

try:
    import yaml
except ImportError:       # degrades gracefully: no packs -> plain engine
    yaml = None

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def _kw_list(raw) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [p.strip() for p in re.split(r"[,;|]", raw) if p.strip()]
    return [str(k).lower() for k in raw if str(k).strip()]


def _normalize(data: Dict, instructions: str) -> Dict:
    return {
        "name": str(data.get("name") or data.get("pack") or "").strip(),
        "description": str(data.get("description", "")).strip(),
        "instructions": instructions.strip()[:config.MAX_SKILL_CHARS],
        "trigger_when": _kw_list(data.get("trigger_when")),
        "always": str(data.get("always", "")).lower() in ("true", "yes", "1")
                  or data.get("always") is True,
    }


def _load_pack(path: Path) -> Dict:
    text = path.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    if path.suffix.lower() == ".md":
        m = _FM_RE.match(text)
        if not m or yaml is None:
            raise ValueError("md pack needs YAML frontmatter")
        docs = list(yaml.safe_load_all(m.group(1)))
        data = docs[0] if docs else {}
        if not isinstance(data, dict):
            raise ValueError("md frontmatter must be a mapping")
        body = re.sub(r"^#\s+.*\n", "", m.group(2), count=1)   # drop title line
        return _normalize(data, body)
    # original yaml pack style
    if yaml is None:
        return {}
    docs = list(yaml.safe_load_all(text))
    data = docs[0] if docs else {}
    if not isinstance(data, dict):
        raise ValueError("pack root must be a mapping")
    return _normalize(data, str(data.get("instructions", "")))


def load_packs() -> List[Dict]:
    """Read every pack (*.yaml | *.md); invalid files are skipped, never fatal."""
    if not config.SKILLS_ENABLED or yaml is None:
        return []
    packs: List[Dict] = []
    seen: set[str] = set()
    for f in sorted(config.SKILLS_DIR.rglob("*")):
        if f.suffix.lower() not in (".yaml", ".yml", ".md") or not f.is_file():
            continue
        if f.name.lower() == "readme.md":
            continue
        try:
            pack = _load_pack(f)
            if not pack["instructions"]:
                raise ValueError("pack has no instructions")
            if not pack["name"]:
                pack["name"] = f.stem
            if pack["name"] in seen:
                # Same pack present as .yaml and .md (or in two library
                # folders): load it once so the prompt and tests stay stable.
                log.debug("duplicate skill pack skipped: %s (%s)",
                          pack["name"], f.name)
                continue
            seen.add(pack["name"])
            packs.append(pack)
        except Exception as exc:
            log.warning("skill pack skipped (%s): %s", f.name, exc)
    return packs


# Single generic words appear in hundreds of packs and made selection almost
# random ("write a PE parser" matched "arbitrary-write-to-rce").
_GENERIC_TRIGGERS = {
    "app", "tool", "script", "program", "code", "file", "web", "help",
    "work", "task", "build", "write", "make", "use", "run", "agent",
}


def _trigger_score(text: str, triggers: List[str]) -> float:
    """Specificity-weighted relevance. Word boundaries stop 'write' from
    matching 'rewrite'; phrases outweigh single words; generic words are weak."""
    score = 0.0
    for raw in triggers:
        key = str(raw).strip().lower()
        if not key:
            continue
        words = re.findall(r"\w+", key, re.UNICODE)
        if len(words) >= 2:
            hit = key in text
        else:
            # optional plural suffix keeps "ioc" matching "IOCs" without
            # reintroducing substring matches like "write" -> "rewrite".
            hit = bool(re.search(r"(?<!\w)" + re.escape(key)
                                 + r"(?:es|s)?(?!\w)", text, re.UNICODE))
        if not hit:
            continue
        if len(words) >= 2:
            score += 3.0 + min(len(key), 30) / 30.0
        elif key in _GENERIC_TRIGGERS:
            score += 0.25
        else:
            score += 1.0 + min(len(key), 16) / 16.0
    return score


def relevant_packs(task: Optional[str],
                   cap: Optional[int] = None) -> List[Dict]:
    """Always-on packs first, then task-matched (model-invoked) packs,
    ranked by trigger hits and capped (default MAX_SKILL_PACKS, or the
    depth-specific cap) â€” so even a large library (strix knowledge
    packs) can never overflow context.

    Never refuses: relevance filters WHAT method guidance loads â€” the
    agent always executes the task it was given.
    """
    packs = load_packs()
    cap = int(cap or config.MAX_SKILL_PACKS)
    if not task:
        return [p for p in packs if p["always"]][:cap]
    text = task.lower()

    always = [p for p in packs if p["always"]]
    scored = []
    for p in packs:
        if p["always"]:
            continue
        value = _trigger_score(text, p["trigger_when"])
        if value > 0:
            scored.append((value, p))
    scored.sort(key=lambda item: (-item[0], item[1]["name"]))
    auto = [p for _, p in scored]
    cap2 = max(0, cap - len(always))
    return always + auto[:cap2]


def skills_block(task: Optional[str] = None,
                 cap: Optional[int] = None,
                 total: Optional[int] = None) -> str:
    """The prompt section injected into the engine's system prompt.
    cap/total let the engine apply its scan-depth budget."""
    packs = relevant_packs(task, cap=cap)
    budget = int(total or config.MAX_SKILL_TOTAL)
    if not packs:
        return ""
    sections, used = [], 0
    for p in packs:
        body = p["instructions"]
        room = budget - used
        if room <= 200:
            break
        if len(body) > room:
            body = body[:room]
        used += len(body)
        label = f"### skill pack: {p['name']}"
        if p["description"]:
            label += f" â€” {p['description']}"
        sections.append(f"{label}\n{body}")
    return ("\n## Loaded skill packs (follow these playbooks)\n"
            + "\n\n".join(sections) + "\n")
