"""Tests for the YAML skill-pack loader (additive self-extension)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import configs as config


def test_starter_pack_loads():
    import skills
    packs = skills.load_packs()
    names = {p["name"] for p in packs}
    assert "offset_forensics_playbook" in names


def test_skills_block_contains_pack_instructions():
    import skills
    try:
        import yaml  # noqa: F401
    except ImportError:
        pytest.skip("pyyaml not installed")
    block = skills.skills_block("derive struct layout and offsets for a binary")
    assert "offset_forensics_playbook" in block
    assert "EVIDENCE FIRST" in block          # instructions made it in


def test_broken_pack_is_skipped_not_fatal(tmp_path, monkeypatch):
    import skills
    monkeypatch.setattr(config, "SKILLS_DIR", tmp_path)
    (tmp_path / "good.yaml").write_text(
        "name: tiny_pack\ndescription: x\ninstructions: |\n  be tiny\n",
        encoding="utf-8")
    (tmp_path / "broken.yaml").write_text(":::not yaml: [[{", encoding="utf-8")
    (tmp_path / "empty_instructions.yaml").write_text(
        "name: emptyone\ndescription: no instructions\n", encoding="utf-8")
    packs = skills.load_packs()
    assert [p["name"] for p in packs] == ["tiny_pack"]


def test_disabled_flag_returns_empty(monkeypatch):
    import skills
    monkeypatch.setattr(config, "SKILLS_ENABLED", False)
    assert skills.skills_block() == ""
