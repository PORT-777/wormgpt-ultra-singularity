---
name: int-ai-red-team-multimodal-vision-audio-attacks
description: "Awesome AI Red Team section: Multimodal / Vision / Audio Attacks"
trigger_when: "ai-red-team,multimodal,vision,audio,attacks"
source: awesome-ai-red-team
---
## 🖼️ Multimodal / Vision / Audio Attacks

Images, audio, and video are the softest injection channel. Everyone tests text; test the rest.

- ⭐ **[FigStep](https://github.com/CryptoAILab/FigStep)** — Typographic images that carry the instruction a text filter would block. AAAI 2025 oral, black-box, cheap. The reason a vision test is not optional.
- **[AdvWave](https://arxiv.org/abs/2412.08608)** — ICLR 2025. Adversarial audio that jailbreaks large audio-language models while sounding like ordinary noise. Use it when the target accepts a waveform, not only text.
- **[JailBreakV-28K](https://github.com/SaFo-Lab/JailBreakV_28K)** — 28k text-image jailbreak pairs; tests transferability of LLM jailbreaks to MLLMs. Go-to benchmark.
- **[MM-SafetyBench](https://github.com/isXinLiu/MM-SafetyBench)** — ECCV'24 image-based jailbreak benchmark: 13 categories, 1,680 samples.
- **[Awesome-MLLM-Safety](https://github.com/isXinLiu/Awesome-MLLM-Safety)** — Curated survey of multimodal LLM safety attacks & defenses.
- **[OmniSafeBench-MM](https://arxiv.org/abs/2512.06589)** — Unified multimodal attack-defense toolbox: 13 attacks, 15 defenses, 9 risk domains.
- **[Adversarial Attacks on MLLMs — Survey](https://arxiv.org/abs/2603.27918)** — Comprehensive 2026 survey of the multimodal attack surface.
- **[OpenRT](https://github.com/AI45Lab/OpenRT)** — Open-source red-teaming framework for multimodal LLMs — 42+ attack methods (ArtPrompt, Past Tense, LAA, imperceptible jailbreak).
- **[Image Hijacks](https://github.com/euanong/image-hijacks)** — Adversarial images that control a VLM's behavior at runtime — steer outputs with a crafted picture. Research code, quiet since 2023.
- **[UltraBreak](https://arxiv.org/abs/2602.01025)** — Universal, transferable jailbreak for vision-language models — regularizes the adversarial image so it survives black-box targets instead of overfitting one surrogate.
- **[MemJack — "Every Picture Tells a Dangerous Story"](https://arxiv.org/abs/2604.12616)** — Memory-augmented multi-agent jailbreak mapping entities in unmodified natural images to malicious intent — 71% ASR on Qwen3-VL (→90% extended). Ships MemJack-Bench (113k trajectories).
- ⭐ **[VPI-Bench](https://arxiv.org/abs/2506.02456)** — Visual prompt injection against computer-use agents: instructions embedded in rendered UIs across 5 platforms — CUAs deceived up to 51%, browser-use agents up to 100%. DOM-text sanitization isn't enough.
- **[GRM — Audio LLM Jailbreak](https://arxiv.org/abs/2604.09222)** — Utility-aware audio jailbreak: perturbs only the Mel bands that drive jailbreak success while preserving transcription/QA utility — 88% average ASR across 4 audio LLMs.

<p align="right"><a href="#top">↑ back to top</a></p>

