-- ACPOS migration 0020: System Lifecycle Runtime materialization.
-- Change ref: CR-SYS-0020 (PENDING HUMAN APPROVAL FOR PRODUCTION APPLY).
-- Materializes the SystemChangeService owner declared by Current SYS-01 Authority.
-- Reuses acpos_app_runtime/session-bound RLS, audit_events, and AIAPI runSandboxTest.
-- Does not enable SYS-01 visual-phase controls and does not create any deploy/release path.

CREATE TABLE IF NOT EXISTS public.system_changes (
  system_change_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  current_goal text NOT NULL,
  scope jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'ACTIVE',
  current_candidate_id uuid NULL,
  created_by uuid NOT NULL REFERENCES public.app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT system_changes_scope_object CHECK (jsonb_typeof(scope) = 'object'),
  CONSTRAINT system_changes_status_check CHECK (
    status IN ('ACTIVE','FROZEN','IMPLEMENTING','VALIDATING','READY_FOR_APPROVAL','APPROVED','BLOCKED','CLOSED')
  )
);

CREATE TABLE IF NOT EXISTS public.system_change_candidates (
  system_change_candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  system_change_id uuid NOT NULL REFERENCES public.system_changes(system_change_id) ON DELETE CASCADE,
  candidate_document jsonb NOT NULL,
  context_fingerprint char(64) NOT NULL,
  status text NOT NULL DEFAULT 'DRAFT',
  created_by uuid NOT NULL REFERENCES public.app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT system_change_candidates_document_object CHECK (jsonb_typeof(candidate_document) = 'object'),
  CONSTRAINT system_change_candidates_fingerprint_check CHECK (context_fingerprint ~ '^[0-9a-f]{64}$'),
  CONSTRAINT system_change_candidates_status_check CHECK (status IN ('DRAFT','READY','SELECTED','SUPERSEDED'))
);

CREATE TABLE IF NOT EXISTS public.system_change_requests (
  system_change_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  system_change_id uuid NOT NULL REFERENCES public.system_changes(system_change_id) ON DELETE CASCADE,
  system_change_candidate_id uuid NOT NULL REFERENCES public.system_change_candidates(system_change_candidate_id),
  reason text NOT NULL,
  impact_scope jsonb NOT NULL DEFAULT '{}'::jsonb,
  status text NOT NULL DEFAULT 'SUBMITTED',
  created_by uuid NOT NULL REFERENCES public.app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  decided_at timestamptz NULL,
  CONSTRAINT system_change_requests_impact_scope_object CHECK (jsonb_typeof(impact_scope) = 'object'),
  CONSTRAINT system_change_requests_status_check CHECK (
    status IN ('SUBMITTED','APPROVED','REJECTED','IN_IMPLEMENTATION','VALIDATING','CLOSED')
  )
);

ALTER TABLE public.system_changes
  DROP CONSTRAINT IF EXISTS fk_system_changes_current_candidate,
  ADD CONSTRAINT fk_system_changes_current_candidate
    FOREIGN KEY (current_candidate_id)
    REFERENCES public.system_change_candidates(system_change_candidate_id)
    DEFERRABLE INITIALLY DEFERRED;

CREATE INDEX IF NOT EXISTS idx_system_changes_status_updated
  ON public.system_changes(status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_system_change_candidates_change_created
  ON public.system_change_candidates(system_change_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_system_change_requests_change_created
  ON public.system_change_requests(system_change_id, created_at DESC);

CREATE OR REPLACE FUNCTION acpos_runtime.can_access_system_change(p_system_change_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT
    acpos_runtime.current_actor_is_bootstrap_admin()
    OR EXISTS (
      SELECT 1
      FROM public.system_changes s
      WHERE s.system_change_id = p_system_change_id
        AND s.created_by = acpos_runtime.current_actor_user_id()
    )
$$;

REVOKE ALL ON FUNCTION acpos_runtime.can_access_system_change(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acpos_runtime.can_access_system_change(uuid) TO acpos_app_runtime;

GRANT SELECT, INSERT, UPDATE ON
  public.system_changes,
  public.system_change_candidates,
  public.system_change_requests
TO acpos_app_runtime;

ALTER TABLE public.system_changes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_system_changes_select ON public.system_changes;
DROP POLICY IF EXISTS acpos_system_changes_write ON public.system_changes;
CREATE POLICY acpos_system_changes_select ON public.system_changes
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_system_change(system_change_id));
CREATE POLICY acpos_system_changes_write ON public.system_changes
FOR ALL TO acpos_app_runtime
USING (acpos_runtime.can_access_system_change(system_change_id))
WITH CHECK (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR created_by = acpos_runtime.current_actor_user_id()
);

ALTER TABLE public.system_change_candidates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_system_change_candidates_select ON public.system_change_candidates;
DROP POLICY IF EXISTS acpos_system_change_candidates_write ON public.system_change_candidates;
CREATE POLICY acpos_system_change_candidates_select ON public.system_change_candidates
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_system_change(system_change_id));
CREATE POLICY acpos_system_change_candidates_write ON public.system_change_candidates
FOR ALL TO acpos_app_runtime
USING (acpos_runtime.can_access_system_change(system_change_id))
WITH CHECK (acpos_runtime.can_access_system_change(system_change_id));

ALTER TABLE public.system_change_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_system_change_requests_select ON public.system_change_requests;
DROP POLICY IF EXISTS acpos_system_change_requests_write ON public.system_change_requests;
CREATE POLICY acpos_system_change_requests_select ON public.system_change_requests
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_system_change(system_change_id));
CREATE POLICY acpos_system_change_requests_write ON public.system_change_requests
FOR ALL TO acpos_app_runtime
USING (acpos_runtime.can_access_system_change(system_change_id))
WITH CHECK (acpos_runtime.can_access_system_change(system_change_id));

DO $$
DECLARE
  table_count bigint;
  policy_count bigint;
BEGIN
  SELECT count(*) INTO table_count
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname IN ('system_changes','system_change_candidates','system_change_requests')
    AND c.relrowsecurity;

  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN ('system_changes','system_change_candidates','system_change_requests')
    AND policyname IN (
      'acpos_system_changes_select','acpos_system_changes_write',
      'acpos_system_change_candidates_select','acpos_system_change_candidates_write',
      'acpos_system_change_requests_select','acpos_system_change_requests_write'
    );

  IF table_count <> 3 THEN
    RAISE EXCEPTION 'SYSTEM_LIFECYCLE_RLS_TABLE_COUNT_MISMATCH:%', table_count;
  END IF;
  IF policy_count <> 6 THEN
    RAISE EXCEPTION 'SYSTEM_LIFECYCLE_RLS_POLICY_COUNT_MISMATCH:%', policy_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES(
  '0020_system_lifecycle_runtime',
  '22fb185cc50fa0d19d1431bd5e2fb6233ca28878dbafa7b65da9d44caba02b9f',
  'migration-runner',
  'PENDING-CR-SYS-0020'
)
ON CONFLICT (migration_id) DO NOTHING;
