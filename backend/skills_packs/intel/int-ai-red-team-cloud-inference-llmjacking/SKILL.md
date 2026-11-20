---
name: int-ai-red-team-cloud-inference-llmjacking
description: "Awesome AI Red Team section: Cloud, Inference & LLMjacking"
trigger_when: "ai-red-team,cloud,inference,llmjacking"
source: awesome-ai-red-team
---
## ☁️ Cloud, Inference & LLMjacking

Where AI meets your cloud-security edge. SSRF a model endpoint, steal the token, ride the quota — or just hit the inference server that was never meant to face the network.

- **[HackTricks — Cloud SSRF → metadata creds](https://hacktricks.wiki/pentesting-web/ssrf-server-side-request-forgery/cloud-ssrf.html)** — SSRF an AI web app → hit the metadata service → steal the service-account token. AWS/Azure/GCP.
- **[Unit 42 — Autonomous AI attacks the cloud](https://unit42.paloaltonetworks.com/autonomous-ai-cloud-attacks/)** — Building an autonomous multi-agent cloud-offense system: recon → SSRF → token theft → lateral.
- **[Unit 42 — Attacking Bedrock multi-agent apps](https://unit42.paloaltonetworks.com/amazon-bedrock-multiagent-applications/)** — Abusing Amazon Bedrock multi-agent deployments. Concrete agentic-cloud tradecraft.
- **[Why Attackers Target AWS Bedrock (Vectra)](https://www.vectra.ai/resources/threat-briefing-why-attackers-target-aws-bedrock)** — LLMjacking + Bedrock abuse: stolen creds → invoke hosted models on the victim's bill.
- ⭐ **[LLMjacking (Sysdig)](https://www.sysdig.com/blog/llmjacking-stolen-cloud-credentials-used-in-new-ai-attack/)** — The report that coined "LLMjacking": stolen cloud creds proxied into hosted LLMs (Bedrock/Azure), victim foots up to ~$46k/day. The origin story of the category.
- **[ShadowRay (Oligo)](https://www.oligo.security/blog/shadowray-attack-ai-workloads-actively-exploited-in-the-wild)** — In-the-wild campaign against exposed Ray dashboards via disputed CVE-2023-48022. An open Ray port on an AI cluster is shared infrastructure, not a dev convenience.
- ⭐ **[Probllama — Ollama RCE (Wiz)](https://www.wiz.io/blog/probllama-ollama-vulnerability-cve-2024-37032)** — CVE-2024-37032, unauthenticated remote code execution in Ollama. An exposed Ollama port is a shell.
- **[LiteLLM MCP command injection (CSA)](https://labs.cloudsecurityalliance.org/research/csa-research-note-litellm-cve-2026-42271-ai-gateway-exploita/)** — CVE-2026-42271: command injection on LiteLLM's MCP test endpoints, chained with Starlette's BadHost auth bypass (CVE-2026-48710) to unauthenticated RCE. Added to CISA KEV in June 2026.
- **[Mind Your Key — LLM API Key Leakage in iOS Apps](https://arxiv.org/abs/2606.12212)** — 282 of 444 LLM-enabled iOS apps leaked exploitable credentials (plaintext keys, unauthenticated proxies, JWTs). The feeder channel for LLMjacking.

<p align="right"><a href="#top">↑ back to top</a></p>

