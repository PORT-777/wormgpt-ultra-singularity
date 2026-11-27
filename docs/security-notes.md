# Security Notes

## Last audit: 2026-11-27

### Frontend
- Tool: `npm audit`
- Before: 2 vulnerabilities (1 high, 1 moderate) — `vite` <=6.4.3 and its `esbuild` <=0.24.2.
- Action: upgraded to `vite@6.4.6` (patched 6.x line) with `@vitejs/plugin-react@4.7.0`.
  Vite 8 also fixed the advisories but its stricter parser broke a pre-existing
  JSX file, so the patched 6.x release was used instead.
- Result: **0 vulnerabilities**. `npm audit` exit 0.

### Backend
- Tool: `pip-audit` (installed into `backend/.venv`)
- Before: 10 known vulnerabilities in 3 packages:
  - `oauthlib 4.0.0` — CVE-2026-49272 → upgraded to 4.0.1
  - `pyasn1 0.6.4` — CVE-2026-119194/195/196/197 → upgraded to 0.6.5
  - `chromadb 1.5.9` — PYSEC-2026-311, -3813, -3814, -3815 (5 findings)
- After: 5 findings remain, all in `chromadb 1.5.9`. It is already the latest
  published version (`pip index versions chromadb` reports 1.5.9 as LATEST),
  so no fixed release exists. This is an optional dependency used by the
  vector-store backend abstraction; the default in-process store does not use it.
- Result: no fixable vulnerabilities remain; unfixable ones documented here.

### Process
- Run `npm audit` and `pip-audit --format=columns` before every release.
- Pin patched versions in lockfiles; avoid `--force` major upgrades without a build gate.
- Dependabot / Renovate recommended for automated dependency PRs.
- Re-check `chromadb` advisories when a new upstream release is published.
