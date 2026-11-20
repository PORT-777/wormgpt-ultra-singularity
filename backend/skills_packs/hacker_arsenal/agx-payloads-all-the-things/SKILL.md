---
name: agx-payloads-all-the-things
description: "payloads-all-the-things"
trigger_when: "payloads-all-the-things,payloadsallthethings,security,reference,skill,coverage,map,injection,attacks,web,application"
source: antigravity-pentest-skills/
---
---
name: payloads-all-the-things
description: >-
  Comprehensive web application security payloads and bypass techniques reference
  based on PayloadsAllTheThings (https://github.com/swisskyrepo/PayloadsAllTheThings).
  Use this skill when the user asks about security payloads, exploitation techniques,
  CTF challenges, penetration testing, web vulnerabilities (SQLi, XSS, SSRF, LFI, RFI,
  Command Injection, XXE, SSTI, JWT attacks, CORS, CSRF, OAuth, IDOR, etc.),
  or needs ready-to-use bypass strings and attack payloads. Activate for questions
  about web security, pentest methodology, or specific vulnerability exploitation.
---

## PayloadsAllTheThings — Security Reference Skill

> ⚠️ **Disclaimer**: This knowledge is for authorized security testing, CTF competitions,
> and educational purposes only. Use responsibly and only on systems you have permission to test.

**Source**: [swisskyrepo/PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings)

---

### How to Use This Skill

When the user asks about a specific vulnerability or attack technique, consult the relevant
reference file below and provide accurate payloads, bypass techniques, and methodology.

Always remind the user to use payloads only in authorized environments.

---

### Coverage Map

#### Injection Attacks
| Topic | Reference File |
|-------|---------------|
| SQL Injection | [sql-injection.md](./references/sql-injection.md) |
| NoSQL Injection | [nosql-injection.md](./references/nosql-injection.md) |
| Command Injection | [command-injection.md](./references/command-injection.md) |
| LDAP Injection | [ldap-injection.md](./references/ldap-injection.md) |
| GraphQL Injection | [graphql-injection.md](./references/graphql-injection.md) |
| SAML Injection | [saml-injection.md](./references/saml-injection.md) |
| LaTeX Injection | [latex-injection.md](./references/latex-injection.md) |
| CSV Injection | [csv-injection.md](./references/csv-injection.md) |
| CRLF Injection | [crlf-injection.md](./references/crlf-injection.md) |
| CSS Injection | [css-injection.md](./references/css-injection.md) |

#### Web Application Attacks
| Topic | Reference File |
|-------|---------------|
| XSS (Cross-Site Scripting) | [xss.md](./references/xss.md) |
| SSRF (Server-Side Request Forgery) | [ssrf.md](./references/ssrf.md) |
| SSTI (Server-Side Template Injection) | [ssti.md](./references/ssti.md) |
| XXE (XML External Entity) | [xxe.md](./references/xxe.md) |
| File Inclusion (LFI/RFI) | [file-inclusion.md](./references/file-inclusion.md) |
| Directory Traversal | [directory-traversal.md](./references/directory-traversal.md) |
| Open Redirect | [open-redirect.md](./references/open-redirect.md) |
| CSRF | [csrf.md](./references/csrf.md) |
| Clickjacking | [clickjacking.md](./references/clickjacking.md) |
| Request Smuggling | [request-smuggling.md](./references/request-smuggling.md) |
| HTTP Parameter Pollution | [http-parameter-pollution.md](./references/http-parameter-pollution.md) |

#### Authentication & Authorization
| Topic | Reference File |
|-------|---------------|
| JWT Attacks | [jwt.md](./references/jwt.md) |
| OAuth Misconfiguration | [oauth.md](./references/oauth.md) |
| CORS Misconfiguration | [cors.md](./references/cors.md) |
| Account Takeover | [account-takeover.md](./references/account-takeover.md) |
| IDOR | [idor.md](./references/idor.md) |
| Mass Assignment | [mass-assignment.md](./references/mass-assignment.md) |

#### Infrastructure & Advanced
| Topic | Reference File |
|-------|---------------|
| Insecure Deserialization | [deserialization.md](./references/deserialization.md) |
| Prototype Pollution | [prototype-pollution.md](./references/prototype-pollution.md) |
| Race Condition | [race-condition.md](./references/race-condition.md) |
| DNS Rebinding | [dns-rebinding.md](./references/dns-rebinding.md) |
| Reverse Proxy Misconfigurations | [reverse-proxy.md](./references/reverse-proxy.md) |
| Dependency Confusion | [dependency-confusion.md](./references/dependency-confusion.md) |
| API Key Leaks | [api-key-leaks.md](./references/api-key-leaks.md) |
| Prompt Injection | [prompt-injection.md](./references/prompt-injection.md) |
| CVE Exploits | [cve-exploits.md](./references/cve-exploits.md) |

#### Methodology & Resources
| Topic | Reference File |
|-------|---------------|
| Pentest Methodology | [methodology.md](./references/methodology.md) |

---

### Quick Reference: Common Payloads

#### Blind Detection (Universal)
```
'
"
`
;
--
##
/*
{{7*7}}
${7*7}
<svg onload=alert(1)>
../../../../etc/passwd
http://169.254.169.254/latest/meta-data/
```

#### Encoding Cheat Sheet
| Encoding | `<` | `>` | `"` | `'` | `/` |
|----------|-----|-----|-----|-----|-----|
| URL | `%3C` | `%3E` | `%22` | `%27` | `%2F` |
| Double URL | `%253C` | `%253E` | `%2522` | `%2527` | `%252F` |
| HTML | `&lt;` | `&gt;` | `&quot;` | `&#x27;` | `&#x2F;` |
| Unicode | `\u003C` | `\u003E` | `\u0022` | `\u0027` | `\u002F` |

#### WAF Bypass Techniques
- **Case variation**: `SeLeCt`, `UnIoN`
- **Comments**: `SE/**/LECT`, `UN/**/ION`
- **URL encoding**: `%53ELECT`
- **Double encoding**: `%2553ELECT`
- **Whitespace alternatives**: `%09`, `%0A`, `%0D`, `%0C`
- **Null bytes**: `%00`, `\x00`
