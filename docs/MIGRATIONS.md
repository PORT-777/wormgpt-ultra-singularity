# Database migrations and data migration

## Schema migrations

Schema lives in `backend/migrations/*.sql` and is applied in lexicographic
order. `schema_migrations` records which files have been applied.

```powershell
cd backend
python migrate.py --status    # what is applied / pending
python migrate.py --check     # fail-fast preview for CI
python migrate.py             # apply additive migrations
```

Rules:

- `001_initial.sql` uses only `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`.
- No destructive operation is ever run automatically.
- To make a breaking change, add a new numbered migration and review it before
  applying. Keep a Supabase point-in-time recovery point.

## SQLite → Supabase data migration

Local development stores data in `backend/data/agent.db`. To move it:

```powershell
cd backend
python migrate_data.py --check          # inspect tables and columns
python migrate_data.py --confirm        # backup + insert with ON CONFLICT DO NOTHING
python migrate_data.py --check          # validate
```

The script:

1. Copies the SQLite file to `backend/backups/pre_supabase_<timestamp>.db`.
2. Inserts rows with `ON CONFLICT DO NOTHING` (never overwrites existing rows).
3. Writes `backend/backups/migrate_<timestamp>.json` listing inserted ids.

Rollback (removes only the rows inserted by that run):

```powershell
python migrate_data.py --rollback backups/migrate_<timestamp>.json
```

If the PostgreSQL side needs a full restore, use Supabase point-in-time
recovery and then restore the SQLite backup file.

## Production deployment order

1. Create the Supabase project and collect credentials.
2. Set `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY` in Render.
3. Run `python migrate.py` once (locally or as a one-off Render job).
4. Deploy the web service. Startup only applies additive schema and creates
   missing buckets; it never deletes data.
