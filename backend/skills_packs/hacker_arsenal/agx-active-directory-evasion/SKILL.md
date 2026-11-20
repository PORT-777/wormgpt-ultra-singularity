---
name: agx-active-directory-evasion
description: "active-directory-evasion"
trigger_when: "active-directory-evasion,active,directory,evasion,stealth,attacks,skill,coverage,map"
source: antigravity-pentest-skills/
---
---
name: active-directory-evasion
description: >-
  Use this skill when executing stealthy Active Directory attacks, evading MDI (Microsoft Defender for Identity) / ATA,
  or bypassing AD monitoring. Covers OPSEC-safe Kerberoasting, AS-REP Roasting without noise, LDAP query throttling, and DC shadow manipulation.
---

## Active Directory Evasion & Stealth Attacks Skill

OPSEC-focused Active Directory exploitation, stealth enumeration, and identity defense bypasses.

### Coverage Map

| Reference File | Contents |
|---|---|
| [opsec-kerberoast.md](references/opsec-kerberoast.md) | Targeted Kerberoasting without triggering high-volume TGS request alerts |
| [stealth-ldap-enum.md](references/stealth-ldap-enum.md) | LDAP paging, avoiding honeypot accounts, throttled queries |
| [mdi-ata-evasion.md](references/mdi-ata-evasion.md) | Evading Microsoft Defender for Identity heuristics and honey-tokens |
