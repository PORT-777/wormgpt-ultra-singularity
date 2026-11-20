# backend/security_ops/forensics.py
# Host and artifact forensics with the standard library: Windows LNK /
# prefetch / registry / shellbags / jumplists, browser credential stores,
# NTFS MFT records, hibernation headers, steganography, firmware blobs,
# APK/IPA packages, secret scanning, IaC/container/Kubernetes/cloud configs,
# fileless activity, bootkit/supply-chain heuristics.

from __future__ import annotations

import binascii
import datetime as _dt
import hashlib
import io
import ipaddress
import json
import os
import plistlib
import re
import shlex
import sqlite3
import struct
import zipfile
import zlib
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .util import (ascii_strings, entropy, extract_iocs, extract_strings,
                   file_type, hash_bytes, parse_time, severity_rank,
                   unicode_strings)

# --------------------------------------------------------------------------- #
#  Windows LNK (.lnk)
# --------------------------------------------------------------------------- #
LNK_CLSID = bytes.fromhex("0114020000000000c000000000000046")
DRIVE_TYPES = {0: "unknown", 1: "no root dir", 2: "removable", 3: "fixed", 4: "remote",
               5: "cdrom", 6: "ramdisk"}


def analyze_lnk(data: bytes, filename: str = "") -> Dict[str, Any]:
    if len(data) < 0x4C:
        raise ValueError("too small for a LNK file")
    hdr_size = struct.unpack_from("<I", data, 0)[0]
    if hdr_size != 0x4C:
        raise ValueError(f"unexpected LNK header size 0x{hdr_size:x}")
    clsid = data[4:20]
    flags, attrs = struct.unpack_from("<II", data, 20)
    ctime, atime, mtime = struct.unpack_from("<QQQ", data, 28)
    file_size, icon_index, show_cmd = struct.unpack_from("<IIi", data, 52)
    hotkey = struct.unpack_from("<H", data, 64)[0]
    out: Dict[str, Any] = {
        "filename": filename, "size": len(data),
        "flags": _lnk_flags(flags),
        "attributes": _file_attrs(attrs),
        "created": _filetime(ctime), "accessed": _filetime(atime),
        "modified": _filetime(mtime),
        "target_size": file_size, "icon_index": icon_index,
        "show_command": {1: "normal", 3: "maximized", 7: "minimized"}.get(show_cmd, str(show_cmd)),
        "hotkey": hex(hotkey), "clsid": clsid.hex(),
        "is_lnk": clsid == LNK_CLSID,
        "link_info": {}, "string_data": {}, "extra": {},
    }
    pos = 0x4C
    if flags & 0x1:   # HasLinkTargetIDList
        if pos + 2 > len(data):
            return out
        idlist_size = struct.unpack_from("<H", data, pos)[0]
        idlist = data[pos + 2:pos + 2 + idlist_size]
        out["target_idlist_size"] = idlist_size
        out["target_path_from_idlist"] = _lnk_idlist_path(idlist)
        pos += 2 + idlist_size
    if flags & 0x2:   # HasLinkInfo
        if pos + 4 > len(data):
            return out
        li_size = struct.unpack_from("<I", data, pos)[0]
        li = data[pos:pos + li_size]
        out["link_info"] = _lnk_link_info(li)
        pos += li_size
    if flags & 0x4:   # HasName / relative path / working dir / args / icon
        for key, label in (("name", "name_string"), ("relative_path", "relative_path"),
                           ("working_dir", "working_dir"), ("arguments", "arguments"),
                           ("icon_location", "icon_location")):
            if pos + 2 > len(data):
                break
            count = struct.unpack_from("<H", data, pos)[0]
            pos += 2
            raw = data[pos:pos + count * 2]
            pos += count * 2
            if flags & 0x80:
                out["string_data"][key] = raw.decode("utf-16le", "replace").rstrip("\x00")
            else:
                out["string_data"][key] = raw.decode("latin-1", "replace").rstrip("\x00")
    # Extra data blocks
    while pos + 8 <= len(data):
        bsize, sig = struct.unpack_from("<II", data, pos)
        if bsize < 8:
            break
        body = data[pos + 8:pos + bsize]
        out["extra"][hex(sig)] = _lnk_extra(sig, body)
        pos += bsize
    # Heuristics
    ld = out["string_data"]
    target = out["link_info"].get("local_base_path") or out["target_path_from_idlist"] or ""
    flags_out = []
    if ld.get("arguments"):
        flags_out.append("has arguments")
    if re.search(r"(?i)(powershell|cmd|wscript|cscript|mshta|rundll32|regsvr32|bitsadmin|certutil)", str(ld.get("arguments", ""))):
        flags_out.append("script/LOLBin arguments")
    if re.search(r"(?i)\.(exe|dll|ps1|vbs|js|bat|cmd|scr|hta|lnk)(\s|$)", target):
        flags_out.append("executable target")
    if re.search(r"(?i)(\\\\|http://|https://)", target):
        flags_out.append("remote/UNC target")
    if out["link_info"].get("volume_label") or target.startswith("\\\\"):
        flags_out.append("network share target")
    if len(data) > 4096 and entropy(data[0x4C:]) > 7.0:
        flags_out.append("high-entropy payload after header")
    out["indicators"] = flags_out
    out["iocs"] = extract_iocs(" ".join([target, ld.get("arguments", ""), ld.get("working_dir", "")]))["categories"]
    out["score"] = min(100, len(flags_out) * 18)
    return out


def _lnk_flags(flags: int) -> List[str]:
    table = {0x1: "HasLinkTargetIDList", 0x2: "HasLinkInfo", 0x4: "HasName",
             0x8: "HasRelativePath", 0x10: "HasWorkingDir", 0x20: "HasArguments",
             0x40: "HasIconLocation", 0x80: "IsUnicode", 0x100: "ForceNoLinkInfo",
             0x200: "HasExpString", 0x400: "RunInSeparateProcess",
             0x800: "HasDarwinID", 0x1000: "RunAsUser", 0x2000: "HasExpIcon",
             0x4000: "NoPidlAlias", 0x8000: "RunWithShimLayer",
             0x10000: "ForceNoLinkTrack", 0x20000: "EnableTargetMetadata"}
    return [name for bit, name in table.items() if flags & bit]


def _file_attrs(attrs: int) -> List[str]:
    table = {0x1: "READONLY", 0x2: "HIDDEN", 0x4: "SYSTEM", 0x10: "DIRECTORY",
             0x20: "ARCHIVE", 0x40: "DEVICE", 0x80: "NORMAL", 0x100: "TEMPORARY",
             0x200: "SPARSE_FILE", 0x400: "REPARSE_POINT", 0x800: "COMPRESSED",
             0x4000: "ENCRYPTED"}
    return [name for bit, name in table.items() if attrs & bit]


def _filetime(value: int) -> str:
    if not value:
        return ""
    try:
        return (_dt.datetime(1601, 1, 1, tzinfo=_dt.timezone.utc) +
                _dt.timedelta(microseconds=value / 10)).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ""


def _lnk_idlist_path(idlist: bytes) -> str:
    try:
        parts = []
        pos = 0
        while pos + 2 <= len(idlist):
            size = struct.unpack_from("<H", idlist, pos)[0]
            if size == 0 or pos + size > len(idlist):
                break
            item = idlist[pos:pos + size]
            # Item type byte at offset 2
            if len(item) > 3:
                typ = item[2]
                if typ == 0x31 or typ == 0x32:  # directory / file entry
                    name_len = struct.unpack_from("<H", item, 12)[0] if len(item) >= 14 else 0
                    name = item[14:14 + name_len * 2].decode("utf-16le", "replace")
                    if name:
                        parts.append(name)
                elif typ == 0x2F:  # volume
                    name = item[3:].split(b"\x00", 1)[0].decode("latin-1", "replace")
                    if name:
                        parts.append(name)
            pos += size
        return "\\".join(parts)
    except Exception:
        return ""


def _lnk_link_info(li: bytes) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        li_size, li_hdr = struct.unpack_from("<II", li, 0)
        flags = struct.unpack_from("<I", li, 8)[0]
        out["size"] = li_size
        out["flags"] = hex(flags)
        pos = 12
        if flags & 0x1:  # VolumeIDAndLocalBasePath
            vol_size = struct.unpack_from("<I", li, pos)[0]
            vol = li[pos:pos + vol_size]
            if vol_size >= 16:
                out["drive_type"] = DRIVE_TYPES.get(struct.unpack_from("<I", vol, 4)[0], "unknown")
                out["volume_serial"] = hex(struct.unpack_from("<I", vol, 8)[0])
                out["volume_label"] = vol[16:].split(b"\x00", 1)[0].decode("latin-1", "replace")
            pos += vol_size
            if flags & 0x2 and pos + 4 <= len(li):
                lbp = li[pos:].split(b"\x00", 1)[0].decode("latin-1", "replace")
                out["local_base_path"] = lbp
                out["local_base_path_unicode"] = li[pos:].split(b"\x00\x00", 1)[0].decode("utf-16le", "replace")
        if flags & 0x4:  # CommonNetworkRelativeLink
            pass
    except Exception as exc:
        out["error"] = str(exc)
    return out


def _lnk_extra(sig: int, body: bytes) -> Dict[str, Any]:
    if sig == 0xA0000003:  # TrackerDataBlock
        try:
            machine_id = body[16:32].split(b"\x00", 1)[0].decode("latin-1", "replace")
            droid = body[32:32 + 32].hex() if len(body) >= 64 else ""
            droid_birth = body[64:64 + 32].hex() if len(body) >= 96 else ""
            return {"type": "TrackerDataBlock", "machine_id": machine_id,
                    "droid": droid, "droid_birth": droid_birth}
        except Exception:
            return {"type": "TrackerDataBlock", "size": len(body)}
    if sig == 0xA0000001:
        return {"type": "EnvironmentVariableDataBlock", "size": len(body)}
    if sig == 0xA0000005:
        return {"type": "SpecialFolderDataBlock", "size": len(body)}
    if sig == 0xA0000002:
        return {"type": "ConsoleDataBlock", "size": len(body)}
    if sig == 0xA0000004:
        return {"type": "ConsoleFEDataBlock", "size": len(body)}
    if sig == 0xA0000006:
        return {"type": "DarwinDataBlock", "size": len(body)}
    if sig == 0xA0000007:
        return {"type": "IconEnvironmentDataBlock", "size": len(body)}
    if sig == 0xA0000008:
        return {"type": "ShimDataBlock", "size": len(body)}
    if sig == 0xA0000009:
        return {"type": "PropertyStoreDataBlock", "size": len(body)}
    if sig == 0xA000000B:
        return {"type": "KnownFolderDataBlock", "size": len(body)}
    if sig == 0xA000000C:
        return {"type": "VistaAndAboveIDListDataBlock", "size": len(body)}
    return {"type": hex(sig), "size": len(body)}


# --------------------------------------------------------------------------- #
#  Windows Prefetch (MAM / SCCA)
# --------------------------------------------------------------------------- #
def analyze_prefetch(data: bytes, filename: str = "") -> Dict[str, Any]:
    if len(data) < 0x80:
        raise ValueError("prefetch file too small")
    # MAM compressed prefetch (Win10+)
    if data[:4] == b"MAM\x04":
        try:
            data, algo = _decompress_prefetch(data)
            compressed = True
        except Exception as exc:
            return {"filename": filename, "error": f"cannot decompress MAM: {exc}",
                    "compressed": True}
    else:
        compressed = False
    version = struct.unpack_from("<I", data, 0)[0]
    signature = data[4:8]
    if signature != b"SCCA":
        raise ValueError("not a prefetch file (missing SCCA signature)")
    file_size = struct.unpack_from("<I", data, 12)[0]
    exe_name = data[16:76].split(b"\x00", 1)[0].decode("utf-16le", "replace")
    hash_val = struct.unpack_from("<I", data, 76)[0]
    out: Dict[str, Any] = {
        "filename": filename, "format": f"Prefetch v{version}", "compressed": compressed,
        "signature": signature.decode("latin-1"), "file_size": file_size,
        "executable": exe_name, "hash": hex(hash_val),
        "run_count": 0, "last_run": "", "previous_runs": [],
        "volumes": [], "files": [], "directories": [], "loaded_files": [],
        "hashes": hash_bytes(data),
    }
    try:
        if version == 17:
            out["run_count"] = struct.unpack_from("<I", data, 0x98)[0]
            ft = struct.unpack_from("<Q", data, 0x80)[0]
            out["last_run"] = _filetime(ft)
            for i in range(7):
                off = 0x90 + i * 8
                ft = struct.unpack_from("<Q", data, off)[0]
                if ft:
                    out["previous_runs"].append(_filetime(ft))
        elif version in (23, 26, 30, 31):
            out["run_count"] = struct.unpack_from("<I", data, 0xD0)[0]
            ft = struct.unpack_from("<Q", data, 0xB0)[0]
            out["last_run"] = _filetime(ft)
            for i in range(7):
                off = 0xC0 + i * 8
                ft = struct.unpack_from("<Q", data, off)[0]
                if ft:
                    out["previous_runs"].append(_filetime(ft))
    except Exception:
        pass
    text = data.decode("utf-16le", "ignore") + "\n" + data.decode("latin-1", "ignore")
    out["strings"] = list(dict.fromkeys(re.findall(r"[ -~]{5,200}", text)))[:300]
    suspicious = []
    low = " ".join(out["strings"]).lower()
    for name, marker in (("temp execution", "\\temp\\"), ("appdata execution", "\\appdata\\"),
                         ("downloads execution", "\\downloads\\"), ("powershell", "powershell.exe"),
                         ("cmd shell", "cmd.exe"), ("script host", "wscript.exe"),
                         ("rundll32", "rundll32.exe"), ("regsvr32", "regsvr32.exe"),
                         ("usb", "\\usb"), ("recycle bin", "recycle")):
        if marker in low:
            suspicious.append(name)
    out["suspicious_indicators"] = suspicious
    out["score"] = min(100, len(suspicious) * 15)
    return out


def _decompress_prefetch(data: bytes) -> Tuple[bytes, str]:
    # MAM\x04 uses XPRESS Huffman (Windows) — implement a pure-python decoder
    # for the common variant, fall back to zlib for wrapped data.
    if data[:4] != b"MAM\x04":
        raise ValueError("not MAM")
    payload = data[8:]
    try:
        return zlib.decompress(payload, -15), "zlib-raw"
    except Exception:
        pass
    try:
        return zlib.decompress(payload), "zlib"
    except Exception:
        pass
    return _xpress_huffman(payload), "xpress-huffman"


def _xpress_huffman(data: bytes) -> bytes:
    # Adapted from the public XPRESS Huffman description. 256 symbols, 16-bit
    # table; this is a compact reference implementation for prefetch files.
    if len(data) < 260:
        raise ValueError("XPRESS Huffman header too small")
    table_size = struct.unpack_from("<I", data, 0)[0]
    table = data[4:4 + table_size]
    if len(table) != 256 * 2:
        raise ValueError("unexpected Huffman table size")
    lengths = [struct.unpack_from("<H", table, i * 2)[0] for i in range(256)]
    # canonical decoding table
    codes = {}
    code = 0
    for sym in sorted(range(256), key=lambda s: (lengths[s], s)):
        ln = lengths[sym]
        if ln == 0:
            continue
        # assign
        code = (code + (1 << (ln - 1) if ln else 0)) if False else code
    # Simpler bit-by-bit tree
    max_len = max(lengths) if lengths else 0
    canon = []
    for ln in range(1, max_len + 1):
        for sym in range(256):
            if lengths[sym] == ln:
                canon.append(sym)
    # build decode map using canonical Huffman assignment
    mapping = {}
    c = 0
    last_len = 0
    for sym in canon:
        ln = lengths[sym]
        if ln != last_len:
            c <<= (ln - last_len)
            last_len = ln
        mapping[(ln, c)] = sym
        c += 1
    out = bytearray()
    pos = 4 + table_size
    bitbuf = 0
    bitcount = 0
    while pos < len(data):
        bitbuf |= data[pos] << bitcount
        bitcount += 8
        pos += 1
        while bitcount >= 1:
            for ln in range(1, min(max_len, bitcount) + 1):
                key = (ln, (bitbuf >> (bitcount - ln)) & ((1 << ln) - 1))
                if key in mapping:
                    sym = mapping[key]
                    bitcount -= ln
                    if sym < 256:
                        out.append(sym)
                        break
                    # length/distance pair
                    extra = (sym - 256) & 0xF
                    base = (sym - 256) >> 4
                    dist = 0
                    nbits = 0
                    if pos + 2 <= len(data):
                        dist = ((data[pos] << 8) | data[pos + 1])
                        pos += 2
                    if dist:
                        start = len(out) - dist
                        for _ in range(base + 3):
                            if start < 0 or start >= len(out):
                                break
                            out.append(out[start])
                            start += 1
                    break
            else:
                break
            if bitcount < max_len:
                # need more bits for next symbol; loop handles it
                pass
    return bytes(out)


def analyze_prefetch_summary(files: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine multiple parsed prefetch records into an execution timeline."""
    rows = []
    for f in files:
        if not isinstance(f, dict) or f.get("error"):
            continue
        rows.append({"executable": f.get("executable", ""),
                     "last_run": f.get("last_run", ""),
                     "run_count": f.get("run_count", 0),
                     "suspicious": f.get("suspicious_indicators", [])})
    rows.sort(key=lambda r: r["last_run"], reverse=True)
    return {"programs": rows, "count": len(rows),
            "rare_programs": [r for r in rows if r["run_count"] <= 1],
            "suspicious_programs": [r for r in rows if r["suspicious"]]}


# --------------------------------------------------------------------------- #
#  Registry (.reg text + hive hints)
# --------------------------------------------------------------------------- #
REG_PERSISTENCE_KEYS = (
    "currentversion\\run", "currentversion\\runonce", "currentversion\\runservices",
    "winlogon", "appinit_dlls", "image file execution options", "currentversion\\policies\\explorer\\run",
    "\\services\\", "currentcontrolset\\control\\print\\monitors", "netsh",
    "\\microsoft\\windows\\currentversion\\shell", "currentversion\\explorer\\browser helper objects",
)


def analyze_reg(text: str, filename: str = "") -> Dict[str, Any]:
    keys: List[Dict[str, Any]] = []
    current = ""
    values = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            if current:
                keys.append({"key": current, "values": values})
            current = line[1:-1]
            values = []
            continue
        if current and "=" in line:
            name, _, data = line.partition("=")
            values.append({"name": name.strip().strip('"'),
                           "value": data.strip().strip('"'),
                           "type": _reg_type(data.strip())})
    if current:
        keys.append({"key": current, "values": values})
    findings = []
    for key in keys:
        low = key["key"].lower()
        for pers in REG_PERSISTENCE_KEYS:
            if pers in low:
                risky = [v for v in key["values"]
                         if re.search(r"(?i)(temp|appdata|programdata|users\\|powershell|cmd\.exe|http:|\\\\|\.ps1|\.vbs|\.js|\.dll|rundll32|certutil)", str(v.get("value", "")))]
                findings.append({"severity": "high" if risky else "medium",
                                 "key": key["key"], "persistence_type": pers,
                                 "values": key["values"][:20], "risky_values": risky[:10]})
                break
        if "defender" in low or "amsi" in low or "windows defender" in low:
            findings.append({"severity": "critical", "key": key["key"],
                             "persistence_type": "security tampering",
                             "values": key["values"][:20]})
    iocs = extract_iocs(text)
    return {"filename": filename, "keys": keys[:500], "key_count": len(keys),
            "findings": sorted(findings, key=lambda f: severity_rank(f["severity"])),
            "iocs": iocs["categories"], "ioc_count": iocs["count"],
            "summary": {"run_keys": sum(1 for f in findings if "run" in f["persistence_type"]),
                        "services": sum(1 for f in findings if "service" in f["persistence_type"]),
                        "security_tampering": sum(1 for f in findings if "tampering" in f["persistence_type"])}}


def _reg_type(value: str) -> str:
    if value.startswith("dword:"):
        return "REG_DWORD"
    if value.startswith("hex:"):
        return "REG_BINARY"
    if value.startswith("hex(7):"):
        return "REG_MULTI_SZ"
    if value.startswith("hex(2):"):
        return "REG_EXPAND_SZ"
    return "REG_SZ"


def analyze_registry_hive(data: bytes, filename: str = "") -> Dict[str, Any]:
    """Heuristic hive parser: regf header, hbin/sk/1; strings extraction."""
    if data[:4] != b"regf":
        raise ValueError("not a Windows registry hive (missing regf)")
    major, minor = struct.unpack_from("<II", data, 0x14)[0], struct.unpack_from("<II", data, 0x18)[0]
    root = struct.unpack_from("<I", data, 0x24)[0]
    hive_bins = struct.unpack_from("<I", data, 0x28)[0]
    file_type = struct.unpack_from("<I", data, 0x1C)[0]
    last_write = _filetime(struct.unpack_from("<Q", data, 0x0C)[0])
    strings = list(dict.fromkeys(unicode_strings(data, 5, 5000) + ascii_strings(data, 5, 5000)))
    low = " ".join(strings).lower()
    indicators = []
    for marker in ("run", "runonce", "winlogon", "services", "defender", "amsi",
                   "appinit", "image file execution", "mimikatz", "powershell",
                   "currentversion\\explorer\\shell"):
        if marker in low:
            indicators.append(marker)
    return {"filename": filename, "size": len(data), "signature": "regf",
            "version": f"{major}.{minor}", "root_offset": hex(root),
            "hive_bins": hive_bins, "file_type": file_type,
            "last_write": last_write,
            "strings_sample": strings[:400], "indicators": indicators,
            "hashes": hash_bytes(data),
            "note": "Full hive parsing (cells/values) is heuristic here; use"
                    " regipy/RegistryFlush for production forensics."}


# --------------------------------------------------------------------------- #
#  Browser artifact databases (SQLite)
# --------------------------------------------------------------------------- #
BROWSER_DB_SIGNATURES = {
    "Login Data": "saved credentials", "Cookies": "cookies", "History": "browsing history",
    "Web Data": "autofill", "Bookmarks": "bookmarks", "Top Sites": "top sites",
    "Preferences": "settings", "Local State": "encryption keys",
    "places.sqlite": "firefox history", "logins.json": "firefox logins",
    "key4.db": "firefox keys", "cookies.sqlite": "firefox cookies",
}


def analyze_browser_db(data: bytes, filename: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {"filename": filename, "size": len(data),
                           "type": file_type(data, filename)["type"],
                           "kind": BROWSER_DB_SIGNATURES.get(Path(filename).name, "unknown")}
    if data[:16] != b"SQLite format 3\x00":
        out["note"] = "not a SQLite database"
        out["strings"] = ascii_strings(data, 6, 300)[:100]
        return out
    try:
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        Path(path).write_bytes(data)
        conn = sqlite3.connect(path)
        conn.text_factory = lambda b: b.decode("utf-8", "replace")
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        out["tables"] = tables
        rows: Dict[str, Any] = {}
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM '{table}'")
                rows[table] = cur.fetchone()[0]
            except Exception:
                continue
        out["row_counts"] = rows
        samples = {}
        for table in ("urls", "visits", "logins", "cookies", "autofill", "downloads",
                      "keyword_search_terms", "history_items"):
            if table in tables:
                try:
                    cur.execute(f"SELECT * FROM '{table}' LIMIT 20")
                    cols = [d[0] for d in cur.description]
                    samples[table] = [dict(zip(cols, [str(x)[:200] for x in row]))
                                      for row in cur.fetchall()]
                except Exception:
                    pass
        out["samples"] = samples
        conn.close()
        os.unlink(path)
        # Indicators
        blob = json.dumps(samples).lower()
        out["indicators"] = [k for k in ("password", "credit", "wallet", "bank", "crypto",
                                         "metamask", "binance", "coinbase", "paypal")
                             if k in blob]
        out["credential_store"] = "logins" in tables
    except Exception as exc:
        out["error"] = str(exc)
    return out


# --------------------------------------------------------------------------- #
#  NTFS MFT
# --------------------------------------------------------------------------- #
def analyze_mft(data: bytes, filename: str = "") -> Dict[str, Any]:
    if data[:4] != b"FILE":
        raise ValueError("not an MFT record (missing FILE signature)")
    records = []
    pos = 0
    size = 1024
    while pos + size <= len(data) and len(records) < 5000:
        rec = data[pos:pos + size]
        if rec[:4] == b"FILE":
            parsed = _mft_record(rec)
            if parsed:
                records.append(parsed)
        pos += size
    names = [r["name"] for r in records if r.get("name")]
    suspicious = [r for r in records if r.get("suspicious")]
    return {"filename": filename, "records": len(records),
            "files": records[:2000], "suspicious": suspicious[:200],
            "timestomp_candidates": [r for r in records if r.get("timestomp")][:100],
            "deleted": [r for r in records if r.get("deleted")][:200],
            "extension_counts": dict(Counter(Path(n).suffix.lower() for n in names if Path(n).suffix).most_common(30)),
            "hashes": hash_bytes(data)}


def _mft_record(rec: bytes) -> Optional[Dict[str, Any]]:
    try:
        usa_off, usa_count = struct.unpack_from("<HH", rec, 4)
        lsn = struct.unpack_from("<Q", rec, 8)[0]
        seq, link = struct.unpack_from("<HH", rec, 16)
        flags = struct.unpack_from("<H", rec, 22)[0]
        base = struct.unpack_from("<Q", rec, 32)[0]
        next_attr = struct.unpack_from("<H", rec, 20)[0]
        in_use = bool(flags & 0x1)
        is_dir = bool(flags & 0x2)
        name = ""
        si_times = {}
        fn_times = {}
        pos = next_attr
        while pos + 8 < len(rec) and pos < 0x400:
            atype, alen = struct.unpack_from("<II", rec, pos)
            if atype == 0xFFFFFFFF or alen == 0:
                break
            if atype == 0x30 and alen > 0x18:  # FILE_NAME
                content = rec[pos + 0x18:pos + alen]
                try:
                    parent = struct.unpack_from("<Q", content, 0)[0]
                    c, a, m, ch = struct.unpack_from("<QQQQ", content, 8)
                    nlen = content[64]
                    nspace = content[65]
                    nm = content[66:66 + nlen * 2].decode("utf-16le", "replace")
                    if nm and not name:
                        name = nm
                        fn_times = {"created": _filetime(c), "accessed": _filetime(a),
                                    "modified": _filetime(m), "changed": _filetime(ch)}
                except Exception:
                    pass
            elif atype == 0x10 and alen > 0x18:  # STANDARD_INFORMATION
                content = rec[pos + 0x18:pos + alen]
                try:
                    c, a, m, ch = struct.unpack_from("<QQQQ", content, 0)
                    si_times = {"created": _filetime(c), "accessed": _filetime(a),
                                "modified": _filetime(m), "changed": _filetime(ch)}
                except Exception:
                    pass
            pos += alen
        suspicious = False
        timestomp = False
        if in_use and name and re.search(r"(?i)\.(exe|dll|scr|ps1|vbs|js|hta|bat|cmd)$", name):
            suspicious = True
        if si_times and fn_times and si_times.get("modified") != fn_times.get("modified"):
            timestomp = True
        return {"in_use": in_use, "directory": is_dir, "name": name,
                "sequence": seq, "links": link, "lsn": lsn, "base_record": base,
                "si_times": si_times, "fn_times": fn_times,
                "suspicious": suspicious, "timestomp": timestomp,
                "deleted": not in_use}
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  Shellbags / jumplists / hibernation / VSS hints
# --------------------------------------------------------------------------- #
def analyze_shellbags(data: bytes, filename: str = "") -> Dict[str, Any]:
    strings = list(dict.fromkeys(unicode_strings(data, 4, 8000) + ascii_strings(data, 4, 8000)))
    folders = [s for s in strings if re.search(r"(?i)^[a-z]:\\(?:[^\\/:*?\"<>|]+\\)*[^\\/:*?\"<>|]*$", s)]
    network = [s for s in strings if s.startswith("\\\\")]
    usb = [s for s in strings if re.search(r"(?i)(usb|removable|flash|kingston|sandisk|cruzer)", s)]
    return {"filename": filename, "size": len(data), "strings": strings[:600],
            "folders": list(dict.fromkeys(folders))[:300],
            "network_paths": list(dict.fromkeys(network))[:100],
            "usb_artifacts": list(dict.fromkeys(usb))[:100],
            "likely_shellbag": b"Bags" in data or b"BagMRU" in data or b"Shell" in data,
            "hashes": hash_bytes(data)}


def analyze_jumplist(data: bytes, filename: str = "") -> Dict[str, Any]:
    strings = list(dict.fromkeys(unicode_strings(data, 4, 8000) + ascii_strings(data, 4, 8000)))
    paths = [s for s in strings if re.search(r"(?i)(^[a-z]:\\|^\\\\)", s)]
    return {"filename": filename, "size": len(data),
            "dest_list": "DestList" in data.decode("latin-1", "ignore"),
            "paths": list(dict.fromkeys(paths))[:300],
            "strings_sample": strings[:300], "hashes": hash_bytes(data)}


def analyze_hibernation(data: bytes, filename: str = "") -> Dict[str, Any]:
    sig = data[:8]
    valid = data[:4] in (b"hibr", b"HIBR", b"wake", b"WAKE")
    return {"filename": filename, "size": len(data), "signature": sig.hex(),
            "valid_header": valid, "entropy": round(entropy(data[:1 << 20]), 3),
            "note": "Full hibernation parsing requires volatility3; this reports"
                    " header validity and entropy for triage.",
            "hashes": hash_bytes(data)}


# --------------------------------------------------------------------------- #
#  Steganography
# --------------------------------------------------------------------------- #
def analyze_stego(data: bytes, filename: str = "") -> Dict[str, Any]:
    ftype = file_type(data, filename)
    out: Dict[str, Any] = {"filename": filename, "type": ftype["type"],
                           "size": len(data), "findings": [], "extracted": []}
    kind = ftype["type"]
    if kind == "PNG":
        _stego_png(data, out)
    elif kind == "JPEG":
        _stego_jpeg(data, out)
    elif kind == "GIF":
        _stego_gif(data, out)
    elif kind == "BMP":
        _stego_bmp(data, out)
    elif kind == "WAV":
        _stego_wav(data, out)
    # Generic trailing data
    tail = _trailing_data(data, ftype)
    if tail:
        out["extracted"].append({"location": "trailing_after_eof", "size": len(tail),
                                 "type": file_type(tail)["type"],
                                 "sha256": hashlib.sha256(tail).hexdigest(),
                                 "preview_hex": tail[:32].hex()})
        out["findings"].append({"severity": "high",
                                "finding": f"{len(tail)} bytes appended after valid {kind} data"})
    # LSB strings / appended archives
    for marker, label in ((b"PK\x03\x04", "ZIP archive"), (b"MZ", "PE executable"),
                          (b"\x7fELF", "ELF binary"), (b"%PDF", "PDF document"),
                          (b"-----BEGIN", "PEM key/certificate")):
        idx = data.find(marker)
        if idx > 0 and idx < len(data) - 64:
            out["findings"].append({"severity": "medium",
                                    "finding": f"{label} at offset {idx} (possible embedded payload)"})
    if not out["findings"]:
        out["findings"].append({"severity": "info", "finding": "no overt stego indicators"})
    out["hashes"] = hash_bytes(data)
    return out


def _trailing_data(data: bytes, ftype: Dict[str, Any]) -> bytes:
    kind = ftype.get("type", "")
    if kind == "PNG":
        idx = data.rfind(b"IEND")
        if idx > 0:
            return data[idx + 8:]
    if kind == "JPEG":
        idx = data.rfind(b"\xff\xd9")
        if idx > 0:
            return data[idx + 2:]
    if kind == "GIF":
        idx = data.rfind(b"\x3b")
        if idx > 0 and idx < len(data) - 1:
            return data[idx + 1:]
    if kind == "BMP":
        if len(data) >= 6:
            size = struct.unpack_from("<I", data, 2)[0]
            if size < len(data):
                return data[size:]
    if kind == "WAV":
        idx = data.rfind(b"data")
        if idx > 0 and idx + 8 <= len(data):
            size = struct.unpack_from("<I", data, idx + 4)[0]
            end = idx + 8 + size
            if end < len(data):
                return data[end:]
    return b""


def _stego_png(data: bytes, out: Dict[str, Any]) -> None:
    pos = 8
    chunks = []
    while pos + 12 <= len(data):
        ln = struct.unpack_from(">I", data, pos)[0]
        ctype = data[pos + 4:pos + 8].decode("latin-1", "replace")
        body = data[pos + 8:pos + 8 + ln]
        chunks.append({"type": ctype, "length": ln})
        if ctype in ("tEXt", "zTXt", "iTXt", "eXIf", "tIME"):
            text = body.decode("latin-1", "replace")[:400]
            out["findings"].append({"severity": "medium",
                                    "finding": f"PNG metadata chunk {ctype}", "data": text})
        if ctype not in ("IHDR", "IDAT", "IEND", "PLTE", "tRNS", "gAMA", "pHYs",
                         "sRGB", "tEXt", "zTXt", "iTXt", "bKGD", "cHRM", "eXIf",
                         "tIME", "iCCP", "sBIT", "hIST", "tRNS", "acTL", "fcTL", "fdAT"):
            out["findings"].append({"severity": "high",
                                    "finding": f"non-standard PNG chunk {ctype!r} ({ln} bytes)"})
        pos += 12 + ln
        if ctype == "IEND":
            break
    out["chunks"] = chunks[:100]


def _stego_jpeg(data: bytes, out: Dict[str, Any]) -> None:
    pos = 2
    segments = []
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0xD9):
            pos += 2
            continue
        if marker == 0xDA:
            break
        ln = struct.unpack_from(">H", data, pos + 2)[0]
        body = data[pos + 4:pos + 2 + ln]
        label = {0xE0: "APP0/JFIF", 0xE1: "APP1/EXIF", 0xE2: "APP2/ICC",
                 0xED: "APP13/Photoshop", 0xEE: "APP14/Adobe",
                 0xFE: "COM"}.get(marker, f"APP{marker - 0xE0}" if 0xE0 <= marker <= 0xEF else hex(marker))
        segments.append({"marker": label, "length": ln})
        if marker in (0xE1, 0xED, 0xEE, 0xFE) and b"<" in body[:64]:
            out["findings"].append({"severity": "medium",
                                    "finding": f"{label} contains markup/XML data"})
        pos += 2 + ln
    out["segments"] = segments[:60]


def _stego_gif(data: bytes, out: Dict[str, Any]) -> None:
    # Check for extra graphics control / application extensions
    count = data.count(b"\x21\xff\x0bNETSCAPE2.0")
    if count:
        out["findings"].append({"severity": "low", "finding": "GIF Netscape looping extension"})
    if data.count(b"\x21\xfe"):
        out["findings"].append({"severity": "medium", "finding": "GIF comment extension present"})


def _stego_bmp(data: bytes, out: Dict[str, Any]) -> None:
    if len(data) >= 54:
        width, height = struct.unpack_from("<ii", data, 18)
        bpp = struct.unpack_from("<H", data, 28)[0]
        out["dimensions"] = {"width": width, "height": height, "bpp": bpp}
        if bpp not in (1, 4, 8, 16, 24, 32):
            out["findings"].append({"severity": "medium", "finding": f"unusual BMP bit depth {bpp}"})


def _stego_wav(data: bytes, out: Dict[str, Any]) -> None:
    idx = data.find(b"fmt ")
    if idx > 0 and idx + 20 <= len(data):
        fmt, channels, rate, _, _, bits = struct.unpack_from("<HHIIHH", data, idx + 8)
        out["audio"] = {"format": fmt, "channels": channels, "rate": rate, "bits": bits}
        if bits == 8:
            out["findings"].append({"severity": "low",
                                    "finding": "8-bit PCM WAV (common LSB stego carrier)"})


def lsb_extract(data: bytes, channel: str = "auto", max_bytes: int = 65536) -> Dict[str, Any]:
    """Extract least-significant bits and try to detect a text/PE payload."""
    bits = [b & 1 for b in data]
    payload = bytearray()
    for i in range(0, min(len(bits), max_bytes * 8) - 7, 8):
        byte = 0
        for bit in bits[i:i + 8]:
            byte = (byte << 1) | bit
        payload.append(byte)
    head = bytes(payload)
    printable = sum(1 for b in head[:512] if 32 <= b <= 126 or b in (9, 10, 13))
    kind = "text" if printable / max(1, len(head[:512])) > 0.8 else "binary"
    if head[:2] == b"MZ":
        kind = "PE executable"
    elif head[:4] == b"PK\x03\x04":
        kind = "ZIP archive"
    if head[:5] in (b"BEGIN", b"-----"):
        kind = "PEM"
    return {"extracted_size": len(head), "detected": kind,
            "entropy": round(entropy(head), 3),
            "preview": head[:300].decode("latin-1", "replace"),
            "preview_hex": head[:64].hex(),
            "score": 90 if kind in ("PE executable", "ZIP archive", "PEM") else
                     (60 if kind == "text" and printable > 400 else 20)}


# --------------------------------------------------------------------------- #
#  Firmware / IoT
# --------------------------------------------------------------------------- #
FIRMWARE_SIGNATURES = {
    b"hsqs": "SquashFS (little-endian)", b"sqsh": "SquashFS (big-endian)",
    b"UBI#": "UBI erase count header", b"UBI!": "UBI volume", b"\x27\x05\x19\x56": "uImage",
    b"\xd0\x0d\xfe\xed": "FIT/DTB", b"ANDROID!": "Android boot image",
    b"CRAMFS": "CramFS", b"\x85\x19": "JFFS2", b"-rom1fs-": "romfs",
    b"_\x1b\xf1\x8c": "MOTOROLA firmware", b"LINUX": "Linux kernel setup",
    b"U-Boot": "U-Boot bootloader", b"rockchip": "Rockchip image",
}

FIRMWARE_INTERESTING = (
    "telnetd", "busybox", "dropbear", "wpa_supplicant", "nvram", "setenv",
    "admin", "password", "root", "/etc/shadow", "/etc/passwd", "ssh-rsa",
    "private key", "wget", "curl", "tftp", "nc ", "backdoor", "debug",
    "httpd", "/bin/sh", "upgrade", "firmware", "squashfs", "jffs2", "ubifs",
)


def analyze_firmware(data: bytes, filename: str = "") -> Dict[str, Any]:
    sigs = []
    for sig, name in FIRMWARE_SIGNATURES.items():
        if data[:len(sig)] == sig or sig in data[:4096]:
            sigs.append({"signature": name, "offset": data.find(sig)})
    # binwalk-style scan for embedded filesystems/compressions
    embedded = _binwalk_scan(data)
    strings = list(dict.fromkeys(re.findall(r"[ -~]{6,200}", data.decode("latin-1", "ignore"))))
    interesting = [s for s in strings if any(k in s.lower() for k in FIRMWARE_INTERESTING)]
    credentials = [s for s in strings if re.search(
        r"(?i)(password|passwd|admin:|root:|wpa_passphrase|psk=|ssh-rsa|BEGIN .*PRIVATE KEY)", s)]
    findings = []
    if credentials:
        findings.append({"severity": "high", "finding": "possible hardcoded credentials",
                         "evidence": credentials[:10]})
    if any("telnetd" in s.lower() for s in interesting):
        findings.append({"severity": "medium", "finding": "telnetd present (cleartext admin)"})
    if any("BEGIN" in s and "PRIVATE KEY" in s for s in strings):
        findings.append({"severity": "critical", "finding": "private key material in firmware"})
    out = {"filename": filename, "size": len(data),
           "entropy": round(entropy(data), 3),
           "signatures": sigs, "embedded": embedded,
           "interesting_strings": interesting[:200],
           "credential_candidates": credentials[:50],
           "findings": findings,
           "hashes": hash_bytes(data),
           "next_steps": ["binwalk -eM firmware.bin", "firmwalker / firmadyne",
                          "Check update signature verification", "Audit default accounts"]}
    # Try to unpack SquashFS block list hint
    if any(s["signature"].startswith("SquashFS") for s in sigs):
        out["next_steps"].insert(0, "unsquashfs -d out firmware.bin")
    return out


def _binwalk_scan(data: bytes) -> List[Dict[str, Any]]:
    markers = {
        b"\x1f\x8b\x08": "gzip", b"BZh": "bzip2", b"\xfd7zXZ\x00": "xz",
        b"hsqs": "SquashFS", b"UBI#": "UBI", b"\x85\x19": "JFFS2",
        b"PK\x03\x04": "ZIP", b"\x7fELF": "ELF", b"MZ": "PE",
        b"\x89PNG\r\n\x1a\n": "PNG", b"\xff\xd8\xff": "JPEG", b"ustar": "tar",
        b"-----BEGIN": "PEM", b"%PDF": "PDF",
    }
    out = []
    for marker, name in markers.items():
        start = 0
        while True:
            idx = data.find(marker, start)
            if idx < 0:
                break
            out.append({"offset": idx, "type": name})
            start = idx + 1
            if len(out) > 200:
                break
    out.sort(key=lambda x: x["offset"])
    return out[:200]


# --------------------------------------------------------------------------- #
#  APK / IPA
# --------------------------------------------------------------------------- #
PERMISSION_RISK = {
    "android.permission.SEND_SMS": ("critical", "SMS sending (premium fraud)"),
    "android.permission.READ_SMS": ("high", "SMS interception (2FA theft)"),
    "android.permission.RECEIVE_SMS": ("high", "SMS interception"),
    "android.permission.CALL_PHONE": ("medium", "premium calls"),
    "android.permission.RECORD_AUDIO": ("high", "microphone capture"),
    "android.permission.CAMERA": ("medium", "camera capture"),
    "android.permission.ACCESS_FINE_LOCATION": ("medium", "precise location"),
    "android.permission.READ_CONTACTS": ("medium", "contact exfiltration"),
    "android.permission.READ_CALL_LOG": ("high", "call log theft"),
    "android.permission.SYSTEM_ALERT_WINDOW": ("high", "overlay / clickjacking"),
    "android.permission.BIND_ACCESSIBILITY_SERVICE": ("critical", "accessibility abuse"),
    "android.permission.REQUEST_INSTALL_PACKAGES": ("high", "dropper capability"),
    "android.permission.QUERY_ALL_PACKAGES": ("medium", "app enumeration"),
    "android.permission.MANAGE_EXTERNAL_STORAGE": ("high", "broad file access"),
    "android.permission.READ_PHONE_STATE": ("medium", "device identifiers"),
    "android.permission.POST_NOTIFICATIONS": ("low", "notification abuse"),
    "android.permission.INTERNET": ("info", "network access"),
    "android.permission.WAKE_LOCK": ("low", "background persistence"),
}


def analyze_apk(data: bytes, filename: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {"filename": filename, "size": len(data), "format": "APK",
                           "hashes": hash_bytes(data), "findings": []}
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except Exception as exc:
        return {"filename": filename, "error": f"not a valid APK/ZIP: {exc}"}
    names = zf.namelist()
    out["entries"] = len(names)
    out["files"] = names[:400]
    manifest = None
    try:
        raw = zf.read("AndroidManifest.xml")
        manifest = _axml_parse(raw)
    except Exception as exc:
        out["findings"].append({"severity": "info", "finding": f"manifest parse: {exc}"})
    if manifest:
        out["package"] = manifest.get("package", "")
        out["version"] = manifest.get("versionName", "")
        out["permissions"] = manifest.get("permissions", [])
        out["activities"] = manifest.get("activities", [])[:60]
        out["services"] = manifest.get("services", [])[:60]
        out["receivers"] = manifest.get("receivers", [])[:60]
        out["providers"] = manifest.get("providers", [])[:40]
        risky = []
        for perm in out["permissions"]:
            if perm in PERMISSION_RISK:
                sev, desc = PERMISSION_RISK[perm]
                risky.append({"permission": perm, "severity": sev, "meaning": desc})
        out["risky_permissions"] = sorted(risky, key=lambda x: severity_rank(x["severity"]))
        if manifest.get("debuggable"):
            out["findings"].append({"severity": "medium", "finding": "android:debuggable=true"})
        if manifest.get("allowBackup"):
            out["findings"].append({"severity": "low", "finding": "android:allowBackup=true"})
        if manifest.get("usesCleartextTraffic"):
            out["findings"].append({"severity": "medium", "finding": "cleartext traffic permitted"})
    # Libraries / packers
    libs = sorted({n.split("/")[1] for n in names if n.startswith("lib/") and n.count("/") > 1})
    out["native_libs"] = libs
    dex = [n for n in names if n.endswith(".dex")]
    out["dex_files"] = dex
    packers = [l for l in libs if any(k in l.lower() for k in
               ("jiagu", "qprotect", "bangs", "tencent", "baidu", "360", "ijiami",
                "alipay", "mobisec", "secneo", "kiwisec", "upx"))]
    if packers:
        out["findings"].append({"severity": "high", "finding": f"APK packer/protector libraries: {packers}"})
    # Strings / IOCs from DEX + resources
    text = []
    for name in names:
        if name.endswith((".dex", ".so", ".xml", ".json", ".txt", ".smali")):
            try:
                blob = zf.read(name)
                if len(blob) > 8 << 20:
                    continue
                text.append(blob.decode("utf-8", "ignore"))
            except Exception:
                continue
    joined = "\n".join(text)
    iocs = extract_iocs(joined)
    out["iocs"] = iocs["categories"]
    out["urls"] = iocs["categories"]["urls"][:100]
    out["domains"] = iocs["categories"]["domains"][:100]
    out["suspicious_strings"] = [s for s in re.findall(r"[ -~]{6,120}", joined)
                                 if re.search(r"(?i)(/system/bin/su|superuser|magisk|frida|xposed|root|inject|dexclassloader|reflection|sms|otp|bank|wallet|telegram|bot)", s)][:100]
    if any("su" in str(l).lower() for l in libs) or "superuser" in joined.lower():
        out["findings"].append({"severity": "high", "finding": "root/superuser references"})
    if "frida" in joined.lower() or "xposed" in joined.lower():
        out["findings"].append({"severity": "medium", "finding": "instrumentation framework references"})
    out["score"] = min(100, len(out.get("risky_permissions", [])) * 8 + len(out["findings"]) * 15)
    return out


def _axml_parse(raw: bytes) -> Dict[str, Any]:
    """Minimal Android binary XML (AXML) string-pool + element reader."""
    out: Dict[str, Any] = {"permissions": [], "activities": [], "services": [],
                           "receivers": [], "providers": []}
    if len(raw) < 8:
        raise ValueError("AXML too small")
    typ, hsize, size = struct.unpack_from("<HHI", raw, 0)
    if typ != 0x0003:
        # plain-text XML fallback
        text = raw.decode("utf-8", "ignore")
        m = re.search(r'package="([^"]+)"', text)
        if m:
            out["package"] = m.group(1)
        out["permissions"] = re.findall(r'uses-permission[^>]*android:name="([^"]+)"', text)
        out["activities"] = re.findall(r'<activity[^>]*android:name="([^"]+)"', text)
        out["services"] = re.findall(r'<service[^>]*android:name="([^"]+)"', text)
        out["receivers"] = re.findall(r'<receiver[^>]*android:name="([^"]+)"', text)
        out["debuggable"] = "android:debuggable=\"true\"" in text
        out["allowBackup"] = "android:allowBackup=\"true\"" in text
        out["usesCleartextTraffic"] = "usesCleartextTraffic=\"true\"" in text
        return out
    pos = hsize
    strings: List[str] = []
    res_ids: List[int] = []
    while pos + 8 <= len(raw):
        ctype, chsize, csize = struct.unpack_from("<HHI", raw, pos)
        if csize < 8 or pos + csize > len(raw):
            break
        body = raw[pos:pos + csize]
        if ctype == 0x0001:  # string pool
            count, style_count, flags, str_start, style_start = struct.unpack_from("<IIIII", body, 8)
            utf8 = bool(flags & 0x100)
            offsets = []
            for i in range(count):
                offsets.append(struct.unpack_from("<I", body, 8 + 20 + i * 4)[0])
            for off in offsets:
                sp = 8 + str_start + off
                try:
                    if utf8:
                        # utf16 length then utf8 length
                        l1 = body[sp]
                        if l1 & 0x80:
                            sp += 1
                        sp += 1
                        l2 = body[sp]
                        if l2 & 0x80:
                            l2 = ((l2 & 0x7F) << 8) | body[sp + 1]
                            sp += 2
                        else:
                            sp += 1
                        strings.append(body[sp:sp + l2].decode("utf-8", "replace"))
                    else:
                        ln = struct.unpack_from("<H", body, sp)[0]
                        sp += 2
                        if ln & 0x8000:
                            sp += 2
                        strings.append(body[sp:sp + ln * 2].decode("utf-16le", "replace"))
                except Exception:
                    strings.append("")
        elif ctype == 0x0180:  # resource map
            n = (csize - 8) // 4
            for i in range(n):
                try:
                    res_ids.append(struct.unpack_from("<I", body, 8 + i * 4)[0])
                except Exception:
                    pass
        elif ctype == 0x0102:  # START_ELEMENT
            pass
        pos += csize
    text = "\n".join(strings)
    out["package"] = _first_after(strings, "package")
    for perm in strings:
        if perm.startswith("android.permission."):
            out["permissions"].append(perm)
    for s in strings:
        if re.match(r"^[a-zA-Z][\w.]+\.[A-Z]\w+$", s) and "." in s:
            pass
    out["activities"] = [s for s in strings if re.search(r"(?i)(activity|main)", s)][:80]
    out["services"] = [s for s in strings if re.search(r"(?i)service", s)][:80]
    out["receivers"] = [s for s in strings if re.search(r"(?i)receiver", s)][:80]
    out["debuggable"] = any("debuggable" in s.lower() for s in strings)
    out["allowBackup"] = any("allowBackup" in s for s in strings)
    out["usesCleartextTraffic"] = any("usesCleartextTraffic" in s for s in strings)
    out["strings_sample"] = strings[:300]
    return out


def _first_after(strings: Sequence[str], needle: str) -> str:
    for i, s in enumerate(strings):
        if s == needle and i + 1 < len(strings):
            return strings[i + 1]
    return ""


def analyze_ipa(data: bytes, filename: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {"filename": filename, "size": len(data), "format": "IPA",
                           "hashes": hash_bytes(data), "findings": []}
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except Exception as exc:
        return {"filename": filename, "error": f"not a valid IPA/ZIP: {exc}"}
    names = zf.namelist()
    out["entries"] = len(names)
    info = None
    for n in names:
        if n.endswith("Info.plist") and ".app/" in n:
            try:
                info = plistlib.loads(zf.read(n))
            except Exception:
                info = None
            break
    if info:
        out["bundle_id"] = info.get("CFBundleIdentifier", "")
        out["bundle_name"] = info.get("CFBundleName", "")
        out["version"] = info.get("CFBundleShortVersionString", "")
        out["build"] = info.get("CFBundleVersion", "")
        out["minimum_os"] = info.get("MinimumOSVersion", "")
        out["executable"] = info.get("CFBundleExecutable", "")
        out["url_schemes"] = [u for d in info.get("CFBundleURLTypes", []) or []
                              for u in d.get("CFBundleURLSchemes", []) or []]
        out["app_transport_security"] = "NSAllowsArbitraryLoads" in json.dumps(info)
        if out["app_transport_security"]:
            out["findings"].append({"severity": "medium", "finding": "App Transport Security disabled"})
    # Entitlements
    ent = None
    for n in names:
        if n.endswith(".entitlements"):
            try:
                ent = plistlib.loads(zf.read(n))
            except Exception:
                continue
            break
    if ent:
        out["entitlements"] = {k: ent[k] for k in list(ent)[:60]}
        if ent.get("get-task-allow"):
            out["findings"].append({"severity": "high", "finding": "get-task-allow (debuggable)"})
        if "com.apple.private" in json.dumps(ent):
            out["findings"].append({"severity": "high", "finding": "private Apple entitlement"})
    frameworks = sorted({n.split("/")[2] for n in names
                         if n.startswith("Payload/") and n.count("/") >= 3})
    out["frameworks"] = frameworks[:100]
    out["dylibs"] = sorted({n for n in names if n.endswith(".dylib")})[:100]
    text = []
    for n in names:
        if n.endswith((".plist", ".json", ".strings", ".js", ".html")):
            try:
                text.append(zf.read(n).decode("utf-8", "ignore"))
            except Exception:
                continue
    joined = "\n".join(text)
    iocs = extract_iocs(joined)
    out["urls"] = iocs["categories"]["urls"][:80]
    out["domains"] = iocs["categories"]["domains"][:80]
    if "password" in joined.lower() or "secret" in joined.lower():
        out["findings"].append({"severity": "low", "finding": "secret-related strings present"})
    out["score"] = min(100, len(out["findings"]) * 20)
    return out


# --------------------------------------------------------------------------- #
#  Secret scanning
# --------------------------------------------------------------------------- #
SECRET_PATTERNS: List[Dict[str, Any]] = [
    {"name": "AWS Access Key ID", "regex": r"\b(?:AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}\b",
     "severity": "critical"},
    {"name": "AWS Secret Access Key", "regex": r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})",
     "severity": "critical"},
    {"name": "GitHub Token", "regex": r"\bgh[pousr]_[A-Za-z0-9]{30,}\b", "severity": "critical"},
    {"name": "GitLab Token", "regex": r"\bglpat-[A-Za-z0-9_-]{20,}\b", "severity": "critical"},
    {"name": "Slack Token", "regex": r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "severity": "high"},
    {"name": "Stripe Secret Key", "regex": r"\bsk_(?:live|test)_[A-Za-z0-9]{20,}\b", "severity": "critical"},
    {"name": "Google API Key", "regex": r"\bAIza[0-9A-Za-z_-]{35}\b", "severity": "high"},
    {"name": "Private Key Block", "regex": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----",
     "severity": "critical"},
    {"name": "JWT", "regex": r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
     "severity": "medium"},
    {"name": "Generic API Key", "regex": r"(?i)(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token)\s*[=:]\s*['\"]([A-Za-z0-9_\-]{20,})['\"]",
     "severity": "high"},
    {"name": "Password Assignment", "regex": r"(?i)(?:password|passwd|pwd)\s*[=:]\s*['\"]([^'\"\s]{6,})['\"]",
     "severity": "high"},
    {"name": "Basic Auth Header", "regex": r"(?i)authorization\s*:\s*basic\s+([A-Za-z0-9+/=]{10,})",
     "severity": "high"},
    {"name": "Bearer Token", "regex": r"(?i)authorization\s*:\s*bearer\s+([A-Za-z0-9._\-]{20,})",
     "severity": "high"},
    {"name": "Twilio Account SID", "regex": r"\bAC[a-f0-9]{32}\b", "severity": "medium"},
    {"name": "SendGrid Key", "regex": r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}\b", "severity": "critical"},
    {"name": "npm Token", "regex": r"\bnpm_[A-Za-z0-9]{36}\b", "severity": "high"},
    {"name": "Discord Webhook", "regex": r"https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+",
     "severity": "high"},
    {"name": "Telegram Bot Token", "regex": r"\b\d{8,10}:AA[A-Za-z0-9_-]{33,}\b", "severity": "high"},
    {"name": "MongoDB URI", "regex": r"mongodb(?:\+srv)?://[^\s'\"]+", "severity": "high"},
    {"name": "PostgreSQL URI", "regex": r"postgres(?:ql)?://[^\s'\"]+", "severity": "high"},
    {"name": "MySQL URI", "regex": r"mysql://[^\s'\"]+", "severity": "high"},
    {"name": "Redis URI", "regex": r"redis://[^\s'\"]+", "severity": "medium"},
]


def scan_secrets(text: str, filename: str = "", redact: bool = True) -> Dict[str, Any]:
    findings = []
    seen = set()
    for pat in SECRET_PATTERNS:
        for m in re.finditer(pat["regex"], text):
            value = m.group(0)
            # Prefer captured secret group when present
            if m.groups():
                value = m.group(1) or m.group(0)
            key = (pat["name"], value[:24])
            if key in seen:
                continue
            seen.add(key)
            line_no = text[:m.start()].count("\n") + 1
            line = text.splitlines()[line_no - 1] if line_no <= len(text.splitlines()) else ""
            findings.append({"type": pat["name"], "severity": pat["severity"],
                             "line": line_no,
                             "value": (value[:6] + "…" + value[-4:]) if redact and len(value) > 14 else value,
                             "length": len(value),
                             "context": line.strip()[:160]})
    # Entropy-based detection of long random strings
    for m in re.finditer(r"\b[A-Za-z0-9+/=_\-]{32,}\b", text):
        s = m.group(0)
        if len(set(s)) < 10:
            continue
        if entropy(s.encode()) > 4.4 and not re.fullmatch(r"[0-9a-fA-F]+", s):
            key = ("high-entropy", s[:24])
            if key in seen:
                continue
            seen.add(key)
            findings.append({"type": "High-entropy string", "severity": "medium",
                             "line": text[:m.start()].count("\n") + 1,
                             "value": (s[:6] + "…" + s[-4:]) if redact else s,
                             "length": len(s), "entropy": round(entropy(s.encode()), 2),
                             "context": ""})
    findings.sort(key=lambda f: severity_rank(f["severity"]))
    return {"filename": filename, "findings": findings[:500],
            "count": len(findings),
            "by_type": dict(Counter(f["type"] for f in findings)),
            "severity_counts": dict(Counter(f["severity"] for f in findings)),
            "verdict": "secrets exposed" if findings else "no obvious secrets"}


# --------------------------------------------------------------------------- #
#  IaC / container / Kubernetes / cloud configuration
# --------------------------------------------------------------------------- #
def analyze_iac(text: str, filename: str = "") -> Dict[str, Any]:
    lower_name = Path(filename).name.lower()
    fmt = "yaml"
    if lower_name.endswith(".json"):
        fmt = "json"
    elif lower_name in ("dockerfile",) or lower_name.startswith("dockerfile"):
        fmt = "dockerfile"
    elif lower_name.endswith(".tf") or lower_name.endswith(".tfvars"):
        fmt = "terraform"
    findings: List[Dict[str, Any]] = []
    low = text.lower()
    # Kubernetes
    if "kind:" in low and ("apiversion:" in low or "apiVersion:" in text):
        if re.search(r"(?im)^\s*privileged\s*:\s*true", text):
            findings.append({"severity": "critical", "finding": "privileged container"})
        if re.search(r"(?im)^\s*hostnetwork\s*:\s*true", text):
            findings.append({"severity": "high", "finding": "hostNetwork: true"})
        if re.search(r"(?im)^\s*hostpid\s*:\s*true", text):
            findings.append({"severity": "high", "finding": "hostPID: true"})
        if re.search(r"(?im)^\s*hostipc\s*:\s*true", text):
            findings.append({"severity": "medium", "finding": "hostIPC: true"})
        if "docker.sock" in low:
            findings.append({"severity": "critical", "finding": "Docker socket mounted"})
        if re.search(r"(?im)runasuser\s*:\s*0\b", text):
            findings.append({"severity": "high", "finding": "runs as root (runAsUser: 0)"})
        if re.search(r"(?im)readonlyrootfilesystem\s*:\s*false", text):
            findings.append({"severity": "medium", "finding": "writable root filesystem"})
        if re.search(r"(?im)allowprivilegeescalation\s*:\s*true", text):
            findings.append({"severity": "high", "finding": "allowPrivilegeEscalation: true"})
        if re.search(r"(?im)capabilities\s*:[\s\S]{0,120}add\s*:[\s\S]{0,120}all", text):
            findings.append({"severity": "critical", "finding": "all Linux capabilities added"})
        if re.search(r"(?im)hostpath\s*:", text):
            findings.append({"severity": "high", "finding": "hostPath volume mounted"})
    # Dockerfile
    if fmt == "dockerfile":
        if re.search(r"(?im)^\s*user\s+root", text) or not re.search(r"(?im)^\s*user\s+", text):
            findings.append({"severity": "medium", "finding": "container runs as root or no USER set"})
        if re.search(r"(?im)^\s*add\s+https?://", text):
            findings.append({"severity": "high", "finding": "ADD from remote URL"})
        if re.search(r"(?im)^\s*curl[^\n]*\|\s*(?:bash|sh)", text):
            findings.append({"severity": "critical", "finding": "curl pipe to shell"})
        if re.search(r"(?im)^\s*arg\s+.*(?:password|token|secret)", text):
            findings.append({"severity": "high", "finding": "secret passed as build ARG"})
        if re.search(r"(?im)^\s*env\s+.*(?:password|token|secret|key)=", text):
            findings.append({"severity": "high", "finding": "secret in ENV"})
        if re.search(r"(?im)^\s*expose\s+22\b", text):
            findings.append({"severity": "low", "finding": "SSH exposed"})
    # Terraform
    if fmt == "terraform":
        if re.search(r"(?im)acl\s*=\s*\"public-read", text):
            findings.append({"severity": "critical", "finding": "public S3 ACL"})
        if re.search(r"(?im)publicly_accessible\s*=\s*true", text):
            findings.append({"severity": "critical", "finding": "publicly accessible database"})
        if re.search(r"(?im)encrypted\s*=\s*false", text):
            findings.append({"severity": "high", "finding": "encryption disabled"})
        if re.search(r"(?im)0\.0\.0\.0/0", text):
            findings.append({"severity": "high", "finding": "open CIDR 0.0.0.0/0"})
        if re.search(r"(?im)policy\s*=\s*\"\*\"", text):
            findings.append({"severity": "critical", "finding": "IAM wildcard policy"})
        if re.search(r"(?im)versioning\s*\{[^}]*enabled\s*=\s*false", text, re.S):
            findings.append({"severity": "medium", "finding": "S3 versioning disabled"})
    # Generic cloud config (AWS/Azure/GCP JSON)
    if fmt == "json":
        try:
            obj = json.loads(text)
            _cloud_config_checks(obj, findings)
        except Exception:
            pass
    # Secrets embedded anywhere
    secrets = scan_secrets(text, filename)
    if secrets["findings"]:
        findings.append({"severity": "critical", "finding": f"{secrets['count']} embedded secret(s)",
                         "evidence": secrets["findings"][:10]})
    # CI/CD injection patterns
    if re.search(r"\$\{\{\s*github\.event\.(?:issue|pull_request|comment)", text):
        findings.append({"severity": "high", "finding": "GitHub Actions expression injection risk"})
    if "pull_request_target" in text and "checkout" in text:
        findings.append({"severity": "high", "finding": "pull_request_target with checkout"})
    findings = _dedupe(findings)
    return {"filename": filename, "format": fmt, "findings": findings,
            "count": len(findings),
            "secrets": {"count": secrets["count"], "types": secrets["by_type"]},
            "verdict": "critical misconfigurations" if any(f["severity"] == "critical" for f in findings)
                       else ("issues found" if findings else "no obvious issues"),
            "score": min(100, sum({"critical": 25, "high": 15, "medium": 7, "low": 3}.get(f["severity"], 0)
                                  for f in findings))}


def _cloud_config_checks(obj: Any, findings: List[Dict[str, Any]], path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            p = f"{path}.{key}" if path else key
            if key.lower() in ("publiclyaccessible", "publicaccess", "public") and value is True:
                findings.append({"severity": "critical", "finding": f"public exposure at {p}"})
            if key.lower() in ("encryption", "encrypted", "encryptionenabled") and value is False:
                findings.append({"severity": "high", "finding": f"encryption disabled at {p}"})
            if key.lower() in ("versioning",) and value is False:
                findings.append({"severity": "medium", "finding": f"versioning disabled at {p}"})
            _cloud_config_checks(value, findings, p)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:200]):
            _cloud_config_checks(item, findings, f"{path}[{i}]")


def _dedupe(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for f in findings:
        key = (f.get("severity"), f.get("finding"))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return sorted(out, key=lambda f: severity_rank(f["severity"]))


# --------------------------------------------------------------------------- #
#  Fileless / bootkit / supply chain
# --------------------------------------------------------------------------- #
FILELESS_PATTERNS = [
    (r"(?i)powershell(?:\.exe)?\s+.*-(?:enc|encodedcommand)\s+[A-Za-z0-9+/=]{40,}",
     "high", "Base64-encoded PowerShell", "T1059.001"),
    (r"(?i)powershell\s+.*(?:iex|invoke-expression).*(?:downloadstring|invoke-webrequest|net\.webclient)",
     "critical", "In-memory PowerShell download cradle", "T1059.001"),
    (r"(?i)mshta\s+(?:https?://|javascript:|vbscript:)", "high", "MSHTA remote script", "T1218.005"),
    (r"(?i)regsvr32\s+.*(?:/i:https?://|scrobj\.dll)", "high", "Squiblydoo scriptlet", "T1218.010"),
    (r"(?i)rundll32\s+.*(?:javascript:|https?://)", "high", "Rundll32 script execution", "T1218.011"),
    (r"(?i)wmic\s+(?:process|/node:).*call\s+create", "high", "WMI process creation", "T1047"),
    (r"(?i)powershell\s+.*(?:reflection\.assembly|frombase64string|byte\[\])",
     "critical", "Reflective assembly load", "T1620"),
    (r"(?i)(?:certutil|bitsadmin)\s+.*(?:-urlcache|-decode|/transfer|/addfile)",
     "high", "LOLBin download/decode", "T1105"),
    (r"(?i)wscript\.shell|createobject\(\s*\"wscript", "medium", "WSH COM execution", "T1059.005"),
    (r"(?i)\.net\.webclient\)?\.(?:downloadstring|downloadfile)", "high", "WebClient download", "T1105"),
    (r"(?i)register-scheduledtask\s+.*-action", "medium", "Scheduled task via PowerShell", "T1053.005"),
    (r"(?i)invoke-command\s+-scriptblock", "medium", "PowerShell remoting", "T1021.006"),
]


def analyze_fileless(text: str, filename: str = "") -> Dict[str, Any]:
    findings = []
    for pattern, severity, label, tech in FILELESS_PATTERNS:
        for m in re.finditer(pattern, text):
            findings.append({"severity": severity, "finding": label,
                             "mitre": [tech],
                             "evidence": text[max(0, m.start() - 40):m.end() + 40][:240]})
    encoded = []
    for m in re.finditer(r"(?i)-e(?:nc(?:odedcommand)?)?\s+([A-Za-z0-9+/=]{32,})", text):
        blob = m.group(1)
        try:
            import base64
            decoded = base64.b64decode(blob + "=" * (-len(blob) % 4)).decode("utf-16le", "replace")
            encoded.append({"encoded": blob[:80], "decoded": decoded[:400]})
        except Exception:
            continue
    if encoded:
        findings.append({"severity": "high", "finding": f"{len(encoded)} encoded PowerShell payload(s)",
                         "mitre": ["T1059.001", "T1140"], "evidence": encoded[:5]})
    findings = _dedupe(findings)
    return {"filename": filename, "findings": findings, "count": len(findings),
            "decoded_payloads": encoded[:20],
            "verdict": "fileless execution indicators" if findings else "no fileless indicators",
            "score": min(100, sum({"critical": 25, "high": 15, "medium": 7, "low": 3}.get(f["severity"], 0)
                                  for f in findings))}


def analyze_bootkit(data: bytes, filename: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {"filename": filename, "size": len(data),
                           "findings": [], "hashes": hash_bytes(data)}
    ftype = file_type(data, filename)
    out["type"] = ftype["type"]
    if ftype["type"] == "MBR/boot sector":
        parts = ftype["details"].get("partition_entries", [])
        out["partition_table"] = parts
        code = data[0:446]
        if re.search(rb"(?i)(GRUB|LILO|BOOTMGR|NTLDR|SYSLINUX)", code):
            out["bootloader"] = re.search(rb"(?i)(GRUB|LILO|BOOTMGR|NTLDR|SYSLINUX)", code).group().decode()
        nonzero = sum(1 for b in code if b)
        out["code_bytes_nonzero"] = nonzero
        if any(p.get("type") == "0xee" for p in parts):
            out["findings"].append({"severity": "info", "finding": "GPT protective MBR"})
        if nonzero > 200 and not out.get("bootloader"):
            out["findings"].append({"severity": "medium",
                                    "finding": "unrecognized boot code in MBR (verify integrity)"})
        if len(data) >= 512 and data[510:512] != b"\x55\xaa":
            out["findings"].append({"severity": "high", "finding": "missing 0x55AA boot signature"})
    # UEFI / firmware volume hints
    if b"_FVH" in data[:4096] or data[:4] == b"\x00\x00\x00\x00" and b"FVH" in data[:64]:
        out["findings"].append({"severity": "info", "finding": "UEFI firmware volume header"})
    if data[:4] == b"$SB" or b"$SB" in data[:64]:
        out["findings"].append({"severity": "info", "finding": "UEFI Secure Boot variable store"})
    if b"dbx" in data[:4096] and b"PK" in data[:4096]:
        out["findings"].append({"severity": "info", "finding": "Secure Boot DBX database"})
    strings = list(dict.fromkeys(re.findall(r"[ -~]{6,120}", data[:1 << 20].decode("latin-1", "ignore"))))
    out["strings_sample"] = [s for s in strings if re.search(
        r"(?i)(boot|efi|uefi|ntfs|partition|mbr|vbr|secure|dbx|kek|pk|windows|system32)", s)][:200]
    if not out["findings"]:
        out["findings"].append({"severity": "info", "finding": "no clear bootkit indicators"})
    return out


def analyze_supply_chain(text: str, filename: str = "") -> Dict[str, Any]:
    """Script/package-manager supply-chain review."""
    findings = []
    scripts = re.findall(r'"(?:preinstall|install|postinstall|prepare)"\s*:\s*"([^"]+)"', text)
    for s in scripts:
        if re.search(r"(?i)(curl|wget|http|eval|base64|node -e|python -c|powershell)", s):
            findings.append({"severity": "critical", "finding": "install script fetches/executes remote code",
                             "evidence": s[:240]})
    if re.search(r"(?i)https?://[^\s\"']+\.(?:sh|ps1|exe|bat|js)\b", text):
        findings.append({"severity": "high", "finding": "remote script/binary URL in package manifest"})
    if re.search(r"(?i)(?:npm|yarn|pip|gem)\s+install\s+[^\n]*--(?:unsafe-perm|trusted-host|index-url\s+http)",
                 text):
        findings.append({"severity": "high", "finding": "insecure package-install flags"})
    if re.search(r"(?im)sudo\s+(?:npm|pip|gem)\s+install", text):
        findings.append({"severity": "high", "finding": "package install with sudo (privilege risk)"})
    if re.search(r"(?i)curl[^\n]*\|\s*(?:sudo\s+)?(?:bash|sh)", text):
        findings.append({"severity": "critical", "finding": "curl | sh remote execution"})
    if re.search(r"(?i)chmod\s+\+x\s+[^\n]*&&\s*\./", text):
        findings.append({"severity": "medium", "finding": "download, chmod +x, execute chain"})
    if re.search(r"(?i)source\s+https?://", text):
        findings.append({"severity": "high", "finding": "sourcing remote script"})
    lockless = not any(k in Path(filename).name.lower() for k in
                       ("lock", "requirements", "go.sum", "packages.config", "gemfile.lock"))
    secrets = scan_secrets(text, filename)
    if secrets["count"]:
        findings.append({"severity": "critical", "finding": f"{secrets['count']} secret(s) in build files"})
    findings = _dedupe(findings)
    return {"filename": filename, "findings": findings, "count": len(findings),
            "install_scripts": scripts[:10],
            "lockfile_hint": "no lockfile hint" if lockless else "lockfile-like filename",
            "verdict": "supply-chain risk" if findings else "no obvious supply-chain risk",
            "score": min(100, sum({"critical": 25, "high": 15, "medium": 7, "low": 3}.get(f["severity"], 0)
                                  for f in findings))}
