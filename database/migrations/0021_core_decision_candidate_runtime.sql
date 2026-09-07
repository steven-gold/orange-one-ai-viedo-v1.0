-- ACPOS migration 0021: CORE Decision / Evaluation / Candidate Service runtime materialization.
-- Change ref: CR-CORE-0021 (PENDING PRODUCTION APPLY).
-- Materializes only Current CORE-01 owners already declared by Authority:
-- CORE Evaluation, HumanDecision, StructuredDecision and Candidate Service.
-- Reuses shared Conversation Core, QualityGovernance, Project/Topic, Account Permission and RLS owners.

CREATE TABLE IF NOT EXISTS public.core_evaluations (
  core_evaluation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES public.conversations(conversation_id),
  project_id uuid NOT NULL REFERENCES public.projects(project_id),
  topic_id uuid NULL REFERENCES public.topics(topic_id),
  work_item text NOT NULL,
  criteria_version_id uuid NOT NULL REFERENCES public.quality_criteria_versions(criteria_version_id),
  assistant_message_id uuid NOT NULL REFERENCES public.conversation_messages(conversation_message_id),
  assistant_summary text NOT NULL,
  dimensions jsonb NOT NULL,
  required_checks jsonb NOT NULL,
  gate_policy jsonb NOT NULL,
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  hard_blocks jsonb NOT NULL DEFAULT '[]'::jsonb,
  result text NOT NULL,
  context_fingerprint char(64) NOT NULL,
  content_hash char(64) NOT NULL UNIQUE,
  created_by uuid NOT NULL REFERENCES public.app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT core_evaluations_result_check CHECK (result IN ('PASS','BLOCKED')),
  CONSTRAINT core_evaluations_dimensions_json CHECK (jsonb_typeof(dimensions) IN ('array','object')),
  CONSTRAINT core_evaluations_required_checks_json CHECK (jsonb_typeof(required_checks) IN ('array','object')),
  CONSTRAINT core_evaluations_gate_policy_json CHECK (jsonb_typeof(gate_policy) = 'object'),
  CONSTRAINT core_evaluations_evidence_refs_array CHECK (jsonb_typeof(evidence_refs) = 'array'),
  CONSTRAINT core_evaluations_hard_blocks_array CHECK (jsonb_typeof(hard_blocks) = 'array'),
  CONSTRAINT core_evaluations_fingerprint_check CHECK (context_fingerprint ~ '^[0-9a-f]{64}$'),
  CONSTRAINT core_evaluations_hash_check CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  UNIQUE(conversation_id, assistant_message_id, criteria_version_id)
);

CREATE TABLE IF NOT EXISTS public.core_human_decisions (
  core_human_decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  core_evaluation_id uuid NOT NULL REFERENCES public.core_evaluations(core_evaluation_id),
  conversation_id uuid NOT NULL REFERENCES public.conversations(conversation_id),
  project_id uuid NOT NULL REFERENCES public.projects(project_id),
  topic_id uuid NULL REFERENCES public.topics(topic_id),
  target_assistant_message_id uuid NOT NULL REFERENCES public.conversation_messages(conversation_message_id),
  decision_text text NOT NULL,
  reason text NOT NULL,
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  context_fingerprint char(64) NOT NULL,
  created_by uuid NOT NULL REFERENCES public.app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT core_human_decisions_evidence_refs_array CHECK (jsonb_typeof(evidence_refs) = 'array'),
  CONSTRAINT core_human_decisions_fingerprint_check CHECK (context_fingerprint ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS public.core_structured_decisions (
  core_structured_decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  core_human_decision_id uuid NOT NULL UNIQUE REFERENCES public.core_human_decisions(core_human_decision_id),
  conversation_id uuid NOT NULL REFERENCES public.conversations(conversation_id),
  structured_document jsonb NOT NULL,
  source_human_text text NOT NULL,
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  content_hash char(64) NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT core_structured_decisions_document_object CHECK (jsonb_typeof(structured_document) = 'object'),
  CONSTRAINT core_structured_decisions_evidence_refs_array CHECK (jsonb_typeof(evidence_refs) = 'array'),
  CONSTRAINT core_structured_decisions_hash_check CHECK (content_hash ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS public.candidate_versions (
  candidate_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES public.projects(project_id),
  topic_id uuid NULL REFERENCES public.topics(topic_id),
  work_item text NOT NULL,
  version_no integer NOT NULL CHECK(version_no > 0),
  parent_candidate_version_id uuid NULL REFERENCES public.candidate_versions(candidate_version_id),
  source_conversation_id uuid NOT NULL REFERENCES public.conversations(conversation_id),
  source_assistant_message_id uuid NOT NULL REFERENCES public.conversation_messages(conversation_message_id),
  core_evaluation_id uuid NOT NULL REFERENCES public.core_evaluations(core_evaluation_id),
  core_human_decision_id uuid NOT NULL REFERENCES public.core_human_decisions(core_human_decision_id),
  core_structured_decision_id uuid NOT NULL UNIQUE REFERENCES public.core_structured_decisions(core_structured_decision_id),
  candidate_document jsonb NOT NULL,
  source_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  context_fingerprint char(64) NOT NULL,
  content_hash char(64) NOT NULL UNIQUE,
  created_by uuid NOT NULL REFERENCES public.app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  immutable_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT candidate_versions_document_object CHECK (jsonb_typeof(candidate_document) = 'object'),
  CONSTRAINT candidate_versions_source_refs_array CHECK (jsonb_typeof(source_refs) = 'array'),
  CONSTRAINT candidate_versions_fingerprint_check CHECK (context_fingerprint ~ '^[0-9a-f]{64}$'),
  CONSTRAINT candidate_versions_hash_check CHECK (content_hash ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS public.candidate_decisions (
  candidate_decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_version_id uuid NOT NULL UNIQUE REFERENCES public.candidate_versions(candidate_version_id),
  decision text NOT NULL,
  reason text NOT NULL,
  evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  candidate_content_hash char(64) NOT NULL,
  decided_by uuid NOT NULL REFERENCES public.app_users(user_id),
  decided_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT candidate_decisions_decision_check CHECK (decision IN ('ACCEPTED','MODIFY_REQUESTED','REJECTED')),
  CONSTRAINT candidate_decisions_evidence_refs_array CHECK (jsonb_typeof(evidence_refs) = 'array'),
  CONSTRAINT candidate_decisions_hash_check CHECK (candidate_content_hash ~ '^[0-9a-f]{64}$')
);

CREATE INDEX IF NOT EXISTS idx_core_evaluations_context
  ON public.core_evaluations(project_id, topic_id, work_item, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_core_human_decisions_context
  ON public.core_human_decisions(project_id, topic_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidate_versions_context
  ON public.candidate_versions(project_id, topic_id, work_item, version_no DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_versions_lineage
  ON public.candidate_versions(
    project_id,
    COALESCE(topic_id, '00000000-0000-0000-0000-000000000000'::uuid),
    work_item,
    version_no
  );

GRANT SELECT ON public.quality_criteria_versions TO acpos_app_runtime;
GRANT SELECT, INSERT ON
  public.core_evaluations,
  public.core_human_decisions,
  public.core_structured_decisions,
  public.candidate_versions,
  public.candidate_decisions
TO acpos_app_runtime;

ALTER TABLE public.core_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_human_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_structured_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.candidate_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.candidate_decisions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_core_evaluations_select ON public.core_evaluations;
DROP POLICY IF EXISTS acpos_core_evaluations_insert ON public.core_evaluations;
CREATE POLICY acpos_core_evaluations_select ON public.core_evaluations
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_access_project(project_id));
CREATE POLICY acpos_core_evaluations_insert ON public.core_evaluations
FOR INSERT TO acpos_app_runtime
WITH CHECK (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_manage_project(project_id));

DROP POLICY IF EXISTS acpos_core_human_decisions_select ON public.core_human_decisions;
DROP POLICY IF EXISTS acpos_core_human_decisions_insert ON public.core_human_decisions;
CREATE POLICY acpos_core_human_decisions_select ON public.core_human_decisions
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_access_project(project_id));
CREATE POLICY acpos_core_human_decisions_insert ON public.core_human_decisions
FOR INSERT TO acpos_app_runtime
WITH CHECK (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_manage_project(project_id));

DROP POLICY IF EXISTS acpos_core_structured_decisions_select ON public.core_structured_decisions;
DROP POLICY IF EXISTS acpos_core_structured_decisions_insert ON public.core_structured_decisions;
CREATE POLICY acpos_core_structured_decisions_select ON public.core_structured_decisions
FOR SELECT TO acpos_app_runtime
USING (EXISTS (
  SELECT 1 FROM public.core_human_decisions d
  WHERE d.core_human_decision_id=core_structured_decisions.core_human_decision_id
    AND (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_access_project(d.project_id))
));
CREATE POLICY acpos_core_structured_decisions_insert ON public.core_structured_decisions
FOR INSERT TO acpos_app_runtime
WITH CHECK (EXISTS (
  SELECT 1 FROM public.core_human_decisions d
  WHERE d.core_human_decision_id=core_structured_decisions.core_human_decision_id
    AND (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_manage_project(d.project_id))
));

DROP POLICY IF EXISTS acpos_candidate_versions_select ON public.candidate_versions;
DROP POLICY IF EXISTS acpos_candidate_versions_insert ON public.candidate_versions;
CREATE POLICY acpos_candidate_versions_select ON public.candidate_versions
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_access_project(project_id));
CREATE POLICY acpos_candidate_versions_insert ON public.candidate_versions
FOR INSERT TO acpos_app_runtime
WITH CHECK (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_manage_project(project_id));

DROP POLICY IF EXISTS acpos_candidate_decisions_select ON public.candidate_decisions;
DROP POLICY IF EXISTS acpos_candidate_decisions_insert ON public.candidate_decisions;
CREATE POLICY acpos_candidate_decisions_select ON public.candidate_decisions
FOR SELECT TO acpos_app_runtime
USING (EXISTS (
  SELECT 1 FROM public.candidate_versions c
  WHERE c.candidate_version_id=candidate_decisions.candidate_version_id
    AND (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_access_project(c.project_id))
));
CREATE POLICY acpos_candidate_decisions_insert ON public.candidate_decisions
FOR INSERT TO acpos_app_runtime
WITH CHECK (EXISTS (
  SELECT 1 FROM public.candidate_versions c
  WHERE c.candidate_version_id=candidate_decisions.candidate_version_id
    AND (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_manage_project(c.project_id))
));

DO $$
DECLARE
  table_count bigint;
  policy_count bigint;
BEGIN
  SELECT count(*) INTO table_count
  FROM pg_class c
  JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public'
    AND c.relname IN ('core_evaluations','core_human_decisions','core_structured_decisions','candidate_versions','candidate_decisions')
    AND c.relrowsecurity;

  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public'
    AND tablename IN ('core_evaluations','core_human_decisions','core_structured_decisions','candidate_versions','candidate_decisions')
    AND policyname IN (
      'acpos_core_evaluations_select','acpos_core_evaluations_insert',
      'acpos_core_human_decisions_select','acpos_core_human_decisions_insert',
      'acpos_core_structured_decisions_select','acpos_core_structured_decisions_insert',
      'acpos_candidate_versions_select','acpos_candidate_versions_insert',
      'acpos_candidate_decisions_select','acpos_candidate_decisions_insert'
    );

  IF table_count <> 5 THEN
    RAISE EXCEPTION 'CORE_DECISION_CANDIDATE_RLS_TABLE_COUNT_MISMATCH:%', table_count;
  END IF;
  IF policy_count <> 10 THEN
    RAISE EXCEPTION 'CORE_DECISION_CANDIDATE_RLS_POLICY_COUNT_MISMATCH:%', policy_count;
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES(
  '0021_core_decision_candidate_runtime',
  'PENDING_CHECKSUM',
  'migration-runner',
  'CR-CORE-0021-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
