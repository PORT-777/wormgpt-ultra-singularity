"""Tests for the ReportBuilder tool (strix-style findings compiler)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from tools.report_builder import ReportBuilder


@pytest.mark.asyncio
async def test_report_writes_md_and_json(tmp_path, monkeypatch):
    import configs as config
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    rb = ReportBuilder()
    out = await rb.run(
        title="unit scan",
        findings=[
            {"title": "f1", "severity": "critical", "evidence": "e1",
             "remediation": "r1"},
            {"title": "f2", "severity": "info"},
        ])
    assert "2 findings" in out
    reports = list((tmp_path / "reports").glob("*.md"))
    assert reports, out
    md = reports[0].read_text(encoding="utf-8")
    assert "# unit scan" in md and "| CRITICAL | f1" in md
    j = list((tmp_path / "reports").glob("*.json"))[0]
    assert "f2" in j.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_report_severity_sorted_and_capped(tmp_path, monkeypatch):
    import configs as config
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    rb = ReportBuilder()
    findings = [{"title": f"f{i}", "severity": "medium"} for i in range(80)]
    out = await rb.run(title="cap test", findings=findings)
    assert "60 findings" in out    # capped at 60 rows
