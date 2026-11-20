"""Real acceptance checks for the Code & Binary Intelligence Engine."""
from __future__ import annotations

import asyncio
import hashlib
import sys
import zipfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from intelligence import binary_intel, project_intel, task_workspace, toolchain  # noqa: E402
from tools.intelligence_tool import CodeIntelligence  # noqa: E402


@pytest.fixture()
def sample_project(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "import os\n\ndef add(a, b):\n    return a + b\n\n"
        "def unused(x):\n    # TODO: remove\n    return x\n",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        '{"name":"sample","scripts":{"start":"node app.js"},"dependencies":{"react":"18"}}',
        encoding="utf-8",
    )
    return tmp_path


def test_toolchain_discovery():
    report = toolchain.discover()
    assert report["tools"]
    assert "python" in report["available"]
    assert "git" in report["available"]
    assert all(set(t) >= {"name", "available", "version", "path", "operations", "health"} for t in report["tools"])


def test_project_scan_and_symbols(sample_project):
    data = project_intel.scan_project(str(sample_project))
    assert data["file_count"] >= 2
    assert data["languages"].get("Python") == 1
    assert any(s["name"] == "add" for s in data["symbols"])
    assert any("react" in f for f in data["frameworks"])
    assert "app.py" in " ".join(data["entry_points"])
    assert any(x["marker"] == "TODO" for x in data["incomplete"])
    matches = project_intel.find_symbol(str(sample_project), "add")
    assert any(m["name"] == "add" for m in matches)
    quality = project_intel.code_quality(str(sample_project))
    assert isinstance(quality["duplicate_files"] if "duplicate_files" in quality else quality["duplicates"], list)


def test_task_workspace_preserves_original(tmp_path: Path):
    original = tmp_path / "artifact.bin"
    original.write_bytes(b"PORT777\x00\x01\x02")
    meta = task_workspace.create_task("acceptance", str(original))
    stored = Path(meta["paths"]["input"]) / "artifact.bin"
    assert stored.is_file()
    assert meta["original_hash"] == hashlib.sha256(stored.read_bytes()).hexdigest()
    assert original.read_bytes() == b"PORT777\x00\x01\x02"
    report = task_workspace.save_report(meta["id"], "probe", {"ok": True})
    assert Path(report).is_file()
    exported = task_workspace.export_task(meta["id"])
    assert zipfile.is_zipfile(exported)


def test_binary_identification_and_report():
    exe = Path(sys.executable)
    info = binary_intel.identify(exe)
    assert info["format"] == "pe"
    assert len(info["sha256"]) == 64
    assert info["size"] > 0
    report = binary_intel.analyze(exe, include_strings=False, include_disasm=False)
    assert report["analysis"].get("sections")
    assert report["identification"]["format"] == "pe"
    assert report["limitations"]


def test_agent_tool_adapter(sample_project):
    result = asyncio.run(CodeIntelligence().run(action="scan_project", path=str(sample_project)))
    assert '"file_count"' in result
    result2 = asyncio.run(CodeIntelligence().run(action="toolchain"))
    assert '"available"' in result2
