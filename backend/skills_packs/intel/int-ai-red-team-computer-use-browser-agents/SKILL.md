---
name: int-ai-red-team-computer-use-browser-agents
description: "Awesome AI Red Team section: Computer-Use & Browser Agents"
trigger_when: "ai-red-team,computer-use,browser,agents"
source: awesome-ai-red-team
---
## 🖱️ Computer-Use & Browser Agents

The agent is driving a real desktop or browser. Injection arrives as pixels, pages, and pop-ups, and the impact is a click, a shell, or an exfil.

Also scored elsewhere: VPI-Bench (Multimodal), WASP and OS-Harm (Benchmarks). Agentic-browser field notes: Brave and Guardio (People).

- ⭐ **[ZombAIs (Embrace The Red)](https://embracethered.com/blog/posts/2024/claude-computer-use-c2-the-zombais-are-coming/)** — Indirect prompt injection against Claude's computer-use agent that ends in a payload and command-and-control. The end-to-end chain.
- **[Attacking computer agents via pop-ups](https://arxiv.org/abs/2411.02391)** — On-screen pop-ups that vision-language computer agents click. 86% average click-through in OSWorld and VisualWebArena. Code is SALT-NLP/PopupAttack, quiet since late 2024.
- ⭐ **[RedTeamCUA](https://github.com/OSU-NLP-Group/RedTeamCUA)** — ICLR 2026 oral. Hybrid web-and-OS sandbox plus RTC-Bench for indirect injection against computer-use agents. Use it when the attack has to leave the browser and touch the desktop.
- **[OSWorld](https://github.com/xlang-ai/OSWorld)** — The desktop lab those attacks need: real applications, screenshot in, action out. NeurIPS 2024 benchmark, still maintained. Stand up a computer-use target you control.

<p align="right"><a href="#top">↑ back to top</a></p>

