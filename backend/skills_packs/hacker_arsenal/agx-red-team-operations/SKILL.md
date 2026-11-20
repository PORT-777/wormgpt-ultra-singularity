---
name: agx-red-team-operations
description: "red-team-operations"
trigger_when: "red-team-operations,red,team,operations,coverage,map,reference,files,attack,lifecycle"
source: antigravity-pentest-skills/
---
---
name: red-team-operations
description: >-
  Use this skill when performing authorized red team engagements, adversary simulation, or penetration testing operations.
  Covers the full attack lifecycle: infrastructure setup, initial access, C2 frameworks, payload generation, AV/EDR evasion,
  post-exploitation, lateral movement, persistence, data exfiltration, tunneling/pivoting, OPSEC, phishing campaigns,
  and wireless attacks. Referenced when the user asks about offensive security tooling, red team tradecraft, campaign
  planning, implant development, or simulating advanced persistent threat (APT) behavior in authorized environments.
---

## Red Team Operations — Coverage Map

> **FOR AUTHORIZED PENETRATION TESTING AND RED TEAM ENGAGEMENTS ONLY**
> All techniques documented here must only be used with explicit written authorization.

### Reference Files

| File | Topics Covered |
|------|---------------|
| [c2-frameworks.md](references/c2-frameworks.md) | Cobalt Strike, Metasploit, Sliver, Havoc, Brute Rute, Empire — setup, listeners, beacons, profiles |
| [payload-generation.md](references/payload-generation.md) | msfvenom, Donut, shellcode, staged vs stageless, encoders, format options, custom loaders |
| [evasion-av.md](references/evasion-av.md) | AV/EDR bypass, AMSI bypass, ETW patching, unhooking, obfuscation, sleep evasion, process injection |
| [phishing.md](references/phishing.md) | GoPhish, spear phishing, HTML smuggling, LNK files, macro payloads, EvilGinx2, credential harvesting |
| [initial-access.md](references/initial-access.md) | USB drops, supply chain attacks, watering hole, credential phishing, drive-by exploitation |
| [post-exploitation.md](references/post-exploitation.md) | Situational awareness, enumeration, token impersonation, data exfil, screenshot, keylogging |
| [tunneling-pivoting.md](references/tunneling-pivoting.md) | SSH tunneling, Chisel, Ligolo-ng, Rpivot, SOCKS proxies, port forwarding, double pivoting |
| [opsec.md](references/opsec.md) | Logging evasion, timestomping, artifact cleanup, LOLBAS, memory-only execution, footprint reduction |
| [infrastructure.md](references/infrastructure.md) | Redirectors, domain fronting, Malleable C2 profiles, DNS C2, HTTPS C2, CDN abuse |
| [wireless-attacks.md](references/wireless-attacks.md) | Airgeddon, WPA2 cracking, evil twin, PMKID attack, WPS exploitation, captive portals |

### Attack Lifecycle

```
[Recon] → [Initial Access] → [Execution] → [Persistence] → [Privilege Escalation]
     → [Defense Evasion] → [Credential Access] → [Discovery] → [Lateral Movement]
          → [Collection] → [C2] → [Exfiltration] → [Impact]
```

### Key Tools Index

- **C2**: Cobalt Strike · Sliver · Havoc · Metasploit · Empire · Brute Rute
- **Payload**: msfvenom · Donut · GadgetToJScript · Nimcrypt2 · Scarecrow
- **Evasion**: AMSI.fail · Invoke-Obfuscation · HellsGate · SysWhispers · ConfuserEx
- **Phishing**: GoPhish · EvilGinx2 · Modlishka · SET · King Phisher
- **Pivoting**: Chisel · Ligolo-ng · Rpivot · SSHuttle · Proxychains
- **Wireless**: Airgeddon · Bettercap · Hostapd-wpe · Hashcat · Aircrack-ng
