from tools.base import Tool
from typing import Any, Dict, List, Optional
import re
import os
from pathlib import Path
import logging

log = logging.getLogger("grep_tool")


class GrepSearch(Tool):
    """
    Searches for a regex pattern within files in a directory.
    Crucial for engineers to find specific code patterns, TODOs, or API endpoints.
    """
    name = "GrepSearch"
    description = "Search for a regex pattern within files in a directory. Returns file, line, and content."
    example = {"pattern": "import os", "directory": ".", "max_files": 50}

    def __init__(self):
        super().__init__()

    async def run(self, pattern: str, directory: str = ".", max_files: int = 100, ignore_dirs: Optional[List[str]] = None) -> str:
        """
        Performs a regex search across the filesystem.
        """
        if ignore_dirs is None:
            ignore_dirs = [".git", "__pycache__", ".venv", "node_modules", "dist", "build", ".pytest_cache"]

        results = []
        base_path = Path(__file__).resolve().parents[3]
        search_path = (base_path / directory).resolve()

        if not str(search_path).startswith(str(base_path)):
            return "Error: Access denied. Search path must be within the project directory."

        if not search_path.exists() or not search_path.is_dir():
            return f"Error: Directory not found: {directory}"

        try:
            regex = re.compile(pattern)
            for root, dirs, files in os.walk(search_path):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]

                for file in files:
                    file_path = Path(root) / file

                    if file_path.suffix.lower() in ['.exe', '.pyc', '.bin', '.png', '.jpg', '.pdf', '.zip', '.pyo', '.dll', '.so']:
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                if regex.search(line):
                                    results.append({
                                        "file": str(file_path.relative_to(base_path)),
                                        "line": line_num,
                                        "content": line.strip()
                                    })
                                    if len(results) >= max_files:
                                        break
                    except Exception as e:
                        log.debug(f"Could not read file {file_path}: {e}")
                        continue

                if len(results) >= max_files:
                    break

            if not results:
                return f"No matches found for pattern: '{pattern}' in {directory}"

            return "\n".join([f"{r['file']}:{r['line']} -> {r['content']}" for r in results])

        except re.error as e:
            return f"Error: Invalid regex pattern: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"