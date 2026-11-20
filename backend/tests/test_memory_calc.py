"""Unit tests for MemoryLogicCalculator — pure math, no LLM involved."""
from __future__ import annotations

import asyncio

import pytest

from tools.memory_calc import MemoryLogicCalculator


@pytest.fixture()
def calc():
    return MemoryLogicCalculator()


def test_chain_walk(calc):
    out = asyncio.run(calc.run(
        op="chain", base="0x7FF6A1B2C000",
        offsets=["0x10", "0x28", "0x1C"]))
    # 0x7FF6A1B2C000 + 0x10 + 0x28 + 0x1C == 0x7FF6A1B2C054
    assert "FINAL: 0x7FF6A1B2C054" in out
    assert "hop 2:" in out


def test_delta_negative(calc):
    out = asyncio.run(calc.run(op="delta", a="0x100", b="0x40"))
    assert "(delta)" in out and "-0xC0" in out


def test_hex2dec_dec2hex_roundtrip(calc):
    h = asyncio.run(calc.run(op="dec2hex", value="4113"))
    assert "0x1011" in h
    d = asyncio.run(calc.run(op="hex2dec", value="0x1011"))
    assert "= 4113" in d


def test_struct_offset_alignment(calc):
    out = asyncio.run(calc.run(
        op="struct_offset",
        fields={"id": "u32", "name_len": "u8", "flags": "u32",
                "next": "u64"}))
    # id @0 (4B), name_len @4 (1B) -> pad 3 -> flags @8 (4B), next@16
    assert "@ offset 0x4" in out and "@ offset 0x8" in out \
        and "@ offset 0x10" in out
    assert "TOTAL struct size: 0x18" in out


def test_add_multi_offset(calc):
    out = asyncio.run(calc.run(op="add", base="0x1000",
                               offsets=[0x10, 0x20]))
    assert "= 0x1030" in out


def test_unknown_op_returns_error(calc):
    out = asyncio.run(calc.run(op="hack_offsets"))
    assert out.startswith("ERROR")
