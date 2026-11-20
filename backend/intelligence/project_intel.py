"""Project structure discovery and AST-based code intelligence."""
from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "dist", "build", "__pycache__",
    ".pytest_tmp", ".mypy_cache", ".ruff_cache", "vendor", "data", "memory_data",
}

LANG_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".java": "Java", ".cs": "C#", ".cpp": "C++", ".cc": "C++",
    ".c": "C", ".h": "C/C++", ".rs": "Rust", ".go": "Go", ".rb": "Ruby",
    ".php": "PHP", ".sh": "Shell", ".ps1": "PowerShell", ".html": "HTML",
    ".css": "CSS", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML", ".md": "Markdown", ".sql": "SQL",
}

INCOMPLETE_MARKERS = ("TODO", "FIXME", "NotImplementedError", "XXX", "HACK", "pass  #")


def _safe_root(root: str | Path) -> Path:
    p = Path(root).expanduser().resolve()
    if not p.is_dir():
        raise ValueError(f"not a directory: {p}")
    return p


def _files(root: Path, limit: int = 4000) -> List[Path]:
    out: List[Path] = []
    for path in root.rglob("*"):
        if len(out) >= limit:
            break
        if not path.is_file():
            continue
        # Skip ignored dirs relative to the scanned root only — an ancestor
        # directory with a matching name must not blank the whole scan.
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        out.append(path)
    return out


def _read(path: Path, limit: int = 400_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def _frameworks(root: Path) -> List[str]:
    found: set[str] = set()
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            for key in ("react", "vite", "next", "vue", "angular", "tailwindcss", "express"):
                if key in deps:
                    found.add(key)
        except Exception:
            pass
    req = root / "requirements.txt"
    if req.is_file():
        text = _read(req).lower()
        for key in ("fastapi", "django", "flask", "uvicorn", "pytest", "sqlalchemy"):
            if key in text:
                found.add(key)
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = _read(pyproject).lower()
        for key in ("poetry", "setuptools", "pytest", "ruff"):
            if key in text:
                found.add(key)
    return sorted(found)


def _entry_points(root: Path, files: List[Path]) -> List[str]:
    out: List[str] = []
    for name in ("main.py", "app.py", "index.js", "index.ts", "server.py", "Main.java", "Program.cs", "main.go", "src/main.rs"):
        candidate = root / name
        if candidate.is_file():
            out.append(str(candidate.relative_to(root)))
    for file in files:
        if file.name == "package.json":
            try:
                data = json.loads(_read(file))
                main = data.get("main")
                if main:
                    out.append(f"{file.relative_to(root)}:main={main}")
                for k, v in (data.get("scripts") or {}).items():
                    if k in ("start", "dev", "build"):
                        out.append(f"{file.relative_to(root)}:script.{k}={v}")
            except Exception:
                pass
        if file.name in ("pyproject.toml", "setup.py"):
            text = _read(file)
            if "[project.scripts]" in text or "entry_points" in text:
                out.append(f"{file.relative_to(root)}:entry-points")
    return sorted(set(out))[:40]


def _python_symbols(path: Path, source: str) -> Tuple[List[Dict[str, Any]], List[str], List[Dict[str, Any]]]:
    symbols: List[Dict[str, Any]] = []
    imports: List[str] = []
    calls: List[Dict[str, Any]] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return symbols, imports, [{"error": str(exc)}]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append({"kind": "function", "name": node.name, "line": node.lineno,
                            "end_line": getattr(node, "end_lineno", node.lineno),
                            "args": [a.arg for a in node.args.args],
                            "doc": bool(ast.get_docstring(node))})
        elif isinstance(node, ast.ClassDef):
            symbols.append({"kind": "class", "name": node.name, "line": node.lineno,
                            "end_line": getattr(node, "end_lineno", node.lineno),
                            "bases": [ast.unparse(b) for b in node.bases]})
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
        elif isinstance(node, ast.Call):
            target = node.func
            name = getattr(target, "id", None) or getattr(target, "attr", None)
            if name:
                calls.append({"name": name, "line": node.lineno})
    return symbols, sorted(set(imports)), calls


def _js_symbols(source: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for match in re.finditer(r"(?:async\s+)?function\s+([A-Za-z_$][\w$]*|\w+)\s*\(", source):
        out.append({"kind": "function", "name": match.group(1), "line": source[:match.start()].count("\n") + 1})
    for match in re.finditer(r"class\s+([A-Za-z_$][\w$]*)", source):
        out.append({"kind": "class", "name": match.group(1), "line": source[:match.start()].count("\n") + 1})
    return out


def scan_project(root: str, limit: int = 4000) -> Dict[str, Any]:
    base = _safe_root(root)
    files = _files(base, limit)
    languages: Dict[str, int] = defaultdict(int)
    symbols: List[Dict[str, Any]] = []
    import_graph: Dict[str, List[str]] = {}
    call_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    incomplete: List[Dict[str, Any]] = []
    security: List[Dict[str, Any]] = []
    sizes = 0

    for file in files:
        ext = file.suffix.lower()
        if ext in LANG_BY_EXT:
            languages[LANG_BY_EXT[ext]] += 1
        try:
            sizes += file.stat().st_size
        except Exception:
            pass
        source = _read(file)
        if ext == ".py":
            syms, imps, calls = _python_symbols(file, source)
            rel = str(file.relative_to(base))
            import_graph[rel] = imps
            for s in syms:
                s["file"] = rel
                symbols.append(s)
            for c in calls:
                if "name" in c:
                    call_index[c["name"]].append({"file": rel, "line": c.get("line", 0)})
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            for s in _js_symbols(source):
                s["file"] = str(file.relative_to(base))
                symbols.append(s)
        for i, line in enumerate(source.splitlines(), 1):
            for marker in INCOMPLETE_MARKERS:
                if marker in line:
                    incomplete.append({"file": str(file.relative_to(base)), "line": i, "marker": marker})
                    break
            if ext == ".py" and re.search(r"\beval\s*\(|\bexec\s*\(|shell\s*=\s*True", line):
                security.append({"file": str(file.relative_to(base)), "line": i, "issue": "dynamic execution"})

    # build/test systems
    systems = []
    for name in ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini", "package.json", "Makefile", "CMakeLists.txt", "Cargo.toml"):
        if (base / name).is_file():
            systems.append(name)

    return {
        "root": str(base),
        "file_count": len(files),
        "total_bytes": sizes,
        "languages": dict(sorted(languages.items(), key=lambda kv: -kv[1])),
        "frameworks": _frameworks(base),
        "entry_points": _entry_points(base, files),
        "build_test_systems": systems,
        "symbols": symbols[:4000],
        "symbol_count": len(symbols),
        "import_graph": import_graph,
        "call_index": {k: v[:40] for k, v in list(call_index.items())[:1000]},
        "incomplete": incomplete[:200],
        "security_hints": security[:200],
        "truncated": len(files) >= limit,
    }


def find_symbol(root: str, query: str, limit: int = 40) -> List[Dict[str, Any]]:
    data = scan_project(root)
    q = query.lower()
    return [s for s in data["symbols"] if q in s.get("name", "").lower()][:limit]


def call_hierarchy(root: str, symbol: str, limit: int = 60) -> Dict[str, Any]:
    data = scan_project(root)
    callers = data["call_index"].get(symbol, [])
    return {"symbol": symbol, "callers": callers[:limit], "note": "AST call sites; dynamic dispatch not resolved"}


def code_quality(root: str) -> Dict[str, Any]:
    data = scan_project(root)
    long_functions = [s for s in data["symbols"] if s.get("kind") == "function" and (s.get("end_line", 0) - s.get("line", 0)) > 80]
    undocumented = [s for s in data["symbols"] if s.get("kind") == "function" and not s.get("doc")]
    # duplicate Python functions by normalized name+arg signature
    seen: Dict[Tuple[str, tuple], List[str]] = defaultdict(list)
    for s in data["symbols"]:
        if s.get("kind") == "function":
            seen[(s["name"], tuple(s.get("args", [])))].append(s.get("file", ""))
    duplicates = [{"name": k[0], "files": v} for k, v in seen.items() if len(v) > 1]
    # circular imports among project files
    graph = {k: [v.split(".")[-1] for v in vals] for k, vals in data["import_graph"].items()}
    cycles: List[List[str]] = []
    for start in list(graph)[:400]:
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            for nxt in graph.get(node, []):
                target = next((k for k in graph if k.endswith(nxt + ".py") or k == nxt + ".py"), None)
                if not target:
                    continue
                if target == start and len(path) > 1:
                    cycles.append(path + [target])
                elif target not in path and len(path) < 8:
                    stack.append((target, path + [target]))
    return {
        "long_functions": long_functions[:100],
        "undocumented_count": len(undocumented),
        "duplicates": duplicates[:100],
        "circular_imports": cycles[:50],
        "security_hints": data["security_hints"],
        "incomplete_count": len(data["incomplete"]),
    }
