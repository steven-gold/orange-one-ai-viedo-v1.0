-- ACPOS migration 0027: QA-01 review lifecycle permission + RLS closure.
-- Change ref: CR-QA-0027 (PENDING PRODUCTION APPLY).
-- Reuses existing QA tables and five registered API permission resources.
-- Does not create QA tasks, task outputs, criteria, scorecards, findings, correction requests or release packages.
-- Does not execute AI/provider scoring.

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
    RAISE EXCEPTION 'QA0027_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*) INTO resource_count
  FROM public.permission_resources r
  WHERE r.resource_key IN (
    'api:startQaReview',
    'api:startRecheck',
    'api:decidePass',
    'api:decideFail',
    'api:createReleasePackage'
  )
    AND r.resource_type='API'
    AND r.active=true
    AND 'EXECUTE'=ANY(
      SELECT jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
      )
    );

  IF resource_count <> 5 THEN
    RAISE EXCEPTION 'QA0027_PERMISSION_RESOURCE_COUNT_MISMATCH:%', resource_count;
  END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,
    granted_by_user_id,approval_ref,version_no,effective_from,effective_to,approval_required
  )
  SELECT
    bootstrap_user_id,
    r.resource_id,
    'EXECUTE',
    'ALLOW',
    '{}'::jsonb,
    '{}'::jsonb,
    jsonb_build_object(
      'page_uid','QA-01',
      'runtime_scope','QA_LIFECYCLE_ONLY_NO_PROVIDER_SCORE',
      'operation_resource',r.resource_key,
      'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'
    ),
    'APPROVED',
    bootstrap_user_id,
    'CR-QA-0027-PENDING-PRODUCTION-APPLY',
    1,
    now(),
    NULL,
    false
  FROM public.permission_resources r
  WHERE r.resource_key IN (
    'api:startQaReview',
    'api:startRecheck',
    'api:decidePass',
    'api:decideFail',
    'api:createReleasePackage'
  )
    AND r.resource_type='API'
    AND r.active=true
  ON CONFLICT (user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id
    AND r.resource_key IN (
      'api:startQaReview',
      'api:startRecheck',
      'api:decidePass',
      'api:decideFail',
      'api:createReleasePackage'
    )
    AND a.action='EXECUTE'
    AND a.effect='ALLOW'
    AND a.status='APPROVED'
    AND a.scope='{}'::jsonb
    AND a.condition='{}'::jsonb
    AND a.effective_from<=now()
    AND (a.effective_to IS NULL OR a.effective_to>now());

  IF approved_allow_count <> 5 THEN
    RAISE EXCEPTION 'QA0027_APPROVED_ALLOW_COUNT_MISMATCH:%', approved_allow_count;
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.can_execute_qa_operation(resource_key_input text)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT CASE
    WHEN EXISTS (
      SELECT 1
      FROM public.account_permission_assignments a
      JOIN public.permission_resources r ON r.resource_id=a.resource_id
      WHERE a.user_id=acpos_runtime.current_actor_user_id()
        AND r.resource_key=resource_key_input
        AND r.active=true
        AND a.action='EXECUTE'
        AND a.effect='DENY'
        AND a.status='APPROVED'
        AND a.effective_from<=now()
        AND (a.effective_to IS NULL OR a.effective_to>now())
    ) THEN false
    ELSE EXISTS (
      SELECT 1
      FROM public.account_permission_assignments a
      JOIN public.permission_resources r ON r.resource_id=a.resource_id
      WHERE a.user_id=acpos_runtime.current_actor_user_id()
        AND r.resource_key=resource_key_input
        AND r.active=true
        AND a.action='EXECUTE'
        AND a.effect='ALLOW'
        AND a.status='APPROVED'
        AND a.effective_from<=now()
        AND (a.effective_to IS NULL OR a.effective_to>now())
    )
  END
$$;

REVOKE ALL ON FUNCTION acpos_runtime.can_execute_qa_operation(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acpos_runtime.can_execute_qa_operation(text) TO acpos_app_runtime;

GRANT SELECT ON public.quality_criteria_versions TO acpos_app_runtime;
ALTER TABLE public.quality_criteria_versions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_quality_criteria_versions_qa_select ON public.quality_criteria_versions;
CREATE POLICY acpos_quality_criteria_versions_qa_select ON public.quality_criteria_versions
FOR SELECT TO acpos_app_runtime
USING (
  status='APPROVED'
  AND (
    acpos_runtime.current_actor_is_bootstrap_admin()
    OR acpos_runtime.can_execute_qa_operation('api:startQaReview')
  )
);

GRANT SELECT, INSERT, UPDATE(status,decision_reason,decided_at)
ON public.qa_review_runs TO acpos_app_runtime;
ALTER TABLE public.qa_review_runs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_qa_review_runs_select ON public.qa_review_runs;
DROP POLICY IF EXISTS acpos_qa_review_runs_insert ON public.qa_review_runs;
DROP POLICY IF EXISTS acpos_qa_review_runs_update ON public.qa_review_runs;

CREATE POLICY acpos_qa_review_runs_select ON public.qa_review_runs
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR acpos_runtime.can_access_project(COALESCE(project_id,acpos_runtime.project_id_for_output(output_version_id)))
);

CREATE POLICY acpos_qa_review_runs_insert ON public.qa_review_runs
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  (
    acpos_runtime.current_actor_is_bootstrap_admin()
    OR acpos_runtime.can_execute_qa_operation('api:startQaReview')
  )
  AND acpos_runtime.can_manage_project(COALESCE(project_id,acpos_runtime.project_id_for_output(output_version_id)))
);

CREATE POLICY acpos_qa_review_runs_update ON public.qa_review_runs
FOR UPDATE TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR acpos_runtime.can_manage_project(COALESCE(project_id,acpos_runtime.project_id_for_output(output_version_id)))
)
WITH CHECK (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR acpos_runtime.can_manage_project(COALESCE(project_id,acpos_runtime.project_id_for_output(output_version_id)))
);

DO $$
DECLARE
  policy_count bigint;
BEGIN
  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public'
    AND (
      (tablename='quality_criteria_versions' AND policyname='acpos_quality_criteria_versions_qa_select')
      OR
      (tablename='qa_review_runs' AND policyname IN (
        'acpos_qa_review_runs_select',
        'acpos_qa_review_runs_insert',
        'acpos_qa_review_runs_update'
      ))
    );

  IF policy_count <> 4 THEN
    RAISE EXCEPTION 'QA0027_RLS_POLICY_COUNT_MISMATCH:%', policy_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES(
  '0027_qa_review_lifecycle_permission_rls_closure',
  'b12ec83f4ad0794c215f6b5f0624fdbe98e08d86361d1c47262fcea00aa0255f',
  'migration-runner',
  'CR-QA-0027-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
