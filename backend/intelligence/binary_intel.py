"""Static binary identification and analysis — no uploaded binary is executed."""
from __future__ import annotations

import hashlib
import math
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from .toolchain import discover, pick

MAX_BYTES = 256 * 1024 * 1024


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def identify(path: str | Path) -> Dict[str, Any]:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise ValueError(f"not a file: {p}")
    size = p.stat().st_size
    if size > MAX_BYTES:
        raise ValueError(f"file too large: {size} bytes")
    head = p.read_bytes()[:64]
    fmt = "unknown"
    if head[:2] == b"MZ":
        fmt = "pe"
    elif head[:4] == b"\x7fELF":
        fmt = "elf"
    elif head[:4] == b"PK\x03\x04":
        fmt = "zip"
    elif head[:4] in (b"\xca\xfe\xba\xbe",):
        fmt = "java-class-or-fat-jar"
    elif head[:4] == b"\xde\xd0\xb5\xa2":
        fmt = "dex"
    elif head[:4] == b"\x00asm":
        fmt = "wasm"
    ext = p.suffix.lower()
    if fmt == "zip":
        if ext in (".apk", ".aab"):
            fmt = ext[1:]
        elif ext in (".jar",):
            fmt = "jar"
    arch = ""
    if fmt == "pe":
        import struct

        if len(head) >= 40:
            pe_off = struct.unpack_from("<I", head, 0x3C)[0]
            if pe_off:
                arch = "pe32+" if pe_off + 24 <= len(head) and struct.unpack_from("<H", head, pe_off + 24)[0] == 0x20B else "pe32"
    elif fmt == "elf":
        arch = {1: "elf32", 2: "elf64"}.get(head[4], "elf-unknown")
    return {
        "path": str(p),
        "name": p.name,
        "size": size,
        "sha256": _sha256(p),
        "format": fmt,
        "architecture": arch,
        "extension": ext,
        "magic": head[:16].hex(),
        "identified": fmt != "unknown",
        "tools_available": pick(fmt, "identify"),
        "tools_missing": [t["name"] for t in discover()["tools"] if not t["available"] and fmt in t["inputs"]],
    }


def strings(path: str | Path, minimum: int = 6, limit: int = 500) -> List[str]:
    p = Path(path)
    data = p.read_bytes()[:20 * 1024 * 1024]
    found = re.findall(rb"[\x20-\x7e]{%d,}" % minimum, data)
    out: List[str] = []
    seen = set()
    for item in found:
        text = item.decode("ascii", errors="replace")
        if text not in seen:
            seen.add(text)
            out.append(text[:300])
            if len(out) >= limit:
                break
    return out


def _pe_report(path: Path) -> Dict[str, Any]:
    import pefile

    pe = pefile.PE(str(path), fast_load=False)
    machine = getattr(pe.FILE_HEADER, "Machine", 0)
    sections = []
    for s in pe.sections:
        raw = s.get_data()[:65536]
        sections.append({
            "name": s.Name.decode(errors="replace").rstrip("\x00"),
            "virtual_address": hex(s.VirtualAddress),
            "size": s.SizeOfRawData,
            "entropy": round(_entropy(raw), 3),
            "characteristics": hex(s.Characteristics),
        })
    imports = []
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            imports.append({
                "dll": entry.dll.decode(errors="replace"),
                "functions": [i.name.decode(errors="replace") for i in entry.imports[:200] if i.name],
            })
    exports = []
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        exports = [e.name.decode(errors="replace") for e in pe.DIRECTORY_ENTRY_EXPORT.symbols[:300] if e.name]
    resources = len(getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None).entries) if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE") else 0
    signed = hasattr(pe, "DIRECTORY_ENTRY_SECURITY")
    debug = bool(getattr(pe, "DIRECTORY_ENTRY_DEBUG", None))
    return {
        "machine": hex(machine),
        "sections": sections,
        "imports": imports,
        "exports": exports,
        "resource_entries": resources,
        "signed": signed,
        "debug_info": debug,
        "packing_indicators": [s["name"] for s in sections if s["entropy"] > 7.4 or s["name"].lower() in (".upx0", ".upx1", ".aspack", ".nsp0")],
    }


def _elf_report(path: Path) -> Dict[str, Any]:
    from elftools.elf.elffile import ELFFile

    with path.open("rb") as fh:
        elf = ELFFile(fh)
        header = elf.header
        sections = [{"name": s.name, "type": s["sh_type"], "size": s["sh_size"], "address": hex(s["sh_addr"])}
                    for s in elf.iter_sections()]
        symbols = []
        symtab = elf.get_section_by_name(".symtab")
        if symtab:
            symbols = [{"name": s.name, "value": hex(s["st_value"]), "size": s["st_size"]}
                       for s in symtab.iter_symbols() if s.name][:500]
        needed = []
        dynamic = elf.get_section_by_name(".dynamic")
        if dynamic:
            for tag in dynamic.iter_tags():
                if getattr(tag, "entry", None) == "DT_NEEDED":
                    needed.append(tag.needed)
        return {
            "class": header["e_ident"]["EI_CLASS"],
            "machine": header["e_machine"],
            "entry": hex(header["e_entry"]),
            "sections": sections[:300],
            "symbols": symbols,
            "needed_libraries": needed,
        }


def _archive_report(path: Path, fmt: str) -> Dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            interesting = [n for n in names if re.search(r"(AndroidManifest|classes\.dex|META-INF/|\.so$|plugin|manifest)", n, re.I)]
            return {"entries": len(names), "sample": names[:200], "interesting": interesting[:100], "format": fmt}
    except Exception as exc:
        return {"error": str(exc), "format": fmt}


def disassemble(path: str | Path, limit: int = 120) -> List[Dict[str, Any]]:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_MODE_64

    p = Path(path)
    info = identify(p)
    data = p.read_bytes()[:8 * 1024 * 1024]
    if info["format"] == "pe":
        import pefile

        pe = pefile.PE(str(p))
        code = next((s for s in pe.sections if s.Characteristics & 0x20000000), None)
        if code:
            data = code.get_data()[:200000]
            mode = CS_MODE_64 if info["architecture"] == "pe32+" else CS_MODE_32
        else:
            mode = CS_MODE_32
    elif info["format"] == "elf":
        mode = CS_MODE_64 if info["architecture"] == "elf64" else CS_MODE_32
    else:
        mode = CS_MODE_64
    md = Cs(CS_ARCH_X86, mode)
    return [{"address": hex(i.address), "mnemonic": i.mnemonic, "operands": i.op_str}
            for i in list(md.disasm(data, 0x1000))[:limit]]


def analyze(path: str | Path, include_strings: bool = True, include_disasm: bool = False) -> Dict[str, Any]:
    report = identify(path)
    p = Path(report["path"])
    fmt = report["format"]
    analysis: Dict[str, Any] = {}
    try:
        if fmt == "pe":
            analysis = _pe_report(p)
        elif fmt == "elf":
            analysis = _elf_report(p)
        elif fmt in ("apk", "aab", "jar", "zip"):
            analysis = _archive_report(p, fmt)
    except Exception as exc:
        analysis = {"error": f"{type(exc).__name__}: {exc}"}
    result = {
        "identification": report,
        "analysis": analysis,
        "strings": strings(p) if include_strings else [],
        "disassembly": disassemble(p) if include_disasm else [],
        "limitations": [
            "Static analysis only; the artifact was not executed.",
            "Decompiled or recovered code, when present, is approximate and may not match original source names or structure.",
            "Missing external tools are reported honestly; no result is invented for an unavailable tool.",
        ],
        "tools": discover(),
    }
    return result
