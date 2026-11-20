"""Unified database access layer.

Local development uses the existing SQLite file. Production (Render) uses
Supabase PostgreSQL through ``DATABASE_URL`` with a bounded connection pool.

The public surface mirrors the small subset of the sqlite3 API the project
uses, so existing modules keep working unchanged:

    conn() -> connection-like object
    connection.execute(sql, params) -> cursor
    connection.executescript(sql)
    transaction(connection=None) -> atomic context manager
    health(), ensure_schema(), release(), page_params()

PostgreSQL compatibility shims:
  - ``?`` placeholders become ``%s`` (outside quoted literals).
  - ``INSERT OR REPLACE INTO t(...)`` becomes ``INSERT ... ON CONFLICT ...``.
  - ``INTEGER PRIMARY KEY AUTOINCREMENT`` becomes ``BIGSERIAL PRIMARY KEY``.
  - ``PRAGMA table_info(t)`` becomes an information_schema query.
  - ``VACUUM`` is skipped (it cannot run inside a transaction).
  - INSERTs into tables with an ``id`` column get ``RETURNING id`` so
    ``cursor.lastrowid`` keeps working.
"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:  # keep imports side-effect free when dotenv is absent
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except Exception:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))


class Row:
    """sqlite3.Row-like object that also supports key access and dict()."""

    __slots__ = ("_columns", "_values", "_map")

    def __init__(self, columns: Sequence[str], values: Sequence[Any]):
        self._columns = tuple(columns)
        self._values = tuple(values)
        self._map = dict(zip(self._columns, self._values))

    def keys(self) -> List[str]:
        return list(self._columns)

    def values(self) -> List[Any]:
        return list(self._values)

    def items(self) -> List[Tuple[str, Any]]:
        return list(self._map.items())

    def get(self, key: str, default: Any = None) -> Any:
        return self._map.get(key, default)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        if isinstance(key, slice):
            return self._values[key]
        return self._map[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __contains__(self, key) -> bool:
        return key in self._map

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"Row({self._map!r})"


# Tables with a single-column primary key named "id" (for RETURNING id).
_ID_TABLES = {
    "sessions", "messages", "scheduled_tasks", "audit_log", "proposals",
    "message_feedback", "trace_events", "gamification", "saas_usage",
    "saas_plans", "saas_users", "saas_subscriptions", "saas_payments",
    "saas_api_keys", "saas_files", "computers", "computer_sessions",
    "terminal_sessions", "browser_sessions", "processes", "artifacts",
    "execution_jobs", "execution_logs", "resource_metrics",
}

# Conflict targets for INSERT OR REPLACE translation.
_PK_COLUMNS = {
    "kv_store": ("module", "key"),
    "credit_balances": ("user_id",),
    "computers": ("id",),
    "execution_jobs": ("id",),
    "saas_plans": ("id",),
}

_UPSERT_RE = re.compile(
    r"^\s*INSERT\s+OR\s+REPLACE\s+INTO\s+([A-Za-z_][\w]*)\s*\(([^)]*)\)",
    re.IGNORECASE | re.DOTALL,
)


def _pg_placeholders(sql: str) -> str:
    out: List[str] = []
    quote: Optional[str] = None
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if quote:
            out.append(ch)
            if ch == quote:
                if i + 1 < n and sql[i + 1] == quote:
                    out.append(sql[i + 1])
                    i += 2
                    continue
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            i += 1
            continue
        out.append("%s" if ch == "?" else ch)
        i += 1
    return "".join(out)


def _pg_upsert(sql: str) -> str:
    match = _UPSERT_RE.match(sql)
    if not match:
        return sql
    table = match.group(1)
    columns = match.group(2)
    pk = _PK_COLUMNS.get(table, ("id",))
    names = [c.strip() for c in columns.split(",") if c.strip()]
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in names if c not in pk)
    tail = " ON CONFLICT (" + ", ".join(pk) + ") DO "
    tail += "UPDATE SET " + updates if updates else "NOTHING"
    return f"INSERT INTO {table} ({columns})" + sql[match.end():] + tail


def _translate(sql: str) -> str:
    if not IS_POSTGRES:
        return sql
    text = _pg_placeholders(str(sql))
    text = _pg_upsert(text)
    text = re.sub(
        r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
        "BIGSERIAL PRIMARY KEY",
        text,
        flags=re.IGNORECASE,
    )
    return text


class Cursor:
    def __init__(self, owner: "PGConnection", raw: Any):
        self._owner = owner
        self._raw = raw
        self._lastrowid: Any = None

    @property
    def rowcount(self) -> int:
        return int(self._raw.rowcount or 0)

    @property
    def description(self) -> Any:
        return self._raw.description

    @property
    def lastrowid(self) -> Any:
        return self._lastrowid

    def _decode(self, rows: Iterable[Any]) -> List[Row]:
        desc = self._raw.description
        if not desc:
            return list(rows)
        columns = [d[0] for d in desc]
        return [Row(columns, row) for row in rows]

    def execute(self, sql: str, params: Any = None) -> "Cursor":
        self._lastrowid = None
        statement = str(sql or "").strip()
        if not IS_POSTGRES:
            self._raw.execute(statement, params if params is not None else ())
            return self

        if re.match(r"PRAGMA\b", statement, re.IGNORECASE):
            info = re.search(
                r"table_info\s*\(?\s*\[?([A-Za-z_]\w*)\]?\s*\)?",
                statement,
                re.IGNORECASE,
            )
            if info:
                self._raw.execute(
                    "SELECT (ordinal_position - 1)::int AS cid, "
                    "column_name AS name, data_type AS type "
                    "FROM information_schema.columns "
                    "WHERE table_name = %s ORDER BY ordinal_position",
                    (info.group(1).lower(),),
                )
            else:
                self._raw.execute(
                    "SELECT 1 AS cid, '' AS name, '' AS type WHERE FALSE"
                )
            return self

        if re.match(r"VACUUM\b", statement, re.IGNORECASE):
            return self

        statement = _translate(statement)
        inserted = re.match(r"INSERT\s+INTO\s+([A-Za-z_]\w*)", statement, re.IGNORECASE)
        table = inserted.group(1).lower() if inserted else ""
        if table in _ID_TABLES and "RETURNING" not in statement.upper():
            statement = statement.rstrip().rstrip(";") + " RETURNING id"
        try:
            self._raw.execute(statement, params)
        except Exception:
            if not self._owner.reconnect():
                raise
            self._raw = self._owner.raw.cursor()
            self._raw.execute(statement, params)
        if table in _ID_TABLES and self._raw.description:
            row = self._raw.fetchone()
            if row:
                self._lastrowid = row[0]
        return self

    def executemany(self, sql: str, seq: Iterable[Any]) -> "Cursor":
        statement = _translate(str(sql))
        self._raw.executemany(statement, list(seq))
        return self

    def executescript(self, script: str) -> None:
        self._owner.executescript(script)

    def fetchone(self) -> Optional[Row]:
        row = self._raw.fetchone()
        if row is None:
            return None
        decoded = self._decode([row])
        return decoded[0]

    def fetchall(self) -> List[Row]:
        return self._decode(self._raw.fetchall())

    def fetchmany(self, size: int) -> List[Row]:
        return self._decode(self._raw.fetchmany(size))

    def close(self) -> None:
        self._raw.close()

    def __iter__(self):
        for row in self._raw:
            yield self._decode([row])[0]


class PGConnection:
    """Thin wrapper around a pooled psycopg2 connection."""

    def __init__(self, raw: Any):
        self._raw = raw

    @property
    def raw(self) -> Any:
        return self._raw

    @property
    def closed(self) -> bool:
        return bool(getattr(self._raw, "closed", 0))

    def reconnect(self) -> bool:
        global _pool
        try:
            if _pool is None:
                return False
            try:
                _pool.putconn(self._raw)
            except Exception:
                pass
            self._raw = _pool.getconn()
            return True
        except Exception:
            return False

    def cursor(self) -> Cursor:
        return Cursor(self, self._raw.cursor())

    def execute(self, sql: str, params: Any = None) -> Cursor:
        return self.cursor().execute(sql, params)

    def executemany(self, sql: str, seq: Iterable[Any]) -> Cursor:
        return self.cursor().executemany(sql, seq)

    def executescript(self, script: str) -> None:
        for part in str(script or "").split(";"):
            statement = part.strip()
            if not statement:
                continue
            if re.match(r"PRAGMA\b", statement, re.IGNORECASE):
                continue
            if re.match(r"VACUUM\b", statement, re.IGNORECASE):
                continue
            self._raw.cursor().execute(_translate(statement))
        self._raw.commit()

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        release()

    def __enter__(self) -> "PGConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()


_SQLITE_CONN: Optional[sqlite3.Connection] = None
_SQLITE_LOCK = threading.RLock()
_pool: Any = None
_local = threading.local()


def _sqlite_conn() -> sqlite3.Connection:
    global _SQLITE_CONN
    with _SQLITE_LOCK:
        if _SQLITE_CONN is None:
            base = Path(__file__).resolve().parent / "data"
            base.mkdir(parents=True, exist_ok=True)
            legacy = base / "🔥😈 PORT 777 EVIL ☠️🔥👹.db"
            path = legacy if legacy.exists() else base / "agent.db"
            _SQLITE_CONN = sqlite3.connect(str(path), check_same_thread=False)
            _SQLITE_CONN.row_factory = sqlite3.Row
            _SQLITE_CONN.execute("PRAGMA journal_mode=WAL")
            _SQLITE_CONN.execute("PRAGMA busy_timeout=5000")
            _SQLITE_CONN.execute("PRAGMA synchronous=NORMAL")
        return _SQLITE_CONN


def _dsn(url: str = "") -> str:
    """Strip ORM-only query params (e.g. ?pgbouncer=true) psycopg2 rejects."""
    parts = urlsplit(url or DATABASE_URL)
    if not parts.query:
        return url or DATABASE_URL
    return urlunsplit(parts._replace(query=""))


def _init_pool() -> Any:
    global _pool
    if _pool is None:
        import psycopg2
        from psycopg2.pool import ThreadedConnectionPool

        options = {
            "sslmode": os.getenv("PGSSLMODE", "require"),
            "connect_timeout": int(os.getenv("PGCONNECT_TIMEOUT", "10")),
            "application_name": "port777-ai",
        }
        _pool = ThreadedConnectionPool(
            1, int(os.getenv("PGPOOL_MAX", "40")), _dsn(), **options
        )
    return _pool


def conn():
    """Return the connection for the current thread (SQLite or pooled PG)."""
    if not IS_POSTGRES:
        return _sqlite_conn()
    current = getattr(_local, "conn", None)
    if current is None or current.closed:
        current = PGConnection(_init_pool().getconn())
        _local.conn = current
    return current


def release() -> None:
    """Return this thread's pooled connection (called on shutdown)."""
    current = getattr(_local, "conn", None)
    if current is None:
        return
    try:
        if _pool is not None:
            _pool.putconn(current.raw)
    except Exception:
        pass
    _local.conn = None


@contextmanager
def transaction(c: Any = None):
    """Atomic block: commit on success, rollback on any exception."""
    active = c or conn()
    try:
        yield active
        active.commit()
    except Exception:
        active.rollback()
        raise


def ensure_schema() -> None:
    """Apply idempotent, additive DDL. Never drops or rewrites existing data."""
    if not IS_POSTGRES:
        return
    path = Path(__file__).resolve().parent / "migrations" / "001_initial.sql"
    if path.is_file():
        conn().executescript(path.read_text(encoding="utf-8"))


def health() -> Dict[str, Any]:
    try:
        c = conn()
        c.execute("SELECT 1").fetchone()
        return {"backend": "postgresql" if IS_POSTGRES else "sqlite", "ok": True}
    except Exception as exc:
        return {
            "backend": "postgresql" if IS_POSTGRES else "sqlite",
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def page_params(page: Any, limit: Any, max_limit: int = 200) -> Tuple[int, int, int]:
    p = max(1, int(page or 1))
    size = min(max_limit, max(1, int(limit or 50)))
    return p, size, (p - 1) * size


def backend_name() -> str:
    return "postgresql" if IS_POSTGRES else "sqlite"
