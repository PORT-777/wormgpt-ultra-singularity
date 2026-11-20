# backend/security_ops/__init__.py
# Public entry point for the CyberOps toolkit. Every capability is exposed
# as a named action in ``ACTIONS`` and can be invoked through::
#
#     from security_ops import run_action
#     run_action("pe", path="sample.exe", allow_host=False)
#
# File-driven actions accept any of ``path`` / ``hex`` / ``base64`` /
# ``text`` / ``data``. The HTTP API keeps ``allow_host=False`` so callers stay
# inside the workspace; the agent tool enables it only in Full Access mode.

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from . import (advisory, code, detections, elfmacho, encoding, forensics,
               knowledge, logs, network, pe, reports, util)

__all__ = ["ACTIONS", "run_action", "list_actions", "capabilities",
           "run", "ACTION_ALIASES"]

ACTIONS: Dict[str, Dict[str, Any]] = {}
ACTION_ALIASES: Dict[str, str] = {}


# --------------------------------------------------------------------------- #
#  Registration helpers
# --------------------------------------------------------------------------- #
def _register(name: str, description: str, params: str, input_kind: str = "none",
              category: str = "general", aliases: Sequence[str] = ()) -> Callable:
    def deco(fn: Callable) -> Callable:
        ACTIONS[name] = {"action": name, "description": description,
                         "params": params, "input": input_kind,
                         "category": category, "handler": fn}
        for alias in aliases:
            ACTION_ALIASES[alias] = name
        return fn
    return deco


def _bytes(kw: Dict[str, Any], allow_host: bool) -> tuple:
    return util.bytes_from_kwargs(kw, allow_host=allow_host)


def _text(kw: Dict[str, Any], allow_host: bool) -> tuple:
    return util.text_from_kwargs(kw, allow_host=allow_host)


def _name(kw: Dict[str, Any], source: str) -> str:
    return str(kw.get("filename") or kw.get("name") or source)


def _list(kw: Dict[str, Any], key: str, default: Optional[Sequence[Any]] = None) -> List[Any]:
    value = kw.get(key)
    if value is None:
        return list(default or [])
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, list) else [parsed]
            except Exception:
                pass
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _int(kw: Dict[str, Any], key: str, default: int) -> int:
    try:
        return int(kw.get(key, default))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
#  Core triage
# --------------------------------------------------------------------------- #
@_register("file_info", "Detect file type, hashes, entropy and basic metadata.",
           "path|hex|base64|text|data, filename", "bytes", "triage",
           aliases=("fileinfo", "identify"))
def _file_info(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    info = util.file_type(data, _name(kw, source))
    return {"source": source, "size": len(data), "type": info,
            "hashes": util.hash_bytes(data),
            "entropy": round(util.entropy(data), 3),
            "byte_histogram_entropy": util.entropy_map(data)[:16]}


@_register("hashes", "Compute MD5/SHA1/SHA256/SHA512 and fuzzy hashes.",
           "path|hex|base64|data", "bytes", "triage", aliases=("hash",))
def _hashes(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **util.hash_bytes(data)}


@_register("strings", "Extract ASCII/UTF-16 strings with optional IOC filtering.",
           "path|hex|base64|data, min_len, limit, iocs_only", "bytes", "triage",
           aliases=("extract_strings",))
def _strings(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    result = util.extract_strings(data, _int(kw, "min_len", 4), True, True,
                                  _int(kw, "limit", 5000))
    if kw.get("iocs_only"):
        joined = "\n".join(result["ascii"] + result["unicode"])
        result = {"iocs": util.extract_iocs(joined)}
    return {"source": source, "size": len(data), **result}


@_register("entropy", "Whole-file and block entropy, high-entropy regions.",
           "path|hex|base64|data, block", "bytes", "triage", aliases=("entropy_map",))
def _entropy(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    block = _int(kw, "block", 256)
    return {"source": source, "size": len(data),
            "entropy": round(util.entropy(data), 3),
            "blocks": util.entropy_map(data, block=block),
            "high_entropy": util.high_entropy_regions(data),
            "assessment": ("packed/encrypted" if util.entropy(data) > 7.2 else
                           "possibly compressed" if util.entropy(data) > 6.5 else "normal")}


@_register("iocs", "Extract indicators (IPs, domains, URLs, hashes, wallets, CVEs, paths).",
           "path|hex|base64|text|data", "text", "triage", aliases=("extract_iocs",))
def _iocs(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    result = util.extract_iocs(text)
    return {"source": source, **result}


@_register("ioc_export", "Extract IOCs and export JSON/CSV/text/STIX/MISP.",
           "path|text, fmt, source, save", "text", "triage", aliases=("export_iocs",))
def _ioc_export(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    iocs = util.extract_iocs(text)
    filename, content = util.ioc_export_payload(iocs, str(kw.get("fmt", "json")),
                                                str(kw.get("source") or source))
    out = {"ioc_count": iocs.get("count", 0), "format": kw.get("fmt", "json"),
           "filename": filename, "content": content, "categories": iocs.get("categories", {})}
    if kw.get("save"):
        out["path"] = util.write_artifact(filename, content, kind="iocs",
                                          allow_host=allow_host)
    return out


@_register("hexdump", "Format bytes as a classic hex/ASCII dump.",
           "path|hex|base64|data, width, limit", "bytes", "triage")
def _hexdump(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, "dump": network.hex_dump(data, _int(kw, "width", 16),
                                                      _int(kw, "limit", 1024))}


# --------------------------------------------------------------------------- #
#  Executables
# --------------------------------------------------------------------------- #
@_register("pe", "Full PE analysis: headers, sections, imports, exports, resources, "
                 "rich header, signature, packer, anomalies, MITRE.",
           "path|hex|base64|data, filename, extract", "bytes", "binary", aliases=("analyze_pe",))
def _pe(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return pe.analyze(data, _name(kw, source), extract=bool(kw.get("extract")))


@_register("elf", "ELF analysis: header, sections, segments, dynamic entries, symbols, "
                  "mitigations, packing indicators.", "path|hex|base64|data, filename",
           "bytes", "binary", aliases=("analyze_elf",))
def _elf(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return elfmacho.analyze_elf(data, _name(kw, source))


@_register("macho", "Mach-O analysis: fat/thin, load commands, encryption, entitlements, "
                    "code signature indicators.", "path|hex|base64|data, filename",
           "bytes", "binary", aliases=("analyze_macho", "mach-o"))
def _macho(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return elfmacho.analyze_macho(data, _name(kw, source))


@_register("shellcode", "Shellcode triage: architecture guess, disassembly, API/pattern "
                        "hits and intent.", "path|hex|base64|data, arch", "bytes",
           "binary", aliases=("analyze_shellcode",))
def _shellcode(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **code.analyze_shellcode(data, str(kw.get("arch", "")))}


@_register("rop", "Scan for ROP gadgets and stack-pivot patterns.",
           "path|hex|base64|data, arch, limit", "bytes", "binary", aliases=("scan_rop",))
def _rop(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **code.scan_rop(data, str(kw.get("arch", "x64")),
                                              _int(kw, "limit", 300))}


@_register("crypto", "Find cryptographic constants, keys, IVs and encoded blobs.",
           "path|hex|base64|data", "bytes", "binary", aliases=("scan_crypto",))
def _crypto(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **code.scan_crypto(data)}


@_register("xor", "Recover XOR keys (single/repeating) or decrypt with a known key.",
           "path|hex|base64|data, known_plaintext, key, max_key_len", "bytes",
           "binary", aliases=("xor_brute",))
def _xor(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **code.xor_brute(
        data, str(kw.get("known_plaintext") or ""), str(kw.get("key") or ""),
        _int(kw, "max_key_len", 16))}


@_register("anti_analysis", "Detect anti-debug, anti-VM, sandbox and evasion checks.",
           "path|hex|base64|data, imports", "bytes", "binary", aliases=("anti_debug",))
def _anti_analysis(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **code.anti_analysis_scan(data, imports=_list(kw, "imports"))}


@_register("intent", "Predict malware intent and score behaviour categories.",
           "path|hex|base64|data, strings, imports", "bytes", "binary",
           aliases=("predict_intent",))
def _intent(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **code.predict_intent(
        data, str(kw.get("strings") or "") or None, _list(kw, "imports") or None)}


@_register("family", "Match known malware families by markers and API usage.",
           "path|hex|base64|data, strings, imports", "bytes", "binary",
           aliases=("match_family",))
def _family(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **code.match_family(
        data, str(kw.get("strings") or "") or None, _list(kw, "imports") or None)}


@_register("behavior_dna", "Build a behaviour DNA profile from strings/imports and "
                           "MITRE techniques.", "path|hex|base64|data, imports",
           "bytes", "binary", aliases=("dna",))
def _behavior_dna(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **code.behavior_dna(data, _list(kw, "imports") or None)}


@_register("compare", "Pairwise sample similarity: byte ratio, chunk Jaccard, clusters.",
           "paths (list of paths or {label,path})", "files", "binary",
           aliases=("compare_samples", "similarity"))
def _compare(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    entries = []
    raw = kw.get("paths") or kw.get("files")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = [p.strip() for p in raw.split(",") if p.strip()]
    for item in raw or []:
        if isinstance(item, dict):
            path = item.get("path") or item.get("file")
            label = item.get("label") or (util.Path(str(path)).name if path else "")
        else:
            path, label = str(item), util.Path(str(item)).name
        p = util.resolve_path(str(path), allow_host=allow_host)
        entries.append((label or p.name, util.read_limited(p)))
    if len(entries) < 2:
        raise ValueError("provide at least two paths")
    return code.compare_samples(entries)


# --------------------------------------------------------------------------- #
#  Detection engineering
# --------------------------------------------------------------------------- #
@_register("mitre", "Map text/telemetry to MITRE ATT&CK techniques.",
           "path|text, extra, min_confidence", "text", "detection",
           aliases=("mitre_map", "attack_map"))
def _mitre(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **detections.mitre_map(
        text, _list(kw, "extra"), _int(kw, "min_confidence", 30))}


@_register("mitre_navigator", "Generate an ATT&CK Navigator layer from text.",
           "path|text, extra, name", "text", "detection", aliases=("navigator",))
def _mitre_navigator(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    mapped = detections.mitre_map(text, _list(kw, "extra"))
    return {"source": source, "mapped": mapped,
            "layer": detections.mitre_navigator(mapped, str(kw.get("name")
                                                           or "CyberOps coverage"))}


@_register("coverage", "Score ATT&CK coverage for techniques and detections.",
           "techniques (list), detections (list)", "none", "detection")
def _coverage(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return detections.coverage_score(_list(kw, "techniques"), _list(kw, "detections"))


@_register("defense_gaps", "Analyse defense-in-depth gaps from deployed tools.",
           "tools (list)", "none", "detection", aliases=("gaps",))
def _defense_gaps(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return detections.defense_gap_analysis(_list(kw, "tools"))


@_register("yara_generate", "Generate a YARA rule from text and/or sample bytes.",
           "path|text|hex|base64|data, name, description, author, max_strings, is_pe",
           "mixed", "detection", aliases=("yara_gen", "make_yara"))
def _yara_generate(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text = str(kw.get("text") or kw.get("content") or "")
    data = b""
    if any(k in kw for k in ("path", "hex", "base64", "data")):
        data, _ = _bytes(kw, allow_host)
    return detections.yara_generate(
        text=text, data=data, name=str(kw.get("name") or ""),
        description=str(kw.get("description") or ""),
        author=str(kw.get("author") or "CyberOps"),
        max_strings=_int(kw, "max_strings", 12),
        is_pe=bool(kw.get("is_pe")))


@_register("yara_scan", "Scan bytes with a YARA rule (native yara if installed, "
                        "builtin fallback otherwise).", "rule_text, path|hex|base64|data",
           "mixed", "detection", aliases=("yara",))
def _yara_scan(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    rule = str(kw.get("rule_text") or kw.get("rule") or kw.get("yara") or "")
    if not rule:
        raise ValueError("rule_text is required")
    data, source = _bytes(kw, allow_host)
    result = detections.yara_scan(rule, data, _name(kw, source))
    result["source"] = source
    return result


@_register("sigma_generate", "Generate a Sigma rule from observed activity text.",
           "path|text, title, description, author, level", "text", "detection",
           aliases=("sigma_gen", "make_sigma"))
def _sigma_generate(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **detections.sigma_generate(
        text=text, title=str(kw.get("title") or ""),
        description=str(kw.get("description") or ""),
        author=str(kw.get("author") or "CyberOps"),
        level=str(kw.get("level") or ""))}


@_register("sigma_convert", "Convert Sigma to Splunk/KQL/EQL/AQL/YARA-L.",
           "rule_text, target", "mixed", "detection", aliases=("sigma2query",))
def _sigma_convert(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    rule = str(kw.get("rule_text") or kw.get("rule") or "")
    if not rule:
        raise ValueError("rule_text is required")
    return detections.sigma_convert(rule, str(kw.get("target") or "all"))


@_register("sigma_validate", "Validate Sigma rule structure and fields.",
           "rule_text", "mixed", "detection")
def _sigma_validate(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    rule = str(kw.get("rule_text") or kw.get("rule") or "")
    if not rule:
        raise ValueError("rule_text is required")
    return detections.sigma_validate(rule)


@_register("sigma_test", "Test a Sigma rule against JSON sample events.",
           "rule_text, samples (list)", "mixed", "detection")
def _sigma_test(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    rule = str(kw.get("rule_text") or kw.get("rule") or "")
    if not rule:
        raise ValueError("rule_text is required")
    return detections.sigma_test(rule, _list(kw, "samples"))


@_register("query_build", "Build hunt queries (SPL/KQL/EQL/AQL/YARA-L) from a description.",
           "description, platform, time_range", "none", "detection",
           aliases=("build_query",))
def _query_build(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    description = str(kw.get("description") or kw.get("text") or kw.get("query") or "")
    if not description:
        raise ValueError("description is required")
    return detections.query_build(description, str(kw.get("platform") or "all"),
                                  str(kw.get("time_range") or "24h"))


@_register("query_translate", "Translate a query between SPL/KQL/EQL/AQL/YARA-L.",
           "query, source, target", "none", "detection", aliases=("translate_query",))
def _query_translate(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    query = str(kw.get("query") or kw.get("text") or "")
    if not query:
        raise ValueError("query is required")
    return detections.query_translate(query, str(kw.get("source") or ""),
                                      str(kw.get("target") or "kql"))


@_register("hunt", "Build a structured threat-hunt plan from a hypothesis.",
           "hypothesis", "none", "detection", aliases=("hunt_plan",))
def _hunt(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    hypothesis = str(kw.get("hypothesis") or kw.get("text") or "")
    if not hypothesis:
        raise ValueError("hypothesis is required")
    return detections.hunt_plan(hypothesis)


# --------------------------------------------------------------------------- #
#  Logs / timelines / email
# --------------------------------------------------------------------------- #
@_register("logs", "Parse and analyse Windows/Sysmon/auth/web/Suricata/Zeek/cloud logs.",
           "path|text, kind, max_lines", "text", "logs", aliases=("analyze_logs",))
def _logs(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **logs.analyze_logs(text, str(kw.get("kind") or "auto"),
                                                 _int(kw, "max_lines", 200000))}


@_register("timeline", "Merge timestamped items into an incident timeline with phases.",
           "items (list of {time,event}), or path|text", "mixed", "logs",
           aliases=("build_timeline",))
def _timeline(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    items = _list(kw, "items")
    if not items and any(k in kw for k in ("path", "text", "content")):
        text, _ = _text(kw, allow_host)
        items = [{"time": "", "event": line} for line in text.splitlines() if line.strip()]
    return logs.build_timeline(items)


@_register("beacon", "Analyse connection timestamps for C2 beaconing.",
           "times (list), or path|text", "mixed", "logs", aliases=("beacon_analysis",))
def _beacon(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    times = _list(kw, "times")
    if not times and any(k in kw for k in ("path", "text", "content")):
        text, _ = _text(kw, allow_host)
        times = [line.strip() for line in text.splitlines() if line.strip()]
    if not times:
        raise ValueError("times list is required")
    return logs.beacon_analysis(times)


@_register("lateral", "Build a lateral-movement graph from host/user events.",
           "events (list)", "mixed", "logs", aliases=("lateral_movement",))
def _lateral(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    events = _list(kw, "events")
    if not events:
        raise ValueError("events list is required")
    return logs.lateral_movement(events)


@_register("email", "Analyse email headers/body for spoofing, auth failures, "
                    "lookalikes and attachments.", "path|text", "text", "logs",
           aliases=("analyze_email", "phish"))
def _email(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **logs.analyze_email(text)}


@_register("lolbins", "Detect living-off-the-land binary abuse in command lines.",
           "path|text", "text", "logs", aliases=("scan_lolbins",))
def _lolbins(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **logs.scan_lolbins(text)}


@_register("persistence_scan", "Scan text/registry output for persistence mechanisms.",
           "path|text", "text", "logs", aliases=("scan_persistence",))
def _persistence_scan(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **logs.scan_persistence(text)}


# --------------------------------------------------------------------------- #
#  Network
# --------------------------------------------------------------------------- #
@_register("pcap", "Analyse PCAP/PCAPNG: flows, DNS, HTTP, TLS/JA3, beaconing, scans.",
           "path|base64|data, max_packets", "bytes", "network",
           aliases=("analyze_pcap", "pcap_analysis"))
def _pcap(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    result = network.analyze_pcap(kw, data)
    result["source"] = source
    return result


@_register("cluster_infra", "Cluster indicators by shared infrastructure/sample.",
           "indicators (list)", "none", "network", aliases=("infra_cluster",))
def _cluster_infra(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    indicators = _list(kw, "indicators")
    if isinstance(kw.get("indicators"), dict):
        indicators = kw["indicators"].get("indicators", [])
    return network.cluster_infrastructure(indicators)


@_register("tcp_stream", "Decode a raw TCP payload (HTTP/DNS/TLS/SSH/text/binary).",
           "path|hex|base64|data", "bytes", "network", aliases=("decode_tcp",))
def _tcp_stream(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **network.decode_tcp_stream(data)}


@_register("udp_payload", "Decode a raw UDP payload (DNS/text/binary).",
           "path|hex|base64|data", "bytes", "network", aliases=("decode_udp",))
def _udp_payload(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **network.decode_udp_payload(data)}


@_register("build_packet", "Craft a packet/PCAP with Scapy when available.",
           "src_ip, dst_ip, proto, src_port, dst_port, payload/flags/query", "none",
           "network", aliases=("craft_packet",))
def _build_packet(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return network.build_packet(**kw)


# --------------------------------------------------------------------------- #
#  Host / artifact forensics
# --------------------------------------------------------------------------- #
def _bytes_action(name: str, description: str, fn: Callable,
                  category: str = "forensics", aliases: Sequence[str] = ()) -> None:
    @_register(name, description, "path|hex|base64|data, filename", "bytes",
               category, aliases=aliases)
    def _handler(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
        data, source = _bytes(kw, allow_host)
        result = fn(data, _name(kw, source))
        if isinstance(result, dict):
            result.setdefault("source", source)
        return result


def _text_action(name: str, description: str, fn: Callable,
                 category: str = "forensics", aliases: Sequence[str] = ()) -> None:
    @_register(name, description, "path|text, filename", "text", category, aliases=aliases)
    def _handler(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
        text, source = _text(kw, allow_host)
        result = fn(text, _name(kw, source))
        if isinstance(result, dict):
            result.setdefault("source", source)
        return result


_bytes_action("lnk", "Parse Windows shortcut (.lnk) files.", forensics.analyze_lnk,
              aliases=("analyze_lnk",))
_bytes_action("prefetch", "Parse Windows prefetch (including MAM decompression).",
              forensics.analyze_prefetch, aliases=("analyze_prefetch",))
_bytes_action("registry_hive", "Heuristic Windows registry hive (regf) analysis.",
              forensics.analyze_registry_hive, aliases=("hive", "regf"))
_bytes_action("browser_db", "Analyse browser SQLite stores (history/logins/cookies).",
              forensics.analyze_browser_db, aliases=("browser", "sqlite_browser"))
_bytes_action("mft", "Parse NTFS MFT records and flag timestomping.",
              forensics.analyze_mft, aliases=("ntfs_mft",))
_bytes_action("shellbags", "Extract shellbag folder/USB/network artifacts.",
              forensics.analyze_shellbags, aliases=("analyze_shellbags",))
_bytes_action("jumplist", "Extract jumplist paths and DestList presence.",
              forensics.analyze_jumplist, aliases=("analyze_jumplist",))
_bytes_action("hibernation", "Triage hibernation file headers and entropy.",
              forensics.analyze_hibernation, aliases=("hiberfil",))
_bytes_action("stego", "Detect steganography indicators in images/audio.",
              forensics.analyze_stego, aliases=("analyze_stego", "steganography"))
_bytes_action("firmware", "Firmware triage: signatures, embedded files, credentials.",
              forensics.analyze_firmware, aliases=("analyze_firmware",))
_bytes_action("apk", "Analyse Android APK: manifest, permissions, libraries, IOCs.",
              forensics.analyze_apk, aliases=("analyze_apk",))
_bytes_action("ipa", "Analyse iOS IPA: Info.plist, entitlements, transport security.",
              forensics.analyze_ipa, aliases=("analyze_ipa",))
_bytes_action("bootkit", "Check MBR/UEFI artifacts for bootkit indicators.",
              forensics.analyze_bootkit, aliases=("analyze_bootkit",))
_text_action("reg", "Parse .reg text exports and flag persistence/tampering.",
              forensics.analyze_reg, aliases=("analyze_reg",))
_text_action("secrets", "Scan text/files for API keys, tokens and private keys.",
              forensics.scan_secrets, aliases=("scan_secrets", "secret_scan"))
_text_action("iac", "Review IaC/Docker/Kubernetes/Terraform/cloud configs.",
              forensics.analyze_iac, aliases=("analyze_iac", "dockerfile", "terraform"))
_text_action("fileless", "Detect fileless execution and encoded PowerShell payloads.",
              forensics.analyze_fileless, aliases=("analyze_fileless",))
_text_action("supply_chain", "Review package/build scripts for supply-chain risk.",
              forensics.analyze_supply_chain, aliases=("analyze_supply_chain",))


@_register("lsb", "Extract LSB data and detect embedded text/PE/ZIP payloads.",
           "path|hex|base64|data, max_bytes", "bytes", "forensics",
           aliases=("lsb_extract", "stego_lsb"))
def _lsb(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **forensics.lsb_extract(data,
                                                      max_bytes=_int(kw, "max_bytes", 65536))}


# --------------------------------------------------------------------------- #
#  Encoding / crypto utilities
# --------------------------------------------------------------------------- #
@_register("decode", "Recursively peel encoding layers (base64/hex/url/rot13/...).",
           "path|text, max_layers", "text", "encoding",
           aliases=("auto_decode", "deobfuscate"))
def _decode(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **encoding.auto_decode(text, _int(kw, "max_layers", 8))}


@_register("decode_all", "Run every single-step decoder and rank plausible outputs.",
           "path|text", "text", "encoding", aliases=("try_decoders",))
def _decode_all(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, "results": encoding.try_all_decoders(text)}


@_register("encode", "Encode text (base64/base32/hex/url/rot13/PowerShell/etc.).",
           "path|text, fmt", "text", "encoding", aliases=("encoder",))
def _encode(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **encoding.encode(text, str(kw.get("fmt") or "base64"))}


@_register("jwt", "Decode and assess a JWT (alg, claims, exp, kid/jku risks).",
           "token or path|text", "mixed", "encoding", aliases=("analyze_jwt",))
def _jwt(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    token = str(kw.get("token") or kw.get("jwt") or "")
    if not token:
        token, _ = _text(kw, allow_host)
    return encoding.analyze_jwt(token.strip())


@_register("jwt_crack", "Try a wordlist against an HMAC JWT.",
           "token, wordlist", "none", "encoding", aliases=("crack_jwt",))
def _jwt_crack(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    token = str(kw.get("token") or kw.get("jwt") or "")
    if not token:
        raise ValueError("token is required")
    return encoding.crack_jwt(token, str(kw.get("wordlist") or ""))


@_register("cert", "Parse an X.509 certificate (PEM/DER) and assess validity/SANs.",
           "path|hex|base64|text|data", "bytes", "encoding",
           aliases=("certificate", "x509"))
def _cert(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    if kw.get("text") or kw.get("content"):
        text, source = _text(kw, allow_host)
        return {"source": source, **encoding.analyze_certificate(text.encode("latin-1", "replace"))}
    data, source = _bytes(kw, allow_host)
    return {"source": source, **encoding.analyze_certificate(data)}


@_register("hash_id", "Identify hash format plus hashcat/John modes.",
           "value or path|text", "mixed", "encoding", aliases=("identify_hash",))
def _hash_id(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    value = str(kw.get("value") or kw.get("hash") or "")
    if not value:
        value, _ = _text(kw, allow_host)
    return encoding.identify_hash(value.strip())


@_register("passwords", "Analyse a password/wordlist file for weakness and patterns.",
           "path|text, top_n", "text", "encoding", aliases=("wordlist",))
def _passwords(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **encoding.analyze_passwords(text, _int(kw, "top_n", 30))}


@_register("c2_decrypt", "Decrypt C2 payloads with XOR/RC4/AES-CBC/ECB/single-byte.",
           "path|hex|base64|data, scheme, key, iv", "bytes", "encoding",
           aliases=("decrypt_c2",))
def _c2_decrypt(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    data, source = _bytes(kw, allow_host)
    return {"source": source, **encoding.decrypt_c2(
        data, str(kw.get("scheme") or "xor"), str(kw.get("key") or ""),
        str(kw.get("iv") or ""))}


@_register("hex_decode", "Decode a hexdump or raw hex blob to bytes.",
           "path|text", "text", "encoding", aliases=("hexdump_decode",))
def _hex_decode(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **encoding.decode_hexdump(text)}


@_register("caesar", "Apply a Caesar shift.", "text, shift", "mixed", "encoding")
def _caesar(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text = str(kw.get("text") or kw.get("value") or "")
    if not text:
        text, _ = _text(kw, allow_host)
    return encoding.caesar(text, _int(kw, "shift", 13))


@_register("frequency", "Letter-frequency analysis to spot substitution ciphers.",
           "path|text", "text", "encoding", aliases=("frequency_analysis",))
def _frequency(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **encoding.frequency_analysis(text)}


@_register("encoding_id", "Heuristically classify an encoding before decoding.",
           "path|text", "text", "encoding", aliases=("identify_encoding",))
def _encoding_id(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text, source = _text(kw, allow_host)
    return {"source": source, **encoding.identify_encoding(text)}


# --------------------------------------------------------------------------- #
#  Advisory / decision support
# --------------------------------------------------------------------------- #
@_register("actor_profile", "Match threat-actor profiles by name/alias/TTP/malware.",
           "name, techniques, malware, infrastructure", "none", "advisory",
           aliases=("actor", "attribution_profile"))
def _actor_profile(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.actor_profile(str(kw.get("name") or ""), _list(kw, "techniques"),
                                  _list(kw, "malware"), _list(kw, "infrastructure"))


@_register("attribute", "Attribute activity using text, TTPs and infrastructure.",
           "path|text, techniques, malware, infrastructure", "mixed", "advisory",
           aliases=("attribution",))
def _attribute(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    text = str(kw.get("text") or "")
    if not text and any(k in kw for k in ("path", "content")):
        text, _ = _text(kw, allow_host)
    return advisory.attribute_activity(text, _list(kw, "techniques"),
                                       _list(kw, "malware"),
                                       _list(kw, "infrastructure"))


@_register("kill_chain", "Map techniques to Lockheed Martin kill-chain phases.",
           "techniques (list)", "none", "advisory")
def _kill_chain(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.kill_chain(_list(kw, "techniques"))


@_register("diamond", "Build a Diamond Model of intrusion activity.",
           "adversary, capability, infrastructure, victim", "none", "advisory",
           aliases=("diamond_model",))
def _diamond(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.diamond_model(
        str(kw.get("adversary") or ""), str(kw.get("capability") or ""),
        str(kw.get("infrastructure") or ""), str(kw.get("victim") or ""),
        str(kw.get("confidence") or ""))


@_register("severity", "Calculate business-aware severity and SLA.",
           "cvss, confidence, exposure, data_sensitivity, blast_radius, exploited, "
           "privileged, internet_facing, compensating_controls", "none", "advisory",
           aliases=("risk_score", "severity_calc"))
def _severity(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.severity_calculator(
        cvss=kw.get("cvss", 0), confidence=str(kw.get("confidence") or "medium"),
        exposure=str(kw.get("exposure") or "internal"),
        data_sensitivity=str(kw.get("data_sensitivity") or "internal"),
        blast_radius=str(kw.get("blast_radius") or "single-host"),
        exploited=bool(kw.get("exploited")), privileged=bool(kw.get("privileged")),
        internet_facing=bool(kw.get("internet_facing")),
        compensating_controls=_list(kw, "compensating_controls"))


@_register("threat_model", "Generate a STRIDE/PASTA/LINDDUN threat model.",
           "description, methodology, assets, trust_boundaries, actors", "mixed",
           "advisory", aliases=("stride", "pasta"))
def _threat_model(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    description = str(kw.get("description") or kw.get("text") or "")
    if not description and any(k in kw for k in ("path", "content")):
        description, _ = _text(kw, allow_host)
    assets = _list(kw, "assets")
    return advisory.threat_model(description, str(kw.get("methodology") or "stride"),
                                 assets, _list(kw, "trust_boundaries"),
                                 _list(kw, "actors"))


@_register("attack_surface", "Score and rank exposed assets by attack surface.",
           "assets (list of {name,criticality,exposure,services})", "none", "advisory")
def _attack_surface(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.attack_surface(_list(kw, "assets"))


@_register("posture", "Score security posture by control domain and framework.",
           "controls (list), framework", "none", "advisory",
           aliases=("posture_score",))
def _posture(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.posture_score(_list(kw, "controls"), str(kw.get("framework") or ""))


@_register("fp_tuning", "Suggest false-positive tuning for a noisy detection.",
           "detection, context, known_benign", "none", "advisory",
           aliases=("tune_detection",))
def _fp_tuning(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.false_positive_tuning(
        str(kw.get("detection") or kw.get("text") or ""), _list(kw, "context"),
        _list(kw, "known_benign"))


@_register("explain_anomaly", "Explain deviations from a baseline in plain language.",
           "features (dict), baseline (dict)", "none", "advisory",
           aliases=("anomaly_explain",))
def _explain_anomaly(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    features = kw.get("features") or {}
    baseline = kw.get("baseline") or {}
    if isinstance(features, str):
        try:
            features = json.loads(features)
        except Exception:
            features = {}
    if isinstance(baseline, str):
        try:
            baseline = json.loads(baseline)
        except Exception:
            baseline = {}
    return advisory.explain_anomaly(features, baseline)


@_register("zero_day", "Structure a suspected zero-day investigation.",
           "observations, artifacts, crash_signatures", "none", "advisory",
           aliases=("zero_day_hypothesis",))
def _zero_day(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.zero_day_hypothesis(_list(kw, "observations"),
                                        _list(kw, "artifacts"),
                                        _list(kw, "crash_signatures"))


@_register("chain_vulns", "Detect compound attack paths across findings.",
           "vulns (list of {type/name,severity})", "none", "advisory",
           aliases=("vulnerability_chain",))
def _chain_vulns(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.chain_vulnerabilities(_list(kw, "vulns"))


@_register("patch_priority", "Rank vulnerabilities by exploitability, exposure and asset value.",
           "vulns (list), asset_criticality", "none", "advisory",
           aliases=("patch_prioritization",))
def _patch_priority(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.patch_priority(_list(kw, "vulns"),
                                   str(kw.get("asset_criticality") or "medium"))


@_register("crisis_comms", "Draft holding statements for internal/executive/regulator/public.",
           "incident, audience, severity, confirmed_facts, unknowns, actions, contact",
           "none", "advisory", aliases=("comms",))
def _crisis_comms(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.crisis_comms(
        str(kw.get("incident") or kw.get("text") or ""),
        str(kw.get("audience") or "internal"), str(kw.get("severity") or "high"),
        _list(kw, "confirmed_facts"), _list(kw, "unknowns"), _list(kw, "actions"),
        str(kw.get("contact") or ""))


@_register("compliance_map", "Map findings to compliance control themes.",
           "findings (list), framework", "none", "advisory",
           aliases=("map_compliance",))
def _compliance_map(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return advisory.map_findings_to_compliance(_list(kw, "findings"),
                                               str(kw.get("framework") or "NIST-CSF"))


# --------------------------------------------------------------------------- #
#  Reports
# --------------------------------------------------------------------------- #
@_register("report", "Generate a Markdown/JSON report for any audience.",
           "kind, title, subject, findings, iocs, mitre, timeline, metadata, "
           "recommendations, evidence, fmt, save", "none", "report",
           aliases=("build_report", "generate_report"))
def _report(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    result = reports.generate_report(
        kind=str(kw.get("kind") or "technical"), title=str(kw.get("title") or ""),
        subject=str(kw.get("subject") or ""), findings=_list(kw, "findings"),
        iocs=kw.get("iocs") or {}, mitre=_list(kw, "mitre"),
        timeline=_list(kw, "timeline"), metadata=kw.get("metadata") or {},
        recommendations=_list(kw, "recommendations"), evidence=_list(kw, "evidence"),
        fmt=str(kw.get("fmt") or "markdown"), save=bool(kw.get("save")),
        allow_host=allow_host)
    return result


@_register("incident_narrative", "Turn a timeline into a prose incident narrative.",
           "timeline, subject, initial_access, impact, actor", "none", "report",
           aliases=("narrative",))
def _incident_narrative(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return reports.incident_narrative(
        _list(kw, "timeline"), str(kw.get("subject") or ""),
        str(kw.get("initial_access") or ""), str(kw.get("impact") or ""),
        str(kw.get("actor") or ""))


@_register("custody", "Generate an evidence chain-of-custody table.",
           "evidence (list), case_id, analyst", "none", "report",
           aliases=("chain_of_custody",))
def _custody(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    evidence = _list(kw, "evidence")
    if not evidence and any(k in kw for k in ("path", "hex", "base64")):
        data, source = _bytes(kw, allow_host)
        evidence = [{"item": source, "type": util.file_type(data, source)["type"],
                     "data": data}]
    return reports.chain_of_custody(evidence, str(kw.get("case_id") or ""),
                                    str(kw.get("analyst") or ""))


@_register("lessons", "Build an after-action / lessons-learned review.",
           "incident, went_well, went_wrong, root_causes, actions", "none",
           "report", aliases=("lessons_learned", "after_action"))
def _lessons(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    return reports.lessons_learned(
        str(kw.get("incident") or ""), _list(kw, "went_well"),
        _list(kw, "went_wrong"), _list(kw, "root_causes"), _list(kw, "actions"))


@_register("compliance_report", "Generate a compliance-oriented findings report.",
           "framework, findings, evidence, subject, save", "none", "report")
def _compliance_report(kw: Dict[str, Any], allow_host: bool) -> Dict[str, Any]:
    result = reports.compliance_report(
        str(kw.get("framework") or "NIST-CSF"), _list(kw, "findings"),
        _list(kw, "evidence"), str(kw.get("subject") or ""))
    if kw.get("save"):
        result["path"] = util.write_artifact(result["filename"], result["content"],
                                             kind="reports", allow_host=allow_host)
    return result


# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #
def _resolve(action: str) -> str:
    key = str(action or "").strip().lower().replace("-", "_")
    if key in ACTIONS:
        return key
    if key in ACTION_ALIASES:
        return ACTION_ALIASES[key]
    raise ValueError(f"unknown action '{action}'. Use list_actions() to see {len(ACTIONS)} actions.")


def run_action(action: str, allow_host: bool = False, **kwargs: Any) -> Dict[str, Any]:
    """Execute a named action with kwargs. Raises ValueError on unknown action."""
    key = _resolve(action)
    handler = ACTIONS[key]["handler"]
    result = handler(kwargs, bool(allow_host))
    if not isinstance(result, dict):
        result = {"result": result}
    result.setdefault("action", key)
    return result


# Short alias used by the agent tool.
run = run_action


def list_actions() -> List[Dict[str, Any]]:
    """Return action metadata (no handlers) for discovery/UI."""
    rows = []
    for name, spec in sorted(ACTIONS.items()):
        rows.append({"action": name, "category": spec["category"],
                     "description": spec["description"], "params": spec["params"],
                     "input": spec["input"],
                     "aliases": sorted(a for a, t in ACTION_ALIASES.items() if t == name)})
    return rows


def capabilities() -> Dict[str, Any]:
    """Describe the toolkit, modules and optional dependencies."""
    optional = {}
    for module_name in ("pefile", "capstone", "yara", "scapy", "dpkt", "elftools",
                        "oletools", "volatility3", "cryptography", "PIL", "yaml"):
        optional[module_name] = util.optional_dependency(module_name) \
            if hasattr(util, "optional_dependency") else _have(module_name)
    categories: Dict[str, int] = {}
    for spec in ACTIONS.values():
        categories[spec["category"]] = categories.get(spec["category"], 0) + 1
    return {
        "name": "CyberOps",
        "version": "1.0",
        "action_count": len(ACTIONS),
        "categories": categories,
        "actions": list_actions(),
        "optional_dependencies": optional,
        "notes": [
            "All analysis is local and offline; no telemetry leaves the host.",
            "HTTP API calls are sandboxed to the workspace; the agent tool can "
            "use host paths only in Full Access mode.",
            "Heuristic results require analyst validation before action.",
        ],
    }


def _have(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except Exception:
        return False
