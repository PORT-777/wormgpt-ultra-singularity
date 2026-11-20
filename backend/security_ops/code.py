# backend/security_ops/code.py
# Code-level analysis: shellcode, ROP gadgets, crypto signatures, XOR
# recovery, anti-analysis checks, intent prediction, family matching,
# behavioral DNA and cross-sample similarity.

from __future__ import annotations

import base64
import hashlib
import math
import re
import struct
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .knowledge import API_RISK, FAMILIES
from .util import (data_similarity, decode_hex, entropy, extract_strings,
                   file_type, hash_bytes, high_entropy_regions)

try:
    import capstone  # type: ignore
except Exception:  # pragma: no cover
    capstone = None


# --------------------------------------------------------------------------- #
#  Shellcode
# --------------------------------------------------------------------------- #
_SHELLCODE_PATTERNS: List[Dict[str, Any]] = [
    {"name": "PEB access (x86)", "patterns": [b"\x64\x8b\x30", b"\x64\xa1\x30\x00\x00\x00"],
     "meaning": "Reads the Process Environment Block (API resolution)", "severity": "high"},
    {"name": "PEB access (x64)", "patterns": [b"\x65\x48\x8b\x04\x25\x60\x00\x00\x00",
                                               b"\x65\x48\x8b\x04\x25"],
     "meaning": "Reads PEB via GS segment (API resolution)", "severity": "high"},
    {"name": "API hashing loop", "patterns": [b"\x0f\xb6", b"\x8a\x04", b"\x32\x04"],
     "meaning": "Byte-wise hash calculation used to resolve APIs", "severity": "high"},
    {"name": "GetPC (call/pop)", "patterns": [b"\xe8\x00\x00\x00\x00", b"\xe8\x00\x00\x00"],
     "meaning": "Call-pop trick to locate shellcode position", "severity": "medium"},
    {"name": "Dynamic call", "patterns": [b"\xff\xd0", b"\xff\xd3", b"\xff\xd1", b"\xff\xd2"],
     "meaning": "Indirect call through register (resolved API)", "severity": "medium"},
    {"name": "Indirect call via memory", "patterns": [b"\xff\x15", b"\xff\x25"],
     "meaning": "Call/jump through pointer (IAT/API table)", "severity": "medium"},
    {"name": "Egg hunter", "patterns": [b"\x66\x81\xca\xff\xff", b"\x66\x81\xc9\xff\xff"],
     "meaning": "Scans memory for an egg tag before executing stage 2", "severity": "high"},
    {"name": "Syscall", "patterns": [b"\x0f\x05", b"\x0f\x34"],
     "meaning": "Direct system call (possible EDR evasion)", "severity": "medium"},
    {"name": "Stack pivot / ret", "patterns": [b"\xff\xe4", b"\xc9\xc3", b"\x94\xc3"],
     "meaning": "Stack pivot or ROP transition", "severity": "medium"},
    {"name": "XOR decoding loop", "patterns": [b"\x30\x1c", b"\x32\x1c", b"\x80\x34"],
     "meaning": "Inline XOR decoder (encoded payload)", "severity": "high"},
    {"name": "ARM64 svc", "patterns": [b"\x01\x00\x00\xd4"],
     "meaning": "ARM64 supervisor call (syscall)", "severity": "medium"},
    {"name": "ARM PEB/TEB", "patterns": [b"\x00\x00\xa0\xe1"],
     "meaning": "ARM NOP / alignment (possible ARM shellcode)", "severity": "low"},
]

_SHELLCODE_STRINGS = {
    "urlmon.dll": "URL download", "urldownloadtofile": "download to disk",
    "winexec": "execution", "createprocess": "process creation",
    "virtualalloc": "memory allocation", "writeprocessmemory": "injection",
    "createremotethread": "remote thread", "loadlibrary": "library load",
    "getprocaddress": "API resolution", "ws2_32.dll": "network",
    "wininet.dll": "HTTP", "wsastartup": "network", "connect": "network",
    "cmd.exe": "command shell", "powershell": "PowerShell execution",
}


def analyze_shellcode(data: bytes, arch: str = "") -> Dict[str, Any]:
    if not data:
        raise ValueError("empty shellcode")
    text = " ".join(extract_strings(data, 4, True, True, 2000)["ascii"])
    low = text.lower()
    patterns = []
    for sig in _SHELLCODE_PATTERNS:
        hits = []
        for pat in sig["patterns"]:
            idx = data.find(pat)
            if idx >= 0:
                hits.append(idx)
        if hits:
            patterns.append({"pattern": sig["name"], "offsets": hits[:8],
                             "meaning": sig["meaning"], "severity": sig["severity"]})
    for key, meaning in _SHELLCODE_STRINGS.items():
        if key in low:
            patterns.append({"pattern": f"string {key!r}", "offsets": [],
                             "meaning": meaning, "severity": "medium"})
    arch_guess = arch or _guess_arch(data)
    disasm = _disasm(data, arch_guess, 60)
    enc = entropy(data)
    null_ratio = data.count(0) / len(data)
    flags = []
    if enc > 7.2:
        flags.append("high entropy (encrypted/encoded)")
    if null_ratio < 0.02:
        flags.append("no null bytes (shellcode-friendly)")
    if any(p["pattern"] == "API hashing loop" for p in patterns):
        flags.append("API hashing")
    if any(p["pattern"].startswith("PEB") for p in patterns):
        flags.append("PEB walking")
    if any(p["pattern"] == "Egg hunter" for p in patterns):
        flags.append("egg hunter / staged")
    if "mz" in low[:4].lower() or data[:2] == b"MZ":
        flags.append("embedded PE")
    confidence = min(98, 20 + len(patterns) * 9 + (20 if enc > 7.2 else 0))
    return {
        "size": len(data), "arch_guess": arch_guess, "entropy": round(enc, 3),
        "null_ratio": round(null_ratio, 4),
        "patterns": patterns, "disassembly": disasm,
        "strings": extract_strings(data, 5, True, True, 300)["ascii"],
        "flags": flags, "confidence": confidence,
        "verdict": "malicious shellcode likely" if confidence >= 60 else "possibly shellcode",
        "hashes": hash_bytes(data),
        "high_entropy_regions": high_entropy_regions(data, 7.0, 128, 2)[:12],
    }


def _guess_arch(data: bytes) -> str:
    x64 = sum(1 for i in range(len(data) - 1) if data[i] in (0x48, 0x49, 0x4C, 0x4D) and data[i + 1] in (0x89, 0x8B, 0x8D, 0x31, 0x83))
    x86 = sum(1 for b in data if b in (0x50, 0x51, 0x52, 0x53, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B, 0x5D, 0x5E, 0x5F))
    if data[:4] == b"\x01\x00\x00\xd4" or b"\x00\x00\xa0\xe1" in data[:256]:
        return "arm64"
    return "x64" if x64 > x86 / 3 else "x86"


def _disasm(data: bytes, arch: str, count: int) -> Dict[str, Any]:
    if capstone is None:
        return {"available": False, "note": "install capstone for disassembly"}
    try:
        if arch in ("x64", "x86-64"):
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        elif arch in ("arm64", "arm"):
            md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        else:
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        insns = []
        for ins in md.disasm(data[:4096], 0):
            insns.append({"address": hex(ins.address), "bytes": ins.bytes.hex(),
                          "mnemonic": ins.mnemonic, "op_str": ins.op_str})
            if len(insns) >= count:
                break
        return {"available": True, "instructions": insns}
    except Exception as exc:
        return {"available": False, "note": f"capstone error: {exc}"}


# --------------------------------------------------------------------------- #
#  ROP gadgets
# --------------------------------------------------------------------------- #
def scan_rop(data: bytes, arch: str = "x64", limit: int = 300) -> Dict[str, Any]:
    gadgets: List[Dict[str, Any]] = []
    counts = Counter()
    # Common harmless instruction bytes preceding ret (0xc3) / retf (0xcb)
    one_byte = {0x58: "pop eax/rax", 0x59: "pop ecx/rcx", 0x5A: "pop edx/rdx",
                0x5B: "pop ebx/rbx", 0x5D: "pop ebp/rbp", 0x5E: "pop esi/rsi",
                0x5F: "pop edi/rdi", 0x94: "xchg eax,esp", 0x99: "cdq",
                0x9C: "pushfq", 0x9D: "popfq", 0xC9: "leave", 0xCC: "int3",
                0x90: "nop", 0xF4: "hlt"}
    for i in range(len(data) - 1):
        b = data[i]
        if b == 0xC3:
            counts["ret"] += 1
            # look back up to 6 bytes for a simple gadget
            start = max(0, i - 6)
            seq = data[start:i + 1]
            if len(seq) >= 2 and seq[-2] in one_byte:
                g = {"offset": start, "bytes": seq.hex(),
                     "gadget": f"{one_byte[seq[-2]]}; ret", "kind": "pop-ret"}
                gadgets.append(g)
                counts["pop-ret"] += 1
            elif len(seq) >= 3 and seq[-3] == 0x0F and seq[-2] == 0x05:
                gadgets.append({"offset": start, "bytes": seq.hex(),
                                "gadget": "syscall; ret", "kind": "syscall-ret"})
                counts["syscall-ret"] += 1
        elif b == 0xFF and i + 1 < len(data) and data[i + 1] in (0xE0, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7):
            counts["jmp-reg"] += 1
            gadgets.append({"offset": i, "bytes": data[i:i + 2].hex(),
                            "gadget": f"jmp {['eax','ecx','edx','ebx','esp','ebp','esi','edi'][data[i+1]-0xE0]}",
                            "kind": "jmp-reg"})
        elif b == 0x0F and i + 1 < len(data) and data[i + 1] == 0x05:
            counts["syscall"] += 1
        if len(gadgets) >= limit:
            break
    unique = {}
    for g in gadgets:
        unique[g["gadget"]] = g
    return {
        "arch": arch, "gadget_count": len(unique),
        "counts": dict(counts),
        "gadgets": list(unique.values())[:limit],
        "rop_likely": len(unique) >= 10 or counts["pop-ret"] >= 5,
        "notes": "Executable ranges should be used for a precise ROP inventory.",
    }


# --------------------------------------------------------------------------- #
#  Crypto signatures / XOR recovery
# --------------------------------------------------------------------------- #
CRYPTO_SIGNATURES: List[Dict[str, Any]] = [
    {"name": "AES S-box", "hex": "637c777bf26b6fc5", "family": "AES", "severity": "info"},
    {"name": "AES inverse S-box", "hex": "52096ad53036a538", "family": "AES", "severity": "info"},
    {"name": "AES Rcon", "hex": "01000000020000000400000008000000", "family": "AES", "severity": "info"},
    {"name": "MD5 init vector", "hex": "0123456789abcdeffedcba9876543210", "family": "MD5", "severity": "info"},
    {"name": "SHA1 init vector", "hex": "67452301efcdab8998badcfe10325476c3d2e1f0", "family": "SHA1", "severity": "info"},
    {"name": "SHA256 init vector", "hex": "6a09e667bb67ae853c6ef372a54ff53a", "family": "SHA256", "severity": "info"},
    {"name": "SHA512 init vector", "hex": "6a09e667f3bcc908bb67ae8584caa73b", "family": "SHA512", "severity": "info"},
    {"name": "CRC32 polynomial", "hex": "2083b8ed", "family": "CRC32", "severity": "info"},
    {"name": "Salsa20/ChaCha sigma", "hex": "657870616e642033322d62797465206b", "family": "Salsa20/ChaCha20", "severity": "info"},
    {"name": "RC4 identity permutation", "hex": "000102030405060708090a0b0c0d0e0f", "family": "RC4", "severity": "info"},
    {"name": "RSA public exponent", "hex": "010001", "family": "RSA", "severity": "info"},
    {"name": "bcrypt magic", "hex": "4f726967696e616c", "family": "bcrypt", "severity": "info"},
]

CRYPTO_STRINGS = {
    "aes": "AES", "rijndael": "AES", "chacha": "ChaCha20", "salsa20": "Salsa20",
    "rc4": "RC4", "arc4": "RC4", "blowfish": "Blowfish", "twofish": "Twofish",
    "des": "DES/3DES", "rsa": "RSA", "elliptic": "ECC", "curve25519": "X25519",
    "sha256": "SHA-256", "sha1": "SHA-1", "md5": "MD5", "hmac": "HMAC",
    "pbkdf2": "PBKDF2", "bcrypt": "bcrypt", "scrypt": "scrypt", "argon2": "Argon2",
    "cryptacquirecontext": "Windows CryptoAPI", "bcryptopenalgorithmprovider": "CNG",
    "cryptencrypt": "Windows CryptoAPI encrypt", "cryptdecrypt": "Windows CryptoAPI decrypt",
    "evp_encryptinit": "OpenSSL EVP", "openssl": "OpenSSL",
}


def scan_crypto(data: bytes, strings: Optional[str] = None) -> Dict[str, Any]:
    found = []
    for sig in CRYPTO_SIGNATURES:
        pat = bytes.fromhex(sig["hex"])
        idx = data.find(pat)
        if idx >= 0:
            found.append({**sig, "offset": idx})
    text = (strings or " ".join(extract_strings(data, 5, True, True, 4000)["ascii"])).lower()
    string_hits = [{"name": name, "keyword": key} for key, name in CRYPTO_STRINGS.items() if key in text]
    key_material = _key_material(data, text)
    xor = xor_brute(data)
    score = len(found) * 12 + len(string_hits) * 5
    return {
        "constants": found, "string_hits": string_hits,
        "key_material": key_material,
        "xor_recovery": xor,
        "verdict": "cryptographic functionality detected" if score >= 20 else
                   ("possible crypto/encoding" if score else "no standard crypto signatures"),
        "score": min(100, score),
    }


def _key_material(data: bytes, text: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"pem": [], "hex_candidates": [], "base64_candidates": []}
    for m in re.finditer(rb"-----BEGIN [A-Z ]+-----[\s\S]{20,}?-----END [A-Z ]+-----", data):
        out["pem"].append(m.group().decode("latin-1", "replace")[:4096])
    for m in re.finditer(rb"(?i)\b[0-9a-f]{32,128}\b", data):
        s = m.group().decode()
        if len(s) in (32, 40, 48, 64, 96, 128) and entropy(bytes.fromhex(s)) > 3.0:
            out["hex_candidates"].append({"offset": m.start(), "value": s, "length": len(s)})
        if len(out["hex_candidates"]) >= 20:
            break
    for m in re.finditer(rb"(?i)[A-Za-z0-9+/]{40,}={0,2}", data):
        s = m.group().decode()
        if s.startswith("eyJ"):
            continue
        out["base64_candidates"].append({"offset": m.start(), "value": s[:160],
                                         "length": len(s)})
        if len(out["base64_candidates"]) >= 20:
            break
    out["keyword_hits"] = [k for k in ("key", "iv", "nonce", "salt", "secret") if k in text]
    return out


_XOR_WORDS = (b"http", b"this", b"that", b"the ", b"and ", b"ing", b"tion",
              b"with", b"from", b"shell", b"cmd", b"powershell", b"MZ",
              b"kernel32", b"VirtualAlloc", b"CreateProcess", b"password")


def xor_brute(data: bytes, known_plaintext: str = "", key: str = "",
              max_key_len: int = 16) -> Dict[str, Any]:
    sample = data[:8192]
    if not sample:
        return {"candidates": []}
    if key:
        kb = key.encode() if isinstance(key, str) else bytes(key)
        out = _xor_repeat(sample, kb)
        return {"key": kb.hex(), "decoded_preview": out[:512].decode("latin-1", "replace"),
                "score": _english_score(out), "mode": "provided"}
    candidates = []
    if known_plaintext:
        kp = known_plaintext.encode()
        for off in range(min(len(sample) - len(kp), 4096)):
            derived = bytes(a ^ b for a, b in zip(sample[off:off + len(kp)], kp))
            if len(set(derived)) <= 4:
                candidates.append({"key": derived.hex(), "offset": off,
                                   "mode": "known-plaintext", "score": 100})
                break
    for k in range(1, 256):
        out = bytes(b ^ k for b in sample[:4096])
        score = _english_score(out)
        if score > 15:
            candidates.append({"key": f"{k:02x}", "offset": 0, "mode": "single-byte",
                               "score": score,
                               "preview": out[:120].decode("latin-1", "replace")})
    # repeating-key with space assumption
    for klen in range(2, max_key_len + 1):
        keybuf = bytearray()
        for pos in range(klen):
            chunk = sample[pos::klen]
            if not chunk:
                break
            common = max(set(chunk), key=chunk.count)
            keybuf.append(common ^ 0x20)
        if len(keybuf) == klen:
            out = _xor_repeat(sample[:4096], bytes(keybuf))
            score = _english_score(out)
            if score > 20:
                candidates.append({"key": bytes(keybuf).hex(), "offset": 0,
                                   "mode": f"repeating-{klen}", "score": score,
                                   "preview": out[:120].decode("latin-1", "replace")})
    candidates.sort(key=lambda c: c["score"], reverse=True)
    dedup = []
    seen = set()
    for c in candidates:
        if c["key"] not in seen:
            seen.add(c["key"])
            dedup.append(c)
    return {"candidates": dedup[:10], "tried_single_byte": 255,
            "best": dedup[0] if dedup else None}


def _xor_repeat(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _english_score(data: bytes) -> int:
    if not data:
        return 0
    printable = sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))
    ratio = printable / len(data)
    good = sum(1 for w in _XOR_WORDS if w in data)
    common = sum(data.count(bytes([c])) for c in b" etaoinshrdlu")
    return int(ratio * 50) + good * 15 + int(common / max(1, len(data)) * 30)


# --------------------------------------------------------------------------- #
#  Anti-analysis detection
# --------------------------------------------------------------------------- #
_ANTI_DEBUG = {
    "isdebuggerpresent": ("Anti-debug", "Checks PEB.BeingDebugged", "Patch the return value / hide debugger"),
    "checkremotedebuggerpresent": ("Anti-debug", "Checks remote debugger", "Hook the API and return FALSE"),
    "ntqueryinformationprocess": ("Anti-debug", "ProcessDebugPort/Flags/object checks", "Use ScyllaHide / hook NtQueryInformationProcess"),
    "outputdebugstring": ("Anti-debug", "Detects debugger via last error", "Emulate expected error state"),
    "findwindow": ("Anti-debug", "Looks for OllyDbg/x64dbg/IDA windows", "Rename windows / hide via plugin"),
    "gettickcount": ("Timing", "Compares elapsed time around code", "Hook timing APIs or patch comparisons"),
    "queryperformancecounter": ("Timing", "High-resolution timing check", "Hook QPC / normalize deltas"),
    "rdtsc": ("Timing", "CPU timestamp counter delta", "Trap RDTSC / patch result"),
    "sleep": ("Timing", "Long sleep to outlast sandbox", "Skip/patch sleep or accelerate clock"),
    "ntdelayexecution": ("Timing", "Low-level sleep", "Hook/skip delay"),
    "globalmemorystatusex": ("VM/Sandbox", "Checks RAM size", "Present realistic RAM"),
    "getdiskfreespaceex": ("VM/Sandbox", "Checks disk size", "Present realistic disk"),
    "getsystemmetrics": ("VM/Sandbox", "Checks screen resolution", "Use realistic resolution"),
    "getlogicalprocessorinformation": ("VM/Sandbox", "Checks CPU core count", "Expose >= 2 cores"),
    "cpuid": ("VM/Sandbox", "Hypervisor vendor leaf", "Hide hypervisor CPUID leaf"),
    "getadaptersinfo": ("VM/Sandbox", "MAC OUI check", "Use real vendor OUI"),
    "getvolumeinformation": ("VM/Sandbox", "Volume serial check", "Randomize volume serial"),
    "getusername": ("VM/Sandbox", "Username check", "Use a realistic username"),
    "getcomputername": ("VM/Sandbox", "Hostname check", "Use a realistic hostname"),
    "getcursorpos": ("User interaction", "Requires mouse movement", "Simulate mouse activity"),
    "getasynckeystate": ("User interaction", "Waits for keystrokes", "Simulate keyboard input"),
    "getlastinputinfo": ("User interaction", "Checks idle time", "Keep session interactive"),
    "setwindowshookex": ("Hook", "Global hook", "Inspect hook targets"),
    "blockinput": ("Evasion", "Blocks input", "Unhook / re-enable input"),
    "ntsetinformationthread": ("Anti-debug", "Hides thread from debugger", "Hook and ignore"),
    "virtualprotect": ("Memory", "Changes page permissions", "Monitor RWX transitions"),
    "wine_get_unix_file_name": ("VM/Sandbox", "Wine detection", "Run on real Windows"),
}

_ANTI_STRINGS = {
    "vmware": "VMware artifact", "virtualbox": "VirtualBox artifact", "vbox": "VirtualBox artifact",
    "qemu": "QEMU artifact", "xen": "Xen artifact", "sandboxie": "Sandboxie artifact",
    "cuckoo": "Cuckoo sandbox artifact", "wine": "Wine artifact", "sbie": "Sandboxie DLL",
    "vmtoolsd": "VMware tools process", "vboxservice": "VirtualBox service",
    "ollydbg": "OllyDbg window/process", "x64dbg": "x64dbg window/process",
    "idaq": "IDA process", "wireshark": "Wireshark process", "procmon": "Procmon process",
    "processhacker": "Process Hacker process", "fiddler": "Fiddler process",
    "autoruns": "Autoruns process", "tcpview": "TCPView process",
    "currentuser": "Username check", "sandbox": "Sandbox string",
    "malware analysis": "Analysis environment string",
    "sample.exe": "Generic sample filename", "test.exe": "Generic test filename",
    "john doe": "Generic user artifact", "maltest": "Malware test VM artifact",
}


def anti_analysis_scan(data: bytes, text: Optional[str] = None,
                       imports: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    blob = data.lower()
    strings = (text or " ".join(extract_strings(data, 4, True, True, 8000)["ascii"])).lower()
    imports_low = " ".join(imports or []).lower()
    checks: List[Dict[str, Any]] = []
    for api, (category, purpose, bypass) in _ANTI_DEBUG.items():
        if api.encode() in blob or api in imports_low:
            checks.append({"category": category, "evidence": f"API/string {api}",
                           "purpose": purpose, "bypass": bypass, "confidence": 85})
    for marker, desc in _ANTI_STRINGS.items():
        if marker in strings or marker.encode() in blob:
            checks.append({"category": "Environment", "evidence": f"string {marker!r}",
                           "purpose": desc, "bypass": "Use a realistic analysis VM / hide artifact",
                           "confidence": 70})
    # Anti-disassembly heuristics
    if b"\xcc" in data and data.count(b"\xcc") > 20:
        checks.append({"category": "Anti-disassembly", "evidence": "many INT3 bytes",
                       "purpose": "Confuse linear disassembly", "bypass": "Use recursive-descent disassembler",
                       "confidence": 55})
    if b"\xeb\xff" in data or b"\x74\x00" in data:
        checks.append({"category": "Anti-disassembly", "evidence": "opaque branch/jump into next instruction",
                       "purpose": "Desynchronize disassembler", "bypass": "Use dynamic tracing",
                       "confidence": 45})
    # dedupe (category, evidence)
    seen = set()
    unique = []
    for c in checks:
        k = (c["category"], c["evidence"])
        if k not in seen:
            seen.add(k)
            unique.append(c)
    cats = Counter(c["category"] for c in unique)
    return {"checks": unique, "count": len(unique), "categories": dict(cats),
            "bypass_summary": _bypass_summary(unique),
            "verdict": "evasive/anti-analysis behavior" if unique else "no common evasion checks found"}


def _bypass_summary(checks: List[Dict[str, Any]]) -> List[str]:
    tips = []
    cats = {c["category"] for c in checks}
    if "Anti-debug" in cats:
        tips.append("Use ScyllaHide / TitanHide and patch API results.")
    if "Timing" in cats:
        tips.append("Hook timing APIs or accelerate the VM clock.")
    if "VM/Sandbox" in cats:
        tips.append("Harden the VM (realistic RAM/disk/CPU, vendor OUI, hypervisor leaf hidden).")
    if "User interaction" in cats:
        tips.append("Simulate mouse/keyboard with the sandbox interaction agent.")
    if "Environment" in cats:
        tips.append("Remove analysis tooling names and use realistic user artifacts.")
    if "Anti-disassembly" in cats:
        tips.append("Trace dynamically; do not rely on a single static pass.")
    return tips


# --------------------------------------------------------------------------- #
#  Intent / family / DNA
# --------------------------------------------------------------------------- #
_INTENT_RULES: Dict[str, Dict[str, Any]] = {
    "Ransomware": {"apis": ["cryptencrypt", "cryptgenkey", "cryptacquirecontext", "findfirstfile",
                            "findnextfile", "movefile", "deletefile", "internetopen"],
                   "strings": ["ransom", "decrypt", "your files", "bitcoin", "monero",
                               ".locked", ".encrypted", "readme", "restore", "payment",
                               "vssadmin", "shadow copy", "bcdedit", "wbadmin"],
                   "weight": 3},
    "Infostealer": {"apis": ["getclipboarddata", "getasynckeystate", "bitblt", "createtoolhelp32snapshot",
                             "regopenkey", "sqlite3_open", "internetopenurl", "smtp"],
                    "strings": ["password", "login", "cookie", "wallet", "credit card",
                                "browser", "chromium", "leveldb", "keylog", "screenshot",
                                "discord token", "telegram", "steam", "autofill"],
                    "weight": 3},
    "RAT": {"apis": ["wsastartup", "socket", "connect", "recv", "send", "createremotethread",
                     "setwindowshookex", "getasynckeystate", "bitblt", "createprocess",
                     "winexec", "shellexecute"],
            "strings": ["remote shell", "cmd.exe", "powershell", "screen capture", "webcam",
                        "keylog", "file manager", "process list", "reverse shell", "bot",
                        "command", "upload", "download"],
            "weight": 2},
    "Cryptominer": {"apis": ["createprocess", "wsastartup", "socket", "connect"],
                    "strings": ["xmrig", "stratum+tcp", "stratum+ssl", "monero", "mining pool",
                                "donate-level", "nicehash", "cpuminer", "randomx"],
                    "weight": 5},
    "Wiper": {"apis": ["deletefile", "movefile", "deviceiocontrol", "writefile"],
              "strings": ["wipe", "destroy", "mbr", "overwrite", "goodbye", "no recovery",
                          "bcdedit", "vssadmin delete", "cipher /w"],
              "weight": 4},
    "Dropper/Loader": {"apis": ["virtualalloc", "writeprocessmemory", "createremotethread",
                                "urldownloadtofile", "shellexecute", "winexec", "createprocess"],
                       "strings": ["http://", "https://", "temp\\", "appdata\\", "download",
                                   "payload", "stage", "loader", "inject", "mz"],
                       "weight": 2},
    "Backdoor": {"apis": ["wsastartup", "socket", "bind", "listen", "accept", "createprocess"],
                 "strings": ["backdoor", "bind shell", "reverse shell", "nc -e", "cmd.exe",
                             "hidden", "persistence", "schtasks", "run key"],
                 "weight": 2},
    "Banking Trojan": {"apis": ["setwindowshookex", "getasynckeystate", "bitblt"],
                       "strings": ["bank", "banking", "webinject", "grabber", "credit card",
                                   "iban", "swift", "2fa", "otp", "payment"],
                       "weight": 3},
    "Keylogger": {"apis": ["setwindowshookex", "getasynckeystate", "getkeystate",
                           "registerrawinputdevices", "getforegroundwindow"],
                  "strings": ["keylog", "keystroke", "hook", "raw input", "typed"],
                  "weight": 4},
}


def predict_intent(data: bytes, strings: Optional[str] = None,
                   imports: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    text = (strings or " ".join(extract_strings(data, 4, True, True, 8000)["ascii"])).lower()
    imp = " ".join(imports or []).lower()
    scores = {}
    evidence = {}
    for category, rule in _INTENT_RULES.items():
        score = 0
        ev = []
        for api in rule["apis"]:
            if api in imp:
                score += rule["weight"] * 2
                ev.append(f"import {api}")
        for s in rule["strings"]:
            if s in text:
                score += rule["weight"]
                ev.append(f"string {s!r}")
        if score:
            scores[category] = score
            evidence[category] = ev[:8]
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    total = sum(scores.values()) or 1
    top = ranked[0][0] if ranked else "Unknown"
    confidence = int(round(scores.get(top, 0) / total * 100)) if ranked else 0
    return {
        "intent": top, "confidence": confidence,
        "scores": dict(ranked), "evidence": evidence.get(top, []),
        "all_evidence": evidence,
        "predicted_persistence": _predict_persistence(text, imp),
        "predicted_c2": _predict_c2(text),
        "risk": "high" if top in ("Ransomware", "Wiper", "Infostealer", "Backdoor") else "medium",
    }


def _predict_persistence(text: str, imports: str) -> List[str]:
    out = []
    if "currentversion\\run" in text or "regsetvalue" in imports:
        out.append("Registry Run key")
    if "schtasks" in text or "scheduled task" in text:
        out.append("Scheduled task")
    if "create service" in text or "sc create" in text:
        out.append("Windows service")
    if "startup" in text:
        out.append("Startup folder")
    if "wmi" in text or "eventconsumer" in text:
        out.append("WMI event subscription")
    if "cron" in text or "systemd" in text:
        out.append("Linux cron/systemd")
    return out or ["unknown — no obvious persistence strings"]


def _predict_c2(text: str) -> Dict[str, Any]:
    urls = re.findall(r"https?://[^\s\"'<>]+", text)
    ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    domains = re.findall(r"\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|ru|cn|xyz|top|onion)\b", text)
    return {"urls": list(dict.fromkeys(urls))[:10],
            "ips": list(dict.fromkeys(ips))[:10],
            "domains": list(dict.fromkeys(domains))[:10],
            "protocols": [p for p in ("http", "https", "dns", "tcp", "udp", "websocket",
                                      "telegram", "discord", "tor") if p in text]}


def match_family(data: bytes, strings: Optional[str] = None,
                 imports: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    text = (strings or " ".join(extract_strings(data, 4, True, True, 8000)["ascii"])).lower()
    imp = " ".join(imports or []).lower()
    matches = []
    for fam in FAMILIES:
        score = 0
        ev = []
        for marker in fam["markers"]:
            if marker in text or marker.encode() in data.lower():
                score += 35
                ev.append(f"marker {marker!r}")
        for api in fam.get("apis", []):
            if api in imp:
                score += 10
                ev.append(f"API {api}")
        if score:
            matches.append({"family": fam["name"], "confidence": min(98, score),
                            "evidence": ev[:8], "notes": fam["notes"]})
    matches.sort(key=lambda m: m["confidence"], reverse=True)
    return {"matches": matches[:8], "best": matches[0] if matches else None,
            "attribution_confidence": "high" if matches and matches[0]["confidence"] >= 70 else
                                       ("medium" if matches else "low")}


def behavior_dna(data: bytes, imports: Optional[Sequence[str]] = None,
                 strings: Optional[str] = None) -> Dict[str, Any]:
    text = (strings or " ".join(extract_strings(data, 4, True, True, 8000)["ascii"])).lower()
    imp = [i.lower() for i in (imports or [])]
    categories = {
        "network": [i for i in imp if any(k in i for k in ("socket", "connect", "send", "recv", "internet", "dns", "winhttp", "http"))],
        "file": [i for i in imp if any(k in i for k in ("createfile", "writefile", "readfile", "deletefile", "movefile", "findfirst"))],
        "registry": [i for i in imp if any(k in i for k in ("regopen", "regset", "regcreate", "regquery"))],
        "process": [i for i in imp if any(k in i for k in ("createprocess", "winexec", "shellexecute", "openprocess", "createremotethread"))],
        "memory": [i for i in imp if any(k in i for k in ("virtualalloc", "virtualprotect", "writeprocessmemory", "heapalloc"))],
        "crypto": [i for i in imp if any(k in i for k in ("crypt", "bcrypt", "ncrypt"))],
        "collection": [i for i in imp if any(k in i for k in ("clipboard", "keystate", "bitblt", "hook"))],
    }
    steps = []
    for cat in ("process", "memory", "file", "registry", "network", "crypto", "collection"):
        if categories[cat]:
            steps.append(f"[{cat.upper()}:{categories[cat][0]}]")
    behaviors = []
    if any(k in text for k in ("currentversion\\run", "schtasks", "create service")):
        behaviors.append("PERSIST")
    if any(k in text for k in ("lsass", "mimikatz", "credential")):
        behaviors.append("CREDENTIAL")
    if any(k in text for k in ("encrypt", "ransom", ".locked")):
        behaviors.append("ENCRYPT")
    if any(k in text for k in ("keylog", "clipboard", "screenshot")):
        behaviors.append("COLLECT")
    if any(k in text for k in ("http://", "https://", "dns", "tcp")):
        behaviors.append("NETWORK")
    if behaviors:
        steps.append("→".join(behaviors))
    fingerprint = " → ".join(steps) or "[STATIC:no-imports]"
    digest = hashlib.sha256(fingerprint.encode()).hexdigest()[:32]
    return {"fingerprint": fingerprint, "digest": digest,
            "categories": {k: v[:8] for k, v in categories.items() if v},
            "entity_count": sum(len(v) for v in categories.values()),
            "cluster_key": f"BDNA-{digest[:12].upper()}"}


def compare_samples(entries: List[Tuple[str, bytes]]) -> Dict[str, Any]:
    """entries: [(label, data)]. Returns pairwise similarity matrix + clusters."""
    import itertools
    matrix = []
    clusters: List[List[str]] = []
    for (la, da), (lb, db) in itertools.combinations(entries, 2):
        sim = data_similarity(da, db)
        matrix.append({"a": la, "b": lb, "score": sim["score"],
                       "byte_ratio": sim["byte_ratio"],
                       "chunk_jaccard": sim["chunk_jaccard"]})
    # greedy clustering at 65%
    for label, _ in entries:
        placed = False
        for cluster in clusters:
            if any(m["score"] >= 65 for m in matrix
                   if (m["a"] == label and m["b"] in cluster) or (m["b"] == label and m["a"] in cluster)):
                cluster.append(label)
                placed = True
                break
        if not placed:
            clusters.append([label])
    return {"files": [{"label": l, "size": len(d), "sha256": hashlib.sha256(d).hexdigest()} for l, d in entries],
            "matrix": sorted(matrix, key=lambda m: m["score"], reverse=True),
            "clusters": clusters,
            "likely_related": [m for m in matrix if m["score"] >= 65]}
