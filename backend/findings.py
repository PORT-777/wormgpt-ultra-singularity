# backend/findings.py
# 🔥😈 PORT 777 EVIL ☠️🔥👹 :: Findings Ledger â€” strix-style structured vulnerability ledger.
# ÙƒÙ„ Ø«ØºØ±Ø© Ù…Ø¤ÙƒØ¯Ø© ØªÙØ³Ø¬ÙŽÙ‘Ù„ Ø¨Ø¯Ø±Ø¬Ø© Ø®Ø·ÙˆØ±Ø© + Ø¯Ù„ÙŠÙ„ + Ø¥Ø«Ø¨Ø§Øª Ù…ÙÙ‡ÙˆÙ… + Ø¥ØµÙ„Ø§Ø­ØŒ Ù…Ø¹ ØªÙ‚Ø±ÙŠØ± md Ø¬Ø§Ù‡Ø².
# ÙˆØ­Ø¯Ø© Ù…Ø³ØªÙ‚Ù„Ø© ØªÙ…Ø§Ù…Ø§Ù‹: JSON Ø¹Ù„Ù‰ Ø§Ù„Ù‚Ø±ØµØŒ Ø¨Ø¯ÙˆÙ† Ø£ÙŠ Ø§Ø¹ØªÙ…Ø§Ø¯ÙŠØ§Øª â€” Ù„Ø§ ØªÙ…Ù†Ø¹ ÙˆÙ„Ø§ ØªØ±ÙØ¶ Ø£ÙŠ Ø´ÙŠØ¡.

from __future__ import annotations

import csv
import difflib
import io
import json
import re
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Set

_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_PATH = Path(__file__).resolve().parent / "data" / "findings.json"
_LOCK = threading.Lock()

# ---- strix report/writer.py security ports ---- #
# CWE-1236: Excel/LibreOffice/Sheets ØªÙ†ÙÙ‘Ø° Ø®Ù„ÙŠØ© Ø£ÙˆÙ„ Ø­Ø±ÙÙ‡Ø§ ÙˆØ§Ø­Ø¯ Ù…Ù† Ø¯ÙˆÙ„ â€”
# Ø¹Ù†Ø§ÙˆÙŠÙ† Ø§Ù„Ø«ØºØ±Ø§Øª Ø¨ØªÙŠØ¬ÙŠ Ù…Ù† Ù‡Ø¯Ù ÙŠØªØ­ÙƒÙ… ÙÙŠÙ‡ Ù…Ù‡Ø§Ø¬Ù…ØŒ ÙÙ„Ø§Ø²Ù… ØªØ¹Ø¯ÙŠÙ„ Ø¢Ù…Ù†.
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value: Any) -> str:
    """Ø®Ù„ÙŠØ© CSV Ù…Ø§ ØªÙ†ÙØ°Ø´ ÙƒÙÙˆØ±Ù…ÙŠÙ„Ø§ ÙÙŠ Ø¥ÙƒØ³Ù„ (strix csv_safe â€” CWE-1236)."""
    text = str(value if value is not None else "")
    if text.startswith(_CSV_FORMULA_PREFIXES):
        return "'" + text
    return text


def safe_fence(content: str) -> str:
    """Ø³ÙˆØ± Ø¨Ø§Ùƒ-ØªÙŠÙƒ Ø£Ø·ÙˆÙ„ Ù‚Ù„ÙŠÙ„Ø§Ù‹ Ù…Ù† Ø£ÙŠ ``` Ø¬ÙˆØ§ Ø§Ù„Ù…Ø­ØªÙˆÙ‰ (strix safe_fence) â€”
    Ø¹Ø´Ø§Ù† PoC Ù…ÙƒØªÙˆØ¨ Ù…Ù† Ø§Ù„Ø¯Ù…Ø§Øº/Ù…Ø¤Ø«Ø± Ù…Ù†Ù‡ Ù…Ù‡Ø§Ø¬Ù… ÙŠÙ‚Ø¯Ø± ÙŠÙƒØ³Ø± Ø¨Ù„ÙˆÙƒ Ø§Ù„Ù…Ø§Ø±ÙƒØ¯Ø§ÙˆÙ†."""
    longest = max((len(m.group()) for m in
                   re.finditer(r"`+", content or "")), default=0)
    return "`" * max(3, longest + 1)


def _load() -> List[Dict[str, Any]]:
    try:
        return json.loads(_PATH.read_text("utf-8")) or []
    except Exception:
        return []


def _save(items: List[Dict[str, Any]]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), "utf-8")


def normalize_severity(s: Any) -> str:
    s = str(s or "").strip().lower()
    if s in _SEV_ORDER:
        return s
    for k in _SEV_ORDER:
        if s and k.startswith(s[:3]):
            return k
    return "info"


def _norm_title(s: str) -> str:
    return re.sub(r"\s+", "", str(s or "").lower())[:80]


def _ascii_tokens(s: str) -> Set[str]:
    """Ø§Ù„ÙƒÙ„Ù…Ø§Øª Ø§Ù„ØªÙ‚Ù†ÙŠØ© Ø§Ù„Ù„Ø§ØªÙŠÙ†ÙŠØ© ÙÙŠ Ø§Ù„Ø¹Ù†ÙˆØ§Ù† (Ù„Ù„ØªØ´Ø§Ø¨Ù‡ Ø¹Ø¨Ø± Ø§Ù„Ù„ØºØ§Øª)."""
    return {t for t in re.findall(r"[a-zA-Z0-9]{3,}", s.lower())
            if t not in ("the", "and", "for", "via", "with")}


def _owasp_code(s: str) -> str:
    m = re.search(r"(API?\d+)", str(s or "").upper())
    return m.group(1) if m else ""


def _is_duplicate(item: Dict[str, Any], items: List[Dict[str, Any]]) -> bool:
    """Ù†ÙØ³ Ø§Ù„Ø¹Ù†ÙˆØ§Ù† Ù…ØªØ·Ø§Ø¨Ù‚ØŒ Ø£Ùˆ Ù†ÙØ³ Ø§Ù„Ø®Ø·ÙˆØ±Ø© ÙˆØªÙˆÙƒÙ†Ø² Ù„Ø§ØªÙŠÙ†ÙŠØ© ÙˆØ§Ø­Ø¯Ø© Ø¯Ø§Ø®Ù„ Ø§Ù„ØªØ§Ù†ÙŠØ©
    (ÙŠÙ„ØªÙ‚Ø· Ø§Ù„ØªÙƒØ±Ø§Ø± Ø¹Ø±Ø¨ÙŠ/Ø¥Ù†Ø¬Ù„ÙŠØ²ÙŠ Ù„Ù†ÙØ³ Ø§Ù„Ø«ØºØ±Ø©)."""
    key = _norm_title(item["title"])
    toks = _ascii_tokens(item["title"])
    for x in items:
        if _norm_title(x.get("title", "")) == key:
            return True
        btoks = _ascii_tokens(x.get("title", ""))
        if item["severity"] != x.get("severity") or not toks or not btoks:
            continue
        small, big = (toks, btoks) if len(toks) <= len(btoks) else (btoks, toks)
        same_cat = (_owasp_code(item.get("owasp"))
                    and _owasp_code(item.get("owasp"))
                    == _owasp_code(x.get("owasp")))
        if small <= big and (len(small) >= 2 or (len(small) == 1 and same_cat)):
            return True
        pa, pb = " ".join(sorted(toks)), " ".join(sorted(btoks))
        if difflib.SequenceMatcher(None, pa, pb).ratio() >= 0.85:
            return True
    return False


def add(finding: Dict[str, Any]) -> Dict[str, Any]:
    """Ø³Ø¬Ù‘Ù„ Ø«ØºØ±Ø© ÙˆØ§Ø­Ø¯Ø© â€” Ø±ÙØ¶ Ø£ÙŠ ØªÙƒØ±Ø§Ø± (Ø­ØªÙ‰ Ù„Ùˆ Ø§ØªÙƒØªØ¨ Ø¨Ù„ØºØ© ØªØ§Ù†ÙŠØ©)."""
    item = {
        "title": str(finding.get("title") or "untitled").strip()[:200],
        "severity": normalize_severity(finding.get("severity")),
        "target": str(finding.get("target") or "").strip()[:300],
        "owasp": str(finding.get("owasp") or "").strip()[:40],
        "evidence": str(finding.get("evidence") or "").strip()[:4000],
        "poc": str(finding.get("poc") or "").strip()[:4000],
        "remediation": str(finding.get("remediation") or "").strip()[:4000],
        # strix report schema (Ø§Ø®ØªÙŠØ§Ø±ÙŠ â€” ÙŠØ¹Ø±Ø¶ ÙÙŠ md ÙÙ‚Ø· Ù„Ùˆ Ù…ÙˆØ¬ÙˆØ¯)
        "impact": str(finding.get("impact") or "").strip()[:2000],
        "confidence": str(finding.get("confidence") or "").strip()[:30],
        "severity_change_conditions":
            str(finding.get("severity_change_conditions")
                or "").strip()[:1500],
        "assumptions": str(finding.get("assumptions") or "").strip()[:1500],
        "ts": time.time(),
    }
    with _LOCK:
        items = _load()
        if not _is_duplicate(item, items) and len(items) < 200:
            items.append(item)
            _save(items)
    return item


def clear() -> None:
    with _LOCK:
        _save([])


def list_all() -> List[Dict[str, Any]]:
    return sorted(_load(), key=lambda x: _SEV_ORDER.get(x.get("severity"), 9))


def counts() -> Dict[str, int]:
    c = {k: 0 for k in _SEV_ORDER}
    for f in _load():
        c[f.get("severity", "info")] = c.get(f.get("severity", "info"), 0) + 1
    return c


def report_md(task: str = "") -> str:
    """ØªÙ‚Ø±ÙŠØ± Ø§Ø®ØªØ¨Ø§Ø± Ø£Ù…Ù†ÙŠ Ø¬Ø§Ù‡Ø² (Ù†Ù…Ø· penetration_test_report.md)."""
    items = list_all()
    c = counts()
    lines = [
        "# ØªÙ‚Ø±ÙŠØ± Ø§Ø®ØªØ¨Ø§Ø± Ø£Ù…Ù†ÙŠ â€” 🔥😈 PORT 777 EVIL ☠️🔥👹",
        f"_ØªÙ… Ø¥Ù†Ø´Ø§Ø¤Ù‡: {time.strftime('%Y-%m-%d %H:%M')} â€” Ø§Ù„Ù†Ø·Ø§Ù‚: Ø«ØºØ±Ø§Øª Ù…Ø¤ÙƒØ¯Ø© Ù…Ù† Ù…Ù‡Ø§Ù… Ø§Ù„Ø¬Ù„Ø³Ø©_",
        "",
        "## Ø§Ù„Ù…Ù„Ø®Øµ Ø§Ù„ØªÙ†ÙÙŠØ°ÙŠ",
        "",
        f"- **Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ù†ØªØ§Ø¦Ø¬ Ø§Ù„Ù…Ø¤ÙƒØ¯Ø©:** {len(items)}",
        f"- **Ø­Ø±Ø¬Ø©:** {c['critical']} Â· **Ø¹Ø§Ù„ÙŠØ©:** {c['high']} Â· "
        f"**Ù…ØªÙˆØ³Ø·Ø©:** {c['medium']} Â· **Ù…Ù†Ø®ÙØ¶Ø©:** {c['low']} Â· **Ù…Ø¹Ù„ÙˆÙ…Ø©:** {c['info']}",
        "",
    ]
    if task:
        lines += [f"**Ø§Ù„Ù…Ù‡Ù…Ø©:** {task}", ""]
    if not items:
        lines += [
            "Ù„Ø§ ØªÙˆØ¬Ø¯ Ø«ØºØ±Ø§Øª Ù…Ø¤ÙƒØ¯Ø© Ù…Ø³Ø¬Ù„Ø© Ø­ØªÙ‰ Ø§Ù„Ø¢Ù†. Ù…Ù„Ø§Ø­Ø¸Ø© Ù…Ù‡Ù…Ø©: Ø®Ø±ÙˆØ¬ Ù†Ø¸ÙŠÙ ÙŠØ¹Ù†ÙŠ "
            "\"Ù…ÙÙŠØ´ Ø­Ø§Ø¬Ø© Ø§ØªØ£ÙƒØ¯Øª ÙÙŠ Ø§Ù„Ù„ÙŠ Ø§ØªÙØ­Øµ\" â€” Ù…Ø´ Ø¥Ø«Ø¨Ø§Øª Ø¥Ù† Ø§Ù„Ù‡Ø¯Ù Ø¢Ù…Ù† Ø¨Ø§Ù„ÙƒØ§Ù…Ù„.",
            "",
        ]
    for i, f in enumerate(items, 1):
        lines += [
            f"### {i}. [{f['severity'].upper()}] {f['title']}",
            "",
            f"- **Ø§Ù„Ù‡Ø¯Ù:** {f.get('target') or 'â€”'}",
            f"- **Ø§Ù„ØªØµÙ†ÙŠÙ:** {f.get('owasp') or 'â€”'}",
        ]
        if f.get("confidence"):
            lines.append(f"- **Ø§Ù„Ø«Ù‚Ø©:** {f['confidence']}")
        lines += ["", f"**Ø§Ù„Ø¯Ù„ÙŠÙ„:** {f.get('evidence') or 'â€”'}", ""]
        if f.get("impact"):
            lines += [f"**Ø§Ù„Ø£Ø«Ø±:** {f['impact']}", ""]
        if f.get("poc"):
            fence = safe_fence(f["poc"])
            lines += ["**Ø¥Ø«Ø¨Ø§Øª Ø§Ù„Ù…ÙÙ‡ÙˆÙ… (PoC):**", "", fence, f["poc"], fence, ""]
        if f.get("remediation"):
            lines += [f"**Ø§Ù„Ø¥ØµÙ„Ø§Ø­ Ø§Ù„Ù…Ù‚ØªØ±Ø­:** {f['remediation']}", ""]
        if f.get("severity_change_conditions"):
            lines += [f"**Ø¥ÙŠÙ‡ Ø§Ù„Ù„ÙŠ ÙŠØºÙŠÙ‘Ø± Ø§Ù„Ø¯Ø±Ø¬Ø© Ø¯ÙŠ:** "
                      f"{f['severity_change_conditions']}", ""]
        if f.get("assumptions"):
            lines += [f"**Ø§ÙØªØ±Ø§Ø¶Ø§Øª:** {f['assumptions']}", ""]
    # strix engagement port: Ø®Ø±ÙŠØ·Ø© Ø§Ù„ØªØºØ·ÙŠØ© (Ø§Ù„Ù…Ø³Ø§Ø­Ø© Ø§Ù„Ø³Ø§Ù„Ø¨Ø©) Ù‚Ø¨Ù„ Ø§Ù„Ø®Ø§ØªÙ…Ø©
    try:
        import engagement as _engagement
        cov_section = _engagement.section_md()
        if cov_section:
            lines += [cov_section.rstrip(), ""]
    except Exception:
        pass
    lines += [
        "## ØªØºØ·ÙŠØ© Ø¨ØµØ±Ø§Ø­Ø©",
        "- Ø§Ù„Ø³Ø¬Ù„ Ø¨ÙŠØ¬Ù…Ø¹ Ø§Ù„Ù„ÙŠ Ø§ØªØ¹Ø«Ø± Ø¹Ù„ÙŠÙ‡ ÙØ¹Ù„Ø§Ù‹ ÙÙŠ Ø§Ù„Ù…Ù‡Ø§Ù… â€” Ù…Ø´ Ø§Ø¯Ø¹Ø§Ø¡ Ù…Ø³Ø­ Ø´Ø§Ù…Ù„.",
        "- Ø§Ù„ÙØ¦Ø§Øª Ø§Ù„Ù„ÙŠ Ù…ØªÙØ­ØµØªØ´ ØªØ¹ØªØ¨Ø± ØºÙŠØ± Ù…ÙÙ‚ÙŠÙŽÙ‘Ù…Ø©ØŒ Ù…Ø´ \"Ù…ÙÙ‚ÙÙ„Ø©\".",
        "- ÙƒÙ„ PoC ÙŠØªØ·Ù„Ø¨Ø§Ø¯ Ø¥Ø¹Ø§Ø¯Ø© Ø§Ù„ØªØ­Ù‚Ù‚ Ù…Ù†Ù‡ Ù‚Ø¨Ù„ Ø§Ù„Ø§Ø³ØªØ®Ø¯Ø§Ù… Ø£Ù…Ø§Ù… Ø£ÙŠ Ø·Ø±Ù ØªØ§Ù„Øª.",
        "",
    ]
    return "\n".join(lines)


def parse_json_array(text: str) -> List[Any]:
    """Ø§Ø³ØªØ®Ø±Ø¬ JSON array Ù…Ù† Ù†Øµ Ø§Ù„Ø¯Ù…Ø§Øº (Ù…ØªØ³Ø§Ù…Ø­ Ù…Ø¹ fences ÙˆØ§Ù„Ø²ÙˆØ§Ø¦Ø¯)."""
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.MULTILINE).strip()
    start, end = t.find("["), t.rfind("]")
    if start >= 0 and end > start:
        t = t[start:end + 1]
    try:
        v = json.loads(t)
        return v if isinstance(v, list) else []
    except Exception:
        return []


_LEVEL_MAP = {"critical": "error", "high": "error",
              "medium": "warning", "low": "note", "info": "note"}


def sarif() -> Dict[str, Any]:
    """SARIF 2.1.0 â€” ØªÙƒØ§Ù…Ù„ Ù…Ø¨Ø§Ø´Ø± Ù…Ø¹ GitHub code scanning Ùˆ ASPM."""
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "🔥😈 PORT 777 EVIL ☠️🔥👹",
                "informationUri": "https://127.0.0.1:7777",
                "rules": [{"id": "WGT-VALIDATED-FINDING",
                           "name": "ValidatedSecurityFinding",
                           "shortDescription": {"text":
                               "Security finding validated with a PoC"}}],
            }},
            "results": [{
                "ruleId": "WGT-VALIDATED-FINDING",
                "level": _LEVEL_MAP.get(f.get("severity"), "note"),
                "message": {"text":
                            f"[{f.get('severity','info').upper()}] "
                            f"{f.get('title','')}"
                            + (f" â€” target: {f['target']}"
                               if f.get("target") else "")},
                "properties": {
                    "severity": f.get("severity", "info"),
                    "owasp": f.get("owasp", ""),
                    "evidence": f.get("evidence", ""),
                    "poc": f.get("poc", ""),
                    "remediation": f.get("remediation", ""),
                },
            } for f in list_all()],
        }],
    }


def report_csv() -> str:
    """CSV Ø¨ØªØ±Ù…ÙŠØ² UTF-8-BOM â€” ÙŠÙØªØ­ ÙÙŠ Excel Ø§Ù„Ø¹Ø±Ø¨ÙŠ Ù…Ø¨Ø§Ø´Ø±Ø© (Ù†Ù…Ø· findings.csv)."""
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow(["severity", "title", "target", "owasp",
                "evidence", "poc", "remediation", "recorded_at"])
    for f in list_all():
        w.writerow([
            csv_safe(f.get("severity", "info")),
            csv_safe(f.get("title", "")),
            csv_safe(f.get("target", "")),
            csv_safe(f.get("owasp", "")),
            csv_safe(f.get("evidence", "")),
            csv_safe(f.get("poc", "")),
            csv_safe(f.get("remediation", "")),
            time.strftime("%Y-%m-%d %H:%M:%S",
                          time.localtime(f.get("ts", time.time()))),
        ])
    return "\ufeff" + buf.getvalue()


def vuln_md(index: int) -> str:
    """Ø«ØºØ±Ø© ÙˆØ§Ø­Ø¯Ø© ÙƒÙ…Ù„Ù Ù…Ø³ØªÙ‚Ù„ (Ù†Ù…Ø· strix vulnerabilities/0001-title.md)."""
    items = list_all()
    if index < 1 or index > len(items):
        return ""
    f = items[index - 1]
    lines = [
        f"# [{f['severity'].upper()}] {f['title']}",
        "",
        f"- **Ø§Ù„Ù‡Ø¯Ù:** {f.get('target') or 'â€”'}",
        f"- **Ø§Ù„ØªØµÙ†ÙŠÙ:** {f.get('owasp') or 'â€”'}",
        f"- **Ù…Ø³Ø¬Ù„Ø©:** {time.strftime('%Y-%m-%d %H:%M', time.localtime(f.get('ts', time.time())))}",
        "",
        "## Ø§Ù„Ø¯Ù„ÙŠÙ„",
        "",
        f.get("evidence") or "â€”",
        "",
    ]
    if f.get("impact"):
        lines += ["## Ø§Ù„Ø£Ø«Ø±", "", f["impact"], ""]
    if f.get("poc"):
        fence = safe_fence(f["poc"])
        lines += ["## Ø¥Ø«Ø¨Ø§Øª Ø§Ù„Ù…ÙÙ‡ÙˆÙ… (PoC)", "", fence, f["poc"], fence, ""]
    if f.get("remediation"):
        lines += ["## Ø§Ù„Ø¥ØµÙ„Ø§Ø­ Ø§Ù„Ù…Ù‚ØªØ±Ø­", "", f["remediation"], ""]
    if f.get("severity_change_conditions"):
        lines += ["## Ø¥ÙŠÙ‡ Ø§Ù„Ù„ÙŠ ÙŠØºÙŠÙ‘Ø± Ø§Ù„Ø¯Ø±Ø¬Ø© Ø¯ÙŠ", "",
                  f["severity_change_conditions"], ""]
    if f.get("assumptions"):
        lines += ["## Ø§ÙØªØ±Ø§Ø¶Ø§Øª", "", f["assumptions"], ""]
    lines += ["---",
              "_Generated by 🔥😈 PORT 777 EVIL ☠️🔥👹 findings ledger "
              "(strix-style artifact)_"]
    return "\n".join(lines)


_SEV_COLOR = {"critical": "#ef4444", "high": "#f97316",
              "medium": "#f59e0b", "low": "#38bdf8", "info": "#9ca3af"}


def report_html() -> str:
    """ØªÙ‚Ø±ÙŠØ± HTML Ø°Ø§ØªÙŠ Ø§Ù„Ø§Ø­ØªÙˆØ§Ø¡ â€” Ø¯Ø§ÙƒÙ† RTL (Ù†Ù…Ø· ØªÙ‚Ø±ÙŠØ± strix Ø§Ù„ØªÙØ§Ø¹Ù„ÙŠ)."""
    items = list_all()
    c = counts()
    cards = []
    for i, f in enumerate(items, 1):
        col = _SEV_COLOR.get(f.get("severity"), "#9ca3af")
        cards.append(f"""
  <div style="border:1px solid {col}55;border-right:4px solid {col};
              background:#141420;border-radius:12px;padding:14px 16px;margin:10px 0">
    <div style="color:{col};font-weight:700;font-size:14px">
      [{i}] [{f.get('severity','info').upper()}] â€” {_esc(f.get('title',''))}</div>
    <div style="color:#9ca3af;font-size:11px;margin-top:4px">
      Ø§Ù„Ù‡Ø¯Ù: {_esc(f.get('target') or 'â€”')} Â· OWASP: {_esc(f.get('owasp') or 'â€”')}</div>
    <div style="color:#d1d5db;font-size:13px;margin-top:8px;white-space:pre-wrap">{_esc(f.get('evidence') or '')}</div>
    {f'<pre style="background:#0b0b12;border:1px solid #2a2a3a;border-radius:8px;padding:8px;color:#fca5a5;font-size:11px;overflow:auto">{_esc(f.get("poc") or "")}</pre>' if f.get('poc') else ''}
    {f'<div style="color:#34d399;font-size:12px;margin-top:6px">Ø§Ù„Ø¥ØµÙ„Ø§Ø­: {_esc(f.get("remediation") or "")}</div>' if f.get('remediation') else ''}
  </div>""")
    sev_row = " Â· ".join(
        f'<span style="color:{_SEV_COLOR[k]}">{k}: {c[k]}</span>'
        for k in ("critical", "high", "medium", "low", "info"))
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar"><head><meta charset="utf-8">
<title>🔥😈 PORT 777 EVIL ☠️🔥👹 â€” ØªÙ‚Ø±ÙŠØ± Ø§Ù„Ø§Ø®ØªØ¨Ø§Ø± Ø§Ù„Ø£Ù…Ù†ÙŠ</title></head>
<body style="background:#0b0b12;color:#e5e7eb;font-family:Segoe UI,Tahoma,sans-serif;
             max-width:860px;margin:0 auto;padding:24px">
<h1 style="color:#f87171;font-size:22px;margin:0 0 4px">ØªÙ‚Ø±ÙŠØ± Ø§Ù„Ø§Ø®ØªØ¨Ø§Ø± Ø§Ù„Ø£Ù…Ù†ÙŠ â€” 🔥😈 PORT 777 EVIL ☠️🔥👹</h1>
<div style="color:#6b7280;font-size:12px;margin-bottom:14px">
  ØªÙ… Ø§Ù„Ø¥Ù†Ø´Ø§Ø¡: {time.strftime('%Y-%m-%d %H:%M')} â€” Ø§Ù„Ù†ØªØ§Ø¦Ø¬ Ø§Ù„Ù…Ø¤ÙƒØ¯Ø©: {len(items)}</div>
<div style="font-size:13px;margin-bottom:10px">{sev_row}</div>
<div style="background:#11111c;border:1px solid #26263a;border-radius:10px;
            padding:10px 14px;color:#9ca3af;font-size:12px;margin:12px 0">
  âš  Ø®Ø±ÙˆØ¬ Ù†Ø¸ÙŠÙ = Â«Ù…ÙÙŠØ´ Ø«ØºØ±Ø© Ø§ØªØ£ÙƒØ¯Øª ÙÙŠ Ø§Ù„Ù„ÙŠ Ø§ØªÙØ­ØµÂ» â€” Ù…Ø´ Ø¥Ø«Ø¨Ø§Øª Ø¥Ù† Ø§Ù„Ù‡Ø¯Ù Ø¢Ù…Ù†.
  Ø§Ù„ÙØ¦Ø§Øª Ø§Ù„Ù„ÙŠ Ù…ØªÙØ­ØµØªØ´ ØºÙŠØ± Ù…ÙÙ‚ÙŠÙŽÙ‘Ù…Ø©.</div>
{''.join(cards) if cards else '<div style="color:#6b7280">Ø§Ù„Ø³Ø¬Ù„ ÙØ§Ø¶ÙŠ â€” Ù…ÙÙŠØ´ Ø«ØºØ±Ø§Øª Ù…Ø¤ÙƒØ¯Ø©.</div>'}
</body></html>"""


def _esc(s: Any) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def report_zip() -> bytes:
    """Ø­Ø²Ù…Ø© Ø§Ù„Ø£Ø±ØªÙŠÙØ§ÙƒØªØ³ ÙƒØ§Ù…Ù„Ø© (Ù†Ù…Ø· strix_runs/<run>/): ØªÙ‚Ø±ÙŠØ± md + html +
    vulnerabilities/*.md Ù„ÙƒÙ„ Ø«ØºØ±Ø© + findings.json + sarif + csv."""
    buf = io.BytesIO()
    items = list_all()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("penetration_test_report.md", report_md())
        z.writestr("report.html", report_html())
        z.writestr("findings.sarif",
                   json.dumps(sarif(), ensure_ascii=False, indent=2))
        z.writestr("findings.csv", report_csv())
        z.writestr("vulnerabilities.json",
                   json.dumps(items, ensure_ascii=False, indent=2))
        for i in range(1, len(items) + 1):
            slug = re.sub(r"[^\w-]+", "-", items[i - 1].get("title", "vuln")
                          )[:40].strip("-") or "vuln"
            z.writestr(f"vulnerabilities/{i:04d}-{slug}.md", vuln_md(i))
        try:
            import engagement as _engagement
            z.writestr("engagement_state.json",
                       json.dumps(_engagement.summary(),
                                  ensure_ascii=False, indent=2))
        except Exception:
            pass
    return buf.getvalue()
