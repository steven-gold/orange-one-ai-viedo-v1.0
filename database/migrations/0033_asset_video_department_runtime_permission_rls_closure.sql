-- ACPOS migration 0033: ASSET/VIDEO Production runtime permission + RLS closure.
-- Reuses 35 existing effectful resources. No new permission resource is created.
-- No Production task/provider/output data is seeded by this migration.

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
  IF bootstrap_user_id IS NULL THEN RAISE EXCEPTION 'DEPT0033_BOOTSTRAP_ADMIN_NOT_READY'; END IF;

  SELECT count(*) INTO resource_count
  FROM public.permission_resources r
  WHERE r.resource_key IN ('action:workspace:ASSET-01:ACT-TASK-EXECUTE',
      'action:workspace:ASSET-01:ACT-TASK-RETRY',
      'action:workspace:ASSET-01:ACT-OUTPUT-SELECT',
      'action:workspace:ASSET-01:ACT-SCORECARD-SUBMIT',
      'action:workspace:ASSET-01:ACT-FINDING-CREATE',
      'action:workspace:ASSET-01:ACT-CORRECTION-REQUEST',
      'action:workspace:ASSET-01:ACT-HANDOFF-CREATE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-01-ACT-TASK-EXECUTE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-02-ACT-TASK-RETRY',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-03-ACT-OUTPUT-SELECT',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-04-ACT-SCORECARD-SUBMIT',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-05-ACT-FINDING-CREATE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-06-ACT-CORRECTION-REQUEST',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-07-ACT-HANDOFF-CREATE',
      'action:workspace:VIDEO-01:ACT-TASK-EXECUTE',
      'action:workspace:VIDEO-01:ACT-TASK-RETRY',
      'action:workspace:VIDEO-01:ACT-OUTPUT-SELECT',
      'action:workspace:VIDEO-01:ACT-SCORECARD-SUBMIT',
      'action:workspace:VIDEO-01:ACT-FINDING-CREATE',
      'action:workspace:VIDEO-01:ACT-CORRECTION-REQUEST',
      'action:workspace:VIDEO-01:ACT-HANDOFF-CREATE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-01-ACT-TASK-EXECUTE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-02-ACT-TASK-RETRY',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-03-ACT-OUTPUT-SELECT',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-04-ACT-SCORECARD-SUBMIT',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-05-ACT-FINDING-CREATE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-06-ACT-CORRECTION-REQUEST',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-07-ACT-HANDOFF-CREATE',
      'api:requestTaskExecution',
      'api:retryTaskExecution',
      'api:decideOutputCandidate',
      'api:submitScorecard',
      'api:createFinding',
      'api:createCorrectionRequest',
      'api:createDepartmentHandoff')
    AND r.active=true
    AND (
      (r.resource_type IN ('ACTION','CONTROL') AND 'INVOKE'=ANY(SELECT jsonb_array_elements_text(CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END)))
      OR
      (r.resource_type='API' AND 'EXECUTE'=ANY(SELECT jsonb_array_elements_text(CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END)))
    );
  IF resource_count<>35 THEN RAISE EXCEPTION 'DEPT0033_PERMISSION_RESOURCE_COUNT_MISMATCH:%',resource_count; END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,
    granted_by_user_id,approval_ref,version_no,effective_from,effective_to,approval_required
  )
  SELECT bootstrap_user_id,r.resource_id,
    CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END,
    'ALLOW','{}'::jsonb,'{}'::jsonb,
    jsonb_build_object('runtime_scope','ASSET_VIDEO_CORE_DEPARTMENT_RUNTIME','source_resource',r.resource_key,'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'),
    'APPROVED',bootstrap_user_id,'CR-DEPT-0033-PENDING-PRODUCTION-APPLY',1,now(),NULL,false
  FROM public.permission_resources r
  WHERE r.resource_key IN ('action:workspace:ASSET-01:ACT-TASK-EXECUTE',
      'action:workspace:ASSET-01:ACT-TASK-RETRY',
      'action:workspace:ASSET-01:ACT-OUTPUT-SELECT',
      'action:workspace:ASSET-01:ACT-SCORECARD-SUBMIT',
      'action:workspace:ASSET-01:ACT-FINDING-CREATE',
      'action:workspace:ASSET-01:ACT-CORRECTION-REQUEST',
      'action:workspace:ASSET-01:ACT-HANDOFF-CREATE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-01-ACT-TASK-EXECUTE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-02-ACT-TASK-RETRY',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-03-ACT-OUTPUT-SELECT',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-04-ACT-SCORECARD-SUBMIT',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-05-ACT-FINDING-CREATE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-06-ACT-CORRECTION-REQUEST',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-07-ACT-HANDOFF-CREATE',
      'action:workspace:VIDEO-01:ACT-TASK-EXECUTE',
      'action:workspace:VIDEO-01:ACT-TASK-RETRY',
      'action:workspace:VIDEO-01:ACT-OUTPUT-SELECT',
      'action:workspace:VIDEO-01:ACT-SCORECARD-SUBMIT',
      'action:workspace:VIDEO-01:ACT-FINDING-CREATE',
      'action:workspace:VIDEO-01:ACT-CORRECTION-REQUEST',
      'action:workspace:VIDEO-01:ACT-HANDOFF-CREATE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-01-ACT-TASK-EXECUTE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-02-ACT-TASK-RETRY',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-03-ACT-OUTPUT-SELECT',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-04-ACT-SCORECARD-SUBMIT',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-05-ACT-FINDING-CREATE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-06-ACT-CORRECTION-REQUEST',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-07-ACT-HANDOFF-CREATE',
      'api:requestTaskExecution',
      'api:retryTaskExecution',
      'api:decideOutputCandidate',
      'api:submitScorecard',
      'api:createFinding',
      'api:createCorrectionRequest',
      'api:createDepartmentHandoff') AND r.active=true
  ON CONFLICT(user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id
    AND r.resource_key IN ('action:workspace:ASSET-01:ACT-TASK-EXECUTE',
      'action:workspace:ASSET-01:ACT-TASK-RETRY',
      'action:workspace:ASSET-01:ACT-OUTPUT-SELECT',
      'action:workspace:ASSET-01:ACT-SCORECARD-SUBMIT',
      'action:workspace:ASSET-01:ACT-FINDING-CREATE',
      'action:workspace:ASSET-01:ACT-CORRECTION-REQUEST',
      'action:workspace:ASSET-01:ACT-HANDOFF-CREATE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-01-ACT-TASK-EXECUTE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-02-ACT-TASK-RETRY',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-03-ACT-OUTPUT-SELECT',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-04-ACT-SCORECARD-SUBMIT',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-05-ACT-FINDING-CREATE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-06-ACT-CORRECTION-REQUEST',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-07-ACT-HANDOFF-CREATE',
      'action:workspace:VIDEO-01:ACT-TASK-EXECUTE',
      'action:workspace:VIDEO-01:ACT-TASK-RETRY',
      'action:workspace:VIDEO-01:ACT-OUTPUT-SELECT',
      'action:workspace:VIDEO-01:ACT-SCORECARD-SUBMIT',
      'action:workspace:VIDEO-01:ACT-FINDING-CREATE',
      'action:workspace:VIDEO-01:ACT-CORRECTION-REQUEST',
      'action:workspace:VIDEO-01:ACT-HANDOFF-CREATE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-01-ACT-TASK-EXECUTE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-02-ACT-TASK-RETRY',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-03-ACT-OUTPUT-SELECT',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-04-ACT-SCORECARD-SUBMIT',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-05-ACT-FINDING-CREATE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-06-ACT-CORRECTION-REQUEST',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-07-ACT-HANDOFF-CREATE',
      'api:requestTaskExecution',
      'api:retryTaskExecution',
      'api:decideOutputCandidate',
      'api:submitScorecard',
      'api:createFinding',
      'api:createCorrectionRequest',
      'api:createDepartmentHandoff')
    AND a.action=CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END
    AND a.effect='ALLOW' AND a.status='APPROVED'
    AND a.scope='{}'::jsonb AND a.condition='{}'::jsonb
    AND a.effective_from<=now() AND (a.effective_to IS NULL OR a.effective_to>now());
  IF approved_allow_count<>35 THEN RAISE EXCEPTION 'DEPT0033_APPROVED_ALLOW_COUNT_MISMATCH:%',approved_allow_count; END IF;
END
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.project_id_for_department_script_view(p_department_script_view_id uuid)
RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public,acpos_runtime
AS $$
  SELECT COALESCE(t.project_id,acpos_runtime.project_id_for_task(t.task_id))
  FROM public.task_input_manifests m
  JOIN public.department_tasks t ON t.task_id=m.task_id
  WHERE m.department_script_view_id=p_department_script_view_id
  LIMIT 1
$$;
REVOKE ALL ON FUNCTION acpos_runtime.project_id_for_department_script_view(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acpos_runtime.project_id_for_department_script_view(uuid) TO acpos_app_runtime;

GRANT SELECT ON public.task_input_manifests,public.department_script_views,public.instruction_packages,public.route_policies,public.provider_capabilities TO acpos_app_runtime;
GRANT SELECT,INSERT,UPDATE ON public.provider_jobs TO acpos_app_runtime;

ALTER TABLE public.task_input_manifests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.department_script_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.instruction_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.route_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.provider_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.provider_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_task_input_manifests_department_select ON public.task_input_manifests;
CREATE POLICY acpos_task_input_manifests_department_select ON public.task_input_manifests FOR SELECT TO acpos_app_runtime
USING(acpos_runtime.can_access_project(acpos_runtime.project_id_for_task(task_id)));

DROP POLICY IF EXISTS acpos_department_script_views_department_select ON public.department_script_views;
CREATE POLICY acpos_department_script_views_department_select ON public.department_script_views FOR SELECT TO acpos_app_runtime
USING(acpos_runtime.can_access_project(acpos_runtime.project_id_for_department_script_view(department_script_view_id)));

DROP POLICY IF EXISTS acpos_instruction_packages_department_select ON public.instruction_packages;
CREATE POLICY acpos_instruction_packages_department_select ON public.instruction_packages FOR SELECT TO acpos_app_runtime
USING(acpos_runtime.can_access_project(acpos_runtime.project_id_for_task(task_id)));

DROP POLICY IF EXISTS acpos_route_policies_department_select ON public.route_policies;
CREATE POLICY acpos_route_policies_department_select ON public.route_policies FOR SELECT TO acpos_app_runtime USING(status='APPROVED');

DROP POLICY IF EXISTS acpos_provider_capabilities_department_select ON public.provider_capabilities;
CREATE POLICY acpos_provider_capabilities_department_select ON public.provider_capabilities FOR SELECT TO acpos_app_runtime USING(status='APPROVED');

DROP POLICY IF EXISTS acpos_provider_jobs_department_select ON public.provider_jobs;
DROP POLICY IF EXISTS acpos_provider_jobs_department_insert ON public.provider_jobs;
DROP POLICY IF EXISTS acpos_provider_jobs_department_update ON public.provider_jobs;

CREATE POLICY acpos_provider_jobs_department_select ON public.provider_jobs FOR SELECT TO acpos_app_runtime
USING(acpos_runtime.can_access_project(COALESCE(project_id,acpos_runtime.project_id_for_task(task_id))));
CREATE POLICY acpos_provider_jobs_department_insert ON public.provider_jobs FOR INSERT TO acpos_app_runtime
WITH CHECK(acpos_runtime.can_manage_project(COALESCE(project_id,acpos_runtime.project_id_for_task(task_id))));
CREATE POLICY acpos_provider_jobs_department_update ON public.provider_jobs FOR UPDATE TO acpos_app_runtime
USING(acpos_runtime.can_manage_project(COALESCE(project_id,acpos_runtime.project_id_for_task(task_id))))
WITH CHECK(acpos_runtime.can_manage_project(COALESCE(project_id,acpos_runtime.project_id_for_task(task_id))));

DO $$
DECLARE policy_count bigint; assignment_count bigint; grant_count bigint;
BEGIN
  SELECT count(*) INTO policy_count FROM pg_policies
  WHERE schemaname='public'
    AND policyname IN(
      'acpos_task_input_manifests_department_select','acpos_department_script_views_department_select',
      'acpos_instruction_packages_department_select','acpos_route_policies_department_select',
      'acpos_provider_capabilities_department_select','acpos_provider_jobs_department_select',
      'acpos_provider_jobs_department_insert','acpos_provider_jobs_department_update'
    );
  IF policy_count<>8 THEN RAISE EXCEPTION 'DEPT0033_RLS_POLICY_COUNT_MISMATCH:%',policy_count; END IF;

  SELECT count(*) INTO assignment_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.approval_ref='CR-DEPT-0033-PENDING-PRODUCTION-APPLY'
    AND r.resource_key IN ('action:workspace:ASSET-01:ACT-TASK-EXECUTE',
      'action:workspace:ASSET-01:ACT-TASK-RETRY',
      'action:workspace:ASSET-01:ACT-OUTPUT-SELECT',
      'action:workspace:ASSET-01:ACT-SCORECARD-SUBMIT',
      'action:workspace:ASSET-01:ACT-FINDING-CREATE',
      'action:workspace:ASSET-01:ACT-CORRECTION-REQUEST',
      'action:workspace:ASSET-01:ACT-HANDOFF-CREATE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-01-ACT-TASK-EXECUTE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-02-ACT-TASK-RETRY',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-03-ACT-OUTPUT-SELECT',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-04-ACT-SCORECARD-SUBMIT',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-05-ACT-FINDING-CREATE',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-06-ACT-CORRECTION-REQUEST',
      'control:CTRL-WORKSPACE-ASSET-01-ACT-07-ACT-HANDOFF-CREATE',
      'action:workspace:VIDEO-01:ACT-TASK-EXECUTE',
      'action:workspace:VIDEO-01:ACT-TASK-RETRY',
      'action:workspace:VIDEO-01:ACT-OUTPUT-SELECT',
      'action:workspace:VIDEO-01:ACT-SCORECARD-SUBMIT',
      'action:workspace:VIDEO-01:ACT-FINDING-CREATE',
      'action:workspace:VIDEO-01:ACT-CORRECTION-REQUEST',
      'action:workspace:VIDEO-01:ACT-HANDOFF-CREATE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-01-ACT-TASK-EXECUTE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-02-ACT-TASK-RETRY',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-03-ACT-OUTPUT-SELECT',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-04-ACT-SCORECARD-SUBMIT',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-05-ACT-FINDING-CREATE',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-06-ACT-CORRECTION-REQUEST',
      'control:CTRL-WORKSPACE-VIDEO-01-ACT-07-ACT-HANDOFF-CREATE',
      'api:requestTaskExecution',
      'api:retryTaskExecution',
      'api:decideOutputCandidate',
      'api:submitScorecard',
      'api:createFinding',
      'api:createCorrectionRequest',
      'api:createDepartmentHandoff')
    AND a.effect='ALLOW' AND a.status='APPROVED';
  IF assignment_count<>35 THEN RAISE EXCEPTION 'DEPT0033_ASSIGNMENT_COUNT_MISMATCH:%',assignment_count; END IF;

  SELECT count(*) INTO grant_count
  FROM information_schema.role_table_grants
  WHERE grantee='acpos_app_runtime' AND table_schema='public'
    AND (
      (table_name IN('task_input_manifests','department_script_views','instruction_packages','route_policies','provider_capabilities') AND privilege_type='SELECT')
      OR (table_name='provider_jobs' AND privilege_type IN('SELECT','INSERT','UPDATE'))
    );
  IF grant_count<>8 THEN RAISE EXCEPTION 'DEPT0033_RUNTIME_GRANT_COUNT_MISMATCH:%',grant_count; END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES('0033_asset_video_department_runtime_permission_rls_closure','7bb4797ce24c1bba93572b0ec55f5ea6baf7297fc2f0687e95564a556f925c71','migration-runner','CR-DEPT-0033-PENDING-PRODUCTION-APPLY')
ON CONFLICT(migration_id) DO NOTHING;
