# backend/security_ops/advisory.py
# Decision-support layer: threat actor attribution, kill-chain and Diamond
# Model mapping, severity/SLA calculation, STRIDE/PASTA/LINDDUN threat
# modelling, attack-surface and posture scoring, detection tuning advice,
# anomaly explanation, zero-day hypothesis building, vulnerability chaining,
# patch prioritisation and incident crisis communications.
#
# Everything is deterministic and offline. Scores are heuristics meant to
# structure analyst judgement, not replace it.

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .knowledge import (ACTORS, COMPLIANCE, FAMILIES, PERSISTENCE, TECHNIQUE_INDEX,
                        TECHNIQUES)
from .util import normalize_severity, severity_rank, truncate_list

# --------------------------------------------------------------------------- #
#  Kill chain / tactics
# --------------------------------------------------------------------------- #
KILL_CHAIN = [
    ("Reconnaissance", ["Reconnaissance"]),
    ("Weaponization", ["Resource Development"]),
    ("Delivery", ["Initial Access"]),
    ("Exploitation", ["Execution", "Privilege Escalation"]),
    ("Installation", ["Persistence", "Defense Evasion"]),
    ("Command & Control", ["Command and Control"]),
    ("Actions on Objectives", ["Collection", "Credential Access", "Discovery",
                               "Lateral Movement", "Exfiltration", "Impact"]),
]

TACTIC_ORDER = [
    "Reconnaissance", "Resource Development", "Initial Access", "Execution",
    "Persistence", "Privilege Escalation", "Defense Evasion", "Credential Access",
    "Discovery", "Lateral Movement", "Collection", "Command and Control",
    "Exfiltration", "Impact",
]

SEVERITY_SLA = {
    "critical": {"respond_hours": 1, "contain_hours": 4, "resolve_days": 3,
                 "escalation": "CISO + incident commander immediately"},
    "high": {"respond_hours": 4, "contain_hours": 24, "resolve_days": 7,
             "escalation": "Security lead within 1 hour"},
    "medium": {"respond_hours": 24, "contain_hours": 72, "resolve_days": 30,
               "escalation": "Team lead in daily stand-up"},
    "low": {"respond_hours": 72, "contain_hours": 168, "resolve_days": 90,
            "escalation": "Tracked in backlog"},
    "info": {"respond_hours": 168, "contain_hours": 0, "resolve_days": 0,
             "escalation": "No escalation"},
}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _tactic_of(tech_id: str) -> str:
    entry = TECHNIQUE_INDEX.get(tech_id) or TECHNIQUE_INDEX.get(tech_id.split(".")[0])
    return (entry or {}).get("tactic", "")


def _technique_of(tech_id: str) -> Dict[str, Any]:
    return TECHNIQUE_INDEX.get(tech_id) or TECHNIQUE_INDEX.get(tech_id.split(".")[0]) or {
        "id": tech_id, "name": tech_id, "tactic": ""}


# --------------------------------------------------------------------------- #
#  Threat actor attribution
# --------------------------------------------------------------------------- #
def actor_profile(name: str = "", techniques: Sequence[str] = (), malware: Sequence[str] = (),
                  infrastructure: Sequence[str] = ()) -> Dict[str, Any]:
    """Return actor profiles matching a name/alias/technique/malware set."""
    query = _norm(name)
    techs = {str(t).upper() for t in techniques}
    mals = [_norm(m) for m in malware if str(m).strip()]
    infra = " ".join(_norm(i) for i in infrastructure)
    scored: List[Dict[str, Any]] = []
    for actor_name, actor in ACTORS.items():
        score = 0
        reasons: List[str] = []
        haystack = " ".join([actor_name, *actor.get("aliases", []), *actor.get("malware", [])]).lower()
        if query and (query == _norm(actor_name) or query in haystack):
            score += 70
            reasons.append(f"name/alias match '{name}'")
        overlap = techs & {str(t).upper() for t in actor.get("ttps", [])}
        if overlap:
            score += min(45, len(overlap) * 12)
            reasons.append(f"shared TTPs: {sorted(overlap)}")
        mal_overlap = [m for m in mals if m and any(m in _norm(x) or _norm(x) in m
                                                    for x in actor.get("malware", []))]
        if mal_overlap:
            score += min(40, len(mal_overlap) * 20)
            reasons.append(f"malware overlap: {mal_overlap}")
        infra_words = [w for w in ("router", "cloud", "saas", "ransom", "rmm", "supply",
                                   "false flag", "proxy", "vps", "cdn")
                       if w in infra]
        if infra_words:
            score += min(15, len(infra_words) * 5)
            reasons.append(f"infrastructure notes: {infra_words}")
        if score:
            scored.append({
                "actor": actor_name, "confidence": min(95, score),
                "aliases": actor.get("aliases", []),
                "attribution": actor.get("attribution", ""),
                "motivation": actor.get("motivation", ""),
                "targets": actor.get("targets", ""),
                "ttps": actor.get("ttps", []),
                "malware": actor.get("malware", []),
                "infrastructure": actor.get("infrastructure", ""),
                "source_confidence": actor.get("confidence", ""),
                "reasons": reasons,
            })
    scored.sort(key=lambda x: x["confidence"], reverse=True)
    if not scored:
        return {"matched": False, "candidates": [],
                "note": "No actor match. Treat as unattributed; avoid premature attribution.",
                "guidance": ["Collect additional TTPs and infrastructure overlap.",
                             "Cluster with known samples before naming an actor.",
                             "Document competing hypotheses and confidence."]}
    return {
        "matched": True,
        "best": scored[0],
        "candidates": scored[:5],
        "attribution_caveat": ("Attribution is an analytic judgement based on partial "
                               "overlap. Shared tooling is common and does not prove "
                               "actor identity."),
        "pivots": ["Reuse of C2 domains/IPs", "Code-signing certificates",
                   "Malware build paths and PDB strings", "Working hours / language artifacts",
                   "Infrastructure registration patterns"],
    }


def _family_match(text: str) -> List[Dict[str, Any]]:
    low = _norm(text)
    hits = []
    for fam in FAMILIES:
        found = [m for m in fam.get("markers", []) if m and m in low]
        if found:
            hits.append({"family": fam["name"], "markers": found,
                         "notes": fam.get("notes", "")})
    return hits


def attribute_activity(text: str = "", techniques: Sequence[str] = (),
                       malware: Sequence[str] = (), infrastructure: Sequence[str] = ()) -> Dict[str, Any]:
    """Combine actor profiling with malware-family matching."""
    fams = _family_match(text + " " + " ".join(malware))
    profile = actor_profile(
        name="", techniques=techniques,
        malware=list(malware) + [f["family"] for f in fams],
        infrastructure=infrastructure)
    aliases = []
    for fam in fams:
        aliases.extend([m for m in FAMILIES if m["name"] == fam["family"]])
    return {
        "families": fams,
        "family_count": len(fams),
        "actor_matches": profile.get("candidates", []),
        "best_actor": profile.get("best"),
        "confidence": profile.get("best", {}).get("confidence", 0) if profile.get("matched") else 0,
        "language_artifacts": _language_artifacts(text),
        "verdict": ("probable " + fams[0]["family"]) if fams else "unattributed",
        "next_steps": profile.get("pivots", []),
    }


_LANG_HINTS = {
    "russian": ["привет", "пароль", "груз", "тест", "дамп", "crypt", "шифр"],
    "chinese": ["测试", "密码", "后门", "服务", "程序", "攻击"],
    "persian": ["سلام", "رمز", "تست", "داده"],
    "arabic": ["اختبار", "كلمة", "بيانات", "تشفير"],
    "korean": ["테스트", "비밀번호"],
}


def _language_artifacts(text: str) -> List[str]:
    hits = []
    low = text.lower()
    for lang, words in _LANG_HINTS.items():
        for w in words:
            if w in low:
                hits.append(lang)
                break
    if re.search(r"(?i)(gdpr|eu|moscow|beijing|tehran|pyongyang)", text):
        hits.append("geopolitical reference")
    return sorted(set(hits))


# --------------------------------------------------------------------------- #
#  Kill chain & Diamond Model
# --------------------------------------------------------------------------- #
def kill_chain(techniques: Sequence[str]) -> Dict[str, Any]:
    """Map ATT&CK techniques to Lockheed Martin kill-chain phases."""
    present: Dict[str, List[Dict[str, str]]] = {name: [] for name, _ in KILL_CHAIN}
    tactic_hits: Counter = Counter()
    unmatched: List[str] = []
    for tech in techniques:
        tid = str(tech).strip()
        tactic = _tactic_of(tid)
        if not tactic:
            unmatched.append(tid)
            continue
        tactic_hits[tactic] += 1
        for phase, tactics in KILL_CHAIN:
            if tactic in tactics:
                present[phase].append({"id": tid, "name": _technique_of(tid).get("name", ""),
                                       "tactic": tactic})
                break
        else:
            unmatched.append(tid)
    phases = []
    for phase, _ in KILL_CHAIN:
        items = present[phase]
        phases.append({"phase": phase, "reached": bool(items), "techniques": items,
                       "count": len(items)})
    reached = [p["phase"] for p in phases if p["reached"]]
    early = reached and reached[0] in ("Reconnaissance", "Weaponization", "Delivery")
    return {
        "phases": phases,
        "reached_phases": reached,
        "phase_count": len(reached),
        "furthest_phase": reached[-1] if reached else "",
        "coverage_percent": round(len(reached) / len(KILL_CHAIN) * 100, 1),
        "tactic_counts": dict(tactic_hits),
        "unmatched": unmatched,
        "assessment": _kill_chain_assessment(reached, early),
        "detection_priorities": _kill_chain_priorities(reached),
    }


def _kill_chain_assessment(reached: List[str], early: bool) -> str:
    if not reached:
        return "No kill-chain evidence mapped; refine technique extraction."
    if "Actions on Objectives" in reached:
        return ("Activity reached objectives (collection/exfiltration/impact). "
                "Assume data or availability impact and start containment.")
    if "Command & Control" in reached:
        return ("Operator has interactive access. Hunt for lateral movement and "
                "collection before objectives are met.")
    if "Installation" in reached:
        return "Persistence likely established; sweep autostarts and scheduled tasks."
    if early:
        return "Activity stopped at delivery/exploitation; verify execution did not occur."
    return "Partial chain; correlate host and network telemetry to place the stage."


def _kill_chain_priorities(reached: Sequence[str]) -> List[str]:
    mapping = {
        "Reconnaissance": "Monitor scanning and OSINT collection against brand assets.",
        "Weaponization": "Track lure themes, new domains and builder artifacts.",
        "Delivery": "Inspect mail/web gateways for the delivery vector.",
        "Exploitation": "Patch the exploited component and hunt for child processes.",
        "Installation": "Enumerate Run keys, services, tasks, WMI subscriptions.",
        "Command & Control": "Extract C2 from PCAP/proxy logs and sinkhole if policy allows.",
        "Actions on Objectives": "Preserve evidence, scope data access, begin IR playbook.",
    }
    return [mapping[p] for p in reached if p in mapping]


def diamond_model(adversary: str = "", capability: str = "", infrastructure: str = "",
                  victim: str = "", confidence: str = "") -> Dict[str, Any]:
    """Build a Diamond Model record and highlight missing vertices."""
    vertices = {
        "adversary": {"value": adversary, "filled": bool(str(adversary).strip())},
        "capability": {"value": capability, "filled": bool(str(capability).strip())},
        "infrastructure": {"value": infrastructure, "filled": bool(str(infrastructure).strip())},
        "victim": {"value": victim, "filled": bool(str(victim).strip())},
    }
    missing = [k for k, v in vertices.items() if not v["filled"]]
    filled = 4 - len(missing)
    return {
        "vertices": vertices,
        "missing": missing,
        "completeness_percent": filled * 25,
        "confidence": confidence or ("low" if filled < 3 else "medium"),
        "analytic_notes": [
            "Each vertex constrains the others; use filled vertices to pivot to missing ones.",
            "Adversary and victim are social/identity axes; capability and infrastructure are technical.",
        ],
        "pivots": {
            "adversary": ["Infrastructure reuse", "Tooling artifacts", "Language/timezone"],
            "capability": ["Static signatures", "Behavioral detections", "Exploit fingerprints"],
            "infrastructure": ["Passive DNS", "Certificate transparency", "ASN/hosting"],
            "victim": ["Sector targeting", "Identity exposure", "Supply-chain relationships"],
        },
        "verdict": "complete model" if not missing else f"missing {len(missing)} vertex/vertices",
    }


# --------------------------------------------------------------------------- #
#  Severity / risk scoring
# --------------------------------------------------------------------------- #
def severity_calculator(cvss: float = 0.0, confidence: str = "medium",
                        exposure: str = "internal", data_sensitivity: str = "internal",
                        blast_radius: str = "single-host", exploited: bool = False,
                        privileged: bool = False, internet_facing: bool = False,
                        compensating_controls: Sequence[str] = ()) -> Dict[str, Any]:
    """Blend technical severity with business context into a priority + SLA."""
    try:
        base = float(cvss)
    except (TypeError, ValueError):
        base = 0.0
    if base > 10:
        base = 10.0
    if base <= 0:
        base = 5.0  # unknown defaults to medium technical severity
    score = base * 10
    factors: List[Dict[str, Any]] = []

    conf_mult = {"low": 0.7, "medium": 1.0, "high": 1.15, "confirmed": 1.25}.get(confidence, 1.0)
    if conf_mult != 1.0:
        factors.append({"factor": "confidence", "value": confidence, "multiplier": conf_mult})
        score *= conf_mult

    exposure_mult = {"internal": 1.0, "partner": 1.1, "public": 1.25}.get(exposure, 1.0)
    if internet_facing:
        exposure_mult += 0.1
    if exposure_mult != 1.0:
        factors.append({"factor": "exposure", "value": exposure,
                        "multiplier": round(exposure_mult, 2)})
        score *= exposure_mult

    sens_mult = {"public": 0.9, "internal": 1.0, "confidential": 1.1,
                 "regulated": 1.2, "secret": 1.3}.get(data_sensitivity, 1.0)
    if sens_mult != 1.0:
        factors.append({"factor": "data sensitivity", "value": data_sensitivity,
                        "multiplier": sens_mult})
        score *= sens_mult

    blast_mult = {"single-host": 1.0, "department": 1.1, "site": 1.2,
                  "enterprise": 1.3, "supply-chain": 1.4}.get(blast_radius, 1.0)
    if blast_mult != 1.0:
        factors.append({"factor": "blast radius", "value": blast_radius,
                        "multiplier": blast_mult})
        score *= blast_mult

    if exploited:
        score *= 1.3
        factors.append({"factor": "known exploitation", "value": True, "multiplier": 1.3})
    if privileged:
        score *= 1.15
        factors.append({"factor": "privileged context", "value": True, "multiplier": 1.15})

    control_mult = max(0.65, 1.0 - 0.1 * len([c for c in compensating_controls if c]))
    if control_mult < 1.0:
        factors.append({"factor": "compensating controls",
                        "value": list(compensating_controls), "multiplier": round(control_mult, 2)})
        score *= control_mult

    score = min(100.0, max(0.0, score))
    if score >= 85:
        sev = "critical"
    elif score >= 65:
        sev = "high"
    elif score >= 40:
        sev = "medium"
    elif score >= 15:
        sev = "low"
    else:
        sev = "info"
    sla = dict(SEVERITY_SLA[sev])
    return {
        "risk_score": round(score, 1),
        "severity": sev,
        "cvss_base": round(base, 1),
        "sla": sla,
        "factors": factors,
        "business_impact": _business_impact(sev, data_sensitivity, blast_radius),
        "recommended_actions": _severity_actions(sev),
        "rationale": (f"CVSS {base:.1f} adjusted to {score:.1f}/100 using "
                      f"confidence={confidence}, exposure={exposure}, "
                      f"sensitivity={data_sensitivity}, blast_radius={blast_radius}"
                      + (", exploited" if exploited else "")
                      + (", privileged" if privileged else "") + "."),
    }


def _business_impact(sev: str, sensitivity: str, blast: str) -> List[str]:
    impacts = []
    if sev in ("critical", "high"):
        impacts.append("Potential regulatory notification and executive reporting.")
        impacts.append("Operational disruption requiring incident response resources.")
    if sensitivity in ("regulated", "secret", "confidential"):
        impacts.append("Confidential/regulated data exposure risk.")
    if blast in ("enterprise", "supply-chain"):
        impacts.append("Cross-system or third-party impact; consider contractual obligations.")
    if sev in ("low", "info"):
        impacts.append("Limited impact; remediate through normal change management.")
    return impacts


def _severity_actions(sev: str) -> List[str]:
    return {
        "critical": ["Activate incident response", "Isolate affected assets",
                     "Notify CISO/legal/compliance", "Preserve evidence before remediation"],
        "high": ["Contain within 24h", "Validate scope with host+network telemetry",
                 "Apply emergency change or mitigation"],
        "medium": ["Schedule remediation in current sprint", "Add detection coverage",
                   "Track compensating controls"],
        "low": ["Add to backlog", "Monitor for escalation"],
        "info": ["Document and close", "Use for detection tuning"],
    }.get(sev, [])


# --------------------------------------------------------------------------- #
#  Threat modelling
# --------------------------------------------------------------------------- #
STRIDE = {
    "Spoofing": {"question": "Can identity be forged?", "controls": ["MFA", "Mutual TLS", "Signed tokens"]},
    "Tampering": {"question": "Can data be modified in transit or at rest?", "controls": ["Integrity checks", "Signed artifacts", "Immutable logs"]},
    "Repudiation": {"question": "Can actions be denied?", "controls": ["Centralized audit logs", "Non-repudiation signatures"]},
    "Information Disclosure": {"question": "Can data leak?", "controls": ["Encryption", "Least privilege", "DLP"]},
    "Denial of Service": {"question": "Can availability be disrupted?", "controls": ["Rate limits", "Autoscaling", "DDoS protection"]},
    "Elevation of Privilege": {"question": "Can a user gain higher rights?", "controls": ["RBAC", "Sandboxing", "Patch management"]},
}

PASTA_STAGES = [
    ("Define objectives", "Business goals and risk tolerance"),
    ("Define technical scope", "Architecture, data flows, trust boundaries"),
    ("Application decomposition", "Components, entry points, assets"),
    ("Threat analysis", "Actors, capabilities, likely TTPs"),
    ("Vulnerability analysis", "Weaknesses mapped to threats"),
    ("Attack modelling", "Paths, preconditions, impact"),
    ("Risk and impact analysis", "Business impact, prioritisation"),
]

LINDDUN = {
    "Linking": "Correlating records to identify an individual",
    "Identifying": "Determining identity from data",
    "Non-repudiation": "Over-collection preventing plausible deniability",
    "Detecting": "Inferring sensitive facts from metadata",
    "Data Disclosure": "Exposing personal data",
    "Unawareness": "Users unaware of data processing",
    "Non-compliance": "Processing without lawful basis",
}

ASSET_CRITICALITY = {"crown-jewel": 10, "critical": 9, "high": 7, "medium": 5, "low": 3}
EXPOSURE_WEIGHT = {"internet": 1.0, "partner": 0.75, "internal": 0.5, "air-gapped": 0.2}


def threat_model(description: str, methodology: str = "stride",
                 assets: Sequence[Dict[str, Any]] = (),
                 trust_boundaries: Sequence[str] = (),
                 actors: Sequence[str] = ()) -> Dict[str, Any]:
    """Generate a structured threat model from a system description."""
    method = _norm(methodology) or "stride"
    text = description or ""
    trusted = [b for b in trust_boundaries if str(b).strip()]
    asset_list = [a for a in assets if isinstance(a, dict)]
    if not asset_list and text:
        asset_list = _infer_assets(text)
    if method in ("stride", "all"):
        rows = []
        for category, meta in STRIDE.items():
            likelihood = _stride_likelihood(category, text)
            impact = "high" if category in ("Elevation of Privilege", "Information Disclosure") else "medium"
            rows.append({"category": category, "question": meta["question"],
                         "likelihood": likelihood, "impact": impact,
                         "risk": _risk_from(likelihood, impact),
                         "controls": meta["controls"],
                         "test": _stride_test(category)})
        rows.sort(key=lambda r: severity_rank(_risk_to_sev(r["risk"])), reverse=False)
        stride_out = {"rows": rows,
                      "top_risks": [r for r in rows if r["risk"] in ("critical", "high")]}
    else:
        stride_out = {}
    pasta_out = {}
    if method in ("pasta", "all"):
        pasta_out = {"stages": [{"stage": s, "focus": f, "done": False} for s, f in PASTA_STAGES],
                     "next_action": "Complete stage 1 (objectives) before attack modelling."}
    linddun_out = {}
    if method in ("linddun", "privacy", "all"):
        linddun_out = {"threats": [{"category": k, "description": v,
                                    "control": _linddun_control(k)}
                                   for k, v in LINDDUN.items()]}
    surface = attack_surface([{"name": a.get("name", f"asset-{i}"),
                               "criticality": a.get("criticality", "medium"),
                               "exposure": a.get("exposure", "internal"),
                               "services": a.get("services", [])}
                              for i, a in enumerate(asset_list)])
    return {
        "methodology": method,
        "system": text[:400],
        "trust_boundaries": trusted,
        "actors": list(actors),
        "assets": asset_list,
        "stride": stride_out,
        "pasta": pasta_out,
        "linddun": linddun_out,
        "attack_surface": surface,
        "assumptions": [
            "Model is only as good as the architecture description.",
            "Validate trust boundaries against the deployed network, not the diagram.",
            "Re-run after architecture or data-flow changes.",
        ],
    }


def _infer_assets(text: str) -> List[Dict[str, Any]]:
    low = text.lower()
    assets = []
    cues = {
        "web application": "internet", "api": "internet", "database": "internal",
        "kubernetes": "internal", "active directory": "internal", "vpn": "internet",
        "email gateway": "internet", "ci/cd": "internal", "s3 bucket": "internet",
        "file share": "internal", "admin portal": "internet", "payment": "internet",
    }
    for cue, exposure in cues.items():
        if cue in low:
            assets.append({"name": cue, "criticality": "high" if cue in
                           ("payment", "active directory", "database") else "medium",
                           "exposure": exposure, "services": [cue]})
    return assets or [{"name": "described-system", "criticality": "medium",
                       "exposure": "internal", "services": []}]


def _stride_likelihood(category: str, text: str) -> str:
    low = text.lower()
    keys = {
        "Spoofing": ("login", "auth", "token", "session", "api"),
        "Tampering": ("upload", "api", "database", "config", "webhook"),
        "Repudiation": ("audit", "log", "action", "admin"),
        "Information Disclosure": ("data", "customer", "pii", "secret", "backup"),
        "Denial of Service": ("public", "api", "upload", "webhook", "internet"),
        "Elevation of Privilege": ("admin", "role", "permission", "container", "sudo"),
    }
    matches = sum(1 for k in keys.get(category, ()) if k in low)
    return "high" if matches >= 2 else ("medium" if matches == 1 else "low")


def _risk_from(likelihood: str, impact: str) -> str:
    table = {("high", "high"): "critical", ("high", "medium"): "high",
             ("medium", "high"): "high", ("medium", "medium"): "medium",
             ("low", "high"): "medium", ("low", "medium"): "low",
             ("high", "low"): "medium", ("medium", "low"): "low", ("low", "low"): "info"}
    return table.get((likelihood, impact), "medium")


def _risk_to_sev(risk: str) -> str:
    return risk


def _stride_test(category: str) -> str:
    return {
        "Spoofing": "Attempt credential replay, token forgery and MFA bypass.",
        "Tampering": "Modify requests, uploads and signed artifacts; verify integrity checks.",
        "Repudiation": "Perform privileged actions and confirm attribution in logs.",
        "Information Disclosure": "Probe error messages, backups and object references for leaks.",
        "Denial of Service": "Test rate limits, large payloads and resource exhaustion.",
        "Elevation of Privilege": "Attempt role escalation, container escape and sudo abuse.",
    }[category]


def _linddun_control(category: str) -> str:
    return {
        "Linking": "Data minimization and pseudonymisation",
        "Identifying": "Avoid unnecessary identifiers; aggregate where possible",
        "Non-repudiation": "Retention limits and purpose binding",
        "Detecting": "Suppress metadata that reveals sensitive facts",
        "Data Disclosure": "Encryption, access control, DLP",
        "Unawareness": "Clear privacy notices and consent flows",
        "Non-compliance": "Lawful-basis mapping and DPIA",
    }.get(category, "Assess against privacy requirements")


# --------------------------------------------------------------------------- #
#  Attack surface / posture
# --------------------------------------------------------------------------- #
def attack_surface(assets: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Score exposed assets and rank by attack-surface contribution."""
    rows = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name") or asset.get("host") or "unnamed"
        crit = ASSET_CRITICALITY.get(_norm(asset.get("criticality", "medium")), 5)
        exposure = EXPOSURE_WEIGHT.get(_norm(asset.get("exposure", "internal")), 0.5)
        services = asset.get("services", []) or []
        service_risk = min(30, len(services) * 4)
        score = round(crit * 6 * exposure + service_risk, 1)
        rows.append({"asset": name, "criticality": asset.get("criticality", "medium"),
                     "exposure": asset.get("exposure", "internal"),
                     "services": list(services), "surface_score": score,
                     "risk": "critical" if score >= 60 else ("high" if score >= 45 else
                             ("medium" if score >= 25 else "low")),
                     "priority_actions": _surface_actions(asset)})
    rows.sort(key=lambda r: r["surface_score"], reverse=True)
    return {"assets": rows, "asset_count": len(rows),
            "internet_facing": sum(1 for r in rows if _norm(r["exposure"]) == "internet"),
            "total_surface_score": round(sum(r["surface_score"] for r in rows), 1),
            "top_assets": rows[:5]}


def _surface_actions(asset: Dict[str, Any]) -> List[str]:
    out = []
    if _norm(asset.get("exposure")) == "internet":
        out.append("Place behind WAF/reverse proxy and require strong authentication.")
        out.append("Continuous external attack-surface scanning.")
    services = " ".join(str(s).lower() for s in asset.get("services", []) or [])
    if any(s in services for s in ("ssh", "rdp", "smb", "telnet")):
        out.append("Restrict management protocols to bastion/VPN with MFA.")
    if "database" in services:
        out.append("Verify database is not directly reachable from untrusted networks.")
    if not out:
        out.append("Maintain patching and least-privilege review.")
    return out


CONTROL_DOMAINS = {
    "identity": ["MFA", "PAM", "SSO", "conditional access", "least privilege"],
    "endpoint": ["EDR", "application control", "patch management", "disk encryption"],
    "network": ["segmentation", "firewall", "IDS/IPS", "zero trust", "egress filtering"],
    "data": ["DLP", "classification", "backup", "encryption at rest"],
    "monitoring": ["SIEM", "log retention", "alert tuning", "threat hunting", "UEBA"],
    "response": ["IR plan", "tabletop", "forensics", "containment playbooks", "comms plan"],
    "vulnerability": ["scanning", "pen testing", "bug bounty", "patch SLA", "SBOM"],
    "governance": ["risk register", "policy", "training", "third-party assessment", "audit"],
}


def posture_score(controls: Sequence[Any], framework: str = "") -> Dict[str, Any]:
    """Score security posture against control domains and optional framework."""
    present = {_norm(c) for c in controls if str(c).strip()}
    domains = []
    total = 0
    for domain, items in CONTROL_DOMAINS.items():
        hits = [i for i in items if any(_norm(i) in p or p in _norm(i) for p in present)]
        pct = round(len(hits) / len(items) * 100)
        total += pct
        domains.append({"domain": domain, "coverage_percent": pct,
                        "present": hits, "missing": [i for i in items if i not in hits],
                        "rating": _rating(pct)})
    overall = round(total / len(CONTROL_DOMAINS), 1)
    gaps = sorted(domains, key=lambda d: d["coverage_percent"])
    fw = {}
    key = _match_framework(framework) if framework else ""
    if key:
        fw = {"framework": key, "name": COMPLIANCE[key]["name"],
              "controls": COMPLIANCE[key].get("controls", []),
              "note": "Map domain gaps to the listed controls for audit evidence."}
    return {
        "overall_percent": overall,
        "maturity": _maturity(overall),
        "domains": domains,
        "weakest_domains": gaps[:3],
        "strongest_domains": sorted(domains, key=lambda d: d["coverage_percent"], reverse=True)[:3],
        "framework": fw,
        "priorities": [f"Improve {g['domain']} ({g['coverage_percent']}%): add "
                       f"{', '.join(g['missing'][:3])}" for g in gaps[:3]],
        "score_note": "Heuristic coverage estimate; validate with evidence and testing.",
    }


def _match_framework(name: str) -> str:
    target = _norm(name)
    for key, meta in COMPLIANCE.items():
        if target in _norm(key) or target in _norm(meta.get("name")):
            return key
    return ""


def _rating(pct: int) -> str:
    return "strong" if pct >= 80 else ("adequate" if pct >= 60 else
                                      ("weak" if pct >= 35 else "critical gap"))


def _maturity(pct: float) -> str:
    if pct >= 85:
        return "optimized"
    if pct >= 70:
        return "managed"
    if pct >= 50:
        return "defined"
    if pct >= 30:
        return "repeatable"
    return "initial"


# --------------------------------------------------------------------------- #
#  Detection tuning / anomaly explanation
# --------------------------------------------------------------------------- #
def false_positive_tuning(detection: str, context: Sequence[str] = (),
                          known_benign: Sequence[str] = ()) -> Dict[str, Any]:
    """Suggest tuning levers for a noisy detection."""
    text = detection or ""
    ctx = [c for c in context if str(c).strip()]
    benign = [b for b in known_benign if str(b).strip()]
    levers = []
    if re.search(r"(?i)powershell|cmd|wmic|rundll32|regsvr32|mshta", text):
        levers += [
            "Scope to non-admin users or unusual parent processes first.",
            "Exclude signed enterprise management tooling with verified hashes.",
            "Add command-line content filters (encoded commands, download cradles).",
        ]
    if re.search(r"(?i)scanner|nessus|qualys|vuln", text):
        levers += ["Suppress authorized scanner source IPs and schedules.",
                   "Require successful authentication before alerting."]
    if re.search(r"(?i)login|logon|4625|4624", text):
        levers += ["Threshold on failures per user/host within a window.",
                   "Exclude service accounts with documented behavior baselines."]
    if re.search(r"(?i)dns|http|network|beacon", text):
        levers += ["Use allowlists for sanctioned SaaS and CDN domains.",
                   "Alert on new destinations combined with high entropy or low reputation."]
    if re.search(r"(?i)file|hash|unsigned", text):
        levers += ["Allowlist by publisher signature and hash on managed endpoints.",
                   "Prioritise execution from user-writable directories."]
    if benign:
        levers.append(f"Build a time-boxed exception list for: {', '.join(benign[:8])}.")
    if ctx:
        levers.append(f"Use context enrichment ({', '.join(ctx[:5])}) before suppression.")
    levers += [
        "Measure precision/recall against a labeled sample for 2 weeks.",
        "Never suppress solely to reduce volume; log the tuning decision.",
        "Add a low-severity 'tuned' rule to retain visibility.",
    ]
    deduped = list(dict.fromkeys(levers))
    return {
        "detection": text[:300], "levers": deduped,
        "recommended_selector_changes": _selector_changes(text),
        "validation_plan": ["Replay 30 days of data", "Compare alert volume before/after",
                            "Confirm true positives still fire", "Document owner and review date"],
        "risk_of_tuning": "Over-suppression can hide real intrusions; keep an audit trail.",
    }


def _selector_changes(text: str) -> List[str]:
    out = []
    if "Image" in text or "Process" in text:
        out.append("Add parent-image and integrity-level constraints.")
    if "CommandLine" in text:
        out.append("Require at least one high-signal token instead of a generic keyword.")
    if "User" in text:
        out.append("Separate service accounts from interactive users.")
    if not out:
        out.append("Start with a narrow scope, then progressively broaden after validation.")
    return out


def explain_anomaly(features: Dict[str, Any], baseline: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Explain a statistical anomaly in analyst-friendly terms."""
    baseline = baseline or {}
    rows = []
    for key, value in (features or {}).items():
        base = baseline.get(key)
        if isinstance(value, (int, float)) and isinstance(base, (int, float)) and base:
            ratio = float(value) / float(base)
            deviation = abs(ratio - 1.0)
            if deviation >= 0.5:
                rows.append({"feature": key, "observed": value, "baseline": base,
                             "ratio": round(ratio, 2),
                             "explanation": f"{key} is {ratio:.1f}x the baseline"})
        elif base is not None and value != base:
            rows.append({"feature": key, "observed": value, "baseline": base,
                         "ratio": None, "explanation": f"{key} differs from baseline"})
    rows.sort(key=lambda r: abs((r.get("ratio") or 1) - 1), reverse=True)
    hypotheses = []
    names = " ".join(r["feature"].lower() for r in rows)
    if any(w in names for w in ("bytes", "connections", "dns", "traffic", "upload")):
        hypotheses.append("Possible exfiltration or C2 channel; inspect payload sizes and destinations.")
    if any(w in names for w in ("process", "child", "spawn")):
        hypotheses.append("Possible execution chain; inspect process ancestry and command lines.")
    if any(w in names for w in ("login", "auth", "failure")):
        hypotheses.append("Possible credential attack; check spray patterns and source IPs.")
    if any(w in names for w in ("file", "write", "entropy")):
        hypotheses.append("Possible staging/encryption; inspect artifact hashes and entropy.")
    if not hypotheses:
        hypotheses.append("Investigate the top deviating features and correlate with host telemetry.")
    return {
        "deviations": rows[:20],
        "deviation_count": len(rows),
        "plain_language": [r["explanation"] for r in rows[:5]],
        "hypotheses": hypotheses,
        "next_checks": ["Confirm the anomaly is not a legitimate business change.",
                        "Compare with peer hosts/users.", "Pull raw telemetry around the event."],
        "confidence": "high" if len(rows) >= 3 else ("medium" if rows else "low"),
    }


def zero_day_hypothesis(observations: Sequence[str] = (), artifacts: Sequence[str] = (),
                        crash_signatures: Sequence[str] = ()) -> Dict[str, Any]:
    """Structure investigation of a suspected unpatched vulnerability."""
    text = " ".join([*observations, *artifacts, *crash_signatures]).lower()
    indicators = []
    if "crash" in text or "access violation" in text:
        indicators.append("Repeated crashes with controlled input")
    if "waf" in text or "bypass" in text:
        indicators.append("WAF/proxy bypass behaviour")
    if "unusual" in text or "novel" in text:
        indicators.append("Novel traffic or file format")
    if "no detection" in text or "av" in text:
        indicators.append("Absent known signatures")
    if "heap" in text or "buffer" in text or "rce" in text:
        indicators.append("Memory-corruption language")
    hypotheses = [
        "Logic flaw in an exposed service (auth, authorization, parsing).",
        "Memory corruption in a parser (file, protocol, image).",
        "Deserialization or template injection leading to code execution.",
        "Supply-chain compromise in a trusted dependency.",
    ]
    return {
        "indicators": indicators,
        "hypotheses": hypotheses,
        "validation_plan": [
            "Reproduce in an isolated lab with the same build.",
            "Minimise the trigger input and capture a crash dump.",
            "Test patch level and configuration differences against a control host.",
            "Check vendor advisories and CVE feeds before assuming zero-day.",
            "Engage the vendor through coordinated disclosure if confirmed.",
        ],
        "containment": ["Add virtual patching/WAF rule", "Restrict exposure",
                        "Increase telemetry on the component", "Prepare rollback"],
        "confidence": "low" if not indicators else ("medium" if len(indicators) < 3 else "high"),
        "caveat": "Most suspected zero-days are known issues with a missed patch. Verify first.",
    }


# --------------------------------------------------------------------------- #
#  Vulnerabilities: chaining + patching
# --------------------------------------------------------------------------- #
CHAIN_RULES = [
    ({"info_disclosure", "ssrf"}, {"impact": "internal network access",
                                   "reason": "SSRF plus leaked internal endpoints"}),
    ({"xss", "csrf"}, {"impact": "authenticated action hijacking",
                        "reason": "XSS can bypass CSRF tokens in-session"}),
    ({"open_redirect", "oauth_misconfig"}, {"impact": "token theft",
                                            "reason": "Redirect abuse can leak OAuth codes"}),
    ({"sqli", "file_write"}, {"impact": "remote code execution",
                               "reason": "SQLi plus file write enables webshell"}),
    ({"lfi", "file_upload"}, {"impact": "remote code execution",
                               "reason": "Local file inclusion plus upload enables code exec"}),
    ({"ssrf", "cloud_metadata"}, {"impact": "credential theft",
                                  "reason": "SSRF reaching metadata service yields cloud keys"}),
    ({"default_creds", "exposed_admin"}, {"impact": "full administrative takeover",
                                          "reason": "Default credentials on an exposed admin panel"}),
    ({"subdomain_takeover", "phishing"}, {"impact": "brand abuse / credential theft",
                                          "reason": "Takeover enables trusted-domain phishing"}),
    ({"deserialization", "gadget_chain"}, {"impact": "remote code execution",
                                           "reason": "Unsafe deserialization with a gadget chain"}),
]


def chain_vulnerabilities(vulns: Sequence[Any]) -> Dict[str, Any]:
    """Group findings and detect compound attack paths."""
    tags = set()
    normalized = []
    for v in vulns:
        if isinstance(v, dict):
            tag = _norm(v.get("type") or v.get("category") or v.get("name"))
            title = v.get("title") or v.get("name") or tag
            sev = normalize_severity(v.get("severity", "medium"))
        else:
            tag = _norm(v)
            title = str(v)
            sev = "medium"
        tags.add(tag)
        normalized.append({"tag": tag, "title": title, "severity": sev})
    chains = []
    for need, result in CHAIN_RULES:
        if need.issubset(tags):
            chains.append({"components": sorted(need), **result,
                           "severity": "critical" if "execution" in result["impact"]
                           or "takeover" in result["impact"] else "high"})
    steps = _attack_path(normalized, chains)
    return {
        "findings": normalized,
        "chains": chains,
        "chain_count": len(chains),
        "compound_risk": "critical" if any(c["severity"] == "critical" for c in chains) else
                         ("high" if chains else "baseline"),
        "attack_path": steps,
        "recommendation": ("Fix the lowest-effort component to break each chain; "
                           "prioritise chains ending in code execution or admin takeover."
                           if chains else "No known chain matched; review manually for logic flaws."),
    }


def _attack_path(findings: List[Dict[str, Any]], chains: List[Dict[str, Any]]) -> List[str]:
    steps = ["Initial foothold via the lowest-severity exposed finding."]
    for chain in chains:
        steps.append(f"Combine {', '.join(chain['components'])} -> {chain['impact']}.")
    if findings:
        steps.append("Escalate using the highest-severity validated finding.")
    steps.append("Achieve objective (data access, lateral movement, or disruption).")
    return steps


def patch_priority(vulns: Sequence[Any], asset_criticality: str = "medium") -> Dict[str, Any]:
    """Rank vulnerabilities by exploitability, exposure and asset value."""
    crit = ASSET_CRITICALITY.get(_norm(asset_criticality), 5)
    rows = []
    for i, v in enumerate(vulns):
        v = v if isinstance(v, dict) else {"title": str(v)}
        cvss = v.get("cvss", v.get("score", 0)) or 0
        try:
            cvss = float(cvss)
        except (TypeError, ValueError):
            cvss = 0.0
        if cvss > 10:
            cvss /= 10.0
        exploited = bool(v.get("exploited") or v.get("kev") or v.get("in_the_wild"))
        public = bool(v.get("public_exploit") or v.get("poc"))
        exposed = _norm(v.get("exposure", "internal")) in ("internet", "public", "external")
        auth = bool(v.get("requires_auth", True))
        score = cvss * 8 + (15 if exploited else 0) + (8 if public else 0) + \
                (10 if exposed else 0) + (4 if not auth else 0) + crit * 0.5
        score = min(100.0, score)
        sev = ("critical" if score >= 85 else "high" if score >= 65 else
               "medium" if score >= 40 else "low")
        rows.append({
            "rank": 0, "title": v.get("title") or v.get("name") or f"finding-{i+1}",
            "cve": v.get("cve", ""), "cvss": round(cvss, 1), "priority_score": round(score, 1),
            "severity": sev, "exploited_in_wild": exploited, "public_exploit": public,
            "internet_facing": exposed, "requires_auth": auth,
            "sla_days": SEVERITY_SLA[sev]["resolve_days"],
            "why": _patch_why(exploited, public, exposed, cvss),
        })
    rows.sort(key=lambda r: r["priority_score"], reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return {
        "priorities": rows,
        "count": len(rows),
        "immediate": [r["title"] for r in rows if r["severity"] == "critical"][:10],
        "quick_wins": [r["title"] for r in rows if r["cvss"] < 7 and not r["requires_auth"]][:10],
        "asset_criticality": asset_criticality,
        "method": "CVSS-weighted score + exploit availability + exposure + auth requirements.",
    }


def _patch_why(exploited: bool, public: bool, exposed: bool, cvss: float) -> str:
    reasons = []
    if exploited:
        reasons.append("exploited in the wild")
    if public:
        reasons.append("public exploit/PoC")
    if exposed:
        reasons.append("internet-facing")
    if cvss >= 9:
        reasons.append("critical CVSS")
    return ", ".join(reasons) or "baseline severity and asset value"


# --------------------------------------------------------------------------- #
#  Crisis communications
# --------------------------------------------------------------------------- #
def crisis_comms(incident: str = "", audience: str = "all", severity: str = "high",
                 confirmed_facts: Sequence[str] = (), unknowns: Sequence[str] = (),
                 actions: Sequence[str] = (), contact: str = "") -> Dict[str, Any]:
    """Draft holding statements per audience with do/don't guidance."""
    sev = normalize_severity(severity)
    facts = [f for f in confirmed_facts if str(f).strip()]
    unknown = [u for u in unknowns if str(u).strip()]
    doing = [a for a in actions if str(a).strip()]
    headline = _comms_headline(incident, sev)
    aud = _norm(audience)
    if aud in ("regulator", "legal", "compliance"):
        statement = _regulator_statement(headline, facts, doing, contact)
    elif aud in ("customer", "public", "external"):
        statement = _public_statement(headline, facts, doing, contact)
    elif aud in ("board", "executive", "leadership"):
        statement = _board_statement(headline, sev, facts, unknown, doing)
    else:
        statement = _internal_statement(headline, facts, doing, contact)
    missing = []
    if not facts:
        missing.append("confirmed facts")
    if not unknown:
        missing.append("explicit unknowns (prevents speculation)")
    if not doing:
        missing.append("actions underway")
    if not contact:
        missing.append("named contact / press channel")
    return {
        "audience": aud or "internal",
        "severity": sev,
        "headline": headline,
        "statement": statement,
        "confirmed_facts": facts,
        "unknowns": unknown,
        "actions": doing,
        "do": ["State only confirmed facts", "Give a next-update time",
               "Show empathy and accountability", "Use one coordinated channel"],
        "dont": ["Speculate on attribution", "Promise unsupported timelines",
                 "Share victim PII", "Blame third parties prematurely"],
        "missing_inputs": missing,
        "approval_required": aud in ("regulator", "public", "external"),
        "legal_review": sev in ("critical", "high"),
    }


def _comms_headline(incident: str, sev: str) -> str:
    subject = (incident or "a security incident").strip().rstrip(".")
    if sev == "critical":
        return f"Active security incident affecting {subject}"
    if sev == "high":
        return f"Security incident under investigation: {subject}"
    return f"Security notice: {subject}"


def _internal_statement(headline: str, facts: List[str], actions: List[str], contact: str) -> str:
    lines = [headline, "", "What we know:"]
    lines += [f"- {f}" for f in facts] or ["- Investigation is ongoing; details are being validated."]
    if actions:
        lines += ["", "What we are doing:"]
        lines += [f"- {a}" for a in actions]
    lines += ["", f"Point of contact: {contact or 'Security Operations Center'}",
              "Next update: at the scheduled incident bridge."]
    return "\n".join(lines)


def _public_statement(headline: str, facts: List[str], actions: List[str], contact: str) -> str:
    lines = [headline, "",
             "We are aware of a security issue and have activated our incident response process.",
             "We are taking it seriously and working to protect our customers and systems."]
    if facts:
        lines += ["", "Confirmed so far:"]
        lines += [f"- {f}" for f in facts]
    if actions:
        lines += ["", "Measures in progress:"]
        lines += [f"- {a}" for a in actions]
    lines += ["", "We will provide further verified information as it becomes available.",
              f"Media contact: {contact or 'press@example.com'}"]
    return "\n".join(lines)


def _regulator_statement(headline: str, facts: List[str], actions: List[str], contact: str) -> str:
    lines = [headline, "", "Notification summary:"]
    lines += [f"- {f}" for f in facts] or ["- Preliminary assessment in progress."]
    if actions:
        lines += ["", "Containment and remediation measures:"]
        lines += [f"- {a}" for a in actions]
    lines += ["", "We will provide updates within the required regulatory timeframe.",
              f"Regulatory liaison: {contact or 'compliance@example.com'}"]
    return "\n".join(lines)


def _board_statement(headline: str, sev: str, facts: List[str], unknowns: List[str],
                     actions: List[str]) -> str:
    lines = [headline, "", f"Severity: {sev.upper()}", "Business context:"]
    lines += [f"- {f}" for f in facts] or ["- Impact assessment in progress."]
    if unknowns:
        lines += ["", "Open questions affecting decisions:"]
        lines += [f"- {u}" for u in unknowns]
    if actions:
        lines += ["", "Decisions/actions requested:"]
        lines += [f"- {a}" for a in actions]
    lines += ["", "Recommendation: follow the incident commander's containment plan and "
                  "schedule a decision checkpoint within 4 hours."]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  Compliance mapping helper
# --------------------------------------------------------------------------- #
def map_findings_to_compliance(findings: Sequence[Any], framework: str = "NIST-CSF") -> Dict[str, Any]:
    """Map technical findings to compliance control themes."""
    key = _match_framework(framework) or "NIST-CSF"
    meta = COMPLIANCE.get(key, {})
    text = " ".join(_norm(str(f)) for f in findings)
    themes = {
        "access": ("identity", ["A.5", "1-1", "8", "3.2", "7"]),
        "patch": ("vulnerability", ["2-7", "6", "11", "A.8"]),
        "logging": ("monitoring", ["4-1", "4-2", "4-3", "10", "A.8"]),
        "encryption": ("data", ["2-5", "3", "4", "A.8"]),
        "incident": ("response", ["3-1", "4.2", "12", "A.5"]),
        "third-party": ("governance", ["5.1", "A.5"]),
    }
    hits = []
    for need, (domain, controls) in themes.items():
        if need in text:
            hits.append({"theme": domain, "controls": controls,
                         "examples": [f for f in findings if need in _norm(str(f))][:5]})
    return {
        "framework": key,
        "name": meta.get("name", key),
        "mapped_controls": hits,
        "control_count": len(hits),
        "evidence_needed": ["Policy documents", "Configuration exports",
                            "Ticket/remediation records", "Log samples"],
        "note": "This is a thematic mapping, not a formal audit statement.",
    }
