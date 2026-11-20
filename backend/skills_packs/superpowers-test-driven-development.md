---
name: superpowers-test-driven-development
description: Red-Green-Refactor — no production code without a failing test first (from superpowers)
trigger_when: [كود, code, برمج, function, دالة, سكريبت, script, feature, ميزة, implement, اكتب برنامج, وحدة, unit, test, اختبار, تيست, refactor, class, api, endpoint, utility, مكتبة]
---

# Test-Driven Development (TDD)

**Core principle:** Write the test first. Watch it fail. Write minimal
code to pass. If you didn't watch the test fail, you don't know if it
tests the right thing.

**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.** Code written before
the test? Delete it and start from the test. Keeping it "as reference" is
testing-after in disguise.

## The Cycle

**RED — write ONE minimal failing test.**
One behavior, a clear name, real code (no mocks unless unavoidable).
Run it. Confirm it FAILS because the feature is missing — not a typo, not
an import error. A test that passes immediately tests existing behavior:
fix the test.

**GREEN — write the simplest code that passes.**
No extra features, no "improvements" beyond the test. YAGNI. Run the
test: pass. Then run the WHOLE suite (the project's command, not just
your file) — a green file is not a green suite; report any failure by
name, including ones you didn't cause.

**REFACTOR — only after green.**
Remove duplication, improve names, extract helpers. Keep tests green.
No behavior changes. Then next failing test.

## Good tests

| Quality | Good | Bad |
|---|---|---|
| Minimal | one behavior per test | `validates email and domain and whitespace` |
| Clear | name describes behavior | `test1` |
| Real | asserts actual output | asserts mock call counts |

## Rationalizations (all mean: delete and start over)

- "Too simple to test" → simple code breaks; the test costs 30 seconds.
- "I'll test after" → tests-after pass immediately and prove nothing.
- "Already manually tested" → manual proves nothing you can re-run.
- "TDD slows me down" → it's faster than debugging production.
- "It's just this once" → that's the rationalization talking.

## Bug found in existing code?

Write a failing test that reproduces it FIRST, then fix. Never fix bugs
without a test — the test is what proves the bug was real and is now gone.

## Writing GOOD tests

- **Name the break.** Before writing the body: what production change
  would make this test FAIL? Can't name one → it's decoration. The
  failure must be a BUG, not an intentional decision (change detectors
  fire on redesign and sleep through real bugs — don't assert
  `MAX_RETRIES == 5`; assert "a failing call is retried and the 6th
  attempt never happens").
- **Derive expectations by hand.** Literals and hand-checked fixtures —
  never computed by the code under test or its helpers (that passes
  whatever the code does — the mirror-assertion trap).
- **Behavior, not text.** Run the script/artifact and assert outputs,
  side effects, exit codes — never grep the source for a line.
- **Your boundaries, not the framework.** Test the contract YOUR code
  makes (route registered, payload produced, query emitted) — upstream
  mechanics are their maintainers' tests.
- **Mocks earn no assertions.** Assert the REAL component. Mock only
  the slow/external layer (learn its side effects first), mirror the
  complete real data structure, and if mock setup outgrows the test →
  switch to an integration test with real components.
- **Mutation check at the end:** mentally break the code (wrong
  constant, wrong branch, missing state change, missing validation of
  zero/empty/malformed) — at least one test must fail for EACH. A
  mutation nothing catches = unprotected behavior.

## In this engine

- Tests live in the workspace as pytest files, run via PythonInterpreter.
- One vertical slice at a time — never big-bang.
- Hard to write the test? That's a design smell: simplify the interface
  before forcing the test.
- The Final Answer ends with: tests written, pass/fail counts, exact
  commands to re-run.
