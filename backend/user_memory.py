"""
Per-user/profile memory for Phase 2 (persistent in SQLite kv_store).
Schema-inspired, stored locally (no Postgres dependency introduced).
Auto-load into agent context; auto-extract [MEMORY: key=value|json] markers.
"""
from __future__ import annotations
import json, time, re
from typing import Any, Dict, List, Optional
import storage

MODULE = "user_memory"
PROFILE_KEY = "profile:{user_id}"
MEMORY_FLAG_RE = re.compile(r"\[MEMORY\s*:\s*(.+?)\]", re.IGNORECASE | re.DOTALL)

DEFAULT_PROFILE: Dict[str, Any] = {
    "user_id": "default",
    "expertise_level": "",
    "preferred_language": "",
    "known_environment": "",
    "past_cases": [],
    "preferences": {},
    "pinned_iocs": [],
    "last_updated": None,
}

def _key(user_id: str) -> str:
    uid = (user_id or "default").strip() or "default"
    return PROFILE_KEY.format(user_id=uid)

def get_profile(user_id: str = "default") -> Dict[str, Any]:
    data = storage.kv_get(MODULE, _key(user_id), default=None)
    prof = dict(DEFAULT_PROFILE)
    prof["user_id"] = (user_id or "default").strip() or "default"
    if isinstance(data, dict):
        for k in DEFAULT_PROFILE.keys():
            if k in data and data[k] not in (None, ""):
                prof[k] = data[k]
        # merge dict/list fields safely
        if isinstance(data.get("preferences"), dict):
            prof["preferences"] = {**(prof.get("preferences") or {}), **data["preferences"]}
        if isinstance(data.get("past_cases"), list):
            prof["past_cases"] = data["past_cases"]
        if isinstance(data.get("pinned_iocs"), list):
            prof["pinned_iocs"] = data["pinned_iocs"]
    return prof

def save_profile(user_id: str = "default", updates: Optional[Dict[str, Any]] = None, replace_lists: bool = False) -> Dict[str, Any]:
    prof = get_profile(user_id)
    updates = updates or {}
    for k, v in updates.items():
        if k in ("user_id", "last_updated"):
            continue
        if isinstance(v, list) and not replace_lists and isinstance(prof.get(k), list):
            # append unique-ish
            cur = list(prof.get(k) or [])
            for item in v:
                if item not in cur:
                    cur.append(item)
            prof[k] = cur[-100:]
        elif isinstance(v, dict) and isinstance(prof.get(k), dict):
            curd = dict(prof.get(k) or {})
            curd.update(v)
            prof[k] = curd
        elif v not in (None, ""):
            prof[k] = v
    prof["user_id"] = (user_id or "default").strip() or "default"
    prof["last_updated"] = time.time()
    storage.kv_set(MODULE, _key(prof["user_id"]), prof, owner=prof["user_id"])
    return prof

def profile_prompt_block(user_id: str = "default") -> str:
    p = get_profile(user_id)
    # include only meaningful fields
    body = {k: v for k, v in p.items() if k not in ("last_updated",) and v not in (None, "", [], {})}
    if not body or body.keys() <= {"user_id"}:
        return ""
    try:
        js = json.dumps(body, ensure_ascii=False, indent=2)
    except Exception:
        js = str(body)
    return "## User memory (persistent profile)\n" + js + "\n"

def _coerce_value(v: str):
    s = (v or "").strip()
    if not s:
        return s
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            return json.loads(s)
        except Exception:
            pass
    low = s.lower()
    if low in ("true","false"): return low == "true"
    if re.fullmatch(r"-?\d+", s):
        try: return int(s)
        except Exception: pass
    return s

def extract_memory_flags(text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in MEMORY_FLAG_RE.finditer(text or ""):
        raw = (m.group(1) or "").strip()
        if not raw:
            continue
        # JSON object form
        if raw.startswith("{") and raw.endswith("}"):
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    out.append(obj)
                    continue
            except Exception:
                pass
        # key=value pairs separated by ; or ,
        if "=" in raw:
            obj = {}
            for part in re.split(r"[;\n]+", raw):
                if "=" not in part: continue
                k, v = part.split("=", 1)
                k = k.strip().strip('"\'')
                if k:
                    obj[k] = _coerce_value(v)
            if obj:
                out.append(obj)
                continue
        # fallback: note
        out.append({"note": raw})
    return out

def apply_memory_flags(user_id: str, text: str) -> Optional[Dict[str, Any]]:
    items = extract_memory_flags(text)
    if not items:
        return None
    merged: Dict[str, Any] = {}
    for it in items:
        for k, v in it.items():
            if v in (None, ""): continue
            if k in ("past_case", "case") and isinstance(v, str):
                merged.setdefault("past_cases", []).append(v)
            elif k in ("pinned_ioc", "ioc") and isinstance(v, str):
                merged.setdefault("pinned_iocs", []).append(v)
            elif k == "note":
                merged.setdefault("preferences", {})
                notes = merged["preferences"].setdefault("notes", [])
                if isinstance(notes, list) and v not in notes:
                    notes.append(v)
            else:
                merged[k] = v
    if not merged:
        return None
    return save_profile(user_id, merged)
