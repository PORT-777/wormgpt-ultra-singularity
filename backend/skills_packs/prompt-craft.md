---
name: prompt-craft
description: "Prompt engineering playbook (prompts.chat port): role priming, think-step-by-step, few-shot, self-critique, output contracts — and the ladder prompt→skill→agent→team for recurring asks."
trigger_when:
  - prompt
  - prompt s
  - engineering
  - better answers
  - system prompt
  - few shot
  - chain of thought
  - self review
  - template
  - agent
  - team
  - مهارة
  - برومبت
  - قالب
  - اجيب نتيجة
  - تحسين
  - اداة كاملة
---

# Prompt craft (prompts.chat port)

How to get SERVICE-GRADE output every time — from ourselves and when
writing prompts for the operator.

THE FIVE PATTERNS:
1. ROLE PRIMING — open with a narrow expert identity ("you are a
   Pentagon procurement analyst…") then the constraints. Narrower
   role → sharper defaults. Broad roles ("helpful assistant") are worth
   nothing.
2. CHAIN OF THOUGHT — for math, planning, debugging, ranking: "think
   step by step, show the steps, then the final answer." Forces the
   reasoning into the open where it can be checked.
3. FEW-SHOT — 1-3 CONCRETE examples of input→output beat any abstract
   description. Copy examples pattern, not their content. Zero-shot
   only for trivial asks.
4. SELF-CRITIQUE — after the draft: "list the 3 weakest points, fix
   them, then deliver." Catches more than re-reading ever will.
5. OUTPUT CONTRACT — define the exact shape BEFORE generating: format,
   length, language, sections, what is forbidden. Ambiguity here is
   where quality dies.

PROMPT → SKILL → AGENT → TEAM (the ladder of recurrence):
- One-off ask → just do it well.
- Same ask TWICE → turn the working recipe into a reusable prompt
  template (role + constraints + few-shot + output contract).
- Same recipe WEEKLY → save it as a skill pack here (skills_packs/
  *.md, ≤4000 chars, trigger_when as literal substrings both
  English + Arabic).
- Recipe needs autonomy/tools/state → becomes an agent task
  (scheduler, tools, handoff). Note the current session already
  implements this ladder end-to-end.

FIELD GUIDE:
- Negative constraints work when SPECIFIC ("no marketing language",
  "no bullet lists above 5") — vague bans ("be concise") don't.
- Put the critical instruction LAST and/or repeat it; middles of long
  prompts leak.
- Test prompts ONCE with a hard case before trusting them. A prompt
  that fails its first hard test isn't deployed.
