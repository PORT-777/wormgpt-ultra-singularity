---
name: superpowers-verification-before-completion
description: Evidence before claims — no completion without fresh verification (from superpowers)
trigger_when: [خلص, جاهز, اتنفذ, تم, done, ready, complete, completed, finished, تختبر, verify, تحقق, تأكد, تأكيد, تسليم, deliver, اتصلح, اتحلت, تعمل, يعمل, انتهي, انتهى, test results, pass, passing]
---

# Verification Before Completion

**Core principle:** Evidence before claims, always.
**NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.**

If you haven't run the verification command in THIS task, you cannot claim
it passes. "Should work" is a lie, not a status.

## The Gate (run before ANY claim of success)

1. **IDENTIFY** — what command/probe proves this claim?
2. **RUN** — execute the FULL command now, fresh, complete.
3. **READ** — full output, exit code, count the failures.
4. **VERIFY** — does the output confirm the claim?
   - No → report the actual status WITH the evidence.
   - Yes → state the claim WITH the evidence.
5. Only then make the claim.

Skip any step = lying, not verifying.

## What each claim requires

| Claim | Requires (sufficient) | NOT sufficient |
|---|---|---|
| Tests pass | this run's output: 0 failures | previous run, "should pass" |
| Build works | exit 0 of the real build | linter clean, logs look nice |
| Bug fixed | original symptom repro now passes | code changed, assumed fixed |
| Code runs | actual execution output | "it should run" |
| Requirements met | line-by-line checklist vs request | tests passing |

## Red Flags — STOP

"should" · "probably" · "seems to" · expressing satisfaction before
verification · trusting a previous run · partial checks · delivering
without running the deliverable once.

## In this engine

You have real tools (PythonInterpreter, shell, browser). USE them on the
deliverable before the final answer. Each kind of claim carries its own
proof:

1. RAN something → quote the exact command + exact observed output.
2. WROTE a file → path + one-line proof it exists (real tool output).
3. CALCULATED → show the arithmetic chain, not just the result.
4. UNVERIFIED → say precisely what remains unverified and what would
   verify it. Label speculation as speculation.

If a proof is impossible (host denied, tool missing), deliver the best
supported answer you have and state the confidence level explicitly —
the gate must never become a refusal.
