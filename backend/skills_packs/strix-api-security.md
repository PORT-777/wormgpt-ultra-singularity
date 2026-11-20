---
name: strix-api-security
description: API security testing like strix api-security-testing — OWASP API Top 10 (BOLA/IDOR, property & function authz, unrestricted consumption) with PoC requests
trigger_when:
  - "api security"
  - "api test"
  - "bola"
  - "idor"
  - "api pentest"
  - "graphql"
  - "rest api"
always: false
---

# Strix API Security (usestrix/strix methodology)

APIs fail differently from web UIs: no rendered surface to crawl, the
interesting bugs are authorization-shaped, and the same endpoint
behaves differently per token. Coverage checklist = OWASP API Security
Top 10 (2023).

**1. Gather the inputs that make testing possible:**
- Schema (OpenAPI/Swagger, Postman collection, GraphQL introspection,
  gRPC proto) → turns guesswork into full endpoint enumeration.
- TWO tenant tokens — BOLA (API1) can only be proven by reading
  tenant A's objects with tenant B's token.
- Low + high privilege tokens — proves broken function-level authz
  (API5: a `user` calling admin routes).
- Example object IDs → immediate ID tampering tests.
- Out-of-scope routes + rate limits in front.

**2. Sweep the API Top 10:** API1 BOLA · API2 broken authentication ·
API3 object property-level authz (mass assignment + over-exposed
fields in responses) · API4 unrestricted resource consumption · API5
function-level authz · API6 business flows · API7 SSRF · API8
misconfiguration · API9 improper inventory · API10 unsafe consumption.

**3. GraphQL specifics:** batching/aliasing abuse, depth/complexity
limits, per-field authorization, introspection exposure.

**4. Verify:** replay each PoC request; authorization findings must
show the other tenant's data (not an empty 200). Record with the exact
request in the ledger; fix the authorization CHECK (shared helper),
not the single endpoint; re-test to prove it is dead.
