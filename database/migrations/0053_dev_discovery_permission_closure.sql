-- ACPOS migration 0053: DEV Discovery Current action permission closure.
-- Change ref: CR-DEV-0053 (PENDING PRODUCTION APPLY).
-- Grants only the four Current executable DEV-01 Discovery lifecycle ACTION resources to the READY bootstrap admin.
-- ACT-NAV-OPEN and all unbound/retired DEV formal resources remain untouched.
-- No discovery job, company, provider, campaign, message, delivery or other business row is created.

DO $$
DECLARE
  bootstrap_user_id uuid;
  resource_count bigint;
  approved_allow_count bigint;
BEGIN
  SELECT u.user_id INTO bootstrap_user_id
  FROM public.app_users u
  JOIN acpos_runtime.accounts a ON lower(a.email)=lower(u.email::text)
  WHERE a.id='runtime-admin' AND a.status='READY' AND u.disabled_at IS NULL
  LIMIT 1;

  IF bootstrap_user_id IS NULL THEN
    RAISE EXCEPTION 'DEV0053_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*) INTO resource_count
  FROM public.permission_resources r
  WHERE r.resource_key IN (
      'action:admin:DEV-01:ACT-DISCOVERY-START',
      'action:admin:DEV-01:ACT-DISCOVERY-PAUSE',
      'action:admin:DEV-01:ACT-DISCOVERY-RESUME',
      'action:admin:DEV-01:ACT-DISCOVERY-STOP'
    )
    AND r.resource_type='ACTION'
    AND r.active=true
    AND 'INVOKE'=ANY(
      SELECT jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
      )
    );

  IF resource_count <> 4 THEN
    RAISE EXCEPTION 'DEV0053_PERMISSION_RESOURCE_COUNT_MISMATCH:%', resource_count;
  END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,granted_by_user_id,
    approval_ref,version_no,effective_from,effective_to,approval_required
  )
  SELECT
    bootstrap_user_id,
    r.resource_id,
    'INVOKE',
    'ALLOW',
    '{}'::jsonb,
    '{}'::jsonb,
    jsonb_build_object(
      'current_page_uid','admin:DEV-01',
      'source_page_uid','admin:DEV-01',
      'operation',
      CASE r.resource_key
        WHEN 'action:admin:DEV-01:ACT-DISCOVERY-START' THEN 'startCompanyDiscovery'
        WHEN 'action:admin:DEV-01:ACT-DISCOVERY-PAUSE' THEN 'pauseCompanyDiscovery'
        WHEN 'action:admin:DEV-01:ACT-DISCOVERY-RESUME' THEN 'resumeCompanyDiscovery'
        WHEN 'action:admin:DEV-01:ACT-DISCOVERY-STOP' THEN 'stopCompanyDiscovery'
      END,
      'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'
    ),
    'APPROVED',
    bootstrap_user_id,
    'CR-DEV-0053-PENDING-PRODUCTION-APPLY',
    1,
    now(),
    NULL,
    false
  FROM public.permission_resources r
  WHERE r.resource_key IN (
      'action:admin:DEV-01:ACT-DISCOVERY-START',
      'action:admin:DEV-01:ACT-DISCOVERY-PAUSE',
      'action:admin:DEV-01:ACT-DISCOVERY-RESUME',
      'action:admin:DEV-01:ACT-DISCOVERY-STOP'
    )
    AND r.resource_type='ACTION'
    AND r.active=true
  ON CONFLICT (user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id
    AND r.resource_key IN (
      'action:admin:DEV-01:ACT-DISCOVERY-START',
      'action:admin:DEV-01:ACT-DISCOVERY-PAUSE',
      'action:admin:DEV-01:ACT-DISCOVERY-RESUME',
      'action:admin:DEV-01:ACT-DISCOVERY-STOP'
    )
    AND a.action='INVOKE'
    AND a.effect='ALLOW'
    AND a.status='APPROVED'
    AND a.scope='{}'::jsonb
    AND a.condition='{}'::jsonb
    AND a.effective_from<=now()
    AND (a.effective_to IS NULL OR a.effective_to>now());

  IF approved_allow_count <> 4 THEN
    RAISE EXCEPTION 'DEV0053_APPROVED_ALLOW_COUNT_MISMATCH:%', approved_allow_count;
  END IF;
END
$$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0053_dev_discovery_permission_closure',
  'e410c52e8a65e31f86554b591d1e9d2d895127d47e30a9402a3558a6eb3f9149',
  'migration-runner',
  'CR-DEV-0053-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT(migration_id) DO NOTHING;
