---
name: osint-passive
description: "Passive reconnaissance sweep: CT logs, archive, RDAP, DNS, fingerprint — evidence tables only."
trigger_when:
  - osint
  - recon
  - domain
  - subdomain
  - whois
  - footprint
  - investigate
  - تحقيق
  - سكان
  - اسكان
  - ريكون
  - دومين
  - فحص
  - معلومات
  - دمن
  - توط
---

# Passive OSINT sweep

TOOLS in order (OsintToolkit handles all of them, no API keys):
1. `action=all` for one-shot: DNS → cert-transparency subdomains →
   RDAP registration → Wayback history → HTTP fingerprint.
2. Follow-up precision calls only where the sweep found signal:
   `certs` again with a wider max, targeted `probe` of a flagged host.

DISCIPLINE:
- PASSIVE first: everything above touches only public records.
- EVIDENCE TABLE: every claim = the exact record it came from
  (crt entry, RDAP event date, CDX line). No "probably registered...".
- Sort subdomains by suspicion (admin/panel/api/dev/staging/test/vpn
  first) and mark each as UNVERIFIED until probed.
- Old endpoints from the Archive = live-attack-surface leads, labeled
  by capture year — never presented as currently live.
- Emails harvested are contact-surface, not verified identities.
- Cross-check the fingerprint against the whois org for mismatches
  (CDN/proxy chain); state the chain, not a guess.
- End with a NEXT-STEP list: what active probing would confirm which
  guess (and that it needs the operator's authorization).
