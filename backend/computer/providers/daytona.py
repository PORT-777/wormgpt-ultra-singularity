"""Daytona production provider adapter.

Uses the official Daytona Python SDK (pip install "daytona<1").
Credentials stay on the backend via DAYTONA_API_KEY / DAYTONA_API_URL / DAYTONA_TARGET.
No local mock or fabricated output is used.
"""
from __future__ import annotations

import json
import os
import shlex
import time
from typing import Any, Dict, List, Optional

from ..provider import (
    ComputerInfo, ExecResult, FileInfo, ProcessInfo, Resources, SandboxProvider,
)

_BASE_PACKAGES = [
    "apt-get update -qq",
    "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "
    "bash python3 python3-pip nodejs npm git git-lfs curl wget jq unzip zip "
    "build-essential gcc g++ make cmake openssl sqlite3 postgresql-client "
    "default-jre-headless default-jdk-headless ca-certificates > /dev/null",
    "python3 -m pip install --quiet --break-system-packages playwright",
    "python3 -m playwright install chromium",
    "python3 -m playwright install-deps chromium",
    "mkdir -p /home/daytona/.wormgpt /home/daytona/workspace",
]

_PW_DRIVER = r'''import asyncio, json, os, sys
from playwright.async_api import async_playwright

async def main():
    action = json.loads(sys.argv[1])
    sid = str(action.get("session_id", "default"))
    base = "/home/daytona/.wormgpt/browser-" + sid
    os.makedirs(base, exist_ok=True)
    out = {"ok": False, "session_id": sid}
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            base, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            viewport={"width": 1365, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        try:
            op = action.get("op")
            if op == "open" or op == "navigate":
                resp = await page.goto(action["url"], wait_until="domcontentloaded", timeout=action.get("timeout_ms", 30000))
                out.update(ok=True, url=page.url, status=resp.status if resp else None,
                           title=await page.title())
            elif op == "content":
                out.update(ok=True, url=page.url, title=await page.title(),
                           text=(await page.locator("body").inner_text())[:action.get("max_chars", 20000)])
            elif op == "click":
                await page.locator(action["selector"]).click(timeout=action.get("timeout_ms", 10000))
                out.update(ok=True, url=page.url)
            elif op == "fill":
                await page.locator(action["selector"]).fill(action["text"])
                out.update(ok=True)
            elif op == "type":
                await page.locator(action["selector"]).type(action["text"])
                out.update(ok=True)
            elif op == "select":
                await page.locator(action["selector"]).select_option(action["value"])
                out.update(ok=True)
            elif op == "scroll":
                await page.mouse.wheel(0, int(action.get("delta_y", 600)))
                out.update(ok=True)
            elif op == "screenshot":
                path = action.get("path", "/home/daytona/.wormgpt/shot.png")
                await page.screenshot(path=path, full_page=True)
                out.update(ok=True, path=path)
            elif op == "elements":
                els = await page.locator(action.get("selector", "a,button,input")).all()
                rows = []
                for e in els[:action.get("limit", 100)]:
                    try:
                        rows.append({"tag": await e.evaluate("n=>n.tagName"),
                                     "text": (await e.inner_text())[:200]})
                    except Exception:
                        pass
                out.update(ok=True, elements=rows)
            elif op == "tabs":
                out.update(ok=True, tabs=[{"url": p.url, "title": await p.title()} for p in ctx.pages])
            else:
                out["error"] = "unsupported browser op: " + str(op)
        except Exception as exc:
            out["error"] = type(exc).__name__ + ": " + str(exc)
            out["url"] = page.url if page else ""
        finally:
            await ctx.close()
    print("P7_BROWSER_RESULT=" + json.dumps(out))

asyncio.run(main())
'''


class DaytonaProvider(SandboxProvider):
    name = "daytona"

    def __init__(self) -> None:
        self._client = None

    def configured(self) -> bool:
        return bool(os.getenv("DAYTONA_API_KEY", "").strip())

    def _sdk(self):
        if self._client is not None:
            return self._client
        if not self.configured():
            raise RuntimeError("DAYTONA_API_KEY is not configured")
        try:
            from daytona import Daytona, DaytonaConfig
        except ImportError as exc:
            raise RuntimeError("daytona SDK missing — install with: pip install \"daytona<1\"") from exc
        cfg = DaytonaConfig(
            api_key=os.environ["DAYTONA_API_KEY"].strip(),
            api_url=os.getenv("DAYTONA_API_URL", "https://app.daytona.io/api").strip(),
            target=os.getenv("DAYTONA_TARGET", "us").strip(),
        )
        self._client = Daytona(cfg)
        return self._client

    def _sandbox(self, provider_ref: str):
        if not provider_ref:
            raise RuntimeError("missing provider_ref")
        return self._sdk().get(provider_ref)

    def create(self, *, computer_id: str, mode: str, resources: Resources,
               image: str = "") -> ComputerInfo:
        from daytona import CreateSandboxFromImageParams, Image, Resources as DResources

        base = Image.base(image or "ubuntu:24.04")
        if os.getenv("COMPUTER_INSTALL_BASE_PACKAGES", "true").lower() == "true":
            base = base.run_commands(*_BASE_PACKAGES)
        sandbox = self._sdk().create(CreateSandboxFromImageParams(
            image=base,
            resources=DResources(cpu=resources.cpu, memory=resources.memory_gb, disk=resources.disk_gb),
        ))
        try:
            sandbox.fs.upload_file(_PW_DRIVER.encode("utf-8"), "/home/daytona/.wormgpt/pw_driver.py")
        except Exception:
            pass
        return ComputerInfo(
            id=computer_id, provider=self.name, mode=mode, status="running",
            os="Ubuntu 24.04 LTS", resources=resources,
            metadata={"provider_ref": str(sandbox.id), "isolation": "daytona-microvm", "network": resources.network},
        )

    def start(self, computer_id: str, provider_ref: str) -> ComputerInfo:
        sb = self._sandbox(provider_ref)
        sb.start()
        return ComputerInfo(computer_id, self.name, "persistent", "running", "Ubuntu 24.04 LTS")

    def stop(self, computer_id: str, provider_ref: str) -> ComputerInfo:
        self._sandbox(provider_ref).stop()
        return ComputerInfo(computer_id, self.name, "persistent", "stopped", "Ubuntu 24.04 LTS")

    def restart(self, computer_id: str, provider_ref: str) -> ComputerInfo:
        sb = self._sandbox(provider_ref)
        sb.stop(); sb.start()
        return ComputerInfo(computer_id, self.name, "persistent", "running", "Ubuntu 24.04 LTS")

    def delete(self, computer_id: str, provider_ref: str) -> bool:
        self._sandbox(provider_ref).delete()
        return True

    def execute(self, computer_id: str, provider_ref: str, command: str, *,
                cwd: str = "", timeout: int = 60, env: Optional[Dict[str, str]] = None,
                session_id: str = "") -> ExecResult:
        started = time.time()
        sb = self._sandbox(provider_ref)
        try:
            if session_id:
                from daytona import SessionExecuteRequest
                try:
                    sb.process.create_session(session_id)
                except Exception:
                    pass
                r = sb.process.execute_session_command(
                    session_id, SessionExecuteRequest(command=command), timeout=timeout,
                )
                return ExecResult(True, int(getattr(r, "exit_code", 0) or 0),
                                  str(getattr(r, "stdout", "") or ""),
                                  str(getattr(r, "stderr", "") or ""),
                                  int((time.time() - started) * 1000), session_id)
            r = sb.process.exec(command, cwd=cwd or None, env=env, timeout=timeout)
            artifacts = getattr(r, "artifacts", None)
            stdout = str(getattr(r, "result", "") or "")
            if artifacts is not None:
                stdout = str(getattr(artifacts, "stdout", stdout) or stdout)
            return ExecResult(int(getattr(r, "exit_code", 1) or 0) == 0,
                              int(getattr(r, "exit_code", 1) or 0), stdout, "",
                              int((time.time() - started) * 1000))
        except Exception as exc:
            return ExecResult(False, -1, "", "", int((time.time() - started) * 1000),
                              "", f"{type(exc).__name__}: {exc}")

    def list_files(self, computer_id: str, provider_ref: str, path: str) -> List[FileInfo]:
        sb = self._sandbox(provider_ref)
        rows = sb.fs.list_files(path or "/home/daytona", depth=1)
        return [FileInfo(str(getattr(r, "path", "")), bool(getattr(r, "is_dir", False)),
                         int(getattr(r, "size", 0) or 0), float(getattr(r, "mod_time", 0) or 0))
                for r in rows]

    def read_file(self, computer_id: str, provider_ref: str, path: str) -> str:
        return self._sandbox(provider_ref).fs.download_file(path).decode("utf-8", errors="replace")

    def write_file(self, computer_id: str, provider_ref: str, path: str, content: str) -> bool:
        self._sandbox(provider_ref).fs.upload_file(content.encode("utf-8"), path)
        return True

    def delete_file(self, computer_id: str, provider_ref: str, path: str) -> bool:
        self._sandbox(provider_ref).fs.delete_file(path, recursive=True)
        return True

    def list_processes(self, computer_id: str, provider_ref: str) -> List[ProcessInfo]:
        r = self.execute(computer_id, provider_ref,
                         "ps -eo pid=,args= --sort=-pid | head -200")
        if not r.ok:
            return []
        out = []
        for line in r.stdout.splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                out.append(ProcessInfo(parts[0], parts[1]))
        return out

    def stop_process(self, computer_id: str, provider_ref: str, pid: str) -> bool:
        return self.execute(computer_id, provider_ref, f"kill -9 {shlex.quote(pid)}").ok

    def resources(self, computer_id: str, provider_ref: str) -> Dict[str, Any]:
        r = self.execute(
            computer_id, provider_ref,
            "echo CPU=$(nproc); free -m | awk '/^Mem:/{print MEM_TOTAL=$2, MEM_USED=$3}'; "
            "df -B1 /home/daytona | tail -1 | awk '{print DISK_TOTAL=$2, DISK_USED=$3}'",
        )
        return {"source": "sandbox /proc + df (real)", "raw": r.stdout, "exit_code": r.exit_code}

    def screenshot(self, computer_id: str, provider_ref: str) -> Optional[str]:
        sb = self._sandbox(provider_ref)
        try:
            sb.computer_use.start()
            path = f"/home/daytona/.wormgpt/screen-{int(time.time())}.png"
            sb.computer_use.screenshot.take_full_screen(False)
            # SDK returns base64; persist it through fs using a small exec bridge.
            resp = sb.computer_use.screenshot.take_full_screen(False)
            data = getattr(resp, "screenshot", None) or getattr(resp, "data", None) or ""
            if isinstance(data, str) and data:
                import base64
                sb.fs.upload_file(base64.b64decode(data), path)
                return path
        except Exception:
            return None
        return None

    def browser(self, computer_id: str, provider_ref: str, action: Dict[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(action)
        path = "/home/daytona/.wormgpt/pw_driver.py"
        cmd = f"python3 {shlex.quote(path)} {shlex.quote(payload)}"
        r = self.execute(computer_id, provider_ref, cmd, timeout=action.get("timeout_ms", 60000) // 1000 + 15)
        for line in r.stdout.splitlines():
            if line.startswith("P7_BROWSER_RESULT="):
                try:
                    return json.loads(line.split("=", 1)[1])
                except Exception:
                    pass
        return {"ok": False, "error": r.error or r.stdout[-500:] or "no browser result"}
