"""Persistence for the AI Computer subsystem.

Uses the application's existing SQLite database through database.conn().
Large logs and binary artifacts live on disk; DB stores paths and metadata.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import database

ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "data" / "computer_artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS computers (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  mode TEXT NOT NULL,
  provider TEXT NOT NULL,
  provider_ref TEXT NOT NULL,
  status TEXT NOT NULL,
  os TEXT,
  resources TEXT,
  metadata TEXT,
  created REAL,
  updated REAL
);
CREATE TABLE IF NOT EXISTS computer_sessions (
  id TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  provider_ref TEXT,
  metadata TEXT,
  created REAL
);
CREATE TABLE IF NOT EXISTS terminal_sessions (
  id TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  provider_session_id TEXT,
  cwd TEXT,
  history_path TEXT,
  created REAL
);
CREATE TABLE IF NOT EXISTS browser_sessions (
  id TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  provider_session_id TEXT,
  metadata TEXT,
  created REAL
);
CREATE TABLE IF NOT EXISTS processes (
  pid TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  command TEXT,
  status TEXT,
  port INTEGER,
  logs_path TEXT,
  created REAL
);
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  name TEXT,
  path TEXT,
  size INTEGER,
  sha256 TEXT,
  created REAL
);
CREATE TABLE IF NOT EXISTS execution_jobs (
  id TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  session_id TEXT,
  status TEXT,
  steps TEXT,
  result_path TEXT,
  error TEXT,
  created REAL,
  updated REAL
);
CREATE TABLE IF NOT EXISTS execution_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  level TEXT,
  message TEXT,
  ts REAL
);
CREATE TABLE IF NOT EXISTS resource_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  cpu REAL,
  memory REAL,
  disk REAL,
  network TEXT,
  raw TEXT,
  ts REAL
);
CREATE TABLE IF NOT EXISTS provider_configs (
  provider TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL,
  config TEXT,
  updated REAL
);
CREATE INDEX IF NOT EXISTS idx_computers_user ON computers(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON execution_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_job ON execution_logs(job_id);
"""


def init_tables() -> None:
    conn = database.conn()
    conn.executescript(SCHEMA)
    conn.commit()


def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _un(value: Any, fallback=None):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def save_computer(row: Dict[str, Any]) -> None:
    conn = database.conn()
    conn.execute(
        "INSERT OR REPLACE INTO computers(id,user_id,name,mode,provider,provider_ref,status,os,resources,metadata,created,updated) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (row["id"], row["user_id"], row.get("name", ""), row["mode"], row["provider"],
         row["provider_ref"], row["status"], row.get("os", ""), _j(row.get("resources", {})),
         _j(row.get("metadata", {})), row.get("created", time.time()), time.time()),
    )
    conn.commit()


def get_computer(computer_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = database.conn()
    if user_id:
        row = conn.execute("SELECT * FROM computers WHERE id=? AND user_id=?", (computer_id, user_id)).fetchone()
    else:
        row = conn.execute("SELECT * FROM computers WHERE id=?", (computer_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["resources"] = _un(d.get("resources"), {})
    d["metadata"] = _un(d.get("metadata"), {})
    return d


def list_computers(user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = database.conn()
    if user_id:
        rows = conn.execute("SELECT * FROM computers WHERE user_id=? ORDER BY updated DESC LIMIT ?", (user_id, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM computers ORDER BY updated DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r); d["resources"] = _un(d.get("resources"), {}); d["metadata"] = _un(d.get("metadata"), {})
        out.append(d)
    return out


def delete_computer(computer_id: str, user_id: Optional[str] = None) -> bool:
    conn = database.conn()
    cur = conn.execute("DELETE FROM computers WHERE id=? AND user_id=?" if user_id
                       else "DELETE FROM computers WHERE id=?",
                       (computer_id, user_id) if user_id else (computer_id,))
    conn.commit()
    return cur.rowcount > 0


def add_log(job_id: str, computer_id: str, user_id: str, level: str, message: str) -> None:
    conn = database.conn()
    conn.execute("INSERT INTO execution_logs(job_id,computer_id,user_id,level,message,ts) VALUES(?,?,?,?,?,?)",
                 (job_id, computer_id, user_id, level, str(message)[:20000], time.time()))
    conn.commit()


def logs(job_id: str, limit: int = 300) -> List[Dict[str, Any]]:
    conn = database.conn()
    rows = conn.execute("SELECT level,message,ts FROM execution_logs WHERE job_id=? ORDER BY id DESC LIMIT ?",
                        (job_id, limit)).fetchall()
    return [dict(r) for r in reversed(rows)]


def save_job(row: Dict[str, Any]) -> None:
    conn = database.conn()
    conn.execute(
        "INSERT OR REPLACE INTO execution_jobs(id,computer_id,user_id,session_id,status,steps,result_path,error,created,updated) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (row["id"], row["computer_id"], row["user_id"], row.get("session_id", ""), row["status"],
         _j(row.get("steps", [])), row.get("result_path", ""), row.get("error", ""),
         row.get("created", time.time()), time.time()),
    )
    conn.commit()


def get_job(job_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = database.conn()
    row = conn.execute("SELECT * FROM execution_jobs WHERE id=?" + (" AND user_id=?" if user_id else ""),
                       (job_id, user_id) if user_id else (job_id,)).fetchone()
    if not row:
        return None
    d = dict(row); d["steps"] = _un(d.get("steps"), [])
    return d
