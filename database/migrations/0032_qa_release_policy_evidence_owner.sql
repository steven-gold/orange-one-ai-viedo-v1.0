-- ACPOS migration 0032: QA release policy evidence canonical owner.
-- Change ref: CR-QA-0032 (PENDING PRODUCTION APPLY).
-- Creates the missing canonical RightsPolicy/ChannelPolicy version owners and exact output binding.
-- Does not seed policy decisions, create release packages, approve releases, publish, or call external providers.

DO $$
DECLARE
  relation_exists boolean;
BEGIN
  SELECT EXISTS(
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='release_packages' AND column_name='release_policy_binding_id'
  ) INTO relation_exists;

  IF NOT relation_exists AND EXISTS (SELECT 1 FROM public.release_packages) THEN
    RAISE EXCEPTION 'QA0032_EXISTING_RELEASE_PACKAGE_BACKFILL_REQUIRED';
  END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.rights_profiles (
  rights_profile_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES public.projects(project_id),
  profile_key text NOT NULL,
  label text NOT NULL,
  status acpos_status NOT NULL DEFAULT 'DRAFT',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_id,profile_key)
);

CREATE TABLE IF NOT EXISTS public.rights_policy_versions (
  rights_policy_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rights_profile_id uuid NOT NULL REFERENCES public.rights_profiles(rights_profile_id),
  project_id uuid NOT NULL REFERENCES public.projects(project_id),
  version_no integer NOT NULL CHECK(version_no>0),
  policy_scope jsonb NOT NULL,
  policy_document jsonb NOT NULL,
  gate_state text NOT NULL CHECK(gate_state IN ('PASS','BLOCK')),
  status acpos_status NOT NULL DEFAULT 'DRAFT',
  content_hash char(64) NOT NULL UNIQUE,
  approved_by uuid NULL REFERENCES public.app_users(user_id),
  approved_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(rights_profile_id,version_no)
);

CREATE TABLE IF NOT EXISTS public.channel_policy_versions (
  channel_policy_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_account_id uuid NOT NULL REFERENCES public.channel_accounts(channel_account_id),
  project_id uuid NOT NULL REFERENCES public.projects(project_id),
  version_no integer NOT NULL CHECK(version_no>0),
  policy_scope jsonb NOT NULL,
  policy_document jsonb NOT NULL,
  gate_state text NOT NULL CHECK(gate_state IN ('PASS','BLOCK')),
  status acpos_status NOT NULL DEFAULT 'DRAFT',
  content_hash char(64) NOT NULL UNIQUE,
  approved_by uuid NULL REFERENCES public.app_users(user_id),
  approved_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(channel_account_id,project_id,version_no)
);

CREATE TABLE IF NOT EXISTS public.release_policy_bindings (
  release_policy_binding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  output_version_id uuid NOT NULL UNIQUE REFERENCES public.task_outputs(output_version_id),
  project_id uuid NOT NULL REFERENCES public.projects(project_id),
  rights_policy_version_id uuid NOT NULL REFERENCES public.rights_policy_versions(rights_policy_version_id),
  channel_required boolean NOT NULL,
  channel_policy_version_id uuid NULL REFERENCES public.channel_policy_versions(channel_policy_version_id),
  binding_scope jsonb NOT NULL DEFAULT '{}'::jsonb,
  status acpos_status NOT NULL DEFAULT 'DRAFT',
  binding_hash char(64) NOT NULL UNIQUE,
  approved_by uuid NULL REFERENCES public.app_users(user_id),
  approved_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT release_policy_bindings_channel_requirement_check CHECK (
    (channel_required AND channel_policy_version_id IS NOT NULL)
    OR
    (NOT channel_required AND channel_policy_version_id IS NULL)
  )
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='dna_assets_rights_profile_id_fkey'
      AND conrelid='public.dna_assets'::regclass
  ) THEN
    ALTER TABLE public.dna_assets
      ADD CONSTRAINT dna_assets_rights_profile_id_fkey
      FOREIGN KEY(rights_profile_id) REFERENCES public.rights_profiles(rights_profile_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='project_references_rights_profile_id_fkey'
      AND conrelid='public.project_references'::regclass
  ) THEN
    ALTER TABLE public.project_references
      ADD CONSTRAINT project_references_rights_profile_id_fkey
      FOREIGN KEY(rights_profile_id) REFERENCES public.rights_profiles(rights_profile_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='handoffs_rights_profile_id_fkey'
      AND conrelid='public.handoffs'::regclass
  ) THEN
    ALTER TABLE public.handoffs
      ADD CONSTRAINT handoffs_rights_profile_id_fkey
      FOREIGN KEY(rights_profile_id) REFERENCES public.rights_profiles(rights_profile_id);
  END IF;
END
$$;

ALTER TABLE public.release_packages
  ADD COLUMN IF NOT EXISTS release_policy_binding_id uuid,
  ADD COLUMN IF NOT EXISTS rights_policy_version_id uuid,
  ADD COLUMN IF NOT EXISTS channel_policy_version_id uuid;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='release_packages_release_policy_binding_id_fkey'
      AND conrelid='public.release_packages'::regclass
  ) THEN
    ALTER TABLE public.release_packages
      ADD CONSTRAINT release_packages_release_policy_binding_id_fkey
      FOREIGN KEY(release_policy_binding_id)
      REFERENCES public.release_policy_bindings(release_policy_binding_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='release_packages_rights_policy_version_id_fkey'
      AND conrelid='public.release_packages'::regclass
  ) THEN
    ALTER TABLE public.release_packages
      ADD CONSTRAINT release_packages_rights_policy_version_id_fkey
      FOREIGN KEY(rights_policy_version_id)
      REFERENCES public.rights_policy_versions(rights_policy_version_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='release_packages_channel_policy_version_id_fkey'
      AND conrelid='public.release_packages'::regclass
  ) THEN
    ALTER TABLE public.release_packages
      ADD CONSTRAINT release_packages_channel_policy_version_id_fkey
      FOREIGN KEY(channel_policy_version_id)
      REFERENCES public.channel_policy_versions(channel_policy_version_id);
  END IF;
END
$$;

ALTER TABLE public.release_packages
  ALTER COLUMN release_policy_binding_id SET NOT NULL,
  ALTER COLUMN rights_policy_version_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS rights_profiles_project_idx
  ON public.rights_profiles(project_id,status);
CREATE INDEX IF NOT EXISTS rights_policy_versions_project_idx
  ON public.rights_policy_versions(project_id,status,gate_state);
CREATE INDEX IF NOT EXISTS channel_policy_versions_project_idx
  ON public.channel_policy_versions(project_id,status,gate_state);
CREATE INDEX IF NOT EXISTS release_policy_bindings_project_idx
  ON public.release_policy_bindings(project_id,status);

GRANT SELECT ON
  public.rights_profiles,
  public.rights_policy_versions,
  public.channel_policy_versions,
  public.release_policy_bindings
TO acpos_app_runtime;

ALTER TABLE public.rights_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rights_policy_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.channel_policy_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.release_policy_bindings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_rights_profiles_qa_select ON public.rights_profiles;
CREATE POLICY acpos_rights_profiles_qa_select ON public.rights_profiles
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR acpos_runtime.can_access_project(project_id)
);

DROP POLICY IF EXISTS acpos_rights_policy_versions_qa_select ON public.rights_policy_versions;
CREATE POLICY acpos_rights_policy_versions_qa_select ON public.rights_policy_versions
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR acpos_runtime.can_access_project(project_id)
);

DROP POLICY IF EXISTS acpos_channel_policy_versions_qa_select ON public.channel_policy_versions;
CREATE POLICY acpos_channel_policy_versions_qa_select ON public.channel_policy_versions
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR acpos_runtime.can_access_project(project_id)
);

DROP POLICY IF EXISTS acpos_release_policy_bindings_qa_select ON public.release_policy_bindings;
CREATE POLICY acpos_release_policy_bindings_qa_select ON public.release_policy_bindings
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR acpos_runtime.can_access_project(project_id)
);

DO $$
DECLARE
  owner_table_count bigint;
  policy_count bigint;
  release_relation_count bigint;
  legacy_rights_fk_count bigint;
BEGIN
  SELECT count(*) INTO owner_table_count
  FROM information_schema.tables
  WHERE table_schema='public'
    AND table_name IN (
      'rights_profiles',
      'rights_policy_versions',
      'channel_policy_versions',
      'release_policy_bindings'
    );
  IF owner_table_count<>4 THEN
    RAISE EXCEPTION 'QA0032_POLICY_OWNER_TABLE_COUNT_MISMATCH:%',owner_table_count;
  END IF;

  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public'
    AND policyname IN (
      'acpos_rights_profiles_qa_select',
      'acpos_rights_policy_versions_qa_select',
      'acpos_channel_policy_versions_qa_select',
      'acpos_release_policy_bindings_qa_select'
    );
  IF policy_count<>4 THEN
    RAISE EXCEPTION 'QA0032_POLICY_RLS_COUNT_MISMATCH:%',policy_count;
  END IF;

  SELECT count(*) INTO release_relation_count
  FROM pg_constraint
  WHERE conrelid='public.release_packages'::regclass
    AND conname IN (
      'release_packages_release_policy_binding_id_fkey',
      'release_packages_rights_policy_version_id_fkey',
      'release_packages_channel_policy_version_id_fkey'
    );
  IF release_relation_count<>3 THEN
    RAISE EXCEPTION 'QA0032_RELEASE_RELATION_COUNT_MISMATCH:%',release_relation_count;
  END IF;

  SELECT count(*) INTO legacy_rights_fk_count
  FROM pg_constraint
  WHERE conname IN (
    'dna_assets_rights_profile_id_fkey',
    'project_references_rights_profile_id_fkey',
    'handoffs_rights_profile_id_fkey'
  );
  IF legacy_rights_fk_count<>3 THEN
    RAISE EXCEPTION 'QA0032_LEGACY_RIGHTS_FK_COUNT_MISMATCH:%',legacy_rights_fk_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0032_qa_release_policy_evidence_owner',
  '29ea699d2a7330380fa0b74ff0139d7fb5eb9d018a491d03999a615b24892636',
  'migration-runner',
  'CR-QA-0032-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
