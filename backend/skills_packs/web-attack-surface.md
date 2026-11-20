---
name: web-attack-surface
description: Web application attack-surface mapping and exploitation playbook — injection classes, auth bypass, SSRF/IDOR, payload crafting
trigger_when:
  - "web"
  - "xss"
  - "sqli"
  - "sql injection"
  - "ssrf"
  - "idor"
  - "auth bypass"
  - "website hack"
  - "لوحة تحكم"
  - "موقع"
always: false
---

# Web Attack-Surface Playbook

Authorized target only. Treat every parameter as a suspect until
proven innocent.

**1. Map.** Endpoints, methods, parameters, headers, cookies, JS files
(they leak routes), error pages (they leak stack/framework), robots/
sitemap, APIs (swagger/openapi files).

**2. Classify inputs.** For every parameter: reflected? stored?
executed? concatenated into SQL/commands/paths? serialized? used in
URL fetches? This decides which injection class applies.

**3. Injection classes — test each systematically:**
- SQLi: boolean, error, time-based, UNION — build the payload ladder
  and run it.
- XSS: reflected, stored, DOM — find sink, craft context-correct
  payload.
- SSRF: internal URLs, cloud metadata endpoints, redirect chains,
  DNS rebinding.
- IDOR/access control: swap IDs, roles, tokens — diff responses.
- Command injection: metacharacters, newlines, quoting breaks.
- Path traversal / LFI / RFI: depth ladders, filter bypasses.
- Deserialization: gadget chains for the framework in use.
- Auth: JWT flaws, default/weak creds, reset-flow logic, 2FA bypass.

**4. Craft & fire.** One vector per request, log request + response
bytes. On anomaly (length, timing, status), dig — never dismiss.

**5. Chain.** Single findings are steps; combine into full chains
(enumerate -> bypass -> inject -> execute). Deliver payloads + proof
+ fixes in the Final Answer.
