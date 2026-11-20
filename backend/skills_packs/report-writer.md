---
name: report-writer
description: "Professional findings report: exec summary, methodology, severity-ranked findings with PoC + remediation."
trigger_when:
  - report
  - findings
  - document
  - summary
  - تقرير
  - تقارير
  - توثيق
---

# Reports that get read

STRUCTURE (ReportBuilder compiles it; write prose around it):
1. EXECUTIVE SUMMARY — 5-8 lines: what was assessed, the 3 highest
   risks with business impact, the fastest win. No jargon here.
2. SCOPE & METHODOLOGY — what was tested, what was NOT, tools used
   (generic names), time window. Honesty about gaps = credibility.
3. FINDINGS (severity-ranked): for each
   - Title + [severity] + CWE/OWASP + affected target
   - EVIDENCE: exact request/lines/output that proved it
   - PoC: reproducible steps (the payload, the command)
   - IMPACT in operator terms
   - REMEDIATION: the concrete code/config change, not "fix input"
4. APPENDIX: full tool output tables, timeline of testing.

DISCIPLINE:
- One fact per sentence; every number traceable to a tool output.
- Duplicate/merged findings merged (one root cause = one finding with
  all instances listed).
- No fear language, no padding: severity already says it.
- Say "unconfirmed" instead of burying doubt in adjectives.
- Sources: the findings ledger (findings.py) + CodeAuditor scan +
  sandbox outputs — cite run evidence, never memory-only claims.
