# backend/tools/file_master.py
# Language: Python 3 | Runtime: CPython | Target: Windows 11
# Universal File IO (All formats) with AOB pattern searching

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class AOBHit:
    offset: int
    pattern: str
    data: bytes


class FileMaster:
    """Deep parsing of binary files (.bin, .dat, .dll, .exe, .zip, .rar).
    Supports Array-Of-Bytes (AOB) pattern searching with '??' wildcards."""

    def read_bytes(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def write_bytes(self, path: str, data: bytes) -> int:
        with open(path, "wb") as f:
            return f.write(data)

    def patch(self, path: str, offset: int, data: bytes) -> None:
        buf = bytearray(self.read_bytes(path))
        buf[offset : offset + len(data)] = data
        self.write_bytes(path, bytes(buf))

    def aob_scan(self, path: str, pattern_hex: str) -> List[AOBHit]:
        """Search for a byte pattern. Wildcards: '??' matches any byte."""
        data = self.read_bytes(path)
        pattern_bytes: List[int | None] = []
        for token in pattern_hex.split():
            if token == "??":
                pattern_bytes.append(None)
            else:
                pattern_bytes.append(int(token, 16))

        pat_len = len(pattern_bytes)
        hits: List[AOBHit] = []
        for i in range(len(data) - pat_len + 1):
            match = True
            for j, pb in enumerate(pattern_bytes):
                if pb is not None and data[i + j] != pb:
                    match = False
                    break
            if match:
                hits.append(
                    AOBHit(offset=i, pattern=pattern_hex, data=data[i : i + pat_len])
                )
        return hits

    def aob_patch(self, path: str, pattern_hex: str,
                  replacement_hex: str, occurrence: int = 0) -> int:
        hits = self.aob_scan(path, pattern_hex)
        if not hits:
            raise ValueError("Pattern not found")
        if occurrence >= len(hits):
            raise ValueError(
                f"Occurrence {occurrence} out of range ({len(hits)} hits)"
            )
        hit = hits[occurrence]
        repl = bytes(int(b, 16) for b in replacement_hex.split())
        self.patch(path, hit.offset, repl)
        return hit.offset
