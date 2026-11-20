---
name: program-analysis
description: "Precise program analysis: static sources, dynamic behavior, binary triage — always with evidence."
trigger_when:
  - analyze
  - analyst
  - reverse
  - decompile
  - static
  - binary
  - behavior
  - تحليل
  - حلل
  - بيعمل ايه
  - بعمل ايه
  - عكسي
  - ثنائي
  - inary
---

# Program analysis (precise, evidence-first)

STATIC (source available):
- CodeAuditor action=scan (py/c/cpp/js TS php) → sink list with CWE.
  metrics=true adds LOC + function counts for the report.
- Read imports/entrypoints MANUALLY for the logic map the tools miss.

DYNAMIC:
- SandboxExec runs the program isolated; capture real behavior.
- Profile inputs: does it read configs? phones home? (strings/netstat
  via SystemCommander in FULL ACCESS show the real answer.)

BINARY (.exe/.dll) — no source:
- UniversalFileManager action=hex → header/magic/section map.
- AntiTamperSentinel: pe_header, import_table, section_integrity,
  diff_baseline against the operator's trusted build.
- ReverseEngineeringAnalyzer for "what does this snippet do".
- Strings hunt via shell (`findstr` / python scan in sandbox).

DISCIPLINE:
- Every claim = its evidence (file:line, hexdump line, API call).
- Label derivations: "import table shows X" ≠ "it does X" — behavior
  conclusions need dynamic capture; say which you have.
- Build ONE verdict sentence per finding, then the evidence chain under
  it. Precision over volume: 10 confirmed beats 40 vague.
- Unreadable/packed → say so and prescribe the unpack step (needs the
  operator's FULL ACCESS tooling), no guessing.
