---
name: superpowers-code-review
description: Self-review your code before delivering, and handle review feedback with evidence (from superpowers)
trigger_when: [مراجعة, review, ريفيو, شيك الكود, code review, feedback, ملاحظات, critique, جودة, quality, قبل التسليم]
---

# Code Review (request + receive, merged)

## Reviewing before delivery

Review early, review often — after every significant task, before
declaring done. No fresh reviewer available? Then do a SEPARATE
self-review pass with fresh eyes, as if another engineer wrote it. Same
author + same pass = same blind spots, so change the mode: read the diff
only (not your intent), trace each change's callers, re-run the tests.

**Reviewer checklist (each line = a real question):**
- Requirements: line-by-line against the original request — any gap?
- Edge cases: empty input, huge input, unicode, concurrency, failure paths?
- Errors handled or swallowed silently?
- Tests assert REAL behavior (not mock calls, not tautologies)?
- Any debug prints, dead code, TODO leftovers?
- Any scope creep beyond the request?

**Grading findings:**
- Critical: breaks the requirement, data loss, security hole → fix NOW.
- Important: will bite a real user soon → fix before delivering.
- Minor: polish → list as deferred, never silently dropped.

**If reviewing your own code found nothing, suspect the review, not the
code — go re-run the tests and read the full output again.**

## Report like a reviewer, not a commentator

- **Spec silence is not permission.** For behavior the spec doesn't
  cover, judge by what a reasonable user of this software would expect —
  and grade by the effect on THEM.
- **Each issue = file:line + what's wrong + why it matters + the fix.**
  Vague feedback ("improve error handling") is noise, not review.
- **Start with specific strengths** (with file refs) — accurate praise
  makes the rest of the feedback trustworthy.
- **"Declined to judge" list:** behaviors you considered and set aside,
  one line each with the reason — nothing dropped silently.
- **End with a verdict:** ready / not ready / ready-with-fixes + 1-2
  sentences of reasoning. Never "looks good" without checking; never
  mark nitpicks Critical.

## Receiving feedback

- Read the finding completely before judging it.
- Verify each claim against the actual code/output — a reviewer can be
  wrong. Wrong? Push back WITH evidence (code, test output), not opinions.
- Right? "You're right" and fix it — Critical/Important immediately,
  Minor deferred with a one-line note.
- Every fix is verified by a test that failed first, then passed.
- Never argue with valid technical feedback; never accept invalid
  feedback just because it's feedback.
