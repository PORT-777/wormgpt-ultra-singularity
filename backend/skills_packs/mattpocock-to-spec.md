---
name: mattpocock-to-spec
description: Synthesize the discussion into a written spec — problem, user stories, implementation+testing decisions, out-of-scope (from mattpocock)
trigger_when: [spec, سبيك, مواصفات, specification, وثيقة متطلبات, requirements doc, user stories, قصص المستخدم, PRD, صيغة المطلوب]
---

# To Spec — synthesize, don't re-interview

The conversation already happened. Turn it into a spec WITHOUT another
interview: synthesize what was discussed, explore the code for current
state, use the project's vocabulary and follow its conventions.

## Seams first

Before writing: sketch the SEAMS where the feature will be tested —
the points you can drive from outside. Prefer existing seams over new
ones; pick the HIGHEST seam possible (test the API handler, not the
internal helper). New seams? Propose at the highest point you can;
fewer seams across the codebase is better — the ideal is one. State
them explicitly in the spec.

## The template

**## Problem Statement** — the user's problem, from the user's
perspective (not the solution in disguise).

**## Solution** — the fix, still from the user's perspective.

**## User Stories** — a LONG numbered list, format: "As an <actor>, I
want <feature>, so that <benefit>". Extensive: cover every aspect
including edges, permissions, failure cases, and empty states.

**## Implementation Decisions** — modules built/modified and their
interfaces, technical clarifications from discussion, architectural
choices, schema changes, API contracts, key interactions. NO file
paths or code snippets — they rot fast. (Exception: a prototype
snippet that encodes a decision better than prose — inline just the
decision-rich part, noted as coming from a prototype.)

**## Testing Decisions** — what makes a good test here (external
behavior only, never implementation internals), which modules get
tested, and prior art: similar existing tests to imitate.

**## Out of Scope** — what this spec deliberately does NOT cover, so
scope creep has something to be measured against.

**## Further Notes** — anything else that shapes execution.

## Handoff

Save to the workspace (workspace/specs/<slug>.md) and reference it in
your answer. Then plan (writing-plans), ticket (to-tickets), execute
(executing-plans) — the spec is the source of truth every later step
is checked against, and every later deviation updates it first.
