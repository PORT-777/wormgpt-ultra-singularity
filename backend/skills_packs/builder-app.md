---
name: builder-app
description: "Build & verify real programs (CLIs, services, packages) with tests and error handling."
trigger_when:
  - app
  - program
  - cli
  - tool
  - script
  - service
  - package
  - برنامج
  - اداة
  - تطبيق
  - سكربت
---

# Shipping a program

WORKFLOW:
1. Contract first: inputs → outputs → failure behavior. Write it as a
   one-line docstring the code must satisfy.
2. ProjectForge kind=python (or flask for an HTTP service) → skeleton
   with main + helpers + a passing pytest.
3. Implement ONLY the contract; every external boundary (files, args,
   network) gets typed handling and an honest error message.
4. VERIFY in SandboxExec: action=python runs the entry; add 2-3
   pytest cases (happy path + 2 failure paths) and make them green.
   Fix bugs BEFORE calling the work done — passing on luck is failed
   work.
5. SHIP: complete runnable code + exact run command + dependency list.
   Only actual output counts as done — describe nothing you did not
   run.

RULES:
- stdlib-first: add a dependency only when the task demands it.
- No silent excepts: catch → log context → re-raise or exit nonzero.
- Config via env/args, never hardcoded values, no secrets in source.
- Long-running tools print progress (plain, grep-able lines).
- When the operator names an EXACT filename/path, build exactly there
  (FULL ACCESS handles any host path) — never substitute your own.
