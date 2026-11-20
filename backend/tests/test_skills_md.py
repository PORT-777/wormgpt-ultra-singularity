"""Tests for md-style SKILL.md packs (superpowers import) + relevance."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import configs as config


@pytest.fixture()
def md_packs_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SKILLS_DIR", tmp_path)
    (tmp_path / "always_pack.md").write_text(
        "---\n"
        "name: always_pack\n"
        "description: runs always\n"
        "always: true\n"
        "---\n"
        "Always-on body text.\n", encoding="utf-8")
    (tmp_path / "auto_pack.md").write_text(
        "---\n"
        "name: auto_pack\n"
        "description: keyword gated\n"
        "trigger_when: [\"pentest\", \"scan\"]\n"
        "---\n"
        "Auto body text.\n", encoding="utf-8")
    return tmp_path


def test_md_frontmatter_pack_loads(md_packs_dir):
    import skills
    packs = skills.load_packs()
    names = [p["name"] for p in packs]
    assert "always_pack" in names and "auto_pack" in names


def test_relevance_matches_only_triggered(md_packs_dir):
    import skills
    matched = [p["name"] for p in
               skills.relevant_packs("please scan this binary for tamper")]
    assert "auto_pack" in matched and "always_pack" in matched
    unmatched = [p["name"] for p in
                 skills.relevant_packs("write me a poem")]
    assert "auto_pack" not in unmatched
    assert "always_pack" in unmatched


def test_skills_block_no_task_injects_always_only(md_packs_dir):
    import skills
    # No task => only always-on packs are injected (keyword packs stay out).
    block = skills.skills_block()
    assert "always_pack" in block
    assert "auto_pack" not in block


def test_skills_block_task_matches_keyword(md_packs_dir):
    import skills
    block = skills.skills_block("please scan this target")
    assert "always_pack" in block and "auto_pack" in block


def test_skills_block_task_filters(md_packs_dir):
    import skills
    block = skills.skills_block("write a haiku about mountains")
    assert "always_pack" in block and "auto_pack" not in block
