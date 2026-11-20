---
name: mattpocock-to-tickets
description: Break a plan/spec into tracer-bullet vertical slices with blocking edges; expand-contract for wide refactors; wayfinder for huge work (from mattpocock)
trigger_when: [tickets, تذاكر, تقسيم, شرائح, slices, tracer bullet, مهام مصغرة, تفكيك, subtasks, مهام فرعية, خطة ضخمة, مشروع ضخم, blocker, يعتمد على]
---

# To Tickets — vertical slices with blocking edges

Break work into TRACER-BULLET tickets. Each slice cuts a narrow but
COMPLETE path through every layer (schema → API → UI → tests):
vertical, never horizontal — a "schema-only" slice is not a ticket.

**A finished slice is demoable or verifiable on its own**, and sized
to fit one working session. Prefactoring ("make the change easy, then
make the easy change") comes first, as its own ticket.

## Blocking edges

Each ticket declares which tickets BLOCK it (must finish first). No
blockers = can start immediately. Work the FRONTIER: any ticket whose
blockers are all done. A linear chain = top to bottom.

## Wide refactors are the exception: expand–contract

A WIDE refactor is one mechanical change (rename a column, retype a
shared symbol) whose blast radius fans across the codebase — no
vertical slice can land green. Never force it into a tracer bullet:

1. **Expand**: add the new form BESIDE the old; nothing breaks.
2. **Migrate** call sites in batches sized by blast radius (per
   package/directory) — each batch its own ticket blocked by the
   expand. CI stays green batch to batch: the old form still exists.
3. **Contract**: delete the old form once no caller remains — one
   ticket blocked by every migrate batch.

Even the batches can't stay green alone? Keep the sequence but share
an integration branch; green is promised only at a final
integrate-and-verify ticket.

## Ticket file (one file each, numbered blockers-first)

```
# <NN>: <title>
What to build: <end-to-end behavior, user's perspective — not a
layer-by-layer implementation list>
Blocked by: <numbers/titles, or "None (can start immediately)">
- [ ] acceptance criterion 1
- [ ] acceptance criterion 2
```

Write them to workspace/tickets/<feature-slug>/ in dependency order.
Avoid file paths and snippets in ticket bodies (they rot); a prototype
snippet that encodes a decision is the exception.

Then EXECUTE with executing-plans discipline, TDD per slice, one full
verification pass at the end.

## Huge work — the wayfinder pattern

Work too big for one session arrives wrapped in fog: chart a MAP, not
a mega-plan.

- **Name the destination** first — the spec/decision/change this
  effort is finding its way to. The destination fixes the scope; every
  ticket shapes to it.
- **Decision tickets, not build slices** (planning, not doing): each
  ticket is a QUESTION whose resolution is a decision — typed
  research / prototype / discussion / task. One ticket per session's
  worth of work; resolve one at a time and record the answer.
- **Fog of war**: don't pre-slice what you can't specify yet. Tickets
  only when you can state the question sharply NOW; everything dimmer
  goes in a "not yet specified" section and graduates to tickets as
  the frontier clears it.
- **Out of scope** is its own section — ruled out by the destination,
  never graduated. Closing a ticket as out-of-scope is a scoping act,
  not a step on the route.
- The map is an INDEX: one line per resolved decision, detail lives in
  its ticket. Refer to tickets by NAME, never bare numbers.
