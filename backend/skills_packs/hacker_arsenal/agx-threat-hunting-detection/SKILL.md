---
name: agx-threat-hunting-detection
description: "threat-hunting-detection"
trigger_when: "threat-hunting-detection,threat,hunting,detection,engineering,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: threat-hunting-detection
description: >-
  Use this skill when developing detection engineering rules, threat hunting in SIEM/EDR logs, or writing Sigma and YARA-L rules.
  Covers Sysmon event analysis, Windows Event Log hunting (4624, 4688, 7045), MITRE ATT&CK mapping, and Sigma rule syntax.
---

## Threat Hunting & Detection Engineering Skill

Log analysis, behavioral threat hunting, SIEM query building, and detection rule creation.

### Coverage Map

| Reference File | Contents |
|---|---|
| [sysmon-event-hunting.md](references/sysmon-event-hunting.md) | Sysmon Event IDs (1: Process Creation, 3: Network, 8: CreateRemoteThread, 10: ProcessAccess) |
| [sigma-rules-authoring.md](references/sigma-rules-authoring.md) | Writing generic Sigma rules and converting to Splunk/Elastic/QRadar |
| [windows-event-ids.md](references/windows-event-ids.md) | Key Security Event IDs for threat hunting (4624, 4672, 4688, 4768, 7045) |
