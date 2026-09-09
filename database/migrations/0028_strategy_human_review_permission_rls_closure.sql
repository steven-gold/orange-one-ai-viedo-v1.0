-- ACPOS migration 0028: STR-01 human review/adoption permission + RLS closure.
-- Change ref: CR-STR-0028 (PENDING PRODUCTION APPLY).
-- Reuses strategy_candidates, strategy_decisions and decision_requests.
-- Does not create strategy candidates, AI outputs, governance approvals or owner-module execution.

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
    RAISE EXCEPTION 'STR0028_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*) INTO resource_count
  FROM public.permission_resources r
  WHERE r.resource_key IN (
    'api:submitStrategyReview',
    'api:adoptAsContextCandidate'
  )
    AND r.resource_type='API'
    AND r.active=true
    AND 'EXECUTE'=ANY(
      SELECT jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
      )
    );

  IF resource_count <> 2 THEN
    RAISE EXCEPTION 'STR0028_PERMISSION_RESOURCE_COUNT_MISMATCH:%', resource_count;
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
      'page_uid','workspace:STR-01',
      'runtime_scope','HUMAN_REVIEW_AND_CONTEXT_ADOPTION_ONLY',
      'operation_resource',r.resource_key,
      'owner_execution_performed',false,
      'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'
    ),
    'APPROVED',
    bootstrap_user_id,
    'CR-STR-0028-PENDING-PRODUCTION-APPLY',
    1,
    now(),
    NULL,
    false
  FROM public.permission_resources r
  WHERE r.resource_key IN (
    'api:submitStrategyReview',
    'api:adoptAsContextCandidate'
  )
    AND r.resource_type='API'
    AND r.active=true
  ON CONFLICT (user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id
    AND r.resource_key IN ('api:submitStrategyReview','api:adoptAsContextCandidate')
    AND a.action='EXECUTE'
    AND a.effect='ALLOW'
    AND a.status='APPROVED'
    AND a.scope='{}'::jsonb
    AND a.condition='{}'::jsonb
    AND a.effective_from<=now()
    AND (a.effective_to IS NULL OR a.effective_to>now());

  IF approved_allow_count <> 2 THEN
    RAISE EXCEPTION 'STR0028_APPROVED_ALLOW_COUNT_MISMATCH:%', approved_allow_count;
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.has_strategy_resource_action(
  resource_key_input text,
  action_input text,
  workspace_id_input uuid
)
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
        AND a.action=action_input
        AND a.effect='DENY'
        AND a.status='APPROVED'
        AND a.condition='{}'::jsonb
        AND (a.scope='{}'::jsonb OR a.scope->>'workspace_id'=workspace_id_input::text)
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
        AND a.action=action_input
        AND a.effect='ALLOW'
        AND a.status='APPROVED'
        AND a.condition='{}'::jsonb
        AND (a.scope='{}'::jsonb OR a.scope->>'workspace_id'=workspace_id_input::text)
        AND a.effective_from<=now()
        AND (a.effective_to IS NULL OR a.effective_to>now())
    )
  END
$$;

REVOKE ALL ON FUNCTION acpos_runtime.has_strategy_resource_action(text,text,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acpos_runtime.has_strategy_resource_action(text,text,uuid) TO acpos_app_runtime;

GRANT SELECT, UPDATE(decision_status) ON public.strategy_candidates TO acpos_app_runtime;
ALTER TABLE public.strategy_candidates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_strategy_candidates_select ON public.strategy_candidates;
DROP POLICY IF EXISTS acpos_strategy_candidates_update ON public.strategy_candidates;

CREATE POLICY acpos_strategy_candidates_select ON public.strategy_candidates
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.has_strategy_resource_action('page:workspace:STR-01','VIEW',workspace_id)
);

CREATE POLICY acpos_strategy_candidates_update ON public.strategy_candidates
FOR UPDATE TO acpos_app_runtime
USING (
  acpos_runtime.has_strategy_resource_action('page:workspace:STR-01','VIEW',workspace_id)
  AND (
    acpos_runtime.has_strategy_resource_action('api:submitStrategyReview','EXECUTE',workspace_id)
    OR acpos_runtime.has_strategy_resource_action('api:adoptAsContextCandidate','EXECUTE',workspace_id)
  )
)
WITH CHECK (
  acpos_runtime.has_strategy_resource_action('page:workspace:STR-01','VIEW',workspace_id)
  AND (
    acpos_runtime.has_strategy_resource_action('api:submitStrategyReview','EXECUTE',workspace_id)
    OR acpos_runtime.has_strategy_resource_action('api:adoptAsContextCandidate','EXECUTE',workspace_id)
  )
);

GRANT SELECT, INSERT ON public.strategy_decisions TO acpos_app_runtime;
ALTER TABLE public.strategy_decisions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_strategy_decisions_select ON public.strategy_decisions;
DROP POLICY IF EXISTS acpos_strategy_decisions_insert ON public.strategy_decisions;

CREATE POLICY acpos_strategy_decisions_select ON public.strategy_decisions
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS (
    SELECT 1
    FROM public.strategy_candidates s
    WHERE s.strategy_candidate_id=strategy_decisions.strategy_candidate_id
      AND acpos_runtime.has_strategy_resource_action('page:workspace:STR-01','VIEW',s.workspace_id)
  )
);

CREATE POLICY acpos_strategy_decisions_insert ON public.strategy_decisions
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM public.strategy_candidates s
    WHERE s.strategy_candidate_id=strategy_decisions.strategy_candidate_id
      AND acpos_runtime.has_strategy_resource_action('page:workspace:STR-01','VIEW',s.workspace_id)
      AND acpos_runtime.has_strategy_resource_action('api:adoptAsContextCandidate','EXECUTE',s.workspace_id)
  )
);

GRANT SELECT, INSERT ON public.decision_requests TO acpos_app_runtime;
ALTER TABLE public.decision_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_strategy_decision_requests_select ON public.decision_requests;
DROP POLICY IF EXISTS acpos_strategy_decision_requests_insert ON public.decision_requests;

CREATE POLICY acpos_strategy_decision_requests_select ON public.decision_requests
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.has_strategy_resource_action('page:workspace:STR-01','VIEW',workspace_id)
  AND required_resource_id=(
    SELECT r.resource_id FROM public.permission_resources r
    WHERE r.resource_key='api:adoptAsContextCandidate' AND r.active=true
    LIMIT 1
  )
);

CREATE POLICY acpos_strategy_decision_requests_insert ON public.decision_requests
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  acpos_runtime.has_strategy_resource_action('page:workspace:STR-01','VIEW',workspace_id)
  AND acpos_runtime.has_strategy_resource_action('api:submitStrategyReview','EXECUTE',workspace_id)
  AND required_action='EXECUTE'
  AND state='OPEN'
  AND created_by_actor_type='USER'
  AND created_by_user_id=acpos_runtime.current_actor_user_id()
  AND created_by_service_identity_id IS NULL
  AND required_resource_id=(
    SELECT r.resource_id FROM public.permission_resources r
    WHERE r.resource_key='api:adoptAsContextCandidate' AND r.active=true
    LIMIT 1
  )
);

DO $$
DECLARE
  policy_count bigint;
BEGIN
  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public'
    AND (
      (tablename='strategy_candidates' AND policyname IN ('acpos_strategy_candidates_select','acpos_strategy_candidates_update'))
      OR
      (tablename='strategy_decisions' AND policyname IN ('acpos_strategy_decisions_select','acpos_strategy_decisions_insert'))
      OR
      (tablename='decision_requests' AND policyname IN ('acpos_strategy_decision_requests_select','acpos_strategy_decision_requests_insert'))
    );

  IF policy_count <> 6 THEN
    RAISE EXCEPTION 'STR0028_RLS_POLICY_COUNT_MISMATCH:%', policy_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES(
  '0028_strategy_human_review_permission_rls_closure',
  'fbfb62018cdc45e2df51bb8262647a468845a7cdc98439e092453421949f865e',
  'migration-runner',
  'CR-STR-0028-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
