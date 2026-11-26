"""Opt-in live verification of the native tool-calling path.

One benign task only. No keys printed; the report stores excerpts and call
names, not credentials. Exit codes: 0 = probe completed, 2 = provider/network
unavailable, 1 = schema rejected or no structured call returned.

    cd backend && python tests/live_native_tools_probe.py [route]
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

if os.getenv("TEST_USE_REAL_DB") != "1":
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["STORAGE_BACKEND"] = "local"

import agent_engine  # noqa: E402
import model_router  # noqa: E402
import native_tools  # noqa: E402
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage  # noqa: E402

TASK = ("Use the MemoryLogicCalculator tool to convert hexadecimal 0x10 to "
        "decimal. Then give a short Final Answer with the number.")


async def run(route: str = "groq", timeout: float = 60.0) -> dict:
    report: dict = {"route_requested": route, "task": TASK}
    try:
        name, brain = model_router.ROUTER.resolve(route, task="health")
    except Exception as exc:
        report["error"] = f"resolve failed: {type(exc).__name__}: {exc}"
        return report
    if brain is None:
        report["error"] = f"no brain available for route={route}"
        return report
    report["route"] = name

    defs = native_tools.build_definitions()
    report["definitions"] = len(defs)
    bound, enabled = native_tools.prepare(brain, defs)
    report["bind_supported"] = enabled
    if not enabled:
        report["error"] = "model does not support bind_tools"
        return report

    system = ("You are a tool-using agent. When a tool is needed, call it "
              "directly with structured tool calls, then give the answer.")
    messages = [SystemMessage(content=system), HumanMessage(content=TASK)]

    try:
        reply = await asyncio.wait_for(bound.ainvoke(messages), timeout=timeout)
    except Exception as exc:
        report["error"] = f"invoke failed: {type(exc).__name__}: {exc}"
        return report

    calls = native_tools.extract_calls(reply)
    report["tool_calls"] = [{"name": c.name, "args": c.args} for c in calls]
    report["reply_excerpt"] = str(getattr(reply, "content", "") or "")[:300]

    if not calls:
        report["error"] = "provider accepted schemas but returned no structured call"
        return report

    messages.append(reply)
    for call in calls:
        observation, blocked = await agent_engine.AgentEngine()._execute_tool_call(
            call.name, call.args, "code")
        report.setdefault("observations", []).append({
            "tool": call.name, "blocked": blocked,
            "output": str(observation)[:300],
        })
        messages.append(native_tools.make_tool_message(call, observation))

    try:
        final = await asyncio.wait_for(bound.ainvoke(messages), timeout=timeout)
        report["final_excerpt"] = str(getattr(final, "content", "") or "")[:300]
        report["final_tool_calls"] = len(native_tools.extract_calls(final))
    except Exception as exc:
        report["error"] = f"follow-up failed: {type(exc).__name__}: {exc}"
    return report


def main(argv: list[str] | None = None) -> int:
    route = argv[0] if argv else "groq"
    report = asyncio.run(run(route))
    report["meta"] = {
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
    }
    out = _HERE / "live_native_tools_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if "error" in report:
        print(f"ERROR: {report['error']}")
        print(f"report={out}")
        return 2
    print(f"route={report.get('route')} defs={report['definitions']} "
          f"bind={report['bind_supported']}")
    print(f"tool_calls={report['tool_calls']}")
    print(f"observations={report.get('observations')}")
    print(f"final={report.get('final_excerpt')!r}")
    print(f"report={out}")
    return 0 if report.get("observations") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
