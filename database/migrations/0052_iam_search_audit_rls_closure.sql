-- ACPOS migration 0052: IAM Search audit RLS closure.
-- Reuses public.audit_events as the canonical IAM audit owner already used by Production IAM runtime.
-- Adds only a narrow INSERT policy for Current IAM-01 searchProjection evidence.
-- No account, permission, access-review, security-audit or other business rows are created.

DROP POLICY IF EXISTS acpos_audit_events_iam_search_insert ON public.audit_events;

CREATE POLICY acpos_audit_events_iam_search_insert ON public.audit_events
FOR INSERT TO acpos_app_runtime
WITH CHECK(
  entity_type='admin:IAM-01'
  AND actor_type='USER'::public.actor_type
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND workspace_id IS NULL
  AND action='searchProjection'
  AND (
    (
      (reason LIKE 'ALLOWED:%' OR reason LIKE 'SUCCESS:%')
      AND acpos_runtime.has_account_resource_action('page:admin:IAM-01','VIEW')
      AND acpos_runtime.has_account_resource_action('action:admin:IAM-01:ACT-SEARCH','INVOKE')
    )
    OR reason LIKE 'DENIED:%'
    OR reason LIKE 'ERROR:%'
  )
);

DO $$
DECLARE p integer; g integer;
BEGIN
  SELECT count(*) INTO p
  FROM pg_policies
  WHERE schemaname='public'
    AND tablename='audit_events'
    AND policyname='acpos_audit_events_iam_search_insert';
  IF p<>1 THEN RAISE EXCEPTION 'IAMAUDIT0052_POLICY_COUNT_MISMATCH:%',p; END IF;

  SELECT count(*) INTO g
  FROM information_schema.role_table_grants
  WHERE grantee='acpos_app_runtime'
    AND table_schema='public'
    AND table_name='audit_events'
    AND privilege_type='INSERT';
  IF g<>1 THEN RAISE EXCEPTION 'IAMAUDIT0052_INSERT_GRANT_MISMATCH:%',g; END IF;
END $$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES('0052_iam_search_audit_rls_closure','576e039f06550edd7374471ce01ad7384478393b19e5cf9530e85c07de95c305','migration-runner','CR-RUNTIME-0052')
ON CONFLICT(migration_id) DO NOTHING;
