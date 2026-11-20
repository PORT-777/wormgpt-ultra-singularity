---
name: agx-edr-evasion-advanced
description: "edr-evasion-advanced"
trigger_when: "edr-evasion-advanced,advanced,edr,evasion,bypass,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: edr-evasion-advanced
description: >-
  Use this skill when designing EDR evasion techniques, bypassing endpoint protection agents (CrowdStrike, Defender for Endpoint, SentinelOne),
  or analyzing userland/kernel hooks. Covers Direct Syscalls (SysWhispers3, HellsGate, HalosGate), Userland Unhooking,
  Sleep Obfuscation (Ekko, Kronos), ETW/AMSIPatching, and Process Injection evasion.
---

## Advanced EDR Evasion & AV Bypass Skill

Deep technical reference for defeating modern EDR detection engines and endpoint telemetry.

### Coverage Map

| Reference File | Contents |
|---|---|
| [direct-syscalls.md](references/direct-syscalls.md) | Hell's Gate, Halo's Gate, TartarusGate, SysWhispers3 implementation |
| [userland-unhooking.md](references/userland-unhooking.md) | Refreshing NTDLL, unhooking EDR DLLs from memory, suspended process copy |
| [sleep-obfuscation.md](references/sleep-obfuscation.md) | Ekko, Foliage, Kronos sleep obfuscation, memory encryptions |
| [amsea-etw-bypass.md](references/amsea-etw-bypass.md) | AMSI patching, ETW (Event Tracing for Windows) disabling, patching EtwEventWrite |
