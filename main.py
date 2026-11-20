# main.py
# Language: Python 3 | Runtime: CPython | Target: Windows 11
# 🔥😈 PORT 777 EVIL ☠️🔥👹 - Singularity Edition â€” Unified Entry Point + Interactive Shell.
# Ù†Ù‚Ø·Ø© Ø§Ù„Ø¯Ø®ÙˆÙ„ Ø§Ù„Ù…ÙˆØ­Ø¯Ø©: Ø³Ø¬Ù„ Ø§Ù„Ø£Ø¯ÙˆØ§Øª + Ø§Ù„Ù…Ø­Ø±Ùƒ Ø§Ù„ÙƒØ§Ù…Ù„ (backend/agent_engine).
# Ø£ÙˆØ§Ù…Ø± Ø§Ù„Ø´Ù„: Ù…Ù‡Ù…Ø© Ø­Ø±Ø© â†’ Ø§Ù„Ù…Ø­Ø±Ùƒ (ReAct-E). Ø£ÙˆØ§Ù…Ø± Ø®Ø§ØµØ©: /tools /health /trace /full /exit

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

# ÙˆØ­Ø¯Ø© Ø§Ù„ØªØ­ÙƒÙ… Ø¹Ù„Ù‰ Windows Ù‡ÙŠ cp1252 â€” Ù‚ÙˆØ© UTF-8 Ø­ØªÙ‰ Ù„Ø§ ØªØ¹Ø·Ø¨ Ø§Ù„Ø¹Ø±Ø¨ÙŠØ©
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from tools import execute_tool, tool_schemas, TOOL_REGISTRY  # noqa: E402

ENGINE = None
_ENGINE_ERROR: Optional[str] = None
try:
    from backend.agent_engine import ENGINE      # noqa: E402
except Exception as _exc:
    _ENGINE_ERROR = f"{type(_exc).__name__}: {_exc}"

ROUTER = None
try:
    from model_router import ROUTER               # noqa: E402
except Exception as _exc:
    ROUTER = None
    if _ENGINE_ERROR is None:
        _ENGINE_ERROR = f"router: {type(_exc).__name__}: {_exc}"


class SingularityOrchestrator:
    """ÙŠØ¬Ù…Ø¹ ÙƒÙ„ Ø§Ù„Ù…ÙŠØ²Ø§Øª ÙÙŠ Ù…Ø´Ø±ÙˆØ¹ ÙˆØ§Ø­Ø¯."""

    def __init__(self) -> None:
        self.registry = TOOL_REGISTRY
        self.engine = ENGINE
        self.router = ROUTER
        self.history: List[Dict[str, str]] = []
        self.full_access = False

    def available_tools(self) -> List[str]:
        return sorted(self.registry.keys())

    def run_sync(self, description: str, context: Dict[str, Any] | None = None) -> Any:
        """ØªØ´ØºÙŠÙ„ Ù…Ø²Ø§Ù…Ù† Ù„Ø£Ø¯Ø§Ø© ÙˆØ§Ø­Ø¯Ø© Ù…Ø¨Ø§Ø´Ø±Ø© (Ø¨Ø¯ÙˆÙ† LLM)."""
        ctx = dict(context or {})
        tool_name = str(ctx.pop("tool", "") or description).strip()
        if not tool_name:
            return {"error": "tool Ù…Ø·Ù„ÙˆØ¨"}
        try:
            out = asyncio.run(execute_tool(tool_name, ctx))
            return {"tool": tool_name, "output": out}
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    async def run_agent(self, task: str, full_access: bool | None = None) -> str:
        """ØªØ´ØºÙŠÙ„ Ø§Ù„Ù…Ø­Ø±Ùƒ Ø§Ù„ÙƒØ§Ù…Ù„ ReAct-E (ÙŠØ­ØªØ§Ø¬ LLM Ø¹Ø¨Ø± ROUTER)."""
        if self.engine is None:
            return f"ENGINE ØºÙŠØ± Ù…ØªØ§Ø­: {_ENGINE_ERROR}"
        parts: List[str] = []
        final_text = ""
        async for event in self.engine.run_stream(
            task,
            history=self.history or None,
            model_route="auto",
            full_access=self.full_access if full_access is None else full_access,
        ):
            kind = event.get("type", "")
            data = event.get("data")
            if kind == "stream":
                parts.append(str(data))
            elif kind == "final":
                final_text = str(data)
            elif kind == "reflection":
                print(f"  [reflection] {data}")
            elif kind in ("error", "failed"):
                print(f"  [error] {data}")
        answer = final_text or "".join(parts).strip()
        if answer:
            self.history.append({"role": "user", "content": task})
            self.history.append({"role": "assistant", "content": answer})
            self.history = self.history[-12:]
        return answer

    async def show_thoughts(self, task: str) -> None:
        """Ø¹Ø±Ø¶ Ø£Ø­Ø¯Ø§Ø« Ø§Ù„Ù…Ø­Ø±Ùƒ Ø­ÙŠØ§Ù‹ (thought / action / observation)."""
        if self.engine is None:
            print(f"ENGINE ØºÙŠØ± Ù…ØªØ§Ø­: {_ENGINE_ERROR}")
            return
        final_text = ""
        try:
            async for event in self.engine.run_stream(
                task, history=self.history or None, model_route="auto",
                full_access=self.full_access,
            ):
                kind = event.get("type", "")
                data = event.get("data")
                if kind == "thought":
                    print(f"\n>[thought] {data}"[:400])
                elif kind == "action":
                    if isinstance(data, dict):
                        print(f"  >tool {data.get('tool')}  iter={data.get('iteration', '')}"
                              f"  args={json_safe(data.get('args'))}")
                elif kind == "observation":
                    if isinstance(data, dict):
                        out = str(data.get("output", ""))[:500]
                        print(f"  <obs {data.get('tool')}: {out}")
                elif kind == "reflection":
                    print(f"  != reflection: {data}")
                elif kind == "plan":
                    if isinstance(data, list):
                        print(f"  plan: {[s.get('title') for s in data]}")
                elif kind == "stream":
                    print(str(data), end="", flush=True)
                elif kind == "final":
                    final_text = str(data)
                elif kind in ("error", "failed"):
                    print(f"  x ERROR: {data}")
                elif kind == "review":
                    if isinstance(data, dict):
                        print(f"  [crew review] step={data.get('step')} "
                              f"verdict={data.get('verdict')}")
        except Exception as exc:
            print(f"\n  x engine failed: {type(exc).__name__}: {exc}")
            return
        if final_text and not final_text.endswith("\n"):
            print()
        if final_text:
            self.history.append({"role": "user", "content": task})
            self.history.append({"role": "assistant", "content": final_text})
            self.history = self.history[-12:]

    def schemas(self) -> str:
        return tool_schemas()


def json_safe(o: Any) -> str:
    try:
        return str(o if not isinstance(o, dict) else
                   {k: str(v)[:120] for k, v in o.items()})
    except Exception:
        return str(o)


def interactive_shell(orch: SingularityOrchestrator) -> None:
    print("\n--- 🔥😈 PORT 777 EVIL ☠️🔥👹 â€” Interactive Shell (ReAct-E Live) ---")
    print("Ø£ÙˆØ§Ù…Ø± Ø®Ø§ØµØ©: /tools /health /full /mode /exit")
    print("Ø£ÙŠ Ø³Ø·Ø± Ø¢Ø®Ø± ÙŠÙØ±Ø³Ù„ Ù„Ù„Ù…Ø­Ø±Ùƒ Ù…Ø¨Ø§Ø´Ø±Ø©.")
    while True:
        try:
            line = input("\n🔥😈 PORT 777 EVIL ☠️🔥👹> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        if line == "/exit":
            return
        if line == "/tools":
            for t in orch.available_tools():
                print("  -", t)
            continue
        if line == "/full":
            orch.full_access = not orch.full_access
            print("Full Access:", "-> ON" if orch.full_access else "-> OFF")
            continue
        if line == "/health" and ROUTER is not None:
            try:
                snap = ROUTER.status()
                for name, st in snap.items():
                    print(f"  {name}: available={st['available']} "
                          f"active={st['active']} healthy={st['healthy']} "
                          f"models={st['models']}")
            except Exception as exc:
                print(f"  health failed: {exc}")
            continue
        # Ø³Ø·Ø± Ù…Ù‡Ù…Ø© Ø¹Ø§Ø¯ÙŠ â†’ ØªØ´ØºÙŠÙ„ Ø§Ù„Ù…Ø­Ø±Ùƒ Ø­ÙŠØ§Ù‹
        asyncio.run(orch.show_thoughts(line))


def demo() -> None:
    orch = SingularityOrchestrator()
    print("=== 🔥😈 PORT 777 EVIL ☠️🔥👹 - Singularity Edition ===\n")
    tools = orch.available_tools()
    print(f"Ø£Ø¯ÙˆØ§Øª Ù…Ø³Ø¬Ù„Ø©: {len(tools)}")
    for t in tools:
        print("  -", t)

    CALC = "MemoryLogicCalculator"
    cases = [
        ("Ø³Ù„Ø³Ù„Ø© Ù…Ø¤Ø´Ø±Ø§Øª", {"tool": CALC, "op": "chain", "base": "0x7FF6A1B2C000",
                          "offsets": ["0x10", "0x28", "0x1C"]}),
        ("Ù‡ÙƒØ³ Ø¥Ù„Ù‰ Ø¹Ø´Ø±ÙŠ", {"tool": CALC, "op": "hex2dec", "value": "0x1011"}),
        ("Ø¨Ù†ÙŠØ© struct", {"tool": CALC, "op": "struct_offset",
                         "fields": {"id": "u32", "name_len": "u8",
                                    "flags": "u32", "next": "u64"}}),
        ("ÙØ§Ø±Ù‚ Ø¹Ù†Ø§ÙˆÙŠÙ†", {"tool": CALC, "op": "delta", "a": "0x100", "b": "0x40"}),
    ]
    for desc, ctx in cases:
        r = orch.run_sync(desc, ctx)
        out = r.get("output") or r.get("error")
        print(f"\n[{desc}]\n{out}")

    print("\n--- Ø§Ù„Ø®Ø·ÙˆØ© Ø§Ù„ØªØ§Ù„ÙŠØ©: Ø§Ù„ÙˆØ¶Ø¹ Ø§Ù„ØªÙØ§Ø¹Ù„ÙŠ Ø¹Ø¨Ø± interactive_shell(orch) ---")
    print("ENGINE:", "Ù…ØªØ§Ø­" if orch.engine else "ØºÙŠØ± Ù…ØªØ§Ø­")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "shell":
        orch = SingularityOrchestrator()
        interactive_shell(orch)
    else:
        demo()
        if len(sys.argv) > 1 and sys.argv[1] == "agent":
            orch = SingularityOrchestrator()
            task = " ".join(sys.argv[2:]) or "Ø³Ù„Ù…Ù†ÙŠ Ù…Ù„Ø®Øµ Ø§Ù„Ù…Ø´Ø±ÙˆØ¹"
            print("\n[agent run]")
            r = asyncio.run(orch.run_agent(task))
            print(r)
