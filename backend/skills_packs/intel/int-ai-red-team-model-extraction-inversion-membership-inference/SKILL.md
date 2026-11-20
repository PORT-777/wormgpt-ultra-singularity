---
name: int-ai-red-team-model-extraction-inversion-membership-inference
description: "Awesome AI Red Team section: Model Extraction, Inversion & Membership Inference"
trigger_when: "ai-red-team,model,extraction,inversion,membership,inference"
source: awesome-ai-red-team
---
## 🔓 Model Extraction, Inversion & Membership Inference

API access is enough. Steal a training row, a prompt, or a slice of the weights — then put a number on it.

- **[Extracting Training Data from LLMs (Carlini et al.)](https://arxiv.org/abs/2012.07805)** — The seminal training-data extraction attack — memorization = leakage. Foundation of model privacy attacks.
- ⭐ **[Scalable Extraction from Production LMs (Nasr, Carlini et al.)](https://arxiv.org/abs/2311.17035)** — Training data, including PII, pulled out of production ChatGPT. The extraction result you cite when a client says "the API doesn't leak."
- **[Stealing Part of a Production Language Model](https://arxiv.org/abs/2403.06634)** — Recover a production model's embedding projection layer through API queries. Model theft without the weight file.
- **[vec2text — Language Model Inversion](https://github.com/vec2text/vec2text)** — Reconstruct input text from embeddings. Invert the model; leak what it saw.
- **[Membership Inference (Shokri et al.)](https://arxiv.org/abs/1610.05820)** — The attack that defined the class: decide whether a point was in the training set from the model's outputs.
- **[LiRA — Membership Inference From First Principles](https://arxiv.org/abs/2112.03570)** — Carlini et al.'s likelihood-ratio test. The method later papers are measured against; calibrated, and it works on harder targets.
- **[Privacy Meter](https://github.com/privacytrustlab/ml_privacy_meter)** — Open-source library for running membership-inference audits. Use it when the question is whether a row trained the model. Repo quiet since early 2025.

<p align="right"><a href="#top">↑ back to top</a></p>

