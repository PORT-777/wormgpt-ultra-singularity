# Render deployment — PORT 777 AI

## Blueprint

`render.yaml` defines a Python web service:

- Build: install `backend/requirements-prod.txt`, then `npm ci && npm run build`.
- Start: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
- Health check: `/health` returns 200 only when PostgreSQL answers `SELECT 1`.

## Required environment variables (set in Render dashboard)

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Supabase pooler DSN (session/pooled, TLS required) |
| `SUPABASE_URL` | Project URL for Storage REST calls |
| `SUPABASE_PUBLISHABLE_KEY` | Public key (safe) |
| `SUPABASE_SECRET_KEY` | Service key — backend only |
| `STORAGE_BACKEND` | `supabase` |
| `PGSSLMODE` | `require` |
| `ADMIN_PASSWORD`, `AUTH_SECRET`, `ENCRYPTION_MASTER_KEY` | existing platform security |
| `SMTP_*` | email verification / password reset |
| `PAYMOB_*` | payment integration (test mode first) |
| provider keys | existing AI model providers |

Never put these values in source control. The blueprint uses `sync: false` for
all secrets so they must be entered in the dashboard.

## Persistence

Render's local filesystem is ephemeral. All persistent records live in
Supabase PostgreSQL and all uploaded/generated files live in Supabase Storage.
The app's local `backend/data/` directory is used only as a development
fallback and for audit jsonl mirrors.

## CORS

`backend/main.py` restricts CORS to localhost origins by default. Add the
Render public URL to `allow_origins` before going live.

## Upgrade path (free → paid)

- Render free services sleep; move to a paid web service for always-on.
- Supabase free tier has storage/egress caps; monitor `/api/saas/usage` and
  `saas_files` totals, then upgrade the project when limits are approached.
- Replace Supabase Storage by setting `STORAGE_BACKEND=s3` with `S3_*` values;
  no application code changes are needed.

## Do not

- Commit `.env`, database backups, `.db` files, or uploaded files.
- Push to GitHub or deploy to Render without explicit approval.
