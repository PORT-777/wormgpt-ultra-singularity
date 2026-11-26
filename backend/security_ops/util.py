# backend/security_ops/util.py
# Language: Python 3 | Runtime: CPython | Target: Windows 11 / Linux
# Shared helpers for the CyberOps toolkit: sandboxed I/O, hashing, entropy,
# strings, file-type detection, IOC extraction and small data utilities.

from __future__ import annotations

import base64
import binascii
import datetime as _dt
import difflib
import gzip
import hashlib
import ipaddress
import json
import math
import os
import re
import struct
import zlib
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import configs as config
except Exception:  # pragma: no cover - import path differs in some tests
    config = None

BACKEND_DIR = Path(__file__).resolve().parents[1]
WORKSPACE = Path(getattr(config, "WORKSPACE_DIR", BACKEND_DIR / "workspace"))
REPORTS_DIR = WORKSPACE / "reports"
IOC_DIR = WORKSPACE / "iocs"
CASES_DIR = WORKSPACE / "cases"
MAX_BYTES = 64 * 1024 * 1024
MAX_TEXT = 2_000_000

# Windows path characters that would let a name escape the reports folder.
_BAD_NAME = re.compile(r"[^A-Za-z0-9._-]+")


# --------------------------------------------------------------------------- #
#  Paths / I/O
# --------------------------------------------------------------------------- #
def resolve_path(path: str, allow_host: bool = False, must_exist: bool = True) -> Path:
    """Resolve *path* under the workspace unless host access is allowed.

    The agent tool passes ``allow_host=True`` only in Full Access mode. The
    HTTP API never does, so remote callers stay inside the workspace.
    """
    raw = str(path or "").strip().strip('"').strip("'")
    if not raw:
        raise ValueError("empty path")
    raw = os.path.expandvars(os.path.expanduser(raw))
    p = Path(raw)
    if not p.is_absolute():
        p = WORKSPACE / raw.lstrip("/\\")
    p = p.resolve()
    if not allow_host:
        root = WORKSPACE.resolve()
        if p != root and root not in p.parents:
            raise ValueError(f"path '{path}' escapes the workspace sandbox")
    if must_exist and not p.exists():
        raise FileNotFoundError(f"not found: {path}")
    return p


def read_limited(path: Path, limit: int = MAX_BYTES) -> bytes:
    if path.is_dir():
        raise IsADirectoryError(str(path))
    size = path.stat().st_size
    if size > limit:
        raise ValueError(f"file is {size} bytes; limit is {limit} bytes")
    return path.read_bytes()


def bytes_from_kwargs(kw: Dict[str, Any], allow_host: bool = False,
                      limit: int = MAX_BYTES) -> Tuple[bytes, str]:
    """Return (data, source_label) from path/hex/base64/text keys."""
    if kw.get("path"):
        p = resolve_path(str(kw["path"]), allow_host=allow_host)
        return read_limited(p, limit), str(p)
    if kw.get("hex") is not None:
        return decode_hex(str(kw["hex"])), "<hex>"
    if kw.get("base64"):
        return b64decode_loose(str(kw["base64"])), "<base64>"
    if kw.get("text") is not None:
        return str(kw["text"]).encode("utf-8", "replace"), "<text>"
    if kw.get("data") is not None:
        data = kw["data"]
        if isinstance(data, bytes):
            return data[:limit], "<bytes>"
        return str(data).encode("utf-8", "replace")[:limit], "<data>"
    raise ValueError("provide one of: path, hex, base64, text, data")


def text_from_kwargs(kw: Dict[str, Any], allow_host: bool = False,
                     limit: int = MAX_TEXT) -> Tuple[str, str]:
    if kw.get("path"):
        p = resolve_path(str(kw["path"]), allow_host=allow_host)
        raw = read_limited(p, min(limit, MAX_BYTES))
        for enc in ("utf-8", "utf-16", "latin-1"):
            try:
                return raw.decode(enc), str(p)
            except Exception:
                continue
        return raw.decode("latin-1", "replace"), str(p)
    for key in ("text", "content", "data"):
        if kw.get(key) is not None:
            return str(kw[key])[:limit], f"<{key}>"
    if kw.get("hex") is not None:
        return decode_hex(str(kw["hex"])).decode("latin-1", "replace"), "<hex>"
    if kw.get("base64"):
        return b64decode_loose(str(kw["base64"])).decode("latin-1", "replace"), "<base64>"
    raise ValueError("provide one of: path, text, content, data, hex, base64")


def safe_name(name: str, fallback: str = "artifact") -> str:
    name = Path(str(name or "")).name
    name = _BAD_NAME.sub("_", name).strip("._")
    return name[:120] or fallback


def write_artifact(filename: str, content: Any, kind: str = "reports",
                   allow_host: bool = False) -> str:
    """Write generated output (reports, rules, IOC bundles) and return path."""
    if isinstance(content, bytes):
        payload = content
    else:
        payload = str(content).encode("utf-8")
    p = Path(str(filename or "artifact.txt"))
    if p.is_absolute():
        if not allow_host:
            p = WORKSPACE / kind / p.name
    else:
        base = WORKSPACE / kind
        p = base / p
    p = p.resolve()
    if not allow_host:
        root = WORKSPACE.resolve()
        if p != root and root not in p.parents:
            p = root / kind / p.name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(payload)
    return str(p)


def json_dumps(obj: Any, indent: int = 2) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=indent, default=_json_default)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (bytes, bytearray)):
        return bytes(obj).hex()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (set, tuple)):
        return list(obj)
    if isinstance(obj, _dt.datetime):
        return obj.isoformat()
    return str(obj)


# --------------------------------------------------------------------------- #
#  Encoding helpers
# --------------------------------------------------------------------------- #
def decode_hex(value: str) -> bytes:
    s = re.sub(r"(?i)0x", "", value)
    s = re.sub(r"[^0-9a-fA-F]", "", s)
    if len(s) % 2:
        s = "0" + s
    return bytes.fromhex(s)


def b64decode_loose(value: str) -> bytes:
    s = re.sub(r"\s+", "", value)
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s, validate=False)


def b64encode(data: bytes, urlsafe: bool = False) -> str:
    return (base64.urlsafe_b64encode(data) if urlsafe else base64.b64encode(data)).decode()


def try_decompress(data: bytes) -> Tuple[Optional[bytes], str]:
    for name, fn in (
        ("gzip", lambda d: gzip.decompress(d)),
        ("zlib", lambda d: zlib.decompress(d)),
        ("raw-deflate", lambda d: zlib.decompress(d, -15)),
    ):
        try:
            out = fn(data)
            if out:
                return out, name
        except Exception:
            pass
    return None, ""


# --------------------------------------------------------------------------- #
#  Hashing / entropy / similarity
# --------------------------------------------------------------------------- #
def hash_bytes(data: bytes) -> Dict[str, Any]:
    return {
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "sha512": hashlib.sha512(data).hexdigest(),
        "crc32": f"{binascii.crc32(data) & 0xffffffff:08x}",
        "size": len(data),
        "entropy": round(entropy(data), 3),
        "ctph": ctph(data),
    }


def hash_path(path: Path) -> Dict[str, Any]:
    h = {"md5": hashlib.md5(), "sha1": hashlib.sha1(),
         "sha256": hashlib.sha256(), "sha512": hashlib.sha512()}
    crc = 0
    size = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            crc = binascii.crc32(chunk, crc)
            for hh in h.values():
                hh.update(chunk)
    out = {k: v.hexdigest() for k, v in h.items()}
    out.update({"crc32": f"{crc & 0xffffffff:08x}", "size": size, "path": str(path)})
    return out


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = float(len(data))
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def entropy_map(data: bytes, block: int = 256, max_blocks: int = 512) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    total = max(1, (len(data) + block - 1) // block)
    step = max(1, math.ceil(total / max_blocks)) if total > max_blocks else 1
    for idx, off in enumerate(range(0, len(data), block)):
        if idx % step and idx != total - 1:
            continue
        chunk = data[off:off + block]
        blocks.append({"offset": off, "size": len(chunk),
                       "entropy": round(entropy(chunk), 3)})
    return blocks


def high_entropy_regions(data: bytes, threshold: float = 7.0,
                         block: int = 256, min_run: int = 4) -> List[Dict[str, Any]]:
    em = entropy_map(data, block=block, max_blocks=100000)
    runs: List[Dict[str, Any]] = []
    start = None
    for item in em:
        if item["entropy"] >= threshold:
            if start is None:
                start = item["offset"]
        elif start is not None:
            if (item["offset"] - start) >= block * min_run:
                runs.append({"start": start, "end": item["offset"],
                             "size": item["offset"] - start})
            start = None
    if start is not None and (len(data) - start) >= block * min_run:
        runs.append({"start": start, "end": len(data), "size": len(data) - start})
    return runs


def ctph(data: bytes, min_block: int = 64) -> str:
    """Context-triggered piecewise hash (ssdeep-like, not byte-compatible)."""
    if not data:
        return "0:"
    block = min_block
    while block < 65536 and len(data) / block > 64:
        block *= 2
    rolling = 0
    window: List[int] = []
    pieces: List[str] = []
    for byte in data:
        window.append(byte)
        rolling = ((rolling << 5) ^ byte) & 0xFFFFFFFF
        if len(window) > 7:
            rolling ^= window.pop(0)
        if rolling % (block * 4) == (block * 4 - 1):
            pieces.append(_b64char(rolling & 63))
            rolling = 0
    pieces.append(_b64char(rolling & 63))
    sig = "".join(pieces)
    return f"{block}:{sig[:128]}"


def _b64char(v: int) -> str:
    return "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[v & 63]


def fuzzy_compare(a: str, b: str) -> int:
    if not a or not b:
        return 0
    if a == b:
        return 100
    return int(round(difflib.SequenceMatcher(None, a, b).ratio() * 100))


def data_similarity(a: bytes, b: bytes) -> Dict[str, Any]:
    import random
    if not a or not b:
        return {"score": 0}
    sa, sb = ctph(a), ctph(b)
    same = sum(1 for x, y in zip(a[:200000], b[:200000]) if x == y)
    n = min(len(a), len(b), 200000)
    byte_ratio = same / n if n else 0
    # function-chunk overlap: hash every 64-byte block, compare sampled sets
    ca = {hashlib.sha1(a[i:i + 64]).hexdigest()[:12] for i in range(0, len(a) - 64, 64)}
    cb = {hashlib.sha1(b[i:i + 64]).hexdigest()[:12] for i in range(0, len(b) - 64, 64)}
    overlap = len(ca & cb) / max(1, len(ca | cb))
    score = int(round((fuzzy_compare(sa, sb) * 0.35 + byte_ratio * 100 * 0.25 + overlap * 100 * 0.4)))
    return {"score": score, "ctph_a": sa, "ctph_b": sb,
            "byte_ratio": round(byte_ratio, 4), "chunk_jaccard": round(overlap, 4)}


# --------------------------------------------------------------------------- #
#  Strings
# --------------------------------------------------------------------------- #
def ascii_strings(data: bytes, min_len: int = 4, limit: int = 20000) -> List[str]:
    rx = re.compile(rb"[\x20-\x7e]{%d,}" % max(1, min_len))
    out: List[str] = []
    for m in rx.finditer(data):
        out.append(m.group().decode("latin-1"))
        if len(out) >= limit:
            break
    return out


def unicode_strings(data: bytes, min_len: int = 4, limit: int = 20000) -> List[str]:
    rx = re.compile((rb"(?:[\x20-\x7e]\x00){%d,}" % max(1, min_len)))
    out: List[str] = []
    for m in rx.finditer(data):
        out.append(m.group().decode("utf-16le", "ignore"))
        if len(out) >= limit:
            break
    return out


def extract_strings(data: bytes, min_len: int = 4, both: bool = True,
                    unique: bool = True, limit: int = 20000) -> Dict[str, Any]:
    a = ascii_strings(data, min_len, limit)
    u = unicode_strings(data, min_len, limit) if both else []
    if unique:
        a = list(dict.fromkeys(a))
        u = list(dict.fromkeys(u))
    return {"ascii": a[:limit], "unicode": u[:limit],
            "counts": {"ascii": len(a), "unicode": len(u)}}


# --------------------------------------------------------------------------- #
#  File type detection
# --------------------------------------------------------------------------- #
_MACHINES = {
    0x014C: ("x86", 32), 0x8664: ("x86-64", 64), 0x01C0: ("ARM", 32),
    0x01C4: ("ARMv7", 32), 0xAA64: ("ARM64", 64), 0x0200: ("IA-64", 64),
    0x5032: ("RISC-V", 32), 0x5064: ("RISC-V", 64), 0x0000: ("unknown", 0),
}
_ELF_MACHINES = {
    3: "x86", 62: "x86-64", 40: "ARM", 183: "ARM64", 8: "MIPS",
    20: "PowerPC", 21: "PowerPC64", 243: "RISC-V", 22: "S390",
}


def file_type(data: bytes, name: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {"type": "data", "mime": "application/octet-stream",
                           "platform": "unknown", "arch": "unknown", "bits": 0,
                           "confidence": 40, "details": {}}
    if not data:
        out.update(type="empty", mime="inode/x-empty", confidence=100)
        return out
    head = data[:16]
    ext = Path(name).suffix.lower().lstrip(".")

    if head[:2] == b"MZ":
        pe = _pe_meta(data)
        out.update(type=pe.get("type", "PE"), mime="application/vnd.microsoft.portable-executable",
                   platform="Windows", arch=pe.get("arch", "unknown"),
                   bits=pe.get("bits", 0), confidence=99, details=pe)
        return out
    if head[:4] == b"\x7fELF":
        cls = data[4] if len(data) > 4 else 1
        endian = "<" if (len(data) > 5 and data[5] == 1) else ">"
        machine = struct.unpack_from(endian + "H", data, 18)[0] if len(data) >= 20 else 0
        out.update(type="ELF", mime="application/x-elf", platform="Linux/Unix",
                   arch=_ELF_MACHINES.get(machine, f"machine-{machine}"),
                   bits=64 if cls == 2 else 32, confidence=99,
                   details={"machine": machine, "class": cls,
                            "endian": "little" if endian == "<" else "big",
                            "osabi": data[7] if len(data) > 7 else 0})
        return out
    if head[:4] in (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe",
                    b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe"):
        magic = head[:4]
        bits = 64 if magic in (b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe") else 32
        out.update(type=f"Mach-O {bits}-bit", mime="application/x-mach-binary",
                   platform="macOS/iOS", bits=bits,
                   arch=_macho_arch(data), confidence=99)
        return out
    if head[:4] in (b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
        out.update(type="Mach-O Universal", mime="application/x-mach-binary",
                   platform="macOS/iOS", bits=64 if head[:4].endswith(b"\xbf") else 32,
                   arch="fat", confidence=99)
        return out
    if head[:4] == b"PK\x03\x04":
        return _zip_type(data, name, out)
    if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        out.update(type="OLE Compound File", mime="application/x-ole-storage",
                   platform="Windows", confidence=98,
                   details={"likely": _ole_guess(data)})
        return out
    if head[:4] == b"%PDF":
        out.update(type="PDF", mime="application/pdf", confidence=99,
                   details={"version": data[5:8].decode("latin-1", "ignore")})
        return out
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        out.update(type="PNG", mime="image/png", confidence=99)
        return out
    if head[:3] == b"\xff\xd8\xff":
        out.update(type="JPEG", mime="image/jpeg", confidence=99)
        return out
    if head[:6] in (b"GIF87a", b"GIF89a"):
        out.update(type="GIF", mime="image/gif", confidence=99)
        return out
    if head[:4] == b"RIFF":
        fmt = data[8:12]
        m = {b"WAVE": ("WAV", "audio/wav"), b"AVI ": ("AVI", "video/x-msvideo"),
             b"WEBP": ("WebP", "image/webp")}.get(fmt, ("RIFF", "application/riff"))
        out.update(type=m[0], mime=m[1], confidence=95)
        return out
    if head[:3] == b"ID3" or head[:2] in (b"\xff\xfb", b"\xff\xf3"):
        out.update(type="MP3", mime="audio/mpeg", confidence=90)
        return out
    if head[:4] == b"OggS":
        out.update(type="OGG", mime="audio/ogg", confidence=95)
        return out
    if head[:4] == b"fLaC":
        out.update(type="FLAC", mime="audio/flac", confidence=95)
        return out
    if head[:6] == b"7z\xbc\xaf\x27\x1c":
        out.update(type="7-Zip", mime="application/x-7z-compressed", confidence=99)
        return out
    if head[:4] == b"Rar!":
        out.update(type="RAR", mime="application/vnd.rar", confidence=99)
        return out
    if head[:2] == b"\x1f\x8b":
        out.update(type="gzip", mime="application/gzip", confidence=99)
        return out
    if head[:3] == b"BZh":
        out.update(type="bzip2", mime="application/x-bzip2", confidence=99)
        return out
    if head[:6] == b"\xfd7zXZ\x00":
        out.update(type="XZ", mime="application/x-xz", confidence=99)
        return out
    if head[:4] == b"\x28\xb5\x2f\xfd":
        out.update(type="Zstandard", mime="application/zstd", confidence=99)
        return out
    if data[257:262] == b"ustar":
        out.update(type="tar", mime="application/x-tar", confidence=99)
        return out
    if head[:4] in (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4"):
        out.update(type="PCAP", mime="application/vnd.tcpdump.pcap", confidence=99)
        return out
    if head[:4] == b"\x0a\x0d\x0d\x0a":
        out.update(type="PCAPNG", mime="application/x-pcapng", confidence=99)
        return out
    if head[:16] == b"SQLite format 3\x00":
        out.update(type="SQLite", mime="application/vnd.sqlite3", confidence=99)
        return out
    if head[:4] == b"dex\n":
        out.update(type="Dalvik DEX", mime="application/x-dex", platform="Android",
                   confidence=99)
        return out
    if head[:4] == b"\x00asm":
        out.update(type="WebAssembly", mime="application/wasm", confidence=99)
        return out
    if head[:4] == b"L\x00\x00\x00" and ext == "lnk":
        out.update(type="Windows LNK", mime="application/x-ms-shortcut",
                   platform="Windows", confidence=99)
        return out
    if head[:4] == b"\x03\x00\x00\x00" and name.lower().endswith(".lnk"):
        out.update(type="Windows LNK", mime="application/x-ms-shortcut",
                   platform="Windows", confidence=80)
        return out
    if data[510:512] == b"\x55\xaa" and len(data) >= 512:
        out.update(type="MBR/boot sector", mime="application/octet-stream",
                   platform="bare-metal", confidence=85,
                   details={"partition_entries": _mbr_parts(data)})
        return out
    if head[:4] == b"hsqs":
        out.update(type="SquashFS", mime="application/octet-stream",
                   platform="embedded", confidence=95)
        return out
    if head[:4] == b"\x45\x3d\xcd\x28":
        out.update(type="CramFS", mime="application/octet-stream",
                   platform="embedded", confidence=90)
        return out
    if head[:3] == b"UBI":
        out.update(type="UBI image", mime="application/octet-stream",
                   platform="embedded", confidence=95)
        return out
    if head[:2] == b"\x85\x19":
        out.update(type="JFFS2", mime="application/octet-stream",
                   platform="embedded", confidence=85)
        return out
    if head[:5] == b"CD001" or data[32769:32774] == b"CD001":
        out.update(type="ISO 9660", mime="application/x-iso9660-image", confidence=90)
        return out
    if head[:4] in (b"KDMV", b"# Disk"):
        out.update(type="VMDK", mime="application/octet-stream", confidence=85)
        return out
    if head[:4] == b"QFI\xfb":
        out.update(type="QCOW", mime="application/octet-stream", confidence=95)
        return out
    # textual formats
    sample = data[:4096]
    if ext in ("ps1", "psm1", "bat", "cmd", "vbs", "js", "jse", "wsf", "hta",
               "py", "sh", "php", "jsp", "asp", "aspx", "sql", "yml", "yaml",
               "json", "xml", "html", "htm", "css", "md", "txt", "log", "csv"):
        out.update(type=f"{ext.upper()} text", mime="text/plain",
                   confidence=70, details={"encoding": _text_encoding(sample)})
        return out
    if b"\x00" not in sample and _printable_ratio(sample) > 0.9:
        out.update(type="text", mime="text/plain", confidence=65,
                   details={"encoding": _text_encoding(sample)})
        return out
    return out


def _pe_meta(data: bytes) -> Dict[str, Any]:
    if len(data) < 0x40:
        return {"type": "MZ (truncated)"}
    off = struct.unpack_from("<I", data, 0x3C)[0]
    if off + 24 > len(data) or data[off:off + 4] != b"PE\x00\x00":
        return {"type": "MZ (no PE header)", "pe_offset": off}
    machine, nsect, ts, _, _, opt_size, chars = struct.unpack_from("<HHIIIHH", data, off + 4)
    magic = struct.unpack_from("<H", data, off + 24)[0] if off + 26 <= len(data) else 0
    bits = 64 if magic == 0x20B else 32
    arch = _MACHINES.get(machine, (f"machine-{machine}", bits))[0]
    return {"type": f"PE{'' if bits == 32 else '32+'}", "arch": arch, "bits": bits,
            "pe_offset": off, "sections": nsect, "timestamp": ts,
            "characteristics": chars, "optional_magic": hex(magic)}


def _macho_arch(data: bytes) -> str:
    try:
        cpu = struct.unpack_from("<I", data, 4)[0]
        return {7: "x86", 0x01000007: "x86-64", 12: "ARM",
                0x0100000C: "ARM64", 18: "PowerPC", 0x01000012: "PowerPC64"}.get(cpu, f"cpu-{cpu}")
    except Exception:
        return "unknown"


def _zip_type(data: bytes, name: str, out: Dict[str, Any]) -> Dict[str, Any]:
    import io
    import zipfile
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        low = [n.lower() for n in names]
        if "androidmanifest.xml" in low and any(n.endswith(".dex") for n in low):
            out.update(type="APK", mime="application/vnd.android.package-archive",
                       platform="Android", confidence=99,
                       details={"entries": len(names)})
            return out
        if any(n.startswith("payload/") for n in low) and any(n.endswith(".app/") for n in low):
            out.update(type="IPA", mime="application/octet-stream",
                       platform="iOS", confidence=95,
                       details={"entries": len(names)})
            return out
        if "[content_types].xml" in low:
            if any(n.startswith("word/") for n in low):
                out.update(type="DOCX", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           confidence=99)
            elif any(n.startswith("xl/") for n in low):
                out.update(type="XLSX", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           confidence=99)
            elif any(n.startswith("ppt/") for n in low):
                out.update(type="PPTX", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                           confidence=99)
            else:
                out.update(type="OOXML", mime="application/zip", confidence=95)
            return out
        if any(n.endswith(".class") for n in low) or "meta-inf/manifest.mf" in low:
            out.update(type="JAR", mime="application/java-archive", platform="Java",
                       confidence=95, details={"entries": len(names)})
            return out
        out.update(type="ZIP", mime="application/zip", confidence=99,
                   details={"entries": len(names), "top": names[:20]})
        return out
    except Exception:
        out.update(type="ZIP (corrupt/truncated)", mime="application/zip", confidence=60)
        return out


def _ole_guess(data: bytes) -> str:
    low = data[:65536].lower()
    if b"worddocument" in low or b"msword" in low:
        return "Word document"
    if b"workbook" in low or b"excel" in low:
        return "Excel workbook"
    if b"powerpoint" in low:
        return "PowerPoint presentation"
    if b"msi" in low:
        return "MSI installer"
    return "OLE document"


def _printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    printable = sum(1 for b in data if 9 <= b <= 13 or 32 <= b <= 126)
    return printable / len(data)


def _text_encoding(sample: bytes) -> str:
    if sample.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if sample.startswith(b"\xff\xfe") or sample.startswith(b"\xfe\xff"):
        return "utf-16"
    try:
        sample.decode("utf-8")
        return "utf-8"
    except Exception:
        return "latin-1"


def _mbr_parts(data: bytes) -> List[Dict[str, Any]]:
    parts = []
    for i in range(4):
        off = 446 + i * 16
        ent = data[off:off + 16]
        if len(ent) < 16:
            continue
        boot, ptype = ent[0], ent[4]
        lba, count = struct.unpack_from("<II", ent, 8)
        if ptype:
            parts.append({"index": i + 1, "bootable": boot == 0x80,
                          "type": f"0x{ptype:02x}", "lba": lba, "sectors": count})
    return parts


# --------------------------------------------------------------------------- #
#  IOC extraction
# --------------------------------------------------------------------------- #
_DEFANG = [
    (re.compile(r"\[\.\]|\(\.\)|\{\.\}|\[dot\]|\(dot\)|\{dot\}", re.I), "."),
    (re.compile(r"hxxps?", re.I), lambda m: "https" if m.group().lower().endswith("s") else "http"),
    (re.compile(r"fxp://", re.I), "ftp://"),
]
_TLDS = (
    "com|net|org|io|dev|co|gov|edu|info|biz|ru|cn|ir|sa|ae|eg|uk|de|fr|nl|"
    "br|in|jp|kr|au|ca|us|app|xyz|top|online|site|club|shop|cloud|tech|pro|"
    "me|tv|cc|ly|to|ws|su|onion|local|lan|internal|shop|store|blog|live|"
    "support|help|link|click|download|zip|mov|rest|icu|monster|quest|buzz|"
    "cyou|bar|sbs|cfd|bond|best|life|world|space|website|fun|host|press"
)
_DOMAIN_RE = re.compile(
    r"(?<![\w@.-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:" + _TLDS + r")(?![\w.-])",
    re.I,
)
_URL_RE = re.compile(r"\b(?:https?|ftp)://[^\s<>\"'`\]\}]+", re.I)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b")
_IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_IPV6_RE = re.compile(r"(?<![:0-9a-f])(?:[0-9a-f]{1,4}:){2,7}[0-9a-f]{1,4}(?![:0-9a-f])", re.I)
_HASH_RE = re.compile(r"\b(?:[0-9a-fA-F]{128}|[0-9a-fA-F]{64}|[0-9a-fA-F]{40}|[0-9a-fA-F]{32})\b")
_CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)
_REG_RE = re.compile(r"\b(?:HKLM|HKCU|HKCR|HKU|HKCC|HKEY_[A-Z_]+)\\[^\s\"'<>|]+", re.I)
_WINPATH_RE = re.compile(r"\b[A-Za-z]:\\(?:[^\\\s\"'<>|:*?]+\\)*[^\\\s\"'<>|:*?]*")
_UNC_RE = re.compile(r"\\\\[A-Za-z0-9._-]+\\[^\s\"'<>|]+")
_UNIXPATH_RE = re.compile(r"(?<!\w)/(?:etc|tmp|var|usr|opt|home|root|bin|sbin|dev|proc)/[^\s\"'<>|]+")
_MUTEX_RE = re.compile(r"\b(?:Global|Local)\\[A-Za-z0-9_.:{}-]{3,}", re.I)
_BTC_RE = re.compile(r"\b(?:bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_PEM_RE = re.compile(r"-----BEGIN [A-Z ]+-----[\s\S]{20,}?-----END [A-Z ]+-----")
_B64_RE = re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b")


def refang(text: str) -> str:
    out = text
    for rx, repl in _DEFANG:
        out = rx.sub(repl, out)
    return out


def defang(text: str) -> str:
    text = re.sub(r"(?i)https?", lambda m: "hxxp" + ("s" if m.group().lower().endswith("s") else ""), text)
    return text.replace(".", "[.]")


def extract_iocs(text: str, defanged: bool = False) -> Dict[str, Any]:
    raw = refang(text or "")
    cats: Dict[str, List[str]] = {
        "urls": [], "domains": [], "ipv4": [], "ipv6": [], "emails": [],
        "hashes": [], "cves": [], "registry": [], "windows_paths": [],
        "unc_paths": [], "unix_paths": [], "mutexes": [], "wallets": [],
        "jwts": [], "pem": [], "base64_blobs": [],
    }

    def add(cat: str, value: str) -> None:
        value = value.strip().rstrip(".,;:)]}>'\"")
        if value and value not in cats[cat]:
            cats[cat].append(value)

    for m in _URL_RE.finditer(raw):
        add("urls", m.group())
    for m in _EMAIL_RE.finditer(raw):
        add("emails", m.group())
    for m in _IPV4_RE.finditer(raw):
        try:
            ipaddress.IPv4Address(m.group())
            add("ipv4", m.group())
        except ValueError:
            pass
    for m in _IPV6_RE.finditer(raw):
        try:
            ip = ipaddress.IPv6Address(m.group())
            if not ip.ipv4_mapped:
                add("ipv6", m.group())
        except ValueError:
            pass
    for m in _DOMAIN_RE.finditer(raw):
        add("domains", m.group().lower())
    for m in _HASH_RE.finditer(raw):
        add("hashes", m.group().lower())
    for m in _CVE_RE.finditer(raw):
        add("cves", m.group().upper())
    for m in _REG_RE.finditer(raw):
        add("registry", m.group())
    for m in _WINPATH_RE.finditer(raw):
        add("windows_paths", m.group())
    for m in _UNC_RE.finditer(raw):
        add("unc_paths", m.group())
    for m in _UNIXPATH_RE.finditer(raw):
        add("unix_paths", m.group())
    for m in _MUTEX_RE.finditer(raw):
        add("mutexes", m.group())
    for m in _BTC_RE.finditer(raw):
        add("wallets", m.group())
    for m in _JWT_RE.finditer(raw):
        add("jwts", m.group())
    for m in _PEM_RE.finditer(raw):
        add("pem", m.group())
    for m in _B64_RE.finditer(raw):
        if len(m.group()) >= 64 and not _is_probably_hash(m.group()):
            add("base64_blobs", m.group())
    if defanged:
        for k in list(cats):
            if k in ("urls", "domains", "ipv4", "ipv6", "emails"):
                cats[k] = [defang(x) for x in cats[k]]
    total = sum(len(v) for v in cats.values())
    return {"count": total, "categories": cats,
            "summary": {k: len(v) for k, v in cats.items() if v}}


def _is_probably_hash(s: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]+", s)) and len(s) in (32, 40, 64, 128)


def ioc_export_payload(iocs: Dict[str, Any], fmt: str = "json",
                       source: str = "") -> Tuple[str, str]:
    """Build an export bundle; returns (filename, content)."""
    cats = iocs.get("categories", iocs)
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    flat: List[Dict[str, Any]] = []
    kind_map = {
        "urls": "url", "domains": "domain", "ipv4": "ipv4", "ipv6": "ipv6",
        "emails": "email", "hashes": "file", "cves": "vulnerability",
        "registry": "registry-key", "windows_paths": "file-path",
        "unix_paths": "file-path", "mutexes": "mutex", "wallets": "cryptocurrency",
        "jwts": "token", "pem": "x509", "base64_blobs": "artifact",
    }
    for cat, values in cats.items():
        if not isinstance(values, list):
            continue
        for v in values:
            flat.append({"type": kind_map.get(cat, cat), "category": cat, "value": v,
                         "source": source, "confidence": "medium"})
    fmt = (fmt or "json").lower()
    if fmt == "csv":
        import csv
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["type", "category", "value", "source", "confidence"])
        w.writeheader()
        w.writerows(flat)
        return f"iocs_{stamp}.csv", buf.getvalue()
    if fmt == "text":
        lines = [f"# IOCs from {source or 'analysis'} ({stamp} UTC)"]
        for item in flat:
            lines.append(f"{item['type']}: {item['value']}")
        return f"iocs_{stamp}.txt", "\n".join(lines)
    if fmt in ("stix", "stix2.1", "stix2"):
        objects = []
        for item in flat:
            objects.append({
                "type": "indicator", "spec_version": "2.1",
                "id": f"indicator--{hashlib.sha256((item['type']+item['value']).encode()).hexdigest()}",
                "created": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "modified": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "name": f"{item['type']}: {item['value']}",
                "pattern_type": "stix",
                "pattern": _stix_pattern(item["type"], item["value"]),
                "valid_from": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "labels": ["malicious-activity"],
            })
        bundle = {"type": "bundle", "id": f"bundle--{hashlib.sha256(str(flat).encode()).hexdigest()}",
                  "objects": objects}
        return f"iocs_{stamp}_stix.json", json_dumps(bundle)
    if fmt == "misp":
        attrs = []
        misp_type = {
            "url": "url", "domain": "domain", "ipv4": "ip-dst", "ipv6": "ip-dst",
            "email": "email-src", "file": "sha256" if any(
                len(i["value"]) == 64 for i in flat if i["category"] == "hashes") else "filename",
            "registry-key": "regkey", "mutex": "mutex", "x509": "x509-fingerprint-sha256",
        }
        for item in flat:
            t = misp_type.get(item["type"], "text")
            if t == "sha256" and len(item["value"]) != 64:
                t = "sha1" if len(item["value"]) == 40 else "md5"
            attrs.append({"type": t, "category": "Network activity"
                          if item["type"] in ("url", "domain", "ipv4", "ipv6") else "Payload delivery",
                          "value": item["value"], "to_ids": True})
        event = {"Event": {"info": f"CyberOps export {stamp}", "distribution": "0",
                           "threat_level_id": "2", "analysis": "1",
                           "Attribute": attrs}}
        return f"iocs_{stamp}_misp.json", json_dumps(event)
    payload = {"generated": _dt.datetime.now(_dt.timezone.utc)
                       .replace(tzinfo=None).isoformat() + "Z",
               "source": source, "count": len(flat), "indicators": flat,
               "raw": cats}
    return f"iocs_{stamp}.json", json_dumps(payload)


def _stix_pattern(kind: str, value: str) -> str:
    if kind == "ipv4":
        return f"[ipv4-addr:value = '{value}']"
    if kind == "ipv6":
        return f"[ipv6-addr:value = '{value}']"
    if kind == "domain":
        return f"[domain-name:value = '{value}']"
    if kind == "url":
        return f"[url:value = '{value}']"
    if kind == "file":
        h = "SHA-256" if len(value) == 64 else ("SHA-1" if len(value) == 40 else "MD5")
        return f"[file:hashes.'{h}' = '{value}']"
    if kind == "email":
        return f"[email-addr:value = '{value}']"
    if kind == "mutex":
        return f"[mutex:name = '{value}']"
    return f"[artifact:payload_bin = '{value}']"


# --------------------------------------------------------------------------- #
#  Misc utilities
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0
    return f"{n} B"


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def severity_rank(sev: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(str(sev).lower(), 5)


def normalize_severity(sev: str) -> str:
    s = str(sev or "").strip().lower()
    return s if s in ("critical", "high", "medium", "low", "info") else "medium"


def parse_time(value: Any) -> Optional[_dt.datetime]:
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=_dt.timezone.utc)
    if isinstance(value, (int, float)):
        v = float(value)
        if v > 1e18:          # 100ns FILETIME
            v /= 10_000_000
        elif v > 1e14:        # milliseconds
            v /= 1000.0
        try:
            return _dt.datetime.fromtimestamp(v, tz=_dt.timezone.utc)
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    if re.fullmatch(r"\d{10,19}", s):
        return parse_time(int(s))
    s2 = s.replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
                "%d/%b/%Y:%H:%M:%S %z", "%b %d %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            if fmt is None:
                d = _dt.datetime.fromisoformat(s2)
            else:
                parse_s, parse_fmt = s, fmt
                if fmt == "%b %d %H:%M:%S":
                    parse_s = f"{_dt.datetime.now().year} {s}"
                    parse_fmt = "%Y %b %d %H:%M:%S"
                d = _dt.datetime.strptime(parse_s, parse_fmt)
                if d.tzinfo is None and "%z" not in fmt:
                    d = d.replace(tzinfo=_dt.timezone.utc)
            return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)
        except Exception:
            continue
    return None


def fmt_time(d: Optional[_dt.datetime]) -> str:
    return d.astimezone(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC") if d else "unknown"


def tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_.\\/-]{2,}", (text or "").lower())


def contains_any(text: str, needles: Iterable[str]) -> List[str]:
    low = (text or "").lower()
    return [n for n in needles if n and n.lower() in low]


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def truncate_list(items: Sequence[Any], limit: int = 200) -> List[Any]:
    return list(items[:limit])


def flatten_strings(text: str) -> str:
    return " ".join(text.split())


def walk_files(root: Path, suffixes: Optional[Sequence[str]] = None,
               limit: int = 2000) -> List[Path]:
    out: List[Path] = []
    if root.is_file():
        return [root]
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules", ".venv")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if suffixes and p.suffix.lower() not in {s.lower() for s in suffixes}:
                continue
            out.append(p)
            if len(out) >= limit:
                return out
    return out


def table(rows: Sequence[Dict[str, Any]], columns: Optional[Sequence[str]] = None) -> str:
    if not rows:
        return "(no rows)"
    cols = list(columns or rows[0].keys())
    widths = {c: max(len(str(c)), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    head = " | ".join(str(c).ljust(widths[c]) for c in cols)
    sep = "-+-".join("-" * widths[c] for c in cols)
    body = [" | ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols) for r in rows]
    return "\n".join([head, sep, *body])
