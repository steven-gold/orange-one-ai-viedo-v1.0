-- ACPOS migration 0024: KB-01 KnowledgeSource state/version + configure permission runtime closure.
-- Change ref: CR-KB-0024 (PENDING PRODUCTION APPLY).
-- Materializes only Current KB-01 Authority requirements for pauseKnowledgeSource/resumeKnowledgeSource.
-- Reuses public.knowledge_sources, public.audit_events, account permission authority and session-bound RLS.
-- Does not create a second knowledge source store, ingestion runtime, provider path or synthetic knowledge data.

DO $$
DECLARE
  invalid_status_count bigint;
BEGIN
  SELECT count(*) INTO invalid_status_count
  FROM public.knowledge_sources
  WHERE status::text NOT IN ('DRAFT','ACTIVE','PAUSED','RETIRED');

  IF invalid_status_count <> 0 THEN
    RAISE EXCEPTION 'KB01_KNOWLEDGE_SOURCE_STATUS_PRECONDITION_FAILED:%', invalid_status_count;
  END IF;
END
$$;

ALTER TABLE public.knowledge_sources
  ALTER COLUMN status DROP DEFAULT;

ALTER TABLE public.knowledge_sources
  ALTER COLUMN status TYPE text USING status::text;

ALTER TABLE public.knowledge_sources
  ALTER COLUMN status SET DEFAULT 'DRAFT';

ALTER TABLE public.knowledge_sources
  ADD COLUMN IF NOT EXISTS source_version integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE public.knowledge_sources
  DROP CONSTRAINT IF EXISTS knowledge_sources_status_check,
  DROP CONSTRAINT IF EXISTS knowledge_sources_source_version_check;

ALTER TABLE public.knowledge_sources
  ADD CONSTRAINT knowledge_sources_status_check
    CHECK (status IN ('DRAFT','ACTIVE','PAUSED','RETIRED')),
  ADD CONSTRAINT knowledge_sources_source_version_check
    CHECK (source_version > 0);

INSERT INTO public.permission_resources(
  resource_id, resource_key, resource_type, parent_resource_key, classification, allowed_actions, active, risk_tier
)
VALUES(
  'aa55cc3a-bab5-5c45-9625-617de64a8fff'::uuid,
  'permission:knowledge.source.configure',
  'SENSITIVE_PERMISSION',
  'section:admin:KB-01:source_table',
  'INTERNAL'::classification_level,
  '["EXECUTE"]'::jsonb,
  true,
  'STANDARD'
)
ON CONFLICT (resource_key) DO NOTHING;

DO $$
DECLARE
  resource_count bigint;
BEGIN
  SELECT count(*) INTO resource_count
  FROM public.permission_resources
  WHERE resource_id='aa55cc3a-bab5-5c45-9625-617de64a8fff'::uuid
    AND resource_key='permission:knowledge.source.configure'
    AND resource_type='SENSITIVE_PERMISSION'
    AND parent_resource_key='section:admin:KB-01:source_table'
    AND classification='INTERNAL'
    AND active=true
    AND 'EXECUTE'=ANY(
      SELECT jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(allowed_actions)='array' THEN allowed_actions ELSE '[]'::jsonb END
      )
    );

  IF resource_count <> 1 THEN
    RAISE EXCEPTION 'KB01_CONFIGURE_PERMISSION_RESOURCE_MISMATCH:%', resource_count;
  END IF;
END
$$;

DO $$
DECLARE
  bootstrap_user_id uuid;
BEGIN
  SELECT u.user_id INTO bootstrap_user_id
  FROM public.app_users u
  JOIN acpos_runtime.accounts a ON lower(a.email)=lower(u.email::text)
  WHERE a.id='runtime-admin' AND a.status='READY' AND u.disabled_at IS NULL
  LIMIT 1;

  IF bootstrap_user_id IS NULL THEN
    RAISE EXCEPTION 'KB01_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,granted_by_user_id,
    approval_ref,version_no,effective_from,effective_to,approval_required
  )
  VALUES(
    bootstrap_user_id,
    'aa55cc3a-bab5-5c45-9625-617de64a8fff'::uuid,
    'EXECUTE','ALLOW','{}'::jsonb,'{}'::jsonb,
    '{"page_uid":"admin:KB-01","permission":"knowledge.source.configure","operations":["pauseKnowledgeSource","resumeKnowledgeSource"],"production_apply":"PENDING_FINAL_RELEASE_SEQUENCE"}'::jsonb,
    'APPROVED',bootstrap_user_id,'CR-KB-0024-PENDING-PRODUCTION-APPLY',1,now(),NULL,false
  )
  ON CONFLICT (user_id,resource_id,action,version_no) DO NOTHING;
END
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.can_configure_knowledge_source()
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
        AND r.resource_key='permission:knowledge.source.configure'
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
        AND r.resource_key='permission:knowledge.source.configure'
        AND r.active=true
        AND a.action='EXECUTE'
        AND a.effect='ALLOW'
        AND a.status='APPROVED'
        AND a.effective_from<=now()
        AND (a.effective_to IS NULL OR a.effective_to>now())
    )
  END
$$;

REVOKE ALL ON FUNCTION acpos_runtime.can_configure_knowledge_source() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acpos_runtime.can_configure_knowledge_source() TO acpos_app_runtime;

GRANT SELECT, UPDATE(status,source_version,updated_at) ON public.knowledge_sources TO acpos_app_runtime;
ALTER TABLE public.knowledge_sources ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_knowledge_sources_configure_select ON public.knowledge_sources;
DROP POLICY IF EXISTS acpos_knowledge_sources_configure_update ON public.knowledge_sources;

CREATE POLICY acpos_knowledge_sources_configure_select ON public.knowledge_sources
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_configure_knowledge_source());

CREATE POLICY acpos_knowledge_sources_configure_update ON public.knowledge_sources
FOR UPDATE TO acpos_app_runtime
USING (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_configure_knowledge_source())
WITH CHECK (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_configure_knowledge_source());

GRANT SELECT, INSERT ON public.audit_events TO acpos_app_runtime;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_audit_events_kb_select ON public.audit_events;
DROP POLICY IF EXISTS acpos_audit_events_kb_insert ON public.audit_events;

CREATE POLICY acpos_audit_events_kb_select ON public.audit_events
FOR SELECT TO acpos_app_runtime
USING (
  entity_type='admin:KB-01'
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_configure_knowledge_source())
);

CREATE POLICY acpos_audit_events_kb_insert ON public.audit_events
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  entity_type='admin:KB-01'
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND action IN ('knowledge.source.paused','knowledge.source.resumed')
  AND (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_configure_knowledge_source())
);

DO $$
DECLARE
  approved_allow_count bigint;
  policy_count bigint;
BEGIN
  SELECT count(*) INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE r.resource_key='permission:knowledge.source.configure'
    AND a.action='EXECUTE' AND a.effect='ALLOW' AND a.status='APPROVED'
    AND a.scope='{}'::jsonb AND a.condition='{}'::jsonb
    AND a.effective_from<=now() AND (a.effective_to IS NULL OR a.effective_to>now());

  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public'
    AND (
      (tablename='knowledge_sources' AND policyname IN ('acpos_knowledge_sources_configure_select','acpos_knowledge_sources_configure_update'))
      OR
      (tablename='audit_events' AND policyname IN ('acpos_audit_events_kb_select','acpos_audit_events_kb_insert'))
    );

  IF approved_allow_count <> 1 THEN
    RAISE EXCEPTION 'KB01_CONFIGURE_APPROVED_ALLOW_COUNT_MISMATCH:%', approved_allow_count;
  END IF;
  IF policy_count <> 4 THEN
    RAISE EXCEPTION 'KB01_RLS_POLICY_COUNT_MISMATCH:%', policy_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES(
  '0024_kb_source_state_permission_rls_closure',
  'de41bfa7773dd495056b49e656fa8fd0fb5c032b5d0f680065aa4f90911c9341',
  'migration-runner',
  'CR-KB-0024-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
