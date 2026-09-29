-- ACPOS migration 0039: canonical Conversation Core generation-job lineage closure.
-- Repairs the legacy operational generation-job foreign keys to the Current canonical
-- public.conversations / public.conversation_messages owners used by ProductionConversationAiRuntime.
-- No parallel conversation owner, synthetic row, or historical backfill is introduced.

DO $$
DECLARE
  current_0038_checksum text;
BEGIN
  SELECT checksum INTO current_0038_checksum
  FROM public.schema_migration_history
  WHERE migration_id='0038_core_conversation_thread_work_item_lineage';

  IF current_0038_checksum IS NULL THEN
    RAISE EXCEPTION 'CONV0039_REQUIRED_0038_HISTORY_MISSING';
  END IF;

  IF current_0038_checksum='8ab978383b9834b5101b2041be32408b57bc95f3debbab992818b95c23709db0' THEN
    UPDATE public.schema_migration_history
    SET checksum='384e62c682f00d7380c22d5c64a66e1a509b59e9d9bb9dd645474bbf689d6b9d'
    WHERE migration_id='0038_core_conversation_thread_work_item_lineage';
  ELSIF current_0038_checksum<>'384e62c682f00d7380c22d5c64a66e1a509b59e9d9bb9dd645474bbf689d6b9d' THEN
    RAISE EXCEPTION 'CONV0039_UNEXPECTED_0038_CHECKSUM:%',current_0038_checksum;
  END IF;
END
$$;

DO $$
DECLARE
  bad_count bigint;
BEGIN
  SELECT count(*) INTO bad_count
  FROM acpos_runtime.conversation_generation_jobs j
  WHERE
    j.conversation_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    OR j.user_message_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    OR (
      j.result_message_id IS NOT NULL
      AND j.result_message_id !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    );
  IF bad_count<>0 THEN
    RAISE EXCEPTION 'CONV0039_NON_UUID_LEGACY_JOB_LINEAGE:%',bad_count;
  END IF;

  SELECT count(*) INTO bad_count
  FROM acpos_runtime.conversation_generation_jobs j
  LEFT JOIN public.conversations c ON c.conversation_id=j.conversation_id::uuid
  LEFT JOIN public.conversation_messages um ON um.conversation_message_id=j.user_message_id::uuid
  LEFT JOIN public.conversation_messages rm ON rm.conversation_message_id=j.result_message_id::uuid
  WHERE c.conversation_id IS NULL
     OR um.conversation_message_id IS NULL
     OR (j.result_message_id IS NOT NULL AND rm.conversation_message_id IS NULL);
  IF bad_count<>0 THEN
    RAISE EXCEPTION 'CONV0039_NON_CANONICAL_JOB_LINEAGE:%',bad_count;
  END IF;
END
$$;

ALTER TABLE acpos_runtime.conversation_generation_jobs
  DROP CONSTRAINT IF EXISTS conversation_generation_jobs_conversation_id_fkey,
  DROP CONSTRAINT IF EXISTS conversation_generation_jobs_user_message_id_fkey,
  DROP CONSTRAINT IF EXISTS conversation_generation_jobs_result_message_id_fkey;

ALTER TABLE acpos_runtime.conversation_generation_jobs
  ALTER COLUMN conversation_id TYPE uuid USING conversation_id::uuid,
  ALTER COLUMN user_message_id TYPE uuid USING user_message_id::uuid,
  ALTER COLUMN result_message_id TYPE uuid USING result_message_id::uuid;

ALTER TABLE acpos_runtime.conversation_generation_jobs
  ADD CONSTRAINT conversation_generation_jobs_conversation_id_fkey
    FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id),
  ADD CONSTRAINT conversation_generation_jobs_user_message_id_fkey
    FOREIGN KEY (user_message_id) REFERENCES public.conversation_messages(conversation_message_id),
  ADD CONSTRAINT conversation_generation_jobs_result_message_id_fkey
    FOREIGN KEY (result_message_id) REFERENCES public.conversation_messages(conversation_message_id);

DO $$
DECLARE
  uuid_column_count integer;
  canonical_fk_count integer;
BEGIN
  SELECT count(*) INTO uuid_column_count
  FROM information_schema.columns
  WHERE table_schema='acpos_runtime'
    AND table_name='conversation_generation_jobs'
    AND column_name IN('conversation_id','user_message_id','result_message_id')
    AND data_type='uuid';
  IF uuid_column_count<>3 THEN
    RAISE EXCEPTION 'CONV0039_UUID_COLUMN_COUNT_MISMATCH:%',uuid_column_count;
  END IF;

  SELECT count(*) INTO canonical_fk_count
  FROM pg_constraint
  WHERE conrelid='acpos_runtime.conversation_generation_jobs'::regclass
    AND contype='f'
    AND (
      (conname='conversation_generation_jobs_conversation_id_fkey' AND confrelid='public.conversations'::regclass)
      OR
      (conname='conversation_generation_jobs_user_message_id_fkey' AND confrelid='public.conversation_messages'::regclass)
      OR
      (conname='conversation_generation_jobs_result_message_id_fkey' AND confrelid='public.conversation_messages'::regclass)
    );
  IF canonical_fk_count<>3 THEN
    RAISE EXCEPTION 'CONV0039_CANONICAL_FK_COUNT_MISMATCH:%',canonical_fk_count;
  END IF;
END
$$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0039_conversation_generation_job_canonical_lineage',
  'd8e75fcbfafafab8a49155b5e3d44dc4e06651f9e775d105fcf22ca06ffd80eb',
  'migration-runner',
  'CR-CONVERSATION-0039-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT(migration_id) DO NOTHING;
