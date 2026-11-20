# backend/tools/report_builder.py
# Language: Python 3 | Runtime: CPython | Target: Windows 11
# 🔥😈 PORT 777 EVIL ☠️🔥👹 :: ReportBuilder â€” strix-style findings report compiler.
# Ø§Ù„ÙˆØ±ÙˆØ¯: findings JSON (Ù‚Ø§Ø¦Ù…Ø©)ØŒ ÙŠØ¨Ù†ÙŠ ØªÙ‚Ø±ÙŠØ± markdown + JSON ÙƒÙ„Ø§Ù‡Ù…Ø§ ÙÙŠ reports/.
from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from .base import Tool

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


class ReportBuilder(Tool):
    """ØªØ¬Ù…ÙŠØ¹ Ù†ØªØ§Ø¦Ø¬ Ø§Ù„ØªØ­Ù„ÙŠÙ„ (findings) ÙÙŠ ØªÙ‚Ø±ÙŠØ± Ù…Ù†Ø¸Ù‘Ù… Ø¯Ø§Ø®Ù„ reports/."""

    name = "ReportBuilder"
    description = (
        "Compile a structured findings/analysis report: takes findings as "
        "JSON list [{title, target, severity, evidence, remediation}], "
        "writes a markdown + JSON report under workspace/reports/, and "
        "returns the report summary + paths."
    )
    example = {
        "title": "PE tamper scan of target.exe",
        "findings": [
            {"title": "LSB rotated header", "target": "target.exe",
             "severity": "high", "evidence": "e_lfanbl mismatch at 0x3C",
             "remediation": "rebuild headers"}
        ],
    }

    async def run(self, **kwargs: Any) -> str:
        title = str(kwargs.get("title") or "🔥😈 PORT 777 EVIL ☠️🔥👹 Recon Report").strip()
        raw = kwargs.get("findings")
        if isinstance(raw, str):
            try:
                findings = json.loads(raw)
            except Exception:
                return "ERROR: findings must be a JSON list or dict"
        elif isinstance(raw, list):
            findings = raw
        else:
            findings = []
        if isinstance(findings, dict):
            findings = [findings]

        rows = []
        for f in findings[:60]:
            if isinstance(f, dict):
                sev = str(f.get("severity", "info")).lower()
                sev = sev if sev in SEVERITY_ORDER else "info"
                rows.append({
                    "title": str(f.get("title", "untitled finding"))[:200],
                    "target": str(f.get("target", "-"))[:120],
                    "severity": sev,
                    "evidence": str(f.get("evidence", ""))[:600],
                    "remediation": str(f.get("remediation", ""))[:400],
                })

        rows.sort(key=lambda r: SEVERITY_ORDER[r["severity"]])
        counts: Dict[str, int] = {}
        for r in rows:
            counts[r["severity"]] = counts.get(r["severity"], 0) + 1

        ts = time.strftime("%Y%m%d-%H%M%S")
        reports_dir = Tool.safe_path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        slug = "".join(c if c.isalnum() else "_" for c in title)[:40]
        md_path = reports_dir / f"report_{ts}{('_' + slug) if slug else ''}.md"
        json_path = md_path.with_suffix(".json")

        md: List[str] = [
            f"# {title}", "",
            f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')} by "
            f"🔥😈 PORT 777 EVIL ☠️🔥👹 ReportBuilder_", "",
            "## Summary", "",
            f"- Findings: **{len(rows)}** â€” "
            + " / ".join(f"{k}: {v}" for k, v in
                         sorted(counts.items(), key=lambda kv: SEVERITY_ORDER[kv[0]]))
            or "(none)", "",
            "| Severity | Title | Target |",
            "|----------|-------|--------|",
        ]
        for r in rows:
            md.append(f"| {r['severity'].upper()} | {r['title']} | "
                      f"{r['target']} |")
        md += ["", "## Findings detail", ""]
        for i, r in enumerate(rows, 1):
            md += [
                f"### {i}. [{r['severity'].upper()}] {r['title']}",
                f"- target: {r['target']}",
                f"- evidence: {r['evidence'] or '(none recorded)'}",
                f"- remediation: {r['remediation'] or '(none suggested)'}",
                "",
            ]

        md_path.write_text("\n".join(md), encoding="utf-8")
        json_path.write_text(json.dumps(
            {"title": title, "generated": ts, "counts": counts,
             "findings": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8")

        top = ", ".join(f"{r['severity'].upper()}:{r['title']}"
                        for r in rows[:3]) or "no findings"
        return (f"Report written: {md_path.name} + {json_path.name} "
                f"({len(rows)} findings; top: {top})")
