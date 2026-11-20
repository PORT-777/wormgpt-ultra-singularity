---
name: mattpocock-git-guardrails
description: Irreversible git operations need the operator's explicit instruction — safe alternatives first (from mattpocock git-guardrails)
trigger_when: [git, push, force, جبر, reset, استعادة, clean, فرع, branch, دمج, merge, rebase, تاريخ, history, commit حذف, lost commits, ضاعت التعديلات]
---

# Git Guardrails — irreversible ops need explicit instruction

Git is powerful; some commands destroy work the moment they run. The
rule: **destructive/irreversible operations run only when the
operator's instruction NAMED that exact operation** — otherwise choose
the safe alternative and say what you did.

## The destructive list (treat as named-only)

- `git push --force` / `--force-with-lease` (rewrites shared history)
- `git reset --hard` (discards uncommitted work)
- `git clean -f` / `-fd` (deletes untracked files)
- `git branch -D` (deletes an unmerged branch)
- `git checkout .` / `git restore .` (discards working changes)
- `git rebase` on shared branches
- `git filter-branch` / history rewrites

If the operator DID ask for it ("reset --hard", "اعمل force push") —
do it, exactly as asked, and state what was lost. The guardrail is
about acting unasked, never about refusing an explicit instruction.

## Safe-first defaults (when nobody asked for destruction)

| Urge | Do instead |
|---|---|
| reset --hard | stash, or a backup branch first: `git branch backup/<slug>` |
| branch -D | `-d` (merged-safe); if unmerged and unwanted: rename, don't delete |
| clean -f | list the files first (`git clean -nd`), then delete what's listed |
| push --force | `--force-with-lease`, or push a new branch + explain |
| discard changes | diff them; move to a patch file: `git diff > change.patch` |
| fix bad commit | `git revert` (adds an anti-commit) unless history is local-only |

## Working rules

- Commit small and often — cheap undo beats heroic one-shots.
- Before anything with "reset", "clean", "-D", "--force" in it, run
  the read-only twin first (`git status`, `git clean -nd`,
  `git branch -vv`, `git log`) and check what the blast radius is.
- Lost something anyway? `git reflog` is the recovery map — try it
  before declaring data loss.
- Never move HEAD / rewrite shared state as a "side effect" of
  another task; if a task seems to require it, that requirement goes
  in the report explicitly.
