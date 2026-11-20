---
name: agx-macos-ios-internals
description: "macos-ios-internals"
trigger_when: "macos-ios-internals,macos,ios,security,internals,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: macos-ios-internals
description: >-
  Use this skill when researching macOS and iOS platform security, reverse engineering Mach-O binaries, analyzing XNU kernel extensions,
  or testing mobile/desktop Apple security. Covers SIP bypass, Gatekeeper, TCC, Entitlements, Mach ports, and Frida on iOS/macOS.
---

## macOS & iOS Security Internals Skill

Apple operating system security models, XNU kernel concepts, Mach IPC, and security control bypasses.

### Coverage Map

| Reference File | Contents |
|---|---|
| [tcc-sip-gatekeeper.md](references/tcc-sip-gatekeeper.md) | TCC permission bypasses, SIP rules, Gatekeeper quarantine flags |
| [macho-entitlements.md](references/macho-entitlements.md) | Mach-O binary format, codesigning, entitlements parsing, dyld insertion |
| [mach-ports-ipc.md](references/mach-ports-ipc.md) | Mach messaging, port voucher vulnerabilities, IPC security |
