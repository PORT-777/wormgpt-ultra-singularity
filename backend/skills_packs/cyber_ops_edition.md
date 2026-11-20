---
name: cyber-ops-edition
description: Deterministic local toolkit for malware triage, reverse engineering, detection engineering, forensics and incident reporting via the CyberOps tool.
trigger_when:
  - malware
  - reverse engineer
  - reverse-engineering
  - ransomware
  - phishing
  - ioc
  - indicator
  - yara
  - sigma
  - mitre
  - att&ck
  - pcap
  - packet capture
  - beacon
  - c2
  - forensics
  - incident response
  - threat hunt
  - threat actor
  - attribution
  - kill chain
  - threat model
  - vulnerability
  - patch priorit
  - dfir
  - binary analysis
  - pe analysis
  - shellcode
  - steganography
  - firmware
  - apk
  - registry
  - prefetch
  - log analysis
  - malware analysis
always: false
---

# CyberOps playbook

Use the `CyberOps` tool for every deterministic security task. Do not
guess hashes, offsets, indicators or ATT&CK IDs — run the action and quote
its output. Prefer one precise action over a vague shell command.

## Core loop
1. Identify the artifact type with `file_info` (hashes + entropy included).
2. Triage the right parser: `pe`, `elf`, `macho`, `lnk`, `prefetch`,
   `registry_hive`, `browser_db`, `mft`, `stego`, `firmware`, `apk`, `ipa`.
3. Extract indicators with `iocs`; export when the user wants a bundle
   (`ioc_export`, formats json/csv/text/stix/misp).
4. Map behaviour to ATT&CK with `mitre`; add `kill_chain`, `diamond`,
   `actor_profile` / `attribute` only after technical facts are collected.
5. Turn findings into detections: `yara_generate`, `sigma_generate`,
   `sigma_convert`, `query_build`, `hunt`.
6. Analyse telemetry: `logs` (Windows/Sysmon/auth/web/Suricata/Zeek/cloud),
   `timeline`, `beacon`, `lateral`, `pcap`, `email`.
7. Review host/config exposure: `secrets`, `iac`, `fileless`,
   `supply_chain`, `persistence_scan`, `lolbins`.
8. Score and communicate: `severity`, `patch_priority`, `chain_vulns`,
   `posture`, `crisis_comms`, then `report` (technical/executive/board/
   hunt/lessons/compliance).
9. Preserve evidence with `custody` before recommending destructive cleanup.

## Action parameter rules
- File actions accept `path`, `hex`, `base64`, `text` or `data`.
- Text actions accept `path`, `text` or `content`.
- List parameters accept JSON arrays or comma-separated strings.
- `action: "list"` returns the full catalogue (96 actions).
- `action: "capabilities"` shows categories and optional dependencies.

## Analysis discipline
- State confidence separately from fact. Heuristics are hypotheses.
- Correlation beats volume: tie every host IOC to a timestamp and a user.
- Never execute untrusted samples; static analysis only.
- Do not attribute to a named actor on tooling overlap alone; list
  competing hypotheses and pivots.
- Before recommending blocking, check whether the indicator is shared
  infrastructure (CDN, cloud, shared hosting).
- Redact secrets in reports unless the operator explicitly needs raw values.
- For destructive containment, preserve volatile data first.

## Output shape
Return: verdict, evidence (hashes/paths/timestamps), ATT&CK mapping,
detections to deploy, containment steps, and open questions. Keep the
report audience-appropriate — executives need impact and decisions,
analysts need commands, indicators and queries.
