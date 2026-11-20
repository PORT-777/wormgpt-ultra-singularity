---
name: mattpocock-diagnosing-bugs
description: Hard-bug discipline — build a TIGHT feedback loop first (red on this bug), minimise, ranked falsifiable hypotheses, tagged instrumentation (from mattpocock)
trigger_when: [diagnose, تشخيص, hard bug, باج عويص, مشكلة صعبة, intermittent, متقطع, أحيانا بيحصل, flaky, regression, تراجع, بطء مفاجئ, slow, performance, أداء, reproduce, مش بيتكرر]
---

# Diagnosing Hard Bugs — the feedback loop comes FIRST

Skip phases only with explicit justification. The difference between
thrashing and debugging: a TIGHT pass/fail signal for THIS bug.

## Phase 1 — Build a loop that goes RED

**This is the skill; everything else is mechanical.** With a loop that
goes red on this bug, bisection/hypotheses/instrumentation all just
consume it. Without one, staring at code saves nothing. Be aggressive,
be creative, refuse to give up — spend disproportionate effort here.

Ways to build one (roughly in this order):
1. Failing test at whatever seam reaches the bug (unit/integration/e2e).
2. Curl/HTTP script against the running server, asserting the symptom.
3. CLI invocation with a fixture input, diff stdout vs known-good.
4. Headless browser driving the UI; assert on DOM/console/network.
5. Replay a captured trace (saved request/payload/log) in isolation.
6. Throwaway harness: minimal subset of the system exercising the path.
7. Property/fuzz loop: 1000 random inputs, hunt the failure mode.
8. Bisection harness: automate "boot at state X, check" (git bisect).
9. Differential: same input through old vs new version, diff outputs.

**Tighten the loop** — treat it as a product: faster (cache setup,
narrow scope), sharper (assert the exact symptom, not "didn't crash"),
deterministic (pin time, seed RNG, freeze network).

**Non-deterministic bug?** The goal is a higher reproduction RATE, not
a clean repro: loop the trigger 100x, add stress, narrow timing
windows. 50%-flake is debuggable; 1% is not.

Phase 1 is DONE when you can name ONE command — already run at least
once, show its output — that is: red-capable (asserts the user's exact
symptom), deterministic, fast (seconds), runnable unattended. Reading
code to build a theory before this command exists = the exact failure
this discipline prevents. Genuinely cannot build one? Say so, list
what you tried, and ask for the environment/artifact that reproduces
it — never hypothesize without a loop.

## Phase 2 — Reproduce + minimise

Run the loop; watch it go red on the USER's failure mode, not a nearby
different one. Then shrink: cut inputs/callers/steps ONE at a time,
re-running after each cut, keeping only what's load-bearing. A minimal
repro shrinks the hypothesis space and becomes the regression test.

## Phase 3 — Ranked falsifiable hypotheses

Generate 3-5 BEFORE testing any (a single hypothesis anchors you).
Each must be falsifiable with a prediction: "If X is the cause, then
changing Y kills the bug / changing Z worsens it." No prediction = a
vibe; discard or sharpen it.

## Phase 4 — Instrument

One variable at a time; each probe maps to one Phase-3 prediction.
Debugger/REPL inspection first (one breakpoint beats ten logs);
targeted logs at hypothesis-distinguishing boundaries second; never
"log everything and grep". Tag every debug log `DEBUG-<tag>` — cleanup
becomes a single grep. Perf regression? Logs are usually wrong:
baseline measurement first (timing harness/profiler), then bisect.
Measure first, fix second.

## Phase 5 — Fix + regression test

Regression test BEFORE the fix — but only at a CORRECT seam (one that
exercises the real bug pattern as it occurs at the call site). No
correct seam exists? That itself is a finding: the architecture cannot
lock this bug down — flag it. Then: minimised repro → failing test →
watch it fail → fix → watch it pass → re-run the Phase-1 loop against
the ORIGINAL un-minimised scenario.

## Phase 6 — Cleanup

- repro no longer fires (re-run the Phase-1 loop)
- regression test green (or missing-seam documented)
- all `DEBUG-` tags removed (grep the prefix)
- throwaway harnesses deleted
- the winning hypothesis recorded in the commit/report — the next
  debugger learns from it.
