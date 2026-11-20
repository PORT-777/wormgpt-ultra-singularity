"""Tests for the CyberOps toolkit, agent tool, API and skill pack."""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

import security_ops
from security_ops import util


@pytest.fixture()
def safe_tmp():
    """Temporary directory that avoids pytest's broken default temp base."""
    path = Path(tempfile.mkdtemp(prefix="cyberops_test_"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


# --------------------------------------------------------------------------- #
#  Registry
# --------------------------------------------------------------------------- #
def test_action_registry_is_complete_and_unique():
    actions = security_ops.ACTIONS
    assert len(actions) >= 90
    assert len(set(actions)) == len(actions)
    for name, spec in actions.items():
        assert spec["description"], name
        assert callable(spec["handler"]), name
        assert spec["category"], name


def test_aliases_resolve():
    assert security_ops.run_action("hash", text="abc")["action"] == "hashes"
    assert security_ops.run_action("extract_iocs", text="8.8.8.8")["action"] == "iocs"
    with pytest.raises(ValueError):
        security_ops.run_action("definitely_not_an_action")


def test_capabilities_payload():
    caps = security_ops.capabilities()
    assert caps["name"] == "CyberOps"
    assert caps["action_count"] == len(security_ops.ACTIONS)
    assert set(caps["categories"]) >= {"triage", "binary", "detection",
                                       "logs", "network", "forensics",
                                       "encoding", "advisory", "report"}


# --------------------------------------------------------------------------- #
#  Triage + binary
# --------------------------------------------------------------------------- #
def test_ioc_extraction_and_export():
    text = ("c2 at https://evil.example.com/gate.php and 8.8.8.8 "
            "hash d41d8cd98f00b204e9800998ecf8427e")
    result = security_ops.run_action("iocs", text=text)
    assert "evil.example.com" in result["categories"]["domains"]
    assert "8.8.8.8" in result["categories"]["ipv4"]
    export = security_ops.run_action("ioc_export", text=text, fmt="stix")
    assert "bundle" in export["content"]
    assert export["format"] == "stix"


def test_file_action_with_allowed_host_path(safe_tmp):
    sample = safe_tmp / "note.txt"
    sample.write_text("hello evil.example.com", encoding="utf-8")
    result = security_ops.run_action("file_info", path=str(sample), allow_host=True)
    assert result["size"] == len(sample.read_bytes())
    assert result["hashes"]["sha256"]
    # without host access the same path must be rejected
    with pytest.raises(ValueError):
        security_ops.run_action("file_info", path=str(sample))


def test_entropy_and_strings():
    data = b"A" * 100 + b"secret-token-123"
    result = security_ops.run_action("strings", data=data)
    assert any("secret-token-123" in s for s in result["ascii"])
    ent = security_ops.run_action("entropy", data=b"\x00" * 512)
    assert ent["entropy"] == 0.0


def test_pe_parser_graceful_on_non_pe():
    with pytest.raises(ValueError):
        security_ops.run_action("pe", hex="4d5a" + "00" * 20)


# --------------------------------------------------------------------------- #
#  Detection engineering
# --------------------------------------------------------------------------- #
def test_mitre_mapping_and_kill_chain():
    mapped = security_ops.run_action(
        "mitre", text="powershell encoded command then lsass minidump and c2")
    ids = {t["id"] for t in mapped["techniques"]}
    assert "T1059.001" in ids or "T1059" in ids
    chain = security_ops.run_action(
        "kill_chain",
        techniques=["T1566.001", "T1059.001", "T1071.001"])
    assert chain["phase_count"] >= 2
    assert chain["furthest_phase"]


def test_yara_generate_and_scan_roundtrip():
    gen = security_ops.run_action(
        "yara_generate", text="evil.example.com unique-marker-xyz", name="unit_test")
    assert "rule unit_test" in gen["rule"]
    scan = security_ops.run_action(
        "yara_scan", rule_text=gen["rule"],
        text="this contains unique-marker-xyz for sure")
    assert scan["matches"], scan
    assert scan["matches"][0]["rule"] == "unit_test"


def test_sigma_generate_convert_validate():
    gen = security_ops.run_action(
        "sigma_generate",
        text="powershell.exe -EncodedCommand downloadstring http://evil.test")
    assert "title:" in gen["yaml"]
    converted = security_ops.run_action("sigma_convert", rule_text=gen["yaml"],
                                        target="all")
    assert set(converted["conversions"]) >= {"splunk", "kql", "eql", "aql", "yara-l"}
    valid = security_ops.run_action("sigma_validate", rule_text=gen["yaml"])
    assert "valid" in valid


# --------------------------------------------------------------------------- #
#  Logs / timeline
# --------------------------------------------------------------------------- #
def test_log_analysis_auth_failures():
    text = "\n".join(
        f"2024-01-01 10:0{i}:00 Failed password for root from 1.2.3.4 port 22 ssh2"
        for i in range(6))
    result = security_ops.run_action("logs", text=text)
    assert result["lines"] >= 6
    assert result["findings"] is not None


def test_timeline_and_beacon():
    timeline = security_ops.run_action(
        "timeline", items=[
            {"time": "2024-01-01T10:00:00Z", "event": "phish opened"},
            {"time": "2024-01-01T10:05:00Z", "event": "payload downloaded"},
        ])
    assert timeline["count"] == 2
    assert [e["event"] for e in timeline["events"]] == ["phish opened",
                                                        "payload downloaded"]
    beacon = security_ops.run_action(
        "beacon", times=["2024-01-01T10:00:00Z", "2024-01-01T10:05:00Z",
                         "2024-01-01T10:10:00Z", "2024-01-01T10:15:00Z"])
    assert "verdict" in beacon


# --------------------------------------------------------------------------- #
#  Forensics / encoding
# --------------------------------------------------------------------------- #
def test_secrets_and_iac():
    secrets = security_ops.run_action(
        "secrets", text="key = AKIAIOSFODNN7EXAMPLE\npassword = 'hunter2'")
    assert secrets["count"] >= 1
    iac = security_ops.run_action(
        "iac", text="apiVersion: v1\nkind: Pod\nspec:\n  containers:\n"
                     "  - securityContext:\n      privileged: true")
    assert any("privileged" in f["finding"] for f in iac["findings"])


def test_multi_layer_decode():
    first = util.b64encode(b"http://evil.example.com/payload")
    second = util.b64encode(first.encode())
    result = security_ops.run_action("decode", text=second)
    assert result["layer_count"] >= 1


def test_jwt_analysis_flags_none_algorithm():
    header = util.b64encode(b'{"alg":"none","typ":"JWT"}', urlsafe=True).rstrip("=")
    payload = util.b64encode(b'{"sub":"1","exp":9999999999}', urlsafe=True).rstrip("=")
    result = security_ops.run_action("jwt", token=f"{header}.{payload}.")
    assert result["algorithm"] == "none"
    assert any("alg=none" in f["finding"] for f in result["findings"])


# --------------------------------------------------------------------------- #
#  Advisory / reports
# --------------------------------------------------------------------------- #
def test_severity_and_patch_priority():
    sev = security_ops.run_action(
        "severity", cvss=9.8, exposure="public",
        data_sensitivity="regulated", exploited=True)
    assert sev["severity"] == "critical"
    assert sev["sla"]["respond_hours"] == 1
    patch = security_ops.run_action(
        "patch_priority",
        vulns=[{"title": "RCE", "cvss": 9.8, "exploited": True,
                "exposure": "public"},
               {"title": "info", "cvss": 3.0}])
    assert patch["priorities"][0]["title"] == "RCE"


def test_threat_model_and_posture():
    model = security_ops.run_action(
        "threat_model",
        description="public web application with database and admin portal")
    assert model["stride"]["rows"]
    posture = security_ops.run_action("posture", controls=["MFA", "EDR", "SIEM"])
    assert 0 <= posture["overall_percent"] <= 100
    assert posture["weakest_domains"]


def test_report_markdown_and_json():
    md = security_ops.run_action(
        "report", kind="technical", subject="unit test",
        findings=[{"severity": "high", "finding": "test finding",
                   "mitre": ["T1055"]}],
        iocs={"categories": {"domains": ["evil.example.com"]}})
    assert md["format"] == "markdown"
    assert "unit test" in md["content"]
    assert "evil.example.com" in md["content"]
    js = security_ops.run_action(
        "report", kind="executive", subject="unit test",
        findings=[], fmt="json")
    parsed = json.loads(js["content"])
    assert parsed["kind"] == "executive"


def test_incident_narrative_and_custody():
    narrative = security_ops.run_action(
        "incident_narrative",
        timeline=[{"time": "2024-01-01T10:00:00Z", "event": "phish opened"}],
        subject="test incident")
    assert "test incident" in narrative["narrative"]
    custody = security_ops.run_action(
        "custody", evidence=[{"item": "disk.img", "type": "image", "data": b"abc"}])
    assert custody["item_count"] == 1
    assert custody["items"][0]["sha256"]


# --------------------------------------------------------------------------- #
#  Agent tool + HTTP API
# --------------------------------------------------------------------------- #
def test_agent_tool_is_discovered_and_runs():
    import asyncio
    from tools import TOOL_REGISTRY, execute_tool
    assert "CyberOps" in TOOL_REGISTRY
    out = asyncio.run(execute_tool("CyberOps", {"action": "iocs",
                                                "text": "8.8.8.8"}))
    assert "8.8.8.8" in out
    listing = asyncio.run(execute_tool("CyberOps", {"action": "list"}))
    assert "action_count" in listing


def test_http_api_capabilities_run_and_sandbox(safe_tmp):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import security_api

    app = FastAPI()
    app.include_router(security_api.router)
    client = TestClient(app)

    caps = client.get("/api/security/capabilities")
    assert caps.status_code == 200
    assert caps.json()["action_count"] == len(security_ops.ACTIONS)

    ran = client.post("/api/security/run",
                      json={"action": "iocs", "text": "evil.example.com"})
    assert ran.status_code == 200
    assert ran.json()["sandboxed"] is True

    outside = safe_tmp / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    blocked = client.post("/api/security/run",
                          json={"action": "file_info", "path": str(outside)})
    assert blocked.status_code == 400
    assert "sandbox" in blocked.text.lower()

    unknown = client.post("/api/security/run", json={"action": "nope"})
    assert unknown.status_code == 400


def test_skill_pack_is_loaded():
    import skills
    packs = skills.load_packs()
    names = {p["name"] for p in packs}
    assert "cyber-ops-edition" in names
    matched = skills.relevant_packs("analyse this malware sample and extract IOCs")
    assert any(p["name"] == "cyber-ops-edition" for p in matched)
