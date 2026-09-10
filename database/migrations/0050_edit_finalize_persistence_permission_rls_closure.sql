-- ACPOS migration 0050: EDIT Finalize canonical persistence, permission and RLS closure.
-- Materializes only Current EDIT-01 Finalize objects already required by the locked page authority/runtime.
-- Reuses public.production_output_version_locks as the single canonical lock owner; no parallel edit lock table is created.
-- No Production business rows are created by this migration.

ALTER TABLE public.editing_timelines
  ADD COLUMN IF NOT EXISTS source_timeline_id uuid NULL,
  ADD COLUMN IF NOT EXISTS source_draft_hash char(64) NULL,
  ADD COLUMN IF NOT EXISTS version_content_hash char(64) NULL,
  ADD COLUMN IF NOT EXISTS source_scorecard_id uuid NULL,
  ADD COLUMN IF NOT EXISTS saved_by uuid NULL,
  ADD COLUMN IF NOT EXISTS saved_at timestamptz NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='editing_timelines_source_timeline_id_fkey'
      AND conrelid='public.editing_timelines'::regclass
  ) THEN
    ALTER TABLE public.editing_timelines
      ADD CONSTRAINT editing_timelines_source_timeline_id_fkey
      FOREIGN KEY(source_timeline_id) REFERENCES public.editing_timelines(editing_timeline_id);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='editing_timelines_source_scorecard_id_fkey'
      AND conrelid='public.editing_timelines'::regclass
  ) THEN
    ALTER TABLE public.editing_timelines
      ADD CONSTRAINT editing_timelines_source_scorecard_id_fkey
      FOREIGN KEY(source_scorecard_id) REFERENCES public.scorecards(scorecard_id);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='editing_timelines_saved_by_fkey'
      AND conrelid='public.editing_timelines'::regclass
  ) THEN
    ALTER TABLE public.editing_timelines
      ADD CONSTRAINT editing_timelines_saved_by_fkey
      FOREIGN KEY(saved_by) REFERENCES public.app_users(user_id);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.edit_render_jobs(
  edit_render_job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id text NOT NULL,
  task_id uuid NOT NULL REFERENCES public.department_tasks(task_id),
  input_edit_version_id uuid NOT NULL REFERENCES public.editing_timelines(editing_timeline_id),
  route_policy_id uuid NOT NULL REFERENCES public.route_policies(route_policy_id),
  idempotency_key char(64) NOT NULL UNIQUE,
  settings jsonb NOT NULL DEFAULT '{}'::jsonb,
  settings_hash char(64) NOT NULL,
  status text NOT NULL DEFAULT 'QUEUED'
    CHECK(status IN('QUEUED','RUNNING','COMPLETED','BLOCKED','CANCELLED')),
  route_decision_id text NULL,
  output_uri text NULL,
  artifact_checksum char(64) NULL,
  manifest jsonb NULL,
  output_version_id uuid NULL REFERENCES public.task_outputs(output_version_id),
  failure_reason text NULL,
  started_at timestamptz NULL,
  completed_at timestamptz NULL,
  cancelled_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.production_output_version_locks
  ADD COLUMN IF NOT EXISTS edit_version_id uuid NULL,
  ADD COLUMN IF NOT EXISTS render_job_id uuid NULL,
  ADD COLUMN IF NOT EXISTS reason text NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='production_output_version_locks_edit_version_id_fkey'
      AND conrelid='public.production_output_version_locks'::regclass
  ) THEN
    ALTER TABLE public.production_output_version_locks
      ADD CONSTRAINT production_output_version_locks_edit_version_id_fkey
      FOREIGN KEY(edit_version_id) REFERENCES public.editing_timelines(editing_timeline_id);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='production_output_version_locks_render_job_id_fkey'
      AND conrelid='public.production_output_version_locks'::regclass
  ) THEN
    ALTER TABLE public.production_output_version_locks
      ADD CONSTRAINT production_output_version_locks_render_job_id_fkey
      FOREIGN KEY(render_job_id) REFERENCES public.edit_render_jobs(edit_render_job_id);
  END IF;
END $$;

ALTER TABLE public.production_output_version_locks
  DROP CONSTRAINT IF EXISTS production_output_version_locks_department_check;
ALTER TABLE public.production_output_version_locks
  ADD CONSTRAINT production_output_version_locks_department_check
  CHECK(department IN('ASSET','VIDEO','EDITING'));

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='production_output_version_locks_edit_lineage_check'
      AND conrelid='public.production_output_version_locks'::regclass
  ) THEN
    ALTER TABLE public.production_output_version_locks
      ADD CONSTRAINT production_output_version_locks_edit_lineage_check
      CHECK(
        department<>'EDITING'
        OR (edit_version_id IS NOT NULL AND render_job_id IS NOT NULL AND reason IS NOT NULL)
      );
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS production_output_version_locks_edit_version_uidx
ON public.production_output_version_locks(edit_version_id)
WHERE edit_version_id IS NOT NULL;

INSERT INTO public.permission_resources(resource_key,resource_type,parent_resource_key,allowed_actions,risk_tier)
VALUES
  ('api:saveEditVersion','API',NULL,'["EXECUTE"]'::jsonb,'HIGH'),
  ('api:startEditRender','API',NULL,'["EXECUTE"]'::jsonb,'HIGH'),
  ('api:cancelEditRender','API',NULL,'["EXECUTE"]'::jsonb,'STANDARD'),
  ('api:saveEditOutputVersion','API',NULL,'["EXECUTE"]'::jsonb,'HIGH'),
  ('api:lockEditVersion','API',NULL,'["EXECUTE"]'::jsonb,'HIGH'),
  ('api:restoreEditVersionAsDraft','API',NULL,'["EXECUTE"]'::jsonb,'STANDARD'),
  ('api:getEditOutputDownload','API',NULL,'["EXECUTE"]'::jsonb,'STANDARD'),
  ('action:workspace:EDIT-01:EDIT-01-ACT-VERSION-SAVE','ACTION','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'HIGH'),
  ('action:workspace:EDIT-01:EDIT-01-ACT-RENDER-START','ACTION','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'HIGH'),
  ('action:workspace:EDIT-01:EDIT-01-ACT-RENDER-CANCEL','ACTION','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'STANDARD'),
  ('action:workspace:EDIT-01:EDIT-01-ACT-OUTPUT-VERSION-SAVE','ACTION','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'HIGH'),
  ('action:workspace:EDIT-01:EDIT-01-ACT-VERSION-LOCK','ACTION','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'HIGH'),
  ('action:workspace:EDIT-01:EDIT-01-ACT-VERSION-RESTORE-AS-DRAFT','ACTION','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'STANDARD'),
  ('action:workspace:EDIT-01:EDIT-01-ACT-OUTPUT-DOWNLOAD','ACTION','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'STANDARD'),
  ('control:workspace:EDIT-01:EDIT-01-BTN-VERSION-SAVE','CONTROL','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'HIGH'),
  ('control:workspace:EDIT-01:EDIT-01-BTN-RENDER-EXECUTE','CONTROL','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'HIGH'),
  ('control:workspace:EDIT-01:EDIT-01-BTN-RENDER-CANCEL','CONTROL','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'STANDARD'),
  ('control:workspace:EDIT-01:EDIT-01-BTN-OUTPUT-SAVE','CONTROL','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'HIGH'),
  ('control:workspace:EDIT-01:EDIT-01-BTN-VERSION-LOCK','CONTROL','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'HIGH'),
  ('control:workspace:EDIT-01:EDIT-01-BTN-VERSION-RESTORE','CONTROL','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'STANDARD'),
  ('control:workspace:EDIT-01:EDIT-01-BTN-DOWNLOAD','CONTROL','section:workspace:EDIT-01:editing_runtime','["INVOKE"]'::jsonb,'STANDARD')
ON CONFLICT(resource_key) DO NOTHING;

DO $$
DECLARE bootstrap_user_id uuid; n bigint;
BEGIN
  SELECT u.user_id INTO bootstrap_user_id
  FROM public.app_users u
  JOIN acpos_runtime.accounts ac ON lower(ac.email)=lower(u.email::text)
  WHERE ac.id='runtime-admin' AND ac.status='READY' AND u.disabled_at IS NULL
  LIMIT 1;
  IF bootstrap_user_id IS NULL THEN RAISE EXCEPTION 'EDITFINAL0050_BOOTSTRAP_ADMIN_NOT_READY'; END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,
    granted_by_user_id,approval_ref,version_no,effective_from,effective_to,approval_required
  )
  SELECT bootstrap_user_id,r.resource_id,
         CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END,
         'ALLOW','{}'::jsonb,'{}'::jsonb,
         jsonb_build_object('runtime_scope','EDIT_FINALIZE_RUNTIME','source_resource',r.resource_key,'production_apply','PENDING_RELEASE_GATE'),
         'APPROVED',bootstrap_user_id,'CR-RUNTIME-0050',1,now(),NULL,false
  FROM public.permission_resources r
  WHERE r.resource_key IN(
    'api:saveEditVersion','api:startEditRender','api:cancelEditRender','api:saveEditOutputVersion',
    'api:lockEditVersion','api:restoreEditVersionAsDraft','api:getEditOutputDownload',
    'action:workspace:EDIT-01:EDIT-01-ACT-VERSION-SAVE',
    'action:workspace:EDIT-01:EDIT-01-ACT-RENDER-START',
    'action:workspace:EDIT-01:EDIT-01-ACT-RENDER-CANCEL',
    'action:workspace:EDIT-01:EDIT-01-ACT-OUTPUT-VERSION-SAVE',
    'action:workspace:EDIT-01:EDIT-01-ACT-VERSION-LOCK',
    'action:workspace:EDIT-01:EDIT-01-ACT-VERSION-RESTORE-AS-DRAFT',
    'action:workspace:EDIT-01:EDIT-01-ACT-OUTPUT-DOWNLOAD',
    'control:workspace:EDIT-01:EDIT-01-BTN-VERSION-SAVE',
    'control:workspace:EDIT-01:EDIT-01-BTN-RENDER-EXECUTE',
    'control:workspace:EDIT-01:EDIT-01-BTN-RENDER-CANCEL',
    'control:workspace:EDIT-01:EDIT-01-BTN-OUTPUT-SAVE',
    'control:workspace:EDIT-01:EDIT-01-BTN-VERSION-LOCK',
    'control:workspace:EDIT-01:EDIT-01-BTN-VERSION-RESTORE',
    'control:workspace:EDIT-01:EDIT-01-BTN-DOWNLOAD'
  )
  ON CONFLICT(user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO n
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id AND a.effect='ALLOW' AND a.status='APPROVED'
    AND r.resource_key IN(
      'api:saveEditVersion','api:startEditRender','api:cancelEditRender','api:saveEditOutputVersion',
      'api:lockEditVersion','api:restoreEditVersionAsDraft','api:getEditOutputDownload',
      'action:workspace:EDIT-01:EDIT-01-ACT-VERSION-SAVE',
      'action:workspace:EDIT-01:EDIT-01-ACT-RENDER-START',
      'action:workspace:EDIT-01:EDIT-01-ACT-RENDER-CANCEL',
      'action:workspace:EDIT-01:EDIT-01-ACT-OUTPUT-VERSION-SAVE',
      'action:workspace:EDIT-01:EDIT-01-ACT-VERSION-LOCK',
      'action:workspace:EDIT-01:EDIT-01-ACT-VERSION-RESTORE-AS-DRAFT',
      'action:workspace:EDIT-01:EDIT-01-ACT-OUTPUT-DOWNLOAD',
      'control:workspace:EDIT-01:EDIT-01-BTN-VERSION-SAVE',
      'control:workspace:EDIT-01:EDIT-01-BTN-RENDER-EXECUTE',
      'control:workspace:EDIT-01:EDIT-01-BTN-RENDER-CANCEL',
      'control:workspace:EDIT-01:EDIT-01-BTN-OUTPUT-SAVE',
      'control:workspace:EDIT-01:EDIT-01-BTN-VERSION-LOCK',
      'control:workspace:EDIT-01:EDIT-01-BTN-VERSION-RESTORE',
      'control:workspace:EDIT-01:EDIT-01-BTN-DOWNLOAD'
    )
    AND a.action=CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END;
  IF n<>21 THEN RAISE EXCEPTION 'EDITFINAL0050_APPROVED_ALLOW_COUNT_MISMATCH:%',n; END IF;
END $$;

GRANT SELECT,INSERT ON public.editing_timelines TO acpos_app_runtime;
GRANT SELECT,INSERT,UPDATE ON public.edit_render_jobs TO acpos_app_runtime;
GRANT SELECT,INSERT ON public.production_output_version_locks TO acpos_app_runtime;

ALTER TABLE public.editing_timelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.edit_render_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_editing_timelines_actor_select ON public.editing_timelines;
DROP POLICY IF EXISTS acpos_editing_timelines_actor_insert ON public.editing_timelines;
CREATE POLICY acpos_editing_timelines_actor_select ON public.editing_timelines
FOR SELECT TO acpos_app_runtime
USING(acpos_runtime.can_access_project(acpos_runtime.project_id_for_task(task_id)));
CREATE POLICY acpos_editing_timelines_actor_insert ON public.editing_timelines
FOR INSERT TO acpos_app_runtime
WITH CHECK(acpos_runtime.can_manage_project(acpos_runtime.project_id_for_task(task_id)));

DROP POLICY IF EXISTS acpos_edit_render_jobs_actor_select ON public.edit_render_jobs;
DROP POLICY IF EXISTS acpos_edit_render_jobs_actor_insert ON public.edit_render_jobs;
DROP POLICY IF EXISTS acpos_edit_render_jobs_actor_update ON public.edit_render_jobs;
CREATE POLICY acpos_edit_render_jobs_actor_select ON public.edit_render_jobs
FOR SELECT TO acpos_app_runtime
USING(acpos_runtime.can_access_project(acpos_runtime.project_id_for_task(task_id)));
CREATE POLICY acpos_edit_render_jobs_actor_insert ON public.edit_render_jobs
FOR INSERT TO acpos_app_runtime
WITH CHECK(
  acpos_runtime.can_execute_edit_voice_operation('api:startEditRender')
  AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_task(task_id))
);
CREATE POLICY acpos_edit_render_jobs_actor_update ON public.edit_render_jobs
FOR UPDATE TO acpos_app_runtime
USING(acpos_runtime.can_manage_project(acpos_runtime.project_id_for_task(task_id)))
WITH CHECK(acpos_runtime.can_manage_project(acpos_runtime.project_id_for_task(task_id)));

DROP POLICY IF EXISTS acpos_output_version_locks_shared_insert ON public.production_output_version_locks;
CREATE POLICY acpos_output_version_locks_shared_insert ON public.production_output_version_locks
FOR INSERT TO acpos_app_runtime
WITH CHECK(
  (
    (department='ASSET' AND acpos_runtime.can_execute_shared_operation('api:lockAssetVersion'))
    OR (department='VIDEO' AND acpos_runtime.can_execute_shared_operation('api:lockVideoVersion'))
    OR (department='EDITING' AND acpos_runtime.can_execute_edit_voice_operation('api:lockEditVersion'))
  )
  AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_output(output_version_id))
);

DO $$
DECLARE c integer; p integer; r integer;
BEGIN
  SELECT count(*) INTO c
  FROM information_schema.columns
  WHERE table_schema='public' AND table_name='editing_timelines'
    AND column_name IN('source_timeline_id','source_draft_hash','version_content_hash','source_scorecard_id','saved_by','saved_at');
  IF c<>6 THEN RAISE EXCEPTION 'EDITFINAL0050_TIMELINE_COLUMN_COUNT_MISMATCH:%',c; END IF;

  SELECT count(*) INTO c
  FROM information_schema.columns
  WHERE table_schema='public' AND table_name='production_output_version_locks'
    AND column_name IN('edit_version_id','render_job_id','reason');
  IF c<>3 THEN RAISE EXCEPTION 'EDITFINAL0050_LOCK_LINEAGE_COLUMN_COUNT_MISMATCH:%',c; END IF;

  IF to_regclass('public.edit_render_jobs') IS NULL THEN
    RAISE EXCEPTION 'EDITFINAL0050_RENDER_JOB_OWNER_MISSING';
  END IF;

  SELECT count(*) INTO p FROM pg_policies
  WHERE schemaname='public' AND policyname IN(
    'acpos_editing_timelines_actor_select','acpos_editing_timelines_actor_insert',
    'acpos_edit_render_jobs_actor_select','acpos_edit_render_jobs_actor_insert','acpos_edit_render_jobs_actor_update',
    'acpos_output_version_locks_shared_select','acpos_output_version_locks_shared_insert'
  );
  IF p<>7 THEN RAISE EXCEPTION 'EDITFINAL0050_RLS_POLICY_COUNT_MISMATCH:%',p; END IF;

  SELECT count(*) INTO r FROM public.permission_resources
  WHERE active=true AND resource_key IN(
    'api:saveEditVersion','api:startEditRender','api:cancelEditRender','api:saveEditOutputVersion',
    'api:lockEditVersion','api:restoreEditVersionAsDraft','api:getEditOutputDownload',
    'action:workspace:EDIT-01:EDIT-01-ACT-VERSION-SAVE',
    'action:workspace:EDIT-01:EDIT-01-ACT-RENDER-START',
    'action:workspace:EDIT-01:EDIT-01-ACT-RENDER-CANCEL',
    'action:workspace:EDIT-01:EDIT-01-ACT-OUTPUT-VERSION-SAVE',
    'action:workspace:EDIT-01:EDIT-01-ACT-VERSION-LOCK',
    'action:workspace:EDIT-01:EDIT-01-ACT-VERSION-RESTORE-AS-DRAFT',
    'action:workspace:EDIT-01:EDIT-01-ACT-OUTPUT-DOWNLOAD',
    'control:workspace:EDIT-01:EDIT-01-BTN-VERSION-SAVE',
    'control:workspace:EDIT-01:EDIT-01-BTN-RENDER-EXECUTE',
    'control:workspace:EDIT-01:EDIT-01-BTN-RENDER-CANCEL',
    'control:workspace:EDIT-01:EDIT-01-BTN-OUTPUT-SAVE',
    'control:workspace:EDIT-01:EDIT-01-BTN-VERSION-LOCK',
    'control:workspace:EDIT-01:EDIT-01-BTN-VERSION-RESTORE',
    'control:workspace:EDIT-01:EDIT-01-BTN-DOWNLOAD'
  );
  IF r<>21 THEN RAISE EXCEPTION 'EDITFINAL0050_PERMISSION_RESOURCE_COUNT_MISMATCH:%',r; END IF;
END $$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES('0050_edit_finalize_persistence_permission_rls_closure','f6be546d52ff486236913c5f8c02971cf7e25c9f801fe3a8c5774f1a548553d5','migration-runner','CR-RUNTIME-0050')
ON CONFLICT(migration_id) DO NOTHING;
