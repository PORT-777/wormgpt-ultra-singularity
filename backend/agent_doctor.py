"""Offline readiness report for the agent — no network calls, no keys printed.

    cd backend && python agent_doctor.py

Reports the parts that are actually wired up: tool registry, skill packs,
prompt source, sandbox backend and provider availability flags.
"""
from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_engine  # noqa: E402
import configs as config  # noqa: E402
import native_tools  # noqa: E402
import skills  # noqa: E402
from tools import TOOL_REGISTRY  # noqa: E402

SAMPLE_TASKS = [
    "write a PE parser in C++",
    "derive struct layout and offsets for a binary",
    "web pentest on my own app",
    "hello there",
]


def collect() -> dict:
    broken = []
    for name, cls in sorted(TOOL_REGISTRY.items()):
        try:
            cls()
        except Exception as exc:
            broken.append({"tool": name, "error": f"{type(exc).__name__}: {exc}"})

    packs = skills.load_packs()
    selection = {
        task: [p["name"] for p in skills.relevant_packs(task)]
        for task in SAMPLE_TASKS
    }

    sandbox_info = {}
    try:
        import sandbox
        sandbox_info = sandbox.status()
    except Exception as exc:
        sandbox_info = {"error": f"{type(exc).__name__}: {exc}"}

    providers = {
        key: bool(getattr(config, key, False))
        for key in ("LOCAL_READY", "GROQ_READY", "GEMINI_READY",
                    "HF_READY", "OPENROUTER_READY", "KILO_READY", "Z_AI_READY")
    }

    return {
        "python": platform.python_version(),
        "zero_refusal": bool(getattr(config, "ZERO_REFUSAL", False)),
        "prompt": {
            "source": agent_engine.PROMPT_SOURCE,
            "chars": len(agent_engine.SYSTEM_TEMPLATE),
            "tools_placeholders": agent_engine.SYSTEM_TEMPLATE.count("{tools}"),
        },
        "tools": {
            "registered": len(TOOL_REGISTRY),
            "broken_on_init": broken,
            "native_call_definitions": len(native_tools.build_definitions()),
            "native_calls_enabled": bool(getattr(config, "NATIVE_TOOL_CALLS", True)),
        },
        "skills": {
            "loaded": len(packs),
            "always_on": [p["name"] for p in packs if p["always"]],
            "selection_samples": selection,
        },
        "sandbox": sandbox_info,
        "providers_ready": providers,
    }


def main() -> int:
    report = collect()
    out = Path(__file__).resolve().parent / "agent_doctor_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"python={report['python']} zero_refusal={report['zero_refusal']}")
    print(f"tools={report['tools']['registered']} "
          f"broken={len(report['tools']['broken_on_init'])} "
          f"native_defs={report['tools']['native_call_definitions']} "
          f"native_enabled={report['tools']['native_calls_enabled']}")
    print(f"skills={report['skills']['loaded']} "
          f"always_on={report['skills']['always_on']}")
    print(f"prompt_chars={report['prompt']['chars']} "
          f"placeholders={report['prompt']['tools_placeholders']}")
    print(f"providers_ready={report['providers_ready']}")
    for task, names in report["skills"]["selection_samples"].items():
        print(f"  {task!r} -> {names}")
    print(f"report={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
