-- ACPOS migration 0035: EDIT+VOICE production runtime permission/RLS closure.
-- Reuses migration 0012 runtime owners. No parallel EDIT/VOICE schema is introduced.

INSERT INTO public.permission_resources(resource_key,resource_type,parent_resource_key,allowed_actions,risk_tier)
VALUES ('api:transitionEditingToVoiceStage','API',NULL,'["EXECUTE"]'::jsonb,'STANDARD')
ON CONFLICT(resource_key) DO NOTHING;

DO $$
DECLARE bootstrap_user_id uuid; n bigint;
BEGIN
  SELECT u.user_id INTO bootstrap_user_id
  FROM public.app_users u
  JOIN acpos_runtime.accounts ac ON lower(ac.email)=lower(u.email::text)
  WHERE ac.id='runtime-admin' AND ac.status='READY' AND u.disabled_at IS NULL
  LIMIT 1;
  IF bootstrap_user_id IS NULL THEN RAISE EXCEPTION 'EDITVOICE0035_BOOTSTRAP_ADMIN_NOT_READY'; END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,
    granted_by_user_id,approval_ref,version_no,effective_from,effective_to,approval_required
  )
  SELECT bootstrap_user_id,r.resource_id,
         CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END,
         'ALLOW','{}'::jsonb,'{}'::jsonb,
         jsonb_build_object('runtime_scope','EDIT_VOICE_RUNTIME','source_resource',r.resource_key,'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'),
         'APPROVED',bootstrap_user_id,'CR-EDITVOICE-0035-PENDING-PRODUCTION-APPLY',1,now(),NULL,false
  FROM public.permission_resources r
  WHERE r.resource_key IN(
    'api:createEditingRuntimeRun','api:getEditingRuntimeRun','api:completeAssembly','api:transitionEditingToVoiceStage',
    'api:startVoiceRuntime','api:getVoiceRuntimeRun','api:completeAudioMix','api:completeLipSync','api:completeSubtitle','api:handoffVoiceToQA',
    'control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-CREATE-EDITING-RUNTIME-RUN',
    'control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-GET-EDITING-RUNTIME-RUN',
    'control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-COMPLETE-ASSEMBLY',
    'control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-HANDOFF-EDITING-TO-VOICE'
  )
  ON CONFLICT(user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO n
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id AND a.effect='ALLOW' AND a.status='APPROVED'
    AND r.resource_key IN(
      'api:createEditingRuntimeRun','api:getEditingRuntimeRun','api:completeAssembly','api:transitionEditingToVoiceStage',
      'api:startVoiceRuntime','api:getVoiceRuntimeRun','api:completeAudioMix','api:completeLipSync','api:completeSubtitle','api:handoffVoiceToQA',
      'control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-CREATE-EDITING-RUNTIME-RUN',
      'control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-GET-EDITING-RUNTIME-RUN',
      'control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-COMPLETE-ASSEMBLY',
      'control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-HANDOFF-EDITING-TO-VOICE'
    )
    AND a.action=CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END;
  IF n<>14 THEN RAISE EXCEPTION 'EDITVOICE0035_APPROVED_ALLOW_COUNT_MISMATCH:%',n; END IF;
END $$;

CREATE OR REPLACE FUNCTION acpos_runtime.can_execute_edit_voice_operation(resource_key_input text)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path=pg_catalog,public,acpos_runtime
AS $$
  SELECT CASE WHEN EXISTS(
    SELECT 1
    FROM public.account_permission_assignments a
    JOIN public.permission_resources r ON r.resource_id=a.resource_id
    WHERE a.user_id=acpos_runtime.current_actor_user_id()
      AND r.resource_key=resource_key_input AND r.active=true
      AND a.action='EXECUTE' AND a.effect='DENY' AND a.status='APPROVED'
      AND a.effective_from<=now() AND (a.effective_to IS NULL OR a.effective_to>now())
  ) THEN false ELSE EXISTS(
    SELECT 1
    FROM public.account_permission_assignments a
    JOIN public.permission_resources r ON r.resource_id=a.resource_id
    WHERE a.user_id=acpos_runtime.current_actor_user_id()
      AND r.resource_key=resource_key_input AND r.active=true
      AND a.action='EXECUTE' AND a.effect='ALLOW' AND a.status='APPROVED'
      AND a.effective_from<=now() AND (a.effective_to IS NULL OR a.effective_to>now())
  ) END
$$;
REVOKE ALL ON FUNCTION acpos_runtime.can_execute_edit_voice_operation(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acpos_runtime.can_execute_edit_voice_operation(text) TO acpos_app_runtime;

GRANT SELECT,INSERT ON acpos_runtime.editing_runtime_runs_runtime TO acpos_app_runtime;
GRANT UPDATE(current_state,status,current_output_version_id,updated_at) ON acpos_runtime.editing_runtime_runs_runtime TO acpos_app_runtime;
GRANT SELECT,INSERT ON acpos_runtime.editing_runtime_steps_runtime TO acpos_app_runtime;
GRANT SELECT ON acpos_runtime.voice_runtime_profiles_runtime TO acpos_app_runtime;

ALTER TABLE acpos_runtime.editing_runtime_runs_runtime ENABLE ROW LEVEL SECURITY;
ALTER TABLE acpos_runtime.editing_runtime_steps_runtime ENABLE ROW LEVEL SECURITY;
ALTER TABLE acpos_runtime.voice_runtime_profiles_runtime ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_edit_voice_runs_select ON acpos_runtime.editing_runtime_runs_runtime;
DROP POLICY IF EXISTS acpos_edit_voice_runs_insert ON acpos_runtime.editing_runtime_runs_runtime;
DROP POLICY IF EXISTS acpos_edit_voice_runs_update ON acpos_runtime.editing_runtime_runs_runtime;
CREATE POLICY acpos_edit_voice_runs_select ON acpos_runtime.editing_runtime_runs_runtime
FOR SELECT TO acpos_app_runtime
USING(acpos_runtime.can_access_project(acpos_runtime.project_id_for_task(task_id::uuid)));
CREATE POLICY acpos_edit_voice_runs_insert ON acpos_runtime.editing_runtime_runs_runtime
FOR INSERT TO acpos_app_runtime
WITH CHECK(
  acpos_runtime.can_execute_edit_voice_operation('api:createEditingRuntimeRun')
  AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_task(task_id::uuid))
);
CREATE POLICY acpos_edit_voice_runs_update ON acpos_runtime.editing_runtime_runs_runtime
FOR UPDATE TO acpos_app_runtime
USING(acpos_runtime.can_manage_project(acpos_runtime.project_id_for_task(task_id::uuid)))
WITH CHECK(acpos_runtime.can_manage_project(acpos_runtime.project_id_for_task(task_id::uuid)));

DROP POLICY IF EXISTS acpos_edit_voice_steps_select ON acpos_runtime.editing_runtime_steps_runtime;
DROP POLICY IF EXISTS acpos_edit_voice_steps_insert ON acpos_runtime.editing_runtime_steps_runtime;
CREATE POLICY acpos_edit_voice_steps_select ON acpos_runtime.editing_runtime_steps_runtime
FOR SELECT TO acpos_app_runtime
USING(EXISTS(
  SELECT 1 FROM acpos_runtime.editing_runtime_runs_runtime r
  WHERE r.id=editing_runtime_steps_runtime.run_id
    AND acpos_runtime.can_access_project(acpos_runtime.project_id_for_task(r.task_id::uuid))
));
CREATE POLICY acpos_edit_voice_steps_insert ON acpos_runtime.editing_runtime_steps_runtime
FOR INSERT TO acpos_app_runtime
WITH CHECK(EXISTS(
  SELECT 1 FROM acpos_runtime.editing_runtime_runs_runtime r
  WHERE r.id=editing_runtime_steps_runtime.run_id
    AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_task(r.task_id::uuid))
));

DROP POLICY IF EXISTS acpos_edit_voice_profiles_select ON acpos_runtime.voice_runtime_profiles_runtime;
CREATE POLICY acpos_edit_voice_profiles_select ON acpos_runtime.voice_runtime_profiles_runtime
FOR SELECT TO acpos_app_runtime
USING(EXISTS(
  SELECT 1 FROM acpos_runtime.editing_runtime_runs_runtime r
  WHERE r.voice_runtime_profile_id=voice_runtime_profiles_runtime.id
    AND acpos_runtime.can_access_project(acpos_runtime.project_id_for_task(r.task_id::uuid))
));

DO $$
DECLARE p bigint; tg bigint; cg bigint;
BEGIN
  SELECT count(*) INTO p FROM pg_policies
  WHERE schemaname='acpos_runtime' AND policyname IN(
    'acpos_edit_voice_runs_select','acpos_edit_voice_runs_insert','acpos_edit_voice_runs_update',
    'acpos_edit_voice_steps_select','acpos_edit_voice_steps_insert','acpos_edit_voice_profiles_select'
  );
  IF p<>6 THEN RAISE EXCEPTION 'EDITVOICE0035_RLS_POLICY_COUNT_MISMATCH:%',p; END IF;

  SELECT count(*) INTO tg FROM information_schema.role_table_grants
  WHERE grantee='acpos_app_runtime' AND table_schema='acpos_runtime'
    AND ((table_name='editing_runtime_runs_runtime' AND privilege_type IN('SELECT','INSERT'))
      OR (table_name='editing_runtime_steps_runtime' AND privilege_type IN('SELECT','INSERT'))
      OR (table_name='voice_runtime_profiles_runtime' AND privilege_type='SELECT'));
  IF tg<>5 THEN RAISE EXCEPTION 'EDITVOICE0035_TABLE_GRANT_COUNT_MISMATCH:%',tg; END IF;

  SELECT count(*) INTO cg FROM information_schema.role_column_grants
  WHERE grantee='acpos_app_runtime' AND table_schema='acpos_runtime'
    AND table_name='editing_runtime_runs_runtime' AND privilege_type='UPDATE'
    AND column_name IN('current_state','status','current_output_version_id','updated_at');
  IF cg<>4 THEN RAISE EXCEPTION 'EDITVOICE0035_COLUMN_GRANT_COUNT_MISMATCH:%',cg; END IF;
END $$;

INSERT INTO schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES('0035_edit_voice_runtime_permission_rls_closure','119a8945677f009298cb251c4c974a5758156c395e17af9fd4aafc13ee03c916','migration-runner','CR-EDITVOICE-0035-PENDING-PRODUCTION-APPLY')
ON CONFLICT(migration_id) DO NOTHING;
