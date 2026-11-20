# backend/security_ops/pe.py
# Deep PE/COFF parsing, anomaly detection, imports/exports, resources,
# packer identification and compile-time artifacts. Uses pefile when
# available and falls back to a self-contained parser otherwise.

from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import math
import struct
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .knowledge import API_RISK, PACKERS, SUSPICIOUS_IMPORT_COMBOS
from .util import entropy, extract_strings, file_type, hash_bytes

try:
    import pefile  # type: ignore
except Exception:  # pragma: no cover
    pefile = None

STANDARD_SECTIONS = {".text", ".data", ".rdata", ".rsrc", ".reloc", ".bss",
                     ".idata", ".edata", ".tls", ".didat", ".pdata", ".xdata",
                     ".debug", ".crt", ".gfids", ".00cfg"}

SECTION_CHARS = {
    0x00000020: "CNT_CODE", 0x00000040: "CNT_INITIALIZED_DATA",
    0x00000080: "CNT_UNINITIALIZED_DATA", 0x02000000: "MEM_DISCARDABLE",
    0x04000000: "MEM_NOT_CACHED", 0x08000000: "MEM_NOT_PAGED",
    0x10000000: "MEM_SHARED", 0x20000000: "MEM_EXECUTE",
    0x40000000: "MEM_READ", 0x80000000: "MEM_WRITE",
}

DLL_CHARS = {
    0x0020: "HIGH_ENTROPY_VA", 0x0040: "DYNAMIC_BASE", 0x0080: "FORCE_INTEGRITY",
    0x0100: "NX_COMPAT", 0x0200: "NO_ISOLATION", 0x0400: "NO_SEH",
    0x0800: "NO_BIND", 0x1000: "APPCONTAINER", 0x2000: "WDM_DRIVER",
    0x4000: "GUARD_CF", 0x8000: "TERMINAL_SERVER_AWARE",
}


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def _flags(value: int, table: Dict[int, str]) -> List[str]:
    return [name for bit, name in table.items() if value & bit]


def _ts(value: int) -> Dict[str, Any]:
    if not value:
        return {"raw": 0, "iso": "", "anomaly": "zero timestamp"}
    try:
        d = _dt.datetime.fromtimestamp(value, tz=_dt.timezone.utc)
        now = _dt.datetime.now(_dt.timezone.utc)
        anomaly = ""
        if d > now + _dt.timedelta(days=1):
            anomaly = "timestamp in the future"
        elif d.year < 1990:
            anomaly = "timestamp before 1990"
        return {"raw": value, "iso": d.strftime("%Y-%m-%d %H:%M:%S UTC"), "anomaly": anomaly}
    except Exception:
        return {"raw": value, "iso": "invalid", "anomaly": "unrepresentable"}


def _rva_to_off(rva: int, sections: List[Dict[str, Any]], size: int = 1) -> Optional[int]:
    for s in sections:
        va = s.get("virtual_address", 0)
        vs = s.get("virtual_size", 0) or s.get("raw_size", 0)
        if va <= rva < va + max(vs, s.get("raw_size", 0)):
            delta = rva - va
            if delta < s.get("raw_size", 0) or s.get("raw_size", 0) == 0:
                return s.get("raw_pointer", 0) + delta
    return rva if 0 <= rva < size else None


def _pe_checksum(data: bytes) -> int:
    if len(data) < 0x40:
        return 0
    off = struct.unpack_from("<I", data, 0x3C)[0]
    csum_off = off + 24 + 64
    if csum_off + 4 > len(data):
        return 0
    total = 0
    buf = bytearray(data)
    buf[csum_off:csum_off + 4] = b"\x00\x00\x00\x00"
    if len(buf) % 2:
        buf.append(0)
    for i in range(0, len(buf), 2):
        total += struct.unpack_from("<H", buf, i)[0]
        total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return (total + len(data)) & 0xFFFFFFFF


# --------------------------------------------------------------------------- #
#  Public entry
# --------------------------------------------------------------------------- #
def analyze(data: bytes, filename: str = "", extract: bool = False) -> Dict[str, Any]:
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("not a PE file (missing MZ)")
    result: Dict[str, Any]
    try:
        result = _analyze_pefile(data, filename, extract)
        result["parser"] = "pefile"
    except Exception as exc:
        result = _analyze_manual(data, filename)
        result["parser"] = "manual"
        result.setdefault("parser_notes", []).append(f"pefile failed: {type(exc).__name__}: {exc}")
    result["hashes"] = hash_bytes(data)
    result["type"] = file_type(data, filename)
    result["flags"] = _verdict(result)
    result["score"] = _score(result)
    result["verdict"] = _verdict_label(result["score"])
    return result


# --------------------------------------------------------------------------- #
#  pefile-backed parser
# --------------------------------------------------------------------------- #
def _analyze_pefile(data: bytes, filename: str, extract: bool) -> Dict[str, Any]:
    pe = pefile.PE(data=data, fast_load=False)
    fh = pe.FILE_HEADER
    oh = pe.OPTIONAL_HEADER
    sections: List[Dict[str, Any]] = []
    for s in pe.sections:
        raw = s.Name.rstrip(b"\x00").decode("latin-1", "replace")
        ent = round(s.get_entropy(), 3)
        sections.append({
            "name": raw,
            "virtual_address": int(s.VirtualAddress),
            "virtual_size": int(s.Misc_VirtualSize),
            "raw_pointer": int(s.PointerToRawData),
            "raw_size": int(s.SizeOfRawData),
            "characteristics": int(s.Characteristics),
            "flags": _flags(int(s.Characteristics), SECTION_CHARS),
            "entropy": ent,
            "md5": s.get_hash_md5() if hasattr(s, "get_hash_md5") else "",
            "sha256": hashlib.sha256(s.get_data()).hexdigest() if s.SizeOfRawData else "",
        })

    imports: Dict[str, List[Dict[str, Any]]] = {}
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            dll = entry.dll.decode("latin-1", "replace")
            funcs = []
            for imp in entry.imports:
                name = imp.name.decode("latin-1", "replace") if imp.name else f"ordinal_{imp.ordinal}"
                funcs.append({"name": name, "address": int(imp.address or 0),
                              "ordinal": imp.ordinal})
            imports[dll] = funcs
    delay_imports: Dict[str, List[Dict[str, Any]]] = {}
    if hasattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT"):
        for entry in pe.DIRECTORY_ENTRY_DELAY_IMPORT:
            dll = entry.dll.decode("latin-1", "replace")
            delay_imports[dll] = [
                {"name": (i.name.decode("latin-1", "replace") if i.name else f"ordinal_{i.ordinal}"),
                 "address": int(i.address or 0), "ordinal": i.ordinal}
                for i in entry.imports
            ]

    exports: List[Dict[str, Any]] = []
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT") and pe.DIRECTORY_ENTRY_EXPORT:
        for sym in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            exports.append({"name": sym.name.decode("latin-1", "replace") if sym.name else "",
                            "ordinal": sym.ordinal, "address": int(sym.address or 0),
                            "forwarder": sym.forwarder.decode("latin-1", "replace") if sym.forwarder else ""})

    resources, embedded = _resources_pefile(pe, extract)
    debug = []
    if hasattr(pe, "DIRECTORY_ENTRY_DEBUG"):
        for dbg in pe.DIRECTORY_ENTRY_DEBUG:
            item = {"type": dbg.struct.Type, "size": dbg.struct.SizeOfData,
                    "timestamp": _ts(int(dbg.struct.TimeDateStamp))}
            if dbg.struct.Type == 2:
                try:
                    raw = data[dbg.struct.PointerToRawData:
                               dbg.struct.PointerToRawData + dbg.struct.SizeOfData]
                    item["pdb"] = raw.split(b"\x00", 1)[0].decode("latin-1", "replace")
                except Exception:
                    item["pdb"] = ""
            debug.append(item)

    tls_callbacks = []
    if hasattr(pe, "DIRECTORY_ENTRY_TLS") and pe.DIRECTORY_ENTRY_TLS:
        try:
            tls_callbacks = [int(x) for x in pe.DIRECTORY_ENTRY_TLS.struct.AddressOfCallBacks]
        except Exception:
            tls_callbacks = ["present"]

    version_info = {}
    if hasattr(pe, "FileInfo"):
        for fileinfo_list in pe.FileInfo:
            for entry in fileinfo_list:
                if hasattr(entry, "StringTable"):
                    for st in entry.StringTable:
                        for k, v in st.entries.items():
                            version_info[k.decode("latin-1", "replace")] = v.decode("latin-1", "replace")

    overlay = b""
    overlay_off = 0
    try:
        overlay_off = int(pe.get_overlay_data_start_offset() or 0)
        if overlay_off:
            overlay = data[overlay_off:]
    except Exception:
        pass

    signer = _signature_info(pe, data)
    rich = _rich_header(data)
    section_names = [s["name"] for s in sections]
    import_list = sorted({f["name"] for funcs in imports.values() for f in funcs})

    result: Dict[str, Any] = {
        "filename": filename,
        "size": len(data),
        "file_header": {
            "machine": hex(int(fh.Machine)),
            "machine_name": _machine_name(int(fh.Machine)),
            "number_of_sections": int(fh.NumberOfSections),
            "timestamp": _ts(int(fh.TimeDateStamp)),
            "characteristics": hex(int(fh.Characteristics)),
            "characteristics_flags": _pe_characteristics(int(fh.Characteristics)),
            "optional_header_size": int(fh.SizeOfOptionalHeader),
        },
        "optional_header": {
            "magic": hex(int(oh.Magic)),
            "format": "PE32+" if int(oh.Magic) == 0x20B else "PE32",
            "linker": f"{oh.MajorLinkerVersion}.{oh.MinorLinkerVersion}",
            "os_version": f"{oh.MajorOperatingSystemVersion}.{oh.MinorOperatingSystemVersion}",
            "subsystem_version": f"{oh.MajorSubsystemVersion}.{oh.MinorSubsystemVersion}",
            "image_base": hex(int(oh.ImageBase)),
            "entry_point_rva": hex(int(oh.AddressOfEntryPoint)),
            "size_of_image": int(oh.SizeOfImage),
            "size_of_headers": int(oh.SizeOfHeaders),
            "checksum": int(oh.CheckSum),
            "computed_checksum": _pe_checksum(data),
            "subsystem": int(oh.Subsystem),
            "subsystem_name": _subsystem_name(int(oh.Subsystem)),
            "dll_characteristics": hex(int(oh.DllCharacteristics)),
            "mitigations": _flags(int(oh.DllCharacteristics), DLL_CHARS),
            "stack_reserve": int(oh.SizeOfStackReserve),
            "heap_reserve": int(oh.SizeOfHeapReserve),
        },
        "sections": sections,
        "imports": imports,
        "delay_imports": delay_imports,
        "import_count": sum(len(v) for v in imports.values()),
        "import_dll_count": len(imports),
        "import_list": import_list,
        "imphash": pe.get_imphash() if hasattr(pe, "get_imphash") else "",
        "exports": exports,
        "resources": resources,
        "embedded_in_resources": embedded,
        "debug": debug,
        "pdb_path": next((d.get("pdb") for d in debug if d.get("pdb")), ""),
        "tls_callbacks": tls_callbacks,
        "version_info": version_info,
        "overlay": {"offset": overlay_off, "size": len(overlay),
                    "entropy": round(entropy(overlay), 3) if overlay else 0.0,
                    "ratio": round(len(overlay) / len(data), 4) if data else 0.0,
                    "preview_hex": overlay[:32].hex() if overlay else ""},
        "signature": signer,
        "rich_header": rich,
        "section_names": section_names,
        "strings": _interesting_strings(data),
        "packer": identify_packer(data, sections, import_list, result),
        "imports_analysis": analyze_imports(imports),
    }
    result["anomalies"] = _anomalies(result, data)
    result["compile_artifacts"] = compile_artifacts(result)
    result["mitre"] = _pe_mitre(result)
    return result


# --------------------------------------------------------------------------- #
#  Manual parser fallback
# --------------------------------------------------------------------------- #
def _analyze_manual(data: bytes, filename: str) -> Dict[str, Any]:
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_off:pe_off + 4] != b"PE\x00\x00":
        raise ValueError("invalid PE signature")
    machine, nsect, ts, _, _, opt_size, chars = struct.unpack_from("<HHIIIHH", data, pe_off + 4)
    opt = pe_off + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    bits = 64 if magic == 0x20B else 32
    ep = struct.unpack_from("<I", data, opt + 16)[0]
    image_base = struct.unpack_from("<Q", data, opt + 24)[0] if bits == 64 else struct.unpack_from("<I", data, opt + 28)[0]
    subsystem = struct.unpack_from("<H", data, opt + 68)[0]
    dllchars = struct.unpack_from("<H", data, opt + 70)[0]
    checksum = struct.unpack_from("<I", data, opt + 64)[0]
    size_image = struct.unpack_from("<I", data, opt + 56)[0]
    size_headers = struct.unpack_from("<I", data, opt + 60)[0]
    ndirs = struct.unpack_from("<I", data, opt + (108 if bits == 64 else 92))[0]
    dirs_off = opt + (112 if bits == 64 else 96)
    dirs = []
    for i in range(min(int(ndirs), 16)):
        if dirs_off + i * 8 + 8 > len(data):
            break
        va, sz = struct.unpack_from("<II", data, dirs_off + i * 8)
        dirs.append({"index": i, "virtual_address": va, "size": sz})
    sec_off = opt + opt_size
    sections = []
    for i in range(int(nsect)):
        off = sec_off + i * 40
        if off + 40 > len(data):
            break
        name = data[off:off + 8].rstrip(b"\x00").decode("latin-1", "replace")
        vs, va, rs, rp = struct.unpack_from("<IIII", data, off + 8)
        sc = struct.unpack_from("<I", data, off + 36)[0]
        body = data[rp:rp + rs] if rs else b""
        sections.append({
            "name": name, "virtual_address": va, "virtual_size": vs,
            "raw_pointer": rp, "raw_size": rs, "characteristics": sc,
            "flags": _flags(sc, SECTION_CHARS), "entropy": round(entropy(body), 3),
            "md5": hashlib.md5(body).hexdigest() if body else "",
            "sha256": hashlib.sha256(body).hexdigest() if body else "",
        })
    imports = _imports_manual(data, dirs, sections)
    exports = _exports_manual(data, dirs, sections)
    resources, embedded = _resources_manual(data, dirs, sections)
    overlay_off = max((s["raw_pointer"] + s["raw_size"] for s in sections), default=0)
    overlay = data[overlay_off:] if overlay_off < len(data) else b""
    import_list = sorted({f["name"] for funcs in imports.values() for f in funcs})
    result: Dict[str, Any] = {
        "filename": filename, "size": len(data),
        "file_header": {"machine": hex(machine), "machine_name": _machine_name(machine),
                        "number_of_sections": nsect, "timestamp": _ts(ts),
                        "characteristics": hex(chars),
                        "characteristics_flags": _pe_characteristics(chars)},
        "optional_header": {"magic": hex(magic), "format": "PE32+" if bits == 64 else "PE32",
                            "linker": f"{data[opt+2]}.{data[opt+3]}",
                            "image_base": hex(image_base), "entry_point_rva": hex(ep),
                            "size_of_image": size_image, "size_of_headers": size_headers,
                            "checksum": checksum, "computed_checksum": _pe_checksum(data),
                            "subsystem": subsystem, "subsystem_name": _subsystem_name(subsystem),
                            "dll_characteristics": hex(dllchars),
                            "mitigations": _flags(dllchars, DLL_CHARS)},
        "sections": sections, "section_names": [s["name"] for s in sections],
        "imports": imports, "delay_imports": {}, "import_count": len(import_list),
        "import_dll_count": len(imports), "import_list": import_list,
        "imphash": _imphash_manual(imports), "exports": exports,
        "resources": resources, "embedded_in_resources": embedded,
        "debug": [], "pdb_path": "", "tls_callbacks": [],
        "version_info": {},
        "overlay": {"offset": overlay_off, "size": len(overlay),
                    "entropy": round(entropy(overlay), 3) if overlay else 0.0,
                    "ratio": round(len(overlay) / len(data), 4) if data else 0.0,
                    "preview_hex": overlay[:32].hex() if overlay else ""},
        "signature": {"present": bool(dirs[4]["size"]) if len(dirs) > 4 else False,
                      "verified": False, "note": "manual parser: chain not validated"},
        "rich_header": _rich_header(data),
        "strings": _interesting_strings(data),
        "packer": identify_packer(data, sections, import_list, {}),
        "imports_analysis": analyze_imports(imports),
    }
    result["anomalies"] = _anomalies(result, data)
    result["compile_artifacts"] = compile_artifacts(result)
    result["mitre"] = _pe_mitre(result)
    return result


def _imports_manual(data: bytes, dirs: List[Dict[str, Any]],
                    sections: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    if len(dirs) < 2 or not dirs[1]["virtual_address"]:
        return out
    imp_rva = dirs[1]["virtual_address"]
    off = _rva_to_off(imp_rva, sections, len(data))
    if off is None:
        return out
    for i in range(512):
        pos = off + i * 20
        if pos + 20 > len(data):
            break
        oft, ts, fwd, name_rva, ft = struct.unpack_from("<IIIII", data, pos)
        if not name_rva:
            break
        n_off = _rva_to_off(name_rva, sections, len(data))
        if n_off is None:
            break
        dll = data[n_off:data.find(b"\x00", n_off) if b"\x00" in data[n_off:n_off + 256] else n_off + 64]
        dll = dll.decode("latin-1", "replace")
        thunk_rva = oft or ft
        t_off = _rva_to_off(thunk_rva, sections, len(data))
        funcs = []
        if t_off is not None:
            step = 8 if any(s["virtual_address"] <= thunk_rva < s["virtual_address"] + max(s["virtual_size"], 1) and s.get("characteristics", 0) & 0x20 for s in []) else 4
            # determine width from optional header magic via image base heuristic
            step = 8 if _is_pe64(data) else 4
            for j in range(512):
                p = t_off + j * step
                if p + step > len(data):
                    break
                val = struct.unpack_from("<Q" if step == 8 else "<I", data, p)[0]
                if not val:
                    break
                ordinal_flag = (1 << 63) if step == 8 else (1 << 31)
                if val & ordinal_flag:
                    funcs.append({"name": f"ordinal_{val & 0xFFFF}", "ordinal": val & 0xFFFF,
                                  "address": 0})
                else:
                    h_off = _rva_to_off(val & 0x7FFFFFFF, sections, len(data))
                    if h_off is None or h_off + 2 > len(data):
                        continue
                    end = data.find(b"\x00", h_off + 2)
                    name = data[h_off + 2:end if end > 0 else h_off + 66].decode("latin-1", "replace")
                    funcs.append({"name": name, "ordinal": 0, "address": 0})
        out[dll] = funcs
    return out


def _is_pe64(data: bytes) -> bool:
    try:
        off = struct.unpack_from("<I", data, 0x3C)[0]
        return struct.unpack_from("<H", data, off + 24)[0] == 0x20B
    except Exception:
        return False


def _exports_manual(data: bytes, dirs: List[Dict[str, Any]],
                    sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not dirs or not dirs[0]["virtual_address"]:
        return []
    off = _rva_to_off(dirs[0]["virtual_address"], sections, len(data))
    if off is None or off + 40 > len(data):
        return []
    (_, _, _, _, name_rva, base, nfuncs, nnames, addr_funcs, addr_names,
     addr_ords) = struct.unpack_from("<IIHHIIIIIII", data, off)
    out = []
    a_off = _rva_to_off(addr_funcs, sections, len(data))
    n_off = _rva_to_off(addr_names, sections, len(data))
    o_off = _rva_to_off(addr_ords, sections, len(data))
    if a_off is not None and n_off is not None and o_off is not None:
        for i in range(min(nnames, 4096)):
            try:
                nr = struct.unpack_from("<I", data, n_off + i * 4)[0]
                s_off = _rva_to_off(nr, sections, len(data))
                end = data.find(b"\x00", s_off) if s_off is not None else -1
                name = data[s_off:end].decode("latin-1", "replace") if s_off and end > 0 else ""
                ordinal = struct.unpack_from("<H", data, o_off + i * 2)[0]
                func_rva = struct.unpack_from("<I", data, a_off + ordinal * 4)[0]
                out.append({"name": name, "ordinal": base + ordinal, "address": func_rva,
                            "forwarder": ""})
            except Exception:
                continue
    return out


def _resources_manual(data: bytes, dirs: List[Dict[str, Any]],
                      sections: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if len(dirs) < 3 or not dirs[2]["virtual_address"]:
        return [], []
    base_rva = dirs[2]["virtual_address"]
    base_off = _rva_to_off(base_rva, sections, len(data))
    if base_off is None:
        return [], []
    out: List[Dict[str, Any]] = []
    embedded: List[Dict[str, Any]] = []

    def walk(off: int, depth: int, path: List[str]) -> None:
        if depth > 4 or off + 16 > len(data):
            return
        named, ids = struct.unpack_from("<HH", data, off + 12)
        count = named + ids
        for i in range(min(count, 512)):
            ent = off + 16 + i * 8
            if ent + 8 > len(data):
                return
            name_id, data_rva = struct.unpack_from("<II", data, ent)
            if name_id & 0x80000000:
                noff = base_off + (name_id & 0x7FFFFFFF)
                if noff + 2 <= len(data):
                    ln = struct.unpack_from("<H", data, noff)[0]
                    label = data[noff + 2:noff + 2 + min(ln, 128)].decode("utf-16le", "replace")
                else:
                    label = "?"
            else:
                label = str(name_id)
            if data_rva & 0x80000000:
                walk(base_off + (data_rva & 0x7FFFFFFF), depth + 1, path + [label])
            else:
                leaf = base_off + data_rva
                if leaf + 16 > len(data):
                    continue
                rva, size, cp, _ = struct.unpack_from("<IIII", data, leaf)
                d_off = _rva_to_off(rva, sections, len(data))
                blob = data[d_off:d_off + size] if d_off is not None else b""
                item = {"path": path + [label], "type": _res_type(path[0] if path else ""),
                        "size": size, "rva": rva, "codepage": cp,
                        "entropy": round(entropy(blob), 3),
                        "sha256": hashlib.sha256(blob).hexdigest(),
                        "preview_hex": blob[:24].hex()}
                out.append(item)
                marker = _embedded_marker(blob)
                if marker:
                    embedded.append({"path": "/".join(item["path"]), "kind": marker,
                                     "size": size, "sha256": item["sha256"]})

    walk(base_off, 0, [])
    return out, embedded


# --------------------------------------------------------------------------- #
#  Shared analysis
# --------------------------------------------------------------------------- #
def _resources_pefile(pe: Any, extract: bool) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    out: List[Dict[str, Any]] = []
    embedded: List[Dict[str, Any]] = []
    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        return out, embedded

    def walk(entries: Any, path: List[str]) -> None:
        for entry in entries:
            label = (entry.name.string.decode("utf-8", "replace")
                     if getattr(entry, "name", None) and entry.name.string
                     else str(entry.id))
            if hasattr(entry, "directory"):
                walk(entry.directory.entries, path + [label])
            elif hasattr(entry, "data"):
                st = entry.data.struct
                blob = b""
                try:
                    blob = pe.get_data(st.OffsetToData, st.Size)
                except Exception:
                    pass
                item = {"path": path + [label], "type": _res_type(path[0] if path else ""),
                        "size": int(st.Size), "rva": int(st.OffsetToData),
                        "codepage": int(st.CodePage),
                        "entropy": round(entropy(blob), 3),
                        "sha256": hashlib.sha256(blob).hexdigest(),
                        "preview_hex": blob[:24].hex()}
                if extract and blob:
                    try:
                        from .util import write_artifact
                        fn = "resource_" + "_".join(path + [label]).replace("/", "_")[:100] + ".bin"
                        item["extracted_to"] = write_artifact(fn, blob, kind="extracts")
                    except Exception:
                        pass
                out.append(item)
                marker = _embedded_marker(blob)
                if marker:
                    embedded.append({"path": "/".join(item["path"]), "kind": marker,
                                     "size": item["size"], "sha256": item["sha256"]})
    walk(pe.DIRECTORY_ENTRY_RESOURCE.entries, [])
    return out, embedded


def _res_type(label: str) -> str:
    return {"1": "CURSOR", "2": "BITMAP", "3": "ICON", "4": "MENU", "5": "DIALOG",
            "6": "STRING", "9": "ACCELERATOR", "10": "RCDATA", "11": "MESSAGETABLE",
            "12": "GROUP_CURSOR", "14": "GROUP_ICON", "16": "VERSION",
            "17": "DLGINCLUDE", "19": "PLUGPLAY", "20": "VXD", "21": "ANICURSOR",
            "22": "ANIICON", "23": "HTML", "24": "MANIFEST"}.get(str(label), "UNKNOWN")


def _embedded_marker(blob: bytes) -> str:
    if len(blob) < 8:
        return ""
    if blob[:2] == b"MZ":
        return "PE executable"
    if blob[:4] == b"\x7fELF":
        return "ELF executable"
    if blob[:4] == b"PK\x03\x04":
        return "ZIP archive"
    if blob[:4] == b"%PDF":
        return "PDF document"
    if blob[:5] in (b"#!/bi", b"#!/us", b"#!/en"):
        return "shell script"
    head = blob[:512].lower()
    if b"powershell" in head or b"invoke-expression" in head:
        return "PowerShell script"
    if b"createobject" in head or b"wscript.shell" in head:
        return "VBScript/JScript"
    if b"<html" in head or b"<script" in head:
        return "HTML/JS"
    if b"mscdb" in head:
        return "MSI database"
    if entropy(blob) > 7.5 and len(blob) > 4096:
        return "encrypted/compressed blob"
    return ""


def _signature_info(pe: Any, data: bytes) -> Dict[str, Any]:
    info: Dict[str, Any] = {"present": False, "verified": False, "signers": []}
    try:
        d = pe.OPTIONAL_HEADER.DATA_DIRECTORY[4]
        if not d.Size or not d.VirtualAddress:
            return info
        info["present"] = True
        info["offset"] = int(d.VirtualAddress)
        info["size"] = int(d.Size)
        blob = data[d.VirtualAddress:d.VirtualAddress + d.Size]
        if len(blob) > 8:
            try:
                from cryptography.hazmat.primitives.serialization import pkcs7
                certs = pkcs7.load_der_pkcs7_certificates(blob[8:])
                info["verified"] = bool(certs)
                for c in certs[:5]:
                    info["signers"].append({
                        "subject": c.subject.rfc4514_string(),
                        "issuer": c.issuer.rfc4514_string(),
                        "serial": hex(c.serial_number),
                        "not_before": c.not_valid_before_utc.isoformat() if hasattr(c, "not_valid_before_utc") else str(c.not_valid_before),
                        "not_after": c.not_valid_after_utc.isoformat() if hasattr(c, "not_valid_after_utc") else str(c.not_valid_after),
                        "sha256": c.fingerprint(__import__("cryptography").hazmat.primitives.hashes.SHA256()).hex(),
                    })
            except Exception as exc:
                info["note"] = f"could not parse PKCS#7: {type(exc).__name__}"
        # heuristic: certificate table should be 8-byte aligned and inside file
        if d.VirtualAddress + d.Size > len(data):
            info["note"] = "signature table extends past EOF"
    except Exception as exc:
        info["note"] = str(exc)
    return info


def _rich_header(data: bytes) -> Dict[str, Any]:
    idx = data.rfind(b"Rich")
    if idx < 0:
        return {"present": False}
    if idx + 8 > len(data):
        return {"present": True, "entries": [], "note": "truncated"}
    key = struct.unpack_from("<I", data, idx + 4)[0]
    # Locate encoded DanS
    start = None
    probe = idx - 4
    while probe >= 0x40:
        val = struct.unpack_from("<I", data, probe)[0]
        if (val ^ key) == 0x536E6144:  # DanS
            start = probe
            break
        probe -= 4
    entries = []
    if start is not None:
        p = start + 16
        while p + 8 <= idx:
            comp_id, count = struct.unpack_from("<II", data, p)
            entries.append({"comp_id": hex(comp_id ^ key), "count": count ^ key,
                            "product": _rich_product(comp_id ^ key)})
            p += 8
    return {"present": True, "key": hex(key), "entries": entries,
            "toolchain": _rich_toolchain(entries)}


def _rich_product(value: int) -> str:
    prod = (value >> 16) & 0xFFFF
    build = value & 0xFFFF
    names = {0: "Unknown", 1: "Import0", 2: "Linker510", 3: "Cvtomf510",
             4: "Linker600", 5: "Cvtomf600", 6: "Cvtres500", 7: "Utc11_Basic",
             8: "Utc11_C", 9: "Utc12_Basic", 10: "Utc12_C", 11: "Utc12_CPP",
             12: "AliasObj60", 13: "VisualBasic60", 14: "Masm613", 15: "Masm710",
             16: "Linker511", 17: "Cvtomf511", 18: "Masm614", 19: "Linker512",
             20: "Cvtomf512", 21: "Utc12_C_Std", 22: "Utc12_CPP_Std",
             23: "Utc12_C_Book", 24: "Utc12_CPP_Book", 25: "Implib700",
             26: "Cvtomf700", 27: "Utc13_Basic", 28: "Utc13_C", 29: "Utc13_CPP",
             30: "Linker610", 31: "Cvtomf610", 32: "Linker601", 33: "Cvtomf601",
             34: "Utc12_1_Basic", 35: "Utc12_1_C", 36: "Utc12_1_CPP",
             37: "Linker620", 38: "Cvtomf620", 39: "AliasObj70",
             40: "Linker621", 41: "Cvtomf621", 42: "Masm615", 43: "Utc13_LTCG_C",
             44: "Utc13_LTCG_CPP", 45: "Masm620", 46: "ILAsm100", 47: "Utc12_2_Basic",
             48: "Utc12_2_C", 49: "Utc12_2_CPP", 50: "Utc12_2_C_Std",
             51: "Utc12_2_CPP_Std", 52: "Utc12_2_C_Book", 53: "Utc12_2_CPP_Book",
             54: "Implib622", 55: "Cvtomf622", 56: "Cvtres501", 57: "Utc13_C_Std",
             58: "Utc13_CPP_Std", 59: "Cvtpgd1300", 60: "Linker622",
             61: "Linker700", 62: "Export622", 63: "Export700", 64: "Masm700",
             65: "Utc13_POGO_I_C", 66: "Utc13_POGO_I_CPP", 67: "Utc13_POGO_O_C",
             68: "Utc13_POGO_O_CPP", 69: "Cvtres700", 70: "Cvtres710p",
             71: "Linker710p", 72: "Cvtomf710p", 73: "Export710p",
             74: "Implib710p", 75: "Masm710p", 76: "Utc1310p_C",
             77: "Utc1310p_CPP", 78: "Utc1310p_C_Std", 79: "Utc1310p_CPP_Std",
             80: "Utc1310p_LTCG_C", 81: "Utc1310p_LTCG_CPP", 82: "Utc1310p_POGO_I_C",
             83: "Utc1310p_POGO_I_CPP", 84: "Utc1310p_POGO_O_C",
             85: "Utc1310p_POGO_O_CPP", 86: "Linker624", 87: "Cvtomf624",
             88: "Export624", 89: "Implib624", 90: "Linker710", 91: "Cvtomf710",
             92: "Export710", 93: "Implib710", 94: "Cvtres710", 95: "Utc1310_C",
             96: "Utc1310_CPP", 97: "Utc1310_C_Std", 98: "Utc1310_CPP_Std",
             99: "Utc1310_LTCG_C", 100: "Utc1310_LTCG_CPP", 101: "Utc1310_POGO_I_C",
             102: "Utc1310_POGO_I_CPP", 103: "Utc1310_POGO_O_C",
             104: "Utc1310_POGO_O_CPP", 105: "AliasObj710", 106: "AliasObj710p",
             107: "Cvtpgd1310", 108: "Cvtpgd1310p", 109: "Utc1400_C",
             110: "Utc1400_CPP", 111: "Utc1400_C_Std", 112: "Utc1400_CPP_Std",
             113: "Utc1400_LTCG_C", 114: "Utc1400_LTCG_CPP", 115: "Utc1400_POGO_I_C",
             116: "Utc1400_POGO_I_CPP", 117: "Utc1400_POGO_O_C",
             118: "Utc1400_POGO_O_CPP", 119: "Cvtpgd1400", 120: "Linker800",
             121: "Cvtomf800", 122: "Export800", 123: "Implib800",
             124: "Cvtres800", 125: "Masm800", 126: "AliasObj800",
             127: "PhoenixPrerelease", 128: "Utc1400_CVTCIL_C",
             129: "Utc1400_CVTCIL_CPP", 130: "Utc1400_LTCG_MSIL",
             131: "Utc1500_C", 132: "Utc1500_CPP", 133: "Utc1500_C_Std",
             134: "Utc1500_CPP_Std", 135: "Utc1500_CVTCIL_C",
             136: "Utc1500_CVTCIL_CPP", 137: "Utc1500_LTCG_C",
             138: "Utc1500_LTCG_CPP", 139: "Utc1500_LTCG_MSIL",
             140: "Utc1500_POGO_I_C", 141: "Utc1500_POGO_I_CPP",
             142: "Utc1500_POGO_O_C", 143: "Utc1500_POGO_O_CPP",
             144: "Cvtpgd1500", 145: "Linker900", 146: "Export900",
             147: "Implib900", 148: "Cvtres900", 149: "Masm900",
             150: "AliasObj900", 151: "Resource900", 152: "AliasObj1000",
             153: "Cvtpgd1600", 154: "Cvtres1000", 155: "Export1000",
             156: "Implib1000", 157: "Linker1000", 158: "Masm1000",
             159: "Utc1600_C", 160: "Utc1600_CPP", 161: "Utc1600_CVTCIL_C",
             162: "Utc1600_CVTCIL_CPP", 163: "Utc1600_LTCG_C",
             164: "Utc1600_LTCG_CPP", 165: "Utc1600_LTCG_MSIL",
             166: "Utc1600_POGO_I_C", 167: "Utc1600_POGO_I_CPP",
             168: "Utc1600_POGO_O_C", 169: "Utc1600_POGO_O_CPP",
             170: "Utc1700_C", 171: "Utc1700_CPP", 172: "Utc1700_CVTCIL_C",
             173: "Utc1700_CVTCIL_CPP", 174: "Utc1700_LTCG_C",
             175: "Utc1700_LTCG_CPP", 176: "Utc1700_LTCG_MSIL",
             177: "Utc1700_POGO_I_C", 178: "Utc1700_POGO_I_CPP",
             179: "Utc1700_POGO_O_C", 180: "Utc1700_POGO_O_CPP"}
    return f"{names.get(prod, 'Product' + str(prod))} build {build}"


def _rich_toolchain(entries: List[Dict[str, Any]]) -> str:
    if not entries:
        return "unknown"
    best = max(entries, key=lambda e: e.get("count", 0))
    return best.get("product", "unknown")


def _interesting_strings(data: bytes) -> Dict[str, Any]:
    parsed = extract_strings(data, min_len=5, both=True, unique=True, limit=6000)
    interesting = []
    for s in parsed["ascii"] + parsed["unicode"]:
        low = s.lower()
        if any(k in low for k in (
                "http://", "https://", "\\\\.\\pipe", "\\pipe\\", "cmd.exe",
                "powershell", "rundll32", "regsvr32", "schtasks", "currentversion\\run",
                "virtualalloc", "writeprocessmemory", "createremotethread",
                "lsass", "mimikatz", "bitcoin", "ransom", "decrypt", "encrypt",
                "mutex", "botnet", "c2", "beacon", "steam", "discord", "telegram",
                "api.telegram", "pastebin", "temp\\", "appdata\\", "programdata\\",
                ".onion", "user-agent", "mozilla/", "select ", "insert into",
                "wallet", "clipboard", "keylog", "screenshot", "vssadmin",
                "bcdedit", "wbadmin", "shadowcopy", "wevtutil", "defender",
                "amsi", "etw", "sandbox", "vmware", "virtualbox", "qemu")):
            interesting.append(s)
        if len(interesting) >= 400:
            break
    return {"interesting": list(dict.fromkeys(interesting)),
            "ascii_count": parsed["counts"]["ascii"],
            "unicode_count": parsed["counts"]["unicode"]}


def analyze_imports(imports: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    categories: Counter = Counter()
    techniques: set = set()
    low = {}
    for dll, funcs in imports.items():
        for f in funcs:
            name = f["name"].lower()
            low[name] = dll
            for key, meta in API_RISK.items():
                if key in name:
                    findings.append({"api": f["name"], "dll": dll, **meta})
                    categories[meta["category"]] += 1
                    if meta.get("technique"):
                        techniques.add(meta["technique"])
                    break
    combos = []
    present = set(low)
    for combo in SUSPICIOUS_IMPORT_COMBOS:
        if all(any(api in p for p in present) for api in combo["apis"]):
            combos.append(combo)
    dedup = {}
    for item in findings:
        dedup[(item["api"], item["risk"])] = item
    findings = sorted(dedup.values(), key=lambda x: {"critical": 0, "high": 1,
                                                     "medium": 2, "low": 3}.get(x["risk"], 4))
    return {"total": sum(len(v) for v in imports.values()),
            "risk_counts": dict(categories), "findings": findings[:200],
            "combos": combos, "mitre": sorted(techniques),
            "high_risk": [f for f in findings if f["risk"] in ("critical", "high")][:80]}


def identify_packer(data: bytes, sections: List[Dict[str, Any]],
                    import_list: List[str], result: Dict[str, Any]) -> Dict[str, Any]:
    names = [s["name"].lower() for s in sections]
    text = data[:4096] + data[-4096:]
    low = text.lower()
    matches = []
    for sig in PACKERS:
        score = 0
        evidence = []
        for sec in sig.get("sections", []):
            if sec.lower() in names:
                score += 45
                evidence.append(f"section {sec}")
        for st in sig.get("strings", []):
            if st.lower().encode() in low:
                score += 35
                evidence.append(f"string {st!r}")
        if sig["name"] == "UPX" and b"upx" in data.lower():
            score += 20
            evidence.append("UPX marker")
        if score:
            matches.append({"name": sig["name"], "confidence": min(98, score),
                            "evidence": evidence, "unpack": sig["unpack"]})
    overall = result.get("sections") or sections
    avg_ent = sum(s.get("entropy", 0) for s in overall) / max(1, len(overall))
    high_sections = [s["name"] for s in overall if s.get("entropy", 0) >= 7.2]
    few_imports = len(import_list) <= 8
    if high_sections and few_imports:
        matches.append({"name": "Possible custom packer / crypter",
                        "confidence": min(85, 45 + len(high_sections) * 8),
                        "evidence": [f"high entropy sections: {high_sections}",
                                     f"only {len(import_list)} imports"],
                        "unpack": "Find OEP, dump with Scylla, rebuild IAT"})
    matches.sort(key=lambda m: m["confidence"], reverse=True)
    return {"matches": matches[:6],
            "packed": bool(matches and matches[0]["confidence"] >= 60),
            "average_section_entropy": round(avg_ent, 3),
            "high_entropy_sections": high_sections}


def compile_artifacts(pe: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    fh = pe.get("file_header", {})
    oh = pe.get("optional_header", {})
    ts = fh.get("timestamp", {})
    out["build_time"] = ts.get("iso", "")
    out["timestamp_anomaly"] = ts.get("anomaly", "")
    out["linker"] = oh.get("linker", "")
    out["toolchain"] = (pe.get("rich_header") or {}).get("toolchain", "")
    pdb = pe.get("pdb_path", "")
    out["pdb_path"] = pdb
    if pdb:
        parts = pdb.replace("/", "\\").split("\\")
        out["pdb_user_hint"] = parts[1] if len(parts) > 2 and parts[0].endswith(":") else ""
        out["pdb_project"] = parts[-1] if parts else ""
    out["language"] = _language_hint(pe)
    out["timezone_hint"] = "UTC+3 (Moscow) if build hour 06-14 and targeting CIS" if _looks_cis(pe) else "unknown"
    out["signed"] = bool(pe.get("signature", {}).get("present"))
    out["mitigations"] = oh.get("mitigations", [])
    return out


def _language_hint(pe: Dict[str, Any]) -> str:
    text = " ".join(pe.get("strings", {}).get("interesting", []))
    if any("\u0400" <= ch <= "\u04FF" for ch in text):
        return "Russian (Cyrillic strings present)"
    if any("\u4e00" <= ch <= "\u9fff" for ch in text):
        return "Chinese (CJK strings present)"
    if any("\u0600" <= ch <= "\u06FF" for ch in text):
        return "Arabic (Arabic strings present)"
    if any("\uac00" <= ch <= "\ud7af" for ch in text):
        return "Korean (Hangul strings present)"
    return "English/unknown"


def _looks_cis(pe: Dict[str, Any]) -> bool:
    text = " ".join(pe.get("strings", {}).get("interesting", [])).lower()
    return any(k in text for k in ("\u043f\u0440\u0438\u0432\u0435\u0442", "sberbank", "vk.com", "mail.ru"))


def _pe_mitre(pe: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for item in pe.get("imports_analysis", {}).get("findings", []):
        if item.get("technique"):
            out.append({"id": item["technique"], "evidence": f"import {item['api']}"})
    for combo in pe.get("imports_analysis", {}).get("combos", []):
        out.append({"id": combo["technique"], "evidence": combo["name"]})
    for item in (pe.get("imports_analysis", {}).get("findings", []) or []):
        if "virtuallallo" in item.get("api", "").lower() and item.get("technique"):
            out.append({"id": item["technique"], "evidence": "memory allocation"})
    seen = set()
    dedup = []
    for item in out:
        if item["id"] not in seen:
            seen.add(item["id"])
            dedup.append(item)
    return dedup


def _anomalies(pe: Dict[str, Any], data: bytes) -> List[Dict[str, str]]:
    a: List[Dict[str, str]] = []
    def add(sev: str, msg: str) -> None:
        a.append({"severity": sev, "finding": msg})
    oh = pe.get("optional_header", {})
    fh = pe.get("file_header", {})
    sections = pe.get("sections", [])
    names = [s["name"] for s in sections]
    if len(data) > 0:
        total_raw = sum(s.get("raw_size", 0) for s in sections)
        if total_raw and abs(total_raw - len(data)) > len(data) * 0.35:
            add("medium", f"raw section size ({total_raw}) differs substantially from file size ({len(data)})")
    if fh.get("timestamp", {}).get("anomaly"):
        add("medium", f"PE timestamp anomaly: {fh['timestamp']['anomaly']}")
    if oh.get("checksum") and oh.get("checksum") != oh.get("computed_checksum"):
        add("low", f"PE checksum mismatch (stored 0x{oh.get('checksum',0):08x})")
    if not pe.get("import_count"):
        add("high", "no imports — unusual for a normal executable (packed/shellcode loader)")
    if pe.get("import_count", 0) and pe.get("import_count", 0) < 5:
        add("medium", f"very small import table ({pe.get('import_count')} functions)")
    for s in sections:
        fl = s.get("flags", [])
        if "MEM_WRITE" in fl and "MEM_EXECUTE" in fl:
            add("high", f"section {s['name']} is W+X (write and execute)")
        if s.get("entropy", 0) >= 7.2:
            add("medium", f"section {s['name']} entropy {s['entropy']} (packed/encrypted)")
        if s["name"] and s["name"] not in STANDARD_SECTIONS and not s["name"].startswith("."):
            add("low", f"non-standard section name {s['name']!r}")
        if s.get("raw_size", 0) == 0 and s.get("virtual_size", 0) > 0:
            add("low", f"section {s['name']} has virtual size but zero raw data")
        if s.get("raw_size", 0) > 0 and s.get("raw_pointer", 0) + s.get("raw_size", 0) > len(data):
            add("high", f"section {s['name']} raw data extends past EOF")
    ep = int(str(oh.get("entry_point_rva", "0x0")), 16) if isinstance(oh.get("entry_point_rva"), str) else 0
    if sections and ep:
        inside = [s for s in sections if s["virtual_address"] <= ep < s["virtual_address"] + max(s["virtual_size"], s["raw_size"], 1)]
        if not inside:
            add("high", f"entry point 0x{ep:x} is outside all sections")
        elif inside[0]["name"] not in (".text", ".code", "CODE"):
            add("low", f"entry point is in section {inside[0]['name']}")
        if inside and inside[0] == sections[-1]:
            add("medium", "entry point is in the last section (packer pattern)")
    if (pe.get("overlay") or {}).get("ratio", 0) > 0.25 and (pe.get("overlay") or {}).get("size", 0) > 65536:
        add("medium", f"large overlay ({pe['overlay']['size']} bytes, entropy {pe['overlay']['entropy']})")
    if pe.get("embedded_in_resources"):
        add("high", f"embedded executable/script in resources: {[e['kind'] for e in pe['embedded_in_resources']]}")
    if pe.get("tls_callbacks"):
        add("medium", "TLS callbacks present (run before entry point)")
    if not pe.get("rich_header", {}).get("present"):
        add("low", "no Rich header (non-MSVC toolchain or stripped)")
    if pe.get("pdb_path", "").lower().startswith(("c:\\users\\", "c:\\temp", "/home/", "/tmp/")):
        add("medium", f"PDB path exposes build user/path: {pe['pdb_path']}")
    for combo in pe.get("imports_analysis", {}).get("combos", []):
        add(combo["severity"], f"API combination: {combo['name']} ({', '.join(combo['apis'])})")
    if pe.get("signature", {}).get("present") and not pe.get("signature", {}).get("verified"):
        add("medium", "Authenticode table present but signature could not be validated")
    mit = set(oh.get("mitigations", []))
    if "DYNAMIC_BASE" not in mit:
        add("low", "ASLR not enabled (DYNAMIC_BASE missing)")
    if "NX_COMPAT" not in mit:
        add("low", "DEP/NX not enabled (NX_COMPAT missing)")
    if "GUARD_CF" not in mit:
        add("low", "Control Flow Guard not enabled")
    return sorted(a, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4))


def _verdict(pe: Dict[str, Any]) -> List[str]:
    flags = []
    if pe.get("packer", {}).get("packed"):
        flags.append("packed")
    if pe.get("imports_analysis", {}).get("high_risk"):
        flags.append("high-risk imports")
    if any(a["severity"] == "critical" for a in pe.get("anomalies", [])):
        flags.append("critical anomalies")
    if pe.get("embedded_in_resources"):
        flags.append("embedded payload")
    if pe.get("overlay", {}).get("entropy", 0) > 7.2:
        flags.append("encrypted overlay")
    if not pe.get("signature", {}).get("present"):
        flags.append("unsigned")
    return flags


def _score(pe: Dict[str, Any]) -> int:
    score = 0
    for a in pe.get("anomalies", []):
        score += {"critical": 25, "high": 15, "medium": 7, "low": 3}.get(a["severity"], 0)
    if pe.get("packer", {}).get("packed"):
        score += 15
    score += min(20, len(pe.get("imports_analysis", {}).get("high_risk", [])) * 3)
    if pe.get("embedded_in_resources"):
        score += 20
    return min(100, score)


def _verdict_label(score: int) -> str:
    if score >= 70:
        return "highly suspicious"
    if score >= 40:
        return "suspicious"
    if score >= 15:
        return "needs review"
    return "low risk"


def _machine_name(machine: int) -> str:
    return {0x14C: "x86", 0x8664: "x86-64", 0x1C0: "ARM", 0x1C4: "ARMv7",
            0xAA64: "ARM64", 0x200: "IA-64", 0x5032: "RISC-V 32",
            0x5064: "RISC-V 64"}.get(machine, f"unknown (0x{machine:04x})")


def _subsystem_name(sub: int) -> str:
    return {1: "NATIVE", 2: "WINDOWS_GUI", 3: "WINDOWS_CUI", 5: "OS2_CUI",
            7: "POSIX_CUI", 9: "WINDOWS_CE_GUI", 10: "EFI_APPLICATION",
            11: "EFI_BOOT_SERVICE_DRIVER", 12: "EFI_RUNTIME_DRIVER",
            13: "EFI_ROM", 14: "XBOX", 16: "WINDOWS_BOOT_APPLICATION"}.get(sub, f"unknown ({sub})")


def _pe_characteristics(value: int) -> List[str]:
    table = {0x0001: "RELOCS_STRIPPED", 0x0002: "EXECUTABLE_IMAGE",
             0x0004: "LINE_NUMS_STRIPPED", 0x0008: "LOCAL_SYMS_STRIPPED",
             0x0010: "AGGRESSIVE_WS_TRIM", 0x0020: "LARGE_ADDRESS_AWARE",
             0x0080: "BYTES_REVERSED_LO", 0x0100: "32BIT_MACHINE",
             0x0200: "DEBUG_STRIPPED", 0x0400: "REMOVABLE_RUN_FROM_SWAP",
             0x0800: "NET_RUN_FROM_SWAP", 0x1000: "SYSTEM", 0x2000: "DLL",
             0x4000: "UP_SYSTEM_ONLY", 0x8000: "BYTES_REVERSED_HI"}
    return [name for bit, name in table.items() if value & bit]


def _imphash_manual(imports: Dict[str, List[Dict[str, Any]]]) -> str:
    parts = []
    for dll in sorted(imports):
        base = dll.lower()
        for ext in (".dll", ".ocx", ".sys"):
            if base.endswith(ext):
                base = base[:-4]
                break
        for f in imports[dll]:
            name = f["name"].lower()
            if name.startswith("ordinal_"):
                name = f"ord{name.split('_')[1]}"
            parts.append(f"{base}.{name}")
    return hashlib.md5(",".join(parts).encode()).hexdigest()
