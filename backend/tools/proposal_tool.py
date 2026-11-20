"""
Tool :: ProposalChange

The agent's ONLY sanctioned way to change things it does not own at
runtime — its own playbooks/behavior, or to hand the user a ready and
reviewed patch. Nothing is applied at tool time: the proposal is stored
and waits for explicit human APPROVE in the UI.

Targets:
  '@backend/agent_engine.py'  -> agent's own tree (applied on approval)
  'notes.md'                  -> workspace file (applied on approval)
  'C:/abs/path/...'           -> NEVER auto-written; content exported
                                 for manual apply on approval.
"""
from __future__ import annotations

from typing import Any

import proposals
from .base import Tool


class ProposalChange(Tool):
    name = "ProposalChange"
    description = (
        "Submit a change proposal for HUMAN approval (nothing is applied "
        "at submit time): {'title', 'target_path', 'rationale', "
        "'content'} where content is the FULL proposed new file text. "
        "Prefix target with '@' to address this agent's own backend "
        "tree. Use for self-improvement and reviewed patches; the user "
        "approves or rejects from the UI."
    )
    example = {"title": "harden citation rule",
               "target_path": "@backend/skills_packs/offset_play.yaml",
               "rationale": "add block-hash cross-check step",
               "content": "name: offset_play\ninstructions: | ..."}

    async def run(self, title: str = "", target_path: str = "",
                  rationale: str = "", content: str = "",
                  **_: Any) -> str:
        try:
            if not title.strip():
                return "ERROR: title required"
            if not str(target_path).strip():
                return "ERROR: target_path required"
            if not str(content).strip():
                return "ERROR: content required (full proposed file text)"
            if proposals is None:
                return "ERROR: proposal subsystem unavailable"
            pid = proposals.submit(title=str(title).strip(),
                                   target=str(target_path).strip(),
                                   rationale=str(rationale)[:4000],
                                   content=str(content))
            return (f"OK: proposal #{pid} submitted '{title}' -> "
                    f"{target_path}. Status: pending — awaiting human "
                    "approval in the UI (workspace/proposals/pending/ "
                    "holds the reviewable copy).")
        except Exception as exc:
            return f"ERROR: proposal failed: {exc}"
