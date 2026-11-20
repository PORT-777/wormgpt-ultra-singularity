# backend/security_ops/elfmacho.py
# Self-contained ELF and Mach-O parsers (headers, sections, segments,
# dynamic entries, symbols, mitigations, packing/entitlement indicators).

from __future__ import annotations

import hashlib
import struct
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .util import entropy, extract_strings, hash_bytes, high_entropy_regions

# --------------------------------------------------------------------------- #
#  ELF
# --------------------------------------------------------------------------- #
ELF_TYPES = {0: "NONE", 1: "REL", 2: "EXEC", 3: "DYN", 4: "CORE"}
ELF_MACHINES = {3: "x86", 62: "x86-64", 40: "ARM", 183: "ARM64", 8: "MIPS",
                20: "PowerPC", 21: "PowerPC64", 243: "RISC-V", 22: "S390",
                2: "SPARC", 43: "SPARCv9", 50: "IA-64", 7: "Intel 80860"}
PT_NAMES = {0: "NULL", 1: "LOAD", 2: "DYNAMIC", 3: "INTERP", 4: "NOTE",
            5: "SHLIB", 6: "PHDR", 7: "TLS", 8: "NUM", 0x6474E550: "GNU_EH_FRAME",
            0x6474E551: "GNU_STACK", 0x6474E552: "GNU_RELRO",
            0x6474E553: "GNU_PROPERTY"}
SHT_NAMES = {0: "NULL", 1: "PROGBITS", 2: "SYMTAB", 3: "STRTAB", 4: "RELA",
             5: "HASH", 6: "DYNAMIC", 7: "NOTE", 8: "NOBITS", 9: "REL",
             10: "SHLIB", 11: "DYNSYM", 14: "INIT_ARRAY", 15: "FINI_ARRAY",
             16: "PREINIT_ARRAY", 17: "GROUP", 18: "SYMTAB_SHNDX"}
PF_X, PF_W, PF_R = 1, 2, 4
SHF_WRITE, SHF_ALLOC, SHF_EXECINSTR = 1, 2, 4


def analyze_elf(data: bytes, filename: str = "") -> Dict[str, Any]:
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    if len(data) < 52:
        raise ValueError("truncated ELF header")
    cls = data[4]
    endian = "<" if data[5] == 1 else ">"
    is64 = cls == 2
    hdr = _elf_header(data, endian, is64)
    sections = _elf_sections(data, hdr, endian, is64)
    programs = _elf_programs(data, hdr, endian, is64)
    dyn = _elf_dynamic(data, hdr, sections, programs, endian, is64)
    symbols = _elf_symbols(data, hdr, sections, endian, is64)
    dyn_needed = _dyn_strings(data, hdr, sections, dyn.get("entries", []), "NEEDED",
                              endian, is64)
    rpath = _dyn_strings(data, hdr, sections, dyn.get("entries", []), "RPATH",
                         endian, is64)
    runpath = _dyn_strings(data, hdr, sections, dyn.get("entries", []), "RUNPATH",
                           endian, is64)
    interp = ""
    for p in programs:
        if p["type"] == "INTERP":
            off = p["offset"]
            interp = data[off:p["offset"] + p["filesz"]].split(b"\x00", 1)[0].decode("latin-1", "replace")
    build_id = _elf_build_id(data, hdr, sections)

    imports = sorted({s["name"] for s in symbols if s["undefined"] and s["name"]})
    exports = sorted({s["name"] for s in symbols if not s["undefined"] and s["binding"] in ("GLOBAL", "WEAK") and s["name"]})
    text = " ".join(extract_strings(data, 5, True, True, 4000)["ascii"])
    low = text.lower()
    packed = _elf_packed(sections, symbols, imports)

    mitigations = {
        "nx": any(p["type"] == "GNU_STACK" and not (p["flags"] & PF_X) for p in programs),
        "pie": hdr["type"] == "DYN",
        "relro": any(p["type"] == "GNU_RELRO" for p in programs),
        "bind_now": "BIND_NOW" in dyn.get("tags", []),
        "stack_canary": any("__stack_chk_fail" in s for s in symbols),
        "fortify": any(s["name"].endswith("_chk") for s in symbols),
        "rpath": rpath,
        "runpath": runpath,
    }
    mitigations["full_relro"] = mitigations["relro"] and mitigations["bind_now"]
    anomalies = []
    for p in programs:
        if p["type"] == "LOAD" and (p["flags"] & PF_W) and (p["flags"] & PF_X):
            anomalies.append({"severity": "high", "finding": f"W+X LOAD segment at 0x{p['vaddr']:x}"})
    for s in sections:
        if (s.get("flags", 0) & SHF_WRITE) and (s.get("flags", 0) & SHF_EXECINSTR):
            anomalies.append({"severity": "high", "finding": f"W+X section {s['name']}"})
        if s.get("entropy", 0) >= 7.2 and s.get("size", 0) > 4096:
            anomalies.append({"severity": "medium", "finding": f"high entropy section {s['name']} ({s['entropy']})"})
    if not mitigations["nx"]:
        anomalies.append({"severity": "high", "finding": "no GNU_STACK NX (executable stack)"})
    if not mitigations["pie"]:
        anomalies.append({"severity": "low", "finding": "not PIE (fixed load address)"})
    if not mitigations["relro"]:
        anomalies.append({"severity": "low", "finding": "no RELRO"})
    for rp in rpath + runpath:
        if any(x in rp for x in ("/tmp", "/var/tmp", "/dev/shm", ".")) or rp == "":
            anomalies.append({"severity": "high", "finding": f"untrusted RPATH/RUNPATH: {rp!r}"})
    if interp and interp not in ("/lib64/ld-linux-x86-64.so.2", "/lib/ld-linux.so.2",
                                 "/lib/ld-musl-x86_64.so.1", "/system/bin/linker64",
                                 "/system/bin/linker"):
        anomalies.append({"severity": "medium", "finding": f"non-standard interpreter {interp}"})
    if hdr["type"] == "DYN" and not imports and not exports and not interp:
        anomalies.append({"severity": "medium", "finding": "ET_DYN with no imports/exports/interpreter (shellcode/loader?)"})
    if "upx" in low or any(s["name"].startswith(".upx") for s in sections):
        anomalies.append({"severity": "high", "finding": "UPX packer markers"})

    score = sum({"critical": 25, "high": 15, "medium": 7, "low": 3}.get(a["severity"], 0) for a in anomalies)
    return {
        "filename": filename,
        "size": len(data),
        "format": "ELF64" if is64 else "ELF32",
        "endian": "little" if endian == "<" else "big",
        "header": hdr,
        "sections": sections,
        "program_headers": programs,
        "interpreter": interp,
        "dynamic": dyn,
        "needed": dyn_needed,
        "rpath": rpath,
        "runpath": runpath,
        "symbols_total": len(symbols),
        "symbols_sample": symbols[:80],
        "imports": imports[:400],
        "exports": exports[:400],
        "build_id": build_id,
        "mitigations": mitigations,
        "packed": packed,
        "anomalies": sorted(anomalies, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4)),
        "score": min(100, score),
        "strings": _elf_strings(data),
        "hashes": hash_bytes(data),
        "high_entropy_regions": high_entropy_regions(data, 7.2, 1024, 2)[:20],
    }


def _elf_header(data: bytes, endian: str, is64: bool) -> Dict[str, Any]:
    if is64:
        (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
         e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
         e_shstrndx) = struct.unpack_from(endian + "HHIQQQIHHHHHH", data, 16)
    else:
        (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
         e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
         e_shstrndx) = struct.unpack_from(endian + "HHIIIIIHHHHHH", data, 16)
    return {
        "class": "ELF64" if is64 else "ELF32",
        "type_code": e_type, "type": ELF_TYPES.get(e_type, f"type-{e_type}"),
        "machine_code": e_machine,
        "machine": ELF_MACHINES.get(e_machine, f"machine-{e_machine}"),
        "version": e_version, "entry": hex(e_entry),
        "phoff": e_phoff, "shoff": e_shoff, "flags": hex(e_flags),
        "ehsize": e_ehsize, "phentsize": e_phentsize, "phnum": e_phnum,
        "shentsize": e_shentsize, "shnum": e_shnum, "shstrndx": e_shstrndx,
        "osabi": data[7],
    }


def _elf_sections(data: bytes, hdr: Dict[str, Any], endian: str, is64: bool) -> List[Dict[str, Any]]:
    out = []
    if not hdr["shoff"] or not hdr["shnum"]:
        return out
    raw = []
    for i in range(min(hdr["shnum"], 4096)):
        off = hdr["shoff"] + i * hdr["shentsize"]
        if off + hdr["shentsize"] > len(data):
            break
        if is64:
            (name, typ, flags, addr, offset, size, link, info, align,
             entsize) = struct.unpack_from(endian + "IIQQQQIIQQ", data, off)
        else:
            (name, typ, flags, addr, offset, size, link, info, align,
             entsize) = struct.unpack_from(endian + "IIIIIIIIII", data, off)
        raw.append({"name_off": name, "type_code": typ, "flags": flags, "addr": addr,
                    "offset": offset, "size": size, "link": link, "info": info,
                    "align": align, "entsize": entsize})
    strtab = b""
    if hdr["shstrndx"] < len(raw):
        st = raw[hdr["shstrndx"]]
        strtab = data[st["offset"]:st["offset"] + st["size"]]
    for r in raw:
        name = _cstr(strtab, r["name_off"])
        body = data[r["offset"]:r["offset"] + r["size"]] if r["type_code"] != 8 else b""
        out.append({"name": name, "type": SHT_NAMES.get(r["type_code"], str(r["type_code"])),
                    "type_code": r["type_code"], "flags": r["flags"],
                    "addr": hex(r["addr"]), "offset": r["offset"], "size": r["size"],
                    "link": r["link"], "entsize": r["entsize"],
                    "entropy": round(entropy(body), 3) if body else 0.0,
                    "sha256": hashlib.sha256(body).hexdigest() if body else ""})
    return out


def _elf_programs(data: bytes, hdr: Dict[str, Any], endian: str, is64: bool) -> List[Dict[str, Any]]:
    out = []
    for i in range(min(hdr["phnum"], 1024)):
        off = hdr["phoff"] + i * hdr["phentsize"]
        if off + hdr["phentsize"] > len(data):
            break
        if is64:
            p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = \
                struct.unpack_from(endian + "IIQQQQQQ", data, off)
        else:
            p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = \
                struct.unpack_from(endian + "IIIIIIII", data, off)
        out.append({"type": PT_NAMES.get(p_type, hex(p_type)), "type_code": p_type,
                    "flags": p_flags, "offset": p_offset, "vaddr": p_vaddr,
                    "paddr": p_paddr, "filesz": p_filesz, "memsz": p_memsz,
                    "align": p_align,
                    "perms": ("R" if p_flags & PF_R else "-") +
                             ("W" if p_flags & PF_W else "-") +
                             ("X" if p_flags & PF_X else "-")})
    return out


def _elf_dynamic(data: bytes, hdr: Dict[str, Any], sections: List[Dict[str, Any]],
                 programs: List[Dict[str, Any]], endian: str, is64: bool) -> Dict[str, Any]:
    off = size = 0
    for p in programs:
        if p["type"] == "DYNAMIC":
            off, size = p["offset"], p["filesz"]
            break
    if not off:
        for s in sections:
            if s["type"] == "DYNAMIC":
                off, size = s["offset"], s["size"]
                break
    entries = []
    fmt = endian + ("qQ" if is64 else "iI")
    step = 16 if is64 else 8
    for pos in range(off, min(off + size, len(data) - step + 1), step):
        tag, val = struct.unpack_from(fmt, data, pos)
        entries.append((tag, val))
        if tag == 0:
            break
    tags = {0: "NULL", 1: "NEEDED", 2: "PLTRELSZ", 3: "PLTGOT", 4: "HASH",
            5: "STRTAB", 6: "SYMTAB", 7: "RELA", 8: "RELASZ", 9: "RELAENT",
            10: "STRSZ", 11: "SYMENT", 12: "INIT", 13: "FINI", 14: "SONAME",
            15: "RPATH", 16: "SYMBOLIC", 17: "REL", 18: "RELSZ", 19: "RELENT",
            20: "PLTREL", 21: "DEBUG", 22: "TEXTREL", 23: "JMPREL",
            24: "BIND_NOW", 25: "INIT_ARRAY", 26: "FINI_ARRAY",
            27: "INIT_ARRAYSZ", 28: "FINI_ARRAYSZ", 29: "RUNPATH",
            30: "FLAGS", 0x6ffffef5: "GNU_HASH", 0x6ffffff0: "VERSYM",
            0x6ffffff9: "RELACOUNT", 0x6ffffffa: "RELCOUNT",
            0x6ffffffb: "FLAGS_1", 0x6ffffffc: "VERDEF", 0x6ffffffd: "VERDEFNUM",
            0x6ffffffe: "VERNEED", 0x6fffffff: "VERNEEDNUM"}
    names = [tags.get(t, hex(t)) for t, _ in entries if t in (24,) or tags.get(t)]
    return {"entries": entries[:400], "tags": names,
            "textrel": any(t == 22 for t, _ in entries),
            "soname": _first_dyn_str(data, sections, entries, 14, endian, is64)}


def _first_dyn_str(data: bytes, sections: List[Dict[str, Any]], entries: List[Tuple[int, int]],
                   wanted: int, endian: str, is64: bool) -> str:
    vals = _dyn_strings(data, {}, sections, entries, "SONAME" if wanted == 14 else "NEEDED",
                        endian, is64)
    return vals[0] if vals else ""


def _dyn_strings(data: bytes, hdr: Dict[str, Any], sections: List[Dict[str, Any]],
                 entries: List[Tuple[int, int]], which: str, endian: str,
                 is64: bool) -> List[str]:
    tag_map = {"NEEDED": 1, "SONAME": 14, "RPATH": 15, "RUNPATH": 29}
    wanted = tag_map.get(which, 1)
    strtab_addr = None
    strsz = 0
    for tag, val in entries:
        if tag == 5:
            strtab_addr = val
        elif tag == 10:
            strsz = val
    if strtab_addr is None:
        return []
    off = None
    for s in sections:
        if s["type"] == "STRTAB" or int(s["addr"], 16) == strtab_addr:
            if int(s["addr"], 16) == strtab_addr:
                off = s["offset"]
                break
    if off is None:
        # map virtual address through program headers
        off = strtab_addr
    out = []
    for tag, val in entries:
        if tag == wanted:
            out.append(_cstr(data, off + val))
    return out


def _elf_symbols(data: bytes, hdr: Dict[str, Any], sections: List[Dict[str, Any]],
                 endian: str, is64: bool) -> List[Dict[str, Any]]:
    out = []
    for s in sections:
        if s["type"] not in ("SYMTAB", "DYNSYM"):
            continue
        entsize = s.get("entsize") or (24 if is64 else 16)
        strtab_off = 0
        if s["link"] < len(sections):
            strtab_off = sections[s["link"]]["offset"]
        count = min(s["size"] // entsize if entsize else 0, 20000)
        for i in range(count):
            off = s["offset"] + i * entsize
            if off + entsize > len(data):
                break
            if is64:
                st_name, st_info, st_other, st_shndx, st_value, st_size = \
                    struct.unpack_from(endian + "IBBHQQ", data, off)
            else:
                st_name, st_value, st_size, st_info, st_other, st_shndx = \
                    struct.unpack_from(endian + "IIIBBH", data, off + 0)
            name = _cstr(data, strtab_off + st_name) if st_name else ""
            bind = {0: "LOCAL", 1: "GLOBAL", 2: "WEAK"}.get(st_info >> 4, str(st_info >> 4))
            typ = {0: "NOTYPE", 1: "OBJECT", 2: "FUNC", 3: "SECTION", 4: "FILE",
                   5: "COMMON", 6: "TLS"}.get(st_info & 0xF, str(st_info & 0xF))
            out.append({"name": name, "binding": bind, "type": typ,
                        "undefined": st_shndx == 0, "shndx": st_shndx,
                        "value": hex(st_value), "size": st_size})
    return out


def _elf_build_id(data: bytes, hdr: Dict[str, Any], sections: List[Dict[str, Any]]) -> str:
    for s in sections:
        if s["type"] == "NOTE" and "build" in s["name"].lower():
            blob = data[s["offset"]:s["offset"] + s["size"]]
            idx = blob.find(b"GNU")
            if idx >= 0 and idx + 16 <= len(blob):
                namesz, descsz, ntype = struct.unpack_from("<III", blob, idx)
                start = idx + 12 + ((namesz + 3) & ~3)
                return blob[start:start + descsz].hex()
    return ""


def _cstr(blob: bytes, off: int) -> str:
    if off < 0 or off >= len(blob):
        return ""
    end = blob.find(b"\x00", off)
    return blob[off:end if end >= 0 else off + 128].decode("latin-1", "replace")


def _elf_packed(sections: List[Dict[str, Any]], symbols: List[Dict[str, Any]],
                imports: List[str]) -> Dict[str, Any]:
    evidence = []
    entropy_sections = [s["name"] for s in sections if s.get("entropy", 0) > 7.2 and s.get("size", 0) > 4096]
    if entropy_sections:
        evidence.append(f"high entropy sections: {entropy_sections}")
    if not symbols:
        evidence.append("no symbol table (stripped)")
    if len(imports) <= 3 and symbols:
        evidence.append(f"very few imports ({len(imports)})")
    names = [s["name"].lower() for s in sections]
    if any(n.startswith(".upx") or n == "upx0" for n in names):
        evidence.append("UPX section names")
    return {"likely": bool(entropy_sections or any("UPX" in e for e in evidence)),
            "evidence": evidence}


def _elf_strings(data: bytes) -> Dict[str, Any]:
    parsed = extract_strings(data, 5, True, True, 5000)
    interesting = []
    keep = ("http://", "https://", "/bin/", "/tmp/", "curl", "wget", "chmod",
            "chattr", "crontab", "systemd", "ld.so.preload", "authorized_keys",
            "base64", "openssl", "ssh", "reverse", "shell", "miner", "stratum",
            "xmrig", "ld_preload", "ptrace", "hide", "rootkit", "keylog",
            "ransom", "encrypt", "decrypt", "bitcoin", "monero", "/dev/tcp",
            "bash -i", "sh -c", "python", "perl", "socat", "nc ", "ncat")
    for s in parsed["ascii"] + parsed["unicode"]:
        low = s.lower()
        if any(k in low for k in keep):
            interesting.append(s)
        if len(interesting) >= 300:
            break
    return {"interesting": list(dict.fromkeys(interesting)),
            "ascii_count": parsed["counts"]["ascii"],
            "unicode_count": parsed["counts"]["unicode"]}


# --------------------------------------------------------------------------- #
#  Mach-O
# --------------------------------------------------------------------------- #
MACHO_MAGICS = {
    b"\xfe\xed\xfa\xce": ("32", ">"), b"\xce\xfa\xed\xfe": ("32", "<"),
    b"\xfe\xed\xfa\xcf": ("64", ">"), b"\xcf\xfa\xed\xfe": ("64", "<"),
    b"\xca\xfe\xba\xbe": ("fat32", ">"), b"\xbe\xba\xfe\xca": ("fat32", "<"),
    b"\xca\xfe\xba\xbf": ("fat64", ">"), b"\xbf\xba\xfe\xca": ("fat64", "<"),
}
CPU_TYPES = {7: "x86", 0x01000007: "x86-64", 12: "ARM", 0x0100000C: "ARM64",
             18: "PowerPC", 0x01000012: "PowerPC64"}
FILE_TYPES = {1: "OBJECT", 2: "EXECUTE", 3: "FVMLIB", 4: "CORE", 5: "PRELOAD",
              6: "DYLIB", 7: "DYLINKER", 8: "BUNDLE", 9: "DYLIB_STUB",
              10: "DSYM", 11: "KEXT_BUNDLE"}
PLATFORMS = {1: "macOS", 2: "iOS", 3: "tvOS", 4: "watchOS", 5: "bridgeOS",
             6: "macCatalyst", 7: "iOSSimulator", 8: "tvOSSimulator",
             9: "watchOSSimulator", 10: "driverKit"}


def analyze_macho(data: bytes, filename: str = "") -> Dict[str, Any]:
    magic = data[:4]
    if magic not in MACHO_MAGICS:
        raise ValueError("not a Mach-O file")
    kind, endian = MACHO_MAGICS[magic]
    if kind.startswith("fat"):
        return _analyze_fat(data, filename, kind, endian)
    hdr = _macho_header(data, endian, kind == "64")
    cmds, info = _macho_commands(data, hdr, endian, kind == "64")
    anomalies = []
    if info["encrypted"]:
        anomalies.append({"severity": "high", "finding": "binary is encrypted (App Store fairplay / cryptid != 0)"})
    for seg in [c for c in cmds if c["cmd"] in ("LC_SEGMENT", "LC_SEGMENT_64")]:
        if (seg.get("initprot", 0) & 0x4) and (seg.get("initprot", 0) & 0x2):
            anomalies.append({"severity": "high", "finding": f"segment {seg['name']} is W+X"})
        if seg.get("name") == "__TEXT" and seg.get("entropy", 0) > 7.2:
            anomalies.append({"severity": "medium", "finding": "__TEXT entropy is high (packed/encrypted)"})
    if not info["code_signature"]:
        anomalies.append({"severity": "medium", "finding": "no code signature load command"})
    if info["rpaths"]:
        for rp in info["rpaths"]:
            if "/tmp" in rp or "@executable_path/../" in rp:
                anomalies.append({"severity": "medium", "finding": f"writable-relative rpath {rp}"})
    text = " ".join(extract_strings(data, 5, True, True, 5000)["ascii"])
    low = text.lower()
    if "get-task-allow" in low:
        anomalies.append({"severity": "high", "finding": "get-task-allow entitlement (debuggable build)"})
    if "nsallowsarbitraryloads" in low:
        anomalies.append({"severity": "medium", "finding": "App Transport Security disabled"})
    score = sum({"critical": 25, "high": 15, "medium": 7, "low": 3}.get(a["severity"], 0) for a in anomalies)
    return {
        "filename": filename, "size": len(data), "format": f"Mach-O {kind}",
        "endian": "little" if endian == "<" else "big",
        "header": hdr,
        "load_commands": cmds[:200],
        "dylibs": info["dylibs"], "rpaths": info["rpaths"],
        "segments": info["segments"], "uuid": info["uuid"],
        "platform": info["platform"], "min_os": info["min_os"], "sdk": info["sdk"],
        "entry_point": info["entry_point"],
        "encrypted": info["encrypted"], "code_signature": info["code_signature"],
        "entitlement_hints": [x for x in ("get-task-allow", "platform-application",
                                          "com.apple.security", "com.apple.private",
                                          "nsallowsarbitraryloads") if x in low],
        "objc": "__objc" in low or b"__OBJC" in data,
        "swift": "swift" in low or b"libswiftCore" in data,
        "packed": bool(not info["dylibs"] and hdr["filetype"] == 2 and not info["code_signature"]),
        "anomalies": anomalies,
        "score": min(100, score),
        "strings": _macho_strings(data),
        "hashes": hash_bytes(data),
    }


def _macho_header(data: bytes, endian: str, is64: bool) -> Dict[str, Any]:
    if is64:
        (magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags,
         reserved) = struct.unpack_from(endian + "IIIIIIII", data, 0)
    else:
        magic, cputype, cpusubtype, filetype, ncmds, sizeofcmds, flags = \
            struct.unpack_from(endian + "IIIIIII", data, 0)
        reserved = 0
    return {"magic": hex(magic), "cputype": cputype,
            "cpu": CPU_TYPES.get(cputype, f"cpu-{cputype}"),
            "cpusubtype": cpusubtype, "filetype_code": filetype,
            "filetype": FILE_TYPES.get(filetype, str(filetype)),
            "ncmds": ncmds, "sizeofcmds": sizeofcmds, "flags": hex(flags),
            "reserved": reserved, "header_size": 32 if is64 else 28}


def _macho_commands(data: bytes, hdr: Dict[str, Any], endian: str,
                    is64: bool) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    cmds: List[Dict[str, Any]] = []
    dylibs: List[str] = []
    rpaths: List[str] = []
    segments: List[Dict[str, Any]] = []
    uuid = ""
    platform = ""
    min_os = ""
    sdk = ""
    entry = ""
    encrypted = False
    code_sig = False
    off = hdr["header_size"]
    for _ in range(min(hdr["ncmds"], 4096)):
        if off + 8 > len(data):
            break
        cmd, size = struct.unpack_from(endian + "II", data, off)
        if size < 8 or off + size > len(data):
            break
        body = data[off:off + size]
        name = _lc_name(cmd)
        item: Dict[str, Any] = {"cmd": name, "cmd_code": hex(cmd), "size": size}
        try:
            if cmd in (0x19, 0x1):  # LC_SEGMENT_64 / LC_SEGMENT
                if cmd == 0x19:
                    segname = body[8:24].rstrip(b"\x00").decode("latin-1", "replace")
                    vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, flags = \
                        struct.unpack_from(endian + "QQQQIIII", body, 24)
                    sect_off = 72
                    sect_size = 80
                else:
                    segname = body[8:24].rstrip(b"\x00").decode("latin-1", "replace")
                    vmaddr, vmsize, fileoff, filesize, maxprot, initprot, nsects, flags = \
                        struct.unpack_from(endian + "IIIIIIII", body, 24)
                    sect_off = 56
                    sect_size = 68
                blob = data[fileoff:fileoff + filesize] if filesize else b""
                item.update({"name": segname, "vmaddr": hex(vmaddr), "vmsize": vmsize,
                             "fileoff": fileoff, "filesize": filesize,
                             "maxprot": maxprot, "initprot": initprot,
                             "nsects": nsects, "flags": flags,
                             "entropy": round(entropy(blob), 3) if blob else 0.0})
                segments.append({"name": segname, "entropy": item["entropy"],
                                 "filesize": filesize, "initprot": initprot})
                section_names = []
                for si in range(min(nsects, 256)):
                    so = sect_off + si * sect_size
                    if so + sect_size > len(body):
                        break
                    if cmd == 0x19:
                        sname = body[so:so + 16].rstrip(b"\x00").decode("latin-1", "replace")
                        sgname = body[so + 16:so + 32].rstrip(b"\x00").decode("latin-1", "replace")
                        addr, ssize = struct.unpack_from(endian + "QQ", body, so + 32)
                        offset = struct.unpack_from(endian + "I", body, so + 48)[0]
                    else:
                        sname = body[so:so + 16].rstrip(b"\x00").decode("latin-1", "replace")
                        sgname = body[so + 16:so + 32].rstrip(b"\x00").decode("latin-1", "replace")
                        addr, ssize = struct.unpack_from(endian + "II", body, so + 32)
                        offset = struct.unpack_from(endian + "I", body, so + 40)[0]
                    section_names.append({"name": sname, "segment": sgname,
                                          "addr": hex(addr), "size": ssize,
                                          "offset": offset})
                item["sections"] = section_names
            elif cmd in (0xC, 0x8000001F, 0x18, 0x1F, 0x23):  # load dylibs / weak / reexport / id
                str_off = struct.unpack_from(endian + "I", body, 8)[0]
                path = body[str_off:].split(b"\x00", 1)[0].decode("utf-8", "replace")
                item["path"] = path
                if cmd != 0xD:
                    dylibs.append(path)
            elif cmd == 0x8000001C:  # LC_RPATH
                str_off = struct.unpack_from(endian + "I", body, 8)[0]
                rp = body[str_off:].split(b"\x00", 1)[0].decode("utf-8", "replace")
                item["path"] = rp
                rpaths.append(rp)
            elif cmd in (0x28, 0x28 | 0x80000000):  # LC_MAIN
                entryoff = struct.unpack_from(endian + "Q", body, 8)[0]
                item["entryoff"] = hex(entryoff)
                entry = item["entryoff"]
            elif cmd == 0x32:  # LC_BUILD_VERSION
                plat, minos, sdkv, ntools = struct.unpack_from(endian + "IIII", body, 8)
                platform = PLATFORMS.get(plat, str(plat))
                min_os = _version(minos)
                sdk = _version(sdkv)
                item.update({"platform": platform, "min_os": min_os, "sdk": sdk})
            elif cmd == 0x24:  # LC_VERSION_MIN_MACOSX
                ver, sdkv = struct.unpack_from(endian + "II", body, 8)
                platform, min_os, sdk = "macOS", _version(ver), _version(sdkv)
            elif cmd == 0x1B:  # LC_UUID
                uuid = body[8:24].hex()
            elif cmd == 0x1D:  # LC_CODE_SIGNATURE
                code_sig = True
            elif cmd in (0x21, 0x2C):  # LC_ENCRYPTION_INFO(_64)
                if cmd == 0x21:
                    cryptoff, cryptsize, cryptid = struct.unpack_from(endian + "III", body, 8)
                else:
                    cryptoff, cryptsize, cryptid, pad = struct.unpack_from(endian + "IIII", body, 8)
                encrypted = cryptid != 0
                item.update({"cryptoff": cryptoff, "cryptsize": cryptsize, "cryptid": cryptid})
            elif cmd in (0x2,):  # LC_SYMTAB
                symoff, nsyms, stroff, strsize = struct.unpack_from(endian + "IIII", body, 8)
                item.update({"symoff": symoff, "nsyms": nsyms, "stroff": stroff, "strsize": strsize})
        except Exception:
            item["parse_error"] = True
        cmds.append(item)
        off += size
    return cmds, {"dylibs": dylibs, "rpaths": rpaths, "segments": segments,
                  "uuid": uuid, "platform": platform, "min_os": min_os,
                  "sdk": sdk, "entry_point": entry, "encrypted": encrypted,
                  "code_signature": code_sig}


def _version(v: int) -> str:
    return f"{v >> 16}.{(v >> 8) & 0xFF}.{v & 0xFF}"


def _lc_name(cmd: int) -> str:
    names = {0x1: "LC_SEGMENT", 0x19: "LC_SEGMENT_64", 0x2: "LC_SYMTAB",
             0x3: "LC_SYMSEG", 0x4: "LC_THREAD", 0x5: "LC_UNIXTHREAD",
             0x6: "LC_LOADFVMLIB", 0x7: "LC_IDFVMLIB", 0x8: "LC_IDENT",
             0x9: "LC_FVMFILE", 0xA: "LC_PREPAGE", 0xB: "LC_DYSYMTAB",
             0xC: "LC_LOAD_DYLIB", 0xD: "LC_ID_DYLIB", 0xE: "LC_LOAD_DYLINKER",
             0xF: "LC_ID_DYLINKER", 0x10: "LC_PREBOUND_DYLIB",
             0x11: "LC_ROUTINES", 0x12: "LC_SUB_FRAMEWORK",
             0x13: "LC_SUB_UMBRELLA", 0x14: "LC_SUB_CLIENT",
             0x15: "LC_SUB_LIBRARY", 0x16: "LC_TWOLEVEL_HINTS",
             0x17: "LC_PREBIND_CKSUM", 0x18: "LC_LOAD_WEAK_DYLIB",
             0x19 | 0x80000000: "LC_SEGMENT_64", 0x1A: "LC_ROUTINES_64",
             0x1B: "LC_UUID", 0x1C: "LC_RPATH", 0x1D: "LC_CODE_SIGNATURE",
             0x1E: "LC_SEGMENT_SPLIT_INFO", 0x1F: "LC_REEXPORT_DYLIB",
             0x20: "LC_LAZY_LOAD_DYLIB", 0x21: "LC_ENCRYPTION_INFO",
             0x22: "LC_DYLD_INFO", 0x23: "LC_LOAD_UPWARD_DYLIB",
             0x24: "LC_VERSION_MIN_MACOSX", 0x25: "LC_VERSION_MIN_IPHONEOS",
             0x26: "LC_FUNCTION_STARTS", 0x27: "LC_DYLD_ENVIRONMENT",
             0x28: "LC_MAIN", 0x29: "LC_DATA_IN_CODE", 0x2A: "LC_SOURCE_VERSION",
             0x2B: "LC_DYLIB_CODE_SIGN_DRS", 0x2C: "LC_ENCRYPTION_INFO_64",
             0x2D: "LC_LINKER_OPTION", 0x2E: "LC_LINKER_OPTIMIZATION_HINT",
             0x2F: "LC_VERSION_MIN_TVOS", 0x30: "LC_VERSION_MIN_WATCHOS",
             0x31: "LC_NOTE", 0x32: "LC_BUILD_VERSION",
             0x33: "LC_DYLD_EXPORTS_TRIE", 0x34: "LC_DYLD_CHAINED_FIXUPS"}
    return names.get(cmd, hex(cmd))


def _analyze_fat(data: bytes, filename: str, kind: str, endian: str) -> Dict[str, Any]:
    magic, nfat = struct.unpack_from(endian + "II", data, 0)
    archs = []
    off = 8
    for i in range(min(nfat, 64)):
        if kind == "fat64":
            cputype, cpusubtype, offset, size, align, reserved = \
                struct.unpack_from(endian + "IIQQII", data, off)
            off += 32
        else:
            cputype, cpusubtype, offset, size, align = \
                struct.unpack_from(endian + "IIIII", data, off)
            off += 20
        archs.append({"cpu": CPU_TYPES.get(cputype, f"cpu-{cputype}"),
                      "cpusubtype": cpusubtype, "offset": offset, "size": size,
                      "align": align})
    analyses = []
    for a in archs[:8]:
        try:
            analyses.append(analyze_macho(data[a["offset"]:a["offset"] + a["size"]], filename))
        except Exception as exc:
            analyses.append({"error": str(exc)})
    return {"filename": filename, "format": f"Mach-O Universal ({kind})",
            "size": len(data), "architectures": archs,
            "slices": [{"cpu": a.get("cpu"), "score": a.get("score"),
                        "dylibs": a.get("dylibs"), "anomalies": a.get("anomalies")}
                       for a in analyses],
            "hashes": hash_bytes(data)}


def _macho_strings(data: bytes) -> Dict[str, Any]:
    parsed = extract_strings(data, 5, True, True, 5000)
    keep = ("http://", "https://", "api.", "telegram", "discord", "firebase",
            "amazonaws", "azure", "googleapis", "keychain", "nsuserdefaults",
            "get-task-allow", "platform-application", "com.apple.security",
            "jailbreak", "cydia", "substrate", "frida", "ssh", "password",
            "token", "secret", "api_key", "apikey", "private_key", "pin")
    interesting = [s for s in parsed["ascii"] + parsed["unicode"]
                   if any(k in s.lower() for k in keep)][:300]
    return {"interesting": list(dict.fromkeys(interesting)),
            "ascii_count": parsed["counts"]["ascii"],
            "unicode_count": parsed["counts"]["unicode"]}
