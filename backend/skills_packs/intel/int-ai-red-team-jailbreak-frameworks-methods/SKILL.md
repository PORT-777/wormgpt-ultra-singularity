---
name: int-ai-red-team-jailbreak-frameworks-methods
description: "Awesome AI Red Team section: Jailbreak Frameworks & Methods"
trigger_when: "ai-red-team,jailbreak,frameworks,methods"
source: awesome-ai-red-team
---
## 🧨 Jailbreak Frameworks & Methods

Attack-technique implementations — when a scanner isn't enough and you need the actual method.

- **[Many-shot jailbreaking (Anthropic)](https://www.anthropic.com/research/many-shot-jailbreaking)** — Hundreds of in-context harmful Q&A pairs walk a model past alignment. No gradients, no suffix, just a long prompt.
- ⭐ **[Crescendo](https://arxiv.org/abs/2404.01833)** — Multi-turn jailbreak that starts benign and escalates. This is the attack PyRIT's Crescendo orchestrator implements.
- **[Skeleton Key (Microsoft)](https://www.microsoft.com/en-us/security/blog/2024/06/26/mitigating-skeleton-key-a-new-type-of-generative-ai-jailbreak-technique/)** — One prompt that asks the model to "augment" rather than refuse, then stamps later answers with a warning. A policy bypass, not a suffix.
- **[TAP — Tree of Attacks with Pruning](https://arxiv.org/abs/2312.02119)** — An attacker model branches jailbreaks and drops the ones an evaluator rejects. Black-box and query-efficient; PyRIT ships it.
- **[Simple adaptive attacks (Andriushchenko et al.)](https://arxiv.org/abs/2404.02151)** — Breaks leading safety-aligned models, and a lot of published defenses, with straightforward adaptive search. A guardrail paper with no adaptive attack is not a result.
- **[EasyJailbreak](https://github.com/EasyJailbreak/EasyJailbreak)** — Unified framework: 11 classic attacks (AutoDAN, PAIR, GPTFuzz, DeepInception…) via Selector/Mutator/Constraint/Evaluator.
- **[GPTFuzz](https://github.com/hubertyoo/GPTFuzz)** — AFL-inspired black-box jailbreak fuzzer; auto-generates jailbreak templates from seeds.
- **[Open-Prompt-Injection](https://github.com/liu00222/Open-Prompt-Injection)** — USENIX Sec'24 benchmark: 5 injection attacks × 10 defenses × 10 LLMs × 7 tasks.
- **[HouYi](https://github.com/LLMSecurity/HouYi)** — Automated black-box prompt-injection framework for LLM-integrated apps.
- **[JailbreakZoo](https://github.com/Allen-piexl/JailbreakZoo)** — Catalog of jailbreak methods and papers for LLMs and multimodal models. Repo quiet since 2024.
- **[ArtPrompt (ASCII-art jailbreak)](https://github.com/uw-nsl/ArtPrompt)** — ACL'24 — encode blocked words as ASCII art to slip past alignment. Cheap, black-box.
- **[AutoDAN-Turbo](https://github.com/SaFo-Lab/AutoDAN-Turbo)** — ICLR'25 — lifelong agent that self-discovers jailbreak strategies from scratch.
- ⭐ **[PAIR — Jailbreaking in 20 Queries](https://github.com/patrickrchao/JailbreakingLLMs)** — Attacker-LLM iteratively refines a jailbreak against a black-box target; breaks GPT-4 in <20 queries. The efficient classic.
- **[MasterKey](https://arxiv.org/abs/2307.08715)** — Automated jailbreaks that transferred across multiple production LLM chatbots. Use it when the target is a vendor API and its filter, not a local weight file.
- **[Best-of-N Jailbreaks](https://arxiv.org/abs/2412.03556)** — Black-box: sample many augmented prompts, keep the ones that slip through. Dead simple, brutally effective across modalities.
- **[Jailbroken: How Does LLM Safety Training Fail?](https://arxiv.org/abs/2307.02483)** — Why aligned models break — competing objectives & mismatched generalization. The mental model behind most jailbreaks.
- **[CipherChat](https://github.com/RobustNLP/CipherChat)** — Jailbreak via ciphers — GPT-4 is "too smart to be safe": encode the chat, bypass the filter.
- **[DeepInception](https://github.com/tmlr-group/DeepInception)** — Nested-scene "hypnosis" jailbreak — wrap the ask in a story-within-a-story to erode refusals. Research code, quiet since early 2024.
- **[ReNeLLM — nested jailbreak](https://github.com/NJUNLP/ReNeLLM)** — "Wolf in sheep's clothing": generalized prompt rewriting + scenario nesting. Cheap and effective.

<p align="right"><a href="#top">↑ back to top</a></p>

