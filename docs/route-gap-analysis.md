# Frontend / backend route gap analysis

Observed 2026-11-27.

## Method
- Frontend: all `/api/internal/...` literals in `frontend/src/api/**/*.ts` were extracted (31 unique paths, template parameters normalized).
- Backend: `app.routes` filtered to `/api/internal` from `backend/main.py` (47 route entries across GET/POST/DELETE).
- Responses were also exercised live against `127.0.0.1:7777` with `x-internal-key`.

## Result
**No gaps.** Every route the frontend calls exists in the backend. Examples:
- chat/sessions: `/sessions`, `/sessions/{id}` — present
- workspace chat: `/workspaces/{id}/chat` — present
- RAG: `/rag/ingest`, `/rag/query`, `/rag/documents`, `/rag/stats`, `/rag/search` — present
- agents: `/agents/run`, `/agents/{name}/run`, `/agents/tools`, `/agents/jobs/{id}` — present
- models: `/models/catalog`, `/models/usage`, `/models/cost`, `/models/route`, `/models/call/auto`, `/models/cache/query` — present
- eval: `/eval/metrics`, `/eval/traces`, `/eval/score`, `/eval/health/all`, `/eval/cost/projection` — present
- streaming/jobs/workflows: `/stream/sse/{id}`, `/jobs/submit`, `/jobs/{id}/result`, `/workflows/run` — present

Backend exposes additional routes the frontend does not yet call (`/rag/evaluate`,
`/docs/extract/tables`, `/docs/ocr`, `/code/write`, `/code/run`, `/code/files`,
`/models/cache/warm`, `/agents/tools/{name}`, `/agents/memory/{user}` etc.). These
are available for future UI work; no stub routes were needed.

## Known contract normalizations
- `/models/catalog` returns a dict keyed by model id; `frontend/src/api/internal/models.ts`
  normalizes it to `ModelInfo[]` before components consume it.
- Health items use `service` as the name field; `ServiceHealthGrid` reads `name ?? service`.
- All internal routes return 503 when `INTERNAL_API_KEY` is unset, 401 on a wrong key.
