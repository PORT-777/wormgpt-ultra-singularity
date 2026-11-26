# API Integration Plan (internal services only)

## Phase 0 — project mapping (observed)

- Stack: **Python 3.13 / FastAPI** backend in `backend/`; React+Vite frontend in `frontend/` (Tauri shell in `src-tauri/`). `frontend/package.json` is React-only — no service-layer JS in the app.
- No `src/services/**` TypeScript tree exists. The mission's TS paths are from a different template; they are mapped to Python below. Frontend is **not touched**.
- Route mounting: `backend/main.py::mount_router` mounts `backend/api/*` routers under `/api/*`. New routes mount the same way.
- Env: `backend/.env` (live), `backend/.env.example` (template). DB: `backend/database.py` (SQLite local / Postgres via `DATABASE_URL`).
- `backend/integrations/` is **OAuth account linking**, not a general external-API client layer — new code goes in a separate `backend/external_apis/` package to avoid breaking it.
- Research: `public-apis/public-apis` README studied (2,000+ curated APIs, categories); `freepublicapis.com/tags/ai` studied (AI-tagged entries incl. OpenRouter Models, LimitReset, SnapRender, FinSignals, Pollinations, etc.).

## Path mapping (TS spec -> Python reality)

| Spec path | Python implementation |
|---|---|
| `src/services/api-registry/*` | `backend/external_apis/{registry,cache,rate_limiter,health}.py` |
| `src/lib/external-api-client.ts` | `backend/external_apis/client.py` |
| `src/services/integrations/[api].ts` | `backend/external_apis/services/ai.py` and `data.py` (declarative specs) |
| `src/services/{rag,agents,documents,models,eval,streaming}/*` | `backend/external_apis/{rag,agents,documents,models,eval,streaming}/*.py` |
| `src/services/ai-platform/*` | `backend/external_apis/platform/*.py` |
| `src/config/api-config.ts` | `backend/external_apis/config.py` |
| `POST /api/internal/...` | `backend/external_apis/api.py` mounted at `/api/internal` |

## Design rules

1. Additive only — no existing route, tool or frontend file is modified.
2. Every integration is optional: missing key -> service reports `available: false`, platform keeps working.
3. All external calls go through one client with timeout + bounded retry; failures never crash the platform.
4. Internal routes require `x-internal-key` header (env `INTERNAL_API_KEY`); if unset, routes are disabled (fail closed).
5. Shared TTL cache and per-service token-bucket rate limiter.
6. Services expose `query()`, `healthCheck()`, `getCached()` semantics via a base class.

## Coverage

- Phase 2A-2E: all listed AI/ML, vision, audio, router and specialized APIs declared as service specs.
- Phase 3: all listed general/public APIs declared as service specs.
- Phase 4A-4F: internal modules for RAG, agents, documents, model management, evaluation and streaming.
- Phase 5: central router/enricher/composer/cache-warmer/health dashboard.
- Phase 6: env template additions, typed config, auth + rate limit on every route.
- Phase 7: mocked unit tests + health-shape tests; full suite must stay green.

## Verification

`cd backend && python -m pytest -q` before and after. No frontend files touched. No real keys committed.
