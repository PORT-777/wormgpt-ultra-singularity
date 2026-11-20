"""Database schema and helpers for the SaaS layer.

Uses the unified database layer: SQLite locally, Supabase PostgreSQL in
production. The schema is identical on both backends (see migrations/001).
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import database

SCHEMA = """
CREATE TABLE IF NOT EXISTS saas_users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  username TEXT,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  status TEXT NOT NULL DEFAULT 'pending_verification',
  email_verified INTEGER NOT NULL DEFAULT 0,
  profile_image TEXT,
  preferences TEXT,
  created REAL,
  updated REAL
);
CREATE TABLE IF NOT EXISTS saas_sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created REAL,
  expires REAL,
  remember INTEGER NOT NULL DEFAULT 0,
  last_seen REAL,
  ip TEXT,
  user_agent TEXT,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS saas_tokens (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  expires REAL,
  used INTEGER NOT NULL DEFAULT 0,
  created REAL
);
CREATE TABLE IF NOT EXISTS saas_plans (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  monthly_price REAL NOT NULL DEFAULT 0,
  annual_price REAL NOT NULL DEFAULT 0,
  currency TEXT NOT NULL DEFAULT 'USD',
  config TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  updated REAL
);
CREATE TABLE IF NOT EXISTS saas_subscriptions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  plan_id TEXT NOT NULL,
  status TEXT NOT NULL,
  provider TEXT,
  provider_ref TEXT,
  current_period_end REAL,
  created REAL,
  updated REAL
);
CREATE TABLE IF NOT EXISTS saas_payments (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  subscription_id TEXT,
  plan_id TEXT,
  provider_ref TEXT,
  provider TEXT NOT NULL,
  provider_txn_id TEXT,
  amount REAL,
  currency TEXT,
  status TEXT,
  event TEXT,
  payload TEXT,
  created REAL,
  UNIQUE(provider, provider_txn_id)
);
CREATE TABLE IF NOT EXISTS saas_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  amount REAL NOT NULL,
  model TEXT,
  session_id TEXT,
  success INTEGER NOT NULL DEFAULT 1,
  ts REAL
);
CREATE TABLE IF NOT EXISTS saas_api_keys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT,
  key_hash TEXT NOT NULL,
  prefix TEXT,
  permissions TEXT,
  created REAL,
  last_used REAL,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS saas_files (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  bucket TEXT NOT NULL,
  object_path TEXT NOT NULL,
  filename TEXT,
  size INTEGER NOT NULL DEFAULT 0,
  content_type TEXT,
  sha256 TEXT,
  created REAL,
  updated REAL
);
CREATE TABLE IF NOT EXISTS user_profiles (
  user_id TEXT PRIMARY KEY,
  display_name TEXT,
  bio TEXT,
  avatar_path TEXT,
  system_prompt TEXT,
  model_preferences TEXT,
  memory TEXT,
  preferences TEXT,
  updated REAL
);
CREATE TABLE IF NOT EXISTS webhook_events (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  event_type TEXT,
  payload TEXT,
  signature_valid INTEGER NOT NULL DEFAULT 0,
  processed INTEGER NOT NULL DEFAULT 0,
  created REAL
);
CREATE TABLE IF NOT EXISTS credit_balances (
  user_id TEXT PRIMARY KEY,
  balance REAL NOT NULL DEFAULT 0,
  updated REAL
);
CREATE TABLE IF NOT EXISTS credit_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  delta REAL NOT NULL,
  reason TEXT,
  actor TEXT,
  created REAL
);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT,
  action TEXT NOT NULL,
  target TEXT,
  detail TEXT,
  created REAL
);
CREATE INDEX IF NOT EXISTS idx_saas_sessions_user ON saas_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_saas_usage_user ON saas_usage(user_id, metric);
CREATE INDEX IF NOT EXISTS idx_saas_subs_user ON saas_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_saas_keys_user ON saas_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_saas_files_user ON saas_files(user_id, bucket);
CREATE INDEX IF NOT EXISTS idx_saas_payments_user ON saas_payments(user_id);
"""


def init() -> None:
    c = conn()
    c.executescript(SCHEMA)
    # Safe additive migrations for databases created by earlier versions.
    try:
        cols = [r[1] for r in c.execute("PRAGMA table_info(saas_payments)").fetchall()]
        for name in ("plan_id", "provider_ref"):
            if name not in cols:
                c.execute(f"ALTER TABLE saas_payments ADD COLUMN {name} TEXT")
        c.commit()
    except Exception:
        pass


def conn():
    return database.conn()


def jdump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def jload(value: Any, fallback=None):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def now() -> float:
    return time.time()
