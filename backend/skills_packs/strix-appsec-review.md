---
name: strix-appsec-review
description: Whole-product AppSec review like strix application-security-testing — map assets, pick the right test per asset, consolidate into one ranked plan
trigger_when:
  - "appsec"
  - "security review"
  - "مراجعة أمنية"
  - "تقييم أمني"
  - "امن التطبيق"
always: false
---

# Strix AppSec Review (usestrix/strix methodology)

Entry point when the request is "secure my product" and the target is
not one URL. Pick the right test per asset — do not run everything at
max depth.

**1. Map the assets (write it down before testing):**
- Source: repo / monorepo / services, languages, frameworks.
- Running: staging deployment, production, local dev server.
- APIs: REST / GraphQL / gRPC, schema availability.
- Auth: two test accounts in different tenants?
- Constraints: out-of-scope paths, production touch rules, budget.

**2. Pick the test per asset:**
| Asset | Method |
|---|---|
| Repo / working tree | white-box code review |
| Live web app | black-box web pentest |
| REST/GraphQL/gRPC | API security sweep |
| OWASP-mapped assessment | OWASP ten sweep |

**3. Sequence:** code review first (cheapest, maps the authorization
model) → live test with credentials + source as second target →
continuous/diff scanning for regressions. One asset at a time, read
each report before the next.

**4. Consolidate — rank by PROVEN impact, not scanner labels:**
1. Validated exploits reachable unauthenticated.
2. Validated cross-tenant / privilege-escalation.
3. Validated issues needing an account.
4. Unproven observations — flagged as unproven, NEVER presented as
   confirmed vulnerabilities.

Deduplicate same-root-cause findings across runs. State plainly what
was NOT tested.
