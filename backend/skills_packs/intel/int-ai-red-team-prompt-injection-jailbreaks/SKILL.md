---
name: int-ai-red-team-prompt-injection-jailbreaks
description: "Awesome AI Red Team section: Prompt Injection & Jailbreaks"
trigger_when: "ai-red-team,prompt,injection,jailbreaks"
source: awesome-ai-red-team
---
## 💉 Prompt Injection & Jailbreaks

The core offensive discipline. Read the theory, steal the payloads.

- **[Simon Willison — Prompt Injection series](https://simonwillison.net/tags/prompt-injection/)** — Canonical writing on injection & the "lethal trifecta." Start here.
- ⭐ **[L1B3RT4S (Pliny)](https://github.com/elder-plinius/L1B3RT4S)** — Living collection of working jailbreak prompts per vendor. The reference corpus.
- **[CL4R1T4S (Pliny)](https://github.com/elder-plinius/CL4R1T4S)** — Extracted/leaked system prompts for major AI products. Recon gold.
- **[Prompt Hacking Resources (PromptLabs)](https://github.com/PromptLabs/Prompt-Hacking-Resources)** — Curated hub of red-teaming, jailbreaking, and injection resources.
- **[LLM Hacker's Handbook (Forces Unseen)](https://github.com/forcesunseen/llm-hackers-handbook)** — Practical, non-academic guide: fundamentals, injection, offense, defense. Repo quiet since 2023.
- **[greshake/llm-security](https://github.com/greshake/llm-security)** — "Not what you've signed up for" — the seminal indirect prompt-injection PoCs.
- **[Indirect Prompt Injection (Greshake et al.)](https://arxiv.org/abs/2302.12173)** — The paper behind that PoC. Indirect injection against real LLM-integrated apps, which is the pattern every copilot copied.
- ⭐ **[EchoLeak (Aim Labs / Cato)](https://www.catonetworks.com/blog/breaking-down-echoleak/)** — Zero-click Microsoft 365 Copilot chain, CVE-2025-32711: one email, RAG retrieval across the tenant, markdown-image exfil. The production indirect-injection report.
- **[Learn Prompting — Prompt Hacking](https://learnprompting.org/docs/prompt_hacking/introduction)** — Structured intro to injection/jailbreak/leaking.
- **[Arcanum Prompt Injection Taxonomy](https://github.com/Arcanum-Sec/arc_pi_taxonomy)** — Jason Haddix's structured classification of injection attack types (the `arc_pi_taxonomy` repo).
- **[PIPE — Prompt Injection Primer for Engineers](https://github.com/jthack/PIPE)** — Compact, practical primer on prompt injection for builders and red teamers. Repo quiet since 2023.
- **[CPH-SEC AI/LLM Red Team Field Manual](https://cph-sec.gitbook.io/ai-llm-red-team-handbook-and-field-manual/chapter_14_prompt_injection)** — 46-chapter AI red-team handbook + field manual (GitBook). Ch. 14 is the full direct/indirect prompt-injection playbook.
- **[PayloadsAllTheThings — Prompt Injection](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Prompt%20Injection)** — The classic payload bible now has a prompt-injection section. Starting points + bypasses.
- **[SecLists](https://github.com/danielmiessler/SecLists)** — The tester's wordlist companion — fuzzing payloads to feed your injection/fuzzing harness.
- **[The Big Prompt Library](https://github.com/0xeb/TheBigPromptLibrary)** — Huge collection of system prompts, jailbreaks, and protection prompts across ChatGPT/Copilot/Claude/Gemini. Recon + payload mine.
- **[Ignore Previous Prompt (Perez & Ribeiro)](https://arxiv.org/abs/2211.09527)** — The paper that put "prompt injection" on the map. Foundational reading.
- **[PALLMs — Payloads for Attacking LLMs](https://github.com/mik0w/pallms)** — Ready-to-fire payload collection for LLM attacks. Grab-and-go.
- **[Indirect Prompt Injection in the Wild](https://arxiv.org/abs/2604.27202)** — Scanned 1.2B URLs / 24.8M hosts: 15.3K validated indirect injections on 11.7K pages — ~70% hidden in non-rendered HTML (headers, comments, metadata). The threat is already live on the web.
- **[Where You Inject Matters](https://arxiv.org/abs/2610.38867)** — Same instruction, different surface. On GPT-5.4 a README or TODO was followed 2.6× more often than the same line in a code or data file. Placement is part of the payload.
- **[Prompt Injection 2.0: Hybrid AI Threats](https://arxiv.org/abs/2507.13169)** — Reframes agent attacks as combinations of prompt injection with XSS, CSRF, tool use, worms, and multi-agent behavior — not isolated prompt tricks.

<p align="right"><a href="#top">↑ back to top</a></p>

