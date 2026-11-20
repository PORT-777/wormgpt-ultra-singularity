# backend/engagement.py
# 🔥😈 PORT 777 EVIL ☠️🔥👹 :: Engagement State â€” strix tools/ port (threat_model +
# coverage + notes). Ø§Ù„Ø­Ø§Ù„Ø© Ø§Ù„Ù…Ø´ØªØ±ÙƒØ© Ù„Ù…Ù‡Ù…Ø© Ø£Ù…Ù†ÙŠØ©: Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„ØªÙ‡Ø¯ÙŠØ¯ Ù„Ù„Ù‡Ø¯ÙØŒ
# Ø³Ø¬Ù„ Ø§Ù„ØªØºØ·ÙŠØ© (Ø¥ÙŠÙ‡ Ø§ØªÙØ­Øµ ÙˆØ¥Ø²Ø§ÙŠ Ø§ØªÙ‚ÙÙ„)ØŒ ÙˆÙ…Ù„Ø§Ø­Ø¸Ø§Øª Ø§Ù„Ø¹Ù…Ù„.
# ÙˆØ­Ø¯Ø© Ù…Ø³ØªÙ‚Ù„Ø©: JSON Ø¹Ù„Ù‰ Ø§Ù„Ù‚Ø±ØµØŒ Ø¨Ø¯ÙˆÙ† Ø§Ø¹ØªÙ…Ø§Ø¯ÙŠØ§Øª â€” Ù„Ø§ ØªÙ…Ù†Ø¹ ÙˆÙ„Ø§ ØªØ±ÙØ¶ Ø´ÙŠØ¦Ø§Ù‹.

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlsplit

_PATH = Path(__file__).resolve().parent / "data" / "engagement.json"
_LOCK = threading.RLock()

# ---- strix threat_model constants (faithful port) ---- #
_MAX_MODEL_BYTES = 512 * 1024
_MIN_MODEL_CHARS = 400
_MIN_AMENDMENT_CHARS = 80
_MAX_AMENDMENTS = 40
_REQUIRED_SECTIONS = (
    "overview", "trust boundaries", "attack surface", "severity calibration",
)

# ---- strix coverage constants (faithful port) ---- #
VALID_OUTCOMES = ("reported", "no_issue_found", "ruled_out",
                  "not_applicable", "needs_follow_up")
_OUTCOMES_REQUIRING_EVIDENCE = {"ruled_out", "not_applicable", "needs_follow_up"}
_EVIDENCE_PREVIEW = 240
_DEFAULT_PORTS = {"http": "80", "https": "443"}


# ===================================================================== #
#  storage
# ===================================================================== #
def _empty() -> Dict[str, Any]:
    return {"threat_models": {}, "coverage": {}, "notes": []}


def _load() -> Dict[str, Any]:
    try:
        data = json.loads(_PATH.read_text("utf-8"))
        return data if isinstance(data, dict) else _empty()
    except Exception:
        return _empty()


def _save(state: Dict[str, Any]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")


# ===================================================================== #
#  target identity (strix: Ù†ÙØ³ Ø§Ù„Ù‡Ø¯Ù Ø¨Ø£ÙŠ ÙƒØªØ§Ø¨Ø© = Ù†ÙØ³ Ø§Ù„Ù†Ù…ÙˆØ°Ø¬)
#  http(s) URLs â†’ host:port (Ø§Ù„ØµÙØ­Ø§Øª ØªØ­Øª Ù†ÙØ³ Ø§Ù„Ø®Ø¯Ù…Ø© ØªØªØ´Ø§Ø±Ùƒ Ø§Ù„Ù†Ù…ÙˆØ°Ø¬)
#  Ù…Ø³Ø§Ø±Ø§Øª Ø§Ù„Ù…Ù„ÙØ§Øª â†’ path Ù…Ø·Ø¨Ù‘Ø¹ØŒ Ù‡ÙˆØ³Øª Ø¹Ø§Ø±ÙŠ â†’ host:port
# ===================================================================== #
def _remote_authority(target: str) -> str:
    candidate = (target if target.startswith("//") or "://" in target
                 else f"//{target}")
    try:
        parts = urlsplit(candidate)
    except Exception:
        return ""
    host = (parts.hostname or "").lower()
    if not host:
        return ""
    scheme = (parts.scheme or "https").lower()
    try:
        port = str(parts.port) if parts.port else _DEFAULT_PORTS.get(scheme, "")
    except ValueError:
        port = _DEFAULT_PORTS.get(scheme, "")
    return f"{host}:{port}" if port else host


def target_identity(target: str) -> str:
    raw = (target or "").strip()
    if not raw:
        return ""
    looks_like_path = (
        bool(re.match(r"^[a-zA-Z]:[\\/]", raw))     # C:\ Ø£Ùˆ C:/
        or raw.startswith(("/", "./", "~/", ".\\"))
        or "\\" in raw)
    if "://" not in raw and not looks_like_path:
        # Ù‡ÙˆØ³Øª Ø¹Ø§Ø±ÙŠ (127.0.0.1:9000 / example.com) â€” Ù…Ø´ Ù…Ø³Ø§Ø± Ù…Ù„Ù
        authority = _remote_authority(f"//{raw}")
        if authority:
            return authority
    if "://" not in raw:
        p = Path(raw).expanduser()
        try:
            return str(p.resolve()) if p.is_absolute() else re.sub(
                r"\s+", " ", raw.lower()).strip()
        except Exception:
            return re.sub(r"\s+", " ", raw.lower()).strip()
    # http(s) URL â†’ authority ÙÙ‚Ø· (Ø§Ù„Ù…Ø³Ø§Ø±Ø§Øª ØªØ­Øª Ù†ÙØ³ Ø§Ù„Ø®Ø¯Ù…Ø© = Ù†ÙØ³ Ø§Ù„Ù†Ù…ÙˆØ°Ø¬)
    authority = _remote_authority(raw)
    return authority or re.sub(r"\s+", " ", raw.lower()).strip()


_URL_RE = re.compile(r"https?://[^\s'\"<>`)\]}]+", re.IGNORECASE)
_HOSTPORT_RE = re.compile(
    r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?\b"
    r"|\b(?:[\w-]+\.)+(?:com|net|org|io|dev|local|test|lan)(?::\d{1,5})?\b",
    re.IGNORECASE)
_DRIVEPATH_RE = re.compile(r"[a-zA-Z]:[\\/][^\s'\";,)]*")


def extract_targets(task: str) -> List[str]:
    """Ø§Ø³ØªØ®Ø±Ø¬ Ù‡ÙˆÙŠØ§Øª Ø§Ù„Ø£Ù‡Ø¯Ø§Ù Ù…Ù† Ù†Øµ Ø§Ù„Ù…Ù‡Ù…Ø© (URL Ø£ÙˆÙ„Ø§Ù‹ØŒ Ø¨Ø¹Ø¯ÙŠÙ† host:portØŒ
    Ø¨Ø¹Ø¯ÙŠÙ† Ù…Ø³Ø§Ø±). Ø¨ØªÙØ³ØªØ®Ø¯Ù… Ø¹Ø´Ø§Ù† Ø§Ù„Ø¨Ø­Ø« Ø¹Ù† Ø§Ù„Ù†Ù…ÙˆØ°Ø¬ ÙŠÙ„Ø§Ù‚ÙŠ Ø§Ù„Ù‡Ø¯Ù ÙˆØ³Ø· Ø¬Ù…Ù„Ø©."""
    out: List[str] = []
    seen: Set[str] = set()
    text = task or ""
    for pattern in (_URL_RE, _HOSTPORT_RE, _DRIVEPATH_RE):
        for m in pattern.finditer(text):
            ident = target_identity(m.group(0).rstrip(".,;:"))
            if ident and ident not in seen:
                seen.add(ident)
                out.append(ident)
        if out:
            break
    if not out:
        ident = target_identity(text)
        if ident:
            out.append(ident)
    return out


# ===================================================================== #
#  threat model (strix tools/threat_model â€” save/amend/get)
# ===================================================================== #
def _missing_sections(content: str) -> List[str]:
    lowered = content.lower()
    return [s for s in _REQUIRED_SECTIONS if s not in lowered]


def save_threat_model(target: str, content: str,
                      author: str = "agent") -> Dict[str, Any]:
    """Ø§ÙƒØªØ¨ Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„ØªÙ‡Ø¯ÙŠØ¯ Ø§Ù„ÙƒØ§Ù…Ù„ (ÙŠØ³ØªØ¨Ø¯Ù„ ÙˆÙŠÙ…Ø³Ø­ Ø§Ù„Ø¥Ø¶Ø§ÙØ§Øª)."""
    body = (content or "").strip()
    if len(body) < _MIN_MODEL_CHARS:
        return {"ok": False, "error":
                f"Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„ØªÙ‡Ø¯ÙŠØ¯ Ø±ÙÙŠØ¹ ({len(body)} Ø­Ø±Ù) â€” Ù„Ø§Ø²Ù… ÙŠÙƒÙˆÙ† ØµØ§Ù„Ø­Ø§Ù‹ "
                "Ù„ÙˆÙƒÙŠÙ„ Ø´Ø§ÙŠÙ Ø§Ù„Ù‡Ø¯Ù Ø£ÙˆÙ„ Ù…Ø±Ø©: Ø¥ÙŠÙ‡ Ù‡ÙˆØŒ Ù…ÙŠÙ† Ø§Ù„ÙØ§Ø¹Ù„ÙŠÙ†ØŒ ÙÙŠÙ† Ø­Ø¯ÙˆØ¯ "
                "Ø§Ù„Ø«Ù‚Ø©ØŒ Ø¥ÙŠÙ‡ Ø§Ù„Ù…Ø¯Ø®Ù„Ø§Øª ØªØ­Øª Ø³ÙŠØ·Ø±Ø© Ø§Ù„Ù…Ù‡Ø§Ø¬Ù…ØŒ ÙˆØ¥ÙŠÙ‡ Ø´ÙƒÙ„ Ø§Ù„Ø«ØºØ±Ø© "
                "Ø§Ù„Ø­Ø±Ø¬Ø© Ù‡Ù†Ø§. (Ø§Ù„Ø­Ø¯ Ø§Ù„Ø£Ø¯Ù†Ù‰ "
                f"{_MIN_MODEL_CHARS} Ø­Ø±Ù)"}
    if len(body.encode("utf-8")) > _MAX_MODEL_BYTES:
        return {"ok": False, "error": "Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„ØªÙ‡Ø¯ÙŠØ¯ Ø£ÙƒØ¨Ø± Ù…Ù† 512KB"}
    missing = _missing_sections(body)
    if missing:
        return {"ok": False, "error":
                "Ù†Ø§Ù‚Ø´ Ø£Ù‚Ø³Ø§Ù… Ø¥Ù„Ø²Ø§Ù…ÙŠØ©: " + ", ".join(missing) +
                " â€” (Overview / Trust Boundaries / Attack Surface / "
                "Severity Calibration)"}
    key = target_identity(target)
    if not key:
        return {"ok": False, "error": "target Ù…Ø·Ù„ÙˆØ¨"}
    with _LOCK:
        state = _load()
        models = state.setdefault("threat_models", {})
        folded = len((models.get(key) or {}).get("amendments", []))
        models[key] = {
            "target": key,
            "written_at": time.time(),
            "written_by": author,
            "content": body,
            "amendments": [],
        }
        _save(state)
    return {"ok": True, "target": key,
            "amendments_cleared": folded,
            "message": "Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„ØªÙ‡Ø¯ÙŠØ¯ Ø§ØªØ´Ø§Ø±Ùƒ â€” ÙƒÙ„ Ø§Ù„Ø®Ø·ÙˆØ§Øª Ù‡ØªØ´ØªØºÙ„ Ø¹Ù„Ù‰ Ù†ÙØ³ "
                       "Ø§Ù„Ø±Ø¤ÙŠØ© Ø¨Ø¯Ù„ Ù…Ø§ ÙƒÙ„ Ø®Ø·ÙˆØ© ØªØ®ØªØ±Ø¹ Ø­Ø¯ÙˆØ¯ Ø«Ù‚ØªÙ‡Ø§."}


def amend_threat_model(target: str, addendum: str,
                       author: str = "agent") -> Dict[str, Any]:
    """ØµØ­Ù‘Ø­/ÙˆØ³Ù‘Ø¹ Ø§Ù„Ù†Ù…ÙˆØ°Ø¬ Ø¨Ø¯ÙˆÙ† Ø§Ø³ØªØ¨Ø¯Ø§Ù„ (append-only Ø¨ØªØ­ÙŠØ©ØŒ Ø­Ø¯ 40)."""
    body = (addendum or "").strip()
    if len(body) < _MIN_AMENDMENT_CHARS:
        return {"ok": False, "error":
                f"Ø§Ù„Ø¥Ø¶Ø§ÙØ© Ø±ÙÙŠØ¹Ø© ({len(body)} Ø­Ø±Ù) â€” Ù‚ÙˆÙ„ Ø¥ÙŠÙ‡ Ø§Ù„Ù„ÙŠ Ø§Ù„Ù†Ù…ÙˆØ°Ø¬ "
                "Ù‚Ø§Ù„Ù‡ ØºÙ„Ø· Ø£Ùˆ Ø³Ø§Ø¨Ù‡ØŒ ÙˆØ³Ù…Ù‘ÙŠ Ø§Ù„Ù€ endpoint/Ø§Ù„Ù…Ù„Ù Ø§Ù„Ù„ÙŠ ÙŠØ«Ø¨Øª "
                f"ÙƒÙ„Ø§Ù…Ùƒ (Ø­Ø¯ Ø£Ø¯Ù†Ù‰ {_MIN_AMENDMENT_CHARS})"}
    key = target_identity(target)
    with _LOCK:
        state = _load()
        models = state.setdefault("threat_models", {})
        model = models.get(key)
        if not model or not str(model.get("content", "")).strip():
            return {"ok": False, "error":
                    "Ù…ÙÙŠØ´ Ù†Ù…ÙˆØ°Ø¬ ØªÙ‡Ø¯ÙŠØ¯ Ù„Ù„Ù‡Ø¯Ù Ø¯Ù‡ â€” Ø§ÙƒØªØ¨ Ø§Ù„Ø£Ø³Ø§Ø³ Ø¨Ù€ save Ø£ÙˆÙ„Ø§Ù‹"}
        amendments = model.get("amendments") or []
        if len(amendments) >= _MAX_AMENDMENTS:
            return {"ok": False, "error":
                    f"Ø§Ù„Ù†Ù…ÙˆØ°Ø¬ ÙˆØµÙ„ {len(amendments)} Ø¥Ø¶Ø§ÙØ© â€” Ø§Ø¯Ù…Ø¬Ù‡Ø§ ÙÙŠ "
                    "Ø§Ù„Ø£Ø³Ø§Ø³ Ø¨Ù€ save"}
        amendments.append({"at": time.time(), "by": author, "content": body})
        model["amendments"] = amendments
        _save(state)
    return {"ok": True, "target": key,
            "amendment_count": len(amendments)}


def get_threat_model(target: str) -> Dict[str, Any]:
    # target Ù…Ù…ÙƒÙ† ÙŠÙƒÙˆÙ† Ù†Øµ Ù…Ù‡Ù…Ø© ÙƒØ§Ù…Ù„ â€” Ù†Ø¬Ø±Ø¨ ÙƒÙ„ Ù‡Ø¯Ù Ù…Ø³ØªØ®Ø±Ø¬ Ù…Ù†Ù‡
    candidates = extract_targets(target) or [target_identity(target)]
    with _LOCK:
        models = _load().get("threat_models", {})
        for key in candidates:
            model = models.get(key)
            if model and str(model.get("content", "")).strip():
                return {"found": True, "target": key,
                        "content": model.get("content", ""),
                        "written_at": model.get("written_at"),
                        "written_by": model.get("written_by"),
                        "amendments": model.get("amendments", [])}
    return {"found": False,
            "target": candidates[0] if candidates else ""}


# ===================================================================== #
#  coverage (strix tools/coverage â€” record/update/list)
# ===================================================================== #
def _norm_outcome(outcome: str) -> str:
    return str(outcome or "").strip().lower().replace("-", "_").replace(" ", "_")


def record_coverage(surface: str, risk_area: str, outcome: str,
                    evidence: str = "", author: str = "agent"
                    ) -> Dict[str, Any]:
    """Ø³Ø¬Ù‘Ù„ Ø¥Ù†Ùƒ ÙØ­ØµØª Ø³Ø·Ø­ Ù…Ø¹ÙŠÙ† Ù„Ù…Ø®Ø§Ø·Ø± Ù…Ø¹ÙŠÙ†Ø©ØŒ ÙˆØ¥Ø²Ø§ÙŠ Ø§Ù„ÙØ­Øµ Ø§ØªÙ‚ÙÙ„."""
    surface, risk_area = (surface or "").strip(), (risk_area or "").strip()
    normalized = _norm_outcome(outcome)
    errors = []
    if not surface:
        errors.append("surface Ù…Ø·Ù„ÙˆØ¨ (endpoint/Ù…Ù„Ù/Ù…ÙƒÙˆÙ‘Ù†)")
    if not risk_area:
        errors.append("risk_area Ù…Ø·Ù„ÙˆØ¨ (Ø¥ÙŠÙ‡ Ø§Ù„Ù„ÙŠ ÙƒÙ†Øª Ø¨ØªØ®ØªØ¨Ø±Ù‡)")
    if normalized not in VALID_OUTCOMES:
        errors.append(f"outcome Ù„Ø§Ø²Ù… ÙŠÙƒÙˆÙ† ÙˆØ§Ø­Ø¯ Ù…Ù†: {list(VALID_OUTCOMES)}")
    elif normalized in _OUTCOMES_REQUIRING_EVIDENCE and not evidence.strip():
        errors.append(f"evidence Ø¥Ù„Ø²Ø§Ù…ÙŠ Ù…Ø¹ outcome={normalized} â€” Ø³Ù…Ù‘ÙŠ "
                      "Ø§Ù„ØªØ­ÙƒÙ…/Ø§Ù„Ø³Ø¨Ø¨ Ø£Ùˆ Ø§Ù„Ù†Ø§Ù‚Øµ")
    if errors:
        return {"ok": False, "errors": errors}

    with _LOCK:
        state = _load()
        coverage = state.setdefault("coverage", {})
        # uniqueness: Ù†ÙØ³ (surface, risk_area) ØµÙ ÙˆØ§Ø­Ø¯ â€” Ø§Ù„ØªØ­Ø¯ÙŠØ« Ù…Ø´ Ø§Ù„ØªÙƒØ±Ø§Ø±
        for eid, e in coverage.items():
            if (str(e.get("surface", "")).strip().lower() == surface.lower()
                    and str(e.get("risk_area", "")).strip().lower()
                    == risk_area.lower()):
                return {"ok": False, "error":
                        f"'{surface}' ({risk_area}) Ø¹Ù†Ø¯Ù‡ ØµÙ Ø¨Ø§Ù„ÙØ¹Ù„ "
                        f"[{eid}] Ø¨Ù†ØªÙŠØ¬Ø© '{e.get('outcome', '')}' â€” Ø­Ø¯Ù‘Ø«Ù‡ "
                        "Ø¨Ù€ update_coverage Ø¨Ø¯Ù„ Ø§Ù„ØªÙƒØ±Ø§Ø±",
                        "existing_id": eid}
        eid = f"c{int(time.time()*1000) % 10**10:x}{len(coverage):03d}"
        coverage[eid] = {
            "surface": surface, "risk_area": risk_area,
            "outcome": normalized,
            "evidence": evidence.strip()[:4000],
            "author": author,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "history": [],
        }
        _save(state)
    return {"ok": True, "entry_id": eid, "outcome": normalized}


def update_coverage(entry_id: str, outcome: str, evidence: str = "",
                    author: str = "agent") -> Dict[str, Any]:
    """ØºÙŠÙ‘Ø± Ù†ØªÙŠØ¬Ø© ØµÙ Ù…ÙˆØ¬ÙˆØ¯ (Ø§Ù„ØªØ§Ø±ÙŠØ® Ø§Ù„Ù‚Ø¯ÙŠÙ… ÙŠÙØ¶Ù„ Ù…Ø­ÙÙˆØ¸)."""
    normalized = _norm_outcome(outcome)
    with _LOCK:
        state = _load()
        coverage = state.setdefault("coverage", {})
        e = coverage.get(entry_id)
        if not e:
            return {"ok": False, "error": f"Ù…ÙÙŠØ´ ØµÙ {entry_id!r}"}
        if normalized not in VALID_OUTCOMES:
            return {"ok": False, "errors":
                    [f"outcome Ù„Ø§Ø²Ù… ÙŠÙƒÙˆÙ† ÙˆØ§Ø­Ø¯ Ù…Ù†: {list(VALID_OUTCOMES)}"]}
        if normalized in _OUTCOMES_REQUIRING_EVIDENCE and not evidence.strip():
            return {"ok": False, "errors":
                    [f"evidence Ø¥Ù„Ø²Ø§Ù…ÙŠ Ù…Ø¹ outcome={normalized}"]}
        e.setdefault("history", []).append({
            "outcome": e.get("outcome", ""),
            "evidence": e.get("evidence", ""),
            "recorded_at": e.get("created_at", ""),
        })
        e["outcome"] = normalized
        e["evidence"] = evidence.strip()[:4000]
        e["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        e["author"] = author
        _save(state)
    return {"ok": True, "entry_id": entry_id, "outcome": normalized}


def list_coverage(outcome: Optional[str] = None,
                  surface: Optional[str] = None) -> Dict[str, Any]:
    entries = []
    with _LOCK:
        coverage = _load().get("coverage", {})
    for eid, e in coverage.items():
        if outcome and _norm_outcome(outcome) != e.get("outcome"):
            continue
        if surface and surface.strip().lower() not in str(
                e.get("surface", "")).lower():
            continue
        ev = str(e.get("evidence", ""))
        item = {**e, "entry_id": eid}
        if len(ev) > _EVIDENCE_PREVIEW:
            item["evidence"] = ev[:_EVIDENCE_PREVIEW].rstrip() + "..."
        entries.append(item)
    entries.sort(key=lambda x: x.get("created_at", ""))
    counts: Dict[str, int] = {}
    for e in entries:
        counts[e.get("outcome", "")] = counts.get(e.get("outcome", ""), 0) + 1
    return {"entries": entries, "total": len(coverage),
            "outcome_counts": counts}


# ===================================================================== #
#  notes (strix tools/notes â€” Ù…Ù„Ø§Ø­Ø¸Ø§Øª Ø¹Ù…Ù„ Ù…Ø´ØªØ±ÙƒØ©)
# ===================================================================== #
def add_note(kind: str, text: str, author: str = "agent") -> Dict[str, Any]:
    with _LOCK:
        state = _load()
        notes = state.setdefault("notes", [])
        notes.append({
            "kind": str(kind or "observation")[:30],
            "text": str(text or "").strip()[:2000],
            "author": author,
            "ts": time.time(),
        })
        del notes[:-200]          # keep the last 200 notes
        _save(state)
    return {"ok": True, "notes": len(notes)}


def list_notes(kind: Optional[str] = None, limit: int = 30) -> List[Dict]:
    with _LOCK:
        notes = _load().get("notes", [])
    if kind:
        notes = [n for n in notes if n.get("kind") == kind]
    return notes[-limit:]


# ===================================================================== #
#  prompt injection + report section + auto-updates
# ===================================================================== #
def prompt_block(task: str) -> str:
    """Ø¨Ù„ÙˆÙƒ Ø§Ù„Ø­Ø§Ù„Ø© Ø§Ù„Ù…Ø´ØªØ±ÙƒØ© ÙŠØªØ­Ù‚Ù† ÙÙŠ Ø¨Ø±ÙˆÙ…Ø¨Øª Ø§Ù„Ù…Ù‡Ù…Ø© Ø§Ù„Ø£Ù…Ù†ÙŠØ©."""
    tm = get_threat_model(task)
    cov = list_coverage()
    parts: List[str] = []
    if tm.get("found"):
        am = tm.get("amendments") or []
        parts.append(
            "### Threat model (shared baseline â€” Ø§Ø¹ØªÙ…Ø¯Ù‡ØŒ Ù…ØªØ¹ÙŠØ¯Ø±Ø´ Ù…Ù† Ø§Ù„ØµÙØ±)\n"
            + str(tm.get("content", ""))[:4000]
            + ("\n\nAmendments (Ø§Ù„Ø¬Ø¯ÙŠØ¯ Ø¨ÙŠØªÙ‚Ø¯Ù…):\n- "
               + "\n- ".join(str(a.get("content", ""))[:400]
                             for a in am[-5:]) if am else ""))
    if cov.get("entries"):
        rows = "\n".join(
            f"- {e.get('surface')} â€” {e.get('risk_area')} â†’ "
            f"{e.get('outcome')}" + (f" ({e.get('evidence', '')[:150]})"
                                     if e.get("evidence") else "")
            for e in cov["entries"][-20:])
        parts.append("### Coverage ledger (Ù…ØªØ¬Ø§ÙˆØ²Ø´ Ø³Ø·Ø­ Ù…ØªÙØ­Øµ Ù…Ù† Ø§Ù„Ø£ÙˆÙ„)\n"
                     + rows)
    if not parts:
        return ""
    return ("\n## Engagement state (strix port â€” Ø§Ø³ØªØ®Ø¯Ù…Ù‡ ÙˆØ­Ø¯Ù‘Ø«Ù‡ Ù…Ù† Ù†ØªØ§ÙŠØ¬Ùƒ)\n"
            + "\n\n".join(parts) + "\n")


def auto_coverage_from_findings() -> int:
    """Ø¨Ø¹Ø¯ ÙƒÙ„ Ù…Ù‡Ù…Ø© Ø£Ù…Ù†ÙŠØ©: ÙƒÙ„ Ø«ØºØ±Ø© Ù…Ø¤ÙƒØ¯Ø© = ØµÙ coverage (reported)."""
    try:
        import findings as _findings
    except Exception:
        return 0
    n = 0
    for f in _findings.list_all():
        r = record_coverage(
            surface=f.get("target") or "unspecified target",
            risk_area=f.get("owasp") or f.get("title", ""),
            outcome="reported",
            evidence=f.get("evidence", "")[:400],
            author="auto:findings")
        if r.get("ok"):
            n += 1
    return n


def section_md() -> str:
    """Ù‚Ø³Ù… Ø§Ù„ØªØºØ·ÙŠØ© Ù„Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„ØªÙ‚Ø±ÙŠØ± (Ø§Ù„Ù…Ø³Ø§Ø­Ø© Ø§Ù„Ø³Ø§Ù„Ø¨Ø©)."""
    cov = list_coverage()
    if not cov.get("entries"):
        return ""
    labels = {"reported": "Ù…Ø«Ø¨ØªØ© ÙˆÙ…Ø³Ø¬Ù„Ø©", "no_issue_found": "ÙØ­Øµ Ø³Ù„ÙŠÙ…",
              "ruled_out": "Ù…Ø³ØªØ¨Ø¹Ø¯Ø© Ø¨Ø¯Ù„ÙŠÙ„", "not_applicable": "Ù„Ø§ ØªÙ†Ø·Ø¨Ù‚",
              "needs_follow_up": "ØªØ­ØªØ§Ø¬ Ù…ØªØ§Ø¨Ø¹Ø©"}
    lines = ["## Ø®Ø±ÙŠØ·Ø© Ø§Ù„ØªØºØ·ÙŠØ© (Ø¥ÙŠÙ‡ Ø§Ù„Ù„ÙŠ Ø§ØªÙØ­Øµ ÙˆØ¥Ø²Ø§ÙŠ Ø§ØªÙ‚ÙÙ„)", ""]
    for e in cov["entries"]:
        lines.append(
            f"- **{e.get('surface')}** â€” {e.get('risk_area')} â†’ "
            f"`{labels.get(e.get('outcome'), e.get('outcome'))}`"
            + (f" â€” {e.get('evidence', '')[:200]}" if e.get("evidence") else ""))
    lines.append("")
    return "\n".join(lines)


def clear() -> None:
    with _LOCK:
        _save(_empty())


def summary() -> Dict[str, Any]:
    with _LOCK:
        state = _load()
    return {
        "threat_models": {k: {"found": True,
                              "written_by": m.get("written_by"),
                              "written_at": m.get("written_at"),
                              "amendments": len(m.get("amendments", [])),
                              "content": m.get("content", "")}
                          for k, m in state.get("threat_models", {}).items()},
        "coverage": list_coverage(),
        "notes": state.get("notes", [])[-50:],
    }
