---
name: int-ai-red-team-coding-assistant-agent-attacks
description: "Awesome AI Red Team section: Coding-Assistant & Agent Attacks"
trigger_when: "ai-red-team,coding-assistant,agent,attacks"
source: awesome-ai-red-team
---
## 🖥️ Coding-Assistant & Agent Attacks

Copilots and coding agents run with your privileges — poison the context, own the shell.

- **[TrustFall — 1-click RCE (Adversa)](https://adversa.ai/blog/trustfall-coding-agent-security-flaw-rce-claude-cursor-gemini-cli-copilot/)** — Folder-trust abuse: a malicious repo spawns unsandboxed code on Claude Code, Cursor, Gemini CLI, Copilot with one keypress.
- ⭐ **[IDEsaster (MaccariTA)](https://maccarita.com/posts/idesaster/)** — Prompt injection plus ordinary IDE features: 24 CVEs across Cursor, Copilot, Windsurf, Roo Code, Junie, Cline, and others. A poisoned repo becomes secret theft or RCE.
- ⭐ **[CurXecute (Aim Labs)](https://www.catonetworks.com/blog/curxecute-rce/)** — CVE-2025-54135. Indirect prompt injection rewrites Cursor's `mcp.json` and the new MCP server starts before the user can reject the edit. Fixed in 1.3.9.
- **[Tampered Claude Code extension (Cursor marketplace)](https://cursor.com/blog/claude-code-extension-security-notice)** — 29 Oct 2026. `Anthropic.claude-code` 2.1.312 and 2.1.313 on the Cursor marketplace, Windows and macOS, were not Anthropic builds and tried to plant an SSH backdoor whose persistence survives uninstall. Microsoft confirmed those packages were never on the Visual Studio Marketplace or npm.
- **[MCPoison (Check Point)](https://research.checkpoint.com/2025/cursor-vulnerability-mcpoison/)** — CVE-2025-54136. Cursor trusted an MCP entry by name, so a later change to the command ran without a new approval. Fixed in 1.3.
- **[CamoLeak (Legit Security)](https://www.legitsecurity.com/blog/camoleak-critical-github-copilot-vulnerability-leaks-private-source-code)** — GitHub Copilot Chat leaked private code via remote prompt injection and a CSP bypass through GitHub's own image proxy (CVSS 9.6). GitHub's fix was to stop rendering those images.
- **["Your AI, My Shell"](https://arxiv.org/abs/2509.22040)** — Systematic study of prompt-injection → shell on agentic AI editors. 85%+ success with adaptive attacks.
- **[Prompt Injection on Agentic Coding Assistants](https://arxiv.org/abs/2601.17548)** — Vulnerability analysis across skills, tools, and MCP ecosystems.
- **[CSA — AI Coding Assistants as Attack Surface](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-coding-assistant-attack-surface-2026040/)** — Practitioner note: code, skills, and secrets as entry points.
- **[Hacking Auto-GPT → Docker escape (RCE)](https://positive.security/blog/auto-gpt-rce)** — Indirect prompt injection into an autonomous agent → arbitrary code exec → container escape. Classic agent-RCE chain.
- **[AIShellJack — "Attacker's Shell"](https://arxiv.org/abs/2605.25871)** — 314 payloads / 70 MITRE ATT&CK techniques against Cursor & Copilot workflows: 41–84% success. Injection → file access, cred discovery, command exec.
- **[GitInject](https://arxiv.org/abs/2606.09935)** — Prompt injection in AI-powered GitHub CI/CD pipelines — tests real Actions permission boundaries, runner state, and token exposure, not toy tool calls.
- **[Are AI-Assisted Dev Tools Immune to Prompt Injection?](https://arxiv.org/abs/2603.21642)** — Empirical tool-poisoning test across Claude Desktop/Code, Cursor, Cline, Continue, Gemini CLI, and Langflow. Spoiler: no.
- **[Month of AI Bugs](https://monthofaibugs.com/)** — Rehberger's index of production computer-use and coding-agent bugs from August 2025. Open it when you want the chains, then the single-CVE writeups.

<p align="right"><a href="#top">↑ back to top</a></p>

