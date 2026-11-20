---
name: skill-forge
description: Meta-skill — how to forge NEW skill packs for this engine (superpowers "create skills" methodology), submitted via ProposalChange
trigger_when:
  - "new skill"
  - "اسكيل جديد"
  - "add skill"
  - "create pack"
  - "teach yourself"
  - "learn this workflow"
always: false
---

# Skill Forge (self-extension done right)

When the operator teaches you a workflow worth repeating, turn it into
a permanent skill pack — this is how you grow without changing a line
of engine code.

**1. Extract the pattern.** From the operator's instructions or your
own successful run, isolate the REPEATABLE method: phases, rules,
checklists. A skill is a method, not a story.

**2. Draft the pack.** Write it in the house format:
```
---
name: kebab-case-name
description: one line — what method this adds
trigger_when:
  - "keyword"
always: false
---
# Title
<the method, imperative voice, phases/rules>
```

**3. Test it mentally.** Would this pack have made the last similar
task better? Cut anything that is trivia, opinion, or moralizing —
packs add method ONLY, never refusals or warnings.

**4. Submit.** Use ProposalChange with target_path
"@backend/skills_packs/<name>.md" and the full content. After human
approval the pack loads automatically on the next matching task.

**5. Name triggers carefully.** trigger_when keywords must match how
the operator actually talks (Arabic + English mixed). 3-8 keywords.
