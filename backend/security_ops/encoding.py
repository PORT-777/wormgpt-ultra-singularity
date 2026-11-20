# backend/security_ops/encoding.py
# Encoding and lightweight crypto tooling: recursive multi-layer decoding,
# encoders (base64/base32/base16/hex/url/rot13/quoted-printable/uuencode),
# JWT inspection, X.509/PEM parsing, hash identification, password/wordlist
# statistics, XOR/RC4/AES helpers for C2 payload work.

from __future__ import annotations

import base64
import binascii
import codecs
import hashlib
import hmac
import html
import json
import math
import re
import struct
import urllib.parse
import uuid
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .knowledge import HASH_TYPES
from .util import (b64decode_loose, b64encode, entropy, extract_iocs,
                   extract_strings)

# --------------------------------------------------------------------------- #
#  Encoders / single-step decoders
# --------------------------------------------------------------------------- #
def _looks_text(data: bytes) -> bool:
    if not data:
        return False
    sample = data[:2048]
    printable = sum(1 for b in sample if 32 <= b <= 126 or b in (9, 10, 13))
    return printable / len(sample) > 0.88


def _looks_like_pe(data: bytes) -> bool:
    return data[:2] == b"MZ" and len(data) > 0x40


def decode_base64(value: str) -> Optional[bytes]:
    try:
        return b64decode_loose(value)
    except Exception:
        return None


def decode_base32(value: str) -> Optional[bytes]:
    try:
        s = re.sub(r"\s+", "", value).upper()
        return base64.b32decode(s + "=" * (-len(s) % 8))
    except Exception:
        return None


def decode_base85(value: str) -> Optional[bytes]:
    try:
        return base64.b85decode(value)
    except Exception:
        try:
            return base64.a85decode(value, adobe=False)
        except Exception:
            return None


def decode_hex_string(value: str) -> Optional[bytes]:
    try:
        s = re.sub(r"(?i)0x", "", value)
        s = re.sub(r"[^0-9a-fA-F]", "", s)
        if not s or len(s) % 2:
            return None
        return bytes.fromhex(s)
    except Exception:
        return None


def decode_rot13(value: str) -> str:
    return codecs.encode(value, "rot_13")


def decode_url(value: str) -> str:
    return urllib.parse.unquote(value)


def decode_html_entities(value: str) -> str:
    return html.unescape(value)


def decode_quoted_printable(value: str) -> Optional[bytes]:
    try:
        import quopri
        return quopri.decodestring(value.encode("latin-1"))
    except Exception:
        return None


def decode_uuencode(value: str) -> Optional[bytes]:
    try:
        import uu
        import io
        out = io.BytesIO()
        uu.decode(io.BytesIO(value.encode("latin-1")), out, quiet=True)
        return out.getvalue()
    except Exception:
        return None


def decode_uuencode_alt(value: str) -> Optional[bytes]:
    # uuencode body lines starting with length char
    try:
        lines = [l for l in value.splitlines() if l and not l.startswith(("begin", "end"))]
        out = bytearray()
        for line in lines:
            body = line[1:]
            raw = bytearray()
            for i in range(0, len(body), 4):
                chunk = body[i:i + 4]
                vals = [(ord(c) - 32) & 63 for c in chunk]
                while len(vals) < 4:
                    vals.append(0)
                raw += bytes((((vals[0] << 2) | (vals[1] >> 4)) & 0xFF,
                              ((vals[1] << 4) | (vals[2] >> 2)) & 0xFF,
                              ((vals[2] << 6) | vals[3]) & 0xFF))
            out += raw
        return bytes(out)
    except Exception:
        return None


def decode_escape(value: str) -> Optional[bytes]:
    try:
        return codecs.decode(value, "unicode_escape").encode("latin-1")
    except Exception:
        return None


def decode_unicode_escape(value: str) -> str:
    try:
        return value.encode().decode("unicode_escape")
    except Exception:
        return value


DECODERS: List[Tuple[str, Any]] = [
    ("base64", decode_base64),
    ("base32", decode_base32),
    ("base85", decode_base85),
    ("hex", decode_hex_string),
    ("url", lambda s: decode_url(s).encode("latin-1", "replace")),
    ("html", lambda s: decode_html_entities(s).encode("latin-1", "replace")),
    ("rot13", lambda s: decode_rot13(s).encode("latin-1", "replace")),
    ("quoted-printable", decode_quoted_printable),
    ("uuencode", decode_uuencode_alt),
    ("escape", decode_escape),
]


def try_all_decoders(value: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Run every decoder once; report plausible outputs."""
    results = []
    for name, fn in DECODERS:
        try:
            out = fn(value)
        except Exception:
            continue
        if out is None:
            continue
        if isinstance(out, str):
            out = out.encode("utf-8", "replace")
        if not out or len(out) < 2:
            continue
        texty = _looks_text(out)
        score = 0
        if texty:
            score += 40
        if _looks_like_pe(out):
            score += 50
        if re.search(rb"(?i)(http://|https://|powershell|cmd\.exe|select |mz)", out[:4000]):
            score += 25
        if out[:4] in (b"\x7fELF", b"PK\x03\x04", b"%PDF"):
            score += 30
        results.append({"decoder": name, "size": len(out), "text": texty,
                        "score": score,
                        "preview": out[:400].decode("latin-1", "replace"),
                        "preview_hex": out[:64].hex()})
    results.sort(key=lambda r: (r["score"], r["size"]), reverse=True)
    return results[:limit]


def auto_decode(value: str, max_layers: int = 8) -> Dict[str, Any]:
    """Recursively peel encoding layers, tracking the chain used."""
    current = value.strip()
    layers: List[Dict[str, Any]] = []
    seen = {current}
    for depth in range(max_layers):
        options = try_all_decoders(current)
        if not options:
            break
        best = options[0]
        if best["score"] < 30 and depth > 0:
            break
        decoded_preview = best["preview"]
        # Accept if it is text or a known binary format, otherwise stop.
        if not best["text"] and depth == 0 and best["size"] < len(current) // 2:
            pass
        layers.append({"depth": depth + 1, "decoder": best["decoder"],
                       "size": best["size"], "text": best["text"],
                       "preview": best["preview"][:300],
                       "hex": best["preview_hex"]})
        next_value = best["preview"] if best["text"] else ""
        if not next_value or next_value in seen:
            break
        seen.add(next_value)
        current = next_value
        # stop when nothing looks encoded anymore
        if not re.search(r"[A-Za-z0-9+/=]{16,}", current):
            break
    final_bytes = None
    if layers:
        last = layers[-1]
        if last["text"]:
            final_bytes = last["preview"].encode("latin-1", "replace")
    out: Dict[str, Any] = {
        "input_length": len(value), "layers": layers,
        "layer_count": len(layers),
        "final_preview": layers[-1]["preview"] if layers else value[:300],
        "verdict": "multi-layer encoding decoded" if layers else "no known encoding detected",
    }
    if final_bytes and extract_iocs(final_bytes.decode("latin-1", "replace"))["count"]:
        out["iocs"] = extract_iocs(value + "\n" + final_bytes.decode("latin-1", "replace"))["categories"]
    if final_bytes:
        out["final_sha256"] = hashlib.sha256(final_bytes).hexdigest()
        if _looks_like_pe(final_bytes):
            out["embedded_pe"] = True
    return out


def encode(value: str, fmt: str = "base64") -> Dict[str, Any]:
    fmt = (fmt or "base64").lower().replace("-", "").replace("_", "")
    raw = value.encode("utf-8", "replace")
    mapping = {
        "base64": lambda: base64.b64encode(raw).decode(),
        "base64url": lambda: base64.urlsafe_b64encode(raw).decode().rstrip("="),
        "base32": lambda: base64.b32encode(raw).decode(),
        "base16": lambda: base64.b16encode(raw).decode(),
        "hex": lambda: raw.hex(),
        "url": lambda: urllib.parse.quote(value, safe=""),
        "html": lambda: html.escape(value),
        "rot13": lambda: decode_rot13(value),
        "quotedprintable": lambda: binascii.b2a_qp(raw).decode("latin-1"),
        "uuencode": lambda: _uuencode(raw),
        "powershell": lambda: _ps_encoded_command(value),
        "shellcodehex": lambda: "\\x" + "\\x".join(f"{b:02x}" for b in raw),
    }
    fn = mapping.get(fmt)
    if not fn:
        raise ValueError(f"unsupported format '{fmt}'; choose {sorted(mapping)}")
    try:
        encoded = fn()
    except Exception as exc:
        raise ValueError(f"encoding failed: {exc}")
    return {"format": fmt, "input_length": len(value), "output": encoded,
            "output_length": len(encoded)}


def _uuencode(data: bytes) -> str:
    import uu
    import io
    out = io.BytesIO()
    uu.encode(io.BytesIO(data), out, name="data")
    return out.getvalue().decode("latin-1")


def _ps_encoded_command(text: str) -> str:
    return base64.b64encode(text.encode("utf-16le")).decode()


# --------------------------------------------------------------------------- #
#  JWT
# --------------------------------------------------------------------------- #
def analyze_jwt(token: str) -> Dict[str, Any]:
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("not a JWT (expected 3 dot-separated parts)")
    header_raw, payload_raw, sig_raw = parts
    header = _b64url_json(header_raw)
    payload = _b64url_json(payload_raw)
    alg = (header or {}).get("alg", "")
    findings = []
    now = __import__("time").time()
    exp = payload.get("exp") if isinstance(payload, dict) else None
    iat = payload.get("iat") if isinstance(payload, dict) else None
    nbf = payload.get("nbf") if isinstance(payload, dict) else None
    expired = bool(exp and exp < now)
    if alg.lower() == "none":
        findings.append({"severity": "critical", "finding": "alg=none (unsigned token)"})
    if alg.upper() in ("HS256", "HS384", "HS512"):
        findings.append({"severity": "info", "finding": f"HMAC-signed ({alg}) — brute-forceable if weak secret"})
    if expired:
        findings.append({"severity": "medium", "finding": "token is expired"})
    if not exp:
        findings.append({"severity": "medium", "finding": "no exp claim (non-expiring token)"})
    if isinstance(payload, dict) and payload.get("jku"):
        findings.append({"severity": "high", "finding": "jku header present (key injection risk)",
                         "evidence": payload.get("jku")})
    if isinstance(header, dict) and header.get("jku"):
        findings.append({"severity": "high", "finding": "jku in header (SSRF/key injection risk)"})
    if isinstance(header, dict) and header.get("kid"):
        kid = str(header["kid"])
        if any(c in kid for c in ("../", "/", "\\", "..")) or "'" in kid or "\"" in kid:
            findings.append({"severity": "critical", "finding": "suspicious kid (path/SQL injection)"})
    if isinstance(payload, dict) and any(k in payload for k in ("admin", "role", "is_admin")):
        findings.append({"severity": "info", "finding": "authorization claims present",
                         "evidence": {k: payload[k] for k in ("admin", "role", "is_admin") if k in payload}})
    return {
        "header": header, "payload": payload, "signature_length": len(sig_raw),
        "algorithm": alg, "key_id": (header or {}).get("kid", ""),
        "type": (header or {}).get("typ", ""),
        "issued_at": _ts(iat), "expires_at": _ts(exp), "not_before": _ts(nbf),
        "expired": expired, "age_seconds": int(now - iat) if iat else None,
        "findings": findings, "verdict": "review required" if findings else "looks standard",
    }


def _b64url_json(part: str) -> Any:
    s = part.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    try:
        return json.loads(base64.b64decode(s, validate=False).decode("utf-8", "replace"))
    except Exception:
        return {"_raw": part[:200], "_error": "decode failed"}


def _ts(value: Any) -> str:
    if not value:
        return ""
    try:
        import datetime as dt
        return dt.datetime.fromtimestamp(float(value), tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(value)


def crack_jwt(token: str, wordlist: str = "") -> Dict[str, Any]:
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError("not a JWT")
    header = _b64url_json(parts[0])
    alg = str((header or {}).get("alg", "")).upper()
    if alg not in ("HS256", "HS384", "HS512"):
        return {"cracked": False, "note": f"unsupported alg {alg}"}
    hash_fn = {"HS256": hashlib.sha256, "HS384": hashlib.sha384,
               "HS512": hashlib.sha512}[alg]
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    try:
        sig = base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4))
    except Exception:
        return {"cracked": False, "note": "invalid signature encoding"}
    candidates = [w.strip() for w in wordlist.splitlines() if w.strip()] or [
        "secret", "password", "123456", "changeme", "admin", "test", "secretkey",
        "jwt", "jwtsecret", "your-256-bit-secret", "supersecret", "key", "default",
    ]
    for candidate in candidates[:50000]:
        if hmac.compare_digest(hmac.new(candidate.encode(), signing_input, hash_fn).digest(), sig):
            return {"cracked": True, "secret": candidate, "tried": candidates.index(candidate) + 1}
    return {"cracked": False, "tried": len(candidates), "note": "no match in wordlist"}


# --------------------------------------------------------------------------- #
#  Certificates
# --------------------------------------------------------------------------- #
def analyze_certificate(data: bytes) -> Dict[str, Any]:
    text = data.decode("latin-1", "replace") if b"-----BEGIN" in data else ""
    if not text:
        text = "-----BEGIN CERTIFICATE-----\n" + base64.b64encode(data).decode() + \
               "\n-----END CERTIFICATE-----\n"
    try:
        from cryptography import x509
        cert = x509.load_pem_x509_certificate(text.encode())
        def name(n: Any) -> Dict[str, str]:
            out = {}
            for attr in n:
                out[attr.oid._name] = attr.value
            return out
        subject = name(cert.subject)
        issuer = name(cert.issuer)
        try:
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            dns = san.get_values_for_type(x509.DNSName)
            ips = [str(x) for x in san.get_values_for_type(x509.IPAddress)]
        except Exception:
            dns, ips = [], []
        self_signed = cert.subject == cert.issuer
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        not_before = getattr(cert, "not_valid_before_utc", cert.not_valid_before)
        not_after = getattr(cert, "not_valid_after_utc", cert.not_valid_after)
        findings = []
        if self_signed:
            findings.append({"severity": "medium", "finding": "self-signed certificate"})
        if not_after < now:
            findings.append({"severity": "high", "finding": "certificate expired"})
        if not_before > now:
            findings.append({"severity": "medium", "finding": "certificate not yet valid"})
        if (not_after - not_before).days > 825 and not self_signed:
            findings.append({"severity": "medium", "finding": "validity longer than 825 days"})
        if not dns and not ips:
            findings.append({"severity": "low", "finding": "no SAN entries"})
        drift = re.search(r"(?i)(let'?s encrypt|zerossl|buypass)", subject.get("commonName", ""))
        if drift:
            findings.append({"severity": "low", "finding": "common name resembles a CA (possible abuse)"})
        return {"subject": subject, "issuer": issuer,
                "serial": hex(cert.serial_number),
                "not_before": str(not_before), "not_after": str(not_after),
                "days_remaining": (not_after - now).days,
                "signature_algorithm": cert.signature_algorithm_oid._name,
                "public_key_algorithm": cert.public_key().__class__.__name__,
                "public_key_bits": getattr(cert.public_key(), "key_size", 0),
                "san_dns": dns, "san_ip": ips, "self_signed": self_signed,
                "is_ca": _is_ca(cert), "findings": findings,
                "sha256": cert.fingerprint(__import__("cryptography").hazmat.primitives.hashes.SHA256()).hex(),
                "sha1": cert.fingerprint(__import__("cryptography").hazmat.primitives.hashes.SHA1()).hex(),
                "verdict": "suspicious certificate" if any(f["severity"] in ("critical", "high")
                                                          for f in findings) else "standard"}
    except ImportError:
        info = _asn1_guess(data)
        info["note"] = "install cryptography for full X.509 parsing"
        return info
    except Exception as exc:
        return {"error": f"certificate parse failed: {exc}", **_asn1_guess(data)}


def _is_ca(cert: Any) -> bool:
    try:
        from cryptography import x509
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
        return bool(bc.ca)
    except Exception:
        return False


def _asn1_guess(data: bytes) -> Dict[str, Any]:
    strings = list(dict.fromkeys(re.findall(rb"[ -~]{5,120}", data)))
    text = [s.decode("latin-1") for s in strings]
    return {"size": len(data), "strings_sample": text[:120],
            "looks_der": data[:1] == b"\x30", "looks_pem": b"-----BEGIN" in data,
            "sha256": hashlib.sha256(data).hexdigest()}


# --------------------------------------------------------------------------- #
#  Hash identification
# --------------------------------------------------------------------------- #
def identify_hash(value: str) -> Dict[str, Any]:
    v = value.strip()
    matches = []
    for spec in HASH_TYPES:
        try:
            if re.fullmatch(spec["regex"], v):
                matches.append(spec)
        except Exception:
            continue
    # heuristic disambiguation for 32-hex (MD5/NTLM/LM share a shape)
    notes = []
    if len(v) == 32 and re.fullmatch(r"[0-9a-fA-F]{32}", v):
        notes.append("32 hex chars = MD5, NTLM, or LM; context decides.")
        if re.fullmatch(r"[0-9A-F]{32}", v):
            notes.append("uppercase hex often indicates NTLM dump output.")
    if v.startswith("$2") and len(v) >= 59:
        notes.append("bcrypt hash (cost factor in $2x$NN$).")
    if v.startswith("$krb5tgs$"):
        notes.append("Kerberoastable service ticket hash.")
    if v.startswith("$krb5asrep$"):
        notes.append("AS-REP roastable account hash.")
    if v.count(":") >= 2 and "::" in v:
        notes.append("NetNTLM challenge/response format.")
    if v.startswith("eyJ") and v.count(".") == 2:
        notes.append("JWT; inspect claims instead of cracking blindly.")
    return {"value_length": len(v), "matches": matches,
            "match_count": len(matches), "notes": notes,
            "hashcat_modes": sorted({m.get("hashcat", "") for m in matches if m.get("hashcat")}),
            "john_formats": sorted({m.get("john", "") for m in matches if m.get("john")}),
            "verdict": (matches[0]["name"] if matches else "unknown hash format")}


# --------------------------------------------------------------------------- #
#  Password / wordlist analysis
# --------------------------------------------------------------------------- #
def analyze_passwords(text: str, top_n: int = 30) -> Dict[str, Any]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return {"error": "empty wordlist"}
    lengths = [len(l) for l in lines]
    counts = Counter(lines)
    charset = Counter()
    for p in lines:
        if re.search(r"[a-z]", p):
            charset["lower"] += 1
        if re.search(r"[A-Z]", p):
            charset["upper"] += 1
        if re.search(r"\d", p):
            charset["digits"] += 1
        if re.search(r"[^A-Za-z0-9]", p):
            charset["symbols"] += 1
    base_words = Counter(re.sub(r"[^A-Za-z]", "", l).lower() for l in lines if re.search(r"[A-Za-z]", l))
    patterns = {
        "all_lower": sum(1 for p in lines if p.islower()),
        "all_upper": sum(1 for p in lines if p.isupper()),
        "numeric_only": sum(1 for p in lines if p.isdigit()),
        "alpha_only": sum(1 for p in lines if p.isalpha()),
        "ends_with_digit": sum(1 for p in lines if p[:-1] and p[-1].isdigit()),
        "ends_with_symbol": sum(1 for p in lines if re.search(r"[^A-Za-z0-9]$", p)),
        "year_suffix": sum(1 for p in lines if re.search(r"(?:19|20)\d{2}$", p)),
        "keyboard_walk": sum(1 for p in lines if re.search(r"(?i)(qwerty|asdf|zxcv|1234|abcd)", p)),
        "common_leet": sum(1 for p in lines if re.search(r"[013457@$]", p)),
    }
    est = _estimate_strength_distribution(lines)
    return {
        "count": len(lines), "unique": len(counts), "duplicates": len(lines) - len(counts),
        "avg_length": round(sum(lengths) / len(lengths), 2),
        "min_length": min(lengths), "max_length": max(lengths),
        "length_distribution": dict(sorted(Counter(lengths).items())),
        "charset_usage": dict(charset),
        "pattern_breakdown": patterns,
        "top_passwords": [{"password": p, "count": c} for p, c in counts.most_common(top_n)],
        "top_base_words": [{"word": w, "count": c} for w, c in base_words.most_common(top_n)],
        "weak_count": sum(1 for p in lines if _weak(p)),
        "weak_percent": round(sum(1 for p in lines if _weak(p)) / len(lines) * 100, 1),
        "strength": est,
        "mask_hint": _mask_hint(lines),
        "recommendations": [
            "Reject passwords under 12 characters and known-breached passwords.",
            "Enforce MFA; complexity rules alone do not stop spraying.",
            "Block keyboard walks and company-name based passwords.",
        ],
    }


def _weak(p: str) -> bool:
    if len(p) < 12:
        return True
    if re.fullmatch(r"[a-z]+", p) or re.fullmatch(r"\d+", p):
        return True
    if re.search(r"(?i)(password|qwerty|admin|welcome|letmein|123456|iloveyou)", p):
        return True
    return False


def _estimate_strength_distribution(lines: Sequence[str]) -> Dict[str, Any]:
    buckets = Counter()
    for p in lines:
        score = 0
        if len(p) >= 8:
            score += 1
        if len(p) >= 12:
            score += 1
        if re.search(r"[a-z]", p):
            score += 1
        if re.search(r"[A-Z]", p):
            score += 1
        if re.search(r"\d", p):
            score += 1
        if re.search(r"[^A-Za-z0-9]", p):
            score += 1
        label = "very weak" if score <= 1 else ("weak" if score <= 2 else
                                                ("moderate" if score <= 4 else "strong"))
        buckets[label] += 1
    return dict(buckets)


def _mask_hint(lines: Sequence[str]) -> Optional[str]:
    sample = lines[0] if lines else ""
    mask = ""
    for ch in sample:
        if ch.islower():
            mask += "?l"
        elif ch.isupper():
            mask += "?u"
        elif ch.isdigit():
            mask += "?d"
        else:
            mask += "?s"
    return mask or None


# --------------------------------------------------------------------------- #
#  C2 crypto helpers
# --------------------------------------------------------------------------- #
def xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def rc4(data: bytes, key: bytes) -> bytes:
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xFF
        S[i], S[j] = S[j], S[i]
    out = bytearray()
    i = j = 0
    for byte in data:
        i = (i + 1) & 0xFF
        j = (j + S[i]) & 0xFF
        S[i], S[j] = S[j], S[i]
        out.append(byte ^ S[(S[i] + S[j]) & 0xFF])
    return bytes(out)


def decrypt_c2(data: bytes, scheme: str = "xor", key: str = "",
               iv: str = "") -> Dict[str, Any]:
    scheme = (scheme or "xor").lower()
    raw_key = bytes.fromhex(key) if re.fullmatch(r"(?:[0-9a-fA-F]{2})+", key or "") else (key or "").encode()
    try:
        if scheme == "xor":
            if not raw_key:
                return {"error": "xor needs a key (hex or text)"}
            out = xor_bytes(data, raw_key)
            note = "repeating-key XOR"
        elif scheme in ("rc4", "arc4"):
            if not raw_key:
                return {"error": "rc4 needs a key"}
            out = rc4(data, raw_key)
            note = "RC4"
        elif scheme in ("aes-cbc", "aes"):
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            ivb = bytes.fromhex(iv) if re.fullmatch(r"(?:[0-9a-fA-F]{2})+", iv or "") else (iv or "").encode()
            if len(raw_key) not in (16, 24, 32):
                return {"error": f"AES key must be 16/24/32 bytes, got {len(raw_key)}"}
            if len(ivb) != 16:
                return {"error": "AES-CBC requires a 16-byte IV"}
            dec = Cipher(algorithms.AES(raw_key), modes.CBC(ivb)).decryptor()
            out = dec.update(data) + dec.finalize()
            # strip PKCS#7
            if out and 1 <= out[-1] <= 16:
                out = out[:-out[-1]]
            note = "AES-CBC (PKCS#7 stripped)"
        elif scheme in ("aes-ecb",):
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            dec = Cipher(algorithms.AES(raw_key), modes.ECB()).decryptor()
            out = dec.update(data) + dec.finalize()
            if out and 1 <= out[-1] <= 16:
                out = out[:-out[-1]]
            note = "AES-ECB (PKCS#7 stripped)"
        elif scheme in ("single-byte", "singlebyte"):
            best = max(range(256), key=lambda k: _printable_score(xor_bytes(data[:4096], bytes([k]))))
            out = xor_bytes(data, bytes([best]))
            return {"scheme": "single-byte-xor", "key": f"{best:02x}",
                    "preview": out[:600].decode("latin-1", "replace"),
                    "entropy": round(entropy(out), 3), "confidence": 60}
        else:
            return {"error": f"unsupported scheme {scheme}; use xor/rc4/aes-cbc/aes-ecb/single-byte"}
    except ImportError:
        return {"error": "install cryptography for AES decryption"}
    except Exception as exc:
        return {"error": f"{scheme} decryption failed: {exc}"}
    return {"scheme": scheme, "note": note, "key": raw_key.hex() if raw_key else "",
            "size": len(out), "entropy": round(entropy(out), 3),
            "printable_ratio": round(_printable_score(out) / max(1, len(out[:2048])), 2),
            "preview": out[:800].decode("latin-1", "replace"),
            "preview_hex": out[:64].hex(),
            "looks_valid": _printable_score(out[:2048]) / max(1, len(out[:2048])) > 0.8}


def _printable_score(data: bytes) -> int:
    return sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))


def decode_hexdump(text: str) -> Dict[str, Any]:
    """Decode a hexdump (offset + hex + ascii) or a raw hex blob."""
    out = bytearray()
    lines = 0
    for line in text.splitlines():
        m = re.match(r"\s*[0-9a-fA-F]{4,8}\s*[: ]\s*((?:[0-9a-fA-F]{2,4}\s+)+)", line)
        if m:
            chunk = re.sub(r"[^0-9a-fA-F]", "", m.group(1))
            if len(chunk) % 2:
                chunk = chunk[:-1]
            try:
                out += bytes.fromhex(chunk)
                lines += 1
            except Exception:
                continue
    if not out:
        raw = re.sub(r"(?i)0x|[^0-9a-fA-F]", "", text)
        if len(raw) % 2:
            raw = raw[:-1]
        try:
            out = bytearray(bytes.fromhex(raw))
        except Exception:
            return {"error": "no hex data found"}
    return {"lines": lines, "size": len(out), "preview": out[:800].decode("latin-1", "replace"),
            "preview_hex": out[:64].hex(), "entropy": round(entropy(bytes(out)), 3),
            "sha256": hashlib.sha256(bytes(out)).hexdigest()}


# --------------------------------------------------------------------------- #
#  Misc transforms used by the agent
# --------------------------------------------------------------------------- #
def caesar(value: str, shift: int = 13) -> Dict[str, Any]:
    out = []
    for ch in value:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            out.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            out.append(ch)
    return {"shift": shift, "output": "".join(out)}


def frequency_analysis(text: str) -> Dict[str, Any]:
    letters = [c.lower() for c in text if c.isalpha()]
    if not letters:
        return {"error": "no alphabetic characters"}
    counts = Counter(letters)
    total = len(letters)
    english = {"e": 12.7, "t": 9.1, "a": 8.2, "o": 7.5, "i": 7.0, "n": 6.7,
               "s": 6.3, "h": 6.1, "r": 6.0, "d": 4.3, "l": 4.0, "c": 2.8,
               "u": 2.8, "m": 2.4, "w": 2.4, "f": 2.2, "g": 2.0, "y": 2.0,
               "p": 1.9, "b": 1.5, "v": 1.0, "k": 0.8, "j": 0.15, "x": 0.15,
               "q": 0.10, "z": 0.07}
    observed = {c: round(n / total * 100, 2) for c, n in counts.most_common()}
    deviation = sum(abs(observed.get(c, 0) - pct) for c, pct in english.items()) / len(english)
    return {"total_letters": total, "distribution": observed,
            "english_deviation": round(deviation, 2),
            "verdict": "likely natural language" if deviation < 6 else
                       ("possibly substituted/encoded" if deviation < 12 else "unusual distribution")}


def identify_encoding(value: str) -> Dict[str, Any]:
    """Fast heuristic classifier before attempting full decoding."""
    v = value.strip()
    hints = []
    if re.fullmatch(r"[A-Za-z0-9+/=\s]+", v) and len(v.replace("\n", "").replace(" ", "")) % 4 == 0 and len(v) > 8:
        hints.append(("base64", 70))
    if re.fullmatch(r"[A-Z2-7=\s]+", v) and len(v) > 8:
        hints.append(("base32", 60))
    if re.fullmatch(r"(?:[0-9a-fA-F]{2}){4,}", re.sub(r"\s+", "", v)):
        hints.append(("hex", 80))
    if re.fullmatch(r"[01]{8,}", re.sub(r"\s+", "", v)):
        hints.append(("binary", 80))
    if "%" in v:
        hints.append(("url-encoded", 70))
    if "&" in v and ";" in v:
        hints.append(("html-entities", 60))
    if re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", v):
        hints.append(("jwt", 90))
    if v.startswith("$2") and v.count("$") >= 3:
        hints.append(("bcrypt", 80))
    if v.startswith("-----BEGIN"):
        hints.append(("pem", 95))
    if re.match(r"^[A-Za-z0-9+/]{8,}$", v) and len(v) % 2 == 0 and not re.search(r"[01]", v):
        hints.append(("base64-or-hex", 40))
    hints.sort(key=lambda x: x[1], reverse=True)
    return {"length": len(v), "hints": [{"encoding": h, "confidence": c} for h, c in hints],
            "best": hints[0][0] if hints else "unknown"}
