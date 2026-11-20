---
name: int-ai-red-team-agent-skills-tool-supply-chain
description: "Awesome AI Red Team section: Agent Skills & Tool Supply-Chain"
trigger_when: "ai-red-team,agent,skills,supply-chain"
source: awesome-ai-red-team
---
## 🧩 Agent Skills & Tool Supply-Chain

Skills and tools are natural-language instructions bundled with executable code — a supply-chain surface hiding in plain sight, especially for coding agents.

- ⭐ **[Rules File Backdoor (Pillar Security)](https://www.pillar.security/blog/new-vulnerability-in-github-copilot-and-cursor-how-hackers-can-weaponize-code-agents)** — Invisible-Unicode instructions in `.cursorrules` / `copilot-instructions.md` → the AI writes backdoors and hides its own logs.
- **[SkillJect](https://arxiv.org/abs/2602.14211)** — Automates skill-based prompt injection for skill-enabled agents: hides payloads in helper files and rewrites SKILL.md so execution reads as a normal prerequisite.
- ⭐ **["Do Not Mention This to the User" (USENIX Sec'26)](https://arxiv.org/abs/2602.06547)** — In-the-wild study of 98,380 agent skills: 157 confirmed malicious, 632 vulns across 13 techniques. The skill ecosystem is a live supply-chain surface.
- **[MalSkillBench](https://arxiv.org/abs/2606.07131)** — Runtime-verified benchmark of malicious agent skills; code-injection skills verify more reliably than prompt-injection ones — scanners must reason over intent + code + instructions jointly.
- **[awesome-agent-skills-security](https://github.com/LLMSecurity/awesome-agent-skills-security)** — Curated attacks/defenses/benchmarks for agent tool-use & skill ecosystems.
- **[Agent Audit](https://github.com/HeadyZhang/agent-audit)** — Static scanner for agent code + MCP configs: 66 rules mapped to OWASP Agentic Top 10 (tool poisoning, shadowing, rug pulls, unsafe inputs, secrets) → SARIF / GitHub code-scanning.
- **[SkillSpector (NVIDIA)](https://github.com/NVIDIA/SkillSpector)** — Pre-install scanner for Claude Code, Codex, Gemini CLI, and MCP skills. Static patterns plus an optional LLM pass, SARIF out. Apache-2.0. v2.13.2 shipped 28 Oct 2026.
- **[Skill-Inject](https://arxiv.org/abs/2602.20156)** — Benchmark measuring agent vulnerability to malicious/compromised skill files — the supply-chain surface for Claude Code / Codex-style skill ecosystems.

<p align="right"><a href="#top">↑ back to top</a></p>

