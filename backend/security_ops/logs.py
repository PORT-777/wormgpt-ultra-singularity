# backend/security_ops/logs.py
# Security log analysis: Windows/Sysmon, Linux auth, web access logs,
# Suricata/Zeek, cloud audit logs, email headers, beacon timing, lateral
# movement graphs and unified attack timelines.

from __future__ import annotations

import base64
import email
import hashlib
import io
import json
import math
import re
import statistics
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from email import policy
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .knowledge import (LOLBINS, SYSMON_EVENTS, WINDOWS_EVENTS)
from .util import (extract_iocs, fmt_time, normalize_severity, now_iso,
                   parse_time, severity_rank, tokens)

RISKY_PORTS = {22: "SSH", 23: "Telnet", 445: "SMB", 3389: "RDP", 5985: "WinRM",
               5986: "WinRM TLS", 1433: "MSSQL", 3306: "MySQL", 5432: "PostgreSQL",
               6379: "Redis", 9200: "Elasticsearch", 27017: "MongoDB", 21: "FTP",
               25: "SMTP", 110: "POP3", 143: "IMAP", 389: "LDAP", 636: "LDAPS"}

WEB_ATTACK_PATTERNS = {
    "SQL injection": [r"(?i)\bunion\s+(?:all\s+)?select\b", r"(?i)\bor\s+1\s*=\s*1\b",
                      r"(?i)['\"]\s*;\s*(?:drop|delete|insert|update)\b", r"(?i)sleep\s*\(\s*\d+\s*\)",
                      r"(?i)information_schema", r"(?i)benchmark\s*\("],
    "Cross-site scripting": [r"(?i)<script[^>]*>", r"(?i)javascript\s*:", r"(?i)onerror\s*=",
                             r"(?i)onload\s*=", r"(?i)%3cscript"],
    "Path traversal": [r"(?i)\.\./\.\./", r"(?i)%2e%2e%2f", r"(?i)/etc/passwd",
                       r"(?i)win\.ini", r"(?i)boot\.ini"],
    "Command injection": [r"(?i)[;|&`]\s*(?:id|whoami|uname|cat|curl|wget|nc)\b",
                          r"(?i)\$\([^)]+\)", r"(?i)%0a"],
    "Log4Shell": [r"(?i)\$\{jndi:(?:ldap|rmi|dns|http)"],
    "Web shell access": [r"(?i)/(?:shell|cmd|backdoor|upload)\.(?:php|aspx?|jsp|jspx)\b"],
    "Scanner": [r"(?i)(?:nikto|sqlmap|nmap|masscan|acunetix|nessus|wpscan|dirbuster|gobuster|ffuf)"],
    "SSRF": [r"(?i)(?:169\.254\.169\.254|localhost|127\.0\.0\.1|\[::1\]).*(?:url|dest|target)="],
}

SUSPICIOUS_UA = ("sqlmap", "nikto", "nmap", "masscan", "acunetix", "nessus",
                 "wpscan", "dirbuster", "gobuster", "ffuf", "curl/", "python-requests",
                 "go-http-client", "zgrab", "nuclei")

CLOUD_SENSITIVE_EVENTS = {
    "CreateAccessKey": ("critical", "IAM access key created", "T1098"),
    "CreateUser": ("high", "IAM user created", "T1136"),
    "AttachUserPolicy": ("high", "Policy attached to user", "T1098"),
    "AttachRolePolicy": ("high", "Policy attached to role", "T1098"),
    "PutUserPolicy": ("high", "Inline user policy added", "T1098"),
    "PutRolePolicy": ("high", "Inline role policy added", "T1098"),
    "CreateRole": ("high", "IAM role created", "T1136"),
    "UpdateAssumeRolePolicy": ("critical", "Role trust policy modified", "T1098"),
    "DeleteTrail": ("critical", "CloudTrail deleted", "T1562.008"),
    "StopLogging": ("critical", "CloudTrail logging stopped", "T1562.008"),
    "PutBucketAcl": ("high", "S3 bucket ACL changed", "T1530"),
    "PutBucketPolicy": ("high", "S3 bucket policy changed", "T1530"),
    "PutPublicAccessBlock": ("medium", "S3 public access block changed", "T1530"),
    "DeletePublicAccessBlock": ("critical", "S3 public access block removed", "T1530"),
    "CreateSnapshot": ("medium", "Snapshot created", "T1537"),
    "ModifySnapshotAttribute": ("critical", "Snapshot shared externally", "T1537"),
    "RunInstances": ("medium", "EC2 instance launched", "T1578"),
    "CreateFunction": ("medium", "Lambda function created", "T1648"),
    "UpdateFunctionCode": ("high", "Lambda code updated", "T1648"),
    "GetSecretValue": ("high", "Secret read", "T1552.005"),
    "GetSessionToken": ("medium", "Temporary credentials requested", "T1078.004"),
    "AssumeRole": ("medium", "Role assumed", "T1078.004"),
    "ConsoleLogin": ("info", "Console login", "T1078.004"),
    "DeleteBucket": ("high", "S3 bucket deleted", "T1485"),
    "DeleteDBInstance": ("high", "Database deleted", "T1485"),
    "TerminateInstances": ("high", "EC2 instance terminated", "T1485"),
}

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


# --------------------------------------------------------------------------- #
#  Generic analyzer
# --------------------------------------------------------------------------- #
def analyze_logs(text: str, kind: str = "auto", max_lines: int = 200000) -> Dict[str, Any]:
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return {"error": "empty log"}
    lines = lines[:max_lines]
    if kind in ("auto", "", None):
        kind = detect_log_type(lines)
    parsed, parse_errors = [], 0
    for line in lines:
        try:
            ev = _parse_line(line, kind)
        except Exception:
            ev = None
        if ev:
            parsed.append(ev)
        else:
            parse_errors += 1
    findings: List[Dict[str, Any]] = []
    if kind == "windows":
        findings += _windows_findings(parsed)
    elif kind == "sysmon":
        findings += _sysmon_findings(parsed)
    elif kind == "auth":
        findings += _auth_findings(parsed)
    elif kind == "web":
        findings += _web_findings(parsed, lines)
    elif kind == "suricata":
        findings += _suricata_findings(parsed)
    elif kind == "zeek":
        findings += _zeek_findings(parsed)
    elif kind == "cloud":
        findings += _cloud_findings(parsed)
    else:
        findings += _generic_findings(parsed, text)
    lols = scan_lolbins(text)
    if lols["matches"]:
        findings.append({"severity": "high", "finding": f"LOLBin usage: {[m['bin'] for m in lols['matches']]}",
                         "mitre": sorted({m['technique'] for m in lols['matches']}),
                         "evidence": lols["matches"][:5]})
    iocs = extract_iocs(text)
    timeline = _build_timeline(parsed)
    summary = _summarize(parsed, findings)
    return {
        "log_type": kind, "lines": len(lines), "parsed": len(parsed),
        "parse_errors": parse_errors, "time_range": _time_range(parsed),
        "summary": summary,
        "findings": sorted(findings, key=lambda f: severity_rank(f.get("severity", "info"))),
        "severity_counts": dict(Counter(f.get("severity", "info") for f in findings)),
        "iocs": iocs["categories"], "ioc_count": iocs["count"],
        "timeline": timeline[:200],
        "lolbins": lols,
        "recommendations": _recommendations(findings),
    }


def detect_log_type(lines: Sequence[str]) -> str:
    sample = "\n".join(lines[:80])
    low = sample.lower()
    if '"event_type"' in low and ('"alert"' in low or '"flow"' in low) and "suricata" in low:
        return "suricata"
    if '"event_type"' in low and ('"src_ip"' in low or '"dest_ip"' in low):
        return "suricata"
    if "#fields" in low and "\t" in sample:
        return "zeek"
    if '"eventname"' in low and ('"useridentity"' in low or '"sourceipaddress"' in low):
        return "cloud"
    if '"operationname"' in low and ('"azure' in low or '"signinlogs"' in low or '"resulttype"' in low):
        return "cloud"
    if '"protoPayload"' in low or '"cloudaudit"' in low:
        return "cloud"
    if ("sysmon" in low or '"eventid": 1' in low or re.search(r"\bevent\s*id\s*[:=]\s*(1|3|8|10|11|13|22)\b", low)):
        return "sysmon"
    if re.search(r"\bevent\s*(?:id|code)\s*[:=]\s*\d{3,4}\b", low) or '"eventid"' in low or "<eventid>" in low:
        return "windows"
    if "sshd[" in low or "failed password" in low or "accepted password" in low or "sudo:" in low or "pam_unix" in low:
        return "auth"
    if re.search(r'"(?:GET|POST|PUT|DELETE|HEAD|OPTIONS) /[^"]*HTTP/', sample) or \
       re.search(r"\s(?:GET|POST)\s+/\S+\s+HTTP/", sample):
        return "web"
    if re.search(r"\b(?:sshd|systemd|kernel|audit)\b", low):
        return "syslog"
    return "generic"


def _parse_line(line: str, kind: str) -> Optional[Dict[str, Any]]:
    if line.startswith("{"):
        try:
            obj = json.loads(line)
            return _normalize_json(obj, kind)
        except Exception:
            pass
    if kind == "zeek" and line.startswith("#"):
        return None
    if kind == "web" or re.search(r'"(?:GET|POST|PUT|DELETE|HEAD|OPTIONS) \S+ HTTP/', line):
        return _parse_web(line)
    if kind == "auth":
        return _parse_auth(line)
    if kind == "sysmon":
        return _parse_kv_event(line, "sysmon")
    if kind == "windows":
        return _parse_windows_text(line)
    if kind == "zeek":
        return _parse_zeek(line)
    return _parse_generic(line)


def _normalize_json(obj: Dict[str, Any], kind: str) -> Dict[str, Any]:
    ev: Dict[str, Any] = {"raw": obj, "source": kind}
    ev["timestamp"] = _first(obj, "timestamp", "@timestamp", "TimeCreated", "time",
                             "utctime", "eventTime", "ts")
    ev["host"] = _first(obj, "host", "Computer", "hostname", "device", "ComputerName",
                        "DeviceName", "host_name")
    ev["user"] = _first(obj, "user", "UserName", "TargetUserName", "AccountName",
                        "userIdentity", "principal", "user_name")
    if isinstance(ev.get("user"), dict):
        ev["user"] = _first(ev["user"], "userName", "arn", "principalId", "name")
    ev["event_id"] = _to_int(_first(obj, "EventID", "event_id", "eventID", "eventCode",
                                    "eventcode", "EventCode"))
    ev["message"] = _first(obj, "message", "Message", "Description", "eventName",
                           "operationName", "signature", "alert", "rule", "msg", "CommandLine")
    ev["src_ip"] = _first(obj, "src_ip", "source_ip", "SourceIp", "IpAddress",
                          "sourceIPAddress", "ipAddress", "ClientIP", "src")
    ev["dst_ip"] = _first(obj, "dest_ip", "destination_ip", "DestinationIp",
                          "RemoteIP", "dst", "destinationIPAddress")
    ev["dst_port"] = _to_int(_first(obj, "dest_port", "DestinationPort", "destport", "dst_port",
                                    "destinationPort", "RemotePort"))
    ev["proto"] = _first(obj, "proto", "protocol", "Protocol", "networkProtocol")
    ev["process"] = _first(obj, "Image", "process", "ProcessName", "ImagePath",
                           "NewProcessName", "exe", "process_name")
    ev["parent"] = _first(obj, "ParentImage", "ParentProcessName", "parent_process",
                          "ParentProcess")
    ev["cmdline"] = _first(obj, "CommandLine", "command_line", "ProcessCommandLine",
                           "commandLine", "cmd")
    ev["level"] = _first(obj, "level", "Level", "severity", "Severity", "alert.severity")
    ev["event_type"] = _first(obj, "event_type", "EventType", "type")
    ev["status"] = _first(obj, "status", "Status", "result", "resultType", "response_status")
    ev["url"] = _first(obj, "url", "uri", "request_uri", "RequestUri", "http_url")
    ev["method"] = _first(obj, "method", "http_method", "httpMethod")
    ev["user_agent"] = _first(obj, "user_agent", "http_user_agent", "UserAgent", "userAgent")
    ev["bytes"] = _to_int(_first(obj, "bytes", "size", "response_body_len", "bytes_out",
                                 "flow.bytes_toclient", "network.bytes"))
    ev["rule"] = _first(obj, "rule", "signature", "alert.signature", "name")
    ev["action"] = _first(obj, "action", "decision", "verdict", "outcome")
    # Suricata nested
    if isinstance(obj.get("alert"), dict):
        ev["rule"] = obj["alert"].get("signature")
        ev["level"] = obj["alert"].get("severity")
    if isinstance(obj.get("eventName"), str) and kind == "cloud":
        ev["action"] = obj["eventName"]
        ev["user"] = _cloud_user(obj)
        ev["src_ip"] = _first(obj, "sourceIPAddress", "ipAddress", "callerIpAddress")
        ev["message"] = obj["eventName"]
    return ev


def _first(obj: Any, *keys: str) -> Any:
    if not isinstance(obj, dict):
        return ""
    for k in keys:
        if k in obj and obj[k] not in (None, ""):
            return obj[k]
        # nested dotted path
        if "." in k:
            cur = obj
            for part in k.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    cur = None
                    break
            if cur not in (None, ""):
                return cur
    for k, v in obj.items():
        if k.lower() in {x.lower() for x in keys} and v not in (None, ""):
            return v
    return ""


def _cloud_user(obj: Dict[str, Any]) -> str:
    u = obj.get("userIdentity")
    if isinstance(u, dict):
        return str(u.get("userName") or u.get("arn") or u.get("principalId") or
                   u.get("type") or "")
    if isinstance(obj.get("properties"), dict):
        p = obj["properties"]
        return str(p.get("userPrincipalName") or p.get("account") or "")
    return str(obj.get("user") or obj.get("caller") or "")


def _to_int(v: Any) -> Optional[int]:
    try:
        return int(str(v).strip())
    except Exception:
        return None


def _parse_web(line: str) -> Optional[Dict[str, Any]]:
    m = re.match(r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>[A-Z]+)\s+(?P<url>\S+)(?:\s+HTTP/[^"]+)?"\s+(?P<status>\d{3})\s+(?P<bytes>\d+|-)(?:\s+"(?P<ref>[^"]*)"\s+"(?P<ua>[^"]*)")?', line)
    if not m:
        # nginx JSON or other
        return _parse_generic(line)
    d = m.groupdict()
    ts = d.get("time", "")
    dt = None
    try:
        dt = datetime.strptime(ts.split()[0], "%d/%b/%Y:%H:%M:%S")
        tz = ts.split()[-1] if len(ts.split()) > 1 else "+0000"
        if re.match(r"[+-]\d{4}", tz):
            sign = 1 if tz[0] == "+" else -1
            dt = dt.replace(tzinfo=timezone(sign * timedelta(hours=int(tz[1:3]),
                                                             minutes=int(tz[3:5]))))
    except Exception:
        dt = parse_time(ts)
    return {"timestamp": dt.isoformat() if dt else ts, "source": "web",
            "src_ip": d["ip"], "method": d["method"], "url": d["url"],
            "status": int(d["status"]), "bytes": _to_int(d.get("bytes") or 0) or 0,
            "user_agent": d.get("ua") or "", "referer": d.get("ref") or "",
            "message": f'{d["method"]} {d["url"]} {d["status"]}'}


def _parse_auth(line: str) -> Optional[Dict[str, Any]]:
    ts = line[:15]
    try:
        dt = datetime.strptime(f"{datetime.now().year} {ts}",
                               "%Y %b %d %H:%M:%S").replace(tzinfo=timezone.utc)
        ts_out = dt.isoformat()
    except Exception:
        ts_out = ts
    ev: Dict[str, Any] = {"timestamp": ts_out, "source": "auth", "raw": line,
                          "message": line}
    m = re.search(r"sshd\[\d+\]: (Failed|Accepted) (\S+) for (?:invalid user )?(\S+) from (\S+) port (\d+)", line)
    if m:
        ev.update({"action": m.group(1).lower(), "method": m.group(2),
                   "user": m.group(3), "src_ip": m.group(4),
                   "src_port": int(m.group(5)),
                   "status": "failure" if m.group(1) == "Failed" else "success"})
        return ev
    m = re.search(r"Failed password for (?:invalid user )?(\S+) from (\S+)", line)
    if m:
        ev.update({"user": m.group(1), "src_ip": m.group(2), "action": "failed_password",
                   "status": "failure"})
        return ev
    m = re.search(r"Accepted (?:password|publickey) for (\S+) from (\S+)", line)
    if m:
        ev.update({"user": m.group(1), "src_ip": m.group(2), "action": "accepted",
                   "status": "success"})
        return ev
    m = re.search(r"sudo:\s+(\S+)\s*:.*COMMAND=(.*)", line)
    if m:
        ev.update({"user": m.group(1), "cmdline": m.group(2), "action": "sudo",
                   "status": "success"})
        return ev
    m = re.search(r"(?:useradd|usermod|groupadd|passwd)\[?\d*\]?:?\s*(.*)", line)
    if m:
        ev.update({"action": "account_change", "message": m.group(1)})
        return ev
    return ev


def _parse_kv_event(line: str, source: str) -> Dict[str, Any]:
    ev: Dict[str, Any] = {"source": source, "raw": line, "message": line}
    for key in ("EventID", "EventCode", "UtcTime", "Computer", "User", "Image",
                "ParentImage", "CommandLine", "TargetImage", "SourceImage",
                "DestinationIp", "DestinationPort", "QueryName", "TargetFilename"):
        m = re.search(rf"\b{key}\s*[:=]\s*([^\r\n\t]+?)(?=\s+\w+\s*[:=]|$)", line)
        if m:
            ev[_snake(key)] = m.group(1).strip()
    ev["event_id"] = _to_int(ev.get("event_id") or ev.get("event_code"))
    ev["timestamp"] = ev.get("utc_time") or line[:19]
    return ev


def _parse_windows_text(line: str) -> Dict[str, Any]:
    ev = _parse_kv_event(line, "windows")
    m = re.search(r"\b(?:Event\s*ID|EventCode)\s*[:=]\s*(\d+)", line, re.I)
    if m:
        ev["event_id"] = int(m.group(1))
    m = re.search(r"\b(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})", line)
    if m:
        ev["timestamp"] = m.group(1)
    return ev


def _parse_zeek(line: str) -> Dict[str, Any]:
    fields = line.rstrip("\n").split("\t")
    return {"raw": line, "source": "zeek", "message": line,
            "timestamp": fields[0] if fields else "",
            "src_ip": fields[2] if len(fields) > 2 else "",
            "dst_ip": fields[4] if len(fields) > 4 else "",
            "dst_port": _to_int(fields[5]) if len(fields) > 5 else None,
            "proto": fields[6] if len(fields) > 6 else ""}


def _parse_generic(line: str) -> Dict[str, Any]:
    ev: Dict[str, Any] = {"raw": line, "message": line, "source": "generic"}
    m = re.search(r"\b(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)", line)
    if m:
        ev["timestamp"] = m.group(1)
    m = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", line)
    if m:
        ev["src_ip"] = m.group(0)
    m = re.search(r"\b(ERROR|CRITICAL|WARN(?:ING)?|INFO|DEBUG|FATAL)\b", line, re.I)
    if m:
        ev["level"] = m.group(1)
    if any(k in line.lower() for k in ("failed", "denied", "blocked", "error", "unauthorized")):
        ev["status"] = "failure"
    return ev


# --------------------------------------------------------------------------- #
#  Findings
# --------------------------------------------------------------------------- #
def _windows_findings(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    failed = [e for e in events if e.get("event_id") == 4625]
    success = [e for e in events if e.get("event_id") == 4624]
    if len(failed) >= 10:
        by_ip = Counter(e.get("src_ip") for e in failed if e.get("src_ip"))
        by_user = Counter(e.get("user") for e in failed if e.get("user"))
        findings.append({"severity": "high", "finding": f"Multiple failed logons ({len(failed)})",
                         "mitre": ["T1110"], "evidence": {"top_ips": by_ip.most_common(5),
                                                          "top_users": by_user.most_common(5)}})
        if by_user and max(by_user.values()) >= 5 and len(by_user) >= 5:
            findings.append({"severity": "high", "finding": "Possible password spray (many users, repeated failures)",
                             "mitre": ["T1110.003"], "evidence": dict(by_user.most_common(10))})
    for e in events:
        eid = e.get("event_id")
        meta = WINDOWS_EVENTS.get(eid) if eid else None
        if meta and meta["severity"] in ("critical", "high"):
            findings.append({"severity": meta["severity"], "finding": meta["name"],
                             "mitre": [meta["technique"]] if meta["technique"] else [],
                             "evidence": _short_evidence(e)})
    if failed and success:
        fail_ips = {e.get("src_ip") for e in failed if e.get("src_ip")}
        for e in success:
            if e.get("src_ip") in fail_ips:
                findings.append({"severity": "critical", "finding": "Successful logon after failures from same source",
                                 "mitre": ["T1110", "T1078"], "evidence": _short_evidence(e)})
    return _dedupe_findings(findings)


def _sysmon_findings(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    for e in events:
        eid = e.get("event_id")
        meta = SYSMON_EVENTS.get(eid) if eid else None
        if meta and meta["severity"] in ("critical", "high"):
            findings.append({"severity": meta["severity"], "finding": meta["name"],
                             "mitre": [meta["technique"]] if meta["technique"] else [],
                             "evidence": _short_evidence(e)})
        proc = str(e.get("process") or "").lower()
        parent = str(e.get("parent") or "").lower()
        cmd = str(e.get("cmdline") or "")
        if proc.endswith(("powershell.exe", "pwsh.exe")) and any(
                k in cmd.lower() for k in ("-enc", "downloadstring", "invoke-expression",
                                            "iex", "bypass", "hidden")):
            findings.append({"severity": "high", "finding": "Suspicious PowerShell command line",
                             "mitre": ["T1059.001"], "evidence": {"process": proc, "cmdline": cmd[:300]}})
        if parent.endswith(("winword.exe", "excel.exe", "powerpnt.exe", "outlook.exe")) and \
                proc.endswith(("cmd.exe", "powershell.exe", "wscript.exe", "mshta.exe", "rundll32.exe")):
            findings.append({"severity": "critical", "finding": "Office application spawned a script/shell",
                             "mitre": ["T1566.001", "T1204.002"], "evidence": {"parent": parent, "process": proc}})
        if eid == 10 and "lsass.exe" in str(e.get("target_image") or e.get("raw", "")).lower():
            findings.append({"severity": "critical", "finding": "Process accessed LSASS",
                             "mitre": ["T1003.001"], "evidence": _short_evidence(e)})
        if eid == 8:
            findings.append({"severity": "critical", "finding": "Remote thread creation (injection)",
                             "mitre": ["T1055"], "evidence": _short_evidence(e)})
        if eid in (19, 20, 21):
            findings.append({"severity": "critical", "finding": "WMI event subscription activity",
                             "mitre": ["T1546.003"], "evidence": _short_evidence(e)})
        if eid == 25:
            findings.append({"severity": "critical", "finding": "Process tampering (hollowing)",
                             "mitre": ["T1055.012"], "evidence": _short_evidence(e)})
        if proc.endswith(("certutil.exe", "mshta.exe", "regsvr32.exe", "rundll32.exe", "wmic.exe",
                          "bitsadmin.exe")) and any(k in cmd.lower() for k in ("http", "javascript:", "scrobj", "urlcache")):
            findings.append({"severity": "high", "finding": f"LOLBin proxy execution: {proc}",
                             "mitre": ["T1218", "T1105"], "evidence": {"cmdline": cmd[:300]}})
    return _dedupe_findings(findings)


def _auth_findings(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    failed = [e for e in events if e.get("status") == "failure" or "Failed" in str(e.get("message", ""))]
    success = [e for e in events if e.get("status") == "success" or "Accepted" in str(e.get("message", ""))]
    if len(failed) >= 10:
        by_ip = Counter(e.get("src_ip") for e in failed)
        findings.append({"severity": "high", "finding": f"SSH authentication failures ({len(failed)})",
                         "mitre": ["T1110.001"], "evidence": {"top_ips": by_ip.most_common(8)}})
        if len(by_ip) > 5 and len(failed) > 30:
            findings.append({"severity": "critical", "finding": "Distributed SSH brute force / botnet activity",
                             "mitre": ["T1110"], "evidence": {"unique_ips": len(by_ip)}})
    fail_ips = {e.get("src_ip") for e in failed if e.get("src_ip")}
    for e in success:
        if e.get("src_ip") in fail_ips:
            findings.append({"severity": "critical", "finding": "Successful SSH login after failures",
                             "mitre": ["T1110", "T1078"], "evidence": _short_evidence(e)})
    for e in events:
        if e.get("action") == "sudo":
            findings.append({"severity": "medium", "finding": "sudo command executed",
                             "mitre": ["T1548.003"], "evidence": _short_evidence(e)})
        if "useradd" in str(e.get("raw", "")) or "usermod" in str(e.get("raw", "")) or "groupadd" in str(e.get("raw", "")):
            findings.append({"severity": "high", "finding": "Local account/group modification",
                             "mitre": ["T1136.001"], "evidence": _short_evidence(e)})
    return _dedupe_findings(findings)


def _web_findings(events: List[Dict[str, Any]], lines: Sequence[str]) -> List[Dict[str, Any]]:
    findings = []
    attacks = Counter()
    evidence = defaultdict(list)
    for line in lines:
        for attack, patterns in WEB_ATTACK_PATTERNS.items():
            if any(re.search(p, line) for p in patterns):
                attacks[attack] += 1
                if len(evidence[attack]) < 5:
                    evidence[attack].append(line[:300])
    for attack, count in attacks.items():
        sev = "critical" if attack in ("SQL injection", "Log4Shell", "Web shell access",
                                       "Command injection") else "high"
        findings.append({"severity": sev, "finding": f"Web attack pattern: {attack} ({count})",
                         "mitre": ["T1190"], "evidence": evidence[attack]})
    status = Counter(e.get("status") for e in events)
    if status.get(404, 0) >= 30:
        findings.append({"severity": "medium", "finding": f"High 404 volume ({status[404]}) — possible content discovery",
                         "mitre": ["T1595.002"], "evidence": {"404": status[404]}})
    if status.get(500, 0) + status.get(502, 0) + status.get(503, 0) >= 10:
        findings.append({"severity": "medium", "finding": "Server error burst",
                         "mitre": ["T1190"], "evidence": {k: v for k, v in status.items() if k >= 500}})
    ua_counts = Counter()
    for line in lines:
        low = line.lower()
        for ua in SUSPICIOUS_UA:
            if ua in low:
                ua_counts[ua] += 1
    if ua_counts:
        findings.append({"severity": "high", "finding": "Security scanner / attack tool user-agent",
                         "mitre": ["T1595"], "evidence": dict(ua_counts.most_common(8))})
    # large responses / exfil
    big = [e for e in events if (e.get("bytes") or 0) > 5 * 1024 * 1024]
    if len(big) >= 3:
        findings.append({"severity": "medium", "finding": "Large outbound HTTP responses",
                         "mitre": ["T1041"], "evidence": [{"url": e.get("url"), "bytes": e.get("bytes")} for e in big[:5]]})
    return _dedupe_findings(findings)


def _suricata_findings(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    alerts = Counter()
    for e in events:
        if e.get("event_type") == "alert" or e.get("rule"):
            alerts[str(e.get("rule") or "alert")] += 1
    for rule, count in alerts.most_common(20):
        findings.append({"severity": "high", "finding": f"IDS alert: {rule} ({count})",
                         "mitre": ["T1071"], "evidence": {"signature": rule, "count": count}})
    return _dedupe_findings(findings)


def _zeek_findings(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    ports = Counter(e.get("dst_port") for e in events if e.get("dst_port"))
    for port, count in ports.most_common(10):
        if port in RISKY_PORTS:
            findings.append({"severity": "medium", "finding": f"{RISKY_PORTS[port]} traffic observed ({count} flows)",
                             "mitre": ["T1021"], "evidence": {"port": port, "flows": count}})
    return _dedupe_findings(findings)


def _cloud_findings(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    for e in events:
        action = str(e.get("action") or e.get("message") or "")
        for key, (sev, desc, tech) in CLOUD_SENSITIVE_EVENTS.items():
            if key.lower() == action.lower():
                findings.append({"severity": sev, "finding": f"Cloud: {desc}",
                                 "mitre": [tech], "evidence": _short_evidence(e)})
                break
        if str(e.get("status", "")).lower() in ("failure", "failed", "false", "denied"):
            findings.append({"severity": "medium", "finding": "Cloud action failed/denied",
                             "mitre": ["T1078.004"], "evidence": _short_evidence(e)})
        src = str(e.get("src_ip") or "")
        if src and not _private_ip(src) and "consolelogin" in action.lower():
            pass
    # root account / new access key
    for e in events:
        raw = e.get("raw", {})
        if isinstance(raw, dict):
            ident = raw.get("userIdentity") or {}
            if isinstance(ident, dict) and ident.get("type") == "Root":
                findings.append({"severity": "critical", "finding": "AWS root account activity",
                                 "mitre": ["T1078.004"], "evidence": _short_evidence(e)})
            if str(raw.get("errorCode", "")).startswith("AccessDenied"):
                findings.append({"severity": "medium", "finding": "Access denied event",
                                 "mitre": ["T1078.004"], "evidence": _short_evidence(e)})
    return _dedupe_findings(findings)


def _generic_findings(events: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
    findings = []
    low = text.lower()
    if "failed" in low and ("login" in low or "password" in low):
        count = low.count("failed")
        if count >= 5:
            findings.append({"severity": "medium", "finding": f"Repeated authentication failures ({count})",
                             "mitre": ["T1110"], "evidence": []})
    if any(k in low for k in ("mimikatz", "lsass", "sekurlsa")):
        findings.append({"severity": "critical", "finding": "Credential dumping indicators",
                         "mitre": ["T1003"], "evidence": []})
    return findings


def _short_evidence(e: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("timestamp", "host", "user", "src_ip", "dst_ip", "dst_port",
            "event_id", "process", "parent", "cmdline", "url", "rule", "action")
    out = {k: e.get(k) for k in keys if e.get(k) not in (None, "", 0)}
    if "raw" in e and isinstance(e["raw"], str):
        out["raw"] = e["raw"][:300]
    return out


def _dedupe_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for f in findings:
        key = (f.get("severity"), f.get("finding"))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def _private_ip(ip: str) -> bool:
    try:
        import ipaddress
        return ipaddress.ip_address(ip).is_private
    except Exception:
        return False


# --------------------------------------------------------------------------- #
#  Timeline / summary / recommendations
# --------------------------------------------------------------------------- #
def _build_timeline(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for e in events:
        dt = parse_time(e.get("timestamp"))
        if not dt:
            continue
        rows.append({"time": dt, "timestamp": fmt_time(dt),
                     "source": e.get("source", ""),
                     "host": e.get("host", ""), "user": e.get("user", ""),
                     "event": str(e.get("message") or e.get("event")
                                  or e.get("description") or e.get("activity")
                                  or e.get("event_id") or "")[:220],
                     "src_ip": e.get("src_ip", ""), "dst_ip": e.get("dst_ip", ""),
                     "severity": _event_severity(e)})
    rows.sort(key=lambda r: r["time"])
    for r in rows:
        r.pop("time", None)
    return rows


def _event_severity(e: Dict[str, Any]) -> str:
    eid = e.get("event_id")
    if eid and eid in WINDOWS_EVENTS:
        return WINDOWS_EVENTS[eid]["severity"]
    if eid and eid in SYSMON_EVENTS:
        return SYSMON_EVENTS[eid]["severity"]
    level = str(e.get("level", "")).lower()
    if level in ("critical", "high", "medium", "low", "info"):
        return level
    if str(e.get("status", "")).lower() in ("failure", "failed", "denied"):
        return "medium"
    return "info"


def _time_range(events: List[Dict[str, Any]]) -> Dict[str, str]:
    times = [parse_time(e.get("timestamp")) for e in events]
    times = [t for t in times if t]
    if not times:
        return {"start": "", "end": "", "duration": ""}
    start, end = min(times), max(times)
    return {"start": fmt_time(start), "end": fmt_time(end),
            "duration": str(end - start)}


def _summarize(parsed: List[Dict[str, Any]], findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"events": len(parsed),
            "unique_users": len({e.get("user") for e in parsed if e.get("user")}),
            "unique_hosts": len({e.get("host") for e in parsed if e.get("host")}),
            "unique_source_ips": len({e.get("src_ip") for e in parsed if e.get("src_ip")}),
            "unique_dest_ips": len({e.get("dst_ip") for e in parsed if e.get("dst_ip")}),
            "findings": len(findings),
            "critical": sum(1 for f in findings if f.get("severity") == "critical"),
            "high": sum(1 for f in findings if f.get("severity") == "high"),
            "medium": sum(1 for f in findings if f.get("severity") == "medium"),
            "low": sum(1 for f in findings if f.get("severity") == "low")}


def _recommendations(findings: List[Dict[str, Any]]) -> List[str]:
    text = " ".join(f.get("finding", "") for f in findings).lower()
    recs = []
    if "failed" in text or "brute" in text or "spray" in text:
        recs.append("Enable account lockout/rate limiting and block abusive source IPs.")
        recs.append("Require MFA for remote access and disable unused accounts.")
    if "lsass" in text or "credential" in text:
        recs.append("Enable LSASS protection (RunAsPPL/Credential Guard) and alert on process access.")
    if "powershell" in text or "office" in text:
        recs.append("Enable PowerShell script-block logging and block Office child processes.")
    if "web attack" in text or "scanner" in text:
        recs.append("Review WAF rules and rate-limit scanners; verify no successful exploitation.")
    if "cloud" in text or "iam" in text:
        recs.append("Review IAM changes, enforce MFA, and enable CloudTrail/Audit Log immutability.")
    if "wmi" in text or "scheduled" in text or "log" in text:
        recs.append("Audit persistence locations and centralize logs with tamper protection.")
    if "ransom" in text or "encrypt" in text or "shadow" in text:
        recs.append("Verify offline/immutable backups and isolate affected hosts immediately.")
    return list(dict.fromkeys(recs)) or ["Continue monitoring and correlate with endpoint telemetry."]


# --------------------------------------------------------------------------- #
#  Timeline merge
# --------------------------------------------------------------------------- #
def build_timeline(items: Sequence[Any]) -> Dict[str, Any]:
    events = []
    for item in items:
        if isinstance(item, str):
            ev = _parse_generic(item)
            if ev:
                events.append(ev)
        elif isinstance(item, dict):
            ts = item.get("timestamp") or item.get("time") or item.get("date")
            dt = parse_time(ts)
            if dt:
                events.append({**item, "timestamp": dt.isoformat()})
    rows = _build_timeline(events)
    phases = _phase_tags(rows)
    return {"events": rows, "count": len(rows), "phases": phases,
            "time_range": _time_range(events),
            "attack_story": _story(rows)}


def _phase_tags(rows: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    phases = {"initial_access": [], "execution": [], "persistence": [],
              "privilege_escalation": [], "defense_evasion": [],
              "credential_access": [], "discovery": [], "lateral_movement": [],
              "collection": [], "command_control": [], "exfiltration": [], "impact": []}
    keys = {
        "initial_access": ("phish", "login", "vpn", "exploit", "attachment", "web"),
        "execution": ("process", "powershell", "cmd", "script", "mshta", "wmic"),
        "persistence": ("run key", "scheduled", "service", "wmi", "startup", "cron"),
        "privilege_escalation": ("privilege", "uac", "sudo", "token", "admin"),
        "defense_evasion": ("clear", "disable", "evasion", "amsi", "etw", "timestomp"),
        "credential_access": ("lsass", "credential", "mimikatz", "brute", "kerberos"),
        "discovery": ("discovery", "net user", "whoami", "scan", "enum"),
        "lateral_movement": ("rdp", "smb", "winrm", "psexec", "lateral", "4624"),
        "collection": ("collect", "archive", "keylog", "screenshot", "clipboard"),
        "command_control": ("c2", "beacon", "dns tunnel", "callback", "http"),
        "exfiltration": ("exfil", "upload", "transfer", "mega", "dropbox"),
        "impact": ("ransom", "encrypt", "wiper", "delete", "encrypt", "lock"),
    }
    for i, row in enumerate(rows):
        text = (row.get("event", "") + " " + row.get("source", "")).lower()
        for phase, words in keys.items():
            if any(w in text for w in words):
                phases[phase].append(i)
    return {k: v for k, v in phases.items() if v}


def _story(rows: List[Dict[str, Any]]) -> List[str]:
    if not rows:
        return []
    story = [f"At {rows[0]['timestamp']}, activity begins with: {rows[0]['event'][:160]}."]
    for row in rows[1:6]:
        story.append(f"At {row['timestamp']}, {row.get('host') or row.get('user') or 'an asset'}: {row['event'][:160]}.")
    if len(rows) > 6:
        story.append(f"Activity continues through {rows[-1]['timestamp']} ({len(rows)} events total).")
    return story


# --------------------------------------------------------------------------- #
#  Beacon analysis
# --------------------------------------------------------------------------- #
def beacon_analysis(times: Sequence[Any]) -> Dict[str, Any]:
    parsed = []
    for t in times:
        if isinstance(t, (int, float)):
            parsed.append(float(t))
        else:
            dt = parse_time(t)
            if dt:
                parsed.append(dt.timestamp())
    parsed = sorted(parsed)
    if len(parsed) < 3:
        return {"error": "need at least 3 timestamps", "count": len(parsed)}
    deltas = [b - a for a, b in zip(parsed, parsed[1:]) if b > a]
    if not deltas:
        return {"error": "no positive deltas"}
    mean = statistics.mean(deltas)
    median = statistics.median(deltas)
    stdev = statistics.pstdev(deltas) if len(deltas) > 1 else 0.0
    jitter = (stdev / mean * 100) if mean else 0.0
    rounded = Counter(round(d, 1) for d in deltas)
    mode, mode_count = rounded.most_common(1)[0]
    confidence = 0
    if len(deltas) >= 5:
        confidence = 40
    if jitter < 15:
        confidence += 30
    elif jitter < 35:
        confidence += 15
    if mode_count / max(1, len(deltas)) > 0.4:
        confidence += 20
    if mean < 5:
        confidence = min(confidence, 35)
    framework = _guess_framework(mean, jitter, mode)
    return {
        "count": len(parsed), "intervals": len(deltas),
        "mean_seconds": round(mean, 2), "median_seconds": round(median, 2),
        "stdev_seconds": round(stdev, 2), "jitter_percent": round(jitter, 1),
        "min_seconds": round(min(deltas), 2), "max_seconds": round(max(deltas), 2),
        "mode_seconds": mode, "mode_frequency": mode_count,
        "confidence": min(98, confidence), "framework_guess": framework,
        "verdict": "likely beaconing" if confidence >= 60 else
                   ("possible beaconing" if confidence >= 40 else "inconclusive"),
        "is_regular": jitter < 20 and len(deltas) >= 4,
    }


def _guess_framework(mean: float, jitter: float, mode: float) -> str:
    if 50 <= mean <= 70 and jitter < 25:
        return "Cobalt Strike (default 60s sleep) or similar"
    if 5 <= mean <= 15:
        return "Sliver / short-interval implant"
    if 300 <= mean <= 3600:
        return "Long-sleep RAT / scheduled callback"
    if mean > 3600:
        return "Dormant / daily callback implant"
    if jitter > 40:
        return "Custom or jittered implant"
    return "Unknown C2 framework"


# --------------------------------------------------------------------------- #
#  Lateral movement
# --------------------------------------------------------------------------- #
def lateral_movement(events: Sequence[Any]) -> Dict[str, Any]:
    rows = []
    for item in events:
        if isinstance(item, str):
            ev = _parse_auth(item) or _parse_generic(item)
        elif isinstance(item, dict):
            ev = item
        else:
            continue
        if not ev:
            continue
        text = str(ev.get("message") or ev.get("raw") or "").lower()
        eid = ev.get("event_id")
        method = None
        if eid == 4624 or "accepted" in text:
            method = "RDP" if "type 10" in text else ("SMB" if eid == 4624 and "type 3" in text else "logon")
        elif eid == 4625 or "failed" in text:
            method = "failed-auth"
        elif "psexec" in text or "psexesvc" in text:
            method = "PSExec"
        elif "wmic" in text or "win32_process" in text:
            method = "WMI"
        elif "winrm" in text or "wsman" in text or eid in (91, 168):
            method = "WinRM"
        elif "smb" in text:
            method = "SMB"
        if not method:
            continue
        rows.append({"src": ev.get("src_ip") or ev.get("host") or "?",
                     "dst": ev.get("dst_ip") or ev.get("host") or "?",
                     "user": ev.get("user", ""), "method": method,
                     "timestamp": ev.get("timestamp", ""),
                     "success": ev.get("status") == "success" and "failed" not in method})
    edges = Counter((r["src"], r["dst"], r["method"]) for r in rows)
    graph = [{"src": s, "dst": d, "method": m, "count": c}
             for (s, d, m), c in edges.most_common(100)]
    indicators = []
    if any(r["method"] == "failed-auth" for r in rows):
        indicators.append("Failed authentication attempts precede lateral movement")
    if any("pth" in str(r).lower() or "ntlm" in str(r).lower() for r in rows):
        indicators.append("NTLM/pass-the-hash indicators")
    if len({r["dst"] for r in rows}) >= 3:
        indicators.append("Multiple destination hosts from one campaign")
    return {"events": len(rows), "edges": graph,
            "source_hosts": sorted({r["src"] for r in rows}),
            "destination_hosts": sorted({r["dst"] for r in rows}),
            "methods": dict(Counter(r["method"] for r in rows)),
            "indicators": indicators,
            "path": _movement_path(graph),
            "recommendations": ["Reset credentials for involved accounts",
                                "Isolate destination hosts and review SMB/RDP logs",
                                "Enforce tiered admin and disable NTLM where possible"]}


def _movement_path(edges: List[Dict[str, Any]]) -> List[str]:
    if not edges:
        return []
    adj = defaultdict(list)
    for e in edges:
        adj[e["src"]].append(e["dst"])
    start = max(adj, key=lambda k: len(adj[k]), default="")
    path = [start]
    seen = {start}
    cur = start
    for _ in range(12):
        nxt = next((d for d in adj.get(cur, []) if d not in seen), None)
        if not nxt:
            break
        path.append(nxt)
        seen.add(nxt)
        cur = nxt
    return path


# --------------------------------------------------------------------------- #
#  Email headers
# --------------------------------------------------------------------------- #
def analyze_email(text: str) -> Dict[str, Any]:
    try:
        msg = email.message_from_string(text, policy=policy.default)
    except Exception:
        # header-only input
        msg = email.message_from_string(text + "\n\n", policy=policy.compat32)
    headers = {k.lower(): str(v) for k, v in msg.items()}
    received = msg.get_all("Received") or []
    hops = []
    for r in reversed(received):  # oldest first
        ip = re.search(r"\[?((?:\d{1,3}\.){3}\d{1,3}|[0-9a-f:]{6,})\]?", r)
        hop = {"raw": r[:300].replace("\n", " "), "ip": ip.group(1) if ip else "",
               "from": _received_field(r, "from"), "by": _received_field(r, "by"),
               "timestamp": _received_time(r)}
        hops.append(hop)
    auth = headers.get("authentication-results", "")
    spf = _auth_result(auth, "spf")
    dkim = _auth_result(auth, "dkim")
    dmarc = _auth_result(auth, "dmarc")
    from_addr = email.utils.parseaddr(headers.get("from", ""))[1].lower()
    reply_to = email.utils.parseaddr(headers.get("reply-to", ""))[1].lower()
    return_path = email.utils.parseaddr(headers.get("return-path", ""))[1].lower()
    from_domain = from_addr.split("@")[-1] if "@" in from_addr else ""
    reply_domain = reply_to.split("@")[-1] if "@" in reply_to else ""
    received_spf = headers.get("received-spf", "")
    findings = []
    if spf == "fail" or "fail" in received_spf.lower():
        findings.append({"severity": "high", "finding": "SPF fail"})
    if dkim == "fail":
        findings.append({"severity": "high", "finding": "DKIM fail"})
    if dmarc == "fail":
        findings.append({"severity": "critical", "finding": "DMARC fail"})
    if reply_to and reply_domain and from_domain and reply_domain != from_domain:
        findings.append({"severity": "high", "finding": f"Reply-To domain differs from From ({reply_domain} vs {from_domain})"})
    if return_path and from_domain and return_path.split("@")[-1] != from_domain:
        findings.append({"severity": "medium", "finding": "Return-Path differs from From domain"})
    display_name = email.utils.parseaddr(headers.get("from", ""))[0]
    if display_name and "@" in display_name:
        findings.append({"severity": "medium", "finding": "Display name contains an email address (spoof pattern)"})
    lookalike = _lookalike_domain(from_domain)
    if lookalike:
        findings.append({"severity": "high", "finding": f"Lookalike/punycode domain: {from_domain}"})
    body = ""
    attachments = []
    urls = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            filename = part.get_filename()
            if part.get_content_maintype() == "multipart":
                continue
            payload = part.get_payload(decode=True) or b""
            if filename or "attachment" in disp:
                attachments.append({"filename": filename or "",
                                    "content_type": ctype, "size": len(payload),
                                    "sha256": hashlib.sha256(payload).hexdigest(),
                                    "md5": hashlib.md5(payload).hexdigest(),
                                    "entropy": round(__import__("security_ops.util", fromlist=["entropy"]).entropy(payload), 3)})
            elif ctype in ("text/plain", "text/html"):
                try:
                    body += payload.decode(part.get_content_charset() or "utf-8", "replace")
                except Exception:
                    body += payload.decode("latin-1", "replace")
    else:
        payload = msg.get_payload(decode=True) or b""
        body = payload.decode(msg.get_content_charset() or "utf-8", "replace")
    urls = re.findall(r"https?://[^\s\"'<>]+", body)
    iocs = extract_iocs(text + "\n" + body)
    urgency = [w for w in ("urgent", "immediately", "verify your account", "password expires",
                           "invoice", "payment", "gift card", "wire transfer", "mfa",
                           "login", "click here", "action required") if w in body.lower()]
    if urgency:
        findings.append({"severity": "medium", "finding": f"Social-engineering language: {urgency}"})
    if attachments:
        risky = [a for a in attachments if a["filename"].lower().endswith(
            (".exe", ".dll", ".js", ".vbs", ".hta", ".lnk", ".iso", ".img", ".scr",
             ".bat", ".cmd", ".ps1", ".jar", ".msi", ".docm", ".xlsm", ".pptm", ".zip", ".rar", ".7z"))]
        if risky:
            findings.append({"severity": "high", "finding": "Risky attachment types",
                             "evidence": risky})
    return {
        "subject": headers.get("subject", ""), "from": from_addr,
        "display_name": display_name, "reply_to": reply_to,
        "return_path": return_path, "to": headers.get("to", ""),
        "date": headers.get("date", ""), "message_id": headers.get("message-id", ""),
        "x_mailer": headers.get("x-mailer", ""), "originating_ip": hops[0]["ip"] if hops else "",
        "received_chain": hops, "spf": spf, "dkim": dkim, "dmarc": dmarc,
        "authentication_results": auth, "from_domain": from_domain,
        "lookalike_domain": lookalike,
        "attachments": attachments, "urls": list(dict.fromkeys(urls))[:100],
        "urgency_words": urgency, "findings": findings,
        "iocs": iocs["categories"], "body_preview": body[:1200],
        "verdict": "phishing likely" if sum(1 for f in findings if f["severity"] in ("critical", "high")) >= 2 else
                   ("suspicious" if findings else "no strong phishing indicators"),
    }


def _received_field(value: str, key: str) -> str:
    m = re.search(rf"\b{key}\s+([^\s;]+)", value, re.I)
    return m.group(1) if m else ""


def _received_time(value: str) -> str:
    m = re.search(r";\s*(.+)$", value)
    return m.group(1).strip() if m else ""


def _auth_result(auth: str, mechanism: str) -> str:
    m = re.search(rf"\b{mechanism}=(\w+)", auth or "", re.I)
    return m.group(1).lower() if m else "unknown"


def _lookalike_domain(domain: str) -> str:
    if not domain:
        return ""
    if domain.startswith("xn--") or ".xn--" in domain:
        return domain
    brands = {"microsoft": ["micros0ft", "microsofft", "rnicrosoft", "microsft"],
              "google": ["g00gle", "goog1e", "gooogle"], "apple": ["app1e", "appIe"],
              "paypal": ["paypa1", "paypai"], "amazon": ["amaz0n", "amazan"],
              "dhl": ["dh1", "dhi"], "sberbank": ["sberbank-online", "sberbank24"]}
    low = domain.lower()
    for brand, variants in brands.items():
        if brand in low and low.split(".")[0] != brand:
            return domain
        if any(v in low for v in variants):
            return domain
    return ""


# --------------------------------------------------------------------------- #
#  LOLBins / persistence
# --------------------------------------------------------------------------- #
def scan_lolbins(text: str) -> Dict[str, Any]:
    low = text.lower()
    matches = []
    for binary, meta in LOLBINS.items():
        if re.search(rf"\b{re.escape(binary)}(?:\.exe)?\b", low):
            matches.append({"bin": binary, **meta})
    return {"matches": matches, "count": len(matches),
            "verdict": "LOLBin abuse indicators" if matches else "none found"}


def scan_persistence(text: str) -> Dict[str, Any]:
    from .knowledge import PERSISTENCE
    low = text.lower().replace("/", "\\")
    found = []
    for item in PERSISTENCE:
        loc = item["location"].lower().replace("/", "\\")
        keys = [loc, loc.split("\\")[-1]]
        if any(k and k in low for k in keys):
            found.append(item)
    return {"matches": found, "count": len(found),
            "categories": sorted({f["category"] for f in found}),
            "severity": "high" if found else "info"}
