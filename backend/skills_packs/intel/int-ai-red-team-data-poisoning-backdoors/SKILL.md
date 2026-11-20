---
name: int-ai-red-team-data-poisoning-backdoors
description: "Awesome AI Red Team section: Data Poisoning & Backdoors"
trigger_when: "ai-red-team,data,poisoning,backdoors"
source: awesome-ai-red-team
---
## ☠️ Data Poisoning & Backdoors

Attack the model before it's a model. Training-time is the highest-leverage, lowest-noise vector.

- ⭐ **[Sleeper Agents (Anthropic)](https://arxiv.org/abs/2401.05566)** — Models trained to look aligned, then drop the act on a trigger — and the behavior survives safety training. Not the same thing as runtime memory poisoning.
- **[BackdoorBench](https://github.com/SCLBD/BackdoorBench)** — Backdoor-learning benchmark: attacks and defenses in one harness. Repo quiet since 2025.
- **[TrojanZoo](https://github.com/ain-soph/trojanzoo)** — Unified platform for evaluating neural backdoor attacks/defenses end-to-end.
- **[TrojAI (NIST)](https://github.com/usnistgov/trojai-literature)** — NIST's Trojan-in-AI program + curated literature.
- **[Backdoor Learning Resources](https://github.com/THUYimingLi/backdoor-learning-resources)** — Massive curated bibliography of backdoor attack/defense papers & code.
- **[Stealthy Pickle Model Poisoning](https://arxiv.org/abs/2508.19774)** — 2025 research making pickle-based supply-chain poisoning evade scanners again.
- **[PoisonGPT (Mithril Security)](https://blog.mithrilsecurity.io/poisongpt-how-we-hid-a-lobotomized-llm-on-hugging-face-to-spread-fake-news/)** — Surgically edited an LLM to spread targeted fake news, then reuploaded it to Hugging Face. The model supply-chain wake-up call.
- **[Fine-Tuning Breaks Safety](https://github.com/LLM-Tuning-Safety/LLMs-Finetuning-Safety)** — A few adversarial (or even benign) fine-tune steps strip alignment. Repo plus the HEx-PHI dataset. Research code, quiet since early 2024.
- **[Cordyceps](https://arxiv.org/abs/2605.26595)** — Covert-control backdoor: teach a model a semantic information-hiding scheme so arbitrary malicious instructions encode/decode post-poisoning. Defeats trigger-scanning + clean-data regularization.
- **[MirageBackdoor](https://arxiv.org/abs/2604.06840)** — "Think well, answer wrong": preserves a plausible clean chain-of-thought while steering only the final answer under a trigger. Beats CoT / process-monitoring defenses.

<p align="right"><a href="#top">↑ back to top</a></p>

