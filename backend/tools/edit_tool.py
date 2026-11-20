from tools.base import Tool
from pathlib import Path
import logging
from typing import Optional

log = logging.getLogger("edit_tool")


class SmartEdit(Tool):
    """
    Performs targeted text replacement within a file.
    Essential for engineers to apply patches and fixes without overwriting entire files.
    """
    name = "SmartEdit"
    description = "Replaces a specific string with a new string in a file. Supports replacing all occurrences."
    example = {"path": "config.py", "old_string": "DEBUG = True", "new_string": "DEBUG = False", "replace_all": True}

    def __init__(self):
        super().__init__()

    async def run(self, path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
        """
        Executes a surgical text replacement.
        """
        base_path = Path(__file__).resolve().parents[3]
        target_file = (base_path / path).resolve()

        if not str(target_file).startswith(str(base_path)):
            return "Error: Access denied. Target file must be within the project directory."

        if not target_file.exists():
            return f"Error: File not found: {path}"

        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if old_string not in content:
                return f"Error: The text to replace ('{old_string}') was not found in the file."

            if replace_all:
                new_content = content.replace(old_string, new_string)
                count = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                count = 1

            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return f"Success: Replaced {count} occurrence(s) of '{old_string}' in '{path}'."

        except Exception as e:
            log.error(f"Failed to edit file {path}: {e}")
            return f"Error: {str(e)}"