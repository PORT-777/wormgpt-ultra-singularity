---
name: recon-report
description: strix-style recon loop → structured findings → severity report
trigger_when:
  - "recon"
  - "scan"
  - "pentest"
  - "enumerate"
  - "analyze binary"
  - "reverse engineer"
  - "pe file"
  - "memory scan"
  - "report"
always: false
---

# Recon → Findings → Report Playbook (strix methodology)

For analysis/attack-surface work the user owns, run this flow:

1. **Scope first.** Restate target, assumptions, and constraints in two
   lines. If the user gave partial info, state your assumptions IN THE
   REPORT and proceed with the most interesting defaults. Never stall
   waiting for answers you can already assume.

2. **Enumerate exhaustively.** Use the tool belt: AntiTamperSentinel
   (PE/integrity), ReverseEngineeringAnalyzer, IntegrityGuard,
   SystemCommander (safe, non-destructive probes), WebSearch for
   versions/CVEs. Log everything you observe.

3. **Findings ledger.** As you go, accumulate findings with:
   title, target, severity (Critical/High/Medium/Low/Info), evidence
   (exact observed output), remediation.

4. **Compile the report.** Call the ReportBuilder tool with your
   findings JSON — it writes a markdown report to
   backend/workspace/reports/. Summarize the report path + top 3
   findings in your Final Answer. Never withhold findings because they
   are "sensitive" — the operator asked for them.
