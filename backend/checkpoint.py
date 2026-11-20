from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import difflib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Storage lives OUTSIDE chat history. Resolve to backend/data when running from
# 🔥😈 PORT 777 EVIL ☠️🔥👹 backend; DATA_DIR env can override for tests/ops.
def _data_dir() -> Path:
    env = os.environ.get("DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve().parent
    # .../backend/checkpoint.py -> .../backend/data
    return (here / "data").resolve()


CKPT_ROOT = _data_dir() / "checkpoints"
CKPT_ROOT.mkdir(parents=True, exist_ok=True)

MAX_PER_SESSION = 30
MAX_BYTES_PER_SESSION = 50 * 1024 * 1024  # 50MB hard limit

# Never snapshot sensitive/protected content. Protection mode extends this list.
DEFAULT_DENY_PATTERNS = [
    r"(^|[\\/])\.env($|\.)",
    r"(^|[\\/]).*key.*",
    r"(^|[\\/]).*token.*",
    r"(^|[\\/])\.git([\\/]|$)",
    r"(^|[\\/])node_modules([\\/]|$)",
    r"(^|[\\/])checkpoints([\\/]|$)",
    r"\.(pem|key|p12|pfx|kdbx)$",
]

KEY_PATTERNS = [
    r"sk-[A-Za-z0-9]{8,}",
    r"gsk_[A-Za-z0-9]{8,}",
    r"nvapi-[A-Za-z0-9]{8,}",
    r"AIza[A-Za-z0-9_\-]{10,}",
    r"sk-or-[A-Za-z0-9\-]{8,}",
    r"ghp_[A-Za-z0-9]{8,}",
    r"xox[baprs]-[A-Za-z0-9\-]{8,}",
    r"Bearer\s+[A-Za-z0-9\-_.]{12,}",
]


def _protection_extra_patterns() -> List[str]:
    # Protection mode extends exclusions via env or settings module when present.
    extra = os.environ.get("CHECKPOINT_DENY_EXTRA", "").strip()
    pats = [p for p in extra.split(",") if p.strip()]
    try:
        import configs.settings as settings  # type: ignore
        if getattr(settings, "PROTECTION_MODE", False) or getattr(settings, "CHECKPOINT_PROTECTION", False):
            pats.extend(getattr(settings, "CHECKPOINT_DENY_PATTERNS", []) or [])
            pats.extend([r"(^|[\\/]).*secret.*", r"(^|[\\/]).*credential.*", r"\.sqlite(-wal|-shm)?$"])
    except Exception:
        pass
    return pats


def _is_denied(path: Path) -> bool:
    s = str(path).replace("/", "\\").lower()
    all_pats = DEFAULT_DENY_PATTERNS + _protection_extra_patterns()
    for pat in all_pats:
        try:
            if re.search(pat, s, re.I):
                return True
        except re.error:
            if pat.lower() in s:
                return True
    return False


def mask_sensitive_text(text: str) -> str:
    out = text
    for pat in KEY_PATTERNS:
        try:
            out = re.sub(pat, lambda m: _mask_token(m.group(0)), out)
        except re.error:
            continue
    # generic long token-ish assignments
    out = re.sub(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?([A-Za-z0-9\-_.]{12,})",
                 r"\1=<REDACTED>", out)
    return out


def _mask_token(v: str) -> str:
    if len(v) <= 10:
        return "<REDACTED>"
    return v[:4] + "••••" + v[-4:]


def _session_dir(sid: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", sid or "default")[:120] or "default"
    d = CKPT_ROOT / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


def _manifest_path(d: Path) -> Path:
    return d / "manifest.json"


def _read_manifest(d: Path) -> Optional[Dict[str, Any]]:
    p = _manifest_path(d)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _session_total_bytes(sdir: Path) -> int:
    total = 0
    for p in sdir.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def list_checkpoints(sid: str) -> List[Dict[str, Any]]:
    d = _session_dir(sid)
    items: List[Tuple[float, Dict[str, Any]]] = []
    for p in d.iterdir():
        if not p.is_dir():
            continue
        man = _read_manifest(p)
        if not man:
            continue
        man.setdefault("session_id", sid)
        items.append((float(man.get("ts") or 0), man))
    items.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in items]


def _prune_session(sid: str) -> None:
    d = _session_dir(sid)
    cps = list_checkpoints(sid)  # newest first
    # keep last MAX_PER_SESSION
    for man in cps[MAX_PER_SESSION:]:
        cid = man.get("id")
        if cid:
            shutil.rmtree(d / str(cid), ignore_errors=True)
    # hard byte cap: prune oldest
    cps = list_checkpoints(sid)
    while cps and _session_total_bytes(d) > MAX_BYTES_PER_SESSION:
        oldest = cps.pop()  # newest-first list
        cid = oldest.get("id")
        if not cid:
            break
        shutil.rmtree(d / str(cid), ignore_errors=True)


def _normalize_file(path_like: str) -> Optional[Path]:
    try:
        p = Path(str(path_like)).expanduser()
        # resolve when possible for stable manifests; tolerate non-existent targets
        try:
            return p.resolve()
        except OSError:
            return p.absolute()
    except Exception:
        return None


def create_checkpoint(sid: str, mid: str, files: List[str], *, kind: str = "auto") -> Dict[str, Any]:
    sid = sid or "default"
    cid = f"cp_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    d = _session_dir(sid) / cid
    d.mkdir(parents=True, exist_ok=True)
    manifest: Dict[str, Any] = {
        "id": cid,
        "session_id": sid,
        "message_id": mid or "",
        "ts": time.time(),
        "kind": kind,
        "files": [],
        "skipped": [],
    }
    seen = set()
    for f in files or []:
        src = _normalize_file(f)
        if not src:
            continue
        key = str(src).lower()
        if key in seen:
            continue
        seen.add(key)
        if _is_denied(src):
            manifest["skipped"].append({"path": str(src), "reason": "denied"})
            continue
        if not src.exists() or not src.is_file():
            manifest["skipped"].append({"path": str(src), "reason": "missing"})
            continue
        try:
            data = src.read_bytes()
        except OSError as e:
            manifest["skipped"].append({"path": str(src), "reason": str(e)[:120]})
            continue
        rel_name = f"{len(manifest['files']):04d}_{re.sub(r'[^A-Za-z0-9._-]+', '_', src.name)[:120] or 'file'}"
        backup = d / rel_name
        backup.write_bytes(data)
        manifest["files"].append({
            "path": str(src),
            "size": len(data),
            "hash": hashlib.sha256(data).hexdigest(),
            "backup_path": str(backup),
            "backup_name": rel_name,
        })
    _manifest_path(d).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _prune_session(sid)
    return manifest


def _find_checkpoint(cid: str, sid: str = "") -> Tuple[Path, Dict[str, Any]]:
    if sid:
        d = _session_dir(sid) / cid
        man = _read_manifest(d)
        if man:
            return d, man
    # search all sessions
    if CKPT_ROOT.exists():
        for sdir in CKPT_ROOT.iterdir():
            if not sdir.is_dir():
                continue
            d = sdir / cid
            man = _read_manifest(d)
            if man:
                return d, man
    raise FileNotFoundError(f"checkpoint not found: {cid}")


def _read_text_masked(p: Path) -> str:
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return mask_sensitive_text(txt)


def diff_checkpoint(cid: str, sid: str = "") -> str:
    d, man = _find_checkpoint(cid, sid)
    out: List[str] = []
    for f in man.get("files", []):
        target = Path(f["path"])
        backup_name = f.get("backup_name") or Path(f.get("backup_path", "")).name
        backup = d / backup_name
        old = _read_text_masked(backup).splitlines(keepends=False)
        new = _read_text_masked(target).splitlines(keepends=False) if target.exists() else []
        diff = "\n".join(difflib.unified_diff(
            old, new,
            fromfile=f"a/{target}",
            tofile=f"b/{target}",
            lineterm="",
        ))
        if not diff:
            diff = f"--- a/{target}\n+++ b/{target}\n@@ no changes @@"
        out.append(diff)
    return "\n\n".join(out) if out else "(no files in checkpoint)"


def revert_checkpoint(cid: str, sid: str = "") -> Dict[str, Any]:
    d, man = _find_checkpoint(cid, sid)
    sid_eff = str(man.get("session_id") or sid or "default")
    # Fail-safe: snapshot current state BEFORE restore.
    current_paths = [f["path"] for f in man.get("files", []) if f.get("path")]
    pre = create_checkpoint(sid_eff, f"pre-revert:{cid}", current_paths, kind="pre-revert")
    restored: List[str] = []
    for f in man.get("files", []):
        backup_name = f.get("backup_name") or Path(f.get("backup_path", "")).name
        backup = d / backup_name
        target = Path(f["path"])
        if not backup.exists():
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, target)
            restored.append(str(target))
        except OSError:
            continue
    return {"restored": restored, "pre_revert_checkpoint": pre.get("id")}
