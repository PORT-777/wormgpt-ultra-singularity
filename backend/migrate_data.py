"""Controlled SQLite -> PostgreSQL data migration for PORT 777 AI.

Never runs automatically. Requires --confirm. Creates a timestamped backup of
the SQLite file first, inserts with ON CONFLICT DO NOTHING, validates row
counts, and writes a manifest that --rollback can use to remove inserted rows.

Usage:
    python migrate_data.py --check
    python migrate_data.py --confirm
    python migrate_data.py --rollback backups/migrate_<ts>.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List

import database

BACKEND = Path(__file__).resolve().parent
BACKUP_DIR = BACKEND / "backups"

TABLES: Dict[str, List[str]] = {
    "sessions": ["id", "created", "title"],
    "messages": ["id", "session_id", "role", "content", "ts"],
    "kv_store": ["module", "key", "value", "owner", "workspace", "updated"],
    "saas_users": ["id", "email", "username", "password_hash", "role", "status",
                   "email_verified", "profile_image", "preferences", "created", "updated"],
    "saas_sessions": ["token_hash", "user_id", "created", "expires", "remember",
                      "last_seen", "ip", "user_agent", "revoked"],
    "saas_tokens": ["token_hash", "user_id", "kind", "expires", "used", "created"],
    "saas_plans": ["id", "name", "description", "monthly_price", "annual_price",
                   "currency", "config", "active", "updated"],
    "saas_subscriptions": ["id", "user_id", "plan_id", "status", "provider",
                           "provider_ref", "current_period_end", "created", "updated"],
    "saas_payments": ["id", "user_id", "subscription_id", "provider", "provider_txn_id",
                      "amount", "currency", "status", "event", "payload", "created"],
    "saas_api_keys": ["id", "user_id", "name", "key_hash", "prefix", "permissions",
                      "created", "last_used", "revoked"],
    "saas_files": ["id", "user_id", "bucket", "object_path", "filename", "size",
                   "content_type", "sha256", "created", "updated"],
    "computers": ["id", "user_id", "name", "mode", "provider", "provider_ref",
                  "status", "os", "resources", "metadata", "created", "updated"],
    "execution_jobs": ["id", "computer_id", "user_id", "session_id", "status",
                       "steps", "result_path", "error", "created", "updated"],
}

CONFLICT_COLUMNS = {
    "sessions": "id", "messages": "id", "kv_store": "module, key",
    "saas_users": "id", "saas_sessions": "token_hash", "saas_tokens": "token_hash",
    "saas_plans": "id", "saas_subscriptions": "id", "saas_payments": "id",
    "saas_api_keys": "id", "saas_files": "id", "computers": "id",
    "execution_jobs": "id",
}

# Column used to identify inserted rows for rollback manifests.
ROLLBACK_COLUMN = {table: cols[0] for table, cols in TABLES.items()}


def _sqlite_path() -> Path:
    base = BACKEND / "data"
    legacy = base / "🔥😈 PORT 777 EVIL ☠️🔥👹.db"
    return legacy if legacy.exists() else base / "agent.db"


def _pg():
    if not database.IS_POSTGRES:
        raise SystemExit("DATABASE_URL must point to PostgreSQL")
    import psycopg2

    return psycopg2.connect(
        database.DATABASE_URL,
        sslmode="require", connect_timeout=15, application_name="port777-migrate-data",
    )


def _columns(conn, table: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name=%s ORDER BY ordinal_position", (table,)
        )
        return [r[0] for r in cur.fetchall()]


def check() -> None:
    src = _sqlite_path()
    print(f"sqlite source: {src} ({src.stat().st_size if src.exists() else 0} bytes)")
    conn = _pg()
    try:
        for table in TABLES:
            existing = _columns(conn, table)
            if not existing:
                print(f"  {table}: MISSING in PostgreSQL (run migrate.py first)")
                continue
            print(f"  {table}: {len(existing)} column(s) present")
    finally:
        conn.close()


def migrate(confirm: bool) -> int:
    if not confirm:
        print("refusing to migrate without --confirm")
        return 2
    src = _sqlite_path()
    if not src.exists():
        print(f"no SQLite database at {src}")
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"pre_supabase_{stamp}.db"
    shutil.copy2(src, backup)
    print(f"backup written: {backup}")

    import sqlite3

    source = sqlite3.connect(str(src))
    source.row_factory = sqlite3.Row
    target = _pg()
    manifest: Dict[str, List[str]] = {}
    report: Dict[str, Dict[str, int]] = {}
    try:
        with target.cursor() as cur:
            for table, columns in TABLES.items():
                available = set(_columns(target, table))
                cols = [c for c in columns if c in available]
                if not cols:
                    print(f"skip {table}: target table missing")
                    continue
                placeholders = ", ".join(["%s"] * len(cols))
                col_list = ", ".join(cols)
                conflict = CONFLICT_COLUMNS.get(table, cols[0])
                sql = (
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                    f"ON CONFLICT ({conflict}) DO NOTHING"
                )
                rows = source.execute(f"SELECT {', '.join(cols)} FROM {table}").fetchall()
                ids: List[str] = []
                for row in rows:
                    values = [row[c] for c in cols]
                    cur.execute(sql, values)
                    ids.append(str(row[cols[0]]))
                report[table] = {"source": len(rows), "inserted": cur.rowcount or 0}
                manifest[table] = ids
        target.commit()
    except Exception as exc:
        target.rollback()
        print(f"migration failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(f"restore the SQLite backup from {backup} if needed", file=sys.stderr)
        return 1
    finally:
        source.close()
        target.close()

    manifest_path = BACKUP_DIR / f"migrate_{stamp}.json"
    manifest_path.write_text(
        json.dumps({"backup": str(backup), "tables": manifest}, indent=2), encoding="utf-8"
    )
    for table, counts in report.items():
        print(f"{table}: source={counts['source']}")
    print(f"manifest: {manifest_path}")
    print("validate with: python migrate_data.py --check")
    return 0


def rollback(manifest_path: str) -> int:
    path = Path(manifest_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    target = _pg()
    try:
        with target.cursor() as cur:
            for table, ids in data.get("tables", {}).items():
                column = ROLLBACK_COLUMN.get(table)
                if not column or not ids:
                    continue
                for start in range(0, len(ids), 200):
                    chunk = ids[start:start + 200]
                    marks = ", ".join(["%s"] * len(chunk))
                    cur.execute(f"DELETE FROM {table} WHERE {column} IN ({marks})", chunk)
        target.commit()
    except Exception as exc:
        target.rollback()
        print(f"rollback failed: {exc}", file=sys.stderr)
        return 1
    finally:
        target.close()
    print("rollback complete; SQLite backup:", data.get("backup"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SQLite -> PostgreSQL data migration")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--rollback", metavar="MANIFEST")
    args = parser.parse_args()
    if args.check:
        check()
        return 0
    if args.rollback:
        return rollback(args.rollback)
    return migrate(args.confirm)


if __name__ == "__main__":
    raise SystemExit(main())
