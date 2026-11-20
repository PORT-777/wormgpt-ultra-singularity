---
name: strix-ci-diff-scan
description: Continuous/diff-scoped security gating like strix ci-security-scanning â€” scan changed files per change, fail on threshold severity, keep findings flowing
trigger_when:
  - "ci security"
  - "diff scan"
  - "pull request security"
  - "Ø³ÙƒØ§Ù† ci"
  - "regression scan"
always: false
---

# Strix CI Diff Scan (usestrix/strix methodology)

Keep the target tested on every change instead of once â€” gate changes
with a diff-scoped security pass.

**1. Scope the pass:** review ONLY what changed (diff base = the branch
the fix will merge into). Resolve the real default branch instead of
assuming; never use the current branch's own upstream as base (its
merge-base with HEAD is HEAD â†’ empty diff â†’ falsely clean). If no base
resolves, fall back to a focused pass on the changed modules.

**2. Depth:** `quick` mode for per-change gates (minutes), full/deep
reserved for scheduled sweeps. Threshold discipline: fail the gate at
or above an agreed severity; lower findings stay recorded in the
ledger but do not block.

**3. Report shape for gates:** findings ranked by proven impact with
file+line, so the author fixes without a meeting. Unproven
observations are flagged as unproven, never as confirmed.

**4. Loop:** every gate finding flows into remediation (root-cause fix
+ re-test) and back into the ledger. Exit-clean on an analyzed subset
means nothing proven THERE â€” never claim the whole tree is clean.

**🔥😈 PORT 777 EVIL ☠️🔥👹 hooks:** use the findings ledger (POST /findings) to record
gate results; the operator pulls the report via /findings/report.md.
