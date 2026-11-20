---
name: int-ai-red-team-rag-vector-db-security
description: "Awesome AI Red Team section: RAG & Vector DB Security"
trigger_when: "ai-red-team,rag,vector,security"
source: awesome-ai-red-team
---
## 📚 RAG & Vector DB Security

RAG is the enterprise default — and its knowledge base is an injection sink.

- ⭐ **[PoisonedRAG](https://github.com/sleeepeer/PoisonedRAG)** — USENIX Sec'25 — first knowledge-corruption attack on RAG. 90% success with 5 poisoned docs.
- ⭐ **[AgentPoison](https://github.com/AI-secure/AgentPoison)** — NeurIPS 2024. Backdoor a RAG store or long-term memory so a trigger query retrieves the attacker's demo, at under a 0.1% poison rate. Official code, still updated.
- **[Phantom](https://arxiv.org/abs/2405.20485)** — One poisoned document, retrieved only when the query contains a chosen trigger, then an adversarial suffix steers the answer. Demonstrated on NVIDIA Chat with RTX.
- **[ConfusedPilot](https://arxiv.org/abs/2408.04870)** — Confused-deputy / access-control bypass in RAG (demoed on M365 Copilot).
- **[RAG Poisoning POC (Prompt Security)](https://github.com/prompt-security/RAG_Poisoning_POC)** — Stealthy injection/poisoning via vector-DB embeddings.
- **[RAG Data Poisoning — Promptfoo](https://www.promptfoo.dev/blog/rag-poisoning/)** — Clear practitioner explainer of RAG poisoning mechanics and testing.
- **[SilentRetrieval](https://arxiv.org/abs/2605.28074)** — Semantically-preserving RAG corpus poisoning that survives fluency/perplexity screening — retrieval hijack with one poisoned doc per query; transfers to unseen retrievers (ColBERT + commercial embeddings).
- **[PIDP-Attack](https://arxiv.org/abs/2603.25164)** — Compound RAG attack: inference-time prompt injection + poisoned passages together, without knowing the exact query. Beats PoisonedRAG by 4–16 points across 8 LLMs.
- **[RefineRAG](https://arxiv.org/abs/2604.07403)** — Word-level RAG poisoning: generate harmful seeds, then optimize wording with the retriever in the loop — 90% success on Natural Questions while killing grammar/repetition artifacts.
- **[M3Att — Medical Multimodal RAG Poisoning](https://arxiv.org/abs/2605.10253)** — Covert, clinically-plausible misinformation + paired visual triggers that promote retrieval in medical multimodal RAG. Needs provenance + image integrity, not just answer-level safety.

<p align="right"><a href="#top">↑ back to top</a></p>

