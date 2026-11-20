"""Tests for the AI Computer subsystem using an in-test fake provider only.

No cloud credentials or Docker are used here. The fake provider exists solely
to verify manager/tool/DB wiring; production adapters are tested separately.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import configs as config
from computer.manager import _PROVIDERS, ComputerManager
from computer.provider import ComputerInfo, ExecResult, FileInfo, ProcessInfo, Resources, SandboxProvider
from tools import TOOL_REGISTRY


class FakeProvider(SandboxProvider):
    name = "fake-test"

    def configured(self) -> bool:
        return True

    def create(self, *, computer_id, mode, resources, image=""):
        self.refs = getattr(self, "refs", {})
        self.refs[computer_id] = f"fake-{computer_id}"
        return ComputerInfo(computer_id, self.name, mode, "running", "Fake Linux", resources,
                            {"provider_ref": self.refs[computer_id], "isolation": "test"})

    def start(self, computer_id, provider_ref):
        return ComputerInfo(computer_id, self.name, "persistent", "running")

    def stop(self, computer_id, provider_ref):
        return ComputerInfo(computer_id, self.name, "persistent", "stopped")

    def restart(self, computer_id, provider_ref):
        return ComputerInfo(computer_id, self.name, "persistent", "running")

    def delete(self, computer_id, provider_ref):
        return True

    def execute(self, computer_id, provider_ref, command, *, cwd="", timeout=60, env=None, session_id=""):
        return ExecResult(True, 0, f"fake-exec:{command}", "", 1, session_id)

    def list_files(self, computer_id, provider_ref, path):
        return [FileInfo(path + "/a.txt", False, 3, 1)]

    def read_file(self, computer_id, provider_ref, path):
        return "hello"

    def write_file(self, computer_id, provider_ref, path, content):
        return True

    def delete_file(self, computer_id, provider_ref, path):
        return True

    def list_processes(self, computer_id, provider_ref):
        return [ProcessInfo("1", "bash")]

    def stop_process(self, computer_id, provider_ref, pid):
        return True

    def resources(self, computer_id, provider_ref):
        return {"source": "fake", "raw": "cpu=1"}

    def screenshot(self, computer_id, provider_ref):
        return None


@pytest.fixture()
def manager(monkeypatch):
    monkeypatch.setitem(_PROVIDERS, "fake-test", FakeProvider())
    monkeypatch.setattr(config, "COMPUTER_PROVIDER", "fake-test")
    return ComputerManager()


def test_computer_lifecycle_and_execution(manager):
    row = manager.create(user_id="tester", mode="temporary")
    assert row["status"] == "running"
    assert row["provider"] == "fake-test"
    result = manager.execute(row["id"], "tester", "uname -a")
    assert result["ok"] is True and "uname -a" in result["stdout"]
    assert manager.list_files(row["id"], "tester", "/workspace")[0]["path"].endswith("a.txt")
    manager.stop(row["id"], "tester")
    assert manager.get(row["id"], "tester")["status"] == "stopped"
    manager.restart(row["id"], "tester")
    assert manager.get(row["id"], "tester")["status"] == "running"
    assert manager.delete(row["id"], "tester") is True


def test_tenant_isolation(manager):
    row = manager.create(user_id="owner", mode="persistent")
    with pytest.raises(KeyError):
        manager.get(row["id"], "other-user")
    manager.delete(row["id"], "owner")


def test_agent_tools_registered():
    for name in ("ComputerTool", "TerminalTool", "FilesystemTool", "BrowserTool", "ProcessTool", "DevelopmentTool"):
        assert name in TOOL_REGISTRY
