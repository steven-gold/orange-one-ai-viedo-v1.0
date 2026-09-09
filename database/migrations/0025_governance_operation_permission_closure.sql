-- ACPOS migration 0025: SG-02 / Strategy governance operation permission closure.
-- Change ref: CR-GOV-0025 (PENDING PRODUCTION APPLY).
-- Reuses existing configure/approve ACTION permission resources and the existing governance runtime owner.
-- Adds no new route, governed resource record, page, provider, role or external side effect.

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
    RAISE EXCEPTION 'GOV0025_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*) INTO resource_count
  FROM public.permission_resources r
  WHERE r.resource_key IN (
      'action:admin:SG-02:ACT-CONFIGURE',
      'action:admin:SG-02:ACT-APPROVE',
      'action:admin:STR-02:ACT-CONFIGURE',
      'action:admin:STR-02:ACT-APPROVE'
    )
    AND r.resource_type='ACTION'
    AND r.active=true
    AND 'INVOKE'=ANY(
      SELECT jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
      )
    );

  IF resource_count <> 4 THEN
    RAISE EXCEPTION 'GOV0025_PERMISSION_RESOURCE_COUNT_MISMATCH:%', resource_count;
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
      'current_page_uid',
      CASE WHEN r.resource_key LIKE 'action:admin:SG-02:%' THEN 'admin:SG-02' ELSE 'admin:STR-01' END,
      'source_page_uid',
      CASE WHEN r.resource_key LIKE 'action:admin:SG-02:%' THEN 'admin:SG-02' ELSE 'admin:STR-02' END,
      'operation',
      CASE WHEN r.resource_key LIKE '%ACT-CONFIGURE' THEN 'configureGovernedResource' ELSE 'approveGovernedResource' END,
      'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'
    ),
    'APPROVED',
    bootstrap_user_id,
    'CR-GOV-0025-PENDING-PRODUCTION-APPLY',
    1,
    now(),
    NULL,
    false
  FROM public.permission_resources r
  WHERE r.resource_key IN (
      'action:admin:SG-02:ACT-CONFIGURE',
      'action:admin:SG-02:ACT-APPROVE',
      'action:admin:STR-02:ACT-CONFIGURE',
      'action:admin:STR-02:ACT-APPROVE'
    )
    AND r.resource_type='ACTION'
    AND r.active=true
  ON CONFLICT (user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id
    AND r.resource_key IN (
      'action:admin:SG-02:ACT-CONFIGURE',
      'action:admin:SG-02:ACT-APPROVE',
      'action:admin:STR-02:ACT-CONFIGURE',
      'action:admin:STR-02:ACT-APPROVE'
    )
    AND a.action='INVOKE'
    AND a.effect='ALLOW'
    AND a.status='APPROVED'
    AND a.scope='{}'::jsonb
    AND a.condition='{}'::jsonb
    AND a.effective_from<=now()
    AND (a.effective_to IS NULL OR a.effective_to>now());

  IF approved_allow_count <> 4 THEN
    RAISE EXCEPTION 'GOV0025_APPROVED_ALLOW_COUNT_MISMATCH:%', approved_allow_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES(
  '0025_governance_operation_permission_closure',
  'c95ea4cb98a21749b962abe4f43b28ee3b2552e3505d85704c9c3903be2e3c23',
  'migration-runner',
  'CR-GOV-0025-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
