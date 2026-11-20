"""Generate frontend plugin brand icon module from Simple Icons (CC0)."""

import json
import re
import urllib.request
from pathlib import Path

CDN = "https://cdn.jsdelivr.net/npm/simple-icons@latest"
OUT = Path(__file__).resolve().parent.parent / "frontend" / "src" / "components" / "pluginIcons.js"

MAPPING = {
    # ai
    "claude": "claude",
    "openai": "openai",
    "gemini": "googlegemini",
    "grok": "x",
    "deepseek": "deepseek",
    "mistral": "mistralai",
    "perplexity": "perplexity",
    # social
    "instagram": "instagram",
    "facebook": "facebook",
    "tiktok": "tiktok",
    "youtube": "youtube",
    "linkedin": "linkedin",
    "whatsapp": "whatsapp",
    "mastodon": "mastodon",
    "bluesky": "bluesky",
    "threads": "threads",
    "twitch": "twitch",
    "twitter": "x",
    "reddit": "reddit",
    "discord": "discord",
    "telegram": "telegram",
    # productivity
    "notion": "notion",
    "jira": "jira",
    "obsidian": "obsidian",
    "google_drive": "googledrive",
    "google_sheets": "googlesheets",
    "google_calendar": "googlecalendar",
    "trello": "trello",
    "airtable": "airtable",
    "linear": "linear",
    # communication
    "slack": "slack",
    "teams": "microsoftteams",
    "twilio": "twilio",
    "sendgrid": "sendgrid",
    "matrix": "matrix",
    # devops
    "github": "github",
    "gitlab": "gitlab",
    "jenkins": "jenkins",
    "vercel": "vercel",
    "sentry": "sentry",
    "datadog": "datadog",
    # cloud
    "aws": "amazonwebservices",
    "azure": "microsoftazure",
    "cloudflare": "cloudflare",
    "digitalocean": "digitalocean",
    # security
    "virustotal": "virustotal",
    # siem
    "splunk": "splunk",
    "elastic": "elastic",
}

# Brands whose Simple Icons entry dropped the published hex.
COLORS = {
    "amazonwebservices": "FF9900",
    "microsoftazure": "0078D4",
    "linkedin": "0A66C2",
    "openai": "10A37F",
    "sendgrid": "1A82E2",
    "slack": "4A154B",
    "microsoftteams": "6264A7",
    "twilio": "F22F46",
}

GLYPHS = {
    "webreader": ("CC0000", "globe"),
    "cohere": ("39594D", "layers"),
    "pushover": ("2B7FFF", "send"),
    "shodan": ("CC0000", "globe"),
    "abuseipdb": ("E0552B", "shield"),
    "greynoise": ("4A90E2", "activity"),
    "misp": ("2C3E50", "share"),
    "thehive": ("FFB000", "graph"),
    "malwarebazaar": ("6D28D9", "database"),
    "urlhaus": ("C0392B", "link"),
    "opencti": ("0F62FE", "target"),
    "nvd": ("1A4B8C", "shield"),
    "cisa_kev": ("002D72", "shield"),
    "hibp": ("C62828", "lock"),
    "otx": ("00A6A6", "target"),
    "sentinel": ("0078D4", "target"),
    "wazuh": ("3AB6EC", "shield"),
    "graylog": ("FF3633", "file"),
    "email": ("CC0000", "send"),
    "template_plugin": ("CC0000", "plug"),
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def main() -> None:
    meta = json.loads(fetch(f"{CDN}/data/simple-icons.json"))
    by_slug = {row["slug"]: row for row in meta}

    brands = {}
    for pid, slug in MAPPING.items():
        try:
            svg = fetch(f"{CDN}/icons/{slug}.svg")
        except Exception as exc:
            print(f"!! {pid} ({slug}) fetch failed: {exc}")
            continue
        paths = re.findall(r'<path[^>]*\sd="([^"]+)"', svg)
        if not paths:
            print(f"!! {pid} ({slug}) has no path data")
            continue
        hex_ = (
            COLORS.get(slug)
            or by_slug.get(slug, {}).get("hex")
            or "888888"
        ).upper()
        brands[pid] = {"hex": "#" + hex_, "paths": paths}

    # anything mapped but failed falls back to a glyph
    for pid, slug in MAPPING.items():
        if pid in brands:
            continue
        GLYPHS.setdefault(pid, ("CC0000", "plug"))

    lines = [
        "// Auto-generated from Simple Icons (CC0) — brand marks for every plugin.",
        "// Do not hand-edit; re-run backend/_gen_icons.py to refresh.",
        "",
        "export const BRAND_ICONS = {",
    ]
    for pid in sorted(brands):
        entry = brands[pid]
        paths = ", ".join(json.dumps(p) for p in entry["paths"])
        lines.append(f'  {json.dumps(pid)}: {{ hex: "{entry["hex"]}", paths: [{paths}] }},')
    lines.append("};")
    lines.append("")
    lines.append("export const GLYPH_ICONS = {")
    for pid in sorted(GLYPHS):
        hex_, icon = GLYPHS[pid]
        lines.append(f'  {json.dumps(pid)}: {{ hex: "#{hex_}", icon: {json.dumps(icon)} }},')
    lines.append("};")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} — {len(brands)} brand icons, {len(GLYPHS)} glyph fallbacks")


if __name__ == "__main__":
    main()
