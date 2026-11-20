---
name: strix-remediation
description: Fix security findings like strix fix-security-vulnerabilities — triage by severity, patch the root cause, re-verify each exploit is dead
trigger_when:
  - "fix vulnerability"
  - "اصلاح ثغرة"
  - "remediate"
  - "patch security"
  - "سد الثغرات"
always: false
---

# Strix Remediation (usestrix/strix methodology)

Turn validated findings into minimal, correct fixes — and PROVE they
work by re-testing.

**1. Triage:** order by severity critical → high → medium → low.
Findings were validated with a working PoC — do not dismiss one as a
false positive without replaying the PoC yourself.

**2. Fix per finding:**
1. Reproduce with the recorded PoC when feasible.
2. Fix the ROOT CAUSE, not the payload: parameterize every query
   instead of blocking one string; enforce authorization in the shared
   handler instead of hiding one endpoint.
3. Prefer the framework's built-in defense (ORM parameterization,
   template auto-escaping, CSRF middleware, centralized authz) over
   ad-hoc sanitization.
4. Keep the diff minimal and match the repo's existing patterns.

**Class playbook:** injection → parameterize/escape at the sink;
IDOR/access control → object-level authz checks; SSRF → allowlist +
block internal ranges; XSS → context-aware output encoding + CSP;
secrets exposure → rotate the secret AND remove from code/history;
auth issues → fix the SERVER-side check, never client-side.

**3. Verify by re-testing:** re-run the scoped check (diff-scope on
changed files) or re-run the original PoC as ground truth; run the
project's own tests to prove behavior is intact. Exit-clean on a
truncated re-scan is NOT proof — confirm coverage.

**4. Report:** per finding — severity, root cause, fix applied
(file:line), verification result. Never include live secrets; if one
leaked, state that rotation is required.
