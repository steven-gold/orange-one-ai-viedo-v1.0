-- ACPOS migration 0036: KB-01 KnowledgeSource create/update + RLS/audit closure.
-- Extends 0024 without bypassing the session-bound acpos_app_runtime role.
-- Current Authority: SOURCE-CREATE creates DRAFT; SOURCE-SAVE updates the exact version and transitions DRAFT -> ACTIVE.
-- No synthetic knowledge rows, external acquisition data, raw secrets, or provider data are seeded.

ALTER TABLE public.knowledge_sources
  ADD COLUMN IF NOT EXISTS name text,
  ADD COLUMN IF NOT EXISTS source_type text,
  ADD COLUMN IF NOT EXISTS scope jsonb,
  ADD COLUMN IF NOT EXISTS collection_config jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS secret_reference_id uuid NULL REFERENCES public.secret_references(secret_reference_id);

UPDATE public.knowledge_sources
SET name=COALESCE(NULLIF(name,''),source_key),
    source_type=COALESCE(NULLIF(source_type,''),'LEGACY'),
    scope=COALESCE(scope,jsonb_build_object('source_uri',source_uri)),
    collection_config=COALESCE(collection_config,'{}'::jsonb)
WHERE name IS NULL OR name='' OR source_type IS NULL OR source_type='' OR scope IS NULL OR collection_config IS NULL;

ALTER TABLE public.knowledge_sources
  ALTER COLUMN name SET NOT NULL,
  ALTER COLUMN source_type SET NOT NULL,
  ALTER COLUMN scope SET NOT NULL;

DO $$
DECLARE bootstrap_user_id uuid; configure_resource_id uuid;
BEGIN
  SELECT u.user_id INTO bootstrap_user_id
  FROM public.app_users u
  JOIN acpos_runtime.accounts a ON lower(a.email)=lower(u.email::text)
  WHERE a.id='runtime-admin' AND a.status='READY' AND u.disabled_at IS NULL
  LIMIT 1;
  IF bootstrap_user_id IS NULL THEN RAISE EXCEPTION 'KB0036_BOOTSTRAP_ADMIN_NOT_READY'; END IF;

  SELECT resource_id INTO configure_resource_id
  FROM public.permission_resources
  WHERE resource_key='permission:knowledge.source.configure'
    AND active=true
    AND 'EXECUTE'=ANY(SELECT jsonb_array_elements_text(CASE WHEN jsonb_typeof(allowed_actions)='array' THEN allowed_actions ELSE '[]'::jsonb END))
  LIMIT 1;
  IF configure_resource_id IS NULL THEN RAISE EXCEPTION 'KB0036_CONFIGURE_PERMISSION_RESOURCE_MISSING'; END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,granted_by_user_id,
    approval_ref,version_no,effective_from,effective_to,approval_required
  ) VALUES(
    bootstrap_user_id,configure_resource_id,'EXECUTE','ALLOW','{}'::jsonb,'{}'::jsonb,
    '{"page_uid":"admin:KB-01","permission":"knowledge.source.configure","operations":["createKnowledgeSource","updateKnowledgeSource","pauseKnowledgeSource","resumeKnowledgeSource"],"production_apply":"PENDING_FINAL_RELEASE_SEQUENCE"}'::jsonb,
    'APPROVED',bootstrap_user_id,'CR-KB-0036-PENDING-PRODUCTION-APPLY',2,now(),NULL,false
  )
  ON CONFLICT(user_id,resource_id,action,version_no) DO NOTHING;
END
$$;

GRANT SELECT,INSERT ON public.knowledge_sources TO acpos_app_runtime;
GRANT UPDATE(
  source_key,source_uri,name,source_type,scope,collection_method,collection_config,
  rights_policy,classification,freshness_policy,retention_policy,secret_reference_id,
  status,source_version,updated_at
) ON public.knowledge_sources TO acpos_app_runtime;

ALTER TABLE public.knowledge_sources ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_knowledge_sources_configure_insert ON public.knowledge_sources;
CREATE POLICY acpos_knowledge_sources_configure_insert ON public.knowledge_sources
FOR INSERT TO acpos_app_runtime
WITH CHECK(acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_configure_knowledge_source());

GRANT SELECT,INSERT ON public.audit_events TO acpos_app_runtime;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_audit_events_kb_insert ON public.audit_events;
CREATE POLICY acpos_audit_events_kb_insert ON public.audit_events
FOR INSERT TO acpos_app_runtime
WITH CHECK(
  entity_type='admin:KB-01'
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND action IN('knowledge.source.created','knowledge.source.updated','knowledge.source.paused','knowledge.source.resumed')
  AND (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_configure_knowledge_source())
);

DO $$
DECLARE policy_count bigint; assignment_count bigint;
BEGIN
  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public'
    AND (
      (tablename='knowledge_sources' AND policyname IN(
        'acpos_knowledge_sources_configure_select','acpos_knowledge_sources_configure_update','acpos_knowledge_sources_configure_insert'
      ))
      OR (tablename='audit_events' AND policyname IN('acpos_audit_events_kb_select','acpos_audit_events_kb_insert'))
    );
  IF policy_count<>5 THEN RAISE EXCEPTION 'KB0036_RLS_POLICY_COUNT_MISMATCH:%',policy_count; END IF;

  SELECT count(*) INTO assignment_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.approval_ref='CR-KB-0036-PENDING-PRODUCTION-APPLY'
    AND r.resource_key='permission:knowledge.source.configure'
    AND a.action='EXECUTE' AND a.effect='ALLOW' AND a.status='APPROVED'
    AND a.version_no=2;
  IF assignment_count<>1 THEN RAISE EXCEPTION 'KB0036_ASSIGNMENT_COUNT_MISMATCH:%',assignment_count; END IF;

  IF NOT has_table_privilege('acpos_app_runtime','public.knowledge_sources','SELECT,INSERT') THEN
    RAISE EXCEPTION 'KB0036_KNOWLEDGE_SOURCE_TABLE_GRANT_MISSING';
  END IF;
  IF NOT has_column_privilege('acpos_app_runtime','public.knowledge_sources','source_version','UPDATE')
     OR NOT has_column_privilege('acpos_app_runtime','public.knowledge_sources','name','UPDATE')
     OR NOT has_column_privilege('acpos_app_runtime','public.knowledge_sources','scope','UPDATE') THEN
    RAISE EXCEPTION 'KB0036_KNOWLEDGE_SOURCE_COLUMN_GRANT_MISSING';
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES('0036_kb_source_create_update_permission_rls_closure','9cc3b0d0beeb8b0eadc2e2bf8d356799f39696dbd22b2fa967e02b4a6fe7a3fb','migration-runner','CR-KB-0036-PENDING-PRODUCTION-APPLY')
ON CONFLICT(migration_id) DO NOTHING;
