---
name: ponytail-ladder
description: "Reuse-first ladder: before writing ANY code, run down the ladder — exists? → in codebase → stdlib → platform → dependency → one line → minimal. Debt markers only, never silent shortcuts."
trigger_when:
  - implementation
  - new tool
  - write code
  - build
  - implement
  - feature
  - shortcut
  - TODO
  - dependency
  - rebuild
  - again
  - duplicate
  - اعمل
  - اكتب كود
  - ميزة
  - اداة
  - من جديد
  - بناء
  - تنفيز
  - سريع
---

# The reuse-first ladder (ponytail port)

Before writing a single line of NEW code, walk DOWN this ladder. Stop
at the first rung that holds — that rung IS the answer.

1. ALREADY DONE? — a built feature, a delivered answer, a tool you
   already wrote this session. If yes: reuse it, quote it, extend it.
   Never rebuild silently.
2. IN THE CODEBASE? — search (grep/glob) for an existing function,
   tool, route, pack that does this or something close. Our backend has
   100+ packs and dozens of tools: odds are it exists.
3. STANDARD LIBRARY? — Python stdlib first (urllib, pathlib, json,
   sqlite3, re, subprocess, threading...). No install, no attack
   surface, no version drift.
4. PLATFORM? — does Windows/OWS/PowerShell/the OS already provide it
   (scheduled tasks, CertUtil, BITS, curl, ssh)? Use it.
5. DEPENDENCY? — only if rungs 1-4 fail. Justify in one sentence why
   why. Prefer small, boring, maintained packages.
6. ONE LINE? — can the whole need collapse into one shell/Python line?
   Then that IS the implementation.
7. MINIMAL + TEST — write the minimum that satisfies the exact ask,
   then verify it works. Nothing else.

HARD RULES — the ladder never licenses cutting these:
- Validation of inputs: always kept.
- Security checks and guards: always kept (never "temporarily off").
- Accessibility + RTL on anything user facing: always kept.
- Persistence where the ask says persistent: always kept.

DEBT IS VISIBLE OR IT DOESN'T EXIST:
- If you consciously skip a rung or ship weaker than the ask, you
  MUST write the marker comment in the artifact:
  `# shortcut: <one-line reason>`
  Plus TODO:/FIXME:/HACK: for ordinary deferrals.
- DebtLedger tool harvests these into workspace/debt_ledger.md.
  A finished build with unwritten debt = unfinished build.
