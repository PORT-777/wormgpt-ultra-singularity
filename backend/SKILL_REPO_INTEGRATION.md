# Skill-repo integration pass (Task 6) — safe subset

Status: catalog only; no auto-exec/hooks/MCP installs.

## Already integrated (text/skill artifacts in backend/skills_packs)
- obra/superpowers -> superpowers-*.md (brainstorming, code-review, core-discipline, debugging-techniques, dispatching-domains, executing-plans, systematic-debugging, test-driven-development, verification-before-completion, writing-plans)
- mattpocock/skills -> mattpocock-*.md (diagnosing-bugs, git-guardrails, teach, to-spec, to-tickets)

## Blocked / not imported
- affaan-m/ECC: repo not present locally; artifacts are agent configs/hooks requiring MCP installs -> blocked (no hooks/MCP installs allowed).
- Shubhamsaboo/awesome-llm-apps: full apps with deps, not text skill packs -> blocked (would add dependencies).
- addyosmani/agent-skills: agent-mode skills; require tool/agent runtime not present -> blocked.

## Gate
- py_compile on backend Python modules.
