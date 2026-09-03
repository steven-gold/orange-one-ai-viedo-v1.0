-- ACPOS R9 Final Correction: collaboration, continuity, controlled execution, fixed provider routing and versioned regional patching.
CREATE TABLE IF NOT EXISTS candidate_blocks (
  candidate_block_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), candidate_type text NOT NULL CHECK(candidate_type IN ('STORY','CHAPTER','BLUEPRINT','SCRIPT')), candidate_version_ref text NOT NULL, block_id text NOT NULL, parent_block_id text NULL, block_type text NOT NULL, ordinal integer NOT NULL, content jsonb NOT NULL, checksum char(64) NOT NULL, UNIQUE(project_id, candidate_type, candidate_version_ref, block_id)
);
CREATE TABLE IF NOT EXISTS candidate_patches (
  candidate_patch_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), candidate_block_id uuid NOT NULL REFERENCES candidate_blocks(candidate_block_id), base_candidate_version_ref text NOT NULL, replacement_content jsonb NOT NULL, rationale text NOT NULL, preserve_other_blocks boolean NOT NULL DEFAULT true, blueprint_impact jsonb NOT NULL, continuity_check jsonb NOT NULL, status text NOT NULL CHECK(status IN ('CANDIDATE','ACCEPTED','REJECTED','REVISE_REQUIRED','BLOCKED')), created_by_subject_type text NOT NULL CHECK(created_by_subject_type IN ('USER','SERVICE_IDENTITY')), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS candidate_patch_sets (
  candidate_patch_set_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), base_candidate_version_ref text NOT NULL, status text NOT NULL CHECK(status IN ('DRAFT','PARTIAL_DECISION','APPLIED','REJECTED','BLOCKED')), selected_patch_ids jsonb NOT NULL DEFAULT '[]'::jsonb, resulting_candidate_version_ref text NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS candidate_patch_set_items (
  candidate_patch_set_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), candidate_patch_set_id uuid NOT NULL REFERENCES candidate_patch_sets(candidate_patch_set_id), candidate_patch_id uuid NOT NULL REFERENCES candidate_patches(candidate_patch_id), decision text NULL CHECK(decision IN ('ACCEPT','REJECT','REVISE')), UNIQUE(candidate_patch_set_id, candidate_patch_id)
);
CREATE TABLE IF NOT EXISTS continuity_ledger_entries (
  continuity_ledger_entry_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), entry_type text NOT NULL CHECK(entry_type IN ('STORY_EVENT','CHARACTER_STATE','CHARACTER_KNOWLEDGE','RELATIONSHIP_STATE','OBJECT_STATE','LOCATION_STATE','FORESHADOWING','PAYOFF','OPEN_THREAD','AUDIENCE_PROMISE','CANON_CHANGE')), subject_ref text NULL, payload jsonb NOT NULL, source_episode_chapter_scene_ref text NOT NULL, source_version_ref text NOT NULL, effective_from_ref text NOT NULL, superseded_by_ref text NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS continuity_snapshots (
  continuity_snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), conversation_id uuid NULL REFERENCES conversations(conversation_id), project_id uuid NULL REFERENCES projects(project_id), message_range jsonb NOT NULL, confirmed_items jsonb NOT NULL, unresolved_issues jsonb NOT NULL, canon_refs jsonb NOT NULL, candidate_state jsonb NOT NULL, revision_requirements jsonb NOT NULL, forbidden_changes jsonb NOT NULL, decision_refs jsonb NOT NULL, todo_refs jsonb NOT NULL, reference_refs jsonb NOT NULL, snapshot_hash char(64) NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS execution_bundles (
  execution_bundle_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), change_candidate_ref text NOT NULL, status text NOT NULL CHECK(status IN ('WAITING','PREPARING','RUNNING','VALIDATING','COMPLETED','FAILED','BLOCKED','CANCELLED')), required_layers jsonb NOT NULL, correlation_id uuid NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz NULL
);
CREATE TABLE IF NOT EXISTS execution_bundle_steps (
  execution_bundle_step_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), execution_bundle_id uuid NOT NULL REFERENCES execution_bundles(execution_bundle_id), step_key text NOT NULL, sequence_no smallint NOT NULL, status text NOT NULL CHECK(status IN ('NOT_STARTED','RUNNING','COMPLETED','FAILED','SKIPPED','BLOCKED')), result_ref text NULL, started_at timestamptz NULL, completed_at timestamptz NULL, UNIQUE(execution_bundle_id, step_key), UNIQUE(execution_bundle_id, sequence_no)
);
CREATE TABLE IF NOT EXISTS execution_logs (
  execution_log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), execution_bundle_id uuid NOT NULL REFERENCES execution_bundles(execution_bundle_id), execution_bundle_step_id uuid NULL REFERENCES execution_bundle_steps(execution_bundle_step_id), page_no integer NOT NULL DEFAULT 1 CHECK(page_no > 0), log_level text NOT NULL CHECK(log_level IN ('INFO','WARNING','ERROR')), content text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS provider_candidate_groups (
  provider_candidate_group_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), group_key text NOT NULL UNIQUE, purpose text NOT NULL, allowed_scope jsonb NOT NULL, active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS provider_candidate_members (
  provider_candidate_member_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider_candidate_group_id uuid NOT NULL REFERENCES provider_candidate_groups(provider_candidate_group_id), provider_prompt_profile_id uuid NOT NULL REFERENCES provider_prompt_profiles(provider_prompt_profile_id), rank_policy jsonb NOT NULL, enabled boolean NOT NULL DEFAULT true, UNIQUE(provider_candidate_group_id, provider_prompt_profile_id)
);
CREATE TABLE IF NOT EXISTS provider_route_preflights (
  provider_route_preflight_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider_candidate_group_id uuid NOT NULL REFERENCES provider_candidate_groups(provider_candidate_group_id), requested_provider text NULL, requested_model text NULL, actual_provider text NULL, actual_model text NULL, status text NOT NULL CHECK(status IN ('READY','WARNING','BLOCKED')), checks jsonb NOT NULL, waste_guard jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS provider_quality_observations (
  provider_quality_observation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider_candidate_member_id uuid NOT NULL REFERENCES provider_candidate_members(provider_candidate_member_id), task_class text NOT NULL, result_status text NOT NULL CHECK(result_status IN ('VALID','INVALID_RESULT','EMPTY','SCHEMA_FAILURE','SEVERE_DRIFT')), evidence jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS provider_quarantines (
  provider_quarantine_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider_candidate_member_id uuid NOT NULL REFERENCES provider_candidate_members(provider_candidate_member_id), reason text NOT NULL, status text NOT NULL CHECK(status IN ('ACTIVE','RECHECK_REQUIRED','SANDBOX_REQUIRED','HUMAN_RESTORE_REQUIRED','CLEARED')), imposed_at timestamptz NOT NULL DEFAULT now(), cleared_at timestamptz NULL
);
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_version integer NOT NULL DEFAULT 1, ADD COLUMN IF NOT EXISTS agenda jsonb NOT NULL DEFAULT '{}'::jsonb, ADD COLUMN IF NOT EXISTS context_snapshot_id uuid NULL, ADD COLUMN IF NOT EXISTS candidate_group_ref text NULL, ADD COLUMN IF NOT EXISTS route_mode text NOT NULL DEFAULT 'SINGLE' CHECK(route_mode IN ('SINGLE','MULTI_AI'));
CREATE TABLE IF NOT EXISTS multi_ai_context_snapshots (
  context_snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), version_no integer NOT NULL CHECK(version_no > 0), context_payload jsonb NOT NULL, context_snapshot_hash char(64) NOT NULL, immutable boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(meeting_id, version_no), UNIQUE(context_snapshot_hash)
);
ALTER TABLE meetings ADD CONSTRAINT fk_meetings_context_snapshot FOREIGN KEY(context_snapshot_id) REFERENCES multi_ai_context_snapshots(context_snapshot_id);
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'meeting_participants' AND column_name = 'participant_role') THEN
    ALTER TABLE meeting_participants RENAME COLUMN participant_role TO meeting_function;
  END IF;
END $$;
ALTER TABLE meeting_participants ADD COLUMN IF NOT EXISTS participant_perspective text NULL, ADD COLUMN IF NOT EXISTS requested_provider text NULL, ADD COLUMN IF NOT EXISTS requested_model text NULL, ADD COLUMN IF NOT EXISTS actual_provider text NULL, ADD COLUMN IF NOT EXISTS actual_model text NULL, ADD COLUMN IF NOT EXISTS allow_substitution boolean NOT NULL DEFAULT false, ADD COLUMN IF NOT EXISTS substitution_trace jsonb NOT NULL DEFAULT '{}'::jsonb;
COMMENT ON COLUMN meeting_participants.meeting_function IS 'NON_AUTHORIZATION_METADATA: meeting function/perspective only; never an Authorization Role.';
CREATE TABLE IF NOT EXISTS meeting_rounds (
  meeting_round_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), round_no integer NOT NULL CHECK(round_no > 0), mode text NOT NULL CHECK(mode IN ('INDEPENDENT','CROSS_COMPARE','CROSS_DISCUSSION')), status text NOT NULL CHECK(status IN ('PREPARING','RUNNING','COLLECTED','COMPARED','CLOSED','FAILED')), context_snapshot_id uuid NOT NULL REFERENCES multi_ai_context_snapshots(context_snapshot_id), peer_visibility_allowed boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(meeting_id, round_no)
);
CREATE TABLE IF NOT EXISTS versioned_layer_documents (
  layer_document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), topic_id uuid NULL REFERENCES topics(topic_id), asset_version_id uuid NULL REFERENCES asset_versions(asset_version_id), version_no integer NOT NULL CHECK(version_no > 0), checksum char(64) NOT NULL, status text NOT NULL CHECK(status IN ('DRAFT','APPROVED','SUPERSEDED')), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id, topic_id, asset_version_id, version_no)
);
CREATE TABLE IF NOT EXISTS document_layers (
  document_layer_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), layer_document_id uuid NOT NULL REFERENCES versioned_layer_documents(layer_document_id), layer_id text NOT NULL, layer_type text NOT NULL CHECK(layer_type IN ('BACKGROUND','CHARACTER_BODY','FACE','EYES','HAIR','COSTUME','FOREGROUND','EFFECT','TEXT','LOGICAL','SEMANTIC')), semantic_target text NOT NULL, parent_layer_id text NULL, z_index integer NOT NULL, asset_version_id uuid NULL REFERENCES asset_versions(asset_version_id), dna_version_id uuid NULL REFERENCES dna_versions(dna_version_id), blueprint_version_id uuid NULL REFERENCES blueprint_versions(blueprint_version_id), visible boolean NOT NULL DEFAULT true, locked boolean NOT NULL DEFAULT false, opacity numeric(5,2) NOT NULL DEFAULT 100 CHECK(opacity BETWEEN 0 AND 100), blend_mode text NOT NULL DEFAULT 'NORMAL', transform jsonb NOT NULL DEFAULT '{}'::jsonb, mask_ref jsonb NULL, source_ref jsonb NOT NULL, checksum char(64) NOT NULL, version_no integer NOT NULL, UNIQUE(layer_document_id, layer_id, version_no)
);
CREATE TABLE IF NOT EXISTS asset_patches (
  asset_patch_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_asset_version_id uuid NOT NULL REFERENCES asset_versions(asset_version_id), document_layer_id uuid NULL REFERENCES document_layers(document_layer_id), semantic_region text NOT NULL, mask_ref jsonb NOT NULL, preserve_regions jsonb NOT NULL, revision_instruction jsonb NOT NULL, provider_compiled_prompt_id uuid NULL REFERENCES provider_compiled_prompts(provider_compiled_prompt_id), blueprint_version_id uuid NOT NULL REFERENCES blueprint_versions(blueprint_version_id), dna_version_id uuid NOT NULL REFERENCES dna_versions(dna_version_id), continuity_validation jsonb NOT NULL, rights_validation jsonb NOT NULL, resulting_asset_version_id uuid NULL REFERENCES asset_versions(asset_version_id), status text NOT NULL CHECK(status IN ('CANDIDATE','HUMAN_REVIEW','APPROVED','SUPERSEDED','BLOCKED')), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS video_timecode_patches (
  video_timecode_patch_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), task_id uuid NOT NULL REFERENCES department_tasks(task_id), timeline_id uuid NOT NULL REFERENCES editing_timelines(editing_timeline_id), track_id text NULL, clip_id text NULL, shot_id text NULL, layer_id text NULL, scope_type text NOT NULL CHECK(scope_type IN ('SINGLE_FRAME','FRAME_RANGE','SHOT_RANGE','CLIP_RANGE')), start_timecode text NOT NULL, end_timecode text NOT NULL, frame_start integer NULL, frame_end integer NULL, fps numeric(8,3) NOT NULL, region_mask_ref jsonb NULL, minimum_impact_plan jsonb NOT NULL, blueprint_validation jsonb NOT NULL, dna_validation jsonb NOT NULL, rights_validation jsonb NOT NULL, continuity_validation jsonb NOT NULL, resulting_output_id uuid NULL REFERENCES task_outputs(output_version_id), status text NOT NULL CHECK(status IN ('CANDIDATE','HUMAN_REVIEW','APPROVED','SUPERSEDED','BLOCKED')), created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0005_r9_final_correction', '524ed12ddc1e7718c71fba16f60a5cc191ef88ae36a62ad527250ccea866874b', 'migration-runner', 'CR-R9-0005')
ON CONFLICT (migration_id) DO NOTHING;
