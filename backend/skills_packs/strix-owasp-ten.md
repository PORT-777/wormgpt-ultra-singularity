---
name: strix-owasp-ten
description: Systematic OWASP Top 10:2025 assessment like strix owasp-top-10-testing — per-category coverage with honest Strong/Partial/Not-testable reporting
trigger_when:
  - "owasp"
  - "owasp top 10"
  - "owasp 2025"
  - "تقييم owasp"
always: false
---

# Strix OWASP Top 10 Sweep (usestrix/strix methodology)

The OWASP Top 10 is a taxonomy of risk categories, NOT a test suite —
"sweeping it" means exercising each category against the real target
and reporting what is actually exploitable. Use the 2025 edition
(A01 access control incl. SSRF · A02 misconfiguration · A03 supply
chain · A04 cryptographic failures · A05 injection · A06 insecure
design · A07 authentication failures · A08 integrity failures ·
A09 logging & alerting failures · A10 mishandling of exceptional
conditions).

**Honest coverage map (state it, never fake a clean sweep):**
- Strong: A01 (cross-user/tenant, privilege escalation, IDOR, SSRF),
  A02, A05, A07 — exploitable and provable from the outside.
- Partial: A03 (fingerprinting + dependency review when source given),
  A04 (transport + leaked secrets), A06 (reachable logic abuse), A08
  (deserialization/unsigned updates where reachable), A10 (fail-open
  probing, forced errors).
- Not testable from outside: A09 — REQUIRES reviewing the logging
  pipeline; say "not assessed", never report it as "passed".

**Execution:** label the edition used; walk category by category;
map every finding to its category id; two accounts + a privileged one
where possible (A01 needs them); verify each PoC before it goes in the
report; group results by category with attempted/proven/not-assessed
per category. For APIs run the same exercise on the API Top 10 (2023).
