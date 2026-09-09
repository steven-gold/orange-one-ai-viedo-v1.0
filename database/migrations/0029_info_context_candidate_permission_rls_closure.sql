-- ACPOS migration 0029: INFO-01 read/context-candidate permission + RLS closure.
-- Change ref: CR-INFO-0029 (PENDING PRODUCTION APPLY).
-- Reuses fact_packs, context_candidates, audit_events and existing permission resources.
-- Does not create Fact Packs, Context Candidates, Evidence, exports or external research data.

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
    RAISE EXCEPTION 'INFO0029_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*) INTO resource_count
  FROM public.permission_resources r
  WHERE r.resource_key IN (
    'api:refreshProjection',
    'api:searchProjection',
    'api:adoptContextCandidate',
    'api:decideCandidate'
  )
    AND r.resource_type='API'
    AND r.active=true
    AND 'EXECUTE'=ANY(
      SELECT jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
      )
    );

  IF resource_count <> 4 THEN
    RAISE EXCEPTION 'INFO0029_PERMISSION_RESOURCE_COUNT_MISMATCH:%', resource_count;
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
      'page_uid','workspace:INFO-01',
      'operation_resource',r.resource_key,
      'runtime_scope','INTERNAL_OR_LOWER_FACT_CONTEXT_ONLY',
      'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'
    ),
    'APPROVED',
    bootstrap_user_id,
    'CR-INFO-0029-PENDING-PRODUCTION-APPLY',
    CASE WHEN r.resource_key='api:decideCandidate' THEN 2 ELSE 1 END,
    now(),
    NULL,
    false
  FROM public.permission_resources r
  WHERE r.resource_key IN (
    'api:refreshProjection',
    'api:searchProjection',
    'api:adoptContextCandidate',
    'api:decideCandidate'
  )
    AND r.resource_type='API'
    AND r.active=true
  ON CONFLICT (user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id
    AND r.resource_key IN (
      'api:refreshProjection',
      'api:searchProjection',
      'api:adoptContextCandidate',
      'api:decideCandidate'
    )
    AND a.action='EXECUTE'
    AND a.effect='ALLOW'
    AND a.status='APPROVED'
    AND a.scope='{}'::jsonb
    AND a.condition='{}'::jsonb
    AND a.gate_profile->>'page_uid'='workspace:INFO-01'
    AND a.approval_ref='CR-INFO-0029-PENDING-PRODUCTION-APPLY'
    AND a.effective_from<=now()
    AND (a.effective_to IS NULL OR a.effective_to>now());

  IF approved_allow_count <> 4 THEN
    RAISE EXCEPTION 'INFO0029_APPROVED_ALLOW_COUNT_MISMATCH:%', approved_allow_count;
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.has_info_resource_action(
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
        AND (
          r.resource_key='page:workspace:INFO-01'
          OR a.gate_profile->>'page_uid'='workspace:INFO-01'
        )
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
        AND (
          r.resource_key='page:workspace:INFO-01'
          OR a.gate_profile->>'page_uid'='workspace:INFO-01'
        )
        AND a.effective_from<=now()
        AND (a.effective_to IS NULL OR a.effective_to>now())
    )
  END
$$;

REVOKE ALL ON FUNCTION acpos_runtime.has_info_resource_action(text,text,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acpos_runtime.has_info_resource_action(text,text,uuid) TO acpos_app_runtime;

GRANT SELECT ON public.fact_packs TO acpos_app_runtime;
ALTER TABLE public.fact_packs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_info_fact_packs_select ON public.fact_packs;
CREATE POLICY acpos_info_fact_packs_select ON public.fact_packs
FOR SELECT TO acpos_app_runtime
USING (
  classification <= 'INTERNAL'::classification_level
  AND acpos_runtime.has_info_resource_action('page:workspace:INFO-01','VIEW',workspace_id)
);

GRANT SELECT, UPDATE(decision_status,decided_by,decision_reason) ON public.context_candidates TO acpos_app_runtime;
ALTER TABLE public.context_candidates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_info_context_candidates_select ON public.context_candidates;
DROP POLICY IF EXISTS acpos_info_context_candidates_update ON public.context_candidates;

CREATE POLICY acpos_info_context_candidates_select ON public.context_candidates
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS (
    SELECT 1
    FROM public.fact_packs f
    WHERE f.fact_pack_id=context_candidates.fact_pack_id
      AND f.classification <= 'INTERNAL'::classification_level
      AND acpos_runtime.has_info_resource_action('page:workspace:INFO-01','VIEW',f.workspace_id)
  )
);

CREATE POLICY acpos_info_context_candidates_update ON public.context_candidates
FOR UPDATE TO acpos_app_runtime
USING (
  decision_status='CANDIDATE'
  AND EXISTS (
    SELECT 1
    FROM public.fact_packs f
    WHERE f.fact_pack_id=context_candidates.fact_pack_id
      AND f.classification <= 'INTERNAL'::classification_level
      AND acpos_runtime.has_info_resource_action('page:workspace:INFO-01','VIEW',f.workspace_id)
      AND (
        acpos_runtime.has_info_resource_action('api:adoptContextCandidate','EXECUTE',f.workspace_id)
        OR acpos_runtime.has_info_resource_action('api:decideCandidate','EXECUTE',f.workspace_id)
      )
  )
)
WITH CHECK (
  decided_by=acpos_runtime.current_actor_user_id()
  AND EXISTS (
    SELECT 1
    FROM public.fact_packs f
    WHERE f.fact_pack_id=context_candidates.fact_pack_id
      AND f.classification <= 'INTERNAL'::classification_level
      AND acpos_runtime.has_info_resource_action('page:workspace:INFO-01','VIEW',f.workspace_id)
      AND (
        (
          context_candidates.decision_status='APPROVED'
          AND acpos_runtime.has_info_resource_action('api:adoptContextCandidate','EXECUTE',f.workspace_id)
        )
        OR
        (
          context_candidates.decision_status IN ('ACCEPTED','REJECTED')
          AND acpos_runtime.has_info_resource_action('api:decideCandidate','EXECUTE',f.workspace_id)
        )
      )
  )
);

GRANT SELECT, INSERT ON public.audit_events TO acpos_app_runtime;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_audit_events_info_select ON public.audit_events;
DROP POLICY IF EXISTS acpos_audit_events_info_insert ON public.audit_events;

CREATE POLICY acpos_audit_events_info_select ON public.audit_events
FOR SELECT TO acpos_app_runtime
USING (
  entity_type='workspace:INFO-01'
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND workspace_id IS NOT NULL
  AND acpos_runtime.has_info_resource_action('page:workspace:INFO-01','VIEW',workspace_id)
);

CREATE POLICY acpos_audit_events_info_insert ON public.audit_events
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  entity_type='workspace:INFO-01'
  AND actor_type='USER'
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND workspace_id IS NOT NULL
  AND action IN ('context.adoption_requested','candidate.decided')
  AND acpos_runtime.has_info_resource_action('page:workspace:INFO-01','VIEW',workspace_id)
);

DO $$
DECLARE
  policy_count bigint;
BEGIN
  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public'
    AND (
      (tablename='fact_packs' AND policyname='acpos_info_fact_packs_select')
      OR (tablename='context_candidates' AND policyname IN ('acpos_info_context_candidates_select','acpos_info_context_candidates_update'))
      OR (tablename='audit_events' AND policyname IN ('acpos_audit_events_info_select','acpos_audit_events_info_insert'))
    );

  IF policy_count <> 5 THEN
    RAISE EXCEPTION 'INFO0029_RLS_POLICY_COUNT_MISMATCH:%', policy_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0029_info_context_candidate_permission_rls_closure',
  'a1494503e3dde66d9bcfcf9bdc0c18277bd942a5a415d827058df851dc8ba7b2',
  'migration-runner',
  'CR-INFO-0029-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
