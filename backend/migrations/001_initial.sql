-- PORT 777 AI — initial PostgreSQL/Supabase schema.
-- Idempotent and additive only. No DROP, no TRUNCATE, no data rewrites.

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  created DOUBLE PRECISION,
  title TEXT
);
CREATE TABLE IF NOT EXISTS messages (
  id BIGSERIAL PRIMARY KEY,
  session_id TEXT,
  role TEXT,
  content TEXT,
  ts DOUBLE PRECISION,
  run_id TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS scheduled_tasks (
  id BIGSERIAL PRIMARY KEY,
  prompt TEXT,
  interval_minutes INTEGER,
  active INTEGER DEFAULT 1,
  next_run DOUBLE PRECISION,
  last_result TEXT,
  created DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  ts DOUBLE PRECISION,
  tool TEXT,
  detail TEXT,
  outcome TEXT
);
CREATE TABLE IF NOT EXISTS proposals (
  id BIGSERIAL PRIMARY KEY,
  ts DOUBLE PRECISION,
  title TEXT,
  target TEXT,
  rationale TEXT,
  content TEXT,
  status TEXT DEFAULT 'pending',
  session_id TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS kv_store (
  module TEXT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  owner TEXT DEFAULT '',
  workspace TEXT DEFAULT '',
  updated DOUBLE PRECISION,
  PRIMARY KEY (module, key)
);
CREATE TABLE IF NOT EXISTS message_feedback (
  id BIGSERIAL PRIMARY KEY,
  ts DOUBLE PRECISION,
  session_id TEXT,
  message_id TEXT,
  vote INTEGER
);
CREATE TABLE IF NOT EXISTS trace_events (
  id BIGSERIAL PRIMARY KEY,
  session_id TEXT,
  run_id TEXT,
  seq INTEGER,
  ts DOUBLE PRECISION,
  kind TEXT,
  data TEXT
);

-- Accounts and authentication metadata
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
  created DOUBLE PRECISION,
  updated DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS saas_sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created DOUBLE PRECISION,
  expires DOUBLE PRECISION,
  remember INTEGER NOT NULL DEFAULT 0,
  last_seen DOUBLE PRECISION,
  ip TEXT,
  user_agent TEXT,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS saas_tokens (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  expires DOUBLE PRECISION,
  used INTEGER NOT NULL DEFAULT 0,
  created DOUBLE PRECISION
);

-- Plans, subscriptions, payments and usage
CREATE TABLE IF NOT EXISTS saas_plans (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  monthly_price DOUBLE PRECISION NOT NULL DEFAULT 0,
  annual_price DOUBLE PRECISION NOT NULL DEFAULT 0,
  currency TEXT NOT NULL DEFAULT 'USD',
  config TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  updated DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS saas_subscriptions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  plan_id TEXT NOT NULL,
  status TEXT NOT NULL,
  provider TEXT,
  provider_ref TEXT,
  current_period_end DOUBLE PRECISION,
  created DOUBLE PRECISION,
  updated DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS saas_payments (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  subscription_id TEXT,
  plan_id TEXT,
  provider_ref TEXT,
  provider TEXT NOT NULL,
  provider_txn_id TEXT,
  amount DOUBLE PRECISION,
  currency TEXT,
  status TEXT,
  event TEXT,
  payload TEXT,
  created DOUBLE PRECISION,
  UNIQUE (provider, provider_txn_id)
);
CREATE TABLE IF NOT EXISTS saas_usage (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  amount DOUBLE PRECISION NOT NULL,
  model TEXT,
  session_id TEXT,
  success INTEGER NOT NULL DEFAULT 1,
  ts DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS saas_api_keys (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT,
  key_hash TEXT NOT NULL,
  prefix TEXT,
  permissions TEXT,
  created DOUBLE PRECISION,
  last_used DOUBLE PRECISION,
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
  created DOUBLE PRECISION,
  updated DOUBLE PRECISION
);

-- Conversations, messages and preferences are the sessions/messages tables
-- above plus these explicit platform records.
CREATE TABLE IF NOT EXISTS user_profiles (
  user_id TEXT PRIMARY KEY,
  display_name TEXT,
  bio TEXT,
  avatar_path TEXT,
  system_prompt TEXT,
  model_preferences TEXT,
  memory TEXT,
  preferences TEXT,
  updated DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS webhook_events (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  event_type TEXT,
  payload TEXT,
  signature_valid INTEGER NOT NULL DEFAULT 0,
  processed INTEGER NOT NULL DEFAULT 0,
  created DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS credit_balances (
  user_id TEXT PRIMARY KEY,
  balance DOUBLE PRECISION NOT NULL DEFAULT 0,
  updated DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS credit_ledger (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  delta DOUBLE PRECISION NOT NULL,
  reason TEXT,
  actor TEXT,
  created DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS audit_events (
  id BIGSERIAL PRIMARY KEY,
  actor TEXT,
  action TEXT NOT NULL,
  target TEXT,
  detail TEXT,
  created DOUBLE PRECISION
);

-- AI Computer metadata (large logs/artifacts live in object storage)
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
  created DOUBLE PRECISION,
  updated DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS computer_sessions (
  id TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  provider_ref TEXT,
  metadata TEXT,
  created DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS terminal_sessions (
  id TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  provider_session_id TEXT,
  cwd TEXT,
  history_path TEXT,
  created DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS browser_sessions (
  id TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  provider_session_id TEXT,
  metadata TEXT,
  created DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS processes (
  pid TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  command TEXT,
  status TEXT,
  port INTEGER,
  logs_path TEXT,
  created DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  name TEXT,
  path TEXT,
  size INTEGER,
  sha256 TEXT,
  created DOUBLE PRECISION
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
  created DOUBLE PRECISION,
  updated DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS execution_logs (
  id BIGSERIAL PRIMARY KEY,
  job_id TEXT NOT NULL,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  level TEXT,
  message TEXT,
  ts DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS resource_metrics (
  id BIGSERIAL PRIMARY KEY,
  computer_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  cpu DOUBLE PRECISION,
  memory DOUBLE PRECISION,
  disk DOUBLE PRECISION,
  network TEXT,
  raw TEXT,
  ts DOUBLE PRECISION
);
CREATE TABLE IF NOT EXISTS provider_configs (
  provider TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL,
  config TEXT,
  updated DOUBLE PRECISION
);

-- Indexes for high-frequency ownership/lookup queries
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_trace_session ON trace_events(session_id);
CREATE INDEX IF NOT EXISTS idx_saas_sessions_user ON saas_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_saas_tokens_user ON saas_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_saas_usage_user_metric ON saas_usage(user_id, metric, ts);
CREATE INDEX IF NOT EXISTS idx_saas_subs_user ON saas_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_saas_payments_user ON saas_payments(user_id, created);
CREATE INDEX IF NOT EXISTS idx_saas_keys_user ON saas_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_saas_files_user ON saas_files(user_id, bucket, created);
CREATE INDEX IF NOT EXISTS idx_computers_user ON computers(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON execution_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_job ON execution_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_user ON user_profiles(user_id);
