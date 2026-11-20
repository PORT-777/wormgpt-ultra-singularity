---
name: superpowers-dispatching-domains
description: Split independent problem domains into focused isolated subtasks, then verify together (from superpowers dispatching-parallel-agents)
trigger_when: [عدة مشاكل, multiple failures, اكتر من خطأ, several bugs, اختبارات فاشلة, failing tests, subsystems, أنظمة متعددة, ملفات كتير, refactor متعدد]
---

# Dispatching Independent Domains

**Core principle:** one focused, isolated subtask per independent problem
domain. Never mix domains in one step; never let one subtask inherit the
mess of another.

## When

2+ problems that can be understood WITHOUT context from each other
(different files, subsystems, failure causes). NOT when failures are
related (fixing one may fix the others — investigate together first),
not when they share state/files.

## The pattern

1. **Group by domain.** "File A: approval flow", "File B: batch
   completion", "File C: abort logic" — three domains, three subtasks.
2. **Scope each subtask tight** — every subtask brief carries:
   - **Specific scope:** one file/subsystem only.
   - **Clear goal:** exactly what must pass/change.
   - **Constraints:** what NOT to touch ("do not change other code").
   - **Expected output:** summary of root cause + what was fixed.
3. **Ordering:** independent domains → any order works (plan them
   adjacent); related failures → sequential in one investigation chain.
4. **Contracts between subtasks:** a shared contract file
   `workspace/<name>.md` — each subtask reads/writes its promise there
   (simple interface that guarantees sequencing); the follow-up step
   starts by reading it and reporting PASS/FAIL with evidence.
5. **Integrate at the end:** read each subtask's result, verify no
   conflicts (same files touched?), then run the FULL suite once — the
   whole must be green together, not each piece alone. No branch without
   a known consumer.

## Anti-patterns (each = a wasted subtask)

- "Fix all the tests" (too broad → agent wanders)
- "Fix the race condition" with no error text (no context)
- No constraints (agent refactors everything it passes)
- "Fix it" with no expected output (you can't verify)

## Verification after integration

Each summary read → conflict check → full suite run (read the output) →
spot-check: isolated work can make systematic errors, so sample one fix
and re-verify it by hand.
