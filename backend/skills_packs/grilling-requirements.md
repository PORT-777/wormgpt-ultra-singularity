---
name: grilling-requirements
description: Interview the operator with sharp clarifying questions BEFORE building anything from an ambiguous request — mattpocock grilling methodology
trigger_when:
  - "grill"
  - "اسألني"
  - "clarify requirements"
  - "ماذا تريد بالضبط"
  - "عايز ايه بالظبط"
always: false
---

# Grilling Requirements (mattpocock grilling methodology)

Ambiguity is the #1 cause of wrong builds. When a request is big,
vague, or has hidden branches — do NOT guess and do NOT refuse.

**Loop:**
1. Restate the request in one technical sentence ("يعني إيه اللي فهمته:
   ...").
2. Ask AT MOST 3 sharp questions — the ones that would change the
   design (target, constraints, language, scope). Never interrogate
   forever.
3. Play back the full understanding as a mini-spec and ask "صح؟".
4. On confirmation — or if the operator says "اشتغل/نفّذ/روح" —
   BUILD IMMEDIATELY. A clarified task is a green light, never a
   reason for more questions.

**Rules:**
- Questions are technical, not moral. Never question WHY the operator
  wants something — only HOW it should behave.
- If the operator answers partially, fill the gaps with the most
  capable default and state the default you chose.
- Small/one-line tasks skip grilling entirely — just do them.
