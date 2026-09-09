-- ACPOS migration 0023: ERP-01 Snapshot Refresh operation permission closure.
-- Change ref: CR-ERP-0023 (PENDING PRODUCTION APPLY).
-- Reuses existing registered control/API permission resources and the READY bootstrap admin.
-- Adds no connector, snapshot, sync payload, provider credential, role or external ERP authorization.

DO $$
DECLARE
  bootstrap_user_id uuid;
  resource_count bigint;
  approved_allow_count bigint;
BEGIN
  SELECT u.user_id
  INTO bootstrap_user_id
  FROM public.app_users u
  JOIN acpos_runtime.accounts a ON lower(a.email)=lower(u.email::text)
  WHERE a.id='runtime-admin'
    AND a.status='READY'
    AND u.disabled_at IS NULL
  LIMIT 1;

  IF bootstrap_user_id IS NULL THEN
    RAISE EXCEPTION 'ERP01_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*)
  INTO resource_count
  FROM public.permission_resources r
  WHERE (
      (r.resource_key='control:CTRL-ADMIN-ERP-01-ACT-05-ERP-SNAPSHOT-REFRESH'
       AND r.resource_type='CONTROL'
       AND 'INVOKE'=ANY(
         SELECT jsonb_array_elements_text(
           CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
         )
       ))
      OR
      (r.resource_key='api:refreshERPSnapshot'
       AND r.resource_type='API'
       AND 'EXECUTE'=ANY(
         SELECT jsonb_array_elements_text(
           CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
         )
       ))
    )
    AND r.active=true;

  IF resource_count <> 2 THEN
    RAISE EXCEPTION 'ERP01_SNAPSHOT_REFRESH_PERMISSION_RESOURCE_COUNT_MISMATCH:%', resource_count;
  END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,
    resource_id,
    action,
    effect,
    scope,
    condition,
    gate_profile,
    status,
    granted_by_user_id,
    approval_ref,
    version_no,
    effective_from,
    effective_to,
    approval_required
  )
  SELECT
    bootstrap_user_id,
    r.resource_id,
    CASE
      WHEN r.resource_key='control:CTRL-ADMIN-ERP-01-ACT-05-ERP-SNAPSHOT-REFRESH' THEN 'INVOKE'
      ELSE 'EXECUTE'
    END,
    'ALLOW',
    '{}'::jsonb,
    '{}'::jsonb,
    jsonb_build_object(
      'page_uid','admin:ERP-01',
      'operation','refreshERPSnapshot',
      'operation_resource',r.resource_key,
      'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'
    ),
    'APPROVED',
    bootstrap_user_id,
    'CR-ERP-0023-PENDING-PRODUCTION-APPLY',
    1,
    now(),
    NULL,
    false
  FROM public.permission_resources r
  WHERE r.resource_key IN (
      'control:CTRL-ADMIN-ERP-01-ACT-05-ERP-SNAPSHOT-REFRESH',
      'api:refreshERPSnapshot'
    )
    AND r.active=true
  ON CONFLICT (user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*)
  INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id
    AND (
      (r.resource_key='control:CTRL-ADMIN-ERP-01-ACT-05-ERP-SNAPSHOT-REFRESH' AND a.action='INVOKE')
      OR
      (r.resource_key='api:refreshERPSnapshot' AND a.action='EXECUTE')
    )
    AND a.effect='ALLOW'
    AND a.status='APPROVED'
    AND a.scope='{}'::jsonb
    AND a.condition='{}'::jsonb
    AND a.effective_from<=now()
    AND (a.effective_to IS NULL OR a.effective_to>now());

  IF approved_allow_count <> 2 THEN
    RAISE EXCEPTION 'ERP01_SNAPSHOT_REFRESH_APPROVED_ALLOW_COUNT_MISMATCH:%', approved_allow_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES(
  '0023_erp_snapshot_refresh_permission_closure',
  'd18b51cb45f1c0ed3519ba3b1d2c7ac2ed11bc270e2bf59e21c98d41694f0cfa',
  'migration-runner',
  'CR-ERP-0023-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
