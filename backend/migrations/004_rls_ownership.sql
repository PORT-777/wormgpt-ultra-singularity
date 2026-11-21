-- Extend RLS to conversations and messages now that they carry user_id.
-- Backend service-key access bypasses RLS; these policies protect the tables
-- if a Supabase Auth identity is introduced later.
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS port777_owner_select ON sessions;
CREATE POLICY port777_owner_select ON sessions FOR SELECT
  USING (user_id = port777_claim_sub());
DROP POLICY IF EXISTS port777_owner_insert ON sessions;
CREATE POLICY port777_owner_insert ON sessions FOR INSERT
  WITH CHECK (user_id = port777_claim_sub());
DROP POLICY IF EXISTS port777_owner_update ON sessions;
CREATE POLICY port777_owner_update ON sessions FOR UPDATE
  USING (user_id = port777_claim_sub()) WITH CHECK (user_id = port777_claim_sub());
DROP POLICY IF EXISTS port777_owner_delete ON sessions;
CREATE POLICY port777_owner_delete ON sessions FOR DELETE
  USING (user_id = port777_claim_sub());

DROP POLICY IF EXISTS port777_owner_select ON messages;
CREATE POLICY port777_owner_select ON messages FOR SELECT
  USING (user_id = port777_claim_sub());
DROP POLICY IF EXISTS port777_owner_insert ON messages;
CREATE POLICY port777_owner_insert ON messages FOR INSERT
  WITH CHECK (user_id = port777_claim_sub());
DROP POLICY IF EXISTS port777_owner_update ON messages;
CREATE POLICY port777_owner_update ON messages FOR UPDATE
  USING (user_id = port777_claim_sub()) WITH CHECK (user_id = port777_claim_sub());
DROP POLICY IF EXISTS port777_owner_delete ON messages;
CREATE POLICY port777_owner_delete ON messages FOR DELETE
  USING (user_id = port777_claim_sub());
