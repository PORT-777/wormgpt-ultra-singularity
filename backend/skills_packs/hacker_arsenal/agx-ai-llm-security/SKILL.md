---
name: agx-ai-llm-security
description: "ai-llm-security"
trigger_when: "ai-llm-security,llm,security,red,teaming,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: ai-llm-security
description: >-
  Use this skill when auditing AI/ML models, performing red teaming against Large Language Models (LLMs),
  or analyzing AI application vulnerabilities. Covers Direct & Indirect Prompt Injections, Jailbreaking,
  RAG exfiltration, Training Data Poisoning, Insecure Output Handling, and the OWASP Top 10 for LLM.
---

## AI & LLM Security Red Teaming Skill

Comprehensive skill for vulnerability assessment and adversary simulation against AI, LLM applications, and RAG architectures.

### Coverage Map

| Reference File | Contents |
|---|---|
| [prompt-injection.md](references/prompt-injection.md) | Direct and Indirect Prompt Injection techniques, payload smuggling |
| [jailbreaking-llms.md](references/jailbreaking-llms.md) | Persona adoption, multi-language bypasses, DAN/Do Anything Now techniques |
| [rag-data-exfiltration.md](references/rag-data-exfiltration.md) | Attacking Retrieval-Augmented Generation systems, vector DB leaks |
| [owasp-llm-top10.md](references/owasp-llm-top10.md) | OWASP LLM Top 10 vulnerabilities, insecure output handling, model denial of service |
