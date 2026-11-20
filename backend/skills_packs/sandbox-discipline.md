---
name: sandbox-discipline
description: "Build→run→fix loop inside SandboxExec before anything ships."
trigger_when:
  - run
  - test
  - sandbox
  - verify
  - execute
  - تشغيل
  - تجربة
  - تنفيذ
---

# Sandbox discipline (build → run → fix → ship)

Every generated PROGRAM/CODE answer passes through SandboxExec before
it is called done:

1. BUILD: write the real code (UniversalFileManager or ProjectForge).
2. RUN: SandboxExec action=python (or action=shell for cmd pipelines).
   Each call = fresh isolated dir + scrubbed env + timeout. Pass extra
   files via `files: {}`; artifacts survive inside the run dir.
3. READ the real output. `[exit code: N]` nonzero or a traceback =
   NOT done: fix ONE root cause (reflection discipline), rerun.
4. KEEP: action=keep path=<artifact> copies verified artifacts into
   workspace/sandbox_out (so cleanup cannot eat the deliverable).
5. SHIP: the Final Answer contains the VERIFIED artifact or its kept
   path + the sandbox evidence (what ran, what it printed).

RULES:
- NEVER claim "should work". The sandbox says it, or you say honestly
  it was not run.
- No runs → no "verified" wording, period.
- Timeouts: 90s default; raise consciously (up to 600s) only for
  slow work (compiles, installs).
- The sandbox is isolated from the engine's secrets by design — if a
  run needs the operator's trust, that is what FULL ACCESS is for.
