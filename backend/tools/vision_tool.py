"""
Tool :: Vision (Closed-loop seeing)

Gives the agent EYES: analyse any local image file with a real multimodal
model — screenshots from SystemControl/Browser, photos, diagrams, scanned
documents — and return a natural-language answer.

Chain examples:
  SystemControl(screenshot) -> Vision(describe) -> decide next action
  Browser(screenshot)       -> Vision(find button) -> Browser(click X)

Providers are tried in order (OpenRouter vision -> Gemini) by
vision_service.  No fake success: if every provider fails the tool says so.
"""
from __future__ import annotations

import asyncio
from typing import Any

from .base import Tool


class Vision(Tool):
    name = "Vision"
    description = (
        "Analyse an image file (screenshot, photo, diagram) with a real "
        "multimodal model: {'path': 'screenshots/shot_1.png', 'question': "
        "'what does this screen show?'} — host-scope paths need Full Access "
        "Mode."
    )
    example = {"path": "screenshots/shot_1.png",
               "question": "describe the UI state"}

    async def run(self, path: str = "",
                  question: str = "Describe this image in detail.",
                  **_: Any) -> str:
        if not path:
            return "ERROR: path required"
        try:
            lowered = str(path).lower().replace("\\", "/")
            # treat absolute paths as host scope
            if (len(lowered) > 2 and lowered[1] == ":") or \
                    lowered.startswith("/"):
                target = Tool.resolve_any(path)
            else:
                target = self.safe_path(path)
        except PermissionError as exc:
            return f"ERROR: denied — {exc}"
        except FileNotFoundError:
            return (f"ERROR: no such image: {path} — take one first with "
                    f"SystemControl(action='screenshot')")

        import vision_service  # local import avoids import cycles

        res = await asyncio.to_thread(vision_service.describe_image,
                                      str(target), question)
        if not res.get("ok"):
            return f"ERROR: vision analysis failed: {res.get('error')}"
        return (f"[vision answer | image: {target.name} | "
                f"{res.get('provider')}/{res.get('model')}]\n"
                f"{str(res.get('text') or '')[:4000]}")