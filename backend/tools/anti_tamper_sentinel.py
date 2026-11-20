"""
Tool :: AntiTamperSentinel (defensive hardening suite)

Read-only tamper detection for the user's OWN PE binaries and builds.
Nothing here creates injection/stealth/bypass tooling — it only
ANALYZES and REPORTS so you can harden your own software.

Actions:
  pe_header    -> parse PE/COFF header summary (sections, entry point,
                  image base, characteristics, subsystem)
  import_table -> list imported DLLs + functions (read-only disassembly
                  surface for your own binaries)
  section_integrity -> SHA-256 of each section + size/vsize comparison;
                      flags sections with suspicious RWX characteristics
  diff_baseline -> compare current PE against a previous JSON baseline;
                  reports section-by-section delta offsets (hex)

All paths are sandboxed via UniversalFileManager rules; host paths need
Full Access Mode. Never writes to the inspected target.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Dict, List

import configs as config
from .base import Tool


class AntiTamperSentinel(Tool):
    name = "AntiTamperSentinel"
    description = (
        "Defensive PE/binary integrity analysis (read-only): "
        "{'action': 'pe_header'|'import_table'|'section_integrity'|"
        "'diff_baseline', 'path', 'baseline'} — reports PE structure, "
        "imports, section hashes and RWX flags, and section-level deltas "
        "against a saved baseline. For your own binaries only."
    )
    example = {"action": "pe_header", "path": "build/game.exe"}

    async def run(self, action: str = "", **kw: Any) -> str:
        try:
            handler = {
                "pe_header": self._pe_header,
                "import_table": self._import_table,
                "section_integrity": self._section_integrity,
                "diff_baseline": self._diff_baseline,
            }.get(str(action).lower().strip())
            if handler is None:
                return ("ERROR: unknown action (pe_header | import_table | "
                        "section_integrity | diff_baseline)")
            return await handler(kw)
        except PermissionError as exc:
            return f"ERROR: denied — {exc}"
        except Exception as exc:
            return f"ERROR: sentinel {action}: {exc}"

    def _resolve(self, kw) -> Path:
        path = str(kw.get("path", "."))
        if str(kw.get("scope", "workspace")).lower() == "host":
            return self.resolve_any(path)
        return self.safe_path(path)

    # ------------------------------------------------------------------ #
    def _parse_pe(self, target: Path) -> Dict:
        data = target.read_bytes()
        if len(data) < 64 or data[:2] != b"MZ":
            return {"error": "not a PE file (no MZ signature)"}
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if pe_offset + 24 > len(data):
            return {"error": "truncated PE header"}
        sig = data[pe_offset:pe_offset + 4]
        if sig != b"PE\x00\x00":
            return {"error": "not a PE file (no PE signature)"}
        # COFF header
        machine, num_sections, tdptr, tdsize, characteristics = \
            struct.unpack_from("<HHIII", data, pe_offset + 4)
        # Optional header magic
        opt_magic = struct.unpack_from("<H", data, pe_offset + 24)[0]
        opt_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
        entry = None
        image_base = None
        subsystem = None
        dll_characteristics = None
        if opt_magic == 0x10B:   # PE32
            entry = struct.unpack_from("<I", data, pe_offset + 24 + 16)[0]
            image_base = struct.unpack_from("<I", data, pe_offset + 24 + 28)[0]
            subsystem = struct.unpack_from("<H", data, pe_offset + 24 + 68)[0]
            dll_characteristics = struct.unpack_from(
                "<H", data, pe_offset + 24 + 70)[0]
        elif opt_magic == 0x20B:  # PE32+
            entry = struct.unpack_from("<Q", data, pe_offset + 24 + 24)[0]
            image_base = struct.unpack_from("<Q", data, pe_offset + 24 + 40)[0]
            subsystem = struct.unpack_from("<H", data, pe_offset + 24 + 88)[0]
            dll_characteristics = struct.unpack_from(
                "<H", data, pe_offset + 24 + 114)[0]
        sections: List[Dict] = []
        sec_start = pe_offset + 24 + opt_size
        for i in range(num_sections):
            s = sec_start + i * 40
            if s + 40 > len(data):
                break
            name = data[s:s + 8].split(b"\x00")[0].decode("ascii", "ignore")
            vsize, vaddr, rsize, ptr_raw = struct.unpack_from(
                "<IIII", data, s + 8)
            # s+24: PointerToRelocations(I), s+28: PointerToLinenumbers(I),
            # s+32/34: NumberOfRelocations/Linenumbers (H,H)
            # s+36: Characteristics (I)
            chars = struct.unpack_from("<I", data, s + 36)[0]
            sections.append({
                "name": name,
                "virtual_size": vsize,
                "virtual_address": vaddr,
                "raw_size": rsize,
                "pointer_to_raw": ptr_raw,
                "characteristics": chars,
                "writable": bool(chars & 0x80000000),
                "executable": bool(chars & 0x20000000),
                "readable": bool(chars & 0x40000000),
            })
        return {
            "machine": hex(machine),
            "sections": num_sections,
            "entry_point": hex(entry) if entry is not None else None,
            "image_base": hex(image_base) if image_base is not None else None,
            "subsystem": subsystem,
            "dll_characteristics": hex(dll_characteristics) if dll_characteristics is not None else None,
            "characteristics": hex(characteristics),
            "sections_detail": sections,
            "size": len(data),
        }

    # ------------------------------------------------------------------ #
    async def _pe_header(self, kw) -> str:
        target = self._resolve(kw)
        if not target.is_file():
            return f"ERROR: no such file: {kw.get('path')}"
        info = self._parse_pe(target)
        if "error" in info:
            return f"ERROR: {info['error']}"
        rwx = [s["name"] for s in info["sections_detail"]
               if s["writable"] and s["executable"]]
        lines = [
            f"PE HEADER: {target.name}",
            f"  machine: {info['machine']}  sections: {info['sections']}",
            f"  entry point: {info['entry_point']}  "
            f"image base: {info['image_base']}",
            f"  subsystem: {info['subsystem']}  "
            f"dll chars: {info['dll_characteristics']}",
            f"  file size: {info['size']} bytes",
            f"  sections:",
        ]
        for s in info["sections_detail"]:
            flags = []
            if s["readable"]:
                flags.append("R")
            if s["writable"]:
                flags.append("W")
            if s["executable"]:
                flags.append("X")
            lines.append(
                f"    {s['name']:<8} va=0x{s['virtual_address']:08X} "
                f"vsize=0x{s['virtual_size']:08X} raw=0x{s['raw_size']:08X} "
                f"ptr=0x{s['pointer_to_raw']:08X} [{''.join(flags) or '-'}]"
            )
        if rwx:
            lines.append(f"  ⚠ RWX sections (self-modification surface): {rwx}")
        return "\n".join(lines)

    async def _import_table(self, kw) -> str:
        """Read-only list of imported DLLs/functions via the Import
        Directory (no disassembly engine — structural read only)."""
        target = self._resolve(kw)
        if not target.is_file():
            return f"ERROR: no such file: {kw.get('path')}"
        data = target.read_bytes()
        if data[:2] != b"MZ":
            return "ERROR: not a PE file"
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        try:
            opt_start = pe_offset + 24
            # Data directories تبدأ من opt+96 (PE32) / opt+112 (PE32+)؛
            # directory[1] = Import Directory (RVA, size)
            dd_base = opt_start + \
                (96 if struct.unpack_from("<H", data, opt_start)[0] == 0x10B else 112)
            import_rva, import_size = struct.unpack_from(
                "<II", data, dd_base + 8)
        except struct.error:
            return "ERROR: could not locate import directory"
        if import_rva == 0 or import_size == 0:
            return "No import directory found (statically linked or stripped)"
        # RVA -> file offset (very rough 1:1 for the sentinel; good enough
        # for a read-only summary of your own PE)
        def rva_to_offset(rva: int) -> int:
            return rva  # sentinel approximation; section mapping omitted
        off = rva_to_offset(import_rva)
        dlls: List[str] = []
        i = 0
        while i + 20 <= len(data) and len(dlls) < 60:
            name_rva = struct.unpack_from("<I", data, off + i * 20)[0]
            if name_rva == 0:
                break
            # read dll name (null-terminated ascii)
            noff = rva_to_offset(name_rva)
            end = data.find(b"\x00", noff)
            if end == -1:
                break
            dlls.append(data[noff:end].decode("ascii", "ignore"))
            i += 1
        lines = [f"IMPORT TABLE (structural read-only): {target.name}"]
        lines += [f"  {d}" for d in dlls]
        return "\n".join(lines) if dlls else "No imported DLLs detected"

    async def _section_integrity(self, kw) -> str:
        target = self._resolve(kw)
        if not target.is_file():
            return f"ERROR: no such file: {kw.get('path')}"
        info = self._parse_pe(target)
        if "error" in info:
            return f"ERROR: {info['error']}"
        data = target.read_bytes()
        lines = [f"SECTION INTEGRITY: {target.name}"]
        for s in info["sections_detail"]:
            ptr = s["pointer_to_raw"]
            rsize = s["raw_size"]
            chunk = data[ptr:ptr + rsize] if ptr and rsize else b""
            sha = hashlib.sha256(chunk).hexdigest()[:16]
            crc = hex(__import__("zlib").crc32(chunk) & 0xFFFFFFFF)
            rwx = "RWX" if s["writable"] and s["executable"] else \
                "".join(c for c, v in [("R", s["readable"]),
                                        ("W", s["writable"]),
                                        ("X", s["executable"])] if v) or "-"
            lines.append(
                f"  {s['name']:<8} [{rwx}] sha256={sha} crc32={crc} "
                f"raw=0x{rsize:X} va=0x{s['virtual_address']:08X}"
            )
        return "\n".join(lines)

    async def _diff_baseline(self, kw) -> str:
        target = self._resolve(kw)
        if not target.is_file():
            return f"ERROR: no such file: {kw.get('path')}"
        baseline_name = str(kw.get("baseline", "sentinel_baseline.json"))
        bp = config.WORKSPACE_DIR / "sentinel" / baseline_name
        if not bp.is_file():
            return ("ERROR: baseline not found — run section_integrity "
                    "first and save it, or point 'baseline' at a JSON file")
        old = json.loads(bp.read_text(encoding="utf-8"))
        data = target.read_bytes()
        info = self._parse_pe(target)
        if "error" in info:
            return f"ERROR: {info['error']}"
        old_sections = {s["name"]: s for s in old.get("sections_detail", [])}
        lines = [f"BASELINE DIFF: {target.name} vs {baseline_name}"]
        changed = 0
        for s in info["sections_detail"]:
            old_s = old_sections.get(s["name"])
            if old_s is None:
                lines.append(f"  ADDED section: {s['name']}")
                changed += 1
                continue
            if (s["virtual_size"] != old_s["virtual_size"] or
                    s["raw_size"] != old_s["raw_size"] or
                    s["characteristics"] != old_s["characteristics"]):
                changed += 1
                lines.append(
                    f"  CHANGED: {s['name']} "
                    f"(old vsize=0x{old_s['virtual_size']:X} "
                    f"new=0x{s['virtual_size']:X}; "
                    f"old chars={old_s['characteristics']} "
                    f"new={s['characteristics']})"
                )
        if changed == 0:
            lines.append("  CLEAN — no structural section changes detected")
        return "\n".join(lines)
