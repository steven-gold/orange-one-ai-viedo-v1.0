-- ACPOS migration 0046: compiler RLS, idempotency and user-to-service permission foundation.
-- Additive Current closure only. Does not create business rows or resolve VOICE enum.

DO $$
DECLARE
  bootstrap_user_id uuid;
  resource_count integer;
BEGIN
  SELECT u.user_id INTO bootstrap_user_id
  FROM public.app_users u
  JOIN acpos_runtime.accounts a ON lower(a.email)=lower(u.email::text)
  WHERE a.id='runtime-admin' AND a.status='READY' AND u.disabled_at IS NULL
  LIMIT 1;
  IF bootstrap_user_id IS NULL THEN
    RAISE EXCEPTION 'COMPILER0046_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*) INTO resource_count
  FROM public.permission_resources
  WHERE active=true
    AND resource_type='API'
    AND resource_key IN('api:createCanonicalScriptVersion','api:compileWorkPackage')
    AND 'EXECUTE'=ANY(
      SELECT jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(allowed_actions)='array' THEN allowed_actions ELSE '[]'::jsonb END
      )
    );
  IF resource_count<>2 THEN
    RAISE EXCEPTION 'COMPILER0046_API_RESOURCE_COUNT_MISMATCH:%',resource_count;
  END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,granted_by_user_id,
    approval_ref,version_no,effective_from,effective_to,approval_required
  )
  SELECT
    bootstrap_user_id,r.resource_id,'EXECUTE','ALLOW','{}'::jsonb,'{}'::jsonb,
    jsonb_build_object(
      'runtime_owner','CoreModelingService/TaskOrchestrator',
      'production_apply','0046_COMPILER_FOUNDATION'
    ),
    'APPROVED',bootstrap_user_id,'CR-RUNTIME-0046',1,now(),NULL,false
  FROM public.permission_resources r
  WHERE r.active=true
    AND r.resource_key IN('api:createCanonicalScriptVersion','api:compileWorkPackage')
  ON CONFLICT(user_id,resource_id,action,version_no) DO NOTHING;
END
$$;

ALTER TABLE public.canonical_script_versions
  ADD COLUMN IF NOT EXISTS blueprint_version_id uuid NULL REFERENCES public.blueprint_versions(blueprint_version_id),
  ADD COLUMN IF NOT EXISTS request_idempotency_key_hash char(64) NULL,
  ADD COLUMN IF NOT EXISTS request_payload_hash char(64) NULL,
  ADD COLUMN IF NOT EXISTS source_script_ref text NULL,
  ADD COLUMN IF NOT EXISTS change_summary text NULL;

CREATE UNIQUE INDEX IF NOT EXISTS canonical_script_versions_request_idempotency_uq
ON public.canonical_script_versions(request_idempotency_key_hash)
WHERE request_idempotency_key_hash IS NOT NULL;

ALTER TABLE public.work_packages
  ADD COLUMN IF NOT EXISTS compile_idempotency_key_hash char(64) NULL,
  ADD COLUMN IF NOT EXISTS compile_payload_hash char(64) NULL,
  ADD COLUMN IF NOT EXISTS compiler_version text NULL;

CREATE UNIQUE INDEX IF NOT EXISTS work_packages_compile_idempotency_uq
ON public.work_packages(compile_idempotency_key_hash)
WHERE compile_idempotency_key_hash IS NOT NULL;

ALTER TABLE public.work_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dag_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.dag_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_production_goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.output_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.script_projection_rules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_core_canonical_script_insert ON public.canonical_script_versions;
CREATE POLICY acpos_core_canonical_script_insert ON public.canonical_script_versions
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  created_by=acpos_runtime.current_actor_user_id()
  AND acpos_runtime.has_account_resource_action('api:createCanonicalScriptVersion','EXECUTE')
  AND EXISTS(
    SELECT 1
    FROM public.topics t
    WHERE t.topic_id=canonical_script_versions.topic_id
      AND acpos_runtime.can_manage_project(t.project_id)
  )
);

DROP POLICY IF EXISTS acpos_work_packages_actor_select ON public.work_packages;
CREATE POLICY acpos_work_packages_actor_select ON public.work_packages
FOR SELECT TO acpos_app_runtime
USING (
  project_id IS NOT NULL
  AND acpos_runtime.can_access_project(project_id)
);

DROP POLICY IF EXISTS acpos_work_packages_orchestrator_insert ON public.work_packages;
CREATE POLICY acpos_work_packages_orchestrator_insert ON public.work_packages
FOR INSERT TO acpos_app_runtime
WITH CHECK (acpos_runtime.has_service_capability('dag.materialize_locked_blueprint'));

DROP POLICY IF EXISTS acpos_work_packages_orchestrator_update ON public.work_packages;
CREATE POLICY acpos_work_packages_orchestrator_update ON public.work_packages
FOR UPDATE TO acpos_app_runtime
USING (acpos_runtime.has_service_capability('dag.materialize_locked_blueprint'))
WITH CHECK (acpos_runtime.has_service_capability('dag.materialize_locked_blueprint'));

DROP POLICY IF EXISTS acpos_dag_snapshots_actor_select ON public.dag_snapshots;
CREATE POLICY acpos_dag_snapshots_actor_select ON public.dag_snapshots
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1
    FROM public.work_packages wp
    WHERE wp.work_package_id=dag_snapshots.work_package_id
      AND wp.project_id IS NOT NULL
      AND acpos_runtime.can_access_project(wp.project_id)
  )
);

DROP POLICY IF EXISTS acpos_dag_snapshots_orchestrator_insert ON public.dag_snapshots;
CREATE POLICY acpos_dag_snapshots_orchestrator_insert ON public.dag_snapshots
FOR INSERT TO acpos_app_runtime
WITH CHECK (acpos_runtime.has_service_capability('dag.materialize_locked_blueprint'));

DROP POLICY IF EXISTS acpos_dag_nodes_actor_select ON public.dag_nodes;
CREATE POLICY acpos_dag_nodes_actor_select ON public.dag_nodes
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1
    FROM public.dag_snapshots ds
    JOIN public.work_packages wp ON wp.work_package_id=ds.work_package_id
    WHERE ds.dag_snapshot_id=dag_nodes.dag_snapshot_id
      AND wp.project_id IS NOT NULL
      AND acpos_runtime.can_access_project(wp.project_id)
  )
);

DROP POLICY IF EXISTS acpos_dag_nodes_orchestrator_insert ON public.dag_nodes;
CREATE POLICY acpos_dag_nodes_orchestrator_insert ON public.dag_nodes
FOR INSERT TO acpos_app_runtime
WITH CHECK (acpos_runtime.has_service_capability('dag.materialize_locked_blueprint'));

DROP POLICY IF EXISTS acpos_task_templates_orchestrator_select ON public.task_templates;
CREATE POLICY acpos_task_templates_orchestrator_select ON public.task_templates
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.has_service_capability('dag.materialize_locked_blueprint'));

DROP POLICY IF EXISTS acpos_production_goals_orchestrator_select ON public.topic_production_goals;
CREATE POLICY acpos_production_goals_orchestrator_select ON public.topic_production_goals
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.has_service_capability('dag.materialize_locked_blueprint'));

DROP POLICY IF EXISTS acpos_output_contracts_orchestrator_select ON public.output_contracts;
CREATE POLICY acpos_output_contracts_orchestrator_select ON public.output_contracts
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.has_service_capability('dag.materialize_locked_blueprint'));

DROP POLICY IF EXISTS acpos_projection_rules_instruction_compiler_select ON public.script_projection_rules;
CREATE POLICY acpos_projection_rules_instruction_compiler_select ON public.script_projection_rules
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.has_service_capability('service.script_view.compile'));

GRANT INSERT ON public.canonical_script_versions TO acpos_app_runtime;

GRANT SELECT ON
  public.work_packages,
  public.dag_snapshots,
  public.dag_nodes,
  public.task_templates,
  public.topic_production_goals,
  public.output_contracts,
  public.script_projection_rules
TO acpos_app_runtime;

GRANT INSERT,UPDATE ON public.work_packages TO acpos_app_runtime;
GRANT INSERT ON public.dag_snapshots,public.dag_nodes TO acpos_app_runtime;

DO $$
DECLARE
  assignment_count integer;
  rls_count integer;
  service_capability_count integer;
BEGIN
  SELECT count(*) INTO assignment_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  JOIN public.app_users u ON u.user_id=a.user_id
  JOIN acpos_runtime.accounts ra ON lower(ra.email)=lower(u.email::text)
  WHERE ra.id='runtime-admin'
    AND r.resource_key IN('api:createCanonicalScriptVersion','api:compileWorkPackage')
    AND a.action='EXECUTE' AND a.effect='ALLOW' AND a.status='APPROVED';
  IF assignment_count<>2 THEN
    RAISE EXCEPTION 'COMPILER0046_ASSIGNMENT_COUNT_MISMATCH:%',assignment_count;
  END IF;

  SELECT count(*) INTO rls_count
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public'
    AND c.relname IN(
      'work_packages','dag_snapshots','dag_nodes','task_templates',
      'topic_production_goals','output_contracts','script_projection_rules'
    )
    AND c.relrowsecurity;
  IF rls_count<>7 THEN
    RAISE EXCEPTION 'COMPILER0046_RLS_COUNT_MISMATCH:%',rls_count;
  END IF;

  SELECT count(*) INTO service_capability_count
  FROM public.service_identity_capability_assignments a
  JOIN public.service_identities s ON s.service_identity_id=a.service_identity_id
  WHERE a.status='APPROVED'
    AND (
      (s.service_identity_key='task_orchestrator' AND a.capability_key='dag.materialize_locked_blueprint')
      OR
      (s.service_identity_key='instruction_compiler' AND a.capability_key='service.script_view.compile')
    );
  IF service_capability_count<>2 THEN
    RAISE EXCEPTION 'COMPILER0046_SERVICE_CAPABILITY_MISMATCH:%',service_capability_count;
  END IF;
END
$$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0046_compiler_rls_permission_foundation',
  '73f8b38070d62a8c12307674d9e6c0fbefd838c2eaa23da3f1ca7b7d38745c92',
  'migration-runner',
  'CR-RUNTIME-0046'
)
ON CONFLICT(migration_id) DO NOTHING;
