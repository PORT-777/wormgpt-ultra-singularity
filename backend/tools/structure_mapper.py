from tools.base import Tool
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

log = logging.getLogger("structure_mapper")


class StructureMapper(Tool):
    """
    Generates a visual tree-like structure of the workspace.
    Helps the engineer understand the project architecture at a glance.
    """
    name = "StructureMapper"
    description = "Generates a tree-like structure of the workspace directory. Useful for understanding project layout."
    example = {"directory": ".", "max_depth": 3}

    def __init__(self):
        super().__init__()

    async def run(self, directory: str = ".", max_depth: int = 3, ignore_dirs: Optional[List[str]] = None) -> str:
        """
        Generates a tree view of the directory.
        """
        if ignore_dirs is None:
            ignore_dirs = [".git", "__pycache__", ".venv", "node_modules", "dist", "build", ".pytest_cache"]

        base_path = Path(__file__).resolve().parents[3]
        target_path = (base_path / directory).resolve()

        if not str(target_path).startswith(str(base_path)):
            return "Error: Access denied. Directory must be within the project."

        if not target_path.exists() or not target_path.is_dir():
            return f"Error: Directory not found: {directory}"

        lines = []
        self._build_tree(target_path, "", 0, max_depth, ignore_dirs, lines, base_path)

        if not lines:
            return f"Directory is empty or only contains ignored items: {directory}"

        return "\n".join(lines)

    def _build_tree(self, path: Path, prefix: str, depth: int, max_depth: int, ignore_dirs: List[str], lines: List[str], base_path: Path):
        if depth > max_depth:
            return

        try:
            items = sorted(list(path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
        except Exception:
            return

        count = len(items)
        for i, item in enumerate(items):
            is_last = (i == count - 1)
            connector = "└── " if is_last else "├── "

            if item.name in ignore_dirs:
                continue

            if item.is_dir():
                lines.append(f"{prefix}{connector}{item.name}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._build_tree(item, new_prefix, depth + 1, max_depth, ignore_dirs, lines, base_path)
            else:
                lines.append(f"{prefix}{connector}{item.name}")