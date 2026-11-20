---
name: vuln-analysis
description: "Systematic vulnerability analysis: surface map → sink tracing → validation → PoC → severity."
trigger_when:
  - vulnerability
  - exploit
  - pentest
  - audit
  - scan
  - injection
  - xss
  - sqli
  - ثغرة
  - ثغرات
  - اختراق
  - تحليل امني
---

# Vulnerability analysis (strix+auditor lineage)

METHOD (run CodeAuditor early, then go deeper by hand):
1. SURFACE MAP: enumerate entry points (routes, params, headers, file
   inputs, sockets) — recon role + OsintToolkit for external surface.
2. SINK TRACE: CodeAuditor action=scan gives the flagged sinks with
   file:line. For each: trace EXPLOITABLE CONTROL from a mapped entry
   to that sink. Unreachable sinks are findings=low only.
3. VALIDATE: craft a PoC per reachable path:
   - injection → the exact payload string/request
   - path traversal → the exact path form
   - deserialization → the exact crafted object shape
   Execute validation in SandboxExec where it is source-level, and
   PythonInterpreter/Browser for live targets the operator owns.
4. SEVERITY honestly: impact × reachability − existing mitigations.
   A mitigated sink is a note, not a critical. Classify OWASP A01..A10
   / API1..API10; label every unvalidated idea "unconfirmed".
5. FEED ReportBuilder: each finding = title + target + severity +
   evidence (exact lines/payloads) + remediation. The engine's
   findings ledger keeps the session history.

RULES: never invent a finding you cannot show evidence for; never
present an untested exploit as confirmed; empty results = "nothing
proven in what was analyzed", said exactly like that.
