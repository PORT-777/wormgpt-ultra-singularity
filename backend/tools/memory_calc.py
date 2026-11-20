"""
Tool :: MemoryLogicCalculator

Pure DEBUGGING MATH — a neutral calculator for pointer/offset arithmetic
used with a debugger (x64dbg/WinDbg/Vs debugger) on software you own.
It does NOT touch any process: no handle opening, no ReadProcessMemory,
nothing. It is arithmetic over hex strings the user supplies.

Operations
----------
  add / sub       : base ± offset
  delta           : difference of two addresses (b - a)
  chain           : walk [base, off1, off2, ...] additively and report
                    every hop (classic pointer-chain arithmetic)
  hex2dec / dec2hex : base conversion
  struct_offset   : {fields: {"name": "u32"/"u64"/"f32"/...}} cumulative
                    field offsets with alignment, C-layout style
"""
from __future__ import annotations

from typing import Any, Dict, List

from .base import Tool

_TYPE_SIZES = {"u8": 1, "i8": 1, "u16": 2, "i16": 2,
               "u32": 4, "i32": 4, "f32": 4,
               "u64": 8, "i64": 8, "f64": 8, "ptr": 8}


def _hx(v: int) -> str:
    return f"0x{v:X}"


def _parse(value: Any) -> int:
    s = str(value).strip().replace(" ", "")
    for prefix in ("0x", "0X", "x"):
        if s.lower().startswith(prefix.lower()):
            return int(s, 16)
    return int(s, 16) if any(c in "abcdefABCDEF" and not s.lstrip("-").isdigit()
                             for c in s) else int(s, 0)


class MemoryLogicCalculator(Tool):
    name = "MemoryLogicCalculator"
    description = (
        "Debugging MATH ONLY (touching no process): pointer/offset "
        "arithmetic for your own software. {'op': 'add'|'sub'|'delta'|"
        "'chain'|'hex2dec'|'dec2hex'|'struct_offset', 'base': '7FF...', "
        "'offsets': [..], 'a': .., 'b': .., 'fields': {..}} "
        "Every result is plain arithmetic you can verify by hand."
    )
    example = {"op": "chain", "base": "7FF6A1B2C000",
               "offsets": ["0x10", "0x28", "0x1C"]}

    async def run(self, **kw: Any) -> str:
        try:
            op = str(kw.get("op", "")).lower().strip()
            if op == "add" or op == "sub":
                base = _parse(kw.get("base", 0))
                raw = kw.get("offsets", kw.get("offset", 0))
                offs = raw if isinstance(raw, list) else [raw]
                total = sum(_parse(o) for o in offs)
                res = base + total if op == "add" else base - total
                sign = "+" if op == "add" else "-"
                return f"{_hx(base)} {sign} {_hx(total)} = {_hx(res)}"

            if op == "delta":
                b = _parse(kw.get("b", 0))
                a = _parse(kw.get("a", 0))
                d = b - a
                sign = "+" if d >= 0 else "-"
                return f"{_hx(b)} - {_hx(a)} = {sign}{_hx(abs(d))} (delta)"

            if op == "chain":
                base = _parse(kw.get("base", 0))
                offs = kw.get("offsets", []) or []
                hops: List[str] = [f"start: {_hx(base)}"]
                cur = base
                for i, o in enumerate(offs, 1):
                    delta = _parse(o)
                    cur += delta
                    hops.append(f"hop {i}: + {_hx(delta)} -> {_hx(cur)}")
                hops.append(f"FINAL: {_hx(cur)}")
                return "\n".join(hops)

            if op == "hex2dec":
                v = _parse(kw.get("value", 0))
                return f"{_hx(v)} = {v} (dec)"

            if op == "dec2hex":
                v = int(str(kw.get("value", "0")).strip(), 10)
                return f"{v} (dec) = {_hx(v)}"

            if op == "struct_offset":
                fields: Dict[str, str] = kw.get("fields", {}) or {}
                if not fields:
                    return "ERROR: fields dict required"
                cursor = 0
                max_align = 1
                lines = []
                for name, tname in fields.items():
                    t = str(tname).lower().strip()
                    size, align = _layout(t)
                    max_align = max(max_align, align)
                    pad = (-cursor) % align
                    if pad:
                        lines.append(f"  <padding {pad}B>")
                        cursor += pad
                    lines.append(f"  {name} ({tname}, {size}B) "
                                 f"@ offset {_hx(cursor)}")
                    cursor += size
                total_pad = (-cursor) % max_align
                if total_pad:
                    lines.append(f"  <tail padding {total_pad}B>")
                    cursor += total_pad
                return ("C-layout offsets (alignment respected):\n"
                        + "\n".join(lines)
                        + f"\nTOTAL struct size: {_hx(cursor)} ({cursor}B, "
                          f"align {max_align}B)")

            return ("ERROR: unknown op (add|sub|delta|chain|hex2dec|"
                    "dec2hex|struct_offset)")
        except Exception as exc:
            return f"ERROR: calculation failed: {exc}"


def _layout(tname: str) -> "tuple[int, int]":
    base = tname.lstrip("[").rstrip("]").split("[")[0]
    size = _TYPE_SIZES.get(base, 4)
    arr = tname.split("[")
    if len(arr) > 1 and arr[1].rstrip("]").isdigit():
        size *= int(arr[1].rstrip("]"))
    return size, size
