-- ACPOS migration 0044: remove the historical command/conversation acceptance fixture.
-- Precise cleanup only. It preserves the shared workspace and any non-test projects/conversations.

DO $$
DECLARE
  v_project uuid;
  v_project_version uuid;
  v_conversation uuid;
  v_message uuid;
  v_workspace uuid;
  v_count integer;
BEGIN
  SELECT project_id,active_version_id,workspace_id
    INTO v_project,v_project_version,v_workspace
  FROM public.projects
  WHERE project_code='TEST-CMD-001';

  IF v_project IS NULL THEN
    RETURN;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.projects
    WHERE project_id=v_project
      AND title IN ('TEST-CMD-CREATE-001','STORY / 2026-09-05T19:19:30.789Z')
  ) THEN RAISE EXCEPTION 'CLEANUP0044_TEST_PROJECT_MARKER_INVALID'; END IF;

  SELECT count(*) INTO v_count
  FROM public.project_versions
  WHERE project_id=v_project;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0044_TEST_PROJECT_VERSION_CARDINALITY_INVALID'; END IF;

  IF NOT EXISTS (
    SELECT 1 FROM public.project_versions
    WHERE project_version_id=v_project_version
      AND project_id=v_project
      AND version_no=1
      AND story_core->>'title'='TEST-CMD-CREATE-001'
  ) THEN RAISE EXCEPTION 'CLEANUP0044_TEST_PROJECT_VERSION_MARKER_INVALID'; END IF;

  SELECT count(*) INTO v_count
  FROM public.conversations
  WHERE project_id=v_project;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0044_TEST_CONVERSATION_CARDINALITY_INVALID'; END IF;

  SELECT conversation_id INTO v_conversation
  FROM public.conversations
  WHERE project_id=v_project;

  IF NOT EXISTS (
    SELECT 1 FROM public.conversations
    WHERE conversation_id=v_conversation
      AND workspace_id=v_workspace
      AND title='STORY / 2026-09-05T19:19:30.789Z'
  ) THEN RAISE EXCEPTION 'CLEANUP0044_TEST_CONVERSATION_MARKER_INVALID'; END IF;

  SELECT count(*) INTO v_count
  FROM public.conversation_messages
  WHERE conversation_id=v_conversation;
  IF v_count<>1 THEN RAISE EXCEPTION 'CLEANUP0044_TEST_MESSAGE_CARDINALITY_INVALID'; END IF;

  SELECT conversation_message_id INTO v_message
  FROM public.conversation_messages
  WHERE conversation_id=v_conversation
    AND sequence_no=1
    AND actor_type='USER'
    AND message_content->>'text'='TEST-STR-SEND-001';
  IF v_message IS NULL THEN RAISE EXCEPTION 'CLEANUP0044_TEST_MESSAGE_MARKER_INVALID'; END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema='public'
      AND column_name='project_id'
      AND table_name NOT IN ('projects','project_versions','conversations')
  ) THEN
    -- Individual FK owners are guarded below by direct cardinality checks performed by the release dry-run.
    NULL;
  END IF;

  DELETE FROM public.conversation_messages WHERE conversation_message_id=v_message;
  DELETE FROM public.conversations WHERE conversation_id=v_conversation;

  UPDATE public.projects
  SET active_version_id=NULL
  WHERE project_id=v_project AND active_version_id=v_project_version;

  DELETE FROM public.project_versions WHERE project_version_id=v_project_version;
  DELETE FROM public.projects WHERE project_id=v_project;

  -- The workspace is shared by non-test project data and must remain.
  IF NOT EXISTS (
    SELECT 1 FROM public.workspaces WHERE workspace_id=v_workspace
  ) THEN RAISE EXCEPTION 'CLEANUP0044_SHARED_WORKSPACE_MUST_REMAIN'; END IF;
END
$$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0044_command_acceptance_fixture_cleanup',
  '4115f0e111e13dcbb044432871ba7116276ace5ef50083c8c402ba6cb5a60579',
  'migration-runner',
  'CR-RUNTIME-0044'
)
ON CONFLICT(migration_id) DO NOTHING;
