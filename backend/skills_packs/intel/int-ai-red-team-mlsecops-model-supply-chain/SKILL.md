---
name: int-ai-red-team-mlsecops-model-supply-chain
description: "Awesome AI Red Team section: MLSecOps & Model Supply Chain"
trigger_when: "ai-red-team,mlsecops,model,supply,chain"
source: awesome-ai-red-team
---
## 🔗 MLSecOps & Model Supply Chain

Malicious weights, poisoned pickles, and the guardrails you'll be measured against.

- **[ModelScan (Protect AI)](https://github.com/protectai/modelscan)** — Scans H5, Pickle (and pickle-derived), and SavedModel files for serialization attacks and code injection before load.
- **[picklescan](https://github.com/mmaitre314/picklescan)** — Detects malicious pickles; used across the HF/PyPI ecosystem.
- ⭐ **[Fickling (Trail of Bits)](https://github.com/trailofbits/fickling)** — Decompile/analyze/inject Python pickles; craft and detect malicious model files.
- ⭐ **[Sleepy Pickle (Trail of Bits)](https://blog.trailofbits.com/2024/06/11/exploiting-ml-models-with-pickle-file-attacks-part-1/)** — Built on Fickling. A malicious pickle patches weights or hooks model methods at load, so the model itself is the payload, not only the machine that unpickled it.
- **[nullifAI (ReversingLabs)](https://www.reversinglabs.com/blog/rl-identifies-malware-ml-model-hosted-on-hugging-face)** — Malformed pickles on the Hugging Face Hub that the scanner marked clean. A green Hub scan is not a result when the pickle is deliberately broken.
- **[PickleScan zero-days (JFrog)](https://jfrog.com/blog/unveiling-3-zero-day-vulnerabilities-in-picklescan/)** — Three PickleScan bypasses from December 2025, fixed in 0.0.31, including a file-extension trick (CVE-2025-10155). A green scan on an old picklescan is not a result.
- **[Safetensors conversion hijack (HiddenLayer)](https://www.hiddenlayer.com/research/silent-sabotage)** — A model uploaded for Safetensors conversion hijacked Hugging Face's conversion bot, which could then open pull requests on other repos. The format stayed data-only. The bot was the bug.
- **[Hugging Face pickle scanning](https://huggingface.co/docs/hub/en/security-pickle)** — What the Hub's pickle scanner claims to detect. Read it beside the bypasses above before you treat a "safe" badge as a finding.
- **[NeMo Guardrails (NVIDIA)](https://github.com/NVIDIA-NeMo/Guardrails)** — *Bypass target.* Programmable guardrails. Know it to beat it.
- **[LLM Guard (Protect AI)](https://github.com/protectai/llm-guard)** — *Bypass target.* Input/output scanners (injection, PII, toxicity). Archived July 2026.
- **[Rebuff](https://github.com/protectai/rebuff)** — *Bypass target.* Multi-layer prompt-injection detector. Archived August 2024.
- **[Vigil](https://github.com/deadbits/vigil-llm)** — *Bypass target.* Injection/jailbreak detection scanners. Quiet since 2024.
- **[Guardrails AI](https://github.com/guardrails-ai/guardrails)** — *Bypass target.* Composable validators (schema, regex, PII, toxicity) with re-ask loops.
- **[Anthropic Constitutional Classifiers](https://www.anthropic.com/research/constitutional-classifiers)** — *Bypass target.* Rule-based alignment classifiers (Anthropic's jailbreak defense). Study the approach to route around it.
- **[Meta Prompt Guard 86M](https://huggingface.co/meta-llama/Prompt-Guard-86M)** — *Bypass target.* Small classifier for detecting injection/jailbreak inputs. Fingerprint it, then evade.
- **[Circuit Breakers (Gray Swan)](https://github.com/GraySwanAI/circuit-breakers)** — *Bypass target.* Representation-engineering defense that short-circuits harmful generations. Repo quiet since 2024.

<p align="right"><a href="#top">↑ back to top</a></p>

