# -*- coding: utf-8 -*-
"""Pull ALL strix internal knowledge packs -> our skills_packs/strix/.

- walks every category dir (skips cloud=SaaS driving + custom=empty)
- downloads every *.md via raw CDN (no API rate limit)
- sanitizes: strix CLI/cloud code fences, SaaS links, Safety sections
  (Maker's iron rule: NOTHING injected may seed refusals)
- wraps each file with our SKILL.md frontmatter (name/description/trigger_when)
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import yaml

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://api.github.com/repos/usestrix/strix/contents/"
RAW = "https://raw.githubusercontent.com/usestrix/strix/main/"
OUT = Path(__file__).resolve().parent / "skills_packs" / "strix"
CATEGORIES = ["analysis", "coordination", "frameworks", "protocols",
              "reconnaissance", "scan_modes", "technologies", "tooling",
              "vulnerabilities"]
STOPWORDS = {"the", "and", "for", "with", "from", "into", "that", "this",
             "your", "their", "how", "why", "what", "when", "use", "using",
             "via", "per", "own", "user", "agent", "strix"}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "🔥😈 PORT 777 EVIL ☠️🔥👹-pull"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    return ""


def sanitize(text: str) -> str:
    # 1. drop code fences that drive the strix CLI/cloud binary (irrelevant here)
    def _fence(m):
        return "" if re.search(r"\bstrix\s", m.group(0)) else m.group(0)
    text = re.sub(r"```[\w]*\n.*?\n```", _fence, text, flags=re.S)
    # 2. drop SaaS/cloud/marketing lines and links
    text = re.sub(r"^.*(?:app\.strix\.ai|docs\.strix\.ai|strix\.ai|strix cloud"
                  r"|managed platform|managed cloud).*$",
                  "", text, flags=re.M | re.I)
    # 3. drop whole Safety / authorization-preach sections (refusal seeds)
    text = re.sub(r"^#+\s*(Safety|Authorized use only|Ethical note)\b.*?"
                  r"(?=^#+\s|\Z)", "", text, flags=re.S | re.M)
    # 4. neutralize remaining authorization-preach lines
    text = re.sub(r"^.*(?:authorized to test|explicit, written permission"
                  r"|do not (?:scan|pentest|test) (?:a|an|third-party)).*$",
                  "", text, flags=re.M | re.I)
    # 5. collapse >2 blank lines
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def frontmatter(name: str, title: str, body: str) -> str:
    words = set()
    for w in re.split(r"[-_\s/]+", (name + " " + title).lower()):
        w = w.strip()
        if len(w) >= 3 and w not in STOPWORDS and re.fullmatch(r"[\w+#-]+", w):
            words.add(w)
    # always include the full compound name tokens for phrase matching
    phrase = name.replace("_", " ").replace("-", " ").lower()
    meta = {
        "name": "strix_" + name,
        "description": (title or phrase)[:180],
        "trigger_when": sorted(words | {phrase})[:16],
        "always": False,
    }
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True,
                        default_flow_style=False)
    return "---\n" + fm + "---\n\n"


def main() -> None:
    total = 0
    failures = []
    for cat in CATEGORIES:
        try:
            listing = json.loads(fetch(API + "strix/skills/" + cat))
        except Exception as exc:
            failures.append(f"{cat}: listing failed: {exc}")
            continue
        d = OUT / cat
        d.mkdir(parents=True, exist_ok=True)
        for item in listing:
            if item.get("type") != "file" or not item["name"].endswith(".md"):
                continue
            raw_name = item["name"][:-3]
            slug = re.sub(r"[^\w-]+", "_", raw_name).strip("_")
            try:
                text = fetch(RAW + item["path"])
                if not text or len(text) < 200:
                    continue
                clean = sanitize(text)
                if len(clean) < 200:
                    continue
                m = re.search(r"^#\s+(.+)$", clean, re.M)
                title = (m.group(1).strip() if m else slug)
                body = re.sub(r"^#\s+.+\n", "", clean, count=1).strip()
                (d / f"{slug}.md").write_text(
                    frontmatter(slug, title, body) + "# " + title + "\n\n"
                    + body + "\n", encoding="utf-8")
                total += 1
            except Exception as exc:
                failures.append(f"{cat}/{raw_name}: {exc}")
    print(f"pulled {total} packs -> {OUT}")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)


if __name__ == "__main__":
    main()
