---
name: agx-digital-forensics-dfir
description: "digital-forensics-dfir"
trigger_when: "digital-forensics-dfir,digital,forensics,incident,response,dfir,coverage,map,quick,decision,tree"
source: antigravity-pentest-skills/
---
---
name: digital-forensics-dfir
description: >-
  Use this skill when the user needs Digital Forensics and Incident Response (DFIR) assistance.
  Covers memory forensics with Volatility3, disk/filesystem forensics with Autopsy and Sleuthkit,
  Windows artifact analysis (registry, event logs, prefetch, shellbags, LNK files, USN journal),
  log analysis and threat hunting with Chainsaw/Hayabusa/Sigma rules, timeline analysis with
  plaso/log2timeline and Timesketch, network forensics with Wireshark/Zeek/tcpdump, mobile
  forensics with Andriller/ADB, Linux live response with UAC, incident response playbooks,
  malware artifact hunting, MITRE ATT&CK mapping, and IOC-based threat hunting. Use when
  investigating breaches, performing triage, building forensic timelines, or hunting threats.
---

## Digital Forensics & Incident Response (DFIR)

### Coverage Map

| Domain | Tools | References |
|--------|-------|------------|
| Memory Forensics | Volatility3, MemProcFS, Rekall | [memory-forensics.md](references/memory-forensics.md) |
| Windows Artifacts | RegRipper, LECmd, PECmd, ShellBagsExplorer | [windows-artifacts.md](references/windows-artifacts.md) |
| Log Analysis | Chainsaw, Hayabusa, python-evtx, Sigma | [log-analysis.md](references/log-analysis.md) |
| Disk Forensics | Autopsy, Sleuthkit, FTK, PhotoRec | [disk-forensics.md](references/disk-forensics.md) |
| Network Forensics | Wireshark, Zeek, tcpdump, NetworkMiner | [network-forensics.md](references/network-forensics.md) |
| Incident Response | IR Playbooks, Evidence Collection, Triage | [incident-response.md](references/incident-response.md) |
| Timeline Analysis | log2timeline/plaso, Timesketch, mactime | [timeline-analysis.md](references/timeline-analysis.md) |
| Mobile Forensics | Andriller, ADB, MVT, iLEAPP | [mobile-forensics.md](references/mobile-forensics.md) |
| Artifact Locations | Windows/Linux/macOS artifact paths | [artifact-locations.md](references/artifact-locations.md) |
| Threat Hunting | MITRE ATT&CK, IOC hunting, Turbinia | [threat-hunting.md](references/threat-hunting.md) |

### Quick Decision Tree

```
Incident Type?
├── Malware/Compromise → memory-forensics.md + windows-artifacts.md + threat-hunting.md
├── Insider Threat    → windows-artifacts.md + artifact-locations.md + log-analysis.md
├── Data Exfiltration → network-forensics.md + disk-forensics.md + timeline-analysis.md
├── Log Review        → log-analysis.md + threat-hunting.md
├── Full IR           → incident-response.md → all references
├── Mobile Device     → mobile-forensics.md
└── Timeline Build    → timeline-analysis.md + disk-forensics.md
```

### Key Repositories

- **Volatility3**: https://github.com/volatilityfoundation/volatility3
- **Chainsaw**: https://github.com/WithSecureLabs/chainsaw
- **Autopsy/Sleuthkit**: https://github.com/sleuthkit/autopsy + https://github.com/sleuthkit/sleuthkit
- **Timesketch**: https://github.com/google/timesketch
- **Hayabusa**: https://github.com/Yamato-Security/hayabusa
- **Plaso/log2timeline**: https://github.com/log2timeline/plaso
- **Andriller**: https://github.com/den4uk/andriller
- **UAC**: https://github.com/tclahr/uac
- **Hindsight**: https://github.com/obsidianforensics/hindsight
- **USBRip**: https://github.com/snovvcrash/usbrip
- **RecoverPy**: https://github.com/PabloLec/RecoverPy
- **Sysmon Config**: https://github.com/ion-storm/sysmon-config
- **python-evtx**: https://github.com/williballenthin/python-evtx
- **Turbinia**: https://github.com/google/turbinia
- **Digital Forensics Lab**: https://github.com/frankwxu/digital-forensics-lab
