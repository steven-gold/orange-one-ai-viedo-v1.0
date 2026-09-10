-- ACPOS migration 0048: WorkPackage DAG edge RLS/runtime closure.
-- Completes the compiler graph foundation omitted by 0046.
-- Additive security/runtime wiring only; creates no business rows.

ALTER TABLE public.dag_edges ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_dag_edges_actor_select ON public.dag_edges;
CREATE POLICY acpos_dag_edges_actor_select ON public.dag_edges
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1
    FROM public.dag_snapshots ds
    JOIN public.work_packages wp ON wp.work_package_id=ds.work_package_id
    WHERE ds.dag_snapshot_id=dag_edges.dag_snapshot_id
      AND wp.project_id IS NOT NULL
      AND acpos_runtime.can_access_project(wp.project_id)
  )
);

DROP POLICY IF EXISTS acpos_dag_edges_orchestrator_insert ON public.dag_edges;
CREATE POLICY acpos_dag_edges_orchestrator_insert ON public.dag_edges
FOR INSERT TO acpos_app_runtime
WITH CHECK (acpos_runtime.has_service_capability('dag.materialize_locked_blueprint'));

GRANT SELECT,INSERT ON public.dag_edges TO acpos_app_runtime;

DO $$
DECLARE
  rls_enabled boolean;
  policy_count integer;
  service_capability_count integer;
BEGIN
  SELECT c.relrowsecurity INTO rls_enabled
  FROM pg_class c
  JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relname='dag_edges';

  IF rls_enabled IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'COMPILER0048_DAG_EDGES_RLS_NOT_ENABLED';
  END IF;

  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public'
    AND tablename='dag_edges'
    AND policyname IN(
      'acpos_dag_edges_actor_select',
      'acpos_dag_edges_orchestrator_insert'
    );
  IF policy_count<>2 THEN
    RAISE EXCEPTION 'COMPILER0048_DAG_EDGES_POLICY_COUNT_MISMATCH:%',policy_count;
  END IF;

  SELECT count(*) INTO service_capability_count
  FROM public.service_identity_capability_assignments a
  JOIN public.service_identities s ON s.service_identity_id=a.service_identity_id
  WHERE a.status='APPROVED'
    AND s.service_identity_key='task_orchestrator'
    AND a.capability_key='dag.materialize_locked_blueprint';
  IF service_capability_count<>1 THEN
    RAISE EXCEPTION 'COMPILER0048_TASK_ORCHESTRATOR_CAPABILITY_MISMATCH:%',service_capability_count;
  END IF;

  IF NOT has_table_privilege('acpos_app_runtime','public.dag_edges','SELECT') THEN
    RAISE EXCEPTION 'COMPILER0048_DAG_EDGES_SELECT_GRANT_MISSING';
  END IF;
  IF NOT has_table_privilege('acpos_app_runtime','public.dag_edges','INSERT') THEN
    RAISE EXCEPTION 'COMPILER0048_DAG_EDGES_INSERT_GRANT_MISSING';
  END IF;
END
$$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0048_dag_edge_rls_runtime_closure',
  '5e218c9a78826c0e56719ef7865957b75e4508a021cac9f858edebc7bd2a2f60',
  'migration-runner',
  'CR-RUNTIME-0048'
)
ON CONFLICT(migration_id) DO NOTHING;
