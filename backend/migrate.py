"""Safe, versioned PostgreSQL migration runner for PORT 777 AI.

Usage:
    python migrate.py            apply all pending migrations
    python migrate.py --check    list pending migrations (no changes)
    python migrate.py --status   show applied migrations

Only additive/idempotent DDL is applied. Destructive changes are never run
automatically; write a new migration and review it before applying.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import database

MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def _connect():
    if not database.IS_POSTGRES:
        raise SystemExit(
            "DATABASE_URL is not a PostgreSQL URL. Migrations target Supabase/Render PostgreSQL."
        )
    try:
        import psycopg2
    except ImportError as exc:
        raise SystemExit("psycopg2-binary is required: pip install psycopg2-binary") from exc
    return psycopg2.connect(
        database.DATABASE_URL,
        sslmode=os.getenv("PGSSLMODE", "require"),
        connect_timeout=int(os.getenv("PGCONNECT_TIMEOUT", "15")),
        application_name="port777-migrate",
    )


def _files():
    return sorted(p for p in MIGRATIONS.glob("*.sql") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="PORT 777 AI PostgreSQL migrations")
    parser.add_argument("--check", action="store_true", help="only list pending migrations")
    parser.add_argument("--status", action="store_true", help="show applied migrations")
    args = parser.parse_args()

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("SELECT version FROM schema_migrations ORDER BY version")
            applied = {r[0] for r in cur.fetchall()}

        files = _files()
        if args.status:
            for path in files:
                print(f"{'[applied]' if path.name in applied else '[pending]'} {path.name}")
            return 0

        pending = [p for p in files if p.name not in applied]
        if args.check:
            for path in pending:
                print(f"[pending] {path.name}")
            print(f"{len(pending)} pending migration(s)")
            return 0

        if not pending:
            print("database is up to date")
            return 0

        for path in pending:
            print(f"applying {path.name} ...")
            sql = path.read_text(encoding="utf-8")
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations(version) VALUES(%s)", (path.name,)
                    )
                conn.commit()
            except Exception as exc:
                conn.rollback()
                print(f"FAILED {path.name}: {type(exc).__name__}: {exc}", file=sys.stderr)
                return 1
            print(f"applied {path.name}")
        print("migrations complete")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
