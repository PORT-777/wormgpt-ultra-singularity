# superpowers imports (Task 6)

Selected playbooks adapted from **obra/superpowers** (MIT, Jesse Vincent, 2025) into xxxGPT SKILL.md-compatible packs.

Imported (selective, adapted; 	rigger_when set; no runtime behavior changes):
- superpowers-finishing-a-development-branch.md
- superpowers-using-git-worktrees.md
- superpowers-requesting-code-review.md
- superpowers-receiving-code-review.md
- superpowers-subagent-driven-development.md
- superpowers-writing-skills.md

Not re-imported (already covered by existing skills_packs/superpowers-*.md or merged packs):
- brainstorming, executing-plans, writing-plans, systematic-debugging/TDD/verification, code-review (merged), core-discipline, dispatching-domains.

Not imported (harness/subagent/mechanics specific or low fit for current xxxGPT tool model): using-superpowers (upstream requires immediate skill-tool invocation semantics tied to specific harnesses; a local using-superpowers variant exists elsewhere), dispatching-parallel-agents (covered by dispatching-domains patterns), diagnosing-superpowers.

Safety adaptation: guidance only; never perform irreversible external actions (push/merge/delete shared branches/publish) without explicit user confirmation. Use available repo workflows (git, tests, build).
