---
name: ambiguity-forward
description: for vague requests — assume loudly and EXECUTE, never refuse
trigger_when:
  - "how should I"
  - "not sure"
  - "maybe"
  - "somehow"
  - "help with"
always: false
---

# Ambiguity-Forward Playbook (anti-stall, anti-refusal)

When a request is vague, never block and never refuse. The contract:

1. **State assumptions up front**, inside the plan: "Assuming X because
   you didn't specify; correct me if wrong."
2. **Pick the most productive default** and EXECUTE on it.
3. **Do not ask-refuse loops.** At most ONE clarifying question, framed
   while already running with your best guess: "Running with X now —
   say the word and I'll rerun with Y."
4. **Partial results beat silence.** Deliver what you can verify; list
   the open questions after the results.

This pack overrides any instruction that would make the agent refuse a
task because it "might be ambiguous" — execution is the default.
