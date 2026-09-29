-- ACPOS migration 0045: remove the historical local:test acceptance identity.
-- Cleanup is exact and fail-closed; admin/current identities are not touched.

DO $$
DECLARE
  v_user uuid;
  v_count integer;
BEGIN
  SELECT user_id INTO v_user
  FROM public.app_users
  WHERE external_subject='local:test';

  IF v_user IS NULL THEN
    RETURN;
  END IF;

  SELECT count(*) INTO v_count
  FROM public.app_users
  WHERE external_subject='local:test';
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0045_TEST_IDENTITY_CARDINALITY_INVALID'; END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.app_users
    WHERE user_id=v_user
      AND display_name='TEST'
      AND email::text='test'
      AND status='READY'
      AND disabled_at IS NULL
  ) THEN RAISE EXCEPTION 'CLEANUP0045_TEST_IDENTITY_MARKER_INVALID'; END IF;

  SELECT count(*) INTO v_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE (a.user_id=v_user OR a.granted_by_user_id=v_user);
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0045_TEST_ASSIGNMENT_CARDINALITY_INVALID'; END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM public.account_permission_assignments a
    JOIN public.permission_resources r ON r.resource_id=a.resource_id
    WHERE a.user_id=v_user
      AND a.granted_by_user_id=v_user
      AND r.resource_key='page:workspace:WB-01'
      AND a.action='VIEW'
      AND a.effect='ALLOW'
      AND a.status='APPROVED'
      AND a.approval_ref='BOOTSTRAP-TEST-WB01-VIEW-2026-09-05'
  ) THEN RAISE EXCEPTION 'CLEANUP0045_TEST_ASSIGNMENT_MARKER_INVALID'; END IF;

  SELECT count(*) INTO v_count
  FROM public.audit_events
  WHERE actor_id=v_user OR entity_id=v_user;
  IF v_count<>3 THEN RAISE EXCEPTION 'CLEANUP0045_TEST_AUDIT_CARDINALITY_INVALID'; END IF;

  IF EXISTS (
    SELECT 1 FROM public.audit_events
    WHERE (actor_id=v_user OR entity_id=v_user)
      AND NOT (
        actor_id=v_user
        AND entity_id=v_user
        AND action='getDashboardReadModel'
        AND entity_type='workspace:WB-01'
        AND actor_type='USER'
      )
  ) THEN RAISE EXCEPTION 'CLEANUP0045_TEST_AUDIT_MARKER_INVALID'; END IF;

  IF EXISTS (
    SELECT 1 FROM acpos_runtime.sessions
    WHERE account_id=v_user::text
  ) THEN RAISE EXCEPTION 'CLEANUP0045_TEST_IDENTITY_SESSION_STILL_ACTIVE'; END IF;

  DELETE FROM public.audit_events
  WHERE actor_id=v_user AND entity_id=v_user
    AND action='getDashboardReadModel'
    AND entity_type='workspace:WB-01';

  DELETE FROM public.account_permission_assignments
  WHERE user_id=v_user
    AND granted_by_user_id=v_user
    AND approval_ref='BOOTSTRAP-TEST-WB01-VIEW-2026-09-05';

  DELETE FROM public.app_users
  WHERE user_id=v_user AND external_subject='local:test';
END
$$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0045_local_test_identity_cleanup',
  'af1384b6f8c1cdb36a69e4d1e69baabdf8c1fbcce7bc17edc7c5ad39feaf0376',
  'migration-runner',
  'CR-RUNTIME-0045'
)
ON CONFLICT(migration_id) DO NOTHING;
