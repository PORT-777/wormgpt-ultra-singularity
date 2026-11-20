-- Row Level Security for Supabase.
--
-- Important: the application authenticates with its own account system and
-- calls Supabase with the service key from the trusted backend. The service
-- key intentionally bypasses RLS; the backend enforces ownership on every
-- request (saas/files.py, saas/api.py). These policies protect the same
-- tables if a Supabase Auth identity is introduced later, and they map the
-- JWT `sub` claim to the existing `*_user_id` columns.
--
-- Re-running this file is safe: policies are dropped before recreation.

CREATE OR REPLACE FUNCTION port777_claim_sub() RETURNS TEXT AS $$
  SELECT NULLIF(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub';
$$ LANGUAGE sql STABLE;

-- saas_users
ALTER TABLE saas_users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS saas_users_self_select ON saas_users;
CREATE POLICY saas_users_self_select ON saas_users FOR SELECT
  USING (id = port777_claim_sub());
DROP POLICY IF EXISTS saas_users_self_update ON saas_users;
CREATE POLICY saas_users_self_update ON saas_users FOR UPDATE
  USING (id = port777_claim_sub()) WITH CHECK (id = port777_claim_sub());

-- Owned records
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'saas_sessions', 'saas_tokens', 'saas_subscriptions', 'saas_payments',
    'saas_usage', 'saas_api_keys', 'saas_files', 'user_profiles',
    'credit_balances', 'credit_ledger', 'computers', 'computer_sessions',
    'terminal_sessions', 'browser_sessions', 'execution_jobs',
    'execution_logs', 'resource_metrics', 'artifacts'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'port777_owner_select', t);
    EXECUTE format(
      'CREATE POLICY %I ON %I FOR SELECT USING (user_id = port777_claim_sub())',
      'port777_owner_select', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'port777_owner_insert', t);
    EXECUTE format(
      'CREATE POLICY %I ON %I FOR INSERT WITH CHECK (user_id = port777_claim_sub())',
      'port777_owner_insert', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'port777_owner_update', t);
    EXECUTE format(
      'CREATE POLICY %I ON %I FOR UPDATE USING (user_id = port777_claim_sub()) WITH CHECK (user_id = port777_claim_sub())',
      'port777_owner_update', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'port777_owner_delete', t);
    EXECUTE format(
      'CREATE POLICY %I ON %I FOR DELETE USING (user_id = port777_claim_sub())',
      'port777_owner_delete', t);
  END LOOP;
END $$;

-- Storage bucket policies. Files are stored at {user_id}/filename.ext.
DO $$
DECLARE b TEXT;
BEGIN
  FOREACH b IN ARRAY ARRAY[
    'user-files', 'chat-attachments', 'ai-generated-files',
    'agent-artifacts', 'exports'
  ] LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON storage.objects', 'port777_' || replace(b, '-', '_') || '_select');
    EXECUTE format(
      'CREATE POLICY %I ON storage.objects FOR SELECT TO authenticated '
      'USING (bucket_id = %L AND (storage.foldername(name))[1] = port777_claim_sub())',
      'port777_' || replace(b, '-', '_') || '_select', b);
    EXECUTE format('DROP POLICY IF EXISTS %I ON storage.objects', 'port777_' || replace(b, '-', '_') || '_insert');
    EXECUTE format(
      'CREATE POLICY %I ON storage.objects FOR INSERT TO authenticated '
      'WITH CHECK (bucket_id = %L AND (storage.foldername(name))[1] = port777_claim_sub())',
      'port777_' || replace(b, '-', '_') || '_insert', b);
    EXECUTE format('DROP POLICY IF EXISTS %I ON storage.objects', 'port777_' || replace(b, '-', '_') || '_update');
    EXECUTE format(
      'CREATE POLICY %I ON storage.objects FOR UPDATE TO authenticated '
      'USING (bucket_id = %L AND (storage.foldername(name))[1] = port777_claim_sub())',
      'port777_' || replace(b, '-', '_') || '_update', b);
    EXECUTE format('DROP POLICY IF EXISTS %I ON storage.objects', 'port777_' || replace(b, '-', '_') || '_delete');
    EXECUTE format(
      'CREATE POLICY %I ON storage.objects FOR DELETE TO authenticated '
      'USING (bucket_id = %L AND (storage.foldername(name))[1] = port777_claim_sub())',
      'port777_' || replace(b, '-', '_') || '_delete', b);
  END LOOP;
END $$;

-- Avatars are public reads, owner-only writes (matches the setup spreadsheet).
DROP POLICY IF EXISTS port777_avatars_public_select ON storage.objects;
CREATE POLICY port777_avatars_public_select ON storage.objects FOR SELECT
  USING (bucket_id = 'avatars');
DROP POLICY IF EXISTS port777_avatars_insert ON storage.objects;
CREATE POLICY port777_avatars_insert ON storage.objects FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'avatars' AND (storage.foldername(name))[1] = port777_claim_sub());
DROP POLICY IF EXISTS port777_avatars_update ON storage.objects;
CREATE POLICY port777_avatars_update ON storage.objects FOR UPDATE TO authenticated
  USING (bucket_id = 'avatars' AND (storage.foldername(name))[1] = port777_claim_sub());
DROP POLICY IF EXISTS port777_avatars_delete ON storage.objects;
CREATE POLICY port777_avatars_delete ON storage.objects FOR DELETE TO authenticated
  USING (bucket_id = 'avatars' AND (storage.foldername(name))[1] = port777_claim_sub());
