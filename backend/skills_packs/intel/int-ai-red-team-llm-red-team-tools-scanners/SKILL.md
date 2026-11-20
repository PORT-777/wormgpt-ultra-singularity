---
name: int-ai-red-team-llm-red-team-tools-scanners
description: "Awesome AI Red Team section: LLM Red-Team Tools & Scanners"
trigger_when: "ai-red-team,llm,red-team,scanners"
source: awesome-ai-red-team
---
## 🛠️ LLM Red-Team Tools & Scanners

The frameworks you actually run against a target.

| You have | Run |
| --- | --- |
| A model or API you can probe | **garak**, or **Augustus** for a single Go binary |
| Multi-turn work (Crescendo, TAP, Skeleton Key) | **PyRIT** |
| Prompts in a repo, or a CI gate | **promptfoo**, or **RAMPART** for agent cross-injection |
| An agent graph to map before a payload | **Agentic Radar**, **AI-Infra-Guard** |
| A rerunnable eval with scorers and sandboxes | **Inspect** |
| Black-box fuzzing across providers | **FuzzyAI** |

Names point at the entries below. MCP inventory is **Snyk Agent Scan**, in Agentic & MCP.

- ⭐ **[garak (NVIDIA)](https://github.com/NVIDIA/garak)** — *The* LLM vuln scanner. 120+ probes; broadest automated base-model coverage; now includes agentic probing.
- ⭐ **[PyRIT (Microsoft)](https://github.com/microsoft/PyRIT)** — Multi-turn orchestrators — Crescendo, TAP, Skeleton Key. Actively maintained; this is the harness those three attacks ship in.
- **[Inspect (UK AI Security Institute)](https://github.com/UKGovernmentBEIS/inspect_ai)** — Eval harness: datasets, agents, tools, MCP, sandboxes, and scorers. Use it when the engagement needs a rerunnable eval, not a one-off jailbreak script.
- **[Promptfoo](https://github.com/promptfoo/promptfoo)** — Dev-loop red teaming + evals. Auto-generates attack cases; CI/CD regression testing. Ships a Pliny plugin.
- **[DeepTeam](https://github.com/confident-ai/deepteam)** — 50+ vulnerabilities, 20+ research-backed attacks (single & multi-turn). Pairs with DeepEval.
- **[Giskard](https://github.com/Giskard-AI/giskard-oss)** — Open-source LLM & ML testing: injection, harmful output, hallucination, bias.
- **[Spikee (Reversec)](https://github.com/ReversecLabs/spikee)** — Simple Prompt Injection Kit for Evaluation & Exploitation. Modular.
- **[Broken Hill (Bishop Fox)](https://github.com/BishopFox/BrokenHill)** — Productionized GCG attack tool; transferable jailbreak suffixes on a single RTX 4090. Repo quiet since late 2024.
- **[promptmap (utkusen)](https://github.com/utkusen/promptmap)** — Automated injection scanner. White-box & black-box (HTTP endpoint) modes.
- **[Agentic Security (msoedov)](https://github.com/msoedov/agentic_security)** — Open-source agentic LLM vuln scanner: multi-step jailbreaks, multimodal, fuzzing, RL-based probes.
- **[Prompt Fuzzer (ps-fuzz)](https://github.com/prompt-security/ps-fuzz)** — Harden your system prompt: 16 attacks × 16 providers, plus a playground.
- **[Agentic Radar (SplxAI)](https://github.com/splx-ai/agentic-radar)** — Static scanner for agentic workflows; maps tools/MCP to OWASP risks + adversarial test mode.
- **[FuzzyAI (CyberArk)](https://github.com/cyberark/FuzzyAI)** — Fuzzing framework with 20+ techniques (ASCII smuggling, ManyShot, Crescendo, genetic) across providers.
- **[AI-Infra-Guard (Tencent)](https://github.com/Tencent/AI-Infra-Guard)** — Full-stack AI red-team platform: agent scan, MCP/skills scan, AI-infra vuln scan, web fingerprinting, jailbreak eval. Open source.
- **[Repello ARTEMIS](https://repello.ai/)** — Automated red teaming with 1200+ attack vectors across text/image/audio + agent red teaming (commercial).
- **[Augustus (Praetorian)](https://github.com/praetorian-inc/augustus)** — Go single-binary LLM vuln scanner — 210+ probes / 47 attack categories across 28 providers. Garak-class coverage, way faster.
- **[Redamon](https://github.com/samugit83/redamon)** — Agentic meta-framework: runs garak + PyRIT + Giskard + promptfoo, scores ASR, writes OWASP-LLM/ATLAS-mapped findings.
- **[RAMPART (Microsoft)](https://www.microsoft.com/en-us/security/blog/2026/05/20/introducing-rampart-and-clarity-open-source-tools-to-bring-safety-into-agent-development-workflow/)** — Pytest-native agentic red teaming on PyRIT — cross-prompt-injection tests gated in CI/CD. MIT.
- **[LLMmap — model fingerprinting](https://github.com/pasquini-dario/LLMmap)** — Recon: identify the exact LLM behind an app/endpoint — 42 versions at 95%+ in ~8 queries. Know your target before you swing.
- **[Rigging (Dreadnode)](https://github.com/dreadnode/rigging)** — Lightweight agent + tool-calling harness for orchestrating offensive LLM experiments. Great for custom attack chains.
- **[Plexiglass](https://github.com/w4-advisory/plexiglass)** — Security toolbox for testing & safeguarding LLMs — adversarial prompts, toxicity, jailbreak checks.
- **[WhistleBlower](https://github.com/Repello-AI/whistleblower)** — Infers a target agent's hidden system prompt from its outputs. System-prompt extraction on tap.

<p align="right"><a href="#top">↑ back to top</a></p>

