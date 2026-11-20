---
name: superpowers-debugging-techniques
description: Advanced debugging techniques — backward root-cause tracing, defense-in-depth validation, condition-based waiting (from superpowers)
trigger_when: [تتبع, trace, السبب الجذري, root cause, مكالمة, call stack, يظهر بعيد, deep in stack, من أين جاء, where did, طبقات, layers, تحقق, validation, مدخلات, input validation, flaky, متقطع, مهلة, timeout, sleep, انتظار, waiting, polling, race, توقيت, timing, حارس, guard]
---

# Debugging Techniques (tracing · layers · waiting)

## 1 — Backward Root-Cause Tracing

Bugs often manifest DEEP in the call stack. The instinct is to fix where
the error appears — that's treating the symptom.

**Trace backward through the call chain to the original trigger, then fix
at the source.**

- **Observe** the symptom exactly (error, file, line, value).
- **Instrument every boundary**: log what enters/exits each layer
  (input → handler → storage → output), run once, read the evidence to
  find the first layer where data goes bad.
- **Trace up the stack**: which caller passed that bad value? Repeat
  until you reach the ORIGINAL source (wrong flag, wrong path, wrong
  config at entry).
- Dead end (can't trace)? Fix the symptom minimally AND leave an
  instrumented probe at the boundary for next time.
- **BEST:** fix at source AND add defense-in-depth (below).

Use when: error happens deep in execution, long call chain, unclear
where invalid data originated.

## 2 — Defense-in-Depth Validation

After fixing a data bug, one validation point is NOT enough — other code
paths, refactoring, or mocks can bypass it.

**Validate at EVERY layer data passes through. Goal: make the bug
structurally impossible, not "fixed this time".**

1. **Entry point** — reject obviously invalid input at the API/command
   boundary (empty, missing, wrong type, nonexistent path).
2. **Business logic** — domain rules near the code that depends on them
   (state transitions, invariants, relationship checks).
3. **Environment guard** — refuse to run in the wrong context (missing
   env var, wrong cwd, wrong version) with a CLEAR error naming the fix.
4. **Debug logging** — log suspicious-but-not-fatal data so the next
   investigation starts with evidence instead of guesswork.

Different layers catch different cases: entry catches most, business
catches edge cases, guards prevent context dangers, logs help when the
rest fail.

## 3 — Condition-Based Waiting

Arbitrary delays (`sleep(2)`, `setTimeout(50)`) create race conditions:
pass on fast machines, fail under load.

**Wait for the ACTUAL condition you care about, not a guess about how
long it takes.**

```python
# BAD: sleep and hope
time.sleep(2); result = poll_server()
# GOOD: poll until the real condition, with a timeout
deadline = time.time() + 10
while time.time() < deadline:
    if condition_met(): break
    time.sleep(0.01)          # short poll interval
else:
    raise TimeoutError(f"condition not met in 10s: {what_we_waited_for}")
```

- Poll with a SHORT interval (10ms) and a GENEROUS timeout.
- On timeout, fail with a message saying WHAT condition never became
  true — never a bare timeout.
- Testing actual timing behavior (debounce/throttle)? That's the one
  exception — and document WHY the arbitrary timeout exists.

Flaky test or intermittent failure? Suspect a sleep-vs-condition race
before anything else.
