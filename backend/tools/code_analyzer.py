"""
Tool :: CodeAnalyzer

Static analysis of imports and dependencies for local Python projects.
Produces a dependency graph, flags unresolved imports, and identifies
entry points — useful for the Engineer Mode's "Analyze" phase.

Purely local, no network, no external API keys.
"""
from __future__ import annotations

import ast
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .base import Tool


class CodeAnalyzer(Tool):
    name = "CodeAnalyzer"
    description = (
        "Statically analyze a Python project: parse imports, build a "
        "dependency graph, detect unresolved/missing imports, and find "
        "entry points. Input: { path: '<project dir>' }."
    )
    example = {"path": "."}

    def __init__(self):
        super().__init__()

    # ------------------------------------------------------------------ #
    #  Entry point
    # ------------------------------------------------------------------ #
    async def run(
        self,
        path: str = ".",
        include_stdlib: bool = False,
        max_files: int = 200,
        **_: Any,
    ) -> str:
        root = Path(path).resolve()
        if not root.exists() or not root.is_dir():
            return f"ERROR: not a directory: {path}"

        py_files: List[Path] = []
        for p in root.rglob("*.py"):
            # skip common noise
            parts = set(p.relative_to(root).parts)
            if parts & {"__pycache__", ".git", ".venv", "venv", "env", "node_modules"}:
                continue
            py_files.append(p)
            if len(py_files) >= max_files:
                break

        if not py_files:
            return "No Python files found."

        # Parse each file
        file_imports: Dict[str, List[str]] = {}      # file -> list of imported modules
        all_imports: Set[str] = set()                  # all imported module names
        unresolved: Dict[str, List[str]] = {}          # file -> [unresolved imports]

        for f in py_files:
            try:
                src = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            try:
                tree = ast.parse(src, filename=str(f))
            except SyntaxError:
                continue

            imps = self._extract_imports(tree)
            rel = str(f.relative_to(root))
            file_imports[rel] = imps
            all_imports.update(imps)

        # Resolve imports: is it local (within project) or external?
        local_modules = self._local_module_names(root, py_files)
        external = sorted(m for m in all_imports if m not in local_modules)

        if not include_stdlib:
            external = [m for m in external if not self._is_stdlib(m)]

        # Build dependency graph (local file -> local files it imports)
        dep_graph: Dict[str, List[str]] = {}
        for rel, imps in file_imports.items():
            deps: List[str] = []
            for imp in imps:
                target = self._resolve_local(imp, root, rel, local_modules)
                if target:
                    deps.append(target)
            dep_graph[rel] = deps

        # Find entry points (files not imported by anyone)
        imported_by_others: Set[str] = set()
        for deps in dep_graph.values():
            imported_by_others.update(deps)
        entry_points = [f for f in dep_graph if f not in imported_by_others]

        # Build report
        lines: List[str] = [
            f"📊 CodeAnalyzer — Project: {root.name}",
            f"📁 Python files analyzed: {len(py_files)}",
            f"📦 External dependencies: {len(external)}",
            f"🔗 Local dependency edges: {sum(len(v) for v in dep_graph.values())}",
            f"🚪 Entry points (not imported): {len(entry_points)}",
            "",
            "=== EXTERNAL DEPENDENCIES ===",
        ]
        for m in external:
            lines.append(f"  - {m}")

        lines.append("")
        lines.append("=== LOCAL DEPENDENCY GRAPH ===")
        for rel in sorted(dep_graph):
            deps = dep_graph[rel]
            lines.append(f"  {rel} -> {', '.join(deps) if deps else '(none)'}")

        lines.append("")
        lines.append("=== ENTRY POINTS ===")
        for ep in sorted(entry_points):
            lines.append(f"  - {ep}")

        # Unresolved local imports (imports that look local but don't resolve)
        lines.append("")
        lines.append("=== UNRESOLVED / MISSING ===")
        found_any = False
        for rel, imps in file_imports.items():
            missing = [i for i in imps if not self._resolve_local(i, root, rel, local_modules)
                       and i not in external and not self._is_stdlib(i)]
            if missing:
                found_any = True
                lines.append(f"  {rel}: {', '.join(missing)}")
        if not found_any:
            lines.append("  (none)")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_imports(tree: ast.AST) -> List[str]:
        """Extract top-level module names imported by an AST."""
        mods: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mods.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mods.append(node.module.split(".")[0])
        return mods

    @staticmethod
    def _local_module_names(root: Path, files: List[Path]) -> Set[str]:
        """Set of importable local module names (file stems + package names)."""
        names: Set[str] = set()
        for f in files:
            rel = f.relative_to(root)
            parts = rel.with_suffix("").parts
            # module path without .py
            mod = ".".join(parts)
            names.add(mod)
            # also the top-level package
            names.add(parts[0])
            if parts[-1] == "__init__":
                names.add(".".join(parts[:-1]))
        return names

    @staticmethod
    def _is_stdlib(module: str) -> bool:
        """Cheap stdlib check: is it a built-in module name?"""
        try:
            return importlib.util.find_spec(module) is not None and \
                (importlib.util.find_spec(module).origin is None or
                 "site-packages" not in str(importlib.util.find_spec(module).origin))
        except Exception:
            return module in sys.builtin_module_names

    @staticmethod
    def _resolve_local(
        imp: str, root: Path, current_rel: str, local_modules: Set[str],
    ) -> Optional[str]:
        """Try to resolve an import to a local file path relative to root."""
        candidates = [
            root / (imp.replace(".", "/") + ".py"),
            root / (imp.replace(".", "/") + "/__init__.py"),
        ]
        # relative to current file's directory
        cur_dir = root / Path(current_rel).parent
        candidates += [
            cur_dir / (imp + ".py"),
            cur_dir / imp / "__init__.py",
        ]
        for c in candidates:
            try:
                if c.exists() and c.is_file():
                    return str(c.relative_to(root))
            except ValueError:
                continue
        return None


__all__ = ["CodeAnalyzer"]
