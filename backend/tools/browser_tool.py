"""
Tool :: Browser (Playwright)

Real browser automation — not just search: navigate, click, type,
extract page text, take screenshots. Used for logging into dashboards,
scraping document pages, downloading files, etc.

Setup (once):
    pip install playwright
    playwright install chromium

Async-native (Playwright's asyncio API) — fits our event loop cleanly.
The browser instance is a module-level singleton reused across calls.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import configs as config
from .base import Tool

_pw = None          # playwright instance
_browser = None     # chromium browser
_page = None        # active tab


class Browser(Tool):
    name = "Browser"
    description = (
        "Drive a real browser: {'action': 'navigate'|'click'|'type'|'content'|"
        "'screenshot', 'url': ..., 'selector': ..., 'text': ...}. "
        "Use for pages that require interaction beyond plain search."
    )
    example = {"action": "navigate", "url": "https://github.com/login"}

    @staticmethod
    async def _ensure_browser():
        global _pw, _browser, _page
        if _browser is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright not installed: pip install playwright "
                "&& playwright install chromium"
            ) from exc
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(headless=True)
        _page = await _browser.new_page()

    async def run(
        self,
        action: str = "navigate",
        url: str = "",
        selector: str = "",
        text: str = "",
        **_: Any,
    ) -> str:
        # self-healing: if the browser/page died mid-session, relaunch
        # once transparently instead of failing all following calls.
        for attempt in (1, 2):
            try:
                await self._ensure_browser()
                outcome = await self._dispatch(action, url, selector, text)
                return outcome
            except Exception as exc:
                if "closed" in str(exc).lower() and attempt == 1:
                    await self._reset()
                    continue
                return (f"ERROR: browser action '{action}' failed: {exc}")
        return f"ERROR: browser action '{action}' failed"

    async def _reset(self):
        global _browser, _pw, _page
        try:
            if _browser is not None:
                await _browser.close()
        except Exception:
            pass
        try:
            if _pw is not None:
                await _pw.stop()
        except Exception:
            pass
        _browser = _page = _pw = None

    async def _dispatch(self, action, url, selector, text) -> str:
        action = action.lower().strip()
        try:
            if action == "navigate":
                if not url:
                    return "ERROR: url required"
                await _page.goto(url, timeout=25000,
                                 wait_until="domcontentloaded")
                title = await _page.title()
                return f"OK: navigated to {url} | title: {title} | status: {_page.url}"

            if action == "click":
                if not selector:
                    return "ERROR: selector required"
                await _page.click(selector, timeout=10000)
                return f"OK: clicked '{selector}' | now at {_page.url}"

            if action == "type":
                if not selector or not text:
                    return "ERROR: selector + text required"
                await _page.fill(selector, text, timeout=10000)
                return f"OK: typed {len(text)} chars into '{selector}'"

            if action == "content":
                body = await _page.inner_text("body", timeout=10000)
                return body[:6000] or "[empty page]"

            if action == "screenshot":
                shots = config.WORKSPACE_DIR / "screenshots"
                shots.mkdir(exist_ok=True)
                path = shots / f"shot_{int(time.time())}.png"
                await _page.screenshot(path=str(path), full_page=False)
                return f"OK: screenshot saved -> {path}"

            return f"ERROR: unknown action '{action}' (navigate|click|type|content|screenshot)"

        except Exception:
            # propagate so run()'s self-healing logic can react
            raise


async def shutdown_browser():
    """Called on FastAPI shutdown to close chromium cleanly."""
    global _browser, _pw, _page
    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = _page = None
        if _pw is not None:
            await _pw.stop()
            _pw = None
