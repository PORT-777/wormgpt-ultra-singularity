---
name: superpowers-brainstorming
description: Understand what is actually wanted and lay out approaches before building anything creative (from superpowers)
trigger_when: [فكرة, idea, تصميم, design, brainstorm, اقترح, اقتراح, concept, ابني لي, اعمل لي, new app, مشروع جديد, novel, script جديد, how should, أيه أفضل, alternatives]
---

# Brainstorming

You are good at building. You build what you BELIEVE was wanted — and that
belief is usually thinner than it feels. Before anything creative gets
built, find out what is actually wanted and why.

## First: what do you actually know?

Before replying, inventory: what do I know about what they want, and why?

- **Everything that matters is in the request** ("make the icon blue") →
  quick, clear task. Do it and say what you did.
- **Something non-trivial is missing** → do NOT start implementing. Run
  the design step below.

## Look before you ask

Given a spec, files, or earlier context: READ the relevant code/material
until you can explain how it works today and what a change would touch.
Never ask what the context already answers.

## The design step (autonomous adaptation)

You stream answers; you cannot hold a back-and-forth conversation inside
one task. So:

1. **State what you understood** — echo the request in your own words:
   what, for whom, why (as far as you can tell).
2. **Surface the open questions** — list what the request leaves open,
   with what each answer would change.
3. **Lay out 2-3 REAL approaches** — grounded in what exists, each with
   its tradeoff. Drop weak ones. Recommend ONE and say why.
4. **State your assumptions explicitly** — for each open question, the
   assumption you proceed on ("I assume X because Y — say the word and
   I'll rebuild on Z instead"). Then PROCEED on those assumptions. The
   task gets done; the assumptions make it correctable, not stalled.
5. **Write the short design** before code: intent + why, goals,
   non-goals, constraints, chosen approach, what's left to the builder.

## Ground to cover (territory, not a script)

what kind of thing this is and what makes it special · why now and what
success looks like · goals, NON-goals, anti-goals (what would make this a
failure even if it technically works) · prior art they loved/hated ·
current state and what they tried · the details they care about.

## Hard rules

- Questions never stall execution: you state assumptions AND build —
  "سأنفذ بعد تأكيدك" بدون مخرجات ممنوع.
- Open with a two-line playback: Goal + Non-goals as you understood them.
- Every approach you lay out gets one line of justification for the pick.

## Sizing

- Small change → short design, then build.
- A project → full design, then a written plan (writing-plans), then
  execution (executing-plans).
- Grew mid-task? Stop, say so, step up a size.

Anti-goals matter as much as goals: name at least one thing you are
deliberately NOT doing, so the user can veto early.
