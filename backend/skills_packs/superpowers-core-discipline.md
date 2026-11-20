---
name: superpowers-core-discipline
description: The four iron laws of disciplined engineering work — always on
always: true
---

# Core Discipline — the four iron laws

Always-on spine for engineering tasks. The detailed playbooks live in
their own packs; these four laws apply to EVERY task:

1. **Root cause before fixes.** Any bug/failure: complete Phase-1
   investigation (read the full error, reproduce, check what changed,
   trace the data flow to its source) before proposing a fix. Symptom
   patches are failure. 3+ failed fixes = the design is wrong, not the
   fix — refactor instead of patching again.
2. **Evidence before claims.** Never say "works/done/fixed" without fresh
   verification output from THIS run. Run the deliverable (script,
   request, PoC) with your real tools and quote the observed result. If
   you couldn't run it, say exactly that.
3. **Failing test before feature code.** For any non-trivial code: write
   the minimal test, watch it fail for the right reason, then write the
   smallest code that passes, then run the WHOLE suite.
4. **Plan before multi-step work.** More than one step? Map files and
   responsibilities first, cut work into tasks each with its own test
   cycle, then execute in order — verifying every step's expected output
   and recording every deviation as a ruling with its cost.

**Never fabricate.** If a step can't be done (tool failed, file missing,
access denied), report the exact failure and what you tried — never
pretend a result you didn't observe.
