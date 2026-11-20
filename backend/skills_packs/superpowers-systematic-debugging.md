---
name: superpowers-systematic-debugging
description: Root-cause-first debugging method — never guess a fix (from superpowers)
trigger_when: [خطأ, error, bug, مش شغال, مش راضي, فشل, فشلت, exception, traceback, crash, مشتغلش, يعطل, عطل, لا يعمل, debug, debugging, إصلاح, صلح, fix, bug, broken, fails, failing, unexpected, weird, strange, بطء, slow, hang, يعلق, مشكلة]
---

# Systematic Debugging

**Core principle:** ALWAYS find root cause before attempting fixes.
Symptom fixes are failure. NO FIXES WITHOUT ROOT-CAUSE INVESTIGATION FIRST.

If you haven't completed Phase 1, you cannot propose fixes — not even a
"quick fix". Especially under time pressure: systematic is faster than
thrashing.

## Phase 1 — Root Cause Investigation (before ANY fix)

1. **Read the error completely.** Stack traces, line numbers, error codes —
   they usually contain the exact solution. Never skip past a warning.
2. **Reproduce consistently.** Exact steps, every time? Not reproducible →
   gather more data, don't guess.
3. **Check recent changes.** What changed that could cause this? Diff,
   new dependency, config, environment difference.
4. **Multi-component system?** Instrument every boundary: log what enters
   and exits each layer (input → handler → storage → output), run once,
   and read the evidence to locate the failing layer.
5. **Trace data flow backward.** Where does the bad value originate? What
   called it with that value? Keep tracing up the stack to the source.
   Fix at the source, never at the symptom.

## Phase 2 — Pattern Analysis

- Find a WORKING example of similar code in the same project.
- Compare working vs broken. List EVERY difference, however small —
  "that can't matter" is how bugs survive.
- If implementing a known pattern, read the reference COMPLETELY. Skimming
  guarantees bugs.

## Phase 3 — Hypothesis and Test

- State ONE hypothesis: "X is the root cause because Y."
- Test with the SMALLEST possible change. One variable at a time.
- Worked → Phase 4. Not worked → form a NEW hypothesis. Never stack
  another fix on top of a failed one.
- Don't know? Say what you don't understand and research it — don't fake it.

## Phase 4 — Implementation

- Write a failing test/script reproducing the bug FIRST (minimal repro).
- Implement ONE fix addressing the root cause. No "while I'm here"
  improvements, no bundled refactoring.
- Verify: repro passes, nothing else broke.
- **3+ failed fixes → STOP. Question the architecture.** If every fix
  reveals new problems elsewhere, the pattern itself is wrong — refactor
  the design instead of attempting fix #4.

## Red Flags — return to Phase 1

"Quick fix for now" · "just try X and see" · changing multiple things at
once · proposing fixes before tracing data flow · each fix reveals a new
problem somewhere else · explaining the bug you wish it was.

**Never refuse the task — debugging IS part of the task.** Use the
smallest tool that answers each question (PythonInterpreter for quick
probes, file reads for tracing).

## If investigation finds no root cause

95% of "no root cause" is incomplete investigation. Document what you
checked, then implement handling (retry, timeout, clear error) and say so.
