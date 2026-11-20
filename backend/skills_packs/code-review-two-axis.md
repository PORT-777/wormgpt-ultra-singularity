---
name: code-review-two-axis
description: parallel review axes — standards vs spec (mattpocock code-review)
trigger_when:
  - "review"
  - "audit"
  - "diff"
  - "improve"
  - "quality"
always: false
---

# Two-Axis Code Review Playbook

When reviewing code/diffs, run TWO independent passes and merge findings:

**Axis 1 — Standards.** Correctness bugs, security footguns, edge
cases, naming, dead code, structure. Severity-tag each finding.

**Axis 2 — Spec.** Does the code do what the requester actually asked?
Missing requirements? Silent scope creep? Cross-check against the
original request text, not memory.

Output shape (markdown, findings only — no refusal language):
- `CRITICAL:` must fix, broken or dangerous right now
- `HIGH:`  likely to bite in production
- `MEDIUM`: style/design debt worth paying
- `INFO`:  nits and preferences
Then a one-paragraph verdict. Every finding cites file/line evidence.
