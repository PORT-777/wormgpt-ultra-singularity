---
name: int-ai-red-team-payload-obfuscation-token-smuggling
description: "Awesome AI Red Team section: Payload Obfuscation & Token Smuggling"
trigger_when: "ai-red-team,payload,obfuscation,token,smuggling"
source: awesome-ai-red-team
---
## 🐍 Payload Obfuscation & Token Smuggling

Where nobody's looking. Beat filters that only read plaintext — encode, hide, and smuggle.

- ⭐ **[P4RS3LT0NGV3 / Parseltongue (Pliny)](https://elder-plinius.github.io/P4RS3LT0NGV3/)** — The payload crafter. Encode/mutate text into leetspeak, base64, runes, invisible Unicode, variation selectors — plus "tokenade" grenades that explode into thousands of tokens.
- **[P4RS3LT0NGV3 — source](https://github.com/elder-plinius/P4RS3LT0NGV3)** — Repo: universal text transformation, encoding/decoding, promptcrafting.
- **[Parseltongue (BASI Labs) — browser extension](https://github.com/BASI-LABS/parseltongue)** — Real-time tokenization viz + text conversion (binary/base64/leetspeak/unicode). Live crafting inside the target UI. Extension quiet since early 2025.
- **[Emoji Smuggler (Paul Butler)](https://emoji.paulbutler.org/)** — Hide arbitrary text inside a single emoji via Unicode variation selectors. Invisible-instruction channel.
- **[OpenAI Tokenizer](https://platform.openai.com/tokenizer)** — See exactly how a payload tokenizes. Essential for building smuggling / token-expansion attacks.
- **[Cryptex OSS](https://github.com/m4xx101/cryptex-oss)** — 159 transforms, 36 mutators, 26 tool surfaces, and 19 red-team labs, plus one-shot Campaign mode with an ASR report. MIT.
- **[Data Exfiltration Attacks (Simon Willison)](https://simonwillison.net/tags/exfiltration-attacks/)** — Curated running log of zero-click exfil via markdown-image rendering + ASCII/Unicode smuggling. The other half of obfuscation: getting data OUT.
- **[Invisible Unicode Tags Playground (jthack)](https://josephthacker.com/invisible_prompt_injection)** — Convert text to invisible Unicode tag characters to smuggle hidden instructions past filters and humans.
- **[ASCII→Unicode Reducer (jthack)](https://josephthacker.com/unicode_reducer)** — Re-encode ASCII as compact Unicode lookalikes to defeat brittle string filters.
- **[TokenBreak](https://arxiv.org/abs/2506.07948)** — Token-manipulation smuggling past text-classifier guards: perturb text so the BPE/WordPiece guard misclassifies while the main model (and humans) still recover the meaning.
- **[PUZZLED](https://arxiv.org/abs/2508.01306)** — Mask harmful keywords as anagrams / crosswords / word-search — the model's own reasoning reconstructs the instruction, so raw-prompt scanners miss it. 88.8% ASR across 5 LLMs.
- **[Controlled-Release Prompting](https://arxiv.org/abs/2510.01529)** — Exploits the cheap-guard vs strong-model split: encode intent so the lightweight prompt guard can't decode it but the main LLM can. The resource-asymmetry bypass.

<p align="right"><a href="#top">↑ back to top</a></p>

