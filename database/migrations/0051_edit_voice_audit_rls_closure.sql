-- ACPOS migration 0051: EDIT+VOICE audit RLS closure.
-- Adds only EDIT-01 audit policies to the existing canonical public.audit_events owner.
-- No business rows, provider mappings or synthetic acceptance fixtures are created.

DROP POLICY IF EXISTS acpos_audit_events_edit_insert ON public.audit_events;
DROP POLICY IF EXISTS acpos_audit_events_edit_select ON public.audit_events;

CREATE POLICY acpos_audit_events_edit_insert ON public.audit_events
FOR INSERT TO acpos_app_runtime
WITH CHECK(
  entity_type='workspace:EDIT-01'
  AND actor_type='USER'::public.actor_type
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND action=ANY(ARRAY[
    'createEditingRuntimeRun','getEditingRuntimeRun','completeAssembly','transitionEditingToVoiceStage',
    'startVoiceRuntime','getVoiceRuntimeRun','completeAudioMix','completeLipSync','completeSubtitle','handoffVoiceToQA',
    'saveEditVersion','startEditRender','cancelEditRender','saveEditOutputVersion',
    'lockEditVersion','restoreEditVersionAsDraft','getEditOutputDownload'
  ]::text[])
  AND (
    (
      workspace_id IS NOT NULL
      AND EXISTS(
        SELECT 1 FROM public.projects p
        WHERE p.workspace_id=audit_events.workspace_id
          AND acpos_runtime.can_access_project(p.project_id)
      )
    )
    OR (
      workspace_id IS NULL
      AND (reason LIKE 'DENIED:%' OR reason LIKE 'ERROR:%')
    )
  )
);

CREATE POLICY acpos_audit_events_edit_select ON public.audit_events
FOR SELECT TO acpos_app_runtime
USING(
  entity_type='workspace:EDIT-01'
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND (
    (
      workspace_id IS NOT NULL
      AND EXISTS(
        SELECT 1 FROM public.projects p
        WHERE p.workspace_id=audit_events.workspace_id
          AND acpos_runtime.can_access_project(p.project_id)
      )
    )
    OR (
      workspace_id IS NULL
      AND (reason LIKE 'DENIED:%' OR reason LIKE 'ERROR:%')
    )
  )
);

DO $$
DECLARE p integer; g integer;
BEGIN
  SELECT count(*) INTO p
  FROM pg_policies
  WHERE schemaname='public'
    AND tablename='audit_events'
    AND policyname IN('acpos_audit_events_edit_insert','acpos_audit_events_edit_select');
  IF p<>2 THEN RAISE EXCEPTION 'EDITAUDIT0051_POLICY_COUNT_MISMATCH:%',p; END IF;

  SELECT count(*) INTO g
  FROM information_schema.role_table_grants
  WHERE grantee='acpos_app_runtime'
    AND table_schema='public'
    AND table_name='audit_events'
    AND privilege_type IN('INSERT','SELECT');
  IF g<>2 THEN RAISE EXCEPTION 'EDITAUDIT0051_AUDIT_GRANT_COUNT_MISMATCH:%',g; END IF;
END $$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES('0051_edit_voice_audit_rls_closure','ddce6a15daa6f3f5e1407163fa2e10717fead8b82c264cbd08ac77ed0c4ab74e','migration-runner','CR-RUNTIME-0051')
ON CONFLICT(migration_id) DO NOTHING;
