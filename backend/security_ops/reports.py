# backend/security_ops/reports.py
# Report generation for the CyberOps toolkit: one renderer that emits
# Markdown or JSON for executive, technical, threat-hunt, board, lessons-
# learned and compliance audiences. Also builds incident narratives and
# evidence chain-of-custody tables.

from __future__ import annotations

import datetime as _dt
import hashlib
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .util import (hash_bytes, json_dumps, normalize_severity, now_iso,
                   severity_rank, write_artifact)

REPORT_KINDS = ("technical", "executive", "board", "hunt", "lessons", "compliance")

AUDIENCE = {
    "technical": "SOC analysts, incident responders and detection engineers",
    "executive": "CISO, security leadership and engineering managers",
    "board": "Board of directors / risk committee",
    "hunt": "Threat hunters and detection engineering",
    "lessons": "IR team and process owners",
    "compliance": "GRC, audit and compliance teams",
}


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _sev(value: Any) -> str:
    return normalize_severity(value)


def _sev_counts(findings: Sequence[Any]) -> Dict[str, int]:
    counts = Counter(_sev(f.get("severity", "info")) if isinstance(f, dict) else "info"
                     for f in findings)
    order = ["critical", "high", "medium", "low", "info"]
    return {k: counts.get(k, 0) for k in order}


def _finding_rows(findings: Sequence[Any], limit: int = 500) -> List[Dict[str, Any]]:
    rows = []
    for f in findings[:limit]:
        if isinstance(f, dict):
            rows.append({
                "severity": _sev(f.get("severity", "info")),
                "title": str(f.get("finding") or f.get("title") or f.get("name") or "finding"),
                "detail": str(f.get("detail") or f.get("description") or f.get("evidence") or ""),
                "mitre": ", ".join(_as_list(f.get("mitre", f.get("techniques", [])))),
            })
        else:
            rows.append({"severity": "info", "title": str(f), "detail": "", "mitre": ""})
    rows.sort(key=lambda r: severity_rank(r["severity"]))
    return rows


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    def cell(v: Any) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")[:300]
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(cell(c) for c in row) + " |")
    return "\n".join(out)


def _ioc_flat(iocs: Any) -> List[Dict[str, str]]:
    if not isinstance(iocs, dict):
        return []
    cats = iocs.get("categories", iocs)
    out = []
    if not isinstance(cats, dict):
        return out
    for kind, values in cats.items():
        for v in _as_list(values):
            if str(v).strip():
                out.append({"type": str(kind), "value": str(v)})
    return out


def _mitre_rows(mitre: Any) -> List[Dict[str, str]]:
    rows = []
    for item in _as_list(mitre):
        if isinstance(item, dict):
            rows.append({"id": str(item.get("id", "")),
                         "name": str(item.get("name", "")),
                         "tactic": str(item.get("tactic", ""))})
        elif isinstance(item, str):
            rows.append({"id": item, "name": "", "tactic": ""})
    return rows


def build_report(kind: str = "technical", title: str = "", subject: str = "",
                 findings: Sequence[Any] = (), iocs: Any = None,
                 mitre: Any = None, timeline: Sequence[Any] = (),
                 metadata: Optional[Dict[str, Any]] = None,
                 recommendations: Sequence[str] = (),
                 evidence: Sequence[Any] = (),
                 fmt: str = "markdown") -> Dict[str, Any]:
    """Render a report for the requested audience.

    Returns a dict with ``content`` (the rendered text/JSON), ``filename``,
    and the structured pieces used. Nothing is written unless ``save=True``
    is passed to :func:`generate_report`.
    """
    kind = (kind or "technical").lower()
    if kind not in REPORT_KINDS:
        kind = "technical"
    meta = dict(metadata or {})
    rows = _finding_rows(findings)
    counts = _sev_counts(findings)
    flat_iocs = _ioc_flat(iocs)
    mitre_rows = _mitre_rows(mitre)
    timeline = [t for t in timeline if t]
    meta.setdefault("generated_at", now_iso())
    meta.setdefault("report_kind", kind)
    meta.setdefault("audience", AUDIENCE[kind])
    meta.setdefault("classification", "TLP:AMBER")
    title = title or _default_title(kind, subject)
    recs = [str(r) for r in recommendations if str(r).strip()] or _default_recs(kind, counts)

    sections = {
        "summary": _summary(kind, subject, counts, len(flat_iocs), len(mitre_rows)),
        "findings": rows,
        "iocs": flat_iocs,
        "mitre": mitre_rows,
        "timeline": timeline,
        "recommendations": recs,
    }
    if fmt.lower() in ("json", "raw"):
        payload = {
            "title": title, "kind": kind, "metadata": meta,
            "severity_counts": counts, **sections,
            "evidence": _evidence_rows(evidence),
        }
        content = json_dumps(payload)
        filename = f"cyberops_{kind}_{_stamp()}.json"
        return {"format": "json", "filename": filename, "content": content,
                "title": title, "kind": kind, "severity_counts": counts,
                "sections": payload}
    content = _render_markdown(kind, title, subject, meta, counts, rows,
                               flat_iocs, mitre_rows, timeline, recs, evidence)
    filename = f"cyberops_{kind}_{_stamp()}.md"
    return {"format": "markdown", "filename": filename, "content": content,
            "title": title, "kind": kind, "severity_counts": counts,
            "sections": sections}


def generate_report(**kwargs: Any) -> Dict[str, Any]:
    """Build (and optionally save) a report. Extra keys: save, allow_host."""
    save = bool(kwargs.pop("save", False))
    allow_host = bool(kwargs.pop("allow_host", False))
    result = build_report(**kwargs)
    if save:
        path = write_artifact(result["filename"], result["content"],
                              kind="reports", allow_host=allow_host)
        result["path"] = path
    return result


def _default_title(kind: str, subject: str) -> str:
    base = {
        "technical": "Technical Analysis Report",
        "executive": "Executive Security Report",
        "board": "Board Security Briefing",
        "hunt": "Threat Hunt Report",
        "lessons": "Incident Lessons Learned",
        "compliance": "Compliance Findings Report",
    }[kind]
    return f"{base}: {subject}" if subject else base


def _default_recs(kind: str, counts: Dict[str, int]) -> List[str]:
    recs = []
    if counts["critical"] or counts["high"]:
        recs.append("Contain critical/high findings immediately and preserve evidence.")
    if kind == "technical":
        recs += ["Add detection coverage for observed techniques.",
                 "Hunt for the same tradecraft on peer systems.",
                 "Track remediation in the ticketing system with owners."]
    elif kind == "executive":
        recs += ["Approve emergency remediation resources.",
                 "Confirm regulatory notification requirements with legal.",
                 "Schedule an after-action review."]
    elif kind == "board":
        recs += ["Endorse the containment plan and decision checkpoints.",
                 "Confirm risk acceptance for any deferred remediation.",
                 "Request a post-incident assurance update."]
    elif kind == "hunt":
        recs += ["Convert hypotheses into scheduled detections.",
                 "Expand hunt scope to adjacent identities and hosts.",
                 "Record negative results to close hypotheses."]
    elif kind == "lessons":
        recs += ["Assign owners and due dates to process fixes.",
                 "Update playbooks with the validated timeline.",
                 "Run a tabletop to test the improvements."]
    elif kind == "compliance":
        recs += ["Collect evidence for mapped controls.",
                 "Document exceptions with compensating controls.",
                 "Schedule the follow-up audit checkpoint."]
    return recs or ["Continue monitoring; no immediate action required."]


def _summary(kind: str, subject: str, counts: Dict[str, int], ioc_count: int,
             mitre_count: int) -> str:
    total = sum(counts.values())
    lead = subject or "the analysed activity"
    if kind == "board":
        return (f"Security review of {lead}. {total} findings were recorded: "
                f"{counts['critical']} critical, {counts['high']} high. "
                f"Leadership decision may be required for containment and communication.")
    if kind == "executive":
        return (f"{total} findings were identified for {lead} "
                f"({counts['critical']} critical, {counts['high']} high, "
                f"{counts['medium']} medium). {ioc_count} indicators and "
                f"{mitre_count} ATT&CK techniques were extracted.")
    if kind == "hunt":
        return (f"Hunt over {lead} produced {total} findings, {ioc_count} indicators and "
                f"{mitre_count} mapped techniques. Negative results are retained for coverage.")
    if kind == "lessons":
        return (f"Review of {lead} covering detection, response and coordination. "
                f"{total} findings inform the improvement backlog.")
    if kind == "compliance":
        return (f"Technical findings for {lead} mapped to control requirements. "
                f"{total} findings require evidence or remediation tracking.")
    return (f"Technical analysis of {lead}. {total} findings "
            f"({counts['critical']} critical, {counts['high']} high), "
            f"{ioc_count} indicators, {mitre_count} ATT&CK techniques.")


def _render_markdown(kind: str, title: str, subject: str, meta: Dict[str, Any],
                     counts: Dict[str, int], rows: List[Dict[str, Any]],
                     iocs: List[Dict[str, str]], mitre: List[Dict[str, str]],
                     timeline: Sequence[Any], recs: Sequence[str],
                     evidence: Sequence[Any]) -> str:
    lines = [f"# {title}", ""]
    lines.append(f"**Classification:** {meta.get('classification', 'TLP:AMBER')}  ")
    lines.append(f"**Generated:** {meta.get('generated_at', now_iso())}  ")
    lines.append(f"**Audience:** {meta.get('audience', AUDIENCE[kind])}")
    for key in ("author", "case_id", "source", "system"):
        if meta.get(key):
            lines.append(f"**{key.replace('_', ' ').title()}:** {meta[key]}")
    lines += ["", "---", "", "## Executive Summary", "",
              _summary(kind, subject, counts, len(iocs), len(mitre)), ""]
    lines += ["### Severity Breakdown", "",
              _table(["Severity", "Count"],
                     [[k.title(), counts[k]] for k in ("critical", "high", "medium", "low", "info")]),
              ""]
    if kind in ("technical", "hunt", "compliance"):
        lines += ["## Findings", ""]
        if rows:
            lines += [_table(["Severity", "Finding", "Detail", "ATT&CK"],
                             [[r["severity"].upper(), r["title"], r["detail"], r["mitre"]]
                              for r in rows]), ""]
        else:
            lines += ["No findings were recorded.", ""]
    else:
        top = rows[:10]
        if top:
            lines += ["## Key Issues", "",
                      _table(["Severity", "Issue"],
                             [[r["severity"].upper(), r["title"]] for r in top]), ""]
    if timeline and kind in ("technical", "hunt", "lessons"):
        lines += ["## Timeline", ""]
        trows = []
        for item in timeline[:100]:
            if isinstance(item, dict):
                trows.append([item.get("time") or item.get("timestamp") or item.get("ts") or "",
                              item.get("event") or item.get("description") or
                              item.get("finding") or str(item)[:160]])
            else:
                trows.append(["", str(item)])
        lines += [_table(["Time", "Event"], trows), ""]
    if iocs:
        lines += ["## Indicators of Compromise", ""]
        grouped: Dict[str, List[str]] = {}
        for ioc in iocs:
            grouped.setdefault(ioc["type"], []).append(ioc["value"])
        for typ, values in grouped.items():
            lines.append(f"**{typ}** ({len(values)})")
            lines += [f"- `{v}`" for v in values[:50]]
            if len(values) > 50:
                lines.append(f"- ... and {len(values) - 50} more")
            lines.append("")
    if mitre and kind in ("technical", "hunt", "executive"):
        lines += ["## ATT&CK Techniques", "",
                  _table(["ID", "Name", "Tactic"],
                         [[m["id"], m["name"], m["tactic"]] for m in mitre[:80]]), ""]
    if kind == "lessons":
        lines += ["## What Worked", "",
                  "- Detection and escalation occurred through the documented channel.",
                  "- Evidence was preserved before remediation where possible.", "",
                  "## What Needs Improvement", ""]
        lines += [f"- {r}" for r in recs] or ["- Complete the improvement backlog."]
        lines.append("")
    else:
        lines += ["## Recommendations", ""]
        lines += [f"{i}. {r}" for i, r in enumerate(recs, 1)]
        lines.append("")
    ev = _evidence_rows(evidence)
    if ev:
        lines += ["## Evidence / Chain of Custody", "",
                  _table(["Item", "Type", "SHA-256", "Collected By", "Time", "Notes"],
                         [[e["item"], e["type"], e["sha256"][:32] + "…",
                           e["collected_by"], e["collected_at"], e["notes"]] for e in ev]),
                  ""]
    lines += ["---", "",
              "_Generated by the CyberOps toolkit. Findings are heuristic and require "
              "analyst validation. Handle according to the classification above._"]
    return "\n".join(lines)


def _stamp() -> str:
    return _dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _evidence_rows(evidence: Sequence[Any]) -> List[Dict[str, str]]:
    rows = []
    for i, item in enumerate(evidence, 1):
        if isinstance(item, dict):
            data = item.get("data") or item.get("content") or b""
            sha = item.get("sha256") or (hashlib.sha256(data).hexdigest()
                                         if isinstance(data, (bytes, bytearray)) else "")
            rows.append({
                "item": str(item.get("item") or item.get("name") or f"evidence-{i}"),
                "type": str(item.get("type", "artifact")),
                "sha256": str(sha),
                "collected_by": str(item.get("collected_by", "CyberOps")),
                "collected_at": str(item.get("collected_at", now_iso())),
                "notes": str(item.get("notes", "")),
            })
        else:
            rows.append({"item": str(item), "type": "reference", "sha256": "",
                         "collected_by": "CyberOps", "collected_at": now_iso(), "notes": ""})
    return rows


# --------------------------------------------------------------------------- #
#  Specialised helpers
# --------------------------------------------------------------------------- #
def incident_narrative(timeline: Sequence[Any] = (), subject: str = "",
                       initial_access: str = "", impact: str = "",
                       actor: str = "") -> Dict[str, Any]:
    """Turn a timeline into a prose incident narrative."""
    events = []
    for item in timeline:
        if isinstance(item, dict):
            when = item.get("time") or item.get("timestamp") or item.get("ts") or ""
            what = item.get("event") or item.get("description") or item.get("finding") or str(item)
            events.append((str(when), str(what)))
        else:
            events.append(("", str(item)))
    events.sort(key=lambda e: e[0])
    lead = subject or "the affected environment"
    paragraphs = []
    opener = f"This report describes a security incident affecting {lead}."
    if actor:
        opener += f" Activity is assessed as consistent with {actor}."
    paragraphs.append(opener)
    if initial_access:
        paragraphs.append(f"Initial access is assessed as: {initial_access}.")
    if events:
        first = events[0]
        last = events[-1]
        sections = [f"The earliest recorded event was {first[1]}"
                    + (f" at {first[0]}" if first[0] else "") + "."]
        mid = events[1:-1]
        if mid:
            sections.append("Subsequent activity included: " +
                            "; ".join(w for _, w in mid[:12]) +
                            (f"; and {len(mid) - 12} further events" if len(mid) > 12 else "") + ".")
        sections.append(f"The latest recorded event was {last[1]}"
                        + (f" at {last[0]}" if last[0] else "") + ".")
        paragraphs.append(" ".join(sections))
    if impact:
        paragraphs.append(f"Impact: {impact}.")
    else:
        paragraphs.append("Impact assessment is ongoing; no confirmed data loss has been "
                          "established from the available evidence.")
    paragraphs.append("Recommendations and containment actions are listed in the "
                      "corresponding report sections. All timestamps are presented as "
                      "recorded and have not been independently normalised unless stated.")
    return {
        "narrative": "\n\n".join(paragraphs),
        "event_count": len(events),
        "first_event": events[0] if events else None,
        "last_event": events[-1] if events else None,
        "subject": lead,
    }


def chain_of_custody(evidence: Sequence[Any], case_id: str = "",
                     analyst: str = "") -> Dict[str, Any]:
    """Create a chain-of-custody table with hashes and handling fields."""
    rows = _evidence_rows(evidence)
    for row in rows:
        row["collected_by"] = row["collected_by"] or analyst or "CyberOps"
        row["case_id"] = case_id or "unassigned"
        row["transfer"] = "not transferred"
        row["integrity"] = "recorded" if row["sha256"] else "hash missing"
    return {
        "case_id": case_id or "unassigned",
        "analyst": analyst or "CyberOps",
        "created_at": now_iso(),
        "items": rows,
        "item_count": len(rows),
        "markdown": _table(
            ["Item", "Type", "SHA-256", "Collected By", "Time", "Case", "Integrity"],
            [[r["item"], r["type"], (r["sha256"][:24] + "…") if r["sha256"] else "-",
              r["collected_by"], r["collected_at"], r["case_id"], r["integrity"]]
             for r in rows]),
        "handling": [
            "Hash every item at acquisition and re-verify before analysis.",
            "Store originals read-only; analyse working copies.",
            "Record every transfer with person, time and purpose.",
            "Keep the case ID consistent across reports and tickets.",
        ],
    }


def lessons_learned(incident: str = "", went_well: Sequence[str] = (),
                    went_wrong: Sequence[str] = (), root_causes: Sequence[str] = (),
                    actions: Sequence[str] = ()) -> Dict[str, Any]:
    """Structure an after-action review."""
    good = [str(x) for x in went_well if str(x).strip()] or \
           ["Detection and escalation completed through the documented channel."]
    bad = [str(x) for x in went_wrong if str(x).strip()] or \
          ["Timeline correlation required manual effort."]
    rc = [str(x) for x in root_causes if str(x).strip()] or \
         ["Control gap allowed the initial access vector."]
    act = [str(x) for x in actions if str(x).strip()] or \
          ["Assign owners and due dates for each improvement."]
    return {
        "incident": incident or "security incident",
        "went_well": good, "went_wrong": bad, "root_causes": rc,
        "actions": [{"action": a, "owner": "TBD", "due": "TBD", "status": "open"} for a in act],
        "metrics": {"detection_gap_days": None, "time_to_detect": "TBD",
                    "time_to_contain": "TBD", "time_to_recover": "TBD"},
        "markdown": "\n".join(
            [f"## Lessons Learned: {incident or 'security incident'}", "",
             "### What Went Well"] + [f"- {x}" for x in good] +
            ["", "### What Needs Improvement"] + [f"- {x}" for x in bad] +
            ["", "### Root Causes"] + [f"- {x}" for x in rc] +
            ["", "### Action Items"] + [f"- {a}" for a in act]),
    }


def compliance_report(framework: str = "NIST-CSF", findings: Sequence[Any] = (),
                      evidence: Sequence[Any] = (), subject: str = "") -> Dict[str, Any]:
    """Build a compliance-oriented report with mapped controls."""
    from .advisory import map_findings_to_compliance
    mapping = map_findings_to_compliance(findings, framework)
    result = build_report(kind="compliance", subject=subject or mapping.get("name", framework),
                          findings=findings, metadata={"framework": mapping.get("name", framework)},
                          evidence=evidence)
    result["compliance_mapping"] = mapping
    result["content"] += "\n\n## Compliance Mapping\n\n" + \
        f"**Framework:** {mapping.get('name', framework)}\n\n"
    for hit in mapping.get("mapped_controls", []):
        result["content"] += (f"- **{hit['theme']}** — controls: "
                              f"{', '.join(hit['controls'])}\n")
    result["content"] += ("\nEvidence still required: " +
                          ", ".join(mapping.get("evidence_needed", [])) + "\n")
    return result


def api_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """Compact version of a report result for API responses."""
    return {
        "title": result.get("title"), "kind": result.get("kind"),
        "format": result.get("format"), "filename": result.get("filename"),
        "severity_counts": result.get("severity_counts"),
        "content": result.get("content"),
        "path": result.get("path"),
    }
