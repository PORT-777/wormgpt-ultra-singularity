# backend/tools/reverse_analyzer.py
# Language: Python 3 | Runtime: CPython | Target: Windows 11
# ASM/Binary Logic Analyzer for 🔥😈 PORT 777 EVIL ☠️🔥👹 - Singularity Edition

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class FunctionHint:
    name: str
    start: int
    end: int
    prolog: bool = False
    epilog: bool = False
    obfuscated: bool = False


class ReverseAnalyzer:
    """Translates machine language into human logic. Detects function
    prologs/epilogs, CFG hints, and obfuscated patterns."""

    PROLOG_PATTERNS = [
        rb"\x48\x89\x5C\x24\x08",  # mov [rsp+8], rbx
        rb"\x48\x89\x6C\x24\x10",  # mov [rsp+0x10], rbp
        rb"\x48\x83\xEC\x20",      # sub rsp, 0x20
        rb"\x55",                   # push rbp
        rb"\x48\x8B\xEC",          # mov rbp, rsp
    ]

    EPILOG_PATTERNS = [
        rb"\x48\x83\xC4\x20",      # add rsp, 0x20
        rb"\x5D",                   # pop rbp
        rb"\xC3",                   # ret
        rb"\xCB",                   # retf
    ]

    def __init__(self) -> None:
        self.functions: List[FunctionHint] = []

    def scan_prologues(self, data: bytes, base: int = 0) -> List[FunctionHint]:
        found: List[FunctionHint] = []
        for pat in self.PROLOG_PATTERNS:
            for m in re.finditer(re.escape(pat), data):
                found.append(FunctionHint(
                    name=f"sub_{base + m.start():X}",
                    start=base + m.start(),
                    end=base + m.start() + len(pat),
                    prolog=True,
                ))
        self.functions.extend(found)
        return found

    def scan_epilogues(self, data: bytes, base: int = 0) -> List[FunctionHint]:
        found: List[FunctionHint] = []
        for pat in self.EPILOG_PATTERNS:
            for m in re.finditer(re.escape(pat), data):
                found.append(FunctionHint(
                    name=f"ret_{base + m.start():X}",
                    start=base + m.start(),
                    end=base + m.start() + len(pat),
                    epilog=True,
                ))
        return found

    def detect_obfuscation(self, data: bytes) -> Dict[str, bool]:
        """Heuristic obfuscation detection."""
        return {
            "nop_sled": b"\x90" * 16 in data,
            "frequent_prefix_0f": data.count(b"\x0F") > len(data) // 50,
            "stack_strings": False,
        }

    def asm_to_pseudocode(self, asm_line: str) -> str:
        """Small ASM -> C++ pseudo mapper for common patterns."""
        mapping = {
            "mov": "=",
            "add": "+=",
            "sub": "-=",
            "xor": "^=",
            "ret": "return;",
        }
        stripped = asm_line.strip()
        for op, cpp in mapping.items():
            if stripped.lower().startswith(op):
                return stripped.replace(op, cpp, 1)
        return f"// {asm_line}"
