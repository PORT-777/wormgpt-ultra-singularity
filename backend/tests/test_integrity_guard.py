"""Tests for IntegrityGuard (checksum / baseline / tamper detect)."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import configs as config
from tools.integrity_guard import IntegrityGuard


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def guard(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    return IntegrityGuard()


def test_checksum_is_deterministic(guard, tmp_path):
    f = tmp_path / "build.bin"
    f.write_bytes(b"\x90" * 128)
    out1 = _run(guard.run(action="checksum", path="build.bin"))
    out2 = _run(guard.run(action="checksum", path="build.bin"))
    assert "sha256:" in out1 and "crc32:" in out1
    assert out1 == out2                      # same bytes -> same report


def test_baseline_clean_verify(guard, tmp_path):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "game.bin").write_bytes(b"\xAA" * 32)
    out = _run(guard.run(action="create_baseline", path="build",
                         manifest="t1.json"))
    assert "baseline created for 1 files" in out
    out = _run(guard.run(action="verify_baseline", path="build",
                         manifest="t1.json"))
    assert "CLEAN" in out and "1 files unchanged" in out


def test_baseline_catches_tamper_with_offset(guard, tmp_path):
    build = tmp_path / "build"
    build.mkdir()
    data = bytearray(b"\x00" * 1024 * 10)
    (build / "game.bin").write_bytes(bytes(data))

    _run(guard.run(action="create_baseline", path="build",
                   manifest="t2.json"))

    data[4096] = 0xFF                       # flip the first block-2 byte
    (build / "game.bin").write_bytes(bytes(data))

    out = _run(guard.run(action="verify_baseline", path="build",
                         manifest="t2.json"))
    assert "TAMPERED" in out
    assert "CHANGED: game.bin" in out
    assert "@ 0x1000" in out                # first divergent block reported


def test_verify_requires_baseline(guard, tmp_path):
    (tmp_path / "still").mkdir()
    out = _run(guard.run(action="verify_baseline", path="still",
                         manifest="nope.json"))
    assert out.startswith("ERROR") and "create_baseline" in out
