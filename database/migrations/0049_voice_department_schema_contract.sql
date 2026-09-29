-- ACPOS migration 0049: formal VOICE department schema contract closure.
-- Current production chain treats VOICE as a distinct department; EDITING must not impersonate VOICE.
-- Additive enum registration only; creates or mutates no business rows.

ALTER TYPE public.department_code ADD VALUE IF NOT EXISTS 'VOICE';

DO $$
DECLARE
  voice_values integer;
BEGIN
  SELECT count(*) INTO voice_values
  FROM pg_type t
  JOIN pg_namespace n ON n.oid=t.typnamespace
  JOIN pg_enum e ON e.enumtypid=t.oid
  WHERE n.nspname='public'
    AND t.typname='department_code'
    AND e.enumlabel='VOICE';

  IF voice_values<>1 THEN
    RAISE EXCEPTION 'VOICE0049_DEPARTMENT_ENUM_NOT_REGISTERED:%',voice_values;
  END IF;
END
$$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0049_voice_department_schema_contract',
  'efaca6966229c2cd10c6e0ea4e509d2df8f3c6621cfb460e66635010dacbf947',
  'migration-runner',
  'CR-RUNTIME-0049'
)
ON CONFLICT(migration_id) DO NOTHING;
