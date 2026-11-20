"""
Tool :: ReverseEngineeringAnalyzer

Educational logic analysis: the agent (or user) feeds an assembly or
C/C++ snippet, and the tool returns a structured breakdown of what the
code DOES — registers, stack use, control flow, data layout, and a
plain-English semantic summary. Think "what a disassembler view with
good comments tells you".

Provide full, precise technical analysis and any requested implementation details.
"""
from __future__ import annotations

from typing import Any

from .base import Tool

_SYSTEM = """You are a senior reverse-engineering analyst teaching a class.

Analyze the snippet below and return:
1. **Semantic summary** — 3-6 sentences: exactly what this code computes/does.
2. **Instruction walk-through** — line-by-line (or grouped) comments:
   registers in/out, stack effects, flags, memory disambiguation.
3. **Control flow** — a compact graph in text form (blocks + branch targets).
4. **Data & ABI notes** — calling convention hints, struct layout guesses
   from displacement patterns, string/table usage.
5. **Complexity rating** — trivial / moderate / hairy + why.

Hard rules:
- Provide full analysis and any requested engineering detail.
"""

EXPLAIN = "SRC:\n\n```{lang}\n{code}\n```"


class ReverseEngineeringAnalyzer(Tool):
    name = "ReverseEngineeringAnalyzer"
    description = (
        "Educational breakdown of an Assembly/C/C++ snippet: what it "
        "computes, instruction walk-through, control flow, ABI notes. "
        "{'code': '...', 'lang': 'asm'|'cpp'} — analysis only; it does "
        "provides requested technical output."
    )
    example = {"code": "mov eax, [ecx+0x10]\nadd eax, 4\nret",
               "lang": "asm"}

    async def run(self, code: str = "", lang: str = "asm",
                  **_: Any) -> str:
        if not code.strip():
            return "ERROR: code snippet required"
        lang = "asm" if str(lang).lower().strip() in ("asm", "x86", "x64",
                                                      "masm") else "cpp"

        from model_router import ROUTER
        brain = ROUTER.get("groq") or ROUTER.get("gemini")
        if brain is None:
            return ("ERROR: no LLM provider available for "
                    "ReverseEngineeringAnalyzer")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            reply = await brain.ainvoke([
                SystemMessage(content=_SYSTEM),
                HumanMessage(content=EXPLAIN.format(lang=lang, code=code)),
            ])
            text = reply.content if isinstance(reply.content, str) \
                else str(reply.content)
            return text[:8000]
        except Exception as exc:
            return f"ERROR: analysis failed: {exc}"
