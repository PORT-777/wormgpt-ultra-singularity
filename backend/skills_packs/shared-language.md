---
name: shared-language
description: Build and reuse the operator's domain glossary so every reply uses the same short consistent terms — mattpocock domain-modeling methodology
trigger_when:
  - "glossary"
  - "المصطلحات"
  - "domain language"
  - "اسمك المشاريع كده"
always: false
---

# Shared Language (mattpocock domain-modeling methodology)

One shared vocabulary = shorter answers, consistent naming, less
thinking tokens.

**Protocol:**
1. When the operator names a thing (a tool, a path, a project, a
   habit), record ONE memory line mapping their term to the technical
   substrate: e.g. "المشروع = backend/api/main.py on port 7777".
2. Reuse THEIR term in every later reply instead of re-explaining.
3. If two terms collide (same name, different meanings), surface the
   collision once and pick one with the operator.
4. Keep each glossary line under 25 words; store via memory so it
   survives sessions.

**Why:** the codebase, files and replies stay navigable; the engine
spends its small budget on engineering, not on re-decoding jargon.
