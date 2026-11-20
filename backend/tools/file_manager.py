"""
Tool :: UniversalFileManager (FileSystemMaster lineage)

Full-spectrum filesystem tool. Two scopes:

  workspace (default)  -> sandboxed to WORKSPACE_DIR, always allowed
  host                 -> ANY path on the machine; requires Full Access
                          Mode (explicit UI toggle); OS-critical zones
                          are denylisted in tools/base.resolve_any()

Actions
-------
  list / read / write / append / copy / move / delete / info / download
  search   : regex/substring hunt across text files (with line numbers)
  extract  : unzip/untar archives into workspace (zip-slip guarded;
             .rar needs an external tool -> clear message)
  hex      : hexdump any file slice (addr | hex bytes | ascii) for
             binary/data inspection without crashing on size
`read` chunking + `download` streaming handle arbitrarily large files.
"""
from __future__ import annotations

import fnmatch
import re
import shutil
import tarfile
import zipfile
from typing import Any

import configs as config
from .base import Tool

WORKSPACE_EMPTY = "[workspace is empty]"
SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__",
             "site-packages", "chroma", "memory_data"}
ARCHIVE_SUFFIXES = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2",
                    ".tar.xz", ".tbz2", ".txz")


class UniversalFileManager(Tool):
    name = "UniversalFileManager"
    description = (
        "Files anywhere on the machine (scope='host' needs Full Access "
        "Mode; default scope='workspace' is sandboxed). Handles ALL "
        "formats incl. .cpp/.h/.py/.asm/.bin/.dll/.json: "
        "{'action': 'list'|'read'|'write'|'append'|'copy'|'move'|'delete'|"
        "'info'|'download'|'search'|'extract'|'hex', 'path', 'dest', "
        "'url', 'pattern', 'glob', 'offset', 'length'}"
    )
    example = {"action": "hex", "path": "dump.bin", "offset": 0,
               "length": 256}

    async def run(self, **kw: Any) -> str:
        try:
            action = str(kw.get("action", "list")).lower()
            handler = {
                "list": self._list, "read": self._read, "write": self._write,
                "append": self._append, "copy": self._copy, "move": self._move,
                "delete": self._delete, "info": self._info,
                "download": self._download, "search": self._search,
                "extract": self._extract, "hex": self._hex,
                "aob": self._aob,
            }.get(action)
            if handler is None:
                return (f"ERROR: unknown action '{action}' (list|read|write|"
                        "append|copy|move|delete|info|download|search|"
                        "extract|hex|aob)")
            return await handler(kw)
        except PermissionError as exc:
            return f"ERROR: denied — {exc}"
        except ValueError as exc:
            return f"ERROR: {exc}"
        except FileNotFoundError as exc:
            return f"ERROR: file not found: {exc}"
        except Exception as exc:  # hyper-persistence: always observable
            return f"ERROR: {action} failed: {exc}"

    # ------------------------------------------------------------------ #
    def _resolve(self, kw) -> "Path":
        scope = str(kw.get("scope", "workspace")).lower()
        path = str(kw.get("path", "."))
        return self.resolve_any(path) if scope == "host" else self.safe_path(path)

    # ------------------------------------------------------------------ #
    async def _list(self, kw) -> str:
        root = self._resolve(kw)
        if not root.exists():
            return f"ERROR: no such directory: {kw.get('path')}"
        if root.is_file():
            return f"[file] {root}"

        # bounded walk: depth-limited + heavyweight dirs skipped so a
        # host-scope listing of the whole drive returns in seconds.
        SKIP_DIRS = {"node_modules", ".git", "venv", ".venv",
                     "__pycache__", "site-packages", "chroma"}
        max_depth = int(kw.get("depth", 3))
        lines: list = []

        def walk(p, depth):
            if len(lines) >= 500:
                return
            for child in sorted(p.iterdir()):
                rel = child.relative_to(root)
                if child.is_dir():
                    lines.append(f"[dir ] {rel}")
                    if depth < max_depth and \
                            child.name not in SKIP_DIRS:
                        walk(child, depth + 1)
                else:
                    lines.append(f"[file] {rel} {child.stat().st_size}B")

        walk(root, 0)
        return "\n".join(lines[:500]) or "[directory empty]"

    async def _read(self, kw) -> str:
        target = self._resolve(kw)
        if not target.is_file():
            return f"ERROR: no such file: {kw.get('path')}"
        offset = max(int(kw.get("offset", 0)), 0)
        length = int(kw.get("length", config.FS_CHUNK))
        raw = target.read_bytes()
        # binary heuristics: if unusable as utf-8, report hexd-ish info
        text = raw.decode("utf-8", errors="replace")
        hk = str(target).lower()
        if hk.endswith((".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip",
                        ".exe", ".dll", ".mp4")):
            return (f"[binary file {len(raw)} bytes — cannot show as text. "
                    f"Use Screenshot/vision or PythonInterpreter instead.]")
        size_info = f"[file size: {len(raw)} chars | showing "
        chunk = text[offset:offset + length]
        more = len(text) > offset + length
        note = ", more available — raise offset" if more else ""
        header = f"{size_info}offset {offset}..{offset + len(chunk)}{note}]\n"
        return header + chunk

    async def _write(self, kw) -> str:
        target = self._resolve(kw)
        content = str(kw.get("content", ""))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"OK: wrote {len(content)} chars -> {target}"

    async def _append(self, kw) -> str:
        target = self._resolve(kw)
        content = str(kw.get("content", ""))
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(content)
        return f"OK: appended {len(content)} chars -> {target}"

    async def _copy(self, kw) -> str:
        src = self._resolve(kw)
        dst = self.resolve_any(str(kw.get("dest", "."))) \
            if str(kw.get("scope", "workspace")).lower() == "host" \
            else self.safe_path(str(kw.get("dest", ".")))
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            return f"OK: copied directory {src} -> {dst}"
        shutil.copy2(src, dst)
        return f"OK: copied {src} -> {dst}"

    async def _move(self, kw) -> str:
        src = self._resolve(kw)
        dst = self.resolve_any(str(kw.get("dest", "."))) \
            if str(kw.get("scope", "workspace")).lower() == "host" \
            else self.safe_path(str(kw.get("dest", ".")))
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return f"OK: moved {src} -> {dst}"

    async def _delete(self, kw) -> str:
        target = self._resolve(kw)
        if target == config.WORKSPACE_DIR:
            return "ERROR: refusing to delete the workspace root"
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return f"OK: deleted {target}"

    async def _info(self, kw) -> str:
        target = self._resolve(kw)
        st = target.stat()
        kind = "dir" if target.is_dir() else "file"
        return (f"[{kind}] {target.name}\n  size: {st.st_size} bytes\n"
                f"  modified: {st.st_mtime}\n  path: {target}")

    async def _download(self, kw) -> str:
        url = str(kw.get("url", ""))
        if not url:
            return "ERROR: url required for download"
        import httpx  # local import keeps tool import light
        target = self._resolve(kw)
        target.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
            async with c.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(target, "wb") as fh:
                    async for chunk in resp.aiter_bytes(config.DOWNLOAD_CHUNK):
                        fh.write(chunk)
                        total += len(chunk)
        return f"OK: downloaded {total} bytes -> {target}"

    # ================================================================= #
    #  Intelligence-inputs protocol: search / extract / hex
    # ================================================================= #
    async def _search(self, kw) -> str:
        pattern = str(kw.get("pattern", "")).strip()
        if not pattern:
            return "ERROR: pattern required"
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            return f"ERROR: bad regex: {exc}"
        root = self._resolve(kw)
        glob = str(kw.get("glob", "*")).strip() or "*"
        max_depth = int(kw.get("depth", 5))
        max_hits = int(kw.get("max_hits", 40))
        hits: list = []

        def walk(p, depth):
            if len(hits) >= max_hits or depth > max_depth:
                return
            for child in sorted(p.iterdir()):
                if len(hits) >= max_hits:
                    return
                if child.is_dir():
                    if child.name not in SKIP_DIRS:
                        walk(child, depth + 1)
                    continue
                if glob != "*" and not fnmatch.fnmatch(child.name, glob):
                    continue
                try:
                    if child.stat().st_size > 400_000:
                        continue
                    text = child.read_text(encoding="utf-8",
                                           errors="ignore")
                except OSError:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if rx.search(line):
                        hits.append(
                            f"{child.relative_to(root) or child.name}:"
                            f"{i}: {line.strip()[:160]}")
                        break
                    if len(hits) >= max_hits:
                        return

        walk(root, 0)
        return ("\n".join(hits) if hits else
                f"no matches for /{pattern}/ in {root.name}")

    async def _extract(self, kw) -> str:
        arc = self._resolve(kw)
        suffix = str(arc.suffix).lower()
        combined = str(arc.name).lower()
        is_archive = combined.endswith(ARCHIVE_SUFFIXES) or \
            suffix == ".zip" or combined.endswith((".tar.gz", ".tgz",
                                                    ".tar.bz2", ".tar.xz"))
        if not is_archive:
            return (f"ERROR: '{arc.name}' is not a supported archive "
                    "(zip/tar/tar.gz/tar.bz2/tar.xz). For .rar, convert "
                    "to zip first (needs external unrar tooling).")

        dest = config.WORKSPACE_DIR / "extracted" / arc.stem
        dest.mkdir(parents=True, exist_ok=True)

        def _safe_member(name: str) -> bool:
            # zip-slip guard: absolute or traversal paths are rejected
            n = name.replace("\\", "/").lstrip("/")
            parts = [p for p in n.split("/") if p not in ("", ".")]
            if any(p == ".." for p in parts):
                return False
            if re.match(r"^[a-zA-Z]:", n):
                return False
            return True

        written = 0
        if suffix == ".zip":
            with zipfile.ZipFile(arc) as zf:
                for info in zf.infolist():
                    if not _safe_member(info.filename):
                        return (f"ERROR: blocked unsafe archive entry "
                                f"'{info.filename}' (path traversal)")
                zf.extractall(dest)
                written += len(zf.infolist())
        else:
            with tarfile.open(arc, "r:*") as tf:
                for member in tf.getmembers():
                    if not _safe_member(member.name):
                        return (f"ERROR: blocked unsafe tar member "
                                f"'{member.name}' (path traversal)")
                tf.extractall(dest)
                written += len(tf.getmembers())

        return (f"OK: extracted {written} entries from {arc.name} -> "
                f"{dest.relative_to(config.WORKSPACE_DIR)} "
                f"(zip-slip guard: clean)")

    async def _hex(self, kw) -> str:
        """Hexdump slice: addr | 16 hex bytes | ascii — debugger style."""
        target = self._resolve(kw)
        if not target.is_file():
            return f"ERROR: no such file: {kw.get('path')}"
        offset = max(int(kw.get("offset", 0)), 0)
        length = min(int(kw.get("length", 256)), 1024)
        size = target.stat().st_size
        if offset >= size:
            return f"[empty range: file is {size}B, offset {offset}]"
        with open(target, "rb") as fh:
            fh.seek(offset)
            data = fh.read(length)

        lines = [f"[{target.name} | {size}B total | showing "
                 f"0x{offset:X}..0x{offset + len(data):X}]"]
        for base in range(0, len(data), 16):
            chunk = data[base:base + 16]
            hexies = " ".join(f"{b:02X}" for b in chunk)
            pad = " ".ljust(3 * (16 - len(chunk)))
            ascii_col = "".join(
                chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"0x{offset + base:08X}  {hexies}{pad} |{ascii_col}|")
        if size > offset + len(data):
            lines.append("[more bytes available — raise 'offset']")
        return "\n".join(lines)

    async def _aob(self, kw) -> str:
        """AOB (Array of Bytes) pattern scan — find a byte sequence inside
        any binary/file and report every offset (hex). For your own
        files/dlls/exe only; read-only, never modifies the target."""
        target = self._resolve(kw)
        if not target.is_file():
            return f"ERROR: no such file: {kw.get('path')}"
        pattern = str(kw.get("pattern", "")).strip()
        if not pattern:
            return "ERROR: pattern required (e.g. '48 8B 05 ?? ?? ?? ??')"
        # parse hex pattern: '??' = wildcard byte
        pat_bytes, mask = [], []
        for tok in pattern.replace(",", " ").split():
            tok = tok.strip()
            if tok == "??" or tok == "?":
                pat_bytes.append(0); mask.append(0)
            else:
                try:
                    pat_bytes.append(int(tok, 16)); mask.append(1)
                except ValueError:
                    return f"ERROR: bad pattern token '{tok}' (hex or ??)"
        if not pat_bytes:
            return "ERROR: empty pattern"
        size = target.stat().st_size
        max_len = min(int(kw.get("max_len", size)), size)
        max_hits = int(kw.get("max_hits", 40))
        hits: list = []
        with open(target, "rb") as fh:
            data = fh.read(max_len)
        plen = len(pat_bytes)
        i = 0
        while i <= len(data) - plen:
            if all(mask[j] == 0 or data[i + j] == pat_bytes[j]
                   for j in range(plen)):
                hits.append(f"0x{i:08X}")
                i += plen
                if len(hits) >= max_hits:
                    break
            else:
                i += 1
        if not hits:
            return (f"[AOB scan] pattern /{pattern}/ not found in "
                    f"{target.name} ({max_len}B scanned)")
        return (f"[AOB scan] {len(hits)} hit(s) in {target.name}\n"
                + "\n".join(hits))
