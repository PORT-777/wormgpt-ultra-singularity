"""Unified catalog and safe read tools for every vendored repository.

The hub links all vendor repos to three surfaces at once:

  1. Agent tools  -> tools/vendor_tool.py (auto-discovered, always callable)
  2. Plugins      -> plugins_catalog/vendor/hub.py (one plugin per repo)
  3. MCP          -> mcp_server.py (vendor_* tools on the local MCP server)
  4. Skills       -> skills_packs/vendor-hub.md (always-on playbook)

All file access is read-only and confined to <project>/vendor/<repo>.
Thousands of upstream SKILL.md files are indexed once and cached, then
searched on demand instead of being dumped into every prompt.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except Exception:
    pass

PROJECT_DIR = Path(__file__).resolve().parent.parent
VENDOR_DIR = PROJECT_DIR / "vendor"
DATA_DIR = Path(__file__).resolve().parent / "data"
INDEX_PATH = DATA_DIR / "vendor_index.json"
INDEX_VERSION = "v1"

MAX_INDEX_ENTRIES = int(os.getenv("VENDOR_MAX_INDEX_ENTRIES", "20000"))
MAX_READ_CHARS = int(os.getenv("VENDOR_MAX_READ_CHARS", "20000"))
MAX_SEARCH_RESULTS = 40
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build", "target"}

REPOS: List[Dict[str, Any]] = [
    {
        "id": "autogpt", "name": "AutoGPT", "dir": "autogpt",
        "url": "https://github.com/significant-gravitas/autogpt",
        "role": "Autonomous agent platform, prompt and tool architecture",
        "category": "ai",
        "keywords": ["agent", "autonomous", "prompt", "tools", "workflow"],
    },
    {
        "id": "claude-skills", "name": "Claude Skills", "dir": "claude-skills",
        "url": "https://github.com/alirezarezvani/claude-skills",
        "role": "Reusable skill packs and prompt playbooks",
        "category": "custom",
        "keywords": ["skills", "playbook", "prompt", "claude"],
    },
    {
        "id": "openhands", "name": "OpenHands", "dir": "openhands",
        "url": "https://github.com/OpenHands/openhands",
        "role": "Agent runtime, tool execution and workspace patterns",
        "category": "devops",
        "keywords": ["runtime", "tools", "workspace", "sandbox", "agent"],
    },
    {
        "id": "ecc", "name": "ECC", "dir": "ECC",
        "url": "https://github.com/affaan-m/ECC",
        "role": "Extended capability catalog and engineering references",
        "category": "custom",
        "keywords": ["capabilities", "engineering", "reference"],
    },
    {
        "id": "hermes-agent", "name": "Hermes Agent", "dir": "hermes-agent",
        "url": "https://github.com/nousresearch/hermes-agent",
        "role": "NousResearch autonomous agent patterns and tool use",
        "category": "ai",
        "keywords": ["agent", "tool-use", "research", "hermes"],
    },
    {
        "id": "lunar-source", "name": "Lunar Source", "dir": "lunar-source",
        "url": "",
        "role": "Local reference files: URL policy, secrets, tool patterns",
        "category": "security",
        "keywords": ["reference", "secret", "policy"],
    },
    {
        "id": "deepseek-harness", "name": "DeepSeek Harness", "dir": "deepseek-harness",
        "url": "https://github.com/deepseek-ai/deepseek-harness",
        "role": "DeepSeek agent harness, benchmarks and eval skills",
        "category": "ai",
        "keywords": ["deepseek", "harness", "eval", "benchmark", "agent"],
    },
    {
        "id": "career-ops", "name": "Career Ops", "dir": "career-ops",
        "url": "https://github.com/career-ops-hq/career-ops",
        "role": "Local AI job search, CV tailoring and application tracking",
        "category": "productivity",
        "keywords": ["job", "career", "cv", "resume", "hiring"],
    },
    {
        "id": "ohmyzsh", "name": "Oh My Zsh", "dir": "ohmyzsh",
        "url": "https://github.com/ohmyzsh/ohmyzsh",
        "role": "Shell framework: plugins, themes, lib helpers and tools",
        "category": "devops",
        "keywords": ["zsh", "shell", "terminal", "plugin", "theme"],
    },
    {
        "id": "ruflo", "name": "Ruflo", "dir": "ruflo",
        "url": "https://github.com/ruvnet/ruflo",
        "role": "Agent orchestration, swarms, SPARC and 400+ skills",
        "category": "ai",
        "keywords": ["swarm", "orchestration", "sparc", "agents", "ruflo"],
    },
    {
        "id": "agentic-skills", "name": "Agentic Awesome Skills", "dir": "agentic-awesome-skills",
        "url": "https://github.com/sickn33/agentic-awesome-skills",
        "role": "Large curated catalog of agent skill playbooks",
        "category": "custom",
        "keywords": ["skills", "catalog", "playbook", "awesome"],
    },
]

_BY_ID = {r["id"]: r for r in REPOS}
_LOCK = threading.RLock()
_CACHE: Optional[Dict[str, Any]] = None
_TEXT_EXT = {".py", ".md", ".txt", ".js", ".ts", ".tsx", ".jsx", ".json",
             ".yaml", ".yml", ".sh", ".zsh", ".toml", ".rst", ".html", ".css"}


class VendorError(ValueError):
    pass


def _repo_path(repo_id: str) -> Path:
    meta = _BY_ID.get(str(repo_id or "").strip())
    if not meta:
        raise VendorError(f"unknown repo: {repo_id}. Available: {', '.join(_BY_ID)}")
    path = (VENDOR_DIR / meta["dir"]).resolve()
    if not path.is_dir():
        raise VendorError(f"repo not checked out: {repo_id}")
    return path


def _safe_relative(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise VendorError("path escapes repository root") from exc
    if ".." in rel.split("/"):
        raise VendorError("path escapes repository root")
    return rel


def _commit(path: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=6,
        )
        return (out.stdout or "").strip() or "nogit"
    except Exception:
        return "nogit"


def _frontmatter(text: str, fallback: str) -> Tuple[str, str]:
    name, description = fallback, ""
    match = re.match(r"^\ufeff?---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if match:
        for line in match.group(1).splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip().strip('"').strip("'")
                if key == "name" and value:
                    name = value[:120]
                elif key in ("description", "summary") and value:
                    description = value[:300]
    if not description:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for line in lines:
            if line and not line.startswith(("#", "---", "name:", "description:")):
                description = line[:300]
                break
    return name, description


def _build_index() -> Dict[str, Any]:
    entries: List[Dict[str, str]] = []
    counts: Dict[str, int] = {}
    for meta in REPOS:
        root = VENDOR_DIR / meta["dir"]
        if not root.is_dir():
            counts[meta["id"]] = 0
            continue
        repo_count = 0
        for path in root.rglob("SKILL.md"):
            if not path.is_file() or any(p in SKIP_DIRS for p in path.parts):
                continue
            if len(entries) >= MAX_INDEX_ENTRIES:
                break
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:8000]
                rel = _safe_relative(path, root)
                name, description = _frontmatter(text, path.parent.name)
                entries.append({
                    "id": f"{meta['id']}:{rel}",
                    "repo": meta["id"],
                    "name": name,
                    "description": description,
                    "path": rel,
                })
                repo_count += 1
            except Exception:
                continue
        counts[meta["id"]] = repo_count
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": INDEX_VERSION,
        "built_at": time.time(),
        "counts": counts,
        "entries": entries,
    }
    INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def _fingerprint() -> str:
    parts = [INDEX_VERSION]
    for meta in REPOS:
        path = VENDOR_DIR / meta["dir"]
        parts.append(f"{meta['id']}:{_commit(path) if path.is_dir() else 'missing'}")
    return hashlib.sha1("|".join(parts).encode()).hexdigest()


def get_index(refresh: bool = False) -> Dict[str, Any]:
    global _CACHE
    with _LOCK:
        fingerprint = _fingerprint()
        if _CACHE is not None and _CACHE.get("fingerprint") == fingerprint and not refresh:
            return _CACHE
        cached: Optional[Dict[str, Any]] = None
        if INDEX_PATH.is_file() and not refresh:
            try:
                cached = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            except Exception:
                cached = None
        if cached and cached.get("version") == INDEX_VERSION and cached.get("entries"):
            payload = cached
        else:
            payload = _build_index()
        payload["fingerprint"] = fingerprint
        _CACHE = payload
        return payload


def ensure_index() -> None:
    """Warm the index at startup; failures are non-fatal."""
    try:
        get_index()
    except Exception:
        pass


def list_repos() -> List[Dict[str, Any]]:
    index = get_index()
    counts = index.get("counts", {})
    out = []
    for meta in REPOS:
        item = dict(meta)
        item["checked_out"] = (VENDOR_DIR / meta["dir"]).is_dir()
        item["skills"] = int(counts.get(meta["id"], 0))
        out.append(item)
    return out


def repo_info(repo_id: str) -> Dict[str, Any]:
    meta = _BY_ID.get(str(repo_id or ""))
    if not meta:
        raise VendorError(f"unknown repo: {repo_id}")
    root = VENDOR_DIR / meta["dir"]
    info = dict(meta)
    info["path"] = str(root)
    info["checked_out"] = root.is_dir()
    info["commit"] = _commit(root) if root.is_dir() else "missing"
    info["skills"] = int(get_index().get("counts", {}).get(meta["id"], 0))
    return info


def _score(text: str, tokens: List[str]) -> int:
    lower = text.lower()
    return sum(1 for token in tokens if token and token in lower)


def search(query: str, repo_id: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    tokens = [t for t in re.findall(r"[a-z0-9_+-]{2,}", str(query or "").lower())]
    if not tokens:
        raise VendorError("search query is empty")
    entries = get_index().get("entries", [])
    if repo_id:
        _repo_path(repo_id)
        entries = [e for e in entries if e["repo"] == repo_id]
    ranked = []
    for entry in entries:
        score = _score(entry.get("name", "") + " " + entry.get("description", "")
                       + " " + entry.get("path", ""), tokens)
        if score:
            ranked.append((score, entry))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [e for _, e in ranked[:min(int(limit or 10), MAX_SEARCH_RESULTS)]]


def read_skill(skill_id: str) -> Dict[str, Any]:
    target = str(skill_id or "")
    for entry in get_index().get("entries", []):
        if entry["id"] == target:
            root = _repo_path(entry["repo"])
            path = root / entry["path"]
            if not path.is_file():
                raise VendorError("skill file is missing")
            text = path.read_text(encoding="utf-8", errors="ignore")[:MAX_READ_CHARS]
            return {"id": target, "repo": entry["repo"], "name": entry["name"],
                    "description": entry["description"], "path": entry["path"],
                    "content": text, "truncated": len(text) >= MAX_READ_CHARS}
    raise VendorError(f"skill not found in index: {target}")


def list_files(repo_id: str, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
    root = _repo_path(repo_id)
    base = root / _safe_relative(root / str(prefix or ""), root) if prefix else root
    if not base.is_dir():
        raise VendorError("prefix is not a directory")
    out: List[Dict[str, Any]] = []
    for path in sorted(base.iterdir(), key=lambda p: p.name):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = _safe_relative(path, root)
        out.append({"path": rel, "type": "dir" if path.is_dir() else "file",
                    "size": path.stat().st_size if path.is_file() else 0})
        if len(out) >= min(int(limit or 100), 300):
            break
    return out


def read_file(repo_id: str, rel_path: str) -> Dict[str, Any]:
    root = _repo_path(repo_id)
    path = root / _safe_relative(root / str(rel_path or ""), root)
    if not path.is_file():
        raise VendorError("file not found")
    if path.suffix.lower() not in _TEXT_EXT:
        raise VendorError("binary files are not readable through this tool")
    text = path.read_text(encoding="utf-8", errors="ignore")[:MAX_READ_CHARS]
    return {"repo": repo_id, "path": _safe_relative(path, root), "content": text,
            "truncated": len(text) >= MAX_READ_CHARS}


def repo_search(repo_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    root = _repo_path(repo_id)
    needle = str(query or "").strip().lower()
    if not needle:
        raise VendorError("search query is empty")
    hits: List[Dict[str, Any]] = []
    scanned = 0
    for path in root.rglob("*"):
        if scanned >= 600 or len(hits) >= min(int(limit or 20), MAX_SEARCH_RESULTS):
            break
        if not path.is_file() or path.suffix.lower() not in _TEXT_EXT:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        scanned += 1
        try:
            for number, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines()[:400], 1
            ):
                if needle in line.lower():
                    hits.append({"path": _safe_relative(path, root), "line": number,
                                 "text": line.strip()[:240]})
                    break
        except Exception:
            continue
    return hits


def plugin_tools() -> List[Dict[str, str]]:
    """Describe the vendor plugin catalog for MCP and agent prompts."""
    out: List[Dict[str, str]] = []
    for meta in REPOS:
        pid = "vendor_" + meta["id"].replace("-", "_")
        out.append({
            "id": pid,
            "name": meta["name"],
            "category": meta["category"],
            "tools": ", ".join([
                f"{pid}.info", f"{pid}.skills", f"{pid}.skill_read",
                f"{pid}.search", f"{pid}.list", f"{pid}.read",
            ]),
        })
    return out
