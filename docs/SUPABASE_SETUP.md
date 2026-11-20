# Supabase setup — PORT 777 AI

## 1. Project credentials

From the setup spreadsheet (`supabase_port777ai_setup.xlsx`):

| Item | Value / status |
| --- | --- |
| Project | `port777-ai` (EU West / Ireland) |
| Project ref | `rjcynrwajbcmmmfkgpbr` |
| Project URL | `https://rjcynrwajbcmmmfkgpbr.supabase.co` |
| Publishable key | present in spreadsheet (safe client-side) |
| Secret / service key | **placeholder only** — must be copied from Dashboard → Settings → API |
| PostgreSQL DSN | password is in the spreadsheet; host corrected to the Supabase **pooler** |

### Verified status of the supplied credentials

- Project URL, publishable key, REST and Storage endpoints: **reachable and valid**
  (`GET /storage/v1/bucket` returned `200 []`).
- Secret / service key in the spreadsheet: **placeholder**, not a real key.
- PostgreSQL DSN in the spreadsheet: **invalid**. `db.<ref>.supabase.co` does
  not resolve, the direct host's port `5432` times out, and the pooler returns
  `tenant/user postgres.rjcynrwajbcmmmfkgpbr not found` for every region
  (`eu-west-1`, `eu-west-2`, `us-east-1`, `us-west-1` on ports `5432`/`6543`).

Get a fresh connection string from **Dashboard → Settings → Database →
Connection string (URI / Transaction pooler)** and use that. The expected
format is:

```
postgresql://postgres.<ref>:<password>@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
```

Fill these in `backend/.env` (never commit it):

```
SUPABASE_URL=https://rjcynrwajbcmmmfkgpbr.supabase.co
SUPABASE_PUBLISHABLE_KEY=<publishable key>
SUPABASE_SECRET_KEY=<service key from Dashboard>
DATABASE_URL=postgresql://postgres.rjcynrwajbcmmmfkgpbr:<password>@aws-0-eu-west-1.pooler.supabase.com:6543/postgres
STORAGE_BACKEND=supabase
```

## 2. Database schema

```powershell
cd backend
python -m pip install -r requirements-prod.txt
python migrate.py --check
python migrate.py
python migrate.py --status
```

`migrations/001_initial.sql` is additive and idempotent — it never drops or
rewrites existing tables. `migrations/002_rls.sql` installs ownership policies.

## 3. Storage buckets

Buckets are created automatically on startup by
`storage_backends.ensure_buckets()` when `SUPABASE_SECRET_KEY` is set, or
manually in Dashboard → Storage:

| Bucket | Visibility | Limit | Purpose |
| --- | --- | --- | --- |
| `avatars` | public read | 5 MB | Profile images |
| `user-files` | private | 50 MB | Personal uploads |
| `chat-attachments` | private | 20 MB | Chat files |
| `ai-generated-files` | private | 50 MB | AI output |
| `agent-artifacts` | private | 100 MB | Agent output |
| `exports` | private | 100 MB | Exports |

Objects are stored at `{user_id}/<timestamp>-<random>-<filename>`.

## 4. Identity and RLS

The application keeps its existing account system (PBKDF2 passwords + hashed
session tokens in `saas_users`). It does **not** switch to Supabase Auth.

- The backend uses the **service key**; RLS is intentionally bypassed for
  backend calls, and every API endpoint enforces ownership in code
  (`saas/files.py`, `saas/api.py`).
- `migrations/002_rls.sql` maps the JWT `sub` claim to the existing
  `user_id` columns so the same tables can be exposed through Supabase Auth
  later without a second login system.
- Private buckets are never made public. Download URLs are short-lived signed
  URLs; local development uses HMAC-signed URLs verified by the backend.

## 5. Verification

```powershell
python -c "import database; print(database.health(), database.backend_name())"
python -c "import storage_backends; print(storage_backends.storage_status())"
```

Then start the API and check `/health` (503 if the database is unreachable)
and `/api/saas/storage/status`.

## 6. Migrating existing local data

See `docs/MIGRATIONS.md`. Never overwrite production records without a backup.
