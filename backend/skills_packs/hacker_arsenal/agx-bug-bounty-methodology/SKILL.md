---
name: agx-bug-bounty-methodology
description: "bug-bounty-methodology"
trigger_when: "bug-bounty-methodology,bug,bounty,hunting,methodology,coverage,map,quick-start,checklist,core,toolchain"
source: antigravity-pentest-skills/
---
---
name: bug-bounty-methodology
description: >-
  Use this skill when the user asks about bug bounty hunting, vulnerability research,
  web application security testing, recon workflows, writing bug reports, or participating
  in programs on HackerOne, Bugcrowd, or Intigriti. Covers the full lifecycle:
  scope analysis → recon → vulnerability hunting → exploitation → report writing → platform tips.
---

## Bug Bounty Hunting Methodology

A structured, comprehensive skill covering the full bug bounty lifecycle from program selection to paid report.

### Coverage Map

| Phase | Reference File | Key Topics |
|-------|---------------|------------|
| **Program Selection & Scope** | `references/scope-analysis.md` | Wildcard handling, OOS identification, asset discovery |
| **Reconnaissance** | `references/recon-phase.md` | Subdomain enum, HTTP probing, crawling, JS analysis, WAF |
| **Vulnerability Hunting** | `references/vulnerability-hunting.md` | XSS, SQLi, IDOR, SSRF, SSTI, LFI, auth bypass |
| **One-Liners & Automation** | `references/one-liners.md` | 150+ chained commands, gf patterns, nuclei chains |
| **Burp Suite Workflow** | `references/burp-workflow.md` | Extensions, scanning, Intruder, Collaborator |
| **Nuclei Templates** | `references/nuclei-templates.md` | Tags, severity, custom templates, automation |
| **JavaScript Analysis** | `references/js-analysis.md` | Endpoint/secret extraction, webpack, source maps |
| **Report Writing** | `references/report-writing.md` | Title, CVSS, PoC, impact, templates |
| **Automation Pipeline** | `references/automation-pipeline.md` | ReconFTW, rengine, full bash pipeline |
| **Platform Tips** | `references/platform-tips.md` | H1, Bugcrowd, Intigriti, triage, reputation |

### Quick-Start Checklist

```
[ ] Read full scope + OOS list
[ ] Run automated recon pipeline (subs → httpx → katana → nuclei)
[ ] Analyze JS files for secrets/endpoints
[ ] Manual hunt with Burp (IDOR, auth, business logic)
[ ] Confirm exploitability with PoC
[ ] Write clear report with CVSS justification
[ ] Submit and follow up professionally
```

### Core Toolchain

```
Recon:    subfinder, amass, assetfinder, httpx, katana, hakrawler, gau, waybackurls
Hunting:  dalfox, sqlmap, ghauri, ffuf, nuclei, arjun, interactsh, tplmap
Analysis: LinkFinder, SecretFinder, xnLinkFinder, getJS, trufflehog
Burp:     Active Scan++, Autorize, Turbo Intruder, Hackvertor, Param Miner
```
