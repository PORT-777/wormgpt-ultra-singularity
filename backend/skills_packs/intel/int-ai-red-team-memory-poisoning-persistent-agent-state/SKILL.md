---
name: int-ai-red-team-memory-poisoning-persistent-agent-state
description: "Awesome AI Red Team section: Memory Poisoning & Persistent Agent-State"
trigger_when: "ai-red-team,memory,poisoning,persistent,agent-state"
source: awesome-ai-red-team
---
## 🧠 Memory Poisoning & Persistent Agent-State

The 2026 frontier. Don't jailbreak the model — poison its persistent state, then let normal retrieval, personalization, or tool-selection turn that into future behavior. One write, many sessions.

- ⭐ **[Sleeper Memory Poisoning (Hidden in Memory)](https://arxiv.org/abs/2605.15338)** — 2026's headline agent attack: one poisoned doc writes a dormant false "memory" that fires in later sessions — 99.8% insertion on GPT-5.5. Injection goes from one-shot to persistent.
- **[Poison Once, Exploit Forever (eTAMP)](https://arxiv.org/abs/2604.02623)** — Web agent stores a contaminated trajectory from a manipulated page, then retrieves it on a different site/task later. Cross-session memory poisoning, no direct memory access.
- **[MemMorph](https://arxiv.org/abs/2605.26154)** — Tool hijacking via memory poisoning: benign-looking records make the agent "infer" the attacker's preferred tool — up to 85.9% from 3 injected records.
- **[Visual Inception](https://arxiv.org/abs/2604.16966)** — Multimodal memory poisoning: user-uploaded images with semantic triggers steer an agentic recommender's later planning (~85% goal-hit).
- **[MPBench — Memory Poisoning Benchmark](https://arxiv.org/abs/2606.04329)** — Systematic study of how untrusted input becomes trusted memory: 4 memory-write channels, 9 structural weaknesses. The map for the memory-poisoning attack class.
- **[Appreciation Teaches Unauthorized Execution](https://arxiv.org/abs/2610.39122)** — A personal agent that learns from "do what the document says" gets worse at indirect injection later. Skill evolution raised ASR by 14–49 points over the unevolved agent. Official code is SaFo-Lab/Evolve-IPI.

<p align="right"><a href="#top">↑ back to top</a></p>

