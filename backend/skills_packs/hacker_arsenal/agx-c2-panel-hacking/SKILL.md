---
name: agx-c2-panel-hacking
description: "c2-panel-hacking"
trigger_when: "c2-panel-hacking,panel,hacking,malware,infrastructure,auditing,coverage,map,disclaimer"
source: antigravity-pentest-skills/
---
---
name: c2-panel-hacking
description: >-
  Use this skill when auditing, penetration testing, or finding vulnerabilities in C2 (Command & Control)
  web panels, infostealer backend panels, botnet admin dashboards, or malware infrastructure.
  Covers vulnerability hunting in PHP/Node.js/Python/Go malware panels (SQLi, Auth Bypass, RCE, Arbitrary File Upload),
  reversing C2 APIs, TAKEOVER of stealer backends, tracking threat actors via panel leaks, and defensive counter-attacks.
---

## C2 Panel Hacking & Malware Infrastructure Auditing

Specialized skill focused on attacking, auditing, and finding vulnerabilities in malware Command & Control (C2) web panels, stealer administrative backends, and botnet infrastructure.

### Coverage Map

| Reference File | Contents |
|---|---|
| [c2-panel-vulns.md](references/c2-panel-vulns.md) | Common vulnerabilities in malware panels (SQLi, Auth Bypass, File Upload, RCE) |
| [stealer-panel-analysis.md](references/stealer-panel-analysis.md) | Analysis of Lumma, RedLine, XWorm, DarkCrystal (DCRat) PHP/Node backends |
| [auth-bypass-c2.md](references/auth-bypass-c2.md) | Bypassing authentication in leaked C2 panels (loose comparisons, hardcoded secrets) |
| [sqli-in-malware-panels.md](references/sqli-in-malware-panels.md) | SQL Injection patterns in botnet loggers and admin panels |
| [rce-c2-takeover.md](references/rce-c2-takeover.md) | Remote Code Execution techniques on C2 servers for infrastructure takeover |
| [c2-api-emulation.md](references/c2-api-emulation.md) | Emulating bot requests to flood, poison, or sinkhole C2 servers |
| [panel-fingerprinting.md](references/panel-fingerprinting.md) | Shodan/Fofa/Censys queries for discovering C2 admin panels online |
| [deobfuscating-panel-code.md](references/deobfuscating-panel-code.md) | Deobfuscating ionCube, sourceguardian, hidden PHP in leak panels |
| [sinkholing-botnets.md](references/sinkholing-botnets.md) | Sinkholing methodology, takeover of expired/abandoned C2 domains |
| [c2-countermeasures.md](references/c2-countermeasures.md) | Defense & threat intelligence extraction from compromised panels |

### Disclaimer
All techniques described herein are for authorized threat intelligence research, defensive counter-operations, CTF challenges, and sandbox analysis.
