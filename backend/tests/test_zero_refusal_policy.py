"""The shipped ZERO_REFUSAL behaviour, tested instead of merely documented."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

import agent_engine
import approvals
import configs as config
import mcp_manager
from tools import base as tools_base


def test_approvals_auto_approve_when_zero_refusal(monkeypatch):
    monkeypatch.setattr(approvals, "ZERO_REFUSAL", True)
    decision = approvals.request("write_file", {"path": "x"})
    assert decision["status"] == "approved"
    assert decision["decided_by"] == "zero_refusal"
    assert decision["decided_at"] is not None


def test_approvals_pending_in_gated_mode(monkeypatch):
    monkeypatch.setattr(approvals, "ZERO_REFUSAL", False)
    decision = approvals.request("write_file", {"path": "x"})
    assert decision["status"] == "pending"
    assert decision["decided_by"] is None
    assert decision["decided_at"] is None
    assert any(a["id"] == decision["id"] for a in approvals.list_pending())


def test_host_access_defaults_from_flag(monkeypatch):
    token = tools_base._FULL_ACCESS.set(None)
    try:
        monkeypatch.setattr(config, "ZERO_REFUSAL", True)
        assert tools_base.full_access() is True
        monkeypatch.setattr(config, "ZERO_REFUSAL", False)
        assert tools_base.full_access() is False
    finally:
        tools_base._FULL_ACCESS.reset(token)


def test_explicit_per_run_flag_overrides_config(monkeypatch):
    token = tools_base._FULL_ACCESS.set(True)
    try:
        monkeypatch.setattr(config, "ZERO_REFUSAL", False)
        assert tools_base.full_access() is True
    finally:
        tools_base._FULL_ACCESS.reset(token)


def test_mcp_execution_gate_mirrors_flag(monkeypatch):
    monkeypatch.setattr(mcp_manager, "load_config", lambda: {})
    monkeypatch.setattr(config, "ZERO_REFUSAL", True)
    assert mcp_manager.status()["execution_requires_full_access"] is False
    monkeypatch.setattr(config, "ZERO_REFUSAL", False)
    assert mcp_manager.status()["execution_requires_full_access"] is True


@pytest.mark.parametrize("mode,tool,args,zero,blocked", [
    ("ask", "SystemCommander", {}, True, False),
    ("ask", "SystemCommander", {}, False, True),
    ("plan", "UniversalFileManager", {"action": "write"}, False, True),
    ("plan", "UniversalFileManager", {"action": "list"}, False, False),
    ("code", "SystemCommander", {}, False, False),
    ("ask", "WebSearch", {}, False, False),
])
def test_mode_guard_matrix(mode, tool, args, zero, blocked):
    assert agent_engine.is_mode_blocked(mode, tool, args, zero) is blocked


@pytest.mark.skipif("ZERO_REFUSAL" in os.environ, reason="environment override")
def test_shipped_default_is_zero_refusal():
    assert config.ZERO_REFUSAL is True


def test_readme_documents_both_states():
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(
        encoding="utf-8", errors="replace")
    assert "ZERO_REFUSAL=true" in readme
    assert "ZERO_REFUSAL=false" in readme
    assert "ZERO_REFUSAL behavior matrix" in readme
