-- ACPOS migration 0018: department runtime RLS closure.
-- Scope: project-isolated access for department tasks, outputs, findings, corrections, scorecards, handoffs, and release packages.
-- Reuses 0016 session-bound actor authority; does not grant any account permission or provider/queue capability.

CREATE OR REPLACE FUNCTION acpos_runtime.project_id_for_task(p_task_id uuid)
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT d.project_id
  FROM public.department_tasks d
  WHERE d.task_id = p_task_id
  LIMIT 1
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.project_id_for_output(p_output_version_id uuid)
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT COALESCE(o.project_id, d.project_id)
  FROM public.task_outputs o
  LEFT JOIN public.department_tasks d ON d.task_id = o.task_id
  WHERE o.output_version_id = p_output_version_id
  LIMIT 1
$$;

REVOKE ALL ON FUNCTION acpos_runtime.project_id_for_task(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION acpos_runtime.project_id_for_output(uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION
  acpos_runtime.project_id_for_task(uuid),
  acpos_runtime.project_id_for_output(uuid)
TO acpos_app_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON
  public.department_tasks,
  public.task_outputs,
  public.findings,
  public.correction_requests,
  public.scorecards,
  public.handoffs,
  public.release_packages
TO acpos_app_runtime;

ALTER TABLE public.department_tasks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_department_tasks_select ON public.department_tasks;
DROP POLICY IF EXISTS acpos_department_tasks_write ON public.department_tasks;
CREATE POLICY acpos_department_tasks_select ON public.department_tasks
FOR SELECT TO acpos_app_runtime
USING (
  project_id IS NOT NULL
  AND acpos_runtime.can_access_project(project_id)
);
CREATE POLICY acpos_department_tasks_write ON public.department_tasks
FOR ALL TO acpos_app_runtime
USING (
  project_id IS NOT NULL
  AND acpos_runtime.can_manage_project(project_id)
)
WITH CHECK (
  project_id IS NOT NULL
  AND acpos_runtime.can_manage_project(project_id)
);

ALTER TABLE public.task_outputs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_task_outputs_select ON public.task_outputs;
DROP POLICY IF EXISTS acpos_task_outputs_write ON public.task_outputs;
CREATE POLICY acpos_task_outputs_select ON public.task_outputs
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.can_access_project(
    COALESCE(project_id, acpos_runtime.project_id_for_task(task_id))
  )
);
CREATE POLICY acpos_task_outputs_write ON public.task_outputs
FOR ALL TO acpos_app_runtime
USING (
  acpos_runtime.can_manage_project(
    COALESCE(project_id, acpos_runtime.project_id_for_task(task_id))
  )
)
WITH CHECK (
  acpos_runtime.can_manage_project(
    COALESCE(project_id, acpos_runtime.project_id_for_task(task_id))
  )
);

ALTER TABLE public.findings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_findings_select ON public.findings;
DROP POLICY IF EXISTS acpos_findings_write ON public.findings;
CREATE POLICY acpos_findings_select ON public.findings
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.can_access_project(
    acpos_runtime.project_id_for_output(output_version_id)
  )
);
CREATE POLICY acpos_findings_write ON public.findings
FOR ALL TO acpos_app_runtime
USING (
  acpos_runtime.can_manage_project(
    acpos_runtime.project_id_for_output(output_version_id)
  )
)
WITH CHECK (
  acpos_runtime.can_manage_project(
    acpos_runtime.project_id_for_output(output_version_id)
  )
);

ALTER TABLE public.correction_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_correction_requests_select ON public.correction_requests;
DROP POLICY IF EXISTS acpos_correction_requests_write ON public.correction_requests;
CREATE POLICY acpos_correction_requests_select ON public.correction_requests
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.can_access_project(
    acpos_runtime.project_id_for_output(source_output_version_id)
  )
);
CREATE POLICY acpos_correction_requests_write ON public.correction_requests
FOR ALL TO acpos_app_runtime
USING (
  acpos_runtime.can_manage_project(
    acpos_runtime.project_id_for_output(source_output_version_id)
  )
)
WITH CHECK (
  acpos_runtime.can_manage_project(
    acpos_runtime.project_id_for_output(source_output_version_id)
  )
);

ALTER TABLE public.scorecards ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_scorecards_select ON public.scorecards;
DROP POLICY IF EXISTS acpos_scorecards_write ON public.scorecards;
CREATE POLICY acpos_scorecards_select ON public.scorecards
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.can_access_project(
    COALESCE(project_id, acpos_runtime.project_id_for_task(task_id))
  )
);
CREATE POLICY acpos_scorecards_write ON public.scorecards
FOR ALL TO acpos_app_runtime
USING (
  acpos_runtime.can_manage_project(
    COALESCE(project_id, acpos_runtime.project_id_for_task(task_id))
  )
)
WITH CHECK (
  acpos_runtime.can_manage_project(
    COALESCE(project_id, acpos_runtime.project_id_for_task(task_id))
  )
);

ALTER TABLE public.handoffs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_handoffs_select ON public.handoffs;
DROP POLICY IF EXISTS acpos_handoffs_write ON public.handoffs;
CREATE POLICY acpos_handoffs_select ON public.handoffs
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.can_access_project(
    COALESCE(
      project_id,
      acpos_runtime.project_id_for_task(source_task_id),
      acpos_runtime.project_id_for_task(target_task_id)
    )
  )
);
CREATE POLICY acpos_handoffs_write ON public.handoffs
FOR ALL TO acpos_app_runtime
USING (
  acpos_runtime.can_manage_project(
    COALESCE(
      project_id,
      acpos_runtime.project_id_for_task(source_task_id),
      acpos_runtime.project_id_for_task(target_task_id)
    )
  )
)
WITH CHECK (
  acpos_runtime.can_manage_project(
    COALESCE(
      project_id,
      acpos_runtime.project_id_for_task(source_task_id),
      acpos_runtime.project_id_for_task(target_task_id)
    )
  )
);

ALTER TABLE public.release_packages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_release_packages_select ON public.release_packages;
DROP POLICY IF EXISTS acpos_release_packages_write ON public.release_packages;
CREATE POLICY acpos_release_packages_select ON public.release_packages
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.can_access_project(
    COALESCE(project_id, acpos_runtime.project_id_for_output(output_version_id))
  )
);
CREATE POLICY acpos_release_packages_write ON public.release_packages
FOR ALL TO acpos_app_runtime
USING (
  acpos_runtime.can_manage_project(
    COALESCE(project_id, acpos_runtime.project_id_for_output(output_version_id))
  )
)
WITH CHECK (
  acpos_runtime.can_manage_project(
    COALESCE(project_id, acpos_runtime.project_id_for_output(output_version_id))
  )
);

DO $$
DECLARE
  protected_count bigint;
  policy_count bigint;
  unresolved_existing bigint;
BEGIN
  SELECT count(*) INTO protected_count
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname IN (
      'department_tasks','task_outputs','findings','correction_requests',
      'scorecards','handoffs','release_packages'
    )
    AND c.relrowsecurity;

  IF protected_count <> 7 THEN
    RAISE EXCEPTION 'DEPARTMENT_RLS_TABLE_COUNT_MISMATCH: %', protected_count;
  END IF;

  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN (
      'department_tasks','task_outputs','findings','correction_requests',
      'scorecards','handoffs','release_packages'
    )
    AND policyname IN (
      'acpos_department_tasks_select','acpos_department_tasks_write',
      'acpos_task_outputs_select','acpos_task_outputs_write',
      'acpos_findings_select','acpos_findings_write',
      'acpos_correction_requests_select','acpos_correction_requests_write',
      'acpos_scorecards_select','acpos_scorecards_write',
      'acpos_handoffs_select','acpos_handoffs_write',
      'acpos_release_packages_select','acpos_release_packages_write'
    );

  IF policy_count <> 14 THEN
    RAISE EXCEPTION 'DEPARTMENT_RLS_POLICY_COUNT_MISMATCH: %', policy_count;
  END IF;

  SELECT count(*) INTO unresolved_existing
  FROM public.department_tasks
  WHERE project_id IS NULL;

  unresolved_existing := unresolved_existing + (
    SELECT count(*)
    FROM public.task_outputs o
    WHERE COALESCE(o.project_id, acpos_runtime.project_id_for_task(o.task_id)) IS NULL
  );

  unresolved_existing := unresolved_existing + (
    SELECT count(*)
    FROM public.scorecards s
    WHERE COALESCE(s.project_id, acpos_runtime.project_id_for_task(s.task_id)) IS NULL
  );

  unresolved_existing := unresolved_existing + (
    SELECT count(*)
    FROM public.findings f
    WHERE acpos_runtime.project_id_for_output(f.output_version_id) IS NULL
  );

  unresolved_existing := unresolved_existing + (
    SELECT count(*)
    FROM public.correction_requests c
    WHERE acpos_runtime.project_id_for_output(c.source_output_version_id) IS NULL
  );

  unresolved_existing := unresolved_existing + (
    SELECT count(*)
    FROM public.handoffs h
    WHERE COALESCE(
      h.project_id,
      acpos_runtime.project_id_for_task(h.source_task_id),
      acpos_runtime.project_id_for_task(h.target_task_id)
    ) IS NULL
  );

  unresolved_existing := unresolved_existing + (
    SELECT count(*)
    FROM public.release_packages r
    WHERE COALESCE(r.project_id, acpos_runtime.project_id_for_output(r.output_version_id)) IS NULL
  );

  IF unresolved_existing <> 0 THEN
    RAISE EXCEPTION 'DEPARTMENT_RLS_EXISTING_PROJECT_RESOLUTION_GAP: %', unresolved_existing;
  END IF;
END;
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0018_department_runtime_rls_closure', 'd898fcc1a2ccd0d3b814e3cd0578b4c0a8a573f84e96a0e68c68b4af1b2212b5', 'migration-runner', 'CR-RLS-0018')
ON CONFLICT (migration_id) DO NOTHING;
