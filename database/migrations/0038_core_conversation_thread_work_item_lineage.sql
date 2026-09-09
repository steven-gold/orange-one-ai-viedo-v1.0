-- ACPOS migration 0038: CORE conversation thread work-item lineage owner.
-- Adds canonical CORE-only thread binding without altering generic conversation ownership.
-- No historical title parsing/backfill: legacy unbound conversations remain non-canonical for CORE projection.
-- Production apply remains pending final release sequence.

CREATE TABLE public.core_conversation_thread_bindings (
  conversation_id uuid PRIMARY KEY REFERENCES public.conversations(conversation_id) ON DELETE CASCADE,
  project_id uuid NOT NULL REFERENCES public.projects(project_id),
  topic_id uuid NULL REFERENCES public.topics(topic_id),
  work_item text NOT NULL,
  parent_conversation_id uuid NULL REFERENCES public.conversations(conversation_id),
  source_message_id uuid NULL REFERENCES public.conversation_messages(conversation_message_id),
  relation_kind text NOT NULL DEFAULT 'ROOT',
  created_by uuid NOT NULL REFERENCES public.app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT core_conversation_thread_work_item_check CHECK (
    work_item IN ('STORY','CHAPTER','WORLD_SETTING','DNA','BLUEPRINT','TOPIC_SCOPE','PRODUCTION_SCRIPT')
  ),
  CONSTRAINT core_conversation_thread_mode_check CHECK (
    (topic_id IS NULL AND work_item IN ('STORY','CHAPTER','WORLD_SETTING','DNA','BLUEPRINT'))
    OR
    (topic_id IS NOT NULL AND work_item IN ('TOPIC_SCOPE','PRODUCTION_SCRIPT'))
  ),
  CONSTRAINT core_conversation_thread_relation_check CHECK (
    (relation_kind='ROOT' AND parent_conversation_id IS NULL AND source_message_id IS NULL)
    OR
    (relation_kind='BRANCH' AND parent_conversation_id IS NOT NULL AND source_message_id IS NOT NULL AND parent_conversation_id<>conversation_id)
  )
);

CREATE OR REPLACE FUNCTION acpos_runtime.validate_core_conversation_thread_binding()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
DECLARE
  conversation_project_id uuid;
  conversation_topic_id uuid;
  conversation_created_by uuid;
  parent_project_id uuid;
  parent_topic_id uuid;
  parent_work_item text;
  source_conversation_id uuid;
BEGIN
  SELECT c.project_id,c.topic_id,c.created_by
  INTO conversation_project_id,conversation_topic_id,conversation_created_by
  FROM public.conversations c
  WHERE c.conversation_id=NEW.conversation_id;

  IF conversation_project_id IS NULL THEN
    RAISE EXCEPTION 'CORE0038_CONVERSATION_PROJECT_REQUIRED';
  END IF;
  IF conversation_project_id<>NEW.project_id
     OR conversation_topic_id IS DISTINCT FROM NEW.topic_id
     OR conversation_created_by<>NEW.created_by THEN
    RAISE EXCEPTION 'CORE0038_CONVERSATION_BINDING_MISMATCH';
  END IF;

  IF NEW.topic_id IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM public.topics t
    WHERE t.topic_id=NEW.topic_id AND t.project_id=NEW.project_id
  ) THEN
    RAISE EXCEPTION 'CORE0038_TOPIC_PROJECT_LINEAGE_MISMATCH';
  END IF;

  IF NEW.relation_kind='BRANCH' THEN
    SELECT b.project_id,b.topic_id,b.work_item
    INTO parent_project_id,parent_topic_id,parent_work_item
    FROM public.core_conversation_thread_bindings b
    WHERE b.conversation_id=NEW.parent_conversation_id;

    IF parent_project_id IS NULL
       OR parent_project_id<>NEW.project_id
       OR parent_topic_id IS DISTINCT FROM NEW.topic_id
       OR parent_work_item<>NEW.work_item THEN
      RAISE EXCEPTION 'CORE0038_PARENT_THREAD_SCOPE_MISMATCH';
    END IF;

    SELECT m.conversation_id INTO source_conversation_id
    FROM public.conversation_messages m
    WHERE m.conversation_message_id=NEW.source_message_id;

    IF source_conversation_id IS NULL OR source_conversation_id<>NEW.parent_conversation_id THEN
      RAISE EXCEPTION 'CORE0038_SOURCE_MESSAGE_PARENT_MISMATCH';
    END IF;
  END IF;

  RETURN NEW;
END
$$;

REVOKE ALL ON FUNCTION acpos_runtime.validate_core_conversation_thread_binding() FROM PUBLIC;

CREATE OR REPLACE FUNCTION acpos_runtime.protect_core_bound_conversation_lineage()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
BEGIN
  IF EXISTS(
    SELECT 1
    FROM public.core_conversation_thread_bindings b
    WHERE b.conversation_id=OLD.conversation_id
  ) AND (
    NEW.project_id IS DISTINCT FROM OLD.project_id
    OR NEW.topic_id IS DISTINCT FROM OLD.topic_id
    OR NEW.created_by IS DISTINCT FROM OLD.created_by
  ) THEN
    RAISE EXCEPTION 'CORE0038_BOUND_CONVERSATION_LINEAGE_IMMUTABLE';
  END IF;
  RETURN NEW;
END
$$;

REVOKE ALL ON FUNCTION acpos_runtime.protect_core_bound_conversation_lineage() FROM PUBLIC;

CREATE TRIGGER core_bound_conversation_lineage_guard
BEFORE UPDATE OF project_id,topic_id,created_by ON public.conversations
FOR EACH ROW
EXECUTE FUNCTION acpos_runtime.protect_core_bound_conversation_lineage();



CREATE TRIGGER core_conversation_thread_binding_validate
BEFORE INSERT OR UPDATE ON public.core_conversation_thread_bindings
FOR EACH ROW
EXECUTE FUNCTION acpos_runtime.validate_core_conversation_thread_binding();

GRANT SELECT,INSERT ON public.core_conversation_thread_bindings TO acpos_app_runtime;

ALTER TABLE public.core_conversation_thread_bindings ENABLE ROW LEVEL SECURITY;

CREATE POLICY acpos_core_conversation_thread_select ON public.core_conversation_thread_bindings
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_project(project_id));

CREATE POLICY acpos_core_conversation_thread_insert ON public.core_conversation_thread_bindings
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  created_by=acpos_runtime.current_actor_user_id()
  AND acpos_runtime.can_manage_project(project_id)
);

DO $$
DECLARE
  table_count integer;
  policy_count integer;
BEGIN
  SELECT count(*) INTO table_count
  FROM information_schema.tables
  WHERE table_schema='public' AND table_name='core_conversation_thread_bindings';
  IF table_count<>1 THEN
    RAISE EXCEPTION 'CORE0038_BINDING_TABLE_MISSING';
  END IF;

  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public'
    AND tablename='core_conversation_thread_bindings'
    AND policyname IN('acpos_core_conversation_thread_select','acpos_core_conversation_thread_insert');
  IF policy_count<>2 THEN
    RAISE EXCEPTION 'CORE0038_POLICY_COUNT_MISMATCH:%',policy_count;
  END IF;

  IF NOT has_table_privilege('acpos_app_runtime','public.core_conversation_thread_bindings','SELECT,INSERT') THEN
    RAISE EXCEPTION 'CORE0038_RUNTIME_GRANT_MISSING';
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0038_core_conversation_thread_work_item_lineage',
  '8ab978383b9834b5101b2041be32408b57bc95f3debbab992818b95c23709db0',
  'migration-runner',
  'CR-CORE-0038-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT(migration_id) DO NOTHING;
