from tools.base import Tool
from pathlib import Path
import re
import os
from typing import List, Dict, Any, Optional
import logging

log = logging.getLogger("diff_patch_tool")


class DiffPatchTool(Tool):
    """
    Advanced tool for applying precise patches to files using unified diff format.
    Essential for professional software engineering agents.
    """
    name = "DiffPatchTool"
    description = "Applies a unified diff patch to a file. Use this for surgical code changes."
    example = {"file_path": "main.py", "patch_text": "@@ -1,3 +1,3 @@\n-old_line\n+new_line"}

    def __init__(self):
        super().__init__()

    async def run(self, file_path: str, patch_text: str) -> str:
        """Applies a unified diff patch to a file."""
        base_path = Path(__file__).resolve().parents[3]
        target_file = (base_path / file_path).resolve()

        if not str(target_file).startswith(str(base_path)):
            return "Error: Access denied. Target must be within the workspace."

        if not target_file.exists():
            return f"Error: File not found: {file_path}"

        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()

            new_lines = self._apply_unified_diff(original_lines, patch_text.splitlines(keepends=True))

            if new_lines is None:
                return "Error: Patch failed. The hunk context does not match the file content."

            with open(target_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            return f"Success: Patch applied to '{file_path}'."
        except Exception as e:
            log.error(f"Patch error on {file_path}: {e}")
            return f"Error: {str(e)}"

    def _apply_unified_diff(self, original: List[str], patch_lines: List[str]) -> Optional[List[str]]:
        """Simplified Unified Diff application logic."""
        result = list(original)
        i = 0
        while i < len(patch_lines):
            line = patch_lines[i]
            if line.startswith('@@'):
                match = re.search(r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@', line)
                if not match:
                    return None
                
                old_start = int(match.group(1))
                old_len = int(match.group(2)) if match.group(2) else 1
                idx = old_start - 1
                
                i += 1
                hunk = []
                while i < len(patch_lines) and not patch_lines[i].startswith('@@'):
                    h_line = patch_lines[i]
                    if h_line.startswith(' ') or h_line.startswith('+'):
                        hunk.append(h_line[1:])
                    elif h_line.startswith('-'):
                        pass
                    i += 1
                
                result[idx:idx + old_len] = hunk
            else:
                i += 1
        return result
