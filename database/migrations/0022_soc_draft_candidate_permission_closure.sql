-- ACPOS migration 0022: SOC-01 Draft / Candidate operation permission closure.
-- Change ref: CR-SOC-0022 (PENDING PRODUCTION APPLY).
-- Reuses existing permission_resources api:saveDraft/api:decideCandidate and the READY bootstrap admin.
-- Adds no new resource, role, page, route, table, provider or external publishing permission.

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
    RAISE EXCEPTION 'SOC01_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*)
  INTO resource_count
  FROM public.permission_resources r
  WHERE r.resource_key IN ('api:saveDraft','api:decideCandidate')
    AND r.resource_type='API'
    AND r.active=true
    AND 'EXECUTE'=ANY(
      SELECT jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
      )
    );

  IF resource_count <> 2 THEN
    RAISE EXCEPTION 'SOC01_DRAFT_CANDIDATE_PERMISSION_RESOURCE_COUNT_MISMATCH:%', resource_count;
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
    'EXECUTE',
    'ALLOW',
    '{}'::jsonb,
    '{}'::jsonb,
    jsonb_build_object(
      'page_uid','admin:SOC-01',
      'operation_resource',r.resource_key,
      'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'
    ),
    'APPROVED',
    bootstrap_user_id,
    'CR-SOC-0022-PENDING-PRODUCTION-APPLY',
    1,
    now(),
    NULL,
    false
  FROM public.permission_resources r
  WHERE r.resource_key IN ('api:saveDraft','api:decideCandidate')
    AND r.resource_type='API'
    AND r.active=true
  ON CONFLICT (user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*)
  INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id
    AND r.resource_key IN ('api:saveDraft','api:decideCandidate')
    AND a.action='EXECUTE'
    AND a.effect='ALLOW'
    AND a.status='APPROVED'
    AND a.scope='{}'::jsonb
    AND a.condition='{}'::jsonb
    AND a.effective_from<=now()
    AND (a.effective_to IS NULL OR a.effective_to>now());

  IF approved_allow_count <> 2 THEN
    RAISE EXCEPTION 'SOC01_DRAFT_CANDIDATE_APPROVED_ALLOW_COUNT_MISMATCH:%', approved_allow_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES(
  '0022_soc_draft_candidate_permission_closure',
  '4592e475b078613928117e40a304c3d039a187e234a3ef257844226cb4b50047',
  'migration-runner',
  'CR-SOC-0022-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
