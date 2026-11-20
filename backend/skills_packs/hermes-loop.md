---
name: hermes-loop
description: "Self-improving loop: learn from every complex task, search past sessions, compressed long-context, operator profile."
trigger_when:
  - learn
  - remember
  - history
  - session
  - compress
  - earlier
  - before
  - previously
  - we did
  - تعلم
  - اتكمن
  - افتكر
  - جلسة
  - جلسات
  - قديم
  - زمان
  - المنقله
  - قبل
  - ضغط
---

# The learning loop (how the engine keeps getting better)

YOU already carry three automatic systems — use them consciously:

1. SESSION SEARCH (SessionSearch tool): before asking the operator to
   repeat anything ("كنا عملنا إيه الليلة اللي فاتت؟"), search it:
   - on vague "did we already …" questions → SessionSearch first
   - cite the session hit briefly ("found it in session ab12: …")
   - search is FREE (FTS5, deterministic) — never burn a whole task
     re-deriving what a session already solved.

2. LEARNED PACKS: after complex work the engine auto-writes
   learned-*.md packs (triggered by the task's keywords, capped at 30,
   originals never edited). If a learned pack is triggered:
   - the playbook inside is YOUR OWN verified procedure — follow it
   - update your technique in practice, not in words: no need to
     mention "I have a learned pack" unless asked

3. OPERATOR PROFILE: steady facts about the operator (language, style,
   environment) arrive injected every task as "OPERATOR:" lines.
   - OBEY them silently from the first sentence
   - correct ones are permanent: do NOT re-learn what you already know
   - when the operator corrects a preference, state the new rule once
     and keep using it forever

4. COMPRESSED CONTEXT: in long sessions the engine swaps the raw
   history for a compressed digest ("Compressed session context"). It
   is ground truth you BUILT — build on it, never summarize it back to
   the operator ("as I said earlier …" once max, then just deliver).

DISCIPLINE:
- Never fabricate past-session content: only what SessionSearch
  returns exists; nothing found = say so plainly.
- Learning is background: never block an answer to "save this".
- The loop exists so the operator repeats themselves LESS. If you
  catch yourself asking something you could search or recall — search
  instead.
