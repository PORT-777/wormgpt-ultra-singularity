"""Auto-backup scheduler: daily snapshot to disk."""
from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Optional

_LAST_BACKUP: float = 0.0
_INTERVAL = 24 * 3600


def maybe_backup(backup_dir: str = "data/backups", force: bool = False) -> Optional[str]:
    global _LAST_BACKUP
    now = time.time()
    if not force and (now - _LAST_BACKUP) < _INTERVAL:
        return None
    d = Path(backup_dir)
    d.mkdir(parents=True, exist_ok=True)
    from backup import to_json
    fname = d / f"backup_{int(now)}.json"
    fname.write_text(to_json(), encoding="utf-8")
    _LAST_BACKUP = now
    # prune old (keep 7)
    files = sorted(d.glob("backup_*.json"))
    for f in files[:-7]:
        try:
            f.unlink()
        except Exception:
            pass
    return str(fname)


def last_backup_time() -> float:
    return _LAST_BACKUP
