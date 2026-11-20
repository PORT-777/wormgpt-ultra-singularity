"""Every skill pack in skills_packs/ must parse and carry required keys."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import configs as config


def test_all_real_packs_parse_clean():
    pytest.importorskip("yaml")
    import skills
    packs = skills.load_packs()
    assert len(packs) >= 10, f"expected >=10 packs, got {len(packs)}"
    names = [p["name"] for p in packs]
    assert len(names) == len(set(names)), "duplicate pack names!"
    for p in packs:
        assert p["instructions"], f"{p['name']}: empty instructions"
        assert isinstance(p["trigger_when"], list)
        assert isinstance(p["always"], bool)


def test_no_pack_introduces_refusal_language():
    """User contract: skills add method, never 'refuse the task' gates."""
    pytest.importorskip("yaml")
    import skills
    for p in skills.load_packs():
        text = p["instructions"].lower()
        assert "رفض المهمة" not in text or p["name"] == "ambiguity-forward"
