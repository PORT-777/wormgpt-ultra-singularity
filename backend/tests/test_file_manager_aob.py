"""Tests for UniversalFileManager AOB pattern scan action."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import configs as config
from tools.file_manager import UniversalFileManager


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def mgr(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    return UniversalFileManager()


def test_aob_finds_pattern_with_wildcards(mgr, tmp_path):
    # bytes: 48 8B 05 ?? ?? ?? ??  (mov rax, [rip+imm32] shape)
    blob = bytes(range(256)) + bytes([0x48, 0x8B, 0x05, 0x11, 0x22,
                                      0x33, 0x44]) + bytes(range(256))
    (tmp_path / "driver.sys").write_bytes(blob)
    out = _run(mgr.run(action="aob", path="driver.sys",
                       pattern="48 8B 05 ?? ?? ?? ??"))
    assert "hit(s)" in out
    # the pattern appears exactly once in this blob
    assert out.count("0x") == 1


def test_aob_multiple_hits(mgr, tmp_path):
    sig = bytes([0xDE, 0xAD, 0xBE, 0xEF])
    blob = sig + b"\x00" * 16 + sig + b"\x00" * 16 + sig
    (tmp_path / "scan.bin").write_bytes(blob)
    out = _run(mgr.run(action="aob", path="scan.bin",
                       pattern="DE AD BE EF"))
    assert out.count("0x") == 3


def test_aob_not_found(mgr, tmp_path):
    (tmp_path / "clean.bin").write_bytes(b"\x00" * 256)
    out = _run(mgr.run(action="aob", path="clean.bin", pattern="FF FF"))
    assert "not found" in out


def test_aob_wildcard_only(mgr, tmp_path):
    blob = b"\xAA\xBB\xCC\xDD\xEE\xFF"
    (tmp_path / "wild.bin").write_bytes(blob)
    out = _run(mgr.run(action="aob", path="wild.bin",
                       pattern="?? BB ?? DD ?? FF"))
    assert "0x00000000" in out
