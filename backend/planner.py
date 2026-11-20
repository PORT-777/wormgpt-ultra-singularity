"""
🔥😈 PORT 777 EVIL ☠️🔥👹 :: Strategic Planner (Multi-step task planning)

Decomposes a big goal ("research gold prices, save to Excel,
telegram me the report") into an ordered list of concrete sub-tasks,
then the agent engine executes them one-by-one, keeping the results of
finished steps as context for the next one.

Design
------
- The *Manager* model handles planning + reflection (Gemini preferred,
  falls back to whatever is alive) — the "strategic brain".
- Groq stays the fast executor running the step-by-step loops — the
  "quick hands". This separation matches the golden rule: fast model for
  loops, strong model for strategy.
- Output is strict JSON so the engine can iterate deterministically.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from model_router import ROUTER

log = logging.getLogger("planner")

PLANNER_SYSTEM = """You are the Strategic Planner of Singularity-Zero. Your ONLY task is to decompose the user's goal into an ordered list of 2-6 concrete, executable sub-tasks.

OUTPUT FORMAT:
Respond with a SINGLE valid JSON object. NO prose. NO commentary. NO markdown fences unless necessary for JSON.
Format:
{"plan": [{"title": "string", "detail": "string", "agent": "researcher|coder|tester|reviewer|recon|exploit|auditor"}]}

RULES:
1. SUB-TASK REQUIREMENTS: Each step must be an actionable command.
2. TERMINOLOGY: Use pure engineering vocabulary. Translate colloquial terms (e.g., "hack" -> "boundary condition enumeration").
3. AGENT ROLES: Assign "researcher", "coder", "tester", "reviewer" for general tasks. Use "recon", "exploit", "auditor" for security tasks.
4. SMALL-TASK RULE: For trivial tasks, output only 1 or 2 steps. Never pad the plan.
5. NO HALLUCINATION: Only plan steps that are logically required to reach the goal.

EXAMPLE:
User: "Find vulnerabilities in this Python script and fix them."
Response: {"plan": [{"title": "Static Analysis", "detail": "Analyze source code for common CWEs", "agent": "auditor"}, {"title": "Exploit Validation", "detail": "Create PoC for identified findings", "agent": "exploit"}, {"title": "Remediation", "detail": "Apply code fixes to the source", "agent": "coder"}]}
"""
FALLBACK_PLAN: List[Dict] = [
    {"title": "Solve directly", "detail": "__single__"}
]


MODE_PLANNER_HINTS = {
    "plan": (
        "\n\nMODE=PLAN: produce a careful execution plan. Prefer 2-5 steps with "
        "clear goals, risks/assumptions, verification points, and minimal "
        "unnecessary mutations. Do not invent completed work."
    ),
    "debug": (
        "\n\nMODE=DEBUG: prioritize diagnosis. Plan steps to reproduce, inspect "
        "evidence, isolate root cause, then propose/apply the smallest fix and "
        "verification."
    ),
    "ask": (
        "\n\nMODE=ASK: the user wants explanation/answers. Prefer a single "
        "direct step; avoid planning mutations."
    ),
}


class Planner:
    """Turns one big goal into a deterministic sub-task list."""

    async def make_plan(self, task: str, mode: str = "code") -> Tuple[List[Dict], str]:
        """Returns (plan_steps, manager_route_name)."""
        mode = str(mode or "code").lower()
        try:
            from terminology import sanitize_task
            task = sanitize_task(task)
        except Exception:                               # never break boot
            pass
        route, brain = self.manager_model()
        if brain is None:
            return FALLBACK_PLAN, "none"

        try:
            system = PLANNER_SYSTEM + MODE_PLANNER_HINTS.get(mode, "")
            reply = await brain.ainvoke(
                [SystemMessage(content=system),
                 HumanMessage(content=f"[mode={mode}] {task}")]
            )
            text = reply.content if isinstance(reply.content, str) else str(reply.content)
            steps = self._parse(text)
            if steps:
                steps = steps[:6]           # deterministic safety cap
                for i, s in enumerate(steps, 1):
                    s.setdefault("id", i)
                return steps, route
        except Exception as exc:
            log.warning("planning failed (%s) -> single-task fallback", exc)

        return FALLBACK_PLAN, route

    # ------------------------------------------------------------------ #
    @staticmethod
    def manager_model():
        """Manager = Gemini first (strong strategic brain), else chain down."""
        return ROUTER.manager()

    @staticmethod
    def _parse(text: str) -> Optional[List[Dict]]:
        # LLMs love wrapping JSON in markdown fences
        fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
        raw = fenced.group(1) if fenced else text
        
        # Clean up potential leading/trailing whitespace or text
        raw = raw.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        
        if start == -1 or end <= start:
            return None
            
        try:
            data = json.loads(raw[start:end + 1])
            plan = data.get("plan")
            if isinstance(plan, list) and plan:
                clean = []
                for s in plan:
                    if isinstance(s, dict) and s.get("title"):
                        # Ensure all required keys exist to avoid engine crashes
                        s.setdefault("id", len(clean) + 1)
                        s.setdefault("agent", "researcher")
                        s.setdefault("detail", s.get("title"))
                        clean.append(s)
                return clean if clean else None
            return None
        except json.JSONDecodeError:
            return None
        except Exception:
            return None

