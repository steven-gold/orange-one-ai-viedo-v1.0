-- ACPOS migration 0030: SOC-01 target posting policy permission + RLS runtime closure.
-- Change ref: CR-SOC-0030 (PENDING PRODUCTION APPLY).
-- Reuses social_market_targets, audit_events, acpos_runtime.idempotency and existing registered permission resources.
-- Adds only the optimistic-concurrency version required by ConfigureSocialTargetPolicyRequest.
-- Does not call an external provider and does not create a publish request.

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
    RAISE EXCEPTION 'SOC0030_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*) INTO resource_count
  FROM public.permission_resources r
  WHERE (
      (r.resource_key='action:admin:SOC-04:ACT-SOCIAL-TARGET-POLICY' AND r.resource_type='ACTION' AND 'INVOKE'=ANY(
        SELECT jsonb_array_elements_text(CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END)
      ))
      OR
      (r.resource_key='control:CTRL-ADMIN-SOC-04-ACT-01-ACT-SOCIAL-TARGET-POLICY' AND r.resource_type='CONTROL' AND 'INVOKE'=ANY(
        SELECT jsonb_array_elements_text(CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END)
      ))
      OR
      (r.resource_key='api:configureSocialTargetPolicy' AND r.resource_type='API' AND 'EXECUTE'=ANY(
        SELECT jsonb_array_elements_text(CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END)
      ))
    )
    AND r.active=true;

  IF resource_count <> 3 THEN
    RAISE EXCEPTION 'SOC0030_PERMISSION_RESOURCE_COUNT_MISMATCH:%', resource_count;
  END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,
    granted_by_user_id,approval_ref,version_no,effective_from,effective_to,approval_required
  )
  SELECT
    bootstrap_user_id,
    r.resource_id,
    CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END,
    'ALLOW',
    '{}'::jsonb,
    '{}'::jsonb,
    jsonb_build_object(
      'page_uid','admin:SOC-01',
      'runtime_scope','SOC_TARGET_POLICY_LOCAL_PERSISTENCE_ONLY',
      'operation_resource',r.resource_key,
      'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'
    ),
    'APPROVED',
    bootstrap_user_id,
    'CR-SOC-0030-PENDING-PRODUCTION-APPLY',
    1,
    now(),
    NULL,
    false
  FROM public.permission_resources r
  WHERE r.resource_key IN (
    'action:admin:SOC-04:ACT-SOCIAL-TARGET-POLICY',
    'control:CTRL-ADMIN-SOC-04-ACT-01-ACT-SOCIAL-TARGET-POLICY',
    'api:configureSocialTargetPolicy'
  )
    AND r.active=true
  ON CONFLICT (user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id
    AND r.resource_key IN (
      'action:admin:SOC-04:ACT-SOCIAL-TARGET-POLICY',
      'control:CTRL-ADMIN-SOC-04-ACT-01-ACT-SOCIAL-TARGET-POLICY',
      'api:configureSocialTargetPolicy'
    )
    AND a.action=CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END
    AND a.effect='ALLOW'
    AND a.status='APPROVED'
    AND a.scope='{}'::jsonb
    AND a.condition='{}'::jsonb
    AND a.effective_from<=now()
    AND (a.effective_to IS NULL OR a.effective_to>now());

  IF approved_allow_count <> 3 THEN
    RAISE EXCEPTION 'SOC0030_APPROVED_ALLOW_COUNT_MISMATCH:%', approved_allow_count;
  END IF;
END
$$;

ALTER TABLE public.social_market_targets
  ADD COLUMN IF NOT EXISTS version bigint NOT NULL DEFAULT 1;

CREATE OR REPLACE FUNCTION acpos_runtime.has_soc_resource_action(
  resource_key_input text,
  action_input text
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
        AND a.effective_from<=now()
        AND (a.effective_to IS NULL OR a.effective_to>now())
    )
  END
$$;

REVOKE ALL ON FUNCTION acpos_runtime.has_soc_resource_action(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acpos_runtime.has_soc_resource_action(text,text) TO acpos_app_runtime;

GRANT SELECT, UPDATE(posting_policy,join_status,version)
ON public.social_market_targets TO acpos_app_runtime;
ALTER TABLE public.social_market_targets ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_social_market_targets_soc_select ON public.social_market_targets;
DROP POLICY IF EXISTS acpos_social_market_targets_soc_policy_update ON public.social_market_targets;

CREATE POLICY acpos_social_market_targets_soc_select ON public.social_market_targets
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR acpos_runtime.has_soc_resource_action('page:admin:SOC-01','VIEW')
);

CREATE POLICY acpos_social_market_targets_soc_policy_update ON public.social_market_targets
FOR UPDATE TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR (
    acpos_runtime.has_soc_resource_action('action:admin:SOC-04:ACT-SOCIAL-TARGET-POLICY','INVOKE')
    AND acpos_runtime.has_soc_resource_action('control:CTRL-ADMIN-SOC-04-ACT-01-ACT-SOCIAL-TARGET-POLICY','INVOKE')
    AND acpos_runtime.has_soc_resource_action('api:configureSocialTargetPolicy','EXECUTE')
  )
)
WITH CHECK (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR (
    acpos_runtime.has_soc_resource_action('action:admin:SOC-04:ACT-SOCIAL-TARGET-POLICY','INVOKE')
    AND acpos_runtime.has_soc_resource_action('control:CTRL-ADMIN-SOC-04-ACT-01-ACT-SOCIAL-TARGET-POLICY','INVOKE')
    AND acpos_runtime.has_soc_resource_action('api:configureSocialTargetPolicy','EXECUTE')
  )
);

GRANT SELECT, INSERT ON acpos_runtime.idempotency TO acpos_app_runtime;
ALTER TABLE acpos_runtime.idempotency ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_idempotency_actor_select ON acpos_runtime.idempotency;
DROP POLICY IF EXISTS acpos_idempotency_actor_insert ON acpos_runtime.idempotency;

CREATE POLICY acpos_idempotency_actor_select ON acpos_runtime.idempotency
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_user_id() IS NOT NULL
  AND idempotency_key LIKE acpos_runtime.current_actor_user_id()::text || ':%'
);

CREATE POLICY acpos_idempotency_actor_insert ON acpos_runtime.idempotency
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  acpos_runtime.current_actor_user_id() IS NOT NULL
  AND idempotency_key LIKE acpos_runtime.current_actor_user_id()::text || ':%'
);

GRANT SELECT, INSERT ON public.audit_events TO acpos_app_runtime;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_audit_events_soc_select ON public.audit_events;
DROP POLICY IF EXISTS acpos_audit_events_soc_insert ON public.audit_events;

CREATE POLICY acpos_audit_events_soc_select ON public.audit_events
FOR SELECT TO acpos_app_runtime
USING (
  entity_type='admin:SOC-01'
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND (
    acpos_runtime.current_actor_is_bootstrap_admin()
    OR acpos_runtime.has_soc_resource_action('page:admin:SOC-01','VIEW')
  )
);

CREATE POLICY acpos_audit_events_soc_insert ON public.audit_events
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  entity_type='admin:SOC-01'
  AND actor_type='USER'
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND (
    acpos_runtime.current_actor_is_bootstrap_admin()
    OR (
      acpos_runtime.has_soc_resource_action('action:admin:SOC-04:ACT-SOCIAL-TARGET-POLICY','INVOKE')
      AND acpos_runtime.has_soc_resource_action('control:CTRL-ADMIN-SOC-04-ACT-01-ACT-SOCIAL-TARGET-POLICY','INVOKE')
      AND acpos_runtime.has_soc_resource_action('api:configureSocialTargetPolicy','EXECUTE')
    )
  )
);

DO $$
DECLARE
  policy_count bigint;
BEGIN
  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE (schemaname='public' AND tablename='social_market_targets' AND policyname IN (
      'acpos_social_market_targets_soc_select',
      'acpos_social_market_targets_soc_policy_update'
    ))
    OR (schemaname='acpos_runtime' AND tablename='idempotency' AND policyname IN (
      'acpos_idempotency_actor_select',
      'acpos_idempotency_actor_insert'
    ))
    OR (schemaname='public' AND tablename='audit_events' AND policyname IN (
      'acpos_audit_events_soc_select',
      'acpos_audit_events_soc_insert'
    ));

  IF policy_count <> 6 THEN
    RAISE EXCEPTION 'SOC0030_RLS_POLICY_COUNT_MISMATCH:%', policy_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES(
  '0030_soc_target_policy_permission_rls_closure',
  'd43ee379e03c27824e61613f89ffdb75823182ef3397bd9c507d70b943aed518',
  'migration-runner',
  'CR-SOC-0030-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
