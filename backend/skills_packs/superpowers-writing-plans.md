---
name: superpowers-writing-plans
description: Plan multi-step work as bite-sized verifiable tasks before touching code (from superpowers)
trigger_when: [خطة, plan, مشروع, project, معماري, architecture, خطوات, steps, multi-step, بناء, build system, منظومة, refactor كبير, migration, مهاجرة, pipeline]
---

# Writing Plans

Write implementation plans for an engineer who has NOT seen this
codebase. What they cannot know is what you DECIDED: which files, which
names and signatures, which values, which tests prove each task.
Document those. DRY. YAGNI. TDD. Frequent commits.

## Before the plan

**Scope check:** multiple independent subsystems → one plan per subsystem;
each must produce working, testable software alone.

**File structure first:** map which files are created/modified and each
one's single responsibility. Files that change together live together.
In existing projects, follow the project's established patterns.

## Task right-sizing

A task = smallest unit with its own test cycle that a reviewer could
approve or reject independently. Fold setup/config into the task that
needs them. Each task ends with an independently testable deliverable.

## Step granularity

Each step is ONE action with a checkable result:
- "write the failing test" → step
- "run it, confirm it fails" → step
- "implement minimal code" → step
- "run tests, confirm pass" → step
- "commit" → step

A step is done when the implementer can write exactly one reasonable
thing from it. Order steps so the system stays WORKING after every step
(tracer bullet). Present the plan in your answer for huge tasks, then
execute — never stall waiting for permission to proceed.

A plan longer than the code it describes has written the code instead —
replace bodies with signatures + test names.

## Plan header (always)

```
# <Feature> Implementation Plan
Goal: <one sentence>
Architecture: <2-3 sentences>
Constraints: <exact versions/limits, one line each>
```

## Task block

```
### Task N: <Component>
Files: create/modify/test exact paths
Produces/Consumes: exact signatures neighboring tasks rely on
- [ ] Step 1: write failing test <as code, exact assertions>
- [ ] Step 2: run <command> — expected FAIL with <reason>
- [ ] Step 3: implement <exact signature, file>
- [ ] Step 4: run <command> — expected PASS
- [ ] Step 5: commit
```

## Self-review (fix inline, then proceed)

1. Spec coverage: every requirement → a task?
2. Step scan: every step = one unambiguous action? (no "TBD", no
   "handle edge cases", no bodies the tests already determine)
3. Type consistency: names/signatures match across tasks?
4. Proportion: plan shorter than the code it describes.

Then execute with the executing-plans discipline.
