"""SSRF-guarded web fetch + basic search helper."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse
import urllib.request
import urllib.parse

BLOCKED_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_safe_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    host = p.hostname
    if not host:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        for net in BLOCKED_NETS:
            if ip in net:
                return False
    return True


def fetch(url: str, timeout: int = 15, max_bytes: int = 2_000_000) -> dict:
    if not _is_safe_url(url):
        return {"ok": False, "error": "blocked by SSRF guard"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read(max_bytes)
            text = data.decode("utf-8", errors="replace")
            return {"ok": True, "url": url, "status": resp.status,
                    "content_type": resp.headers.get("Content-Type", ""),
                    "text": text, "truncated": len(data) >= max_bytes}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}


def search_duckduckgo(query: str, limit: int = 8) -> dict:
    url = "https://duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    r = fetch(url)
    if not r.get("ok"):
        return r
    import re
    results = []
    for m in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r["text"]):
        href, title = m.group(1), m.group(2)
        title = re.sub(r"<[^>]+>", "", title)
        results.append({"title": title.strip(), "url": href})
        if len(results) >= limit:
            break
    return {"ok": True, "query": query, "results": results}
