-- Ownership and identity unification (additive, non-destructive).
-- Existing rows keep their ids; new columns are backfilled safely.

-- 1) Conversations and messages are now explicitly owned.
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'default_user';
ALTER TABLE messages ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT 'default_user';
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);

-- 2) Stable UUID identity alongside the existing text id (no id rewrite).
ALTER TABLE saas_users ADD COLUMN IF NOT EXISTS uuid UUID DEFAULT gen_random_uuid();
UPDATE saas_users SET uuid = gen_random_uuid() WHERE uuid IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_saas_users_uuid ON saas_users(uuid);

-- 3) Real TIMESTAMPTZ projections kept in sync with the Unix epoch columns.
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
ALTER TABLE saas_users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
ALTER TABLE saas_files ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
ALTER TABLE saas_payments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
ALTER TABLE saas_subscriptions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;
ALTER TABLE saas_usage ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;

UPDATE sessions SET created_at = to_timestamp(created) WHERE created_at IS NULL AND created IS NOT NULL;
UPDATE messages SET created_at = to_timestamp(ts) WHERE created_at IS NULL AND ts IS NOT NULL;
UPDATE saas_users SET created_at = to_timestamp(created) WHERE created_at IS NULL AND created IS NOT NULL;
UPDATE saas_files SET created_at = to_timestamp(created) WHERE created_at IS NULL AND created IS NOT NULL;
UPDATE saas_payments SET created_at = to_timestamp(created) WHERE created_at IS NULL AND created IS NOT NULL;
UPDATE saas_subscriptions SET created_at = to_timestamp(created) WHERE created_at IS NULL AND created IS NOT NULL;
UPDATE saas_usage SET created_at = to_timestamp(ts) WHERE created_at IS NULL AND ts IS NOT NULL;

CREATE OR REPLACE FUNCTION p7_sessions_ts() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.created_at := to_timestamp(NEW.created); RETURN NEW; END $$;
DROP TRIGGER IF EXISTS p7_sessions_ts ON sessions;
CREATE TRIGGER p7_sessions_ts BEFORE INSERT OR UPDATE ON sessions
  FOR EACH ROW EXECUTE FUNCTION p7_sessions_ts();

CREATE OR REPLACE FUNCTION p7_messages_ts() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.created_at := to_timestamp(NEW.ts); RETURN NEW; END $$;
DROP TRIGGER IF EXISTS p7_messages_ts ON messages;
CREATE TRIGGER p7_messages_ts BEFORE INSERT OR UPDATE ON messages
  FOR EACH ROW EXECUTE FUNCTION p7_messages_ts();

CREATE OR REPLACE FUNCTION p7_created_ts() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.created_at := to_timestamp(NEW.created); RETURN NEW; END $$;
DROP TRIGGER IF EXISTS p7_users_ts ON saas_users;
CREATE TRIGGER p7_users_ts BEFORE INSERT OR UPDATE ON saas_users
  FOR EACH ROW EXECUTE FUNCTION p7_created_ts();
DROP TRIGGER IF EXISTS p7_files_ts ON saas_files;
CREATE TRIGGER p7_files_ts BEFORE INSERT OR UPDATE ON saas_files
  FOR EACH ROW EXECUTE FUNCTION p7_created_ts();
DROP TRIGGER IF EXISTS p7_payments_ts ON saas_payments;
CREATE TRIGGER p7_payments_ts BEFORE INSERT OR UPDATE ON saas_payments
  FOR EACH ROW EXECUTE FUNCTION p7_created_ts();
DROP TRIGGER IF EXISTS p7_subscriptions_ts ON saas_subscriptions;
CREATE TRIGGER p7_subscriptions_ts BEFORE INSERT OR UPDATE ON saas_subscriptions
  FOR EACH ROW EXECUTE FUNCTION p7_created_ts();

CREATE OR REPLACE FUNCTION p7_usage_ts() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.created_at := to_timestamp(NEW.ts); RETURN NEW; END $$;
DROP TRIGGER IF EXISTS p7_usage_ts ON saas_usage;
CREATE TRIGGER p7_usage_ts BEFORE INSERT OR UPDATE ON saas_usage
  FOR EACH ROW EXECUTE FUNCTION p7_usage_ts();
