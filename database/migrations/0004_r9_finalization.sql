-- ACPOS R9 semantic finalization: persistence, prompt compilation, project story/DNA and direct production lineage.
CREATE TABLE IF NOT EXISTS user_ui_preferences (
  user_id uuid PRIMARY KEY REFERENCES app_users(user_id), sidebar_mode text NOT NULL DEFAULT 'MANUAL' CHECK(sidebar_mode IN ('MANUAL','AUTO','PINNED')),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS dashboard_todos (
  todo_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES app_users(user_id), scope_type text NOT NULL CHECK(scope_type IN ('PERSONAL','PROJECT','TOPIC','TASK')),
  project_id uuid NULL REFERENCES projects(project_id), topic_id uuid NULL REFERENCES topics(topic_id), task_id uuid NULL REFERENCES department_tasks(task_id), title text NOT NULL,
  deadline_at timestamptz NULL, priority text NOT NULL CHECK(priority IN ('LOW','MEDIUM','HIGH','URGENT')), status text NOT NULL CHECK(status IN ('OPEN','IN_PROGRESS','DONE','CANCELLED')),
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS project_creation_wizard_sessions (
  wizard_session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NULL REFERENCES projects(project_id), owner_user_id uuid NOT NULL REFERENCES app_users(user_id),
  current_step smallint NOT NULL CHECK(current_step BETWEEN 1 AND 10), draft_payload jsonb NOT NULL DEFAULT '{}'::jsonb, status text NOT NULL CHECK(status IN ('DRAFT','COMPARISON','LOCK_REQUESTED','COMPLETED','ABANDONED')),
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS story_core_versions (
  story_core_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), version_no integer NOT NULL CHECK(version_no > 0),
  title text NOT NULL, logline text NOT NULL, premise text NOT NULL, core_conflict text NOT NULL, theme text NOT NULL, emotional_core text NOT NULL, audience_promise text NOT NULL,
  story_goal text NOT NULL, main_hook text NOT NULL, tone text NOT NULL, genre text NOT NULL, narrative_style text NOT NULL, ending_direction text NOT NULL, forbidden_direction text NOT NULL,
  status text NOT NULL CHECK(status IN ('CANDIDATE','ADOPTED','LOCKED','SUPERSEDED')), source_candidate_id uuid NULL, checksum char(64) NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id, version_no)
);
CREATE TABLE IF NOT EXISTS story_candidates (
  story_candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), wizard_session_id uuid NULL REFERENCES project_creation_wizard_sessions(wizard_session_id),
  candidate_key text NOT NULL, content jsonb NOT NULL, strengths jsonb NOT NULL, weaknesses jsonb NOT NULL, market_positioning text NOT NULL, character_space text NOT NULL,
  long_form_extension text NOT NULL, foreshadowing_capacity text NOT NULL, production_cost text NOT NULL, production_risk text NOT NULL, recommendation text NOT NULL,
  status text NOT NULL CHECK(status IN ('CANDIDATE','COMPARED','ADOPTED','REJECTED','SUPERSEDED')), generated_by_subject_type text NOT NULL CHECK(generated_by_subject_type IN ('USER','SERVICE_IDENTITY')), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id, candidate_key)
);
CREATE TABLE IF NOT EXISTS story_candidate_comparisons (
  comparison_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), candidate_ids jsonb NOT NULL, comparison_payload jsonb NOT NULL,
  human_decision text NULL CHECK(human_decision IN ('ADOPT','MERGE','REQUEST_REVISION','REJECT')), decided_by uuid NULL REFERENCES app_users(user_id), decided_at timestamptz NULL, audit_event_id uuid NULL REFERENCES audit_events(audit_event_id)
);
CREATE TABLE IF NOT EXISTS world_bible_versions (
  world_bible_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), version_no integer NOT NULL CHECK(version_no > 0),
  world_name text NOT NULL, content jsonb NOT NULL, status text NOT NULL CHECK(status IN ('CANDIDATE','ADOPTED','LOCKED','SUPERSEDED')), checksum char(64) NOT NULL,
  created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id, version_no)
);
CREATE TABLE IF NOT EXISTS world_canon_rules (
  world_canon_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), world_bible_version_id uuid NOT NULL REFERENCES world_bible_versions(world_bible_version_id),
  canon_level text NOT NULL CHECK(canon_level IN ('HARD_CANON','SOFT_CANON')), rule_text text NOT NULL, enforcement text NOT NULL CHECK(enforcement IN ('INSTRUCTION_PACKAGE_REQUIRED','VARIATION_RATIONALE_REQUIRED')), active boolean NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS dna_versions (
  dna_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), dna_type text NOT NULL CHECK(dna_type IN ('CHARACTER','OBJECT','SCENE','MUSIC_SOUND')),
  entity_key text NOT NULL, version_no integer NOT NULL CHECK(version_no > 0), content jsonb NOT NULL, status text NOT NULL CHECK(status IN ('CANDIDATE','LOCKED','SUPERSEDED')),
  parent_dna_version_id uuid NULL REFERENCES dna_versions(dna_version_id), lock_decision_request_id uuid NULL REFERENCES decision_requests(decision_request_id), checksum char(64) NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id, dna_type, entity_key, version_no)
);
CREATE TABLE IF NOT EXISTS dna_version_references (
  dna_version_reference_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), dna_version_id uuid NOT NULL REFERENCES dna_versions(dna_version_id), reference_kind text NOT NULL CHECK(reference_kind IN ('REFERENCE_IMAGE','APPROVED_ASSET_VERSION','VOICE_REFERENCE','COLOR_PALETTE','COSTUME_VERSION','EXPRESSION_SET','POSE_REFERENCE','NEGATIVE_REFERENCE')),
  reference_id text NOT NULL, checksum char(64) NULL, approved boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS chapter_versions (
  chapter_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), chapter_number integer NOT NULL CHECK(chapter_number > 0), version_no integer NOT NULL CHECK(version_no > 0),
  content jsonb NOT NULL, estimated_duration_seconds integer NULL CHECK(estimated_duration_seconds > 0), production_complexity text NOT NULL, status text NOT NULL CHECK(status IN ('CANDIDATE','ADOPTED','LOCKED','SUPERSEDED')), created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id, chapter_number, version_no)
);
CREATE TABLE IF NOT EXISTS chapter_topic_links (
  chapter_topic_link_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), chapter_version_id uuid NOT NULL REFERENCES chapter_versions(chapter_version_id), topic_id uuid NOT NULL REFERENCES topics(topic_id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(chapter_version_id, topic_id)
);
CREATE TABLE IF NOT EXISTS provider_prompt_profiles (
  provider_prompt_profile_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider_key text NOT NULL, model_key text NOT NULL, adapter_version text NOT NULL,
  capability_profile jsonb NOT NULL, forbidden_fields jsonb NOT NULL DEFAULT '[]'::jsonb, api_schema_ref text NOT NULL, active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(provider_key, model_key, adapter_version)
);
CREATE TABLE IF NOT EXISTS provider_compiled_prompts (
  provider_compiled_prompt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), instruction_package_id uuid NOT NULL REFERENCES instruction_packages(instruction_package_id), canonical_instruction_id uuid NOT NULL,
  provider_prompt_profile_id uuid NOT NULL REFERENCES provider_prompt_profiles(provider_prompt_profile_id), provider_id text NOT NULL, model_id text NOT NULL, provider_compiler_version text NOT NULL,
  source_script_version text NOT NULL, compiled_prompt jsonb NOT NULL, compiled_prompt_hash char(64) NOT NULL, api_request_hash char(64) NOT NULL, status text NOT NULL CHECK(status IN ('CANDIDATE','APPROVED_FOR_EXECUTION','SUPERSEDED','REJECTED')), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(instruction_package_id, provider_id, model_id, provider_compiler_version, compiled_prompt_hash)
);
CREATE TABLE IF NOT EXISTS correction_script_versions (
  correction_script_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), correction_request_id uuid NOT NULL REFERENCES correction_requests(correction_request_id), target_department text NOT NULL CHECK(target_department IN ('ASSET','VIDEO','EDITING','VOICE')),
  source_blueprint_version_id uuid NOT NULL REFERENCES blueprint_versions(blueprint_version_id), source_instruction_package_id uuid NOT NULL REFERENCES instruction_packages(instruction_package_id), failed_output_id uuid NOT NULL REFERENCES task_outputs(output_version_id), provider_job_id uuid NULL REFERENCES provider_jobs(provider_job_id),
  root_cause jsonb NOT NULL, correction_instruction jsonb NOT NULL, status text NOT NULL CHECK(status IN ('CANDIDATE','HUMAN_REVIEW','APPROVED','SUPERSEDED')), created_by_subject_type text NOT NULL CHECK(created_by_subject_type IN ('USER','SERVICE_IDENTITY')), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS voice_runtime_profiles (
  voice_runtime_profile_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), dna_version_id uuid NOT NULL REFERENCES dna_versions(dna_version_id), voice_profile jsonb NOT NULL, emotion text NOT NULL, emotion_ratio numeric(5,2) NOT NULL CHECK(emotion_ratio BETWEEN 0 AND 100), speed numeric(6,3) NOT NULL, pitch numeric(6,3) NOT NULL, pause_profile jsonb NOT NULL, intensity numeric(6,3) NOT NULL, accent text NULL, timing jsonb NOT NULL, sentence_alignment jsonb NOT NULL, version_no integer NOT NULL CHECK(version_no > 0), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS editing_runtime_runs (
  editing_runtime_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), task_id uuid NOT NULL REFERENCES department_tasks(task_id), state text NOT NULL CHECK(state IN ('ASSEMBLY','AUDIO_MIX','LIP_SYNC','SUBTITLE','QA_READY','FAILED','SUPERSEDED')),
  sequence_no smallint NOT NULL CHECK(sequence_no BETWEEN 1 AND 5), timeline_id uuid NULL REFERENCES editing_timelines(editing_timeline_id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(task_id, sequence_no)
);
CREATE TABLE IF NOT EXISTS conversations (
  conversation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), project_id uuid NULL REFERENCES projects(project_id), topic_id uuid NULL REFERENCES topics(topic_id), title text NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS conversation_messages (
  conversation_message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), conversation_id uuid NOT NULL REFERENCES conversations(conversation_id), sequence_no integer NOT NULL CHECK(sequence_no > 0), actor_type text NOT NULL CHECK(actor_type IN ('USER','SERVICE_IDENTITY')), actor_ref text NOT NULL, message_content jsonb NOT NULL, decision_request_id uuid NULL REFERENCES decision_requests(decision_request_id), blueprint_version_id uuid NULL REFERENCES blueprint_versions(blueprint_version_id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(conversation_id, sequence_no)
);
CREATE TABLE IF NOT EXISTS meetings (
  meeting_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), project_id uuid NULL REFERENCES projects(project_id), topic_id uuid NULL REFERENCES topics(topic_id), title text NOT NULL, status text NOT NULL CHECK(status IN ('SCHEDULED','RUNNING','COMPLETED','CANCELLED')), created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS meeting_participants (
  meeting_participant_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), subject_type text NOT NULL CHECK(subject_type IN ('USER','SERVICE_IDENTITY')), subject_ref text NOT NULL, participant_perspective text NOT NULL, UNIQUE(meeting_id, subject_type, subject_ref)
);
CREATE TABLE IF NOT EXISTS meeting_messages (
  meeting_message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), sequence_no integer NOT NULL CHECK(sequence_no > 0), participant_id uuid NOT NULL REFERENCES meeting_participants(meeting_participant_id), content jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(meeting_id, sequence_no)
);
CREATE TABLE IF NOT EXISTS meeting_summaries (
  meeting_summary_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), version_no integer NOT NULL CHECK(version_no > 0), summary jsonb NOT NULL, decision_links jsonb NOT NULL DEFAULT '[]'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(meeting_id, version_no)
);
CREATE TABLE IF NOT EXISTS notebooks (
  notebook_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), project_id uuid NULL REFERENCES projects(project_id), topic_id uuid NULL REFERENCES topics(topic_id), title text NOT NULL, owner_id uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS notebook_entries (
  notebook_entry_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), notebook_id uuid NOT NULL REFERENCES notebooks(notebook_id), version_no integer NOT NULL CHECK(version_no > 0), content jsonb NOT NULL, decision_request_id uuid NULL REFERENCES decision_requests(decision_request_id), blueprint_version_id uuid NULL REFERENCES blueprint_versions(blueprint_version_id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(notebook_id, version_no)
);
CREATE TABLE IF NOT EXISTS conversation_versions (
  conversation_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), conversation_id uuid NOT NULL REFERENCES conversations(conversation_id), version_no integer NOT NULL CHECK(version_no > 0), snapshot jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(conversation_id, version_no)
);
CREATE TABLE IF NOT EXISTS meeting_versions (
  meeting_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), version_no integer NOT NULL CHECK(version_no > 0), snapshot jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(meeting_id, version_no)
);
-- Direct lineage amendment. The nullable period supports migration; write guards make values mandatory for new effectful records.
ALTER TABLE work_packages ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS output_contract_hash char(64), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE department_tasks ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS output_contract_hash char(64), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE provider_jobs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS output_contract_hash char(64), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE task_outputs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE scorecards ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE handoffs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE qa_review_runs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE release_packages ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE publish_requests ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0004_r9_finalization', 'cf0b7c88be4e676081190d6862bf08d9374785bae34ec88c4507e5cdd0428662', 'migration-runner', 'CR-R9-0004')
ON CONFLICT (migration_id) DO NOTHING;
