---
name: architecture-survey
description: Survey a codebase for deep-module opportunities and hand the operator ranked candidates — mattpocock improve-codebase-architecture methodology
trigger_when:
  - "improve architecture"
  - "سطح معمارية"
  - "refactor survey"
  - "codebase design"
always: false
---

# Architecture Survey (mattpocock improve-codebase-architecture)

A survey, not a rescue. Find where the code hides behavior behind
wide interfaces, and hand the operator ranked candidates.

**Protocol:**
1. Walk the target tree (files, sizes, imports) — build the map
   silently; do not dump file lists at the operator.
2. Score candidates: a module is "shallow" when many small functions
   leak internals (flags, paths, formats) through its interface.
3. Deliver AT MOST 5 candidates, each as:
   - [N/10] file -> what to deepen, one-line benefit, one-line risk.
4. Ask which to implement. On pick — implement with tests, small
   diffs, one step at a time.

**Rules:** never rewrite architecture unprompted; never propose
framework swaps; keep behavior identical unless the operator asked
for a behavior change.
