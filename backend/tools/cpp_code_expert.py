"""
Tool :: CppCodeExpert

Senior C++ engineeer agent: generates, optimizes, reviews and debugs
modern C++ for the USER'S OWN projects (game engines, Unreal Engine
gameplay modules, tools, systems programming).

Quality bar enforced in the prompt:
- compilable single-file output, clearly formatted for copy/paste
- modern C++ (RAII, move semantics, const-correctness), no UB
- performance reasoning: cache locality, allocation strategy, branches
- built-in Syntax & Logic re-check pass before returning

Deliver complete, working implementations for the requested task.
"""
from __future__ import annotations

import re
from typing import Any

from .base import Tool

_SYSTEM = """You are a senior C++ systems/game-engine engineer with 15+ years
in mines like Unreal Engine, custom engines and high-performance tooling.

Task: {action_text}

Hard output rules:
1. Return ONE compilable .cpp/.h block inside a fenced ```cpp block,
   ready to copy — no placeholders like "// implement here".
2. Modern C++17+ where possible: RAII, smart pointers, noexcept on moves,
   const-correctness. Zero undefined behaviour; guard indices/pointers.
3. Performance commentary: explain allocation strategy, cache behaviour
   and branch choices in 3-8 bullet lines after the code.
4. End with a "Self-check" section: syntax risks you re-verified, logic
   edge cases you considered, and the exact minimal compile command.
5. Unreal Engine work: follow UE conventions (USTRUCT/UCLASS, UObject
   lifetime, engine modules) when requested, scoped to the user's OWN
   project.
6. Deliver the requested code fully and completely.
"""

# second-pass verifier prompt: the REAL internal syntax & logic check
_VERIFY = """You are a C++ correctness verifier ( GCC appreciation in mind).
Re-read the answer below and hunt for: syntax errors, undefined behaviour,
API misuse, dangling lifetime mistakes, missing includes that stop
compilation, and logic slips versus the task.

Reply ONLY with JSON: {"ok": true, "issues": []}
or                    {"ok": false, "issues": ["...", "..."]}

If issues exist you MUST fix them and return, in addition, a field
"fixed_code" containing the corrected full answer (same format).
"""

_ACTIONS = {
    "generate": "Generate new C++ code from the requirement below.",
    "optimize": "Optimize the provided C++ for speed/memory WITHOUT changing behaviour.",
    "review": "Review the provided C++ like a principal engineer: bugs, UB, API misuse, perf.",
    "debug": "Diagnose the reported defect in the provided C++ and provide the minimal fix.",
}


class CppCodeExpert(Tool):
    name = "CppCodeExpert"
    description = (
        "Generate / optimize / review / debug modern C++ for the user's own "
        "projects (game engine, tools, systems code): {'action': "
        "'generate'|'optimize'|'review'|'debug', 'requirement': '...', "
        "'code': '...'} — returns a copy-ready single-file block plus a "
        "self-check."
    )
    example = {"action": "generate",
               "requirement": "double-buffered ECS sparse-set"}

    async def run(self, action: str = "generate",
                  requirement: str = "", code: str = "",
                  **_: Any) -> str:
        action = action.lower().strip()
        action_text = _ACTIONS.get(action)
        if action_text is None:
            return ("ERROR: unknown action "
                    "(generate|optimize|review|debug)")
        if action in ("generate",) and not requirement.strip():
            return "ERROR: requirement required for generate"
        if action in ("optimize", "review", "debug") and not code.strip():
            return f"ERROR: code required for {action}"

        from model_router import ROUTER
        brain = ROUTER.get("groq") or ROUTER.get("gemini")
        if brain is None:
            return "ERROR: no LLM provider available for CppCodeExpert"

        user_msg = f"Requirement: {requirement}\n\n```cpp\n{code}\n```"
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            reply = await brain.ainvoke([
                SystemMessage(content=_SYSTEM.format(
                    action_text=action_text)),
                HumanMessage(content=user_msg),
            ])
            text = reply.content if isinstance(reply.content, str) \
                else str(reply.content)

            # ---------- REAL internal verification pass ---------- #
            # A second LLM call re-reads the answer hunting for
            # syntax/UB/logic slips; if issues are found the corrected
            # answer is used, and the issues are reported transparently.
            verified_text, issues = await self._verify(brain, text)
            report = text if not issues else (
                "⚠ Internal verification flagged & fixed "
                f"{len(issues)} issue(s):\n" +
                "\n".join(f" - {i}" for i in issues) +
                "\n\n" + verified_text
            )

            has_block = "```" in report
            note = "" if has_block else \
                "\n[note: model returned no fenced code block — ask again " \
                "with 'reply with a single ```cpp block']"
            return report[:9000] + note
        except Exception as exc:
            return f"ERROR: CppCodeExpert failed: {exc}"

    @staticmethod
    async def _verify(brain, answer: str) -> "tuple[str, list]":
        """Second-pass correctness check. Returns (final_answer, issues).
        Falls back to the original answer on any verifier failure."""
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            reply = await brain.ainvoke([
                SystemMessage(content=_VERIFY),
                HumanMessage(content=answer[:6000]),
            ])
            content = reply.content if isinstance(reply.content, str) \
                else str(reply.content)
            import json as _json
            import re as _re
            fenced = _re.search(r"```(?:json)?\s*(.+?)```",
                                content, _re.DOTALL)
            raw = fenced.group(1) if fenced else content
            s, e = raw.find("{"), raw.rfind("}")
            data = _json.loads(raw[s:e + 1])
            if data.get("ok", True):
                return answer, []
            issues = [str(i)[:200] for i in (data.get("issues") or [])]
            fixed = str(data.get("fixed_code") or "").strip()
            return (fixed if fixed else answer), issues
        except Exception:
            return answer, []
        except Exception as exc:
            return f"ERROR: CppCodeExpert failed: {exc}"
