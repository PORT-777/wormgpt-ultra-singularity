"""Tests for the proposal workflow (human-in-the-loop change control)."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import configs as config


@pytest.fixture()
def proposals(tmp_path, monkeypatch):
    import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(storage, "AUDIT_JSONL", tmp_path / "a.jsonl")
    storage._CONN = None                      # reopen at tmp path
    storage.init()
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    import importlib
    import proposals as pro
    importlib.reload(pro)
    yield pro
    storage._CONN = None                      # leave nothing dangling


def _run(coro):
    return asyncio.run(coro)


def test_submit_writes_reviewable_copy(proposals, tmp_path):
    pid = proposals.submit("fix fusion", "notes.md",
                           "clearer wording", "new content here")
    assert pid > 0
    md = tmp_path / "proposals" / "pending" / f"p{pid}-notes.md"
    assert md.is_file() and "new content here" in md.read_text("utf-8")


def test_approve_applies_inside_workspace(proposals, tmp_path):
    pid = proposals.submit("patch a", "docs/readme.md", "why",
                           "REWRITTEN TEXT")
    result = proposals.apply_proposal(pid)
    assert result["ok"] and result["status"] == "applied"
    got = tmp_path / "docs" / "readme.md"
    assert got.read_text("utf-8") == "REWRITTEN TEXT"


def test_approve_agent_own_tree_via_at_prefix(tmp_path, proposals):
    # hermetic: point the '@' root at a temp agent tree, not the repo
    fake_backend = tmp_path / "agent_tree"
    (fake_backend / "skills_packs").mkdir(parents=True)
    import configs
    proposals.config.BACKEND_DIR = fake_backend
    pid = proposals.submit("self-playbook", "@skills_packs/new.yaml",
                           "more playbooks", "name: new\ninstructions: x\n")
    result = proposals.apply_proposal(pid)
    proposals.config.BACKEND_DIR = config.BACKEND_DIR   # restore
    assert result["ok"] and result["status"] == "applied"
    assert "new.yaml" in result["written"]
    assert (fake_backend / "skills_packs" / "new.yaml").is_file()


def test_host_target_never_auto_applied(tmp_path, proposals):
    # make the sandbox a SUBdir of tmp_path so tmp_path itself counts as
    # "outside the sandbox" — host targets must never be auto-written
    import configs
    proposals.config.WORKSPACE_DIR = tmp_path / "ws"
    proposals.config.WORKSPACE_DIR.mkdir()
    pid = proposals.submit("host change", str(tmp_path / "outside.txt"),
                           "risky", "content")
    result = proposals.apply_proposal(pid)
    proposals.config.WORKSPACE_DIR = config.WORKSPACE_DIR      # restore
    assert result["status"] == "approved"     # human-cleared, but...
    ws = tmp_path / "ws"
    assert not (tmp_path / "outside.txt").exists()   # ...never auto-written
    imported = ws / "proposals" / "imported"
    assert imported.is_dir() and any(imported.iterdir())


def test_double_apply_is_rejected(proposals, tmp_path):
    pid = proposals.submit("x", "a.md", "why", "cc")
    assert proposals.apply_proposal(pid)["ok"]
    second = proposals.apply_proposal(pid)
    assert not second["ok"] and "already applied" in second["error"]


def test_reject_removes_pending_copy(proposals, tmp_path):
    pid = proposals.submit("junk", "a.md", "why", "cc")
    assert proposals.reject(pid)["ok"]
    assert not (tmp_path / "proposals" / "pending").exists() \
        or not any((tmp_path / "proposals" / "pending").iterdir())
