"""
Tool :: SystemControl

Desktop control for GUI workflows: open applications, type into them,
take screenshots (that Gemini 1.5 Pro can later analyse thanks to its
vision), and media/volume keys. All blocking pyautogui / os calls run
off the event loop via asyncio.to_thread.

Note: desktop automation means the agent acts on THIS machine's
desktop intentionally and only when the user commands it.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from typing import Any

import configs as config
from .base import Tool

# common apps resolvable without full paths (Windows-first)
APP_MAP = {
    "notepad": ["notepad"],
    "calculator": ["calc"],
    "calc": ["calc"],
    "chrome": ["cmd", "/c", "start", "", "chrome"],
    "explorer": ["explorer"],
    "cmd": ["cmd", "/c", "start"],
    "file explorer": ["explorer"],
}


class SystemControl(Tool):
    name = "SystemControl"
    description = (
        "Control the local desktop: {'action': 'open_app'|'screenshot'|"
        "'type_text'|'press_key', 'app': ..., 'text': ..., 'key': ...}. "
        "open_app lets you launch programs (notepad, chrome, explorer...)."
    )
    example = {"action": "open_app", "app": "notepad"}

    async def run(
        self,
        action: str = "screenshot",
        app: str = "",
        text: str = "",
        key: str = "",
        **_: Any,
    ) -> str:
        action = action.lower().strip()
        try:
            if action == "open_app":
                if not app:
                    return "ERROR: app name required"
                cmd = APP_MAP.get(app.lower())
                if cmd:
                    await asyncio.to_thread(subprocess.Popen, cmd)
                elif sys.platform == "win32":
                    await asyncio.to_thread(os.startfile, app)  # pyright: ignore
                else:
                    await asyncio.to_thread(subprocess.Popen, [app])
                return f"OK: launched '{app}'"

            if action == "screenshot":
                return await asyncio.to_thread(self._screenshot)

            if action == "type_text":
                if not text:
                    return "ERROR: text required"
                await asyncio.to_thread(self._type, text)
                return f"OK: typed {len(text)} chars"

            if action == "press_key":
                if not key:
                    return "ERROR: key required (e.g. volumeup, enter, volumeupm...)"
                await asyncio.to_thread(self._press, key)
                return f"OK: pressed '{key}'"

            return ("ERROR: unknown action "
                    "(open_app|screenshot|type_text|press_key)")
        except Exception as exc:
            return f"ERROR: system action '{action}' failed: {exc}"

    # ---------------- thread helpers (pyautogui is blocking) -------------- #
    @staticmethod
    def _screenshot() -> str:
        try:
            import pyautogui
        except ImportError:
            return "ERROR: pyautogui not installed (pip install pyautogui)"
        shots = config.WORKSPACE_DIR / "screenshots"
        shots.mkdir(exist_ok=True)
        path = shots / f"screen_{int(time.time())}.png"
        pyautogui.screenshot(str(path))
        return (f"OK: screen saved -> {path}\n"
                f"Use it with Gemini vision or read it via FileManager.")

    @staticmethod
    def _type(text: str) -> None:
        import pyautogui
        pyautogui.typewrite(text, interval=0.02)

    @staticmethod
    def _press(key: str) -> None:
        import pyautogui
        pyautogui.press(key)
