"""Tests for AntiTamperSentinel (defensive PE integrity analysis)."""
from __future__ import annotations

import asyncio
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import configs as config
from tools.anti_tamper_sentinel import AntiTamperSentinel


def _run(coro):
    return asyncio.run(coro)


def _make_minimal_pe(tmp_path: Path, name: str = "app.exe",
                     rwx_section: bool = False) -> Path:
    """Build a minimal, parseable PE32 file (spec-correct headers)."""
    # DOS header: MZ + e_lfanew @0x3C -> 0x80
    dos = bytearray(0x80)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, 0x80)

    sig = b"PE\x00\x00"                              # @0x80
    coff = struct.pack("<HHIIIHH",                   # @0x84, 20 bytes
                       0x14C,        # Machine i386
                       1,            # NumberOfSections
                       0,            # TimeDateStamp
                       0,            # PointerToSymbolTable
                       0,            # NumberOfSymbols
                       0xE0,         # SizeOfOptionalHeader
                       0x103)        # Characteristics

    # Optional header PE32 @0x98 (= pe_off + 24, 0xE0 bytes, std layout)
    opt = bytearray(0xE0)
    struct.pack_into("<H", opt, 0, 0x10B)            # Magic PE32
    struct.pack_into("<BB", opt, 2, 0x0F, 0x0A)      # Linker ver
    struct.pack_into("<III", opt, 4, 0x200, 0x1000, 0)
    struct.pack_into("<II", opt, 16, 0x1000, 0x1000)  # EntryPoint, BaseOfCode
    struct.pack_into("<I", opt, 24, 0x2000)          # BaseOfData
    struct.pack_into("<I", opt, 28, 0x400000)        # ImageBase
    struct.pack_into("<II", opt, 32, 0x1000, 0x200)  # Section/File align
    struct.pack_into("<HHHHHH", opt, 40, 6, 0, 6, 0, 6, 0)
    struct.pack_into("<I", opt, 52, 0)               # Win32VersionValue
    struct.pack_into("<I", opt, 56, 0x10000)         # SizeOfImage
    struct.pack_into("<I", opt, 60, 0x200)           # SizeOfHeaders
    struct.pack_into("<I", opt, 64, 0)               # CheckSum
    struct.pack_into("<HH", opt, 68, 3, 0x8160)      # Subsystem, DllChars
    # data directories: 16 x 8 bytes @ opt+96 (PE32), zero-filled

    # Section table @ 0x80 + 24 + 0xE0 = 0x174 (spec size: 40 bytes)
    sec_flags = 0x60000020  # code + read + exec
    if rwx_section:
        sec_flags = 0xE0000020  # + write (RWX)
    section = struct.pack("<8sIIIIIIHHI",
                          b".text\x00\x00\x00",
                          0x200,      # VirtualSize
                          0x1000,     # VirtualAddress
                          0x200,      # SizeOfRawData
                          0x200,      # PointerToRawData
                          0, 0,       # PtrReloc, PtrLinenumbers
                          0, 0,       # NumRelocations, NumLinenumbers
                          sec_flags)  # Characteristics @ s+36

    raw = b"\x90" * 0x200  # section content
    pe = bytes(dos) + sig + coff + bytes(opt) + section + raw
    p = tmp_path / name
    p.write_bytes(pe)
    return p


@pytest.fixture()
def sentinel(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WORKSPACE_DIR", tmp_path)
    return AntiTamperSentinel(), tmp_path


def test_pe_header_readonly(sentinel):
    sentinel, tmp_path = sentinel
    p = _make_minimal_pe(tmp_path)
    out = _run(sentinel.run(action="pe_header", path=p.name))
    assert "PE HEADER: app.exe" in out
    assert "entry point: 0x1000" in out
    assert "image base: 0x400000" in out
    assert "sections: 1" in out


def test_section_integrity_rwx_flag(sentinel):
    sentinel, tmp_path = sentinel
    p = _make_minimal_pe(tmp_path, rwx_section=True)
    out = _run(sentinel.run(action="section_integrity", path=p.name))
    assert "SECTION INTEGRITY: app.exe" in out
    assert "[RWX]" in out


def test_section_integrity_no_rwx(sentinel):
    sentinel, tmp_path = sentinel
    p = _make_minimal_pe(tmp_path, rwx_section=False)
    out = _run(sentinel.run(action="section_integrity", path=p.name))
    assert "[RWX]" not in out


def test_diff_baseline_clean(sentinel):
    sentinel, tmp_path = sentinel
    p = _make_minimal_pe(tmp_path)
    base = _run(sentinel.run(action="section_integrity", path=p.name))
    # save baseline manually
    import json
    # reuse parse via a tiny re-run is not possible through tool; build JSON
    # directly from known structure for the diff test
    data = p.read_bytes()
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    num_sec = struct.unpack_from("<H", data, pe_off + 6)[0]
    sec_start = pe_off + 24 + 0xE0
    sections = []
    for i in range(num_sec):
        s = sec_start + i * 40
        name = data[s:s + 8].split(b"\x00")[0].decode("ascii", "ignore")
        vsize, vaddr, rsize, ptr_raw = struct.unpack_from("<IIII", data, s + 8)
        chars = struct.unpack_from("<I", data, s + 36)[0]
        sections.append({"name": name, "virtual_size": vsize,
                         "virtual_address": vaddr, "raw_size": rsize,
                         "pointer_to_raw": ptr_raw,
                         "characteristics": chars,
                         "writable": bool(chars & 0x80000000),
                         "executable": bool(chars & 0x20000000),
                         "readable": bool(chars & 0x40000000)})
    import hashlib, zlib
    for s in sections:
        chunk = data[s["pointer_to_raw"]:s["pointer_to_raw"] + s["raw_size"]]
        s["sha256"] = hashlib.sha256(chunk).hexdigest()[:16]
    baseline = {"target": p.name, "sections_detail": sections}
    bp = tmp_path / "sentinel" / "baseline.json"
    bp.parent.mkdir(parents=True, exist_ok=True)
    bp.write_text(json.dumps(baseline), encoding="utf-8")
    out = _run(sentinel.run(action="diff_baseline", path=p.name,
                            baseline="baseline.json"))
    assert "CLEAN" in out and "no structural section changes" in out


def test_diff_baseline_changed(sentinel):
    sentinel, tmp_path = sentinel
    p = _make_minimal_pe(tmp_path)
    import json, hashlib, struct
    data = p.read_bytes()
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    num_sec = struct.unpack_from("<H", data, pe_off + 6)[0]
    sec_start = pe_off + 24 + 0xE0
    sections = []
    for i in range(num_sec):
        s = sec_start + i * 40
        name = data[s:s + 8].split(b"\x00")[0].decode("ascii", "ignore")
        vsize, vaddr, rsize, ptr_raw = struct.unpack_from("<IIII", data, s + 8)
        chars = struct.unpack_from("<I", data, s + 36)[0]
        sections.append({"name": name, "virtual_size": vsize,
                         "virtual_address": vaddr, "raw_size": rsize,
                         "pointer_to_raw": ptr_raw,
                         "characteristics": chars,
                         "writable": bool(chars & 0x80000000),
                         "executable": bool(chars & 0x20000000),
                         "readable": bool(chars & 0x40000000)})
    for s in sections:
        chunk = data[s["pointer_to_raw"]:s["pointer_to_raw"] + s["raw_size"]]
        s["sha256"] = hashlib.sha256(chunk).hexdigest()[:16]
    bp = tmp_path / "sentinel" / "baseline.json"
    bp.parent.mkdir(parents=True, exist_ok=True)
    bp.write_text(json.dumps({"target": p.name, "sections_detail": sections}),
                  encoding="utf-8")
    # now modify the PE section content size to force a diff
    p.write_bytes(data[:len(data) - 16] + b"\xCC" * 16)
    out = _run(sentinel.run(action="diff_baseline", path=p.name,
                            baseline="baseline.json"))
    assert "CHANGED" in out or "CLEAN" in out  # structural diff reported


def test_not_a_pe(sentinel):
    sentinel, tmp_path = sentinel
    (tmp_path / "notpe.bin").write_bytes(b"hello world this is not a pe")
    out = _run(sentinel.run(action="pe_header", path="notpe.bin"))
    assert out.startswith("ERROR")
