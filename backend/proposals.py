"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Proposal workflow (human-in-the-loop change control).

The agent NEVER applies changes by itself. When it wants to improve
itself â€” or hand the user a ready patch â€” it submits a proposal:

    ProposalChange -> proposals table (SQLite)
                   + a human-readable .md copy under
                     workspace/proposals/pending/

The user then APPROVES (content is materialized into the workspace
sandbox â€” host targets are exported for manual apply, never touched)
or REJECTS from the UI.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List, Optional

import configs as config
import storage


def _md_path(target: str, status: str, pid: int) -> Path:
    name = Path(str(target)).name or f"proposal-{pid}"
    if not name.endswith(".md"):
        name += ".md"
    return config.WORKSPACE_DIR / "proposals" / status / f"p{pid}-{name}"


def submit(title: str, target: str, rationale: str, content: str,
           session_id: str = "") -> int:
    """Record a proposal + drop a reviewable .md in the workspace."""
    pid = storage.add_proposal(title=title, target=target,
                               rationale=rationale, content=content,
                               session_id=session_id)
    path = _md_path(target, "pending", pid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Proposal #{pid}: {title}\n\n"
        f"- target: `{target}`\n"
        f"- submitted: {time.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"## Rationale\n{rationale}\n\n"
        f"## Proposed content\n```\n{content}\n```\n",
        encoding="utf-8")
    return pid


def list_proposals(status: Optional[str] = None) -> List[dict]:
    return storage.list_proposals(status)


def reject(pid: int) -> Dict:
    row = storage.get_proposal(pid)
    if not row:
        return {"ok": False, "error": "no such proposal"}
    if row["status"] != "pending":
        return {"ok": False, "error": f"already {row['status']}"}
    storage.set_proposal_status(pid, "rejected")
    try:                      # tidy: remove the pending .md preview
        _md_path(row["target"], "pending", pid).unlink(missing_ok=True)
    except Exception:
        pass
    return {"ok": True, "status": "rejected"}


def _resolve_target(target: str) -> Optional[Path]:
    """Resolve a proposal target into a safe write destination, or None
    when the target must go through the manual-import flow (absolute
    host paths are never auto-written).

      '@something/...'  -> agent's OWN tree (BACKEND_DIR), traversal-guarded
      'relative/...'    -> workspace sandbox
    """
    target = str(target).strip()
    root = config.WORKSPACE_DIR.resolve()
    if target.startswith("@"):
        base = config.BACKEND_DIR.resolve()
        rel = target[1:].strip("/\\").replace("\\", "/")
        dest = (base / rel).resolve()
        if base != dest and base not in dest.parents:
            return None
        return dest
    dest = (root / target.strip("/\\").replace("\\", "/")).resolve()
    if root != dest and root not in dest.parents:
        return None
    return dest


def apply_proposal(pid: int) -> Dict:
    """Human-approved: materialize the content.

    Sandbox rule: targets resolving INSIDE the workspace are written
    directly. Anything pointing at the host (outside WORKSPACE_DIR) is
    NEVER auto-written â€” the content is exported under
    workspace/proposals/imported/ for the user to apply manually.
    """
    row = storage.get_proposal(pid)
    if not row:
        return {"ok": False, "error": "no such proposal"}
    if row["status"] != "pending":
        return {"ok": False, "error": f"already {row['status']}"}

    target = str(row["target"])
    dest = _resolve_target(target)

    if dest is not None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(str(row["content"]), encoding="utf-8")
        storage.set_proposal_status(pid, "applied")
        try:
            _md_path(target, "applied", pid).unlink(missing_ok=True)
        except Exception:
            pass
        rel = dest.relative_to(dest.anchor)  # human-readable tail
        return {"ok": True, "status": "applied",
                "written": str(rel), "bytes": len(str(row["content"]))}

    # host target -> export only; the human applies it themselves
    imported = _md_path(target, "imported", pid)
    imported.parent.mkdir(parents=True, exist_ok=True)
    imported.write_text(
        f"# Proposal #{pid}: {row['title']} (imported for manual apply)\n\n"
        f"- target: `{target}`\n\n```\n{row['content']}\n```\n",
        encoding="utf-8")
    storage.set_proposal_status(pid, "approved")
    return {"ok": True, "status": "approved",
            "note": "target is outside the workspace sandbox â€” content "
                    f"exported to proposals/imported/{imported.name} "
                    "for manual apply"}
