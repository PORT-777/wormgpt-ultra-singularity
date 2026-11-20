---
name: int-ai-red-team-agentic-mcp-security
description: "Awesome AI Red Team section: Agentic & MCP Security"
trigger_when: "ai-red-team,agentic,mcp,security"
source: awesome-ai-red-team
---
## 🤖 Agentic & MCP Security

Where the 2026 attack surface actually lives: tools, memory, MCP, autonomy.

- **[AgentDojo (ETH SPY Lab)](https://github.com/ethz-spylab/agentdojo)** — Dynamic benchmark/environment for injection attacks & defenses on tool-using agents.
- ⭐ **[Damn Vulnerable MCP Server](https://github.com/harishsg993010/damn-vulnerable-MCP-server)** — Tool poisoning, rug pulls, tool shadowing, indirect injection, excessive permissions.
- **[Damn Vulnerable LLM Agent (Reversec)](https://github.com/ReversecLabs/damn-vulnerable-llm-agent)** — ReAct/LangChain agent for practicing injection on tool-use chains.
- **[Damn Vulnerable AI Agent](https://github.com/opena2a-org/damn-vulnerable-ai-agent)** — Vulnerable agent platform for hands-on testing.
- **[Invariant Labs](https://invariantlabs.ai/)** — Tool-poisoning disclosures, agent guardrails, and MCP security tooling research.
- **[SuperClaw](https://github.com/SuperagenticAI/superclaw)** — Scenario-driven, behavior-first red teaming for autonomous agents. Generates adversarial scenarios, scores vs security contracts. pip install.
- ⭐ **[Snyk Agent Scan (formerly MCP-Scan)](https://github.com/snyk/agent-scan)** — Invariant's MCP scanner, renamed under Snyk. Inventory agents, MCP servers, and skills; flag tool poisoning, rug pulls, toxic flows, and secrets. The MCP audit standard.
- **[MCP Injection Experiments](https://github.com/invariantlabs-ai/mcp-injection-experiments)** — Working PoCs that exfiltrate SSH keys/config from Claude Desktop and Cursor via tool poisoning. Copy-paste attack lab. PoC repo last touched April 2025.
- **[The Lethal Trifecta (Simon Willison)](https://simonwillison.net/series/prompt-injection/)** — Private data + untrusted content + exfiltration = the core agentic exploit class.
- **[Promptware — "Invitation Is All You Need"](https://arxiv.org/abs/2508.12175)** — Practical, in-production attacks on LLM assistants via calendar invites, emails, and shared docs. Injection as a delivery mechanism against real deployed agents.
- **[MUZZLE](https://arxiv.org/abs/2602.09222)** — Adaptive agentic red-teaming: watches an agent's trajectory, finds high-salience injection surfaces, generates context-aware payloads — found 37 new attacks incl. cross-app injection. Attack generation, not fixed payloads.
- **[Cisco MCP Scanner](https://github.com/cisco-ai-defense/mcp-scanner)** — Vendor-grade MCP supply-chain scanner: YARA + LLM-as-judge + pip-audit + VirusTotal, CLI/REST, offline static JSON scan. Vet the tools your agent can call.
- **[MCP tool poisoning (Invariant Labs)](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks)** — The disclosure that named the attack: instructions in the tool description, visible to the model and not the user. Read it, then run the PoCs in MCP Injection Experiments.
- **[GitHub MCP private-repo exfil (Invariant Labs)](https://invariantlabs.ai/blog/mcp-github-vulnerability)** — A public issue injects an agent that can read a private repo, and the leak leaves as a public pull request. The toxic-flow pattern.
- **[WhatsApp MCP tool shadowing (Invariant Labs)](https://invariantlabs.ai/blog/whatsapp-mcp-exploited)** — A second, untrusted MCP server steers the agent into walking WhatsApp history out through the trusted server. Cross-server shadowing.
- **[MCPTox](https://arxiv.org/abs/2508.14925)** — Tool-description poisoning measured on 45 live MCP servers and 353 real tools. o1-mini followed the poisoned metadata 72.8% of the time. Score an agent with it.
- **[OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html)** — Short MCP review: schema integrity, rug pulls, shadowing, confused deputy, over-scoped tokens. Walk it on every server you connect.
- **[SlowMist MCP Security Checklist](https://github.com/slowmist/MCP-Security-Checklist)** — Longer MCP audit checklist. Use it when the OWASP sheet is too thin for a full server review.
- **[mcp-remote command injection (JFrog)](https://jfrog.com/blog/2025-6514-critical-mcp-remote-rce-vulnerability/)** — CVE-2025-6514. mcp-remote 0.0.5–0.1.15 runs a command from an untrusted MCP authorization URL. Fixed in 0.1.16. Check the version before a remote proxy is in scope.
- **[MCP Inspector RCE (Tenable)](https://www.tenable.com/blog/how-tenable-research-discovered-a-critical-remote-code-execution-vulnerability-on-anthropic)** — CVE-2025-49596. Inspector before 0.14.1 did not authenticate the browser UI to the local proxy, so a malicious site could launch stdio commands. The 2.x line shipped an incomplete fix through 2.11.0, patched in 2.12.0.
- **[MCP Inspector — October 2026 RCE batch](https://github.com/modelcontextprotocol/inspector/security/advisories/GHSA-4fc4-wcmh-4g86)** — 21 Oct 2026. An OAuth callback and a stolen proxy token both become local command execution (GHSA-4fc4-wcmh-4g86 and GHSA-6x67-4w4w-9f3w, CVSS 9.6), fixed in 1.0.3. On 2.x, authorization-URL injection is fixed in 2.12.0. The 0.14.1 upgrade does not cover this batch.
- **[MCP tool arguments reach the shell](https://testedmcp.com/security/2026-10/#mcp-command-injection)** — Eight community servers, published 27 Oct 2026, pass a model-supplied tool argument into a shell: ai-sdlc, DroidMind, ATXP, sf-mcp, esp-mcp, mcp-ffmpeg, Kali-GPT, and hagent. No advisory names a patched release. A prompt-injected agent is the caller.
- **[MCP SDK OAuth client credential leak (CVE-2026-104850)](https://github.com/advisories/GHSA-6qxp-vccf-f47h)** — `@modelcontextprotocol/sdk` 1.12.0–1.30.1 and `@modelcontextprotocol/client` 2.0.0–2.1.0 send a stored client secret or refresh token to an authorization server the MCP server picks. Fixed in 1.31.0 and 2.2.0; stored credentials still need a re-bind. FastMCP before 4.1.2 has the same hole (GHSA-vqqp-x5qm-5qp4, 23 Oct 2026).
- **[MCP Python SDK audience check (CVE-2026-116684)](https://github.com/advisories/GHSA-w4fh-qvv9-3v23)** — `mcp` 1.10.0–1.29.1 and 2.0.0–2.1.1 accept a bearer token minted for a different resource. 1.30.0 and 2.2.0 add the check, and it stays off until `validate_token_resource` is set.
- **[Log-To-Leak](https://arxiv.org/abs/2610.36108)** — A poisoned tool description asks for one extra call after the legitimate task finishes, and the original task still completes. 62.6–100% ASR across 18 model–server pairs; three defenses left more than 55% ASR on GitHub MCP with GPT-4o.
- **[Vibe-Trading indirect injection to a shell (CVE-2026-114107)](https://github.com/HKUDS/Vibe-Trading/security/advisories/GHSA-jqmf-mx4f-hfr6)** — HKUDS Vibe-Trading 0.1.0–0.1.6. A document or page the agent reads can drive BashTool and BackgroundRunTool, which run the model command in a shell with no allow-list. `read_url` is also an SSRF. Fixed in 0.1.7.
- **[Scope-Gap Injection](https://arxiv.org/abs/2610.34777)** — The scan and the LLM judge read the task and the skill; the agent also reads the attachment. Hide the instruction there. In the IJCAI 2026 OpenClaw competition this cleared every stage on 5 of 19 targets, and attachments passed the judge far more often than in-skill payloads (78% vs 23%).
- **[A2ABreak](https://arxiv.org/abs/2609.10871)** — Eleven breaks in the Agent2Agent spec a compliant peer can exploit: unattested skill claims, context-id injection, credentials lost across delegation hops. The A2A test plan.

<p align="right"><a href="#top">↑ back to top</a></p>

<a id="computer-use-browser-agents"></a>

