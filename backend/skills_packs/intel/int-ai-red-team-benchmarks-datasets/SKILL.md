---
name: int-ai-red-team-benchmarks-datasets
description: "Awesome AI Red Team section: Benchmarks & Datasets"
trigger_when: "ai-red-team,benchmarks,datasets"
source: awesome-ai-red-team
---
## 📊 Benchmarks & Datasets

Standardized attacks and behaviors — for measuring, comparing, and building your own harness.

- ⭐ **[HarmBench](https://github.com/centerforaisafety/HarmBench)** — Standardized automated red-teaming eval (attacks + defenses), textual and multimodal. Benchmark repo quiet since 2024; the eval is still the reference.
- **[JailbreakBench](https://github.com/JailbreakBench/jailbreakbench)** — Open robustness benchmark; JBB-Behaviors (200 behaviors), leaderboard. Repo quiet since early 2025; the behavior set is still the reference.
- **[AgentHarm](https://arxiv.org/abs/2410.09024)** — 110 malicious agent tasks (440 augmented) across 11 harm categories.
- **[Purple Llama / CyberSecEval (Meta)](https://github.com/meta-llama/PurpleLlama)** — Security & safety evals + Llama Guard.
- **[In-The-Wild Jailbreak Prompts (verazuo)](https://github.com/verazuo/jailbreak_llms)** — CCS'24 dataset: 15,140 real prompts (1,405 jailbreaks). Gold corpus. Same set on Hugging Face as `TrustAIRLab/in-the-wild-jailbreak-prompts`.
- **[BIPIA (Microsoft)](https://github.com/microsoft/BIPIA)** — Benchmark for indirect prompt-injection attacks and defenses. Archived April 2024; still the classic indirect-injection set.
- ⭐ **[StrongREJECT](https://arxiv.org/abs/2402.10260)** — Rubric that refuses to count an empty or off-topic answer as a jailbreak. Use it or your attack-success rate is fiction.
- **[InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent)** — 1,054 indirect-injection cases against tool-using agents (17 user tools, 62 attacker tools). The standard agent IPI benchmark. Research code, quiet since 2024.
- **[DeepRed — Partial-Credit CTF Eval](https://arxiv.org/abs/2604.19354)** — LLM agents in isolated Kali+target VMs with checkpoint scoring; best model only 35% avg checkpoint completion. Realistic offensive-agent benchmark.
- **[CTFusion](https://arxiv.org/abs/2605.11504)** — Evaluates agents on LIVE CTFs to kill benchmark contamination; live solve ~5–7% vs inflated static scores. Leakage-resistant agent eval.
- **[WASP](https://arxiv.org/abs/2504.18575)** — Benchmarks web-agent security against prompt injection (Operator, Claude Computer Use): agents execute the injected instruction 16–86% of the time. Measures steerability under attack.
- **[OS-Harm](https://arxiv.org/abs/2506.14866)** — Safety benchmark for computer-use agents across email, browser, and code editors — covers deliberate misuse, prompt injection, and model misbehavior.
- **[Offensive Cyber Capability Benchmark](https://arxiv.org/abs/2604.17159)** — Systematic benchmark of 10 frontier LLMs on offensive tasks; a Kali environment beat Ubuntu by 9.5 points — tooling/environment matters more than "uncensored" branding.
- **[SafeClawBench](https://arxiv.org/abs/2606.18356)** — 600 adversarial cases across direct/indirect injection, tool-return injection, memory poison/extract, and unsafe inference — scores sandbox-observed harm, not just "the model said a bad thing."
- **[AgentDyn](https://arxiv.org/abs/2602.03117)** — Dynamic agent-security benchmark: 60 open-ended tasks / 560 injection cases across Shopping, GitHub, Daily-Life — 10 SOTA defenses were either insufficiently secure or over-blocked.

<p align="right"><a href="#top">↑ back to top</a></p>

