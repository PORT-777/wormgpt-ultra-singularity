---
name: agx-web-hacking-advanced
description: "web-hacking-advanced"
trigger_when: "web-hacking-advanced,web,hacking,advanced,skill,coverage,map,quick,reference,api,endpoint,discovery"
source: antigravity-pentest-skills/
---
---
name: web-hacking-advanced
description: >-
  Use this skill for advanced web application penetration testing, API security
  testing, web recon automation, and web vulnerability hunting beyond basic payloads.
  Covers: API endpoint discovery and fuzzing, GraphQL security, advanced Burp Suite
  workflows, custom wordlist generation, web reconnaissance toolchains (reaper,
  lit-bb-hack-tools, aquattro, wolf), HTTP parameter analysis, authentication testing,
  web cache attacks, request smuggling, business logic flaws, and advanced methodology
  for both manual and automated web security assessments. Use alongside payloads-all-the-things
  for complete web hacking coverage.
---

## Web Hacking Advanced Skill

Advanced web application penetration testing techniques, tools, and methodology.
Complements the `payloads-all-the-things` skill with tool workflows and deeper methodology.

### Coverage Map

| Reference File | Contents |
|---------------|----------|
| [api-testing.md](references/api-testing.md) | REST API, GraphQL, gRPC security testing |
| [recon-automation.md](references/recon-automation.md) | Advanced recon toolchain, JS link finding, endpoint discovery |
| [authentication-testing.md](references/authentication-testing.md) | OAuth, JWT, session management, MFA bypass testing |
| [wordlists-fuzzing.md](references/wordlists-fuzzing.md) | Wordlist selection, generation, ffuf/feroxbuster mastery |
| [burp-advanced.md](references/burp-advanced.md) | Burp Suite Pro advanced features, extensions, custom scans |
| [cache-attacks.md](references/cache-attacks.md) | Web cache poisoning, cache deception, CDN attacks |
| [business-logic.md](references/business-logic.md) | Logic flaws, race conditions, price manipulation |
| [http-tricks.md](references/http-tricks.md) | HTTP method override, header injection, host header attacks |
| [web-tools-reference.md](references/web-tools-reference.md) | Tool-specific guides: reaper, wolf, aquattro, lit-bb |
| [methodology-checklist.md](references/methodology-checklist.md) | Complete web pentest checklist, OWASP WSTG mapping |

### Quick Reference

```bash
## API endpoint discovery
python3 LinkFinder.py -i https://target.com -d -o cli
katana -u https://target.com -jc -d 3 -o endpoints.txt
arjun -u https://target.com/api/v1/endpoint -m GET

## ffuf directory fuzzing
ffuf -w /opt/SecLists/Discovery/Web-Content/raft-large-files.txt \
     -u https://target.com/FUZZ -mc 200,301,302,403 -o output.json

## Nuclei web checks
nuclei -u https://target.com -tags xss,sqli,ssrf,rce,exposure -severity high,critical

## GraphQL introspection
curl -X POST https://target.com/graphql \
     -H 'Content-Type: application/json' \
     -d '{"query":"{ __schema { types { name } } }"}'
```
