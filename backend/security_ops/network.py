# backend/security_ops/network.py
# Network traffic analysis without external dependencies: classic PCAP and
# PCAPNG parsing, protocol decoding (Ethernet/IPv4/IPv6/TCP/UDP/ICMP/DNS/HTTP),
# flow reconstruction, JA3/JA3S client/server fingerprints, beacon detection,
# DNS-tunnel scoring, infrastructure clustering and packet crafting helpers.

from __future__ import annotations

import hashlib
import ipaddress
import math
import re
import socket
import struct
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .util import (entropy, parse_time, severity_rank, human_size)

# --------------------------------------------------------------------------- #
#  Low-level parsing
# --------------------------------------------------------------------------- #
PCAP_MAGIC = {
    b"\xd4\xc3\xb2\xa1": ("<", "usec"),
    b"\xa1\xb2\xc3\xd4": (">", "usec"),
    b"\x4d\x3c\xb2\xa1": ("<", "nsec"),
    b"\xa1\xb2\x3c\x4d": (">", "nsec"),
}

ETH_TYPES = {0x0800: "IPv4", 0x86DD: "IPv6", 0x0806: "ARP", 0x8100: "VLAN",
             0x88CC: "LLDP", 0x8847: "MPLS"}

TCP_FLAGS = {0x01: "FIN", 0x02: "SYN", 0x04: "RST", 0x08: "PSH",
             0x10: "ACK", 0x20: "URG", 0x40: "ECE", 0x80: "CWR"}

WELL_KNOWN_PORTS = {
    20: "ftp-data", 21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    67: "dhcp", 68: "dhcp", 69: "tftp", 80: "http", 110: "pop3", 111: "rpcbind",
    123: "ntp", 135: "msrpc", 137: "netbios-ns", 138: "netbios-dgm", 139: "netbios-ssn",
    143: "imap", 161: "snmp", 162: "snmptrap", 389: "ldap", 443: "https", 445: "smb",
    465: "smtps", 500: "isakmp", 514: "syslog", 587: "submission", 636: "ldaps",
    873: "rsync", 993: "imaps", 995: "pop3s", 1080: "socks", 1433: "mssql",
    1521: "oracle", 1723: "pptp", 1883: "mqtt", 2049: "nfs", 2375: "docker",
    2376: "docker-tls", 3306: "mysql", 3389: "rdp", 4369: "epmd", 5060: "sip",
    5432: "postgres", 5672: "amqp", 5900: "vnc", 5985: "winrm", 5986: "winrm-tls",
    6379: "redis", 6443: "k8s-api", 8080: "http-alt", 8443: "https-alt",
    8888: "http-alt", 9200: "elasticsearch", 9300: "elasticsearch", 11211: "memcached",
    27017: "mongodb",
}

SUSPICIOUS_PORTS = {4444: "Metasploit default", 5555: "ADB / RAT", 6667: "IRC C2",
                    6666: "IRC C2", 7777: "common IRC/C2", 8443: "alt HTTPS",
                    9001: "Tor ORPort", 9050: "Tor SOCKS", 31337: "Back Orifice / elite",
                    12345: "NetBus", 27374: "SubSeven", 1337: "leet / C2"}

DNS_QTYPES = {1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR", 15: "MX",
              16: "TXT", 28: "AAAA", 33: "SRV", 41: "OPT", 43: "DS", 46: "RRSIG",
              48: "DNSKEY", 64: "SVCB", 65: "HTTPS", 255: "ANY"}

HTTP_METHODS = (b"GET ", b"POST ", b"PUT ", b"DELETE ", b"HEAD ", b"OPTIONS ",
                b"PATCH ", b"CONNECT ", b"TRACE ")

# JA3: TLS ClientHello fields hashed as SSLVersion,Ciphers,Extensions,EllipticCurves,ECPointFormats
_TLS_HANDSHAKE = 22
_TLS_CLIENT_HELLO = 1
_TLS_SERVER_HELLO = 2


def _ja3(client_hello: bytes) -> Tuple[str, Dict[str, Any]]:
    """Parse a TLS ClientHello and return (ja3 md5, detail dict)."""
    try:
        pos = 0
        ver = struct.unpack_from(">H", client_hello, pos)[0]
        pos += 2
        pos += 32                      # random
        sid_len = client_hello[pos]
        pos += 1 + sid_len
        cs_len = struct.unpack_from(">H", client_hello, pos)[0]
        pos += 2
        ciphers = []
        end = pos + cs_len
        while pos + 2 <= end:
            ciphers.append(struct.unpack_from(">H", client_hello, pos)[0])
            pos += 2
        comp_len = client_hello[pos]
        pos += 1 + comp_len
        ext_len = struct.unpack_from(">H", client_hello, pos)[0]
        pos += 2
        ext_end = min(len(client_hello), pos + ext_len)
        extensions, curves, formats = [], [], []
        while pos + 4 <= ext_end:
            etype, elen = struct.unpack_from(">HH", client_hello, pos)
            pos += 4
            edata = client_hello[pos:pos + elen]
            pos += elen
            extensions.append(etype)
            if etype == 10 and len(edata) >= 2:   # supported_groups
                glen = struct.unpack_from(">H", edata, 0)[0]
                curves = [struct.unpack_from(">H", edata, 2 + i)[0]
                          for i in range(0, glen - 1, 2)]
            elif etype == 11 and edata:            # ec_point_formats
                formats = list(edata[1:1 + edata[0]])
        raw = ",".join([
            str(ver),
            "-".join(str(c) for c in ciphers),
            "-".join(str(e) for e in extensions),
            "-".join(str(c) for c in curves),
            "-".join(str(f) for f in formats),
        ])
        return hashlib.md5(raw.encode()).hexdigest(), {
            "version": ver, "cipher_count": len(ciphers), "ciphers": ciphers[:40],
            "extension_count": len(extensions), "extensions": extensions[:40],
            "curves": curves[:20], "point_formats": formats, "raw": raw}
    except Exception as exc:
        return "", {"error": str(exc)}


def _ja3s(server_hello: bytes) -> Tuple[str, Dict[str, Any]]:
    try:
        pos = 0
        ver = struct.unpack_from(">H", server_hello, pos)[0]
        pos += 2 + 32
        sid_len = server_hello[pos]
        pos += 1 + sid_len
        cipher = struct.unpack_from(">H", server_hello, pos)[0]
        pos += 2
        pos += 1   # compression
        ext_len = struct.unpack_from(">H", server_hello, pos)[0] if pos + 2 <= len(server_hello) else 0
        pos += 2
        extensions = []
        end = min(len(server_hello), pos + ext_len)
        while pos + 4 <= end:
            etype, elen = struct.unpack_from(">HH", server_hello, pos)
            pos += 4 + elen
            extensions.append(etype)
        raw = f"{ver},{cipher},{'-'.join(str(e) for e in extensions)}"
        return hashlib.md5(raw.encode()).hexdigest(), {
            "version": ver, "cipher": cipher, "extensions": extensions, "raw": raw}
    except Exception as exc:
        return "", {"error": str(exc)}


# --------------------------------------------------------------------------- #
#  PCAP / PCAPNG readers
# --------------------------------------------------------------------------- #
def _read_pcap(data: bytes) -> List[Dict[str, Any]]:
    magic = data[:4]
    if magic not in PCAP_MAGIC:
        return []
    endian, _ = PCAP_MAGIC[magic]
    packets = []
    pos = 24
    linktype = struct.unpack_from(endian + "I", data, 20)[0] & 0x0FFFFFFF
    while pos + 16 <= len(data):
        ts_sec, ts_usec, incl_len, orig_len = struct.unpack_from(endian + "IIII", data, pos)
        pos += 16
        if pos + incl_len > len(data):
            break
        packets.append({"ts": ts_sec + ts_usec / 1_000_000.0,
                        "data": data[pos:pos + incl_len], "orig_len": orig_len,
                        "linktype": linktype})
        pos += incl_len
    return packets


def _read_pcapng(data: bytes) -> List[Dict[str, Any]]:
    packets: List[Dict[str, Any]] = []
    endian = "<"
    ifaces: List[Dict[str, Any]] = []
    pos = 0
    while pos + 12 <= len(data):
        btype, blen = struct.unpack_from(endian + "II", data, pos)
        if btype == 0x0A0D0D0A:  # SHB
            bom = data[pos + 8:pos + 12]
            endian = "<" if bom == b"\x4d\x3c\x2b\x1a" else ">"
            btype, blen = struct.unpack_from(endian + "II", data, pos)
        if blen < 12 or pos + blen > len(data):
            break
        if btype == 1:  # IDB
            linktype = struct.unpack_from(endian + "H", data, pos + 8)[0]
            ifaces.append({"linktype": linktype, "tsresol": 6})
        elif btype == 6:  # EPB
            iface_id, ts_high, ts_low, cap_len, orig_len = struct.unpack_from(
                endian + "IIIII", data, pos + 8)
            ts = ((ts_high << 32) | ts_low) / 1_000_000.0
            body = data[pos + 28:pos + 28 + cap_len]
            lt = ifaces[iface_id]["linktype"] if iface_id < len(ifaces) else 1
            packets.append({"ts": ts, "data": body, "orig_len": orig_len, "linktype": lt})
        elif btype == 3:  # simple packet block
            orig_len = struct.unpack_from(endian + "I", data, pos + 8)[0]
            body = data[pos + 12:pos + blen - 4]
            lt = ifaces[0]["linktype"] if ifaces else 1
            packets.append({"ts": 0.0, "data": body, "orig_len": orig_len, "linktype": lt})
        pos += blen
    return packets


def read_pcap(data: bytes) -> Dict[str, Any]:
    if data[:4] == b"\x0a\x0d\x0d\x0a":
        packets = _read_pcapng(data)
        fmt = "pcapng"
    else:
        packets = _read_pcap(data)
        fmt = "pcap"
    if not packets:
        raise ValueError("not a PCAP/PCAPNG file or no packets decoded")
    return {"format": fmt, "packets": packets,
            "first_ts": packets[0]["ts"], "last_ts": packets[-1]["ts"]}


# --------------------------------------------------------------------------- #
#  Packet decoding
# --------------------------------------------------------------------------- #
def _decode_packet(pkt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = pkt["data"]
    linktype = pkt.get("linktype", 1)
    out: Dict[str, Any] = {"ts": pkt.get("ts", 0.0), "raw_len": len(data)}
    if linktype == 1:  # Ethernet
        if len(data) < 14:
            return None
        dst, src, etype = data[:6], data[6:12], struct.unpack_from(">H", data, 12)[0]
        out["eth_src"] = _mac(src)
        out["eth_dst"] = _mac(dst)
        offset = 14
        while etype == 0x8100 and len(data) >= offset + 4:  # VLAN
            etype = struct.unpack_from(">H", data, offset + 2)[0]
            offset += 4
        out["eth_type"] = ETH_TYPES.get(etype, hex(etype))
    elif linktype in (101, 12, 14):  # raw IP / raw
        out["eth_type"] = "IPv4" if data[0] >> 4 == 4 else "IPv6"
        offset = 0
    elif linktype == 0:  # BSD loopback
        offset = 4
        out["eth_type"] = "IPv4" if data[4] >> 4 == 4 else "IPv6"
    else:
        return None
    data = data[offset:]
    if out["eth_type"] == "IPv4":
        ip = _decode_ipv4(data)
    elif out["eth_type"] == "IPv6":
        ip = _decode_ipv6(data)
    else:
        return None
    if not ip:
        return None
    out.update(ip)
    l4 = out.pop("_payload", b"")
    if out.get("proto") == "TCP":
        out.update(_decode_tcp(l4))
    elif out.get("proto") == "UDP":
        out.update(_decode_udp(l4))
    payload = out.pop("_l4payload", b"")
    if payload:
        _decode_app(out, payload)
    out.pop("_raw_l4", None)
    return out


def _mac(b: bytes) -> str:
    return ":".join(f"{x:02x}" for x in b)


def _decode_ipv4(data: bytes) -> Optional[Dict[str, Any]]:
    if len(data) < 20:
        return None
    ihl = (data[0] & 0x0F) * 4
    total_len = struct.unpack_from(">H", data, 2)[0]
    ttl, proto = data[8], data[9]
    src = socket.inet_ntoa(data[12:16])
    dst = socket.inet_ntoa(data[16:20])
    return {"ip_version": 4, "src_ip": src, "dst_ip": dst, "ttl": ttl,
            "proto": {6: "TCP", 17: "UDP", 1: "ICMP", 47: "GRE", 50: "ESP",
                      51: "AH", 132: "SCTP"}.get(proto, f"IP-{proto}"),
            "ip_len": total_len, "frag": bool(struct.unpack_from(">H", data, 6)[0] & 0x1FFF),
            "_payload": data[ihl:total_len] if total_len >= ihl else data[ihl:]}


def _decode_ipv6(data: bytes) -> Optional[Dict[str, Any]]:
    if len(data) < 40:
        return None
    next_header = data[6]
    src = str(ipaddress.IPv6Address(data[8:24]))
    dst = str(ipaddress.IPv6Address(data[24:40]))
    return {"ip_version": 6, "src_ip": src, "dst_ip": dst, "ttl": data[7],
            "proto": {6: "TCP", 17: "UDP", 58: "ICMPv6"}.get(next_header, f"IP-{next_header}"),
            "ip_len": struct.unpack_from(">H", data, 4)[0] + 40,
            "_payload": data[40:]}


def _decode_tcp(data: bytes) -> Dict[str, Any]:
    if len(data) < 20:
        return {}
    sport, dport, seq, ack = struct.unpack_from(">HHII", data, 0)
    off = (data[12] >> 4) * 4
    flags = data[13]
    return {"src_port": sport, "dst_port": dport, "seq": seq, "ack": ack,
            "tcp_flags": "".join(name for bit, name in TCP_FLAGS.items() if flags & bit),
            "tcp_len": len(data) - off,
            "_l4payload": data[off:]}


def _decode_udp(data: bytes) -> Dict[str, Any]:
    if len(data) < 8:
        return {}
    sport, dport, length = struct.unpack_from(">HHH", data, 0)
    return {"src_port": sport, "dst_port": dport, "udp_len": length,
            "_l4payload": data[8:length] if 8 <= length <= len(data) else data[8:]}


def _decode_app(out: Dict[str, Any], payload: bytes) -> None:
    sport, dport = out.get("src_port", 0), out.get("dst_port", 0)
    if 53 in (sport, dport) or out.get("proto") == "UDP" and 53 in (sport, dport):
        dns = _parse_dns(payload)
        if dns:
            out["dns"] = dns
            out["app"] = "DNS"
            return
    if 80 in (sport, dport) or 8080 in (sport, dport) or 8000 in (sport, dport) or \
            443 in (sport, dport) and payload[:1] in b"GPHO":
        http = _parse_http(payload)
        if http:
            out["http"] = http
            out["app"] = "HTTP"
            return
    if payload[:1] == b"\x16" and len(payload) > 5 and payload[1] == 3:
        rec = payload[5:]
        if rec[:1] == b"\x01":
            ja3, detail = _ja3(rec[4:])
            if ja3:
                out["tls"] = {"type": "client_hello", "ja3": ja3, **detail}
                out["app"] = "TLS"
        elif rec[:1] == b"\x02":
            ja3s, detail = _ja3s(rec[4:])
            if ja3s:
                out["tls"] = {"type": "server_hello", "ja3s": ja3s, **detail}
                out["app"] = "TLS"
        return
    if payload[:4] == b"\x00\x00\x00\x00" or out.get("proto") == "TCP" and payload[:1] in b"\x00\x01\x02":
        out["app"] = "possible-custom-binary"
    elif b"SSH-" in payload[:8]:
        out["app"] = "SSH"
        m = re.search(rb"SSH-([0-9.]+)-(\S+)", payload[:128])
        if m:
            out["ssh_banner"] = m.group(0).decode("latin-1")
    elif payload[:1] == b"*" or payload[:4] == b"\x00\x00\x00\x00":
        out["app"] = "possible-custom"
    elif payload[:4] == b"\x03\x00\x00" and out.get("proto") == "TCP":
        out["app"] = "possible-RDP"


def _parse_dns(data: bytes) -> Optional[Dict[str, Any]]:
    if len(data) < 12:
        return None
    tid, flags, qd, an, ns, ar = struct.unpack_from(">HHHHHH", data, 0)
    qr = "response" if flags & 0x8000 else "query"
    opcode = (flags >> 11) & 0xF
    rcode = flags & 0xF
    pos = 12
    questions = []
    for _ in range(min(qd, 50)):
        name, pos = _dns_name(data, pos)
        if pos + 4 > len(data):
            break
        qtype, qclass = struct.unpack_from(">HH", data, pos)
        pos += 4
        questions.append({"name": name, "type": DNS_QTYPES.get(qtype, str(qtype)),
                          "type_id": qtype, "class": qclass})
    answers = []
    for _ in range(min(an, 100)):
        name, pos = _dns_name(data, pos)
        if pos + 10 > len(data):
            break
        rtype, rclass, ttl, rdlen = struct.unpack_from(">HHIH", data, pos)
        pos += 10
        rdata = data[pos:pos + rdlen]
        pos += rdlen
        value = ""
        if rtype == 1 and rdlen == 4:
            value = socket.inet_ntoa(rdata)
        elif rtype == 28 and rdlen == 16:
            value = str(ipaddress.IPv6Address(rdata))
        elif rtype in (5, 2, 12):
            value, _ = _dns_name(data, pos - rdlen)
        elif rtype == 16:
            value = rdata.decode("latin-1", "replace")
        answers.append({"name": name, "type": DNS_QTYPES.get(rtype, str(rtype)),
                        "value": value, "ttl": ttl})
    return {"id": tid, "qr": qr, "opcode": opcode, "rcode": rcode,
            "questions": questions, "answers": answers}


def _dns_name(data: bytes, pos: int, depth: int = 0) -> Tuple[str, int]:
    labels = []
    start = pos
    if depth > 8:
        return "", pos
    while pos < len(data):
        ln = data[pos]
        if ln == 0:
            pos += 1
            break
        if ln & 0xC0 == 0xC0:
            ptr = struct.unpack_from(">H", data, pos)[0] & 0x3FFF
            sub, _ = _dns_name(data, ptr, depth + 1)
            labels.append(sub)
            pos += 2
            return ".".join(x for x in labels if x), pos
        pos += 1
        labels.append(data[pos:pos + ln].decode("latin-1", "replace"))
        pos += ln
    return ".".join(labels), max(pos, start + 1)


def _parse_http(data: bytes) -> Optional[Dict[str, Any]]:
    head = data[:8192]
    if head.startswith(b"HTTP/"):
        first = head.split(b"\r\n", 1)[0].decode("latin-1", "replace")
        parts = first.split(" ", 2)
        headers = _http_headers(head)
        return {"direction": "response", "status": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
                "version": parts[0], "headers": headers, "body_len": len(data)}
    if any(head.startswith(m) for m in HTTP_METHODS):
        first = head.split(b"\r\n", 1)[0].decode("latin-1", "replace")
        parts = first.split(" ")
        headers = _http_headers(head)
        host = headers.get("host", "")
        uri = parts[1] if len(parts) > 1 else ""
        return {"direction": "request", "method": parts[0], "uri": uri, "version": parts[2] if len(parts) > 2 else "",
                "host": host, "headers": headers, "user_agent": headers.get("user-agent", ""),
                "url": f"http://{host}{uri}" if host else uri,
                "body_len": len(data)}
    return None


def _http_headers(head: bytes) -> Dict[str, str]:
    out = {}
    try:
        block = head.split(b"\r\n\r\n", 1)[0]
        for line in block.split(b"\r\n")[1:]:
            if b":" in line:
                k, v = line.split(b":", 1)
                out[k.decode("latin-1", "replace").strip().lower()] = \
                    v.decode("latin-1", "replace").strip()
    except Exception:
        pass
    return out


# --------------------------------------------------------------------------- #
#  Public analysis entry points
# --------------------------------------------------------------------------- #
def analyze_pcap(kwargs: Dict[str, Any], data: bytes) -> Dict[str, Any]:
    parsed = read_pcap(data)
    packets = parsed["packets"]
    max_pkts = int(kwargs.get("max_packets") or 200000)
    packets = packets[:max_pkts]
    flows: Dict[Tuple, Dict[str, Any]] = {}
    dns_queries: List[Dict[str, Any]] = []
    http_requests: List[Dict[str, Any]] = []
    tls_clients: List[Dict[str, Any]] = []
    tls_servers: List[Dict[str, Any]] = []
    protocols = Counter()
    bytes_total = 0
    errors = 0
    for pkt in packets:
        try:
            p = _decode_packet(pkt)
        except Exception:
            errors += 1
            continue
        if not p:
            continue
        bytes_total += p.get("raw_len", 0)
        protocols[p.get("app") or p.get("proto") or "unknown"] += 1
        if p.get("dns"):
            d = p["dns"]
            for q in d["questions"]:
                dns_queries.append({"ts": p["ts"], "src_ip": p.get("src_ip"),
                                    "dst_ip": p.get("dst_ip"), "name": q["name"],
                                    "type": q["type"], "qr": d["qr"],
                                    "answers": d["answers"]})
        if p.get("http"):
            h = p["http"]
            if h.get("direction") == "request":
                http_requests.append({"ts": p["ts"], "src_ip": p.get("src_ip"),
                                      "dst_ip": p.get("dst_ip"),
                                      "method": h.get("method"), "host": h.get("host"),
                                      "uri": h.get("uri"), "user_agent": h.get("user_agent"),
                                      "url": h.get("url")})
        if p.get("tls"):
            t = p["tls"]
            if t.get("type") == "client_hello":
                tls_clients.append({"ts": p["ts"], "src_ip": p.get("src_ip"),
                                    "dst_ip": p.get("dst_ip"), "ja3": t["ja3"],
                                    "sni": _tls_sni(p.get("_l4payload", b"")),
                                    "detail": t})
            else:
                tls_servers.append({"ts": p["ts"], "src_ip": p.get("src_ip"),
                                    "dst_ip": p.get("dst_ip"), "ja3s": t["ja3s"]})
        if p.get("src_ip") and p.get("dst_ip") and p.get("proto") in ("TCP", "UDP"):
            key = (p["src_ip"], p.get("src_port", 0), p["dst_ip"], p.get("dst_port", 0), p["proto"])
            flow = flows.get(key)
            if not flow:
                flow = {"src_ip": p["src_ip"], "src_port": p.get("src_port", 0),
                        "dst_ip": p["dst_ip"], "dst_port": p.get("dst_port", 0),
                        "proto": p["proto"], "packets": 0, "bytes": 0,
                        "first_ts": p["ts"], "last_ts": p["ts"],
                        "app": p.get("app", ""), "service": WELL_KNOWN_PORTS.get(p.get("dst_port", 0), ""),
                        "flags": Counter()}
                flows[key] = flow
            flow["packets"] += 1
            flow["bytes"] += p.get("raw_len", 0)
            flow["last_ts"] = max(flow["last_ts"], p["ts"])
            if p.get("app"):
                flow["app"] = p["app"]
            if p.get("tcp_flags"):
                flow["flags"][p["tcp_flags"]] += 1
    flow_list = []
    for f in flows.values():
        f["duration"] = round(f["last_ts"] - f["first_ts"], 3)
        f["flags"] = dict(f["flags"])
        flow_list.append(f)
    flow_list.sort(key=lambda x: x["bytes"], reverse=True)
    iocs, infra = _network_iocs(flow_list, dns_queries, http_requests, tls_clients)
    beacon = _beacon_from_flows(flow_list)
    dns_analysis = _dns_analysis(dns_queries)
    port_scan = _port_scan(flow_list)
    return {
        "format": parsed["format"],
        "packet_count": len(packets),
        "bytes": bytes_total,
        "bytes_human": human_size(bytes_total),
        "timespan_seconds": round(parsed["last_ts"] - parsed["first_ts"], 3),
        "decode_errors": errors,
        "protocols": dict(protocols.most_common(30)),
        "flow_count": len(flow_list),
        "flows": flow_list[:400],
        "top_talkers": _top_talkers(flow_list),
        "dns": dns_analysis,
        "dns_queries": dns_queries[:200],
        "http": {"requests": http_requests[:200], "count": len(http_requests),
                 "suspicious": _suspicious_http(http_requests)},
        "tls": {"client_hellos": tls_clients[:100], "server_hellos": tls_servers[:100],
                "ja3_count": len({t["ja3"] for t in tls_clients if t.get("ja3")}),
                "suspicious_ja3": _suspicious_ja3(tls_clients)},
        "beaconing": beacon,
        "port_scan": port_scan,
        "iocs": iocs,
        "infrastructure": infra,
        "findings": _network_findings(flow_list, dns_analysis, beacon, port_scan,
                                      http_requests, tls_clients),
    }


def _tls_sni(payload: bytes) -> str:
    try:
        rec = payload[5:]
        if rec[:1] != b"\x01":
            return ""
        body = rec[4:]
        # skip to extensions
        pos = 2 + 32
        pos += 1 + body[pos]
        cs = struct.unpack_from(">H", body, pos)[0]
        pos += 2 + cs
        pos += 1 + body[pos]
        ext_len = struct.unpack_from(">H", body, pos)[0]
        pos += 2
        end = pos + ext_len
        while pos + 4 <= end:
            etype, elen = struct.unpack_from(">HH", body, pos)
            pos += 4
            if etype == 0:
                s = body[pos:pos + elen]
                # server_name_list: len(2) type(1) len(2) name
                if len(s) > 5:
                    nlen = struct.unpack_from(">H", s, 3)[0]
                    return s[5:5 + nlen].decode("latin-1", "replace")
            pos += elen
    except Exception:
        return ""
    return ""


def _top_talkers(flows: List[Dict[str, Any]], limit: int = 15) -> Dict[str, Any]:
    src = Counter()
    dst = Counter()
    pair = Counter()
    for f in flows:
        src[f["src_ip"]] += f["bytes"]
        dst[f["dst_ip"]] += f["bytes"]
        pair[(f["src_ip"], f["dst_ip"])] += f["bytes"]
    return {"by_source": [{"ip": k, "bytes": v, "human": human_size(v)} for k, v in src.most_common(limit)],
            "by_destination": [{"ip": k, "bytes": v, "human": human_size(v)} for k, v in dst.most_common(limit)],
            "top_pairs": [{"src": a, "dst": b, "bytes": v} for (a, b), v in pair.most_common(limit)]}


def _network_iocs(flows, dns_queries, http_requests, tls_clients) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    ips = sorted({f["dst_ip"] for f in flows if not _is_private(f["dst_ip"])})
    src_ips = sorted({f["src_ip"] for f in flows})
    domains = sorted({q["name"].rstrip(".").lower() for q in dns_queries
                      if q.get("name") and q["qr"] == "query"})
    urls = sorted({h["url"] for h in http_requests if h.get("url")})
    hosts = sorted({h["host"] for h in http_requests if h.get("host")})
    ja3 = sorted({t["ja3"] for t in tls_clients if t.get("ja3")})
    sni = sorted({t.get("sni") for t in tls_clients if t.get("sni")})
    iocs = {"ipv4": ips[:300], "source_ips": src_ips[:300], "domains": domains[:300],
            "urls": urls[:200], "http_hosts": hosts[:200], "ja3": ja3[:100],
            "sni": sni[:200]}
    infra = {"unique_destinations": len(ips), "unique_domains": len(domains),
             "asn_hint": "", "clustering": _cluster_hosts(domains)}
    return iocs, infra


def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except Exception:
        return False


def _cluster_hosts(domains: Sequence[str]) -> List[Dict[str, Any]]:
    clusters: Dict[str, List[str]] = defaultdict(list)
    for d in domains:
        parts = d.split(".")
        key = ".".join(parts[-2:]) if len(parts) >= 2 else d
        clusters[key].append(d)
    out = [{"cluster": k, "members": sorted(set(v))[:20], "count": len(set(v))}
           for k, v in clusters.items()]
    out.sort(key=lambda x: x["count"], reverse=True)
    return out[:30]


def _beacon_from_flows(flows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_dest: Dict[Tuple, List[float]] = defaultdict(list)
    for f in flows:
        by_dest[(f["dst_ip"], f["dst_port"])].append(f["first_ts"])
    results = []
    for (ip, port), times in by_dest.items():
        if len(times) < 4:
            continue
        times = sorted(times)
        deltas = [b - a for a, b in zip(times, times[1:]) if b > a]
        if len(deltas) < 3:
            continue
        mean = sum(deltas) / len(deltas)
        if mean <= 0:
            continue
        var = sum((d - mean) ** 2 for d in deltas) / len(deltas)
        jitter = math.sqrt(var) / mean * 100
        if jitter < 25 and mean >= 3:
            results.append({"dst_ip": ip, "dst_port": port, "connections": len(times),
                            "mean_interval_s": round(mean, 2),
                            "jitter_percent": round(jitter, 1),
                            "confidence": min(98, int(100 - jitter)),
                            "verdict": "likely C2 beacon" if jitter < 15 else "possible beacon"})
    results.sort(key=lambda x: x["confidence"], reverse=True)
    return {"candidates": results[:20], "count": len(results),
            "verdict": "beaconing detected" if results else "no regular callback pattern"}


def _dns_analysis(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    asked = [q for q in queries if q.get("qr") == "query"]
    names = [q["name"].rstrip(".").lower() for q in asked if q.get("name")]
    tunnels = []
    for q in asked:
        name = (q.get("name") or "").rstrip(".")
        if not name:
            continue
        labels = name.split(".")
        longest = max((len(l) for l in labels), default=0)
        score = 0
        evidence = []
        if longest >= 40:
            score += 40
            evidence.append(f"long label ({longest} chars)")
        if _shannon(name) > 3.8 and longest >= 20:
            score += 25
            evidence.append("high-entropy label")
        if len(labels) >= 6:
            score += 15
            evidence.append(f"deep nesting ({len(labels)} labels)")
        if q.get("type") in ("TXT", "NULL", "CNAME") and longest >= 30:
            score += 20
            evidence.append(f"abused record type {q.get('type')}")
        if score >= 45:
            tunnels.append({"name": name, "score": score, "evidence": evidence,
                            "type": q.get("type"), "src_ip": q.get("src_ip")})
    counts = Counter(names)
    nx = Counter(q.get("name") for q in queries if q.get("qr") == "response" and q.get("rcode") in (3,))
    return {"queries": len(asked), "unique_names": len(set(names)),
            "top_names": [{"name": k, "count": v} for k, v in counts.most_common(20)],
            "tlds": dict(Counter(n.split(".")[-1] for n in names if "." in n).most_common(20)),
            "possible_tunnels": tunnels[:30],
            "tunnel_count": len(tunnels),
            "verdict": "possible DNS tunneling" if tunnels else "DNS looks normal"}


def _shannon(s: str) -> float:
    if not s:
        return 0.0
    c = Counter(s)
    n = len(s)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def _suspicious_http(requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for r in requests:
        url = (r.get("url") or "")
        ua = (r.get("user_agent") or "").lower()
        reasons = []
        if any(ext in url.lower() for ext in (".exe", ".dll", ".ps1", ".js", ".vbs", ".hta", ".scr", ".iso", ".img")):
            reasons.append("executable/payload download")
        if any(c in url for c in ("/gate.php", "/panel/", "/api/check", "/ping", "/submit.php")):
            reasons.append("typical C2 endpoint")
        if re.search(r"(?:[a-z0-9+/=]{60,})", url):
            reasons.append("long encoded parameter")
        if any(x in ua for x in ("powershell", "python-requests", "curl/", "wget", "go-http-client", "mozilla/4.0")):
            reasons.append(f"suspicious user agent {ua[:40]!r}")
        if r.get("method") in ("POST", "PUT") and (r.get("host") or ""):
            reasons.append("data upload")
        if reasons:
            out.append({**r, "reasons": reasons})
    return out[:60]


def _suspicious_ja3(clients: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    known_bad = {
        "51c64c77e60f3980eea90869b68c58a8": "Metasploit Meterpreter",
        "a0e9f5d64349fb13191bc781f81f42e1": "Cobalt Strike default",
        "72a589da586844d7f0818ce684948eea": "AsyncRAT",
        "b386946a5a44d1ddcc843bc75336dfce": "TrickBot",
        "e7d705a3286e19ea42f587b344ee6865": "Go HTTP client",
        "3b5074b1b5d032e5620f69f9f700ff0e": "Tor",
        "6734f37431670b3ab4292b8f60f29984": "Emotet",
    }
    hits = []
    for c in clients:
        if c.get("ja3") in known_bad:
            hits.append({"ja3": c["ja3"], "family": known_bad[c["ja3"]],
                         "sni": c.get("sni", ""), "dst_ip": c.get("dst_ip")})
    return hits


def _port_scan(flows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_src: Dict[str, Dict[int, str]] = defaultdict(dict)
    for f in flows:
        if f["proto"] == "TCP":
            by_src[f["src_ip"]][f["dst_port"]] = f["dst_ip"]
    scans = []
    for src, ports in by_src.items():
        if len(ports) >= 15:
            scans.append({"src_ip": src, "distinct_ports": len(ports),
                          "ports": sorted(ports)[:40],
                          "verdict": "port scan" if len(ports) < 100 else "aggressive scan"})
    scans.sort(key=lambda x: x["distinct_ports"], reverse=True)
    return {"scanners": scans[:10], "count": len(scans),
            "verdict": "port scanning detected" if scans else "no scan pattern"}


def _network_findings(flows, dns_analysis, beacon, port_scan, http_requests, tls_clients) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    def add(sev: str, msg: str, mitre: Sequence[str] = (), evidence: Any = None) -> None:
        findings.append({"severity": sev, "finding": msg, "mitre": list(mitre),
                         "evidence": evidence})
    if beacon["candidates"]:
        add("high", f"C2 beaconing to {len(beacon['candidates'])} endpoint(s)",
            ["T1071", "T1573"], beacon["candidates"][:5])
    if dns_analysis["possible_tunnels"]:
        add("high", f"Possible DNS tunneling ({dns_analysis['tunnel_count']} queries)",
            ["T1071.004"], dns_analysis["possible_tunnels"][:5])
    if port_scan["scanners"]:
        add("medium", f"Port scanning from {len(port_scan['scanners'])} source(s)",
            ["T1046"], port_scan["scanners"][:5])
    susp = _suspicious_http(http_requests)
    if susp:
        add("high", f"{len(susp)} suspicious HTTP request(s)", ["T1071.001", "T1105"], susp[:5])
    bad_ja3 = _suspicious_ja3(tls_clients)
    if bad_ja3:
        add("high", f"Known-malicious JA3 fingerprint(s): {[b['family'] for b in bad_ja3]}",
            ["T1573"], bad_ja3)
    for s in SUSPICIOUS_PORTS:
        hits = [f for f in flows if f.get("dst_port") == s]
        if hits:
            add("medium", f"Traffic to suspicious port {s} ({SUSPICIOUS_PORTS[s]})",
                ["T1571"], hits[:3])
    for f in flows:
        if f["dst_port"] == 53 and f["proto"] == "TCP":
            add("low", "DNS over TCP observed (possible large/tunneled responses)",
                ["T1071.004"], f)
            break
    return sorted(findings, key=lambda x: severity_rank(x["severity"]))


# --------------------------------------------------------------------------- #
#  Infrastructure clustering across samples
# --------------------------------------------------------------------------- #
def cluster_infrastructure(indicators: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Group indicators by shared infrastructure signals (IP/domain/ASN hint)."""
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: Counter = Counter()
    for item in indicators:
        label = str(item.get("value") or item.get("indicator") or "")
        kind = item.get("type") or item.get("kind") or "unknown"
        if not label:
            continue
        node = nodes.setdefault(label, {"id": label, "type": kind,
                                        "samples": set(), "tags": set()})
        for s in item.get("samples", []) or []:
            node["samples"].add(str(s))
        for t in item.get("tags", []) or []:
            node["tags"].add(str(t))
        for other in item.get("related", []) or []:
            edges[tuple(sorted((label, str(other))))] += 1
    # cluster by shared sample
    sample_map: Dict[str, List[str]] = defaultdict(list)
    for n in nodes.values():
        for s in n["samples"]:
            sample_map[s].append(n["id"])
    clusters = []
    seen = set()
    for sample, members in sample_map.items():
        key = tuple(sorted(members))
        if key in seen or len(members) < 2:
            continue
        seen.add(key)
        clusters.append({"samples": [sample], "indicators": members,
                         "size": len(members)})
    out_nodes = [{**{k: v for k, v in n.items() if k not in ("samples", "tags")},
                  "samples": sorted(n["samples"]), "tags": sorted(n["tags"])}
                 for n in nodes.values()]
    return {"nodes": out_nodes, "edges": [{"a": a, "b": b, "weight": w} for (a, b), w in edges.most_common(200)],
            "clusters": clusters[:50], "node_count": len(out_nodes)}


# --------------------------------------------------------------------------- #
#  Decoders / encoders
# --------------------------------------------------------------------------- #
def decode_tcp_stream(data: bytes) -> Dict[str, Any]:
    """Reassemble a raw TCP payload into HTTP/DNS/TLS/SSH or plain text."""
    out: Dict[str, Any] = {"size": len(data), "entropy": round(entropy(data), 3)}
    http = _parse_http(data)
    if http:
        out.update({"protocol": "HTTP", "http": http})
        return out
    dns = _parse_dns(data)
    if dns:
        out.update({"protocol": "DNS", "dns": dns})
        return out
    if data[:1] == b"\x16":
        out["protocol"] = "TLS"
        rec = data[5:]
        if rec[:1] == b"\x01":
            ja3, detail = _ja3(rec[4:])
            out["ja3"] = ja3
            out["detail"] = detail
        return out
    if b"SSH-" in data[:16]:
        out["protocol"] = "SSH"
        out["banner"] = data[:128].decode("latin-1", "replace")
        return out
    printable = sum(1 for b in data[:4096] if 32 <= b <= 126 or b in (9, 10, 13))
    out["protocol"] = "text" if printable / max(1, len(data[:4096])) > 0.85 else "binary"
    out["preview"] = data[:600].decode("latin-1", "replace")
    return out


def decode_udp_payload(data: bytes) -> Dict[str, Any]:
    dns = _parse_dns(data)
    if dns:
        return {"protocol": "DNS", "dns": dns, "size": len(data)}
    txt = data[:400].decode("latin-1", "replace")
    return {"protocol": "binary" if entropy(data) > 6.5 else "text",
            "size": len(data), "preview": txt, "entropy": round(entropy(data), 3)}


def hex_dump(data: bytes, width: int = 16, limit: int = 512) -> str:
    lines = []
    for off in range(0, min(len(data), limit), width):
        chunk = data[off:off + width]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
        lines.append(f"{off:08x}  {hexpart:<{width * 3}}  |{asc}|")
    if len(data) > limit:
        lines.append(f"... ({len(data) - limit} more bytes)")
    return "\n".join(lines)


def build_packet(**kw: Any) -> Dict[str, Any]:
    """Best-effort Scapy-backed packet builder; degrades to a JSON spec."""
    try:
        from scapy.all import IP, IPv6, TCP, UDP, ICMP, DNS, DNSQR, Raw, wrpcap  # type: ignore
        import tempfile
        import os
        src = kw.get("src_ip", "192.168.1.10")
        dst = kw.get("dst_ip", "192.168.1.1")
        proto = (kw.get("proto") or "tcp").lower()
        sport = int(kw.get("src_port") or 44444)
        dport = int(kw.get("dst_port") or 80)
        payload = str(kw.get("payload") or "").encode()
        ip_layer = IPv6(src=src, dst=dst) if ":" in str(src) else IP(src=src, dst=dst)
        if proto == "tcp":
            pkt = ip_layer / TCP(sport=sport, dport=dport, flags=str(kw.get("flags") or "S")) / Raw(payload)
        elif proto == "udp":
            pkt = ip_layer / UDP(sport=sport, dport=dport) / Raw(payload)
        elif proto == "icmp":
            pkt = ip_layer / ICMP() / Raw(payload)
        elif proto == "dns":
            qname = kw.get("query") or "example.com"
            pkt = ip_layer / UDP(sport=sport, dport=dport) / DNS(rd=1, qd=DNSQR(qname=qname))
        else:
            return {"built": False, "error": f"unsupported proto {proto}"}
        fd, path = tempfile.mkstemp(suffix=".pcap")
        os.close(fd)
        wrpcap(path, [pkt])
        blob = open(path, "rb").read()
        os.unlink(path)
        return {"built": True, "engine": "scapy", "size": len(blob),
                "pcap_base64": __import__("base64").b64encode(blob).decode(),
                "summary": pkt.summary()}
    except ImportError:
        return {"built": False, "engine": "none",
                "note": "install scapy for packet crafting",
                "spec": {k: v for k, v in kw.items()}}
    except Exception as exc:
        return {"built": False, "error": str(exc), "spec": kw}
