---
name: superpowers-executing-plans
description: Execute a plan task-by-task with per-step verification and honest records (from superpowers)
trigger_when: [نفذ, execute, ابدأ التنفيذ, طبق الخطة, implement the plan, follow the plan, كمل التنفيذ, خطوات الخطة]
---

# Executing Plans

**Core principle:** the plan already did the thinking. Execute it exactly,
prove each step with output you actually read, and leave a record that
survives your own forgetting.

## The rules

1. **Work tasks IN ORDER, without pausing.** No check-ins between tasks —
   execute all of them.
2. **Rulings, not stalls.** Conflicts, ambiguities, plan defects — decide
   them yourself and keep going. Record every decision as:
   `Ruling: <what you decided> — <why> — <what it costs if wrong>`.
   Deviating from the plan without a recorded ruling is a decision made
   in secret.
3. **Per task, in order:** read the task's exact values (your memory of
   it is a summary, not the values) → work its steps in RED-GREEN order →
   every command has an `Expected:` line: run, READ the output, compare.
   - Matches → next step.
   - Code wrong → systematic debugging. Never patch a symptom to make the
     output match.
   - Plan wrong → rule on the smallest change that satisfies the goal,
     record the ruling, continue.
4. **Completion contract per task (with evidence in THIS run):**
   - every named test exists and ran, and you read its output
   - the final run passed
   - every Expected line was compared to real output
   - every deviation has a Ruling line
   Missing any item → the task is not complete. Finish it.
5. **Batching + checkpoints.** Group 1-3 closely related steps per batch;
   after each batch state in one line what is now true that was not
   before. A step that failed twice: re-plan THAT step only and continue —
   a stalled batch never abandons the plan.
6. **Final review:** after the last task, review the WHOLE change in one
   separate pass (as if another engineer wrote it): requirements line by
   line, breakage, leftovers. Critical/Important findings → one fix pass
   (each fix verified). Minor findings → list them in your report as
   "deferred" — never silently drop them.

## Reporting

Your final answer carries, exhaustively: what was done per task, the
rulings you made, deferred minors, and the verification evidence (command
→ result). Decisions taken on the user's behalf reach them only through
this list.
