---
name: strix-whitebox-review
description: White-box code review like strix find-security-vulnerabilities-in-code — model routes/sinks/authz, then PoC-validate; findings with file+line, unproven labeled
trigger_when:
  - "code review"
  - "مراجعة كود"
  - "white box"
  - "audit code"
  - "سكان كود"
  - "vulnerabilities in code"
always: false
---

# Strix White-box Code Review (usestrix/strix methodology)

Read the source to build a model of routes, sinks, and authorization
checks, THEN attempt real exploitation. Output = a short list of
proven issues with file+line, not hundreds of "potential" hits.

**1. Build the model first:** entry points (routes, handlers, RPCs),
dangerous sinks (query builders, exec, file IO, deserialization,
templates, redirects), the authorization model (who checks what,
where tenancy is derived), trust boundaries (which inputs are
attacker-controlled). Tenancy and trust boundaries cannot be inferred
reliably — ask the operator when unclear.

**2. Trace, don't pattern-match:** follow attacker input from entry to
sink through the actual data flow. A grep hit without a reachable
path is not a finding.

**3. Validate:** write and run the PoC (Python sandbox / interpreter)
against the real behavior when possible. If nothing is running,
label static findings as UNCONFIRMED — the difference between "this
looks unsafe" and a validated finding.

**4. Report with precision:** file + line + the exploit so the fix is
obvious. Record in the findings ledger (title/severity/evidence/
poc/remediation).

**5. Completeness honesty:** this is exploit-validated review, not an
exhaustive inventory — known-CVE dependencies and committed secrets
need scanners; say what the review did not cover.

**6. Hand off to remediation:** patch the root cause (the shared authz
helper, not the one route), then re-verify the exploit no longer
works.
