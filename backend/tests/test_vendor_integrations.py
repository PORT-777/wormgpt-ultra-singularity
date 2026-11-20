"""Tests for the vendor hub: catalog, skills, plugins, MCP and tools."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import mcp_server
import vendor_hub
from tools import TOOL_REGISTRY
from plugins_system.registry import registry_instance


@pytest.fixture()
def fresh_index(monkeypatch, tmp_path):
    monkeypatch.setattr(vendor_hub, "INDEX_PATH", tmp_path / "index.json")
    monkeypatch.setattr(vendor_hub, "_CACHE", None)
    return vendor_hub.get_index()


def test_all_repos_registered():
    ids = {r["id"] for r in vendor_hub.list_repos()}
    expected = {
        "autogpt", "claude-skills", "openhands", "ecc", "hermes-agent",
        "lunar-source", "deepseek-harness", "career-ops", "ohmyzsh",
        "ruflo", "agentic-skills",
    }
    assert expected <= ids
    for repo in vendor_hub.list_repos():
        assert repo["checked_out"] is True


def test_index_and_skill_search(fresh_index):
    assert len(fresh_index["entries"]) > 0
    hits = vendor_hub.search("agent skills", limit=5)
    assert hits and all("id" in h and "path" in h for h in hits)
    skill = vendor_hub.read_skill(hits[0]["id"])
    assert skill["content"] and skill["repo"] in {r["id"] for r in vendor_hub.REPOS}


def test_path_confinement():
    with pytest.raises(vendor_hub.VendorError):
        vendor_hub.read_file("autogpt", "../../../.env")
    with pytest.raises(vendor_hub.VendorError):
        vendor_hub.repo_info("does-not-exist")


def test_vendor_tool_registered():
    assert "VendorTool" in TOOL_REGISTRY


def test_vendor_plugins_registered():
    import asyncio

    asyncio.run(registry_instance.discover_plugins())
    manifests = registry_instance.get_all_manifests()
    vendor = [m for m in manifests if m["id"].startswith("vendor_")]
    assert len(vendor) == len(vendor_hub.REPOS)
    assert all(m["auth_type"] == "none" for m in vendor)
    assert all(m["tools"] for m in vendor)


def test_mcp_exposes_vendor_tools():
    names = {t["name"] for t in mcp_server.TOOLS}
    assert {
        "vendor_repos_list", "vendor_skills_search", "vendor_skill_read",
        "vendor_file_list", "vendor_file_read", "vendor_repo_search",
        "vendor_plugins",
    } <= names


def test_always_on_skill_pack():
    pack = BACKEND / "skills_packs" / "vendor-hub.md"
    assert pack.is_file()
    text = pack.read_text(encoding="utf-8")
    assert "always: true" in text
    assert "VendorTool" in text
