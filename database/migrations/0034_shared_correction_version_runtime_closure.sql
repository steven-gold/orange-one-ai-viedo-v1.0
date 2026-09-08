-- ACPOS migration 0034: shared correction/version runtime closure.
-- Human correction candidates remain canonical in public.correction_script_versions.
-- Runtime correction mirrors remain execution/trace only.
-- Output version locks use a dedicated owner; Mother/Child locks are not reused.
-- Restore-as-new creates lineage-only drafts and never fabricates task_outputs.

ALTER TABLE public.correction_script_versions ADD COLUMN IF NOT EXISTS version_no integer;
ALTER TABLE public.correction_script_versions ADD COLUMN IF NOT EXISTS content_hash char(64);
ALTER TABLE public.correction_script_versions ADD COLUMN IF NOT EXISTS decision_reason text;
ALTER TABLE public.correction_script_versions ADD COLUMN IF NOT EXISTS decided_by uuid NULL REFERENCES public.app_users(user_id);
ALTER TABLE public.correction_script_versions ADD COLUMN IF NOT EXISTS decided_at timestamptz NULL;

WITH ranked AS(
  SELECT correction_script_version_id,row_number() OVER(PARTITION BY correction_request_id ORDER BY created_at,correction_script_version_id)::int AS rn
  FROM public.correction_script_versions
)
UPDATE public.correction_script_versions c SET version_no=r.rn FROM ranked r
WHERE c.correction_script_version_id=r.correction_script_version_id AND c.version_no IS NULL;

UPDATE public.correction_script_versions
SET content_hash=encode(digest(concat_ws('|',correction_request_id::text,version_no::text,correction_instruction::text,target_department,failed_output_id::text),'sha256'),'hex')
WHERE content_hash IS NULL;

ALTER TABLE public.correction_script_versions ALTER COLUMN version_no SET NOT NULL;
ALTER TABLE public.correction_script_versions ALTER COLUMN content_hash SET NOT NULL;
DO $$ BEGIN
  IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname='correction_script_versions_request_version_key') THEN
    ALTER TABLE public.correction_script_versions ADD CONSTRAINT correction_script_versions_request_version_key UNIQUE(correction_request_id,version_no);
  END IF;
  IF NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname='correction_script_versions_content_hash_check') THEN
    ALTER TABLE public.correction_script_versions ADD CONSTRAINT correction_script_versions_content_hash_check CHECK(content_hash ~ '^[0-9a-f]{64}$');
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.production_output_version_locks(
  production_output_version_lock_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  output_version_id uuid NOT NULL UNIQUE REFERENCES public.task_outputs(output_version_id),
  task_id uuid NOT NULL REFERENCES public.department_tasks(task_id),
  department text NOT NULL CHECK(department IN('ASSET','VIDEO')),
  scorecard_id uuid NOT NULL REFERENCES public.scorecards(scorecard_id),
  artifact_checksum char(64) NOT NULL,
  output_contract_hash char(64) NOT NULL,
  manifest_hash char(64) NULL,
  locked_by uuid NOT NULL REFERENCES public.app_users(user_id),
  status text NOT NULL DEFAULT 'LOCKED' CHECK(status IN('LOCKED','SUPERSEDED')),
  locked_at timestamptz NOT NULL DEFAULT now(),
  superseded_at timestamptz NULL
);

CREATE TABLE IF NOT EXISTS public.asset_version_restore_drafts(
  asset_version_restore_draft_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_output_version_id uuid NOT NULL REFERENCES public.task_outputs(output_version_id),
  task_id uuid NOT NULL REFERENCES public.department_tasks(task_id),
  project_id uuid NULL REFERENCES public.projects(project_id),
  topic_id uuid NULL REFERENCES public.topics(topic_id),
  source_output_uri text NOT NULL,
  source_artifact_checksum char(64) NOT NULL,
  reason text NOT NULL,
  status text NOT NULL DEFAULT 'DRAFT' CHECK(status IN('DRAFT','CONSUMED','SUPERSEDED')),
  created_by uuid NOT NULL REFERENCES public.app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  consumed_output_version_id uuid NULL REFERENCES public.task_outputs(output_version_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_asset_restore_active_draft
  ON public.asset_version_restore_drafts(source_output_version_id,created_by) WHERE status='DRAFT';

INSERT INTO public.permission_resources(resource_key,resource_type,parent_resource_key,allowed_actions,risk_tier)
VALUES
  ('action:workspace:ASSET-01:ACT-CORRECTION-GENERATE','ACTION','section:workspace:ASSET-01:action_dock','["INVOKE"]'::jsonb,'STANDARD'),
  ('control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-GENERATE','CONTROL','section:workspace:ASSET-01:action_dock','["INVOKE"]'::jsonb,'STANDARD'),
  ('action:workspace:ASSET-01:ACT-CORRECTION-APPROVE','ACTION','section:workspace:ASSET-01:action_dock','["INVOKE"]'::jsonb,'HIGH'),
  ('control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-APPROVE','CONTROL','section:workspace:ASSET-01:action_dock','["INVOKE"]'::jsonb,'HIGH'),
  ('action:workspace:ASSET-01:ACT-RESTORE-AS-NEW','ACTION','section:workspace:ASSET-01:action_dock','["INVOKE"]'::jsonb,'HIGH'),
  ('control:workspace:ASSET-01:ASSET-01-BTN-RESTORE-AS-NEW','CONTROL','section:workspace:ASSET-01:action_dock','["INVOKE"]'::jsonb,'HIGH'),
  ('action:workspace:ASSET-01:ACT-VERSION-LOCK','ACTION','section:workspace:ASSET-01:action_dock','["INVOKE"]'::jsonb,'HIGH'),
  ('control:workspace:ASSET-01:ASSET-01-BTN-LOCK','CONTROL','section:workspace:ASSET-01:action_dock','["INVOKE"]'::jsonb,'HIGH'),
  ('action:workspace:VIDEO-01:ACT-CORRECTION-GENERATE','ACTION','section:workspace:VIDEO-01:action_dock','["INVOKE"]'::jsonb,'STANDARD'),
  ('control:workspace:VIDEO-01:VIDEO-01-BTN-GEN-CORRECTION','CONTROL','section:workspace:VIDEO-01:action_dock','["INVOKE"]'::jsonb,'STANDARD'),
  ('action:workspace:VIDEO-01:ACT-CORRECTION-APPROVE','ACTION','section:workspace:VIDEO-01:action_dock','["INVOKE"]'::jsonb,'HIGH'),
  ('control:workspace:VIDEO-01:VIDEO-01-BTN-APPROVE-CORRECTION','CONTROL','section:workspace:VIDEO-01:action_dock','["INVOKE"]'::jsonb,'HIGH'),
  ('action:workspace:VIDEO-01:ACT-VERSION-LOCK','ACTION','section:workspace:VIDEO-01:action_dock','["INVOKE"]'::jsonb,'HIGH'),
  ('control:workspace:VIDEO-01:VIDEO-01-BTN-LOCK','CONTROL','section:workspace:VIDEO-01:action_dock','["INVOKE"]'::jsonb,'HIGH'),
  ('api:generateCorrectionScriptCandidate','API',NULL,'["EXECUTE"]'::jsonb,'STANDARD'),
  ('api:approveCorrectionScriptCandidate','API',NULL,'["EXECUTE"]'::jsonb,'HIGH'),
  ('api:restoreAssetVersionAsNewDraft','API',NULL,'["EXECUTE"]'::jsonb,'HIGH'),
  ('api:lockAssetVersion','API',NULL,'["EXECUTE"]'::jsonb,'HIGH'),
  ('api:lockVideoVersion','API',NULL,'["EXECUTE"]'::jsonb,'HIGH')
ON CONFLICT(resource_key) DO NOTHING;

DO $$
DECLARE n bigint; bootstrap_user_id uuid; a bigint;
BEGIN
  SELECT count(*) INTO n FROM public.permission_resources r
  WHERE r.resource_key IN('action:workspace:ASSET-01:ACT-CORRECTION-GENERATE','control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-GENERATE','action:workspace:ASSET-01:ACT-CORRECTION-APPROVE','control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-APPROVE','action:workspace:ASSET-01:ACT-RESTORE-AS-NEW','control:workspace:ASSET-01:ASSET-01-BTN-RESTORE-AS-NEW','action:workspace:ASSET-01:ACT-VERSION-LOCK','control:workspace:ASSET-01:ASSET-01-BTN-LOCK','action:workspace:VIDEO-01:ACT-CORRECTION-GENERATE','control:workspace:VIDEO-01:VIDEO-01-BTN-GEN-CORRECTION','action:workspace:VIDEO-01:ACT-CORRECTION-APPROVE','control:workspace:VIDEO-01:VIDEO-01-BTN-APPROVE-CORRECTION','action:workspace:VIDEO-01:ACT-VERSION-LOCK','control:workspace:VIDEO-01:VIDEO-01-BTN-LOCK','api:generateCorrectionScriptCandidate','api:approveCorrectionScriptCandidate','api:restoreAssetVersionAsNewDraft','api:lockAssetVersion','api:lockVideoVersion')
    AND r.active=true
    AND (
      (r.resource_type IN('ACTION','CONTROL') AND r.allowed_actions='["INVOKE"]'::jsonb)
      OR (r.resource_type='API' AND r.allowed_actions='["EXECUTE"]'::jsonb)
    );
  IF n<>19 THEN RAISE EXCEPTION 'SHARED0034_PERMISSION_RESOURCE_COUNT_MISMATCH:%',n; END IF;

  SELECT u.user_id INTO bootstrap_user_id
  FROM public.app_users u JOIN acpos_runtime.accounts ac ON lower(ac.email)=lower(u.email::text)
  WHERE ac.id='runtime-admin' AND ac.status='READY' AND u.disabled_at IS NULL LIMIT 1;
  IF bootstrap_user_id IS NULL THEN RAISE EXCEPTION 'SHARED0034_BOOTSTRAP_ADMIN_NOT_READY'; END IF;

  INSERT INTO public.account_permission_assignments(user_id,resource_id,action,effect,scope,condition,gate_profile,status,granted_by_user_id,approval_ref,version_no,effective_from,effective_to,approval_required)
  SELECT bootstrap_user_id,r.resource_id,CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END,'ALLOW','{}'::jsonb,'{}'::jsonb,
         jsonb_build_object('runtime_scope','SHARED_CORRECTION_VERSION_RUNTIME','source_resource',r.resource_key,'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'),
         'APPROVED',bootstrap_user_id,'CR-SHARED-0034-PENDING-PRODUCTION-APPLY',1,now(),NULL,false
  FROM public.permission_resources r WHERE r.resource_key IN('action:workspace:ASSET-01:ACT-CORRECTION-GENERATE','control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-GENERATE','action:workspace:ASSET-01:ACT-CORRECTION-APPROVE','control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-APPROVE','action:workspace:ASSET-01:ACT-RESTORE-AS-NEW','control:workspace:ASSET-01:ASSET-01-BTN-RESTORE-AS-NEW','action:workspace:ASSET-01:ACT-VERSION-LOCK','control:workspace:ASSET-01:ASSET-01-BTN-LOCK','action:workspace:VIDEO-01:ACT-CORRECTION-GENERATE','control:workspace:VIDEO-01:VIDEO-01-BTN-GEN-CORRECTION','action:workspace:VIDEO-01:ACT-CORRECTION-APPROVE','control:workspace:VIDEO-01:VIDEO-01-BTN-APPROVE-CORRECTION','action:workspace:VIDEO-01:ACT-VERSION-LOCK','control:workspace:VIDEO-01:VIDEO-01-BTN-LOCK','api:generateCorrectionScriptCandidate','api:approveCorrectionScriptCandidate','api:restoreAssetVersionAsNewDraft','api:lockAssetVersion','api:lockVideoVersion')
  ON CONFLICT(user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO a
  FROM public.account_permission_assignments x JOIN public.permission_resources r ON r.resource_id=x.resource_id
  WHERE x.user_id=bootstrap_user_id AND r.resource_key IN('action:workspace:ASSET-01:ACT-CORRECTION-GENERATE','control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-GENERATE','action:workspace:ASSET-01:ACT-CORRECTION-APPROVE','control:workspace:ASSET-01:ASSET-01-BTN-CORRECTION-APPROVE','action:workspace:ASSET-01:ACT-RESTORE-AS-NEW','control:workspace:ASSET-01:ASSET-01-BTN-RESTORE-AS-NEW','action:workspace:ASSET-01:ACT-VERSION-LOCK','control:workspace:ASSET-01:ASSET-01-BTN-LOCK','action:workspace:VIDEO-01:ACT-CORRECTION-GENERATE','control:workspace:VIDEO-01:VIDEO-01-BTN-GEN-CORRECTION','action:workspace:VIDEO-01:ACT-CORRECTION-APPROVE','control:workspace:VIDEO-01:VIDEO-01-BTN-APPROVE-CORRECTION','action:workspace:VIDEO-01:ACT-VERSION-LOCK','control:workspace:VIDEO-01:VIDEO-01-BTN-LOCK','api:generateCorrectionScriptCandidate','api:approveCorrectionScriptCandidate','api:restoreAssetVersionAsNewDraft','api:lockAssetVersion','api:lockVideoVersion') AND x.effect='ALLOW' AND x.status='APPROVED'
    AND x.action=CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END;
  IF a<>19 THEN RAISE EXCEPTION 'SHARED0034_APPROVED_ALLOW_COUNT_MISMATCH:%',a; END IF;
END $$;

CREATE OR REPLACE FUNCTION acpos_runtime.can_execute_shared_operation(resource_key_input text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public,acpos_runtime AS $$
  SELECT CASE WHEN EXISTS(
    SELECT 1 FROM public.account_permission_assignments a JOIN public.permission_resources r ON r.resource_id=a.resource_id
    WHERE a.user_id=acpos_runtime.current_actor_user_id() AND r.resource_key=resource_key_input AND r.active=true
      AND a.action='EXECUTE' AND a.effect='DENY' AND a.status='APPROVED' AND a.effective_from<=now() AND (a.effective_to IS NULL OR a.effective_to>now())
  ) THEN false ELSE EXISTS(
    SELECT 1 FROM public.account_permission_assignments a JOIN public.permission_resources r ON r.resource_id=a.resource_id
    WHERE a.user_id=acpos_runtime.current_actor_user_id() AND r.resource_key=resource_key_input AND r.active=true
      AND a.action='EXECUTE' AND a.effect='ALLOW' AND a.status='APPROVED' AND a.effective_from<=now() AND (a.effective_to IS NULL OR a.effective_to>now())
  ) END
$$;
REVOKE ALL ON FUNCTION acpos_runtime.can_execute_shared_operation(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acpos_runtime.can_execute_shared_operation(text) TO acpos_app_runtime;

GRANT SELECT,INSERT,UPDATE(status,decision_reason,decided_by,decided_at) ON public.correction_script_versions TO acpos_app_runtime;
GRANT SELECT,INSERT ON public.production_output_version_locks TO acpos_app_runtime;
GRANT SELECT,INSERT,UPDATE(status,consumed_output_version_id) ON public.asset_version_restore_drafts TO acpos_app_runtime;

ALTER TABLE public.correction_script_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.production_output_version_locks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.asset_version_restore_drafts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_correction_script_versions_shared_select ON public.correction_script_versions;
DROP POLICY IF EXISTS acpos_correction_script_versions_shared_insert ON public.correction_script_versions;
DROP POLICY IF EXISTS acpos_correction_script_versions_shared_update ON public.correction_script_versions;
CREATE POLICY acpos_correction_script_versions_shared_select ON public.correction_script_versions FOR SELECT TO acpos_app_runtime
USING(EXISTS(SELECT 1 FROM public.correction_requests cr WHERE cr.correction_request_id=correction_script_versions.correction_request_id
  AND acpos_runtime.can_access_project(acpos_runtime.project_id_for_output(cr.source_output_version_id))));
CREATE POLICY acpos_correction_script_versions_shared_insert ON public.correction_script_versions FOR INSERT TO acpos_app_runtime
WITH CHECK(acpos_runtime.can_execute_shared_operation('api:generateCorrectionScriptCandidate')
  AND EXISTS(SELECT 1 FROM public.correction_requests cr WHERE cr.correction_request_id=correction_script_versions.correction_request_id
    AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_output(cr.source_output_version_id))));
CREATE POLICY acpos_correction_script_versions_shared_update ON public.correction_script_versions FOR UPDATE TO acpos_app_runtime
USING(acpos_runtime.can_execute_shared_operation('api:approveCorrectionScriptCandidate')
  AND EXISTS(SELECT 1 FROM public.correction_requests cr WHERE cr.correction_request_id=correction_script_versions.correction_request_id
    AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_output(cr.source_output_version_id))))
WITH CHECK(acpos_runtime.can_execute_shared_operation('api:approveCorrectionScriptCandidate')
  AND EXISTS(SELECT 1 FROM public.correction_requests cr WHERE cr.correction_request_id=correction_script_versions.correction_request_id
    AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_output(cr.source_output_version_id))));

DROP POLICY IF EXISTS acpos_output_version_locks_shared_select ON public.production_output_version_locks;
DROP POLICY IF EXISTS acpos_output_version_locks_shared_insert ON public.production_output_version_locks;
CREATE POLICY acpos_output_version_locks_shared_select ON public.production_output_version_locks FOR SELECT TO acpos_app_runtime
USING(acpos_runtime.can_access_project(acpos_runtime.project_id_for_output(output_version_id)));
CREATE POLICY acpos_output_version_locks_shared_insert ON public.production_output_version_locks FOR INSERT TO acpos_app_runtime
WITH CHECK(
  ((department='ASSET' AND acpos_runtime.can_execute_shared_operation('api:lockAssetVersion'))
    OR(department='VIDEO' AND acpos_runtime.can_execute_shared_operation('api:lockVideoVersion')))
  AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_output(output_version_id))
);

DROP POLICY IF EXISTS acpos_asset_restore_drafts_shared_select ON public.asset_version_restore_drafts;
DROP POLICY IF EXISTS acpos_asset_restore_drafts_shared_insert ON public.asset_version_restore_drafts;
DROP POLICY IF EXISTS acpos_asset_restore_drafts_shared_update ON public.asset_version_restore_drafts;
CREATE POLICY acpos_asset_restore_drafts_shared_select ON public.asset_version_restore_drafts FOR SELECT TO acpos_app_runtime
USING(acpos_runtime.can_access_project(acpos_runtime.project_id_for_output(source_output_version_id)));
CREATE POLICY acpos_asset_restore_drafts_shared_insert ON public.asset_version_restore_drafts FOR INSERT TO acpos_app_runtime
WITH CHECK(acpos_runtime.can_execute_shared_operation('api:restoreAssetVersionAsNewDraft')
  AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_output(source_output_version_id)));
CREATE POLICY acpos_asset_restore_drafts_shared_update ON public.asset_version_restore_drafts FOR UPDATE TO acpos_app_runtime
USING(acpos_runtime.can_execute_shared_operation('api:restoreAssetVersionAsNewDraft')
  AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_output(source_output_version_id)))
WITH CHECK(acpos_runtime.can_execute_shared_operation('api:restoreAssetVersionAsNewDraft')
  AND acpos_runtime.can_manage_project(acpos_runtime.project_id_for_output(source_output_version_id)));

DO $
DECLARE p bigint; g bigint; cg bigint;
BEGIN
  SELECT count(*) INTO p FROM pg_policies WHERE schemaname='public' AND policyname IN(
    'acpos_correction_script_versions_shared_select','acpos_correction_script_versions_shared_insert','acpos_correction_script_versions_shared_update',
    'acpos_output_version_locks_shared_select','acpos_output_version_locks_shared_insert',
    'acpos_asset_restore_drafts_shared_select','acpos_asset_restore_drafts_shared_insert','acpos_asset_restore_drafts_shared_update');
  IF p<>8 THEN RAISE EXCEPTION 'SHARED0034_RLS_POLICY_COUNT_MISMATCH:%',p; END IF;
  SELECT count(*) INTO g FROM information_schema.role_table_grants WHERE grantee='acpos_app_runtime' AND table_schema='public'
    AND ((table_name='correction_script_versions' AND privilege_type IN('SELECT','INSERT'))
      OR(table_name='production_output_version_locks' AND privilege_type IN('SELECT','INSERT'))
      OR(table_name='asset_version_restore_drafts' AND privilege_type IN('SELECT','INSERT')));
  IF g<>6 THEN RAISE EXCEPTION 'SHARED0034_RUNTIME_TABLE_GRANT_COUNT_MISMATCH:%',g; END IF;
  SELECT count(*) INTO cg FROM information_schema.role_column_grants WHERE grantee='acpos_app_runtime' AND table_schema='public'
    AND privilege_type='UPDATE'
    AND (
      (table_name='correction_script_versions' AND column_name IN('status','decision_reason','decided_by','decided_at'))
      OR (table_name='asset_version_restore_drafts' AND column_name IN('status','consumed_output_version_id'))
    );
  IF cg<>6 THEN RAISE EXCEPTION 'SHARED0034_RUNTIME_COLUMN_GRANT_COUNT_MISMATCH:%',cg; END IF;
END $;

INSERT INTO schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES('0034_shared_correction_version_runtime_closure','861adc15e7bb255290fca7d253bed197cc757baf601f5da5887b0ef62fbee83c','migration-runner','CR-SHARED-0034-PENDING-PRODUCTION-APPLY')
ON CONFLICT(migration_id) DO NOTHING;
