"""
Tool :: IntegrityGuard (hardening suite)

Tamper-integrity checking for the user's OWN files and builds:

  checksum          -> SHA-256 + CRC32 + size fingerprint of one file
  create_baseline   -> hashes every file under a directory into a
                       JSON manifest (per-file SHA-256 + 4KB block
                       hashes so changes can be LOCATED later)
  verify_baseline   -> re-hash and report CHANGED / ADDED / MISSING
                       files; each changed file reports the first
                       divergent block offset in hex (tamper triage)

Read-only by design: the tool never modifies the checked targets.
Manifests are written into the workspace sandbox, never next to the
target. Host-scope paths need Full Access Mode like every other tool.
"""
from __future__ import annotations

import hashlib
import json
import zlib
from pathlib import Path
from typing import Any, Dict

import configs as config
from .base import Tool

BLOCK = 4096                 # bytes per tracked block hash
MAX_FILES = 2000             # bounded baseline walk
SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__",
             "site-packages", "chroma", "memory_data", "extracted"}


class IntegrityGuard(Tool):
    name = "IntegrityGuard"
    description = (
        "Integrity / tamper checks on the user's OWN binaries and builds "
        "(read-only): {'action': 'checksum'|'create_baseline'|"
        "'verify_baseline', 'path', 'manifest' (default integrity.json)}. "
        "Reports SHA-256 fingerprints and, on verify, the first divergent "
        "byte-block offset (hex) for every changed file."
    )
    example = {"action": "verify_baseline", "path": "build",
               "manifest": "integrity.json"}

    async def run(self, action: str = "", **kw: Any) -> str:
        try:
            handler = {
                "checksum": self._checksum,
                "create_baseline": self._create,
                "verify_baseline": self._verify,
            }.get(str(action).lower().strip())
            if handler is None:
                return ("ERROR: unknown action (checksum | create_baseline "
                        "| verify_baseline)")
            return await handler(kw)
        except PermissionError as exc:
            return f"ERROR: {exc}"
        except Exception as exc:      # hyper-persistence: observable
            return f"ERROR: integrity {action}: {exc}"

    # ------------------------------------------------------------------ #
    def _resolve(self, kw) -> Path:
        path = str(kw.get("path", "."))
        if str(kw.get("scope", "workspace")).lower() == "host":
            return self.resolve_any(path)
        return self.safe_path(path)

    @staticmethod
    def _hash_file(path: Path) -> Dict:
        size = path.stat().st_size
        sha = hashlib.sha256()
        blocks: list = []
        with open(path, "rb") as fh:
            while True:
                data = fh.read(BLOCK)
                if not data:
                    break
                sha.update(data)
                blocks.append(hashlib.sha256(data).hexdigest()[:16])
        return {"size": size,
                "sha256": sha.hexdigest(),
                "blocks": blocks}

    @staticmethod
    def _walk(root: Path) -> Dict[str, Dict]:
        manifest: Dict[str, Dict] = {}
        count = 0

        def walk(p: Path):
            nonlocal count
            if count >= MAX_FILES:
                return
            if p.is_file():
                count += 1
                manifest[str(p.relative_to(root)).replace("\\", "/")] = \
                    IntegrityGuard._hash_file(p)
                return
            if p.is_dir():
                for child in sorted(p.iterdir()):
                    if child.is_dir():
                        if child.name not in SKIP_DIRS:
                            walk(child)
                    else:
                        walk(child)

        walk(root)
        return manifest

    # ------------------------------------------------------------------ #
    async def _checksum(self, kw) -> str:
        target = self._resolve(kw)
        if not target.is_file():
            return f"ERROR: no such file: {kw.get('path')}"
        raw = target.read_bytes()
        return (f"FILE: {kw.get('path')}\n"
                f"size: {len(raw)} bytes\n"
                f"sha256: {hashlib.sha256(raw).hexdigest()}\n"
                f"crc32: 0x{zlib.crc32(raw) & 0xFFFFFFFF:08X}")
    # note: sha256 = cryptographic integrity; crc32 = quick diff fingerprint

    async def _create(self, kw) -> str:
        root = self._resolve(kw)
        if not root.is_dir():
            return f"ERROR: no such directory: {kw.get('path')}"
        manifest_name = str(kw.get("manifest", "integrity.json"))
        manifest = self._walk(root)
        dest = self.safe_path(f"integrity/{manifest_name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps({
            "target": str(root),
            "created": manifest_name,
            "files": manifest}, indent=1), encoding="utf-8")
        return (f"OK: baseline created for {len(manifest)} files -> "
                f"integrity/{manifest_name} (sha256 + {BLOCK}B block "
                "hashes — verify_baseline reports first divergent offsets)")

    async def _verify(self, kw) -> str:
        root = self._resolve(kw)
        if not root.is_dir():
            return f"ERROR: no such directory: {kw.get('path')}"
        manifest_name = str(kw.get("manifest", "integrity.json"))
        manifest_path = self.safe_path(f"integrity/{manifest_name}")
        if not manifest_path.is_file():
            return ("ERROR: baseline not found — run create_baseline "
                    "first (manifest: integrity/" + manifest_name + ")")
        stored = json.loads(manifest_path.read_text(encoding="utf-8")) \
            .get("files", {})

        changed, added, missing, ok = [], [], [], 0
        current = self._walk(root)
        for rel, old in stored.items():
            now = current.get(rel)
            if now is None:
                missing.append(rel)
            elif now["sha256"] != old["sha256"]:
                delta = None
                for i, (a, b) in enumerate(zip(old["blocks"], now["blocks"])):
                    if a != b:
                        delta = i * BLOCK
                        break
                if delta is None and len(now["blocks"]) != len(old["blocks"]):
                    delta = min(len(old["blocks"]),
                                len(now["blocks"])) * BLOCK
                changed.append(f"{rel}  ({old['size']}B-> {now['size']}B"
                               + (f"; first divergent block @ 0x{delta:X}"
                                  if delta is not None else "") + ")")
            else:
                ok += 1
        added = [r for r in current if r not in stored]

        verdict = ("CLEAN — no tampering detected" if not (changed or
                   added or missing)
                   else f"TAMPERED: {len(changed)} changed, "
                        f"{len(added)} added, {len(missing)} missing")
        lines = [f"INTEGRITY VERIFY: {kw.get('path')}", verdict]
        lines += [f"  CHANGED: {c}" for c in changed]
        lines += [f"  ADDED:   {a}" for a in added]
        lines += [f"  MISSING: {m}" for m in missing]
        lines.append(f"  ({ok} files unchanged)")
        return "\n".join(lines)
