"""Send three escalating benign tasks to a running local /api/chat server.

    cd backend && python tests/chat_tasks_probe.py [base_url]

Captures the SSE event trace (thoughts, actions, observations, final) so tool
execution is observable, not just the final text. No keys are printed.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:7777"

WORKSPACE_RULE = (
    "\n\nIMPORTANT: Do NOT use ComputerTool or Daytona sandboxes (their disk "
    "quota is exhausted). Use UniversalFileManager to write files into the "
    "local workspace and PythonInterpreter to execute them. Report the exact "
    "tool output you observed; never claim execution you did not see."
)

TASKS = [
    {
        "id": "EASY",
        "prompt": "Use the MemoryLogicCalculator tool with op hex2dec and value 0x2A. "
                  "Reply with just the decimal number.",
        "timeout": 300,
    },
    {
        "id": "MEDIUM",
        "prompt": "Create a file named probe_medium.py in the workspace containing a "
                  "function add(a, b) plus two assertions (add(2,3)==5 and add(-1,1)==0). "
                  "Then run it with a Python tool and report the observed output. "
                  "Do not claim it ran unless you saw the tool output."
                  + WORKSPACE_RULE,
        "timeout": 420,
    },
    {
        "id": "HARD",
        "prompt": "Three dependent steps: (1) use MemoryLogicCalculator with op chain, "
                  "base 0x1000 and offsets [0x10, 0x20, 0x30]; (2) write a Python file "
                  "probe_hard.py in the workspace that recomputes the same sum and prints "
                  "the decimal result; (3) execute it and compare the two numbers. "
                  "Report both numbers, whether they match, and the tool output you saw."
                  + WORKSPACE_RULE,
        "timeout": 600,
    },
]


def run_task(client: httpx.Client, task: dict) -> dict:
    started = time.time()
    record = {"id": task["id"], "prompt": task["prompt"], "events": [],
              "tools": [], "final": "", "errors": []}
    try:
        with client.stream(
            "POST", f"{BASE}/api/chat",
            json={
                "message": task["prompt"],
                "messages": [{"role": "user", "content": task["prompt"]}],
                "session_id": f"probe-{task['id'].lower()}",
                "stream": True,
                "model_route": "auto",
                "depth": "standard",
            },
            timeout=task["timeout"],
        ) as response:
            record["http_status"] = response.status_code
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    ev = json.loads(payload)
                except Exception:
                    continue
                kind = ev.get("type", "")
                data = ev.get("data")
                record["events"].append({"type": kind,
                                         "data": str(data)[:600]})
                if kind == "action" and isinstance(data, dict):
                    record["tools"].append(data.get("tool"))
                elif kind == "final":
                    record["final"] = str(data)
                elif kind == "error":
                    record["errors"].append(str(data)[:400])
    except Exception as exc:
        record["errors"].append(f"{type(exc).__name__}: {exc}")
    record["elapsed_s"] = round(time.time() - started, 2)
    return record


def main() -> int:
    out = {"base_url": BASE,
           "observed_at_utc": datetime.now(timezone.utc).isoformat(),
           "tasks": []}
    with httpx.Client() as client:
        try:
            r = client.get(f"{BASE}/health", timeout=10)
            out["health"] = {"status": r.status_code, "body": r.text[:300]}
        except Exception as exc:
            out["health"] = {"error": f"{type(exc).__name__}: {exc}"}
        only = {x.strip().upper() for x in os.getenv("PROBE_TASKS", "").split(",")
                if x.strip()}
        for task in TASKS:
            if only and task["id"] not in only:
                continue
            print(f"--- sending {task['id']} ---", flush=True)
            record = run_task(client, task)
            out["tasks"].append(record)
            print(f"{task['id']}: http={record.get('http_status')} "
                  f"tools={record['tools']} events={len(record['events'])} "
                  f"elapsed={record['elapsed_s']}s", flush=True)
            print(f"  final={record['final'][:300]!r}", flush=True)
            if record["errors"]:
                print(f"  errors={record['errors']}", flush=True)

    path = Path(__file__).resolve().parent / "chat_tasks_probe_report.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    print(f"report={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
