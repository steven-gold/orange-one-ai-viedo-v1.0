-- ACPOS R9 Deployment Ready closure migration
-- Adds columns skipped by CREATE TABLE IF NOT EXISTS on clean install and removes retired/conflicting fields.
BEGIN;

-- Upgrade safety gate. R9 deployment policy does not preserve legacy pre-closure rows.
-- Adding the required NOT NULL columns below to populated pre-closure tables would otherwise
-- fail unpredictably or force fabricated backfill values. Fail early with a stable code instead.
DO $$
DECLARE
  t text;
  has_rows boolean;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'story_core_versions','story_candidates','world_bible_versions','world_canon_rules','chapter_versions',
    'provider_compiled_prompts','correction_script_versions','voice_runtime_profiles','candidate_blocks',
    'candidate_patches','continuity_ledger_entries','continuity_snapshots','document_layers','asset_patches',
    'video_timecode_patches'
  ]
  LOOP
    EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I LIMIT 1)', t) INTO has_rows;
    IF has_rows THEN
      RAISE EXCEPTION 'ACPOS_R9_LEGACY_DATA_CLEANUP_REQUIRED:%', t
        USING ERRCODE = 'P0001',
              HINT = 'Export/archive or remove legacy rows before applying 0006. R9 deployment-ready schema does not fabricate mandatory canonical values.';
    END IF;
  END LOOP;
END $$;

ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS title text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS logline text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS premise text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS core_conflict text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS theme text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS emotional_core text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS audience_promise text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS story_goal text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS main_hook text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS tone text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS genre text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS narrative_style text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS ending_direction text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS forbidden_direction text NOT NULL;
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS source_candidate_id uuid NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS wizard_session_id uuid NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS strengths jsonb NOT NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS weaknesses jsonb NOT NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS market_positioning text NOT NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS character_space text NOT NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS long_form_extension text NOT NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS foreshadowing_capacity text NOT NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS production_cost text NOT NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS production_risk text NOT NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS recommendation text NOT NULL;
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS generated_by_subject_type text NOT NULL CHECK(generated_by_subject_type IN ('USER','SERVICE_IDENTITY'));
ALTER TABLE story_candidate_comparisons ADD COLUMN IF NOT EXISTS human_decision text NULL CHECK(human_decision IN ('ADOPT','MERGE','REQUEST_REVISION','REJECT'));
ALTER TABLE story_candidate_comparisons ADD COLUMN IF NOT EXISTS decided_by uuid NULL;
ALTER TABLE story_candidate_comparisons ADD COLUMN IF NOT EXISTS decided_at timestamptz NULL;
ALTER TABLE story_candidate_comparisons ADD COLUMN IF NOT EXISTS audit_event_id uuid NULL;
ALTER TABLE world_bible_versions ADD COLUMN IF NOT EXISTS world_name text NOT NULL;
ALTER TABLE world_canon_rules ADD COLUMN IF NOT EXISTS enforcement text NOT NULL CHECK(enforcement IN ('INSTRUCTION_PACKAGE_REQUIRED','VARIATION_RATIONALE_REQUIRED'));
ALTER TABLE dna_versions ADD COLUMN IF NOT EXISTS parent_dna_version_id uuid NULL;
ALTER TABLE dna_versions ADD COLUMN IF NOT EXISTS lock_decision_request_id uuid NULL;
ALTER TABLE dna_version_references ADD COLUMN IF NOT EXISTS checksum char(64) NULL;
ALTER TABLE chapter_versions ADD COLUMN IF NOT EXISTS estimated_duration_seconds integer NULL CHECK(estimated_duration_seconds > 0);
ALTER TABLE chapter_versions ADD COLUMN IF NOT EXISTS production_complexity text NOT NULL;
ALTER TABLE provider_prompt_profiles ADD COLUMN IF NOT EXISTS forbidden_fields jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE provider_prompt_profiles ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS canonical_instruction_id uuid NOT NULL;
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS provider_id text NOT NULL;
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS model_id text NOT NULL;
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS provider_compiler_version text NOT NULL;
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS source_script_version text NOT NULL;
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS api_request_hash char(64) NOT NULL;
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS status text NOT NULL CHECK(status IN ('CANDIDATE','APPROVED_FOR_EXECUTION','SUPERSEDED','REJECTED'));
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS target_department text NOT NULL CHECK(target_department IN ('ASSET','VIDEO','EDITING','VOICE'));
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS source_blueprint_version_id uuid NOT NULL;
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS source_instruction_package_id uuid NOT NULL;
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS provider_job_id uuid NULL;
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS root_cause jsonb NOT NULL;
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS created_by_subject_type text NOT NULL CHECK(created_by_subject_type IN ('USER','SERVICE_IDENTITY'));
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS emotion text NOT NULL;
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS emotion_ratio numeric(5,2) NOT NULL CHECK(emotion_ratio BETWEEN 0 AND 100);
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS speed numeric(6,3) NOT NULL;
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS pitch numeric(6,3) NOT NULL;
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS pause_profile jsonb NOT NULL;
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS intensity numeric(6,3) NOT NULL;
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS accent text NULL;
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS timing jsonb NOT NULL;
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS sentence_alignment jsonb NOT NULL;
ALTER TABLE editing_runtime_runs ADD COLUMN IF NOT EXISTS timeline_id uuid NULL;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS decision_request_id uuid NULL;
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS blueprint_version_id uuid NULL;
ALTER TABLE meeting_summaries ADD COLUMN IF NOT EXISTS decision_links jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE notebooks ADD COLUMN IF NOT EXISTS project_id uuid NULL;
ALTER TABLE notebooks ADD COLUMN IF NOT EXISTS topic_id uuid NULL;
ALTER TABLE notebook_entries ADD COLUMN IF NOT EXISTS decision_request_id uuid NULL;
ALTER TABLE notebook_entries ADD COLUMN IF NOT EXISTS blueprint_version_id uuid NULL;
ALTER TABLE candidate_blocks ADD COLUMN IF NOT EXISTS parent_block_id text NULL;
ALTER TABLE candidate_blocks ADD COLUMN IF NOT EXISTS block_type text NOT NULL;
ALTER TABLE candidate_blocks ADD COLUMN IF NOT EXISTS ordinal integer NOT NULL;
ALTER TABLE candidate_patches ADD COLUMN IF NOT EXISTS preserve_other_blocks boolean NOT NULL DEFAULT true;
ALTER TABLE candidate_patches ADD COLUMN IF NOT EXISTS created_by_subject_type text NOT NULL CHECK(created_by_subject_type IN ('USER','SERVICE_IDENTITY'));
ALTER TABLE candidate_patch_sets ADD COLUMN IF NOT EXISTS selected_patch_ids jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE candidate_patch_sets ADD COLUMN IF NOT EXISTS resulting_candidate_version_ref text NULL;
ALTER TABLE continuity_ledger_entries ADD COLUMN IF NOT EXISTS subject_ref text NULL;
ALTER TABLE continuity_ledger_entries ADD COLUMN IF NOT EXISTS source_episode_chapter_scene_ref text NOT NULL;
ALTER TABLE continuity_ledger_entries ADD COLUMN IF NOT EXISTS effective_from_ref text NOT NULL;
ALTER TABLE continuity_ledger_entries ADD COLUMN IF NOT EXISTS superseded_by_ref text NULL;
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS message_range jsonb NOT NULL;
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS confirmed_items jsonb NOT NULL;
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS unresolved_issues jsonb NOT NULL;
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS canon_refs jsonb NOT NULL;
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS candidate_state jsonb NOT NULL;
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS revision_requirements jsonb NOT NULL;
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS forbidden_changes jsonb NOT NULL;
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS decision_refs jsonb NOT NULL;
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS todo_refs jsonb NOT NULL;
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS reference_refs jsonb NOT NULL;
ALTER TABLE execution_bundles ADD COLUMN IF NOT EXISTS completed_at timestamptz NULL;
ALTER TABLE execution_bundle_steps ADD COLUMN IF NOT EXISTS result_ref text NULL;
ALTER TABLE execution_bundle_steps ADD COLUMN IF NOT EXISTS started_at timestamptz NULL;
ALTER TABLE execution_bundle_steps ADD COLUMN IF NOT EXISTS completed_at timestamptz NULL;
ALTER TABLE provider_candidate_groups ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE provider_route_preflights ADD COLUMN IF NOT EXISTS requested_provider text NULL;
ALTER TABLE provider_route_preflights ADD COLUMN IF NOT EXISTS requested_model text NULL;
ALTER TABLE provider_route_preflights ADD COLUMN IF NOT EXISTS actual_provider text NULL;
ALTER TABLE provider_route_preflights ADD COLUMN IF NOT EXISTS actual_model text NULL;
ALTER TABLE provider_quarantines ADD COLUMN IF NOT EXISTS cleared_at timestamptz NULL;
ALTER TABLE multi_ai_context_snapshots ADD COLUMN IF NOT EXISTS immutable boolean NOT NULL DEFAULT true;
ALTER TABLE meeting_rounds ADD COLUMN IF NOT EXISTS peer_visibility_allowed boolean NOT NULL DEFAULT false;
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS parent_layer_id text NULL;
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS z_index integer NOT NULL;
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS visible boolean NOT NULL DEFAULT true;
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS locked boolean NOT NULL DEFAULT false;
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS opacity numeric(5,2) NOT NULL DEFAULT 100 CHECK(opacity BETWEEN 0 AND 100);
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS blend_mode text NOT NULL DEFAULT 'NORMAL';
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS transform jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS mask_ref jsonb NULL;
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS source_ref jsonb NOT NULL;
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS semantic_region text NOT NULL;
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS mask_ref jsonb NOT NULL;
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS preserve_regions jsonb NOT NULL;
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS revision_instruction jsonb NOT NULL;
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS provider_compiled_prompt_id uuid NULL;
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS continuity_validation jsonb NOT NULL;
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS rights_validation jsonb NOT NULL;
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS resulting_asset_version_id uuid NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS track_id text NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS clip_id text NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS shot_id text NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS layer_id text NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS scope_type text NOT NULL CHECK(scope_type IN ('SINGLE_FRAME','FRAME_RANGE','SHOT_RANGE','CLIP_RANGE'));
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS start_timecode text NOT NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS end_timecode text NOT NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS frame_start integer NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS frame_end integer NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS fps numeric(8,3) NOT NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS region_mask_ref jsonb NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS minimum_impact_plan jsonb NOT NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS blueprint_validation jsonb NOT NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS dna_validation jsonb NOT NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS rights_validation jsonb NOT NULL;
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS continuity_validation jsonb NOT NULL;
ALTER TABLE IF EXISTS world_bible_versions DROP COLUMN IF EXISTS production_type;
ALTER TABLE IF EXISTS meeting_participants DROP COLUMN IF EXISTS participant_role;
COMMIT;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0006_deployment_ready_closure', '98eff12b6216c3865d4da33771fa263ad35e60df8753039065958b60ab16d873', 'migration-runner', 'CR-R9-0006')
ON CONFLICT (migration_id) DO NOTHING;
