-- Generated bootstrap migration. PostgreSQL 15+; run through the canonical migration runner.
-- This file embeds canonical_schema.sql to prevent a manual, external bootstrap step.
CREATE TABLE IF NOT EXISTS schema_migration_history (
  migration_id text PRIMARY KEY,
  checksum char(64) NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now(),
  applied_by text NOT NULL,
  approval_ref text NOT NULL
);

-- ACPOS Canonical Schema v3.0.0 (PostgreSQL 15+)
-- This schema is append-only/version-first. Runtime services must never overwrite immutable versions.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TYPE acpos_status AS ENUM ('DRAFT','CORE_MODELING','CORE_REVIEW','READY_FOR_MOTHER_REVIEW','MOTHER_LOCKED','CONTRACT_VALIDATING','CANON_CHECK','BLUEPRINT_DRAFT','BLUEPRINT_REVIEW','READY_FOR_CHILD_REVIEW','CHILD_LOCKED','COMPILED','COMPILE_REQUESTED','WAITING_DEPENDENCY','READY','ROUTING','RUNNING','CALLBACK_PENDING','CANDIDATE_OUTPUT','SCORE_PENDING','HANDOFF_READY','HANDED_OFF','IN_REVIEW','FINDING_OPEN','CORRECTION_REQUIRED','RECHECK','PASS','FAIL','PENDING_APPROVAL','PENDING_EXTERNAL','PUBLISHED','FAILED','WITHDRAWN','BLOCKED','REJECTED','APPROVED','SUPERSEDED','ARCHIVED');
CREATE TYPE decision_status AS ENUM ('CANDIDATE','COMPARISON','DECISION_PENDING','ACCEPTED','MODIFY_REQUESTED','REJECTED','APPROVED','SUPERSEDED');
CREATE TYPE classification_level AS ENUM ('PUBLIC','INTERNAL','RESTRICTED');
ALTER TYPE classification_level ADD VALUE IF NOT EXISTS 'RESTRICTED_FINANCE';
CREATE TYPE department_code AS ENUM ('CORE','ASSET','VIDEO','EDITING','QA','RELEASE','STRATEGY','SYSTEM');
CREATE TYPE lock_kind AS ENUM ('MOTHER','CHILD');
CREATE TYPE actor_type AS ENUM ('USER','SERVICE_IDENTITY','PROVIDER','SYSTEM');

CREATE TABLE workspaces (
  workspace_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_key text NOT NULL UNIQUE,
  name text NOT NULL, status acpos_status NOT NULL DEFAULT 'READY', data_classification classification_level NOT NULL DEFAULT 'INTERNAL',
  created_at timestamptz NOT NULL DEFAULT now(), created_by uuid NULL, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE app_users (
  user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), external_subject text NOT NULL UNIQUE, display_name text NOT NULL,
  email citext NOT NULL UNIQUE, status acpos_status NOT NULL DEFAULT 'READY', created_at timestamptz NOT NULL DEFAULT now(), disabled_at timestamptz NULL
);
CREATE TABLE projects (
  project_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id),
  project_code text NOT NULL, title text NOT NULL, owner_id uuid NOT NULL REFERENCES app_users(user_id), status acpos_status NOT NULL DEFAULT 'DRAFT',
  active_version_id uuid NULL, created_at timestamptz NOT NULL DEFAULT now(), archived_at timestamptz NULL,
  UNIQUE(workspace_id, project_code)
);
CREATE TABLE project_versions (
  project_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id),
  version_no integer NOT NULL CHECK(version_no > 0), status acpos_status NOT NULL DEFAULT 'DRAFT',
  story_core jsonb NOT NULL, world_rules jsonb NOT NULL DEFAULT '{}'::jsonb, character_dna jsonb NOT NULL DEFAULT '{}'::jsonb,
  core_rules jsonb NOT NULL DEFAULT '{}'::jsonb, rights_constraints jsonb NOT NULL DEFAULT '{}'::jsonb,
  source_version_id uuid NULL, content_hash char(64) NOT NULL UNIQUE, created_by uuid NOT NULL REFERENCES app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(), decision_reason text NULL, immutable_at timestamptz NULL,
  UNIQUE(project_id, version_no)
);
ALTER TABLE projects ADD CONSTRAINT projects_active_version_fk FOREIGN KEY(active_version_id) REFERENCES project_versions(project_version_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE project_references (
  project_reference_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_version_id uuid NOT NULL REFERENCES project_versions(project_version_id),
  reference_uri text NOT NULL, reference_version text NOT NULL, rights_profile_id uuid NULL, classification classification_level NOT NULL,
  checksum char(64) NOT NULL, included_scope jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_version_id, reference_uri, reference_version)
);

CREATE TABLE topics (
  topic_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), topic_code text NOT NULL,
  title text NOT NULL, mother_lock_id uuid NOT NULL, status acpos_status NOT NULL DEFAULT 'DRAFT', active_version_id uuid NULL,
  created_at timestamptz NOT NULL DEFAULT now(), archived_at timestamptz NULL, UNIQUE(project_id, topic_code)
);
CREATE TABLE topic_versions (
  topic_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), topic_id uuid NOT NULL REFERENCES topics(topic_id), version_no integer NOT NULL CHECK(version_no > 0),
  mother_project_version_id uuid NOT NULL REFERENCES project_versions(project_version_id), boundary jsonb NOT NULL, bridge jsonb NOT NULL,
  status acpos_status NOT NULL DEFAULT 'DRAFT', content_hash char(64) NOT NULL UNIQUE, source_version_id uuid NULL,
  created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), immutable_at timestamptz NULL,
  UNIQUE(topic_id, version_no)
);
ALTER TABLE topics ADD CONSTRAINT topics_active_version_fk FOREIGN KEY(active_version_id) REFERENCES topic_versions(topic_version_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE topic_production_contracts (
  topic_production_contract_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), topic_version_id uuid NOT NULL REFERENCES topic_versions(topic_version_id),
  contract_version integer NOT NULL CHECK(contract_version > 0), quality_profile_id uuid NULL, asset_strategy jsonb NOT NULL,
  participants jsonb NOT NULL DEFAULT '[]'::jsonb, status acpos_status NOT NULL DEFAULT 'DRAFT', contract_hash char(64) NOT NULL UNIQUE,
  created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), immutable_at timestamptz NULL,
  UNIQUE(topic_version_id, contract_version)
);
CREATE TABLE output_contracts (
  output_contract_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), schema_key text NOT NULL, schema_version text NOT NULL,
  media_spec jsonb NOT NULL, required_checks jsonb NOT NULL, content_hash char(64) NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(schema_key, schema_version, content_hash)
);
CREATE TABLE topic_production_goals (
  production_goal_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), topic_production_contract_id uuid NOT NULL REFERENCES topic_production_contracts(topic_production_contract_id),
  goal_key text NOT NULL, production_type text NOT NULL, quantity integer NOT NULL CHECK(quantity > 0), output_contract_id uuid NOT NULL REFERENCES output_contracts(output_contract_id),
  output_contract_hash char(64) NOT NULL, platform_targets jsonb NOT NULL DEFAULT '[]'::jsonb, asset_strategy jsonb NOT NULL DEFAULT '{}'::jsonb,
  acceptance_criteria_refs jsonb NOT NULL DEFAULT '[]'::jsonb, goal_status acpos_status NOT NULL DEFAULT 'DRAFT',
  UNIQUE(topic_production_contract_id, goal_key), UNIQUE(production_goal_id, output_contract_hash)
);
ALTER TABLE topic_production_goals ADD CONSTRAINT topic_production_goals_production_type_check CHECK(production_type IN ('COMIC','VIDEO','ASSET','AD_VIDEO','AD_ASSET','OTHER'));

CREATE TABLE master_blueprints (
  master_blueprint_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), blueprint_key text NOT NULL UNIQUE, version_no integer NOT NULL,
  schema jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'APPROVED', content_hash char(64) NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE topic_blueprints (
  topic_blueprint_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), topic_production_contract_id uuid NOT NULL REFERENCES topic_production_contracts(topic_production_contract_id),
  master_blueprint_id uuid NOT NULL REFERENCES master_blueprints(master_blueprint_id), active_version_id uuid NULL, status acpos_status NOT NULL DEFAULT 'BLUEPRINT_DRAFT', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE blueprint_versions (
  blueprint_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), topic_blueprint_id uuid NOT NULL REFERENCES topic_blueprints(topic_blueprint_id),
  version_no integer NOT NULL CHECK(version_no > 0), source_contract_hash char(64) NOT NULL, blueprint_document jsonb NOT NULL, validation_result jsonb NOT NULL DEFAULT '{}'::jsonb,
  status acpos_status NOT NULL DEFAULT 'BLUEPRINT_DRAFT', content_hash char(64) NOT NULL UNIQUE, created_by uuid NOT NULL REFERENCES app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(), frozen_at timestamptz NULL, UNIQUE(topic_blueprint_id, version_no)
);
ALTER TABLE topic_blueprints ADD CONSTRAINT topic_blueprints_active_version_fk FOREIGN KEY(active_version_id) REFERENCES blueprint_versions(blueprint_version_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE lock_reviews (
  lock_review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), lock_kind lock_kind NOT NULL, target_type text NOT NULL,
  target_version_id uuid NOT NULL, criteria_version_id uuid NULL, evidence jsonb NOT NULL, reviewer_path jsonb NOT NULL,
  status acpos_status NOT NULL DEFAULT 'IN_REVIEW', expected_target_hash char(64) NOT NULL, requested_by uuid NOT NULL REFERENCES app_users(user_id),
  decided_by uuid NULL REFERENCES app_users(user_id), decision_reason text NULL, created_at timestamptz NOT NULL DEFAULT now(), decided_at timestamptz NULL
);
CREATE TABLE mother_locks (
  mother_lock_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), project_version_id uuid NOT NULL REFERENCES project_versions(project_version_id),
  lock_review_id uuid NOT NULL UNIQUE REFERENCES lock_reviews(lock_review_id), lock_version integer NOT NULL, project_hash char(64) NOT NULL,
  status acpos_status NOT NULL DEFAULT 'MOTHER_LOCKED', locked_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id, lock_version), UNIQUE(project_id, project_version_id)
);
ALTER TABLE topics ADD CONSTRAINT topics_mother_lock_fk FOREIGN KEY(mother_lock_id) REFERENCES mother_locks(mother_lock_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE child_locks (
  child_lock_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), topic_id uuid NOT NULL REFERENCES topics(topic_id), topic_production_contract_id uuid NOT NULL REFERENCES topic_production_contracts(topic_production_contract_id),
  blueprint_version_id uuid NOT NULL REFERENCES blueprint_versions(blueprint_version_id), lock_review_id uuid NOT NULL UNIQUE REFERENCES lock_reviews(lock_review_id),
  lock_version integer NOT NULL, contract_hash char(64) NOT NULL, blueprint_hash char(64) NOT NULL, status acpos_status NOT NULL DEFAULT 'CHILD_LOCKED',
  locked_at timestamptz NOT NULL DEFAULT now(), UNIQUE(topic_id, lock_version), UNIQUE(topic_production_contract_id, blueprint_version_id)
);

CREATE TABLE canonical_script_versions (
  canonical_script_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), topic_id uuid NOT NULL REFERENCES topics(topic_id),
  source_topic_version_id uuid NOT NULL REFERENCES topic_versions(topic_version_id), version_no integer NOT NULL CHECK(version_no > 0), script_document jsonb NOT NULL,
  status acpos_status NOT NULL DEFAULT 'DRAFT', content_hash char(64) NOT NULL UNIQUE, created_by uuid NOT NULL REFERENCES app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(), immutable_at timestamptz NULL, UNIQUE(topic_id, version_no)
);
CREATE TABLE emotional_script_versions (
  emotional_script_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), canonical_script_version_id uuid NOT NULL REFERENCES canonical_script_versions(canonical_script_version_id),
  version_no integer NOT NULL, layer_document jsonb NOT NULL, content_hash char(64) NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(canonical_script_version_id, version_no)
);
CREATE TABLE script_projection_rules (
  script_projection_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), department department_code NOT NULL, rule_version text NOT NULL,
  included_paths jsonb NOT NULL, excluded_paths jsonb NOT NULL, transformation_spec jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'APPROVED',
  rule_hash char(64) NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(department, rule_version)
);
CREATE TABLE department_script_views (
  department_script_view_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), canonical_script_version_id uuid NOT NULL REFERENCES canonical_script_versions(canonical_script_version_id),
  emotional_script_version_id uuid NULL REFERENCES emotional_script_versions(emotional_script_version_id), script_projection_rule_id uuid NOT NULL REFERENCES script_projection_rules(script_projection_rule_id),
  department department_code NOT NULL, child_lock_id uuid NOT NULL REFERENCES child_locks(child_lock_id), view_document jsonb NOT NULL, included_refs jsonb NOT NULL,
  excluded_refs jsonb NOT NULL, view_hash char(64) NOT NULL UNIQUE, scope_authorization jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'COMPILED',
  created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(canonical_script_version_id, script_projection_rule_id, child_lock_id)
);

CREATE TABLE continuity_checkpoints (
  continuity_checkpoint_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), episode_range int4range NOT NULL,
  source_child_lock_id uuid NOT NULL REFERENCES child_locks(child_lock_id), canon_hash char(64) NOT NULL, checkpoint_document jsonb NOT NULL,
  content_hash char(64) NOT NULL UNIQUE, status acpos_status NOT NULL DEFAULT 'APPROVED', created_at timestamptz NOT NULL DEFAULT now(),
  EXCLUDE USING gist (project_id WITH =, episode_range WITH &&) WHERE (status IN ('APPROVED','CHILD_LOCKED'))
);
CREATE TABLE production_cursors (
  production_cursor_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id),
  topic_id uuid NOT NULL REFERENCES topics(topic_id), next_episode_no integer NOT NULL CHECK(next_episode_no > 0), source_checkpoint_id uuid NULL REFERENCES continuity_checkpoints(continuity_checkpoint_id),
  resume_state jsonb NOT NULL, cursor_hash char(64) NOT NULL UNIQUE, status acpos_status NOT NULL DEFAULT 'READY', updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id, topic_id)
);
CREATE TABLE dna_assets (
  dna_asset_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), dna_kind text NOT NULL,
  canonical_reference jsonb NOT NULL, rights_profile_id uuid NULL, content_hash char(64) NOT NULL UNIQUE, status acpos_status NOT NULL DEFAULT 'APPROVED', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE dna_resolutions (
  dna_resolution_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), child_lock_id uuid NOT NULL REFERENCES child_locks(child_lock_id), dna_asset_id uuid NOT NULL REFERENCES dna_assets(dna_asset_id),
  resolution_mode text NOT NULL CHECK(resolution_mode IN ('REUSE','GENERATE_CANDIDATE','APPROVE_NEW')), compatibility_result jsonb NOT NULL, dedupe_key char(64) NOT NULL,
  status acpos_status NOT NULL DEFAULT 'APPROVED', resolved_at timestamptz NOT NULL DEFAULT now(), UNIQUE(child_lock_id, dna_asset_id), UNIQUE(dedupe_key)
);

CREATE TABLE work_packages (
  work_package_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), child_lock_id uuid NOT NULL UNIQUE REFERENCES child_locks(child_lock_id),
  dag_snapshot_id uuid NULL, status acpos_status NOT NULL DEFAULT 'COMPILE_REQUESTED', input_snapshot jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE dag_snapshots (
  dag_snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), work_package_id uuid NOT NULL UNIQUE REFERENCES work_packages(work_package_id),
  child_lock_id uuid NOT NULL REFERENCES child_locks(child_lock_id), compiler_version text NOT NULL, goal_department_map_hash char(64) NOT NULL,
  snapshot_document jsonb NOT NULL, snapshot_hash char(64) NOT NULL UNIQUE, status acpos_status NOT NULL DEFAULT 'COMPILED', created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE work_packages ADD CONSTRAINT work_packages_dag_snapshot_fk FOREIGN KEY(dag_snapshot_id) REFERENCES dag_snapshots(dag_snapshot_id) DEFERRABLE INITIALLY DEFERRED;
CREATE TABLE task_templates (
  task_template_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), template_key text NOT NULL, department department_code NOT NULL, production_type text NOT NULL,
  template_version text NOT NULL, input_schema jsonb NOT NULL, output_schema jsonb NOT NULL, default_edge_gates jsonb NOT NULL, template_hash char(64) NOT NULL UNIQUE,
  status acpos_status NOT NULL DEFAULT 'APPROVED', UNIQUE(template_key, template_version)
);
CREATE TABLE dag_nodes (
  dag_node_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), dag_snapshot_id uuid NOT NULL REFERENCES dag_snapshots(dag_snapshot_id), production_goal_id uuid NOT NULL REFERENCES topic_production_goals(production_goal_id),
  task_template_id uuid NOT NULL REFERENCES task_templates(task_template_id), department department_code NOT NULL, node_key text NOT NULL, idempotency_key char(64) NOT NULL, node_contract jsonb NOT NULL,
  UNIQUE(dag_snapshot_id, node_key), UNIQUE(idempotency_key)
);
CREATE TABLE dag_edges (
  dag_edge_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), dag_snapshot_id uuid NOT NULL REFERENCES dag_snapshots(dag_snapshot_id),
  from_node_id uuid NOT NULL REFERENCES dag_nodes(dag_node_id), to_node_id uuid NOT NULL REFERENCES dag_nodes(dag_node_id), edge_gate jsonb NOT NULL, UNIQUE(dag_snapshot_id, from_node_id, to_node_id)
);
CREATE TABLE department_tasks (
  task_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), work_package_id uuid NOT NULL REFERENCES work_packages(work_package_id), dag_node_id uuid NOT NULL UNIQUE REFERENCES dag_nodes(dag_node_id),
  department department_code NOT NULL, production_goal_id uuid NOT NULL REFERENCES topic_production_goals(production_goal_id), child_lock_id uuid NOT NULL REFERENCES child_locks(child_lock_id),
  topic_production_contract_id uuid NOT NULL REFERENCES topic_production_contracts(topic_production_contract_id), output_contract_hash char(64) NOT NULL, expected_task_version integer NOT NULL DEFAULT 1,
  status acpos_status NOT NULL DEFAULT 'WAITING_DEPENDENCY', input_fingerprint char(64) NULL, assigned_owner_id uuid NULL REFERENCES app_users(user_id),
  created_at timestamptz NOT NULL DEFAULT now(), started_at timestamptz NULL, completed_at timestamptz NULL
);
CREATE TABLE task_input_manifests (
  task_input_manifest_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), task_id uuid NOT NULL UNIQUE REFERENCES department_tasks(task_id),
  department_script_view_id uuid NOT NULL REFERENCES department_script_views(department_script_view_id), input_refs jsonb NOT NULL, rights_profile_refs jsonb NOT NULL,
  criteria_version_id uuid NULL, manifest_hash char(64) NOT NULL UNIQUE, status acpos_status NOT NULL DEFAULT 'READY', created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE instruction_packages (
  instruction_package_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), task_id uuid NOT NULL REFERENCES department_tasks(task_id),
  task_input_manifest_id uuid NOT NULL REFERENCES task_input_manifests(task_input_manifest_id), compiler_version text NOT NULL, provider_neutral_intent jsonb NOT NULL,
  compiled_instruction jsonb NOT NULL, package_hash char(64) NOT NULL UNIQUE, status acpos_status NOT NULL DEFAULT 'COMPILED', approved_by uuid NULL REFERENCES app_users(user_id), approved_at timestamptz NULL,
  created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(task_id, package_hash)
);
CREATE TABLE instruction_package_checks (
  instruction_package_check_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), instruction_package_id uuid NOT NULL REFERENCES instruction_packages(instruction_package_id),
  check_key text NOT NULL, check_result boolean NOT NULL, evidence jsonb NOT NULL, executed_at timestamptz NOT NULL DEFAULT now(), UNIQUE(instruction_package_id, check_key)
);
CREATE TABLE provider_capabilities (
  provider_capability_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider_key text NOT NULL, model_key text NOT NULL, capability_version text NOT NULL,
  accepted_classifications classification_level[] NOT NULL, input_schema jsonb NOT NULL, output_schema jsonb NOT NULL, limits jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'APPROVED',
  capability_hash char(64) NOT NULL UNIQUE, UNIQUE(provider_key, model_key, capability_version)
);
CREATE TABLE route_policies (
  route_policy_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), intent_type text NOT NULL, department department_code NOT NULL, classification classification_level NOT NULL,
  provider_capability_id uuid NOT NULL REFERENCES provider_capabilities(provider_capability_id), fallback_policy jsonb NOT NULL, budget_policy jsonb NOT NULL,
  status acpos_status NOT NULL DEFAULT 'APPROVED', policy_hash char(64) NOT NULL UNIQUE, UNIQUE(intent_type, department, classification, status)
);
CREATE TABLE provider_jobs (
  provider_job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), task_id uuid NOT NULL REFERENCES department_tasks(task_id), instruction_package_id uuid NOT NULL REFERENCES instruction_packages(instruction_package_id),
  route_policy_id uuid NOT NULL REFERENCES route_policies(route_policy_id), idempotency_key char(64) NOT NULL UNIQUE, external_job_ref text NULL UNIQUE,
  status acpos_status NOT NULL DEFAULT 'ROUTING', requested_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz NULL
);
CREATE TABLE integration_attempts (
  integration_attempt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider_job_id uuid NOT NULL REFERENCES provider_jobs(provider_job_id),
  attempt_no integer NOT NULL CHECK(attempt_no > 0), request_fingerprint char(64) NOT NULL, response_summary jsonb NULL, error_code text NULL,
  retryable boolean NOT NULL DEFAULT false, status acpos_status NOT NULL, started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz NULL, UNIQUE(provider_job_id, attempt_no)
);
CREATE TABLE callback_receipts (
  callback_receipt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), provider_job_id uuid NOT NULL REFERENCES provider_jobs(provider_job_id),
  external_event_id text NOT NULL, signature_valid boolean NOT NULL, timestamp_valid boolean NOT NULL, replay_valid boolean NOT NULL, schema_valid boolean NOT NULL,
  payload_hash char(64) NOT NULL, received_at timestamptz NOT NULL DEFAULT now(), UNIQUE(provider_job_id, external_event_id)
);
CREATE TABLE task_outputs (
  output_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), task_id uuid NOT NULL REFERENCES department_tasks(task_id), provider_job_id uuid NULL REFERENCES provider_jobs(provider_job_id),
  production_goal_id uuid NOT NULL REFERENCES topic_production_goals(production_goal_id), output_contract_hash char(64) NOT NULL, output_uri text NOT NULL, artifact_checksum char(64) NOT NULL,
  provenance jsonb NOT NULL, status decision_status NOT NULL DEFAULT 'CANDIDATE', created_at timestamptz NOT NULL DEFAULT now(), immutable_at timestamptz NULL,
  UNIQUE(task_id, artifact_checksum)
);

CREATE TABLE quality_criteria_versions (
  criteria_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), criteria_key text NOT NULL, version_no integer NOT NULL, department department_code NULL,
  dimensions jsonb NOT NULL, required_checks jsonb NOT NULL, gate_policy jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'APPROVED', content_hash char(64) NOT NULL UNIQUE, UNIQUE(criteria_key, version_no)
);
CREATE TABLE scorecards (
  scorecard_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), output_version_id uuid NOT NULL REFERENCES task_outputs(output_version_id), criteria_version_id uuid NOT NULL REFERENCES quality_criteria_versions(criteria_version_id),
  task_id uuid NOT NULL REFERENCES department_tasks(task_id), production_goal_id uuid NOT NULL REFERENCES topic_production_goals(production_goal_id), output_contract_hash char(64) NOT NULL,
  dimensions jsonb NOT NULL, evidence_refs jsonb NOT NULL, total_score numeric(5,2) NOT NULL CHECK(total_score >= 0 AND total_score <= 100), gate_status acpos_status NOT NULL,
  scored_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(output_version_id, criteria_version_id)
);
CREATE TABLE findings (
  finding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), output_version_id uuid NOT NULL REFERENCES task_outputs(output_version_id), scorecard_id uuid NULL REFERENCES scorecards(scorecard_id),
  severity text NOT NULL CHECK(severity IN ('LOW','MEDIUM','HIGH','CRITICAL')), category text NOT NULL, affected_scope jsonb NOT NULL, evidence jsonb NOT NULL,
  status acpos_status NOT NULL DEFAULT 'FINDING_OPEN', created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), closed_at timestamptz NULL
);
CREATE TABLE correction_requests (
  correction_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), finding_id uuid NOT NULL REFERENCES findings(finding_id), source_output_version_id uuid NOT NULL REFERENCES task_outputs(output_version_id),
  source_instruction_package_id uuid NOT NULL REFERENCES instruction_packages(instruction_package_id), source_scorecard_id uuid NULL REFERENCES scorecards(scorecard_id),
  original_owner_task_id uuid NOT NULL REFERENCES department_tasks(task_id), affected_scope jsonb NOT NULL, revalidation_requirements jsonb NOT NULL,
  status acpos_status NOT NULL DEFAULT 'CORRECTION_REQUIRED', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE handoffs (
  handoff_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_task_id uuid NOT NULL REFERENCES department_tasks(task_id), target_task_id uuid NOT NULL REFERENCES department_tasks(task_id),
  source_output_version_id uuid NOT NULL REFERENCES task_outputs(output_version_id), scorecard_id uuid NOT NULL REFERENCES scorecards(scorecard_id),
  topic_production_contract_id uuid NOT NULL REFERENCES topic_production_contracts(topic_production_contract_id), production_goal_id uuid NOT NULL REFERENCES topic_production_goals(production_goal_id),
  output_contract_hash char(64) NOT NULL, rights_profile_id uuid NULL, status acpos_status NOT NULL DEFAULT 'HANDOFF_READY', created_at timestamptz NOT NULL DEFAULT now(),
  CHECK(source_task_id <> target_task_id), UNIQUE(source_task_id, target_task_id, source_output_version_id)
);
CREATE TABLE qa_review_runs (
  qa_review_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), qa_task_id uuid NOT NULL REFERENCES department_tasks(task_id), output_version_id uuid NOT NULL REFERENCES task_outputs(output_version_id),
  criteria_version_id uuid NOT NULL REFERENCES quality_criteria_versions(criteria_version_id), status acpos_status NOT NULL DEFAULT 'IN_REVIEW', decision_reason text NULL,
  reviewer_id uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), decided_at timestamptz NULL, UNIQUE(qa_task_id, output_version_id)
);
CREATE TABLE release_packages (
  release_package_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), qa_review_run_id uuid NOT NULL UNIQUE REFERENCES qa_review_runs(qa_review_run_id),
  output_version_id uuid NOT NULL REFERENCES task_outputs(output_version_id), rights_evidence jsonb NOT NULL, channel_policy_snapshot jsonb NOT NULL, approval_path jsonb NOT NULL,
  status acpos_status NOT NULL DEFAULT 'PENDING_APPROVAL', package_hash char(64) NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now(), approved_at timestamptz NULL
);
CREATE TABLE publish_requests (
  publish_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), release_package_id uuid NOT NULL REFERENCES release_packages(release_package_id),
  channel_account_id uuid NOT NULL, schedule_at timestamptz NULL, timezone text NOT NULL DEFAULT 'Asia/Taipei', metadata jsonb NOT NULL,
  idempotency_key char(64) NOT NULL UNIQUE, external_post_ref text NULL UNIQUE, status acpos_status NOT NULL DEFAULT 'PENDING_EXTERNAL', created_at timestamptz NOT NULL DEFAULT now(), published_at timestamptz NULL
);

CREATE TABLE permission_resources (resource_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), resource_key text NOT NULL UNIQUE, resource_type text NOT NULL CHECK(resource_type IN ('L1','L2','L3','PAGE','SECTION','CONTROL','ACTION','FIELD','API','DECISION')), parent_resource_key text NULL REFERENCES permission_resources(resource_key), classification classification_level NOT NULL DEFAULT 'INTERNAL', allowed_actions jsonb NOT NULL DEFAULT '[]'::jsonb, active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE account_permission_assignments (account_permission_assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES app_users(user_id), resource_id uuid NOT NULL REFERENCES permission_resources(resource_id), action text NOT NULL, effect text NOT NULL CHECK(effect IN ('ALLOW','DENY')), scope jsonb NOT NULL, condition jsonb NOT NULL DEFAULT '{}'::jsonb, gate_profile jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'DRAFT', granted_by_user_id uuid NOT NULL REFERENCES app_users(user_id), approval_ref text NOT NULL, version_no integer NOT NULL CHECK(version_no > 0), audit_event_id uuid NULL, effective_from timestamptz NOT NULL DEFAULT now(), effective_to timestamptz NULL, UNIQUE(user_id, resource_id, action, version_no));
CREATE TABLE service_identities (service_identity_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), service_identity_key text NOT NULL UNIQUE, owner_service text NOT NULL, status acpos_status NOT NULL DEFAULT 'DRAFT', created_at timestamptz NOT NULL DEFAULT now(), disabled_at timestamptz NULL);
CREATE TABLE service_identity_capability_assignments (service_capability_assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), service_identity_id uuid NOT NULL REFERENCES service_identities(service_identity_id), capability_key text NOT NULL, scope jsonb NOT NULL, condition jsonb NOT NULL DEFAULT '{}'::jsonb, gate_profile jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'DRAFT', approval_ref text NOT NULL, audit_event_id uuid NULL, UNIQUE(service_identity_id, capability_key, status));
CREATE TABLE decision_requests (decision_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), required_resource_id uuid NOT NULL REFERENCES permission_resources(resource_id), required_action text NOT NULL, required_scope jsonb NOT NULL, condition_snapshot jsonb NOT NULL, reason text NOT NULL, evidence_refs jsonb NOT NULL, impact_scope jsonb NOT NULL, state text NOT NULL CHECK(state IN ('OPEN','NOTIFIED','APPROVED','REJECTED','MODIFICATION_REQUESTED','CANCELLED')), correlation_id uuid NOT NULL, created_by_actor_type actor_type NOT NULL, created_by_user_id uuid NULL REFERENCES app_users(user_id), created_by_service_identity_id uuid NULL REFERENCES service_identities(service_identity_id), decided_by_user_id uuid NULL REFERENCES app_users(user_id), decision_reason text NULL, audit_event_id uuid NULL, created_at timestamptz NOT NULL DEFAULT now(), decided_at timestamptz NULL, CHECK ((created_by_user_id IS NOT NULL) <> (created_by_service_identity_id IS NOT NULL)));
CREATE TABLE audit_events (audit_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), action text NOT NULL, entity_type text NOT NULL, entity_id uuid NOT NULL, actor_id uuid NULL REFERENCES app_users(user_id), actor_type actor_type NOT NULL, workspace_id uuid NULL REFERENCES workspaces(workspace_id), before_version jsonb NULL, after_version jsonb NULL, reason text NULL, correlation_id uuid NOT NULL, causation_id uuid NULL, occurred_at timestamptz NOT NULL DEFAULT now(), payload_hash char(64) NOT NULL);
CREATE TABLE secret_references (
  secret_reference_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), secret_key text NOT NULL UNIQUE, owner_service text NOT NULL, provider_key text NULL,
  workspace_id uuid NULL REFERENCES workspaces(workspace_id), classification classification_level NOT NULL, rotation_due_at timestamptz NULL, status acpos_status NOT NULL DEFAULT 'APPROVED',
  last_used_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE channel_accounts (
  channel_account_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), platform_key text NOT NULL, external_account_ref text NOT NULL,
  workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), secret_reference_id uuid NULL REFERENCES secret_references(secret_reference_id), capability_snapshot jsonb NOT NULL,
  status acpos_status NOT NULL DEFAULT 'APPROVED', health jsonb NOT NULL DEFAULT '{}'::jsonb, UNIQUE(platform_key, external_account_ref, workspace_id)
);
CREATE TABLE knowledge_sources (
  knowledge_source_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_key text NOT NULL UNIQUE, source_uri text NOT NULL, collection_method text NOT NULL,
  rights_policy jsonb NOT NULL, classification classification_level NOT NULL, freshness_policy jsonb NOT NULL, retention_policy jsonb NOT NULL,
  status acpos_status NOT NULL DEFAULT 'DRAFT', approved_by uuid NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE evidence_records (
  evidence_record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), knowledge_source_id uuid NOT NULL REFERENCES knowledge_sources(knowledge_source_id),
  source_uri text NOT NULL, source_published_at timestamptz NULL, retrieved_at timestamptz NOT NULL, content_hash char(64) NOT NULL,
  classification classification_level NOT NULL, citation jsonb NOT NULL, normalized_content jsonb NOT NULL, UNIQUE(knowledge_source_id, content_hash)
);
CREATE TABLE fact_packs (
  fact_pack_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), scope jsonb NOT NULL,
  fact_document jsonb NOT NULL, evidence_refs jsonb NOT NULL, freshness_at timestamptz NOT NULL, completeness numeric(5,2) NOT NULL CHECK(completeness >= 0 AND completeness <= 100),
  confidence numeric(5,2) NOT NULL CHECK(confidence >= 0 AND confidence <= 100), classification classification_level NOT NULL, content_hash char(64) NOT NULL UNIQUE,
  status acpos_status NOT NULL DEFAULT 'APPROVED', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE context_candidates (
  context_candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), fact_pack_id uuid NOT NULL REFERENCES fact_packs(fact_pack_id), target_scope jsonb NOT NULL,
  candidate_document jsonb NOT NULL, decision_status decision_status NOT NULL DEFAULT 'CANDIDATE', created_by uuid NOT NULL REFERENCES app_users(user_id),
  decided_by uuid NULL REFERENCES app_users(user_id), decision_reason text NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE strategy_candidates (
  strategy_candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id),
  source_fact_pack_ids jsonb NOT NULL, strategy_document jsonb NOT NULL, citations jsonb NOT NULL, freshness_at timestamptz NOT NULL,
  confidence numeric(5,2) NOT NULL CHECK(confidence >= 0 AND confidence <= 100), decision_status decision_status NOT NULL DEFAULT 'CANDIDATE',
  created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE outbox_events (
  outbox_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), event_id uuid NOT NULL UNIQUE, event_type text NOT NULL, event_version integer NOT NULL,
  aggregate_type text NOT NULL, aggregate_id uuid NOT NULL, aggregate_version integer NOT NULL, correlation_id uuid NOT NULL, causation_id uuid NULL,
  actor_id uuid NULL REFERENCES app_users(user_id), payload jsonb NOT NULL, payload_hash char(64) NOT NULL, occurred_at timestamptz NOT NULL DEFAULT now(), published_at timestamptz NULL
);
CREATE TABLE inbox_events (
  inbox_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), consumer_name text NOT NULL, event_id uuid NOT NULL, processed_at timestamptz NOT NULL DEFAULT now(),
  result jsonb NOT NULL, UNIQUE(consumer_name, event_id)
);
CREATE TABLE dead_letters (
  dead_letter_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), event_id uuid NOT NULL, consumer_name text NOT NULL, failure_code text NOT NULL, payload_hash char(64) NOT NULL,
  retry_count integer NOT NULL DEFAULT 0, status acpos_status NOT NULL DEFAULT 'BLOCKED', created_at timestamptz NOT NULL DEFAULT now(), resolved_at timestamptz NULL
);
CREATE TABLE incidents (
  incident_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), severity text NOT NULL CHECK(severity IN ('LOW','MEDIUM','HIGH','CRITICAL')), title text NOT NULL,
  scope jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'READY', source_ref jsonb NOT NULL, owner_id uuid NULL REFERENCES app_users(user_id),
  mitigation jsonb NULL, created_at timestamptz NOT NULL DEFAULT now(), resolved_at timestamptz NULL
);
CREATE TABLE replay_candidates (
  replay_candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), dead_letter_id uuid NOT NULL REFERENCES dead_letters(dead_letter_id),
  impact_analysis jsonb NOT NULL, idempotency_assessment jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'PENDING_APPROVAL', requested_by uuid NOT NULL REFERENCES app_users(user_id),
  approved_by uuid NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE notifications (
  notification_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), recipient_user_id uuid NOT NULL REFERENCES app_users(user_id), notification_type text NOT NULL,
  aggregate_ref jsonb NOT NULL, payload jsonb NOT NULL, read_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_tasks_status_department ON department_tasks(status, department);
CREATE INDEX idx_outputs_task ON task_outputs(task_id, status);
CREATE INDEX idx_findings_open ON findings(status, severity) WHERE status IN ('FINDING_OPEN','CORRECTION_REQUIRED');
CREATE INDEX idx_audit_entity ON audit_events(entity_type, entity_id, occurred_at DESC);
CREATE INDEX idx_handoffs_target ON handoffs(target_task_id, status);
CREATE INDEX idx_outbox_unpublished ON outbox_events(occurred_at) WHERE published_at IS NULL;
CREATE INDEX idx_inbox_consumer_event ON inbox_events(consumer_name, event_id);
CREATE INDEX idx_fact_pack_scope ON fact_packs(workspace_id, freshness_at DESC);

-- R4 data-closure additions: every table named by the Unit Completion Matrix is a concrete owned relation.
CREATE TABLE project_memberships (
  project_membership_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(project_id), user_id uuid NOT NULL REFERENCES app_users(user_id),
  collaboration_label text NOT NULL, scope jsonb NOT NULL DEFAULT '{}'::jsonb, status acpos_status NOT NULL DEFAULT 'APPROVED', invited_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_id, user_id, collaboration_label)
);
CREATE TABLE approval_records (
  approval_record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), aggregate_type text NOT NULL, aggregate_id uuid NOT NULL, aggregate_version integer NOT NULL,
  approval_type text NOT NULL, reviewer_id uuid NOT NULL REFERENCES app_users(user_id), decision text NOT NULL CHECK(decision IN ('APPROVED','REJECTED','EXCEPTION_APPROVED')),
  evidence_refs jsonb NOT NULL, reason text NULL, correlation_id uuid NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(aggregate_type, aggregate_id, aggregate_version, approval_type, reviewer_id)
);
CREATE TABLE script_view_references (
  script_view_reference_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), department_script_view_id uuid NOT NULL REFERENCES department_script_views(department_script_view_id),
  source_entity_type text NOT NULL, source_entity_id uuid NOT NULL, source_version_id uuid NULL, json_pointer text NOT NULL, source_hash char(64) NOT NULL, classification classification_level NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(department_script_view_id, source_entity_type, source_entity_id, json_pointer)
);
CREATE TABLE task_dependencies (
  task_dependency_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), task_id uuid NOT NULL REFERENCES department_tasks(task_id), depends_on_task_id uuid NOT NULL REFERENCES department_tasks(task_id),
  dependency_type text NOT NULL CHECK(dependency_type IN ('FINISH_TO_START','OUTPUT_APPROVAL','HANDOFF','QA_RECHECK')), required_output_contract_hash char(64) NULL, status acpos_status NOT NULL DEFAULT 'WAITING_DEPENDENCY', created_at timestamptz NOT NULL DEFAULT now(),
  CHECK(task_id <> depends_on_task_id), UNIQUE(task_id, depends_on_task_id, dependency_type)
);
CREATE TABLE asset_versions (
  asset_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), task_output_version_id uuid NOT NULL UNIQUE REFERENCES task_outputs(output_version_id), asset_kind text NOT NULL,
  reuse_status text NOT NULL CHECK(reuse_status IN ('NEW','REUSED','CANDIDATE')), rights_profile jsonb NOT NULL, visual_dna_refs jsonb NOT NULL, metadata jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE asset_reuse_candidates (
  asset_reuse_candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_asset_version_id uuid NOT NULL REFERENCES asset_versions(asset_version_id), target_task_id uuid NOT NULL REFERENCES department_tasks(task_id),
  compatibility_score numeric(5,2) NOT NULL CHECK(compatibility_score BETWEEN 0 AND 100), decision_status decision_status NOT NULL DEFAULT 'CANDIDATE', decision_reason text NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE editing_timelines (
  editing_timeline_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), task_id uuid NOT NULL REFERENCES department_tasks(task_id), timeline_version integer NOT NULL, source_video_output_version_id uuid NOT NULL REFERENCES task_outputs(output_version_id),
  timeline_document jsonb NOT NULL, timing_hash char(64) NOT NULL, status acpos_status NOT NULL DEFAULT 'DRAFT', created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(task_id, timeline_version)
);
CREATE TABLE subtitle_versions (
  subtitle_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), task_id uuid NOT NULL REFERENCES department_tasks(task_id), language_code text NOT NULL, version_no integer NOT NULL,
  content_uri text NOT NULL, content_hash char(64) NOT NULL, timing_hash char(64) NOT NULL, status acpos_status NOT NULL DEFAULT 'DRAFT', created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(task_id, language_code, version_no)
);
CREATE TABLE manual_review_cases (
  manual_review_case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), qa_review_run_id uuid NOT NULL REFERENCES qa_review_runs(qa_review_run_id), review_type text NOT NULL,
  assigned_reviewer_id uuid NULL REFERENCES app_users(user_id), status acpos_status NOT NULL DEFAULT 'IN_REVIEW', evidence_refs jsonb NOT NULL, decision jsonb NULL, created_at timestamptz NOT NULL DEFAULT now(), decided_at timestamptz NULL
);
CREATE TABLE content_packages (
  content_package_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), release_package_id uuid NOT NULL REFERENCES release_packages(release_package_id), channel_account_id uuid NOT NULL REFERENCES channel_accounts(channel_account_id),
  metadata_version jsonb NOT NULL, payload_manifest jsonb NOT NULL, package_hash char(64) NOT NULL UNIQUE, status acpos_status NOT NULL DEFAULT 'PENDING_APPROVAL', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE publish_callbacks (
  publish_callback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), publish_request_id uuid NOT NULL REFERENCES publish_requests(publish_request_id), callback_receipt_id uuid NULL REFERENCES callback_receipts(callback_receipt_id),
  provider_event_id text NOT NULL, verified boolean NOT NULL DEFAULT false, payload_hash char(64) NOT NULL, status acpos_status NOT NULL DEFAULT 'PENDING_EXTERNAL', received_at timestamptz NOT NULL DEFAULT now(), UNIQUE(publish_request_id, provider_event_id)
);
CREATE TABLE post_metrics (
  post_metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), publish_request_id uuid NOT NULL REFERENCES publish_requests(publish_request_id), metric_at timestamptz NOT NULL,
  metric_snapshot jsonb NOT NULL, source_snapshot_hash char(64) NOT NULL, freshness_at timestamptz NOT NULL, UNIQUE(publish_request_id, metric_at)
);
CREATE TABLE strategy_decisions (
  strategy_decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), strategy_candidate_id uuid NOT NULL REFERENCES strategy_candidates(strategy_candidate_id),
  decision text NOT NULL CHECK(decision IN ('ADOPT_CONTEXT','REJECT','REQUEST_REVISION')), decider_id uuid NOT NULL REFERENCES app_users(user_id), rationale text NOT NULL, context_candidate_id uuid NULL REFERENCES context_candidates(context_candidate_id), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE users (
  user_id uuid PRIMARY KEY REFERENCES app_users(user_id), department_id uuid NULL, legal_name text NULL, profile jsonb NOT NULL DEFAULT '{}'::jsonb, status acpos_status NOT NULL DEFAULT 'APPROVED', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE departments (
  department_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), department_key text NOT NULL UNIQUE, name text NOT NULL, owner_user_id uuid NULL REFERENCES app_users(user_id), status acpos_status NOT NULL DEFAULT 'APPROVED', created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE users ADD CONSTRAINT fk_users_department FOREIGN KEY(department_id) REFERENCES departments(department_id);
CREATE TABLE memberships (
  membership_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES users(user_id), department_id uuid NOT NULL REFERENCES departments(department_id), position_label text NULL,
  scope jsonb NOT NULL DEFAULT '{}'::jsonb, status acpos_status NOT NULL DEFAULT 'APPROVED', granted_by uuid NOT NULL REFERENCES app_users(user_id), expires_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(user_id, department_id)
);
CREATE TABLE access_reviews (
  access_review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES users(user_id), assignment_scope jsonb NOT NULL, review_due_at timestamptz NOT NULL, decision text NULL CHECK(decision IN ('RETAIN','REVOKE','MODIFY')),
  reviewer_id uuid NULL REFERENCES app_users(user_id), evidence jsonb NOT NULL DEFAULT '{}'::jsonb, status acpos_status NOT NULL DEFAULT 'PENDING_APPROVAL', decided_at timestamptz NULL
);
CREATE TABLE security_audits (
  security_audit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), audit_event_id uuid NOT NULL REFERENCES audit_events(audit_event_id), security_category text NOT NULL, severity text NOT NULL,
  decision text NOT NULL, policy_ref text NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE traces (
  trace_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), correlation_id uuid NOT NULL, root_event_id uuid NULL, operation_id text NULL, status text NOT NULL, spans jsonb NOT NULL, started_at timestamptz NOT NULL, ended_at timestamptz NULL, UNIQUE(correlation_id)
);
CREATE TABLE queues (
  queue_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), queue_key text NOT NULL UNIQUE, purpose text NOT NULL, capacity integer NOT NULL CHECK(capacity > 0), status acpos_status NOT NULL DEFAULT 'READY', policy jsonb NOT NULL
);
CREATE TABLE workers (
  worker_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), worker_key text NOT NULL UNIQUE, queue_id uuid NOT NULL REFERENCES queues(queue_id), capability jsonb NOT NULL, health jsonb NOT NULL DEFAULT '{}'::jsonb, status acpos_status NOT NULL DEFAULT 'READY', last_heartbeat_at timestamptz NULL
);
CREATE TABLE release_records (
  release_record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), release_key text NOT NULL UNIQUE, environment text NOT NULL, artifact_hash char(64) NOT NULL, approval_record_id uuid NULL REFERENCES approval_records(approval_record_id),
  rollback_plan jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'PENDING_APPROVAL', deployed_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE erp_connectors (
  erp_connector_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), provider_key text NOT NULL, adapter_key text NOT NULL, secret_reference_id uuid NULL REFERENCES secret_references(secret_reference_id),
  entity_scope jsonb NOT NULL, connection_status text NOT NULL CHECK(connection_status IN ('UNCONFIGURED','CONFIGURING','VALIDATING','READY','DEGRADED','DISABLED','FAILED')), configuration_version integer NOT NULL DEFAULT 1, health jsonb NOT NULL DEFAULT '{}'::jsonb, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(workspace_id, provider_key, adapter_key)
);
CREATE TABLE erp_mappings (
  erp_mapping_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), erp_connector_id uuid NOT NULL REFERENCES erp_connectors(erp_connector_id), entity_name text NOT NULL, source_schema jsonb NOT NULL, target_schema jsonb NOT NULL, transform_spec jsonb NOT NULL,
  mapping_hash char(64) NOT NULL, status acpos_status NOT NULL DEFAULT 'DRAFT', validated_at timestamptz NULL, UNIQUE(erp_connector_id, entity_name, mapping_hash)
);
CREATE TABLE erp_sync_jobs (
  erp_sync_job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), erp_connector_id uuid NOT NULL REFERENCES erp_connectors(erp_connector_id), requested_by uuid NOT NULL REFERENCES app_users(user_id), idempotency_key char(64) NOT NULL UNIQUE,
  requested_scope jsonb NOT NULL, data_classification text NOT NULL DEFAULT 'INTERNAL', snapshot_type text NOT NULL DEFAULT 'GENERAL', attempt_no integer NOT NULL DEFAULT 1 CHECK(attempt_no > 0), external_evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb, status text NOT NULL CHECK(status IN ('NOT_REQUESTED','QUEUED','RUNNING','COMPLETED','PARTIAL','FAILED','RETRY_PENDING','CANCELLED','PENDING_EXTERNAL')), requested_at timestamptz NOT NULL DEFAULT now(), started_at timestamptz NULL, completed_at timestamptz NULL
);
CREATE TABLE erp_sync_records (
  erp_sync_record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), erp_sync_job_id uuid NOT NULL REFERENCES erp_sync_jobs(erp_sync_job_id), source_entity_ref text NOT NULL, target_entity_ref text NULL, operation text NOT NULL,
  status text NOT NULL CHECK(status IN ('PENDING','IMPORTED','SKIPPED','FAILED')), source_hash char(64) NOT NULL, failure_detail jsonb NULL, processed_at timestamptz NULL, UNIQUE(erp_sync_job_id, source_entity_ref, operation)
);
CREATE TABLE erp_snapshots (
  erp_snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), erp_connector_id uuid NOT NULL REFERENCES erp_connectors(erp_connector_id), erp_sync_job_id uuid NULL REFERENCES erp_sync_jobs(erp_sync_job_id),
  snapshot_type text NOT NULL, snapshot_document jsonb NOT NULL, completeness numeric(5,2) NOT NULL CHECK(completeness BETWEEN 0 AND 100), freshness_at timestamptz NOT NULL, snapshot_hash char(64) NOT NULL UNIQUE, external_result_verified boolean NOT NULL DEFAULT false, external_evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb, status acpos_status NOT NULL DEFAULT 'APPROVED', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE erp_failures (
  erp_failure_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), erp_connector_id uuid NOT NULL REFERENCES erp_connectors(erp_connector_id), erp_sync_job_id uuid NULL REFERENCES erp_sync_jobs(erp_sync_job_id),
  failure_code text NOT NULL, failure_detail jsonb NOT NULL, retryable boolean NOT NULL, status acpos_status NOT NULL DEFAULT 'FAILED', occurred_at timestamptz NOT NULL DEFAULT now(), resolved_at timestamptz NULL
);
CREATE TABLE erp_audit_references (
  erp_audit_reference_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), erp_connector_id uuid NOT NULL REFERENCES erp_connectors(erp_connector_id), audit_event_id uuid NOT NULL REFERENCES audit_events(audit_event_id), reference_type text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(erp_connector_id, audit_event_id, reference_type)
);
-- R8 semantic authorization hardening: risk-based approval and non-authorization labels.
ALTER TABLE permission_resources DROP CONSTRAINT IF EXISTS permission_resources_resource_type_check;
ALTER TABLE permission_resources ADD CONSTRAINT permission_resources_resource_type_check CHECK(resource_type IN ('SURFACE','L1','L2','L3','PAGE','SECTION','CONTROL','ACTION','FIELD','API','DECISION'));
ALTER TABLE permission_resources ADD COLUMN IF NOT EXISTS risk_tier text NOT NULL DEFAULT 'STANDARD' CHECK(risk_tier IN ('STANDARD','HIGH'));
ALTER TABLE account_permission_assignments ALTER COLUMN approval_ref DROP NOT NULL;
ALTER TABLE account_permission_assignments ADD COLUMN IF NOT EXISTS approval_required boolean NOT NULL DEFAULT false;
CREATE OR REPLACE FUNCTION enforce_account_permission_assignment_approval() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE resource_risk_tier text;
BEGIN
  SELECT risk_tier INTO resource_risk_tier FROM permission_resources WHERE resource_id = NEW.resource_id;
  NEW.approval_required := (NEW.effect = 'ALLOW' AND resource_risk_tier = 'HIGH');
  IF NEW.approval_required AND nullif(btrim(coalesce(NEW.approval_ref, '')), '') IS NULL THEN
    RAISE EXCEPTION 'ACCOUNT_PERMISSION_HIGH_RISK_APPROVAL_REQUIRED';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS trg_account_permission_assignment_approval ON account_permission_assignments;
CREATE TRIGGER trg_account_permission_assignment_approval BEFORE INSERT OR UPDATE ON account_permission_assignments FOR EACH ROW EXECUTE FUNCTION enforce_account_permission_assignment_approval();
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'project_memberships' AND column_name = 'collaboration_role') THEN
    ALTER TABLE project_memberships RENAME COLUMN collaboration_role TO collaboration_label;
  END IF;
END $$;
COMMENT ON COLUMN project_memberships.collaboration_label IS 'NON_AUTHORIZATION_METADATA: collaboration label only; never an Authorization Source.';
CREATE INDEX idx_project_memberships_project ON project_memberships(project_id, status);
CREATE INDEX idx_task_dependencies_waiting ON task_dependencies(depends_on_task_id, status);
CREATE INDEX idx_erp_connectors_scope ON erp_connectors(workspace_id, connection_status);
CREATE INDEX idx_erp_sync_jobs_status ON erp_sync_jobs(erp_connector_id, status, requested_at DESC);
CREATE INDEX idx_erp_snapshots_freshness ON erp_snapshots(erp_connector_id, freshness_at DESC);
-- R9 Finalization and Final Correction canonical bootstrap table declarations.
-- 0004_r9_finalization.sql and 0005_r9_final_correction.sql are append-only compatibility migrations; any future additive column must be written in both this self-contained bootstrap and its migration.
CREATE TABLE IF NOT EXISTS project_creation_wizard_sessions (wizard_session_id uuid PRIMARY KEY, project_id uuid NULL REFERENCES projects(project_id), owner_user_id uuid NOT NULL REFERENCES app_users(user_id), current_step smallint NOT NULL, draft_payload jsonb NOT NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS story_core_versions (story_core_version_id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(project_id), version_no integer NOT NULL, content jsonb NOT NULL, checksum char(64) NOT NULL, status text NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(project_id, version_no));
CREATE TABLE IF NOT EXISTS story_candidates (story_candidate_id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(project_id), candidate_key text NOT NULL, content jsonb NOT NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS story_candidate_comparisons (comparison_id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(project_id), candidate_ids jsonb NOT NULL, comparison_payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS world_bible_versions (world_bible_version_id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(project_id), version_no integer NOT NULL, content jsonb NOT NULL, checksum char(64) NOT NULL, status text NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS world_canon_rules (world_canon_rule_id uuid PRIMARY KEY, world_bible_version_id uuid NOT NULL REFERENCES world_bible_versions(world_bible_version_id), canon_level text NOT NULL, rule_text text NOT NULL, active boolean NOT NULL DEFAULT true);
CREATE TABLE IF NOT EXISTS dna_versions (dna_version_id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(project_id), dna_type text NOT NULL, entity_key text NOT NULL, version_no integer NOT NULL, content jsonb NOT NULL, status text NOT NULL, checksum char(64) NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS dna_version_references (dna_version_reference_id uuid PRIMARY KEY, dna_version_id uuid NOT NULL REFERENCES dna_versions(dna_version_id), reference_kind text NOT NULL, reference_id text NOT NULL, approved boolean NOT NULL DEFAULT false);
CREATE TABLE IF NOT EXISTS chapter_versions (chapter_version_id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(project_id), chapter_number integer NOT NULL, version_no integer NOT NULL, content jsonb NOT NULL, status text NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS chapter_topic_links (chapter_topic_link_id uuid PRIMARY KEY, chapter_version_id uuid NOT NULL REFERENCES chapter_versions(chapter_version_id), topic_id uuid NOT NULL REFERENCES topics(topic_id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS provider_prompt_profiles (provider_prompt_profile_id uuid PRIMARY KEY, provider_key text NOT NULL, model_key text NOT NULL, adapter_version text NOT NULL, capability_profile jsonb NOT NULL, api_schema_ref text NOT NULL, active boolean NOT NULL DEFAULT true);
CREATE TABLE IF NOT EXISTS provider_compiled_prompts (provider_compiled_prompt_id uuid PRIMARY KEY, instruction_package_id uuid NOT NULL REFERENCES instruction_packages(instruction_package_id), provider_prompt_profile_id uuid NOT NULL REFERENCES provider_prompt_profiles(provider_prompt_profile_id), compiled_prompt jsonb NOT NULL, compiled_prompt_hash char(64) NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS correction_script_versions (correction_script_version_id uuid PRIMARY KEY, correction_request_id uuid NOT NULL REFERENCES correction_requests(correction_request_id), failed_output_id uuid NOT NULL REFERENCES task_outputs(output_version_id), correction_instruction jsonb NOT NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS voice_runtime_profiles (voice_runtime_profile_id uuid PRIMARY KEY, dna_version_id uuid NOT NULL REFERENCES dna_versions(dna_version_id), voice_profile jsonb NOT NULL, version_no integer NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS editing_runtime_runs (editing_runtime_run_id uuid PRIMARY KEY, task_id uuid NOT NULL REFERENCES department_tasks(task_id), state text NOT NULL, sequence_no smallint NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS conversations (conversation_id uuid PRIMARY KEY, workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), project_id uuid NULL REFERENCES projects(project_id), topic_id uuid NULL REFERENCES topics(topic_id), title text NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS conversation_messages (conversation_message_id uuid PRIMARY KEY, conversation_id uuid NOT NULL REFERENCES conversations(conversation_id), sequence_no integer NOT NULL, actor_type text NOT NULL, actor_ref text NOT NULL, message_content jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS meetings (meeting_id uuid PRIMARY KEY, workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), project_id uuid NULL REFERENCES projects(project_id), topic_id uuid NULL REFERENCES topics(topic_id), title text NOT NULL, status text NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS meeting_participants (meeting_participant_id uuid PRIMARY KEY, meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), subject_type text NOT NULL, subject_ref text NOT NULL, meeting_function text NOT NULL);
CREATE TABLE IF NOT EXISTS meeting_messages (meeting_message_id uuid PRIMARY KEY, meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), sequence_no integer NOT NULL, participant_id uuid NOT NULL REFERENCES meeting_participants(meeting_participant_id), content jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS meeting_summaries (meeting_summary_id uuid PRIMARY KEY, meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), version_no integer NOT NULL, summary jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS notebooks (notebook_id uuid PRIMARY KEY, workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), title text NOT NULL, owner_id uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS notebook_entries (notebook_entry_id uuid PRIMARY KEY, notebook_id uuid NOT NULL REFERENCES notebooks(notebook_id), version_no integer NOT NULL, content jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS conversation_versions (conversation_version_id uuid PRIMARY KEY, conversation_id uuid NOT NULL REFERENCES conversations(conversation_id), version_no integer NOT NULL, snapshot jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS meeting_versions (meeting_version_id uuid PRIMARY KEY, meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), version_no integer NOT NULL, snapshot jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS candidate_blocks (candidate_block_id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(project_id), candidate_type text NOT NULL, candidate_version_ref text NOT NULL, block_id text NOT NULL, content jsonb NOT NULL, checksum char(64) NOT NULL);
CREATE TABLE IF NOT EXISTS candidate_patches (candidate_patch_id uuid PRIMARY KEY, candidate_block_id uuid NOT NULL REFERENCES candidate_blocks(candidate_block_id), base_candidate_version_ref text NOT NULL, replacement_content jsonb NOT NULL, rationale text NOT NULL, blueprint_impact jsonb NOT NULL, continuity_check jsonb NOT NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS candidate_patch_sets (candidate_patch_set_id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(project_id), base_candidate_version_ref text NOT NULL, status text NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS candidate_patch_set_items (candidate_patch_set_item_id uuid PRIMARY KEY, candidate_patch_set_id uuid NOT NULL REFERENCES candidate_patch_sets(candidate_patch_set_id), candidate_patch_id uuid NOT NULL REFERENCES candidate_patches(candidate_patch_id), decision text NULL);
CREATE TABLE IF NOT EXISTS continuity_ledger_entries (continuity_ledger_entry_id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(project_id), entry_type text NOT NULL, payload jsonb NOT NULL, source_version_ref text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS continuity_snapshots (continuity_snapshot_id uuid PRIMARY KEY, conversation_id uuid NULL REFERENCES conversations(conversation_id), project_id uuid NULL REFERENCES projects(project_id), snapshot_hash char(64) NOT NULL UNIQUE, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS execution_bundles (execution_bundle_id uuid PRIMARY KEY, change_candidate_ref text NOT NULL, status text NOT NULL, required_layers jsonb NOT NULL, correlation_id uuid NOT NULL, created_by uuid NOT NULL REFERENCES app_users(user_id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS execution_bundle_steps (execution_bundle_step_id uuid PRIMARY KEY, execution_bundle_id uuid NOT NULL REFERENCES execution_bundles(execution_bundle_id), step_key text NOT NULL, sequence_no smallint NOT NULL, status text NOT NULL);
CREATE TABLE IF NOT EXISTS execution_logs (execution_log_id uuid PRIMARY KEY, execution_bundle_id uuid NOT NULL REFERENCES execution_bundles(execution_bundle_id), execution_bundle_step_id uuid NULL REFERENCES execution_bundle_steps(execution_bundle_step_id), page_no integer NOT NULL, log_level text NOT NULL, content text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS provider_candidate_groups (provider_candidate_group_id uuid PRIMARY KEY, group_key text NOT NULL UNIQUE, purpose text NOT NULL, allowed_scope jsonb NOT NULL, active boolean NOT NULL DEFAULT true);
CREATE TABLE IF NOT EXISTS provider_candidate_members (provider_candidate_member_id uuid PRIMARY KEY, provider_candidate_group_id uuid NOT NULL REFERENCES provider_candidate_groups(provider_candidate_group_id), provider_prompt_profile_id uuid NOT NULL REFERENCES provider_prompt_profiles(provider_prompt_profile_id), rank_policy jsonb NOT NULL, enabled boolean NOT NULL DEFAULT true);
CREATE TABLE IF NOT EXISTS provider_route_preflights (provider_route_preflight_id uuid PRIMARY KEY, provider_candidate_group_id uuid NOT NULL REFERENCES provider_candidate_groups(provider_candidate_group_id), status text NOT NULL, checks jsonb NOT NULL, waste_guard jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS provider_quality_observations (provider_quality_observation_id uuid PRIMARY KEY, provider_candidate_member_id uuid NOT NULL REFERENCES provider_candidate_members(provider_candidate_member_id), task_class text NOT NULL, result_status text NOT NULL, evidence jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS provider_quarantines (provider_quarantine_id uuid PRIMARY KEY, provider_candidate_member_id uuid NOT NULL REFERENCES provider_candidate_members(provider_candidate_member_id), reason text NOT NULL, status text NOT NULL, imposed_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS multi_ai_context_snapshots (context_snapshot_id uuid PRIMARY KEY, meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), version_no integer NOT NULL, context_payload jsonb NOT NULL, context_snapshot_hash char(64) NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS meeting_rounds (meeting_round_id uuid PRIMARY KEY, meeting_id uuid NOT NULL REFERENCES meetings(meeting_id), round_no integer NOT NULL, mode text NOT NULL, status text NOT NULL, context_snapshot_id uuid NOT NULL REFERENCES multi_ai_context_snapshots(context_snapshot_id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS versioned_layer_documents (layer_document_id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(project_id), topic_id uuid NULL REFERENCES topics(topic_id), asset_version_id uuid NULL REFERENCES asset_versions(asset_version_id), version_no integer NOT NULL, checksum char(64) NOT NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS document_layers (document_layer_id uuid PRIMARY KEY, layer_document_id uuid NOT NULL REFERENCES versioned_layer_documents(layer_document_id), layer_id text NOT NULL, layer_type text NOT NULL, layer_name text NOT NULL, semantic_target text NOT NULL, asset_version_id uuid NULL REFERENCES asset_versions(asset_version_id), dna_version_id uuid NULL REFERENCES dna_versions(dna_version_id), blueprint_version_id uuid NULL REFERENCES blueprint_versions(blueprint_version_id), checksum char(64) NOT NULL, version_no integer NOT NULL);
CREATE TABLE IF NOT EXISTS asset_patches (asset_patch_id uuid PRIMARY KEY, source_asset_version_id uuid NOT NULL REFERENCES asset_versions(asset_version_id), document_layer_id uuid NULL REFERENCES document_layers(document_layer_id), blueprint_version_id uuid NOT NULL REFERENCES blueprint_versions(blueprint_version_id), dna_version_id uuid NOT NULL REFERENCES dna_versions(dna_version_id), status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS video_timecode_patches (video_timecode_patch_id uuid PRIMARY KEY, task_id uuid NOT NULL REFERENCES department_tasks(task_id), timeline_id uuid NOT NULL REFERENCES editing_timelines(editing_timeline_id), resulting_output_id uuid NULL REFERENCES task_outputs(output_version_id), status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

-- R9 DEPLOYMENT READY FINAL COLUMN CLOSURE
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

-- ACPOS Deployment Runtime Operational Schema (server-side job/session/UI operational persistence)
CREATE SCHEMA IF NOT EXISTS acpos_runtime;
CREATE TABLE IF NOT EXISTS acpos_runtime.entities(kind text NOT NULL, id text NOT NULL, parent_id text NULL, status text NULL, version integer NOT NULL DEFAULT 1, payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS acpos_runtime.audit(id text PRIMARY KEY, operation_id text NOT NULL, account_id text NULL, correlation_id text NULL, idempotency_key text NULL, request_hash text NULL, outcome text NOT NULL, payload jsonb NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.idempotency(idempotency_key text PRIMARY KEY, operation_id text NOT NULL, response_json jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.events(id text PRIMARY KEY, event_type text NOT NULL, resource_ref text NULL, payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.project_conversation_workspaces(id text PRIMARY KEY, project_id text NOT NULL UNIQUE, shared_context_snapshot_id text NULL, view_state jsonb NOT NULL DEFAULT '{}'::jsonb, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.conversations(id text PRIMARY KEY, workspace_id text NOT NULL REFERENCES acpos_runtime.project_conversation_workspaces(id), project_id text NOT NULL, topic_id text NULL, task_id text NULL, candidate_version_id text NULL, blueprint_version_id text NULL, asset_version_id text NULL, shot_id text NULL, title text NOT NULL, parent_thread_id text NULL REFERENCES acpos_runtime.conversations(id), branch_source_message_id text NULL, context_snapshot_id text NULL, view_state jsonb NOT NULL DEFAULT '{}'::jsonb, draft_text text NOT NULL DEFAULT '', draft_attachments jsonb NOT NULL DEFAULT '[]'::jsonb, draft_cursor_position integer NULL, status text NOT NULL, last_read_message_id text NULL, scroll_anchor_message_id text NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.conversation_messages(id text PRIMARY KEY, conversation_id text NOT NULL REFERENCES acpos_runtime.conversations(id), sender_type text NOT NULL, content text NOT NULL, provider_id text NULL, model_id text NULL, job_id text NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.thread_syncs(id text PRIMARY KEY, source_thread_id text NOT NULL REFERENCES acpos_runtime.conversations(id), target_thread_id text NOT NULL REFERENCES acpos_runtime.conversations(id), direction text NOT NULL, sync_types jsonb NOT NULL, selected_message_ids jsonb NOT NULL DEFAULT '[]'::jsonb, sync_payload jsonb NOT NULL DEFAULT '{}'::jsonb, provenance_json jsonb NOT NULL DEFAULT '{}'::jsonb, applied_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.thread_context_items(id text PRIMARY KEY, thread_id text NOT NULL REFERENCES acpos_runtime.conversations(id), item_type text NOT NULL, source_thread_id text NOT NULL REFERENCES acpos_runtime.conversations(id), source_ref text NULL, payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.conversation_generation_jobs(id text PRIMARY KEY, conversation_id text NOT NULL REFERENCES acpos_runtime.conversations(id), user_message_id text NOT NULL REFERENCES acpos_runtime.conversation_messages(id), candidate_group_id text NULL, provider_mode text NOT NULL, requested_provider_id text NULL, requested_model_id text NULL, status text NOT NULL, cancel_requested boolean NOT NULL DEFAULT false, provider_id text NULL, model_id text NULL, result_message_id text NULL REFERENCES acpos_runtime.conversation_messages(id), failure_code text NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.meetings(id text PRIMARY KEY, project_id text NOT NULL, topic_id text NULL, title text NOT NULL, objective text NOT NULL, agenda jsonb NOT NULL, context_snapshot_id text NULL, context_snapshot_hash char(64) NULL, current_round integer NOT NULL DEFAULT 0, version integer NOT NULL DEFAULT 1, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.meeting_participants(id text PRIMARY KEY, meeting_id text NOT NULL REFERENCES acpos_runtime.meetings(id), perspective text NOT NULL, route_mode text NOT NULL, candidate_group_id text NULL, requested_provider_id text NULL, requested_model_id text NULL, actual_provider_id text NULL, actual_model_id text NULL, allow_substitution boolean NOT NULL DEFAULT false, participant_status text NOT NULL, preflight_status text NULL, failure_reason text NULL, substitution_reason text NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.meeting_rounds(id text PRIMARY KEY, meeting_id text NOT NULL REFERENCES acpos_runtime.meetings(id), round_no integer NOT NULL, round_mode text NOT NULL, context_snapshot_id text NULL, prompt text NOT NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.meeting_messages(id text PRIMARY KEY, meeting_id text NOT NULL REFERENCES acpos_runtime.meetings(id), round_id text NULL REFERENCES acpos_runtime.meeting_rounds(id), participant_id text NULL REFERENCES acpos_runtime.meeting_participants(id), sender_type text NOT NULL, content text NOT NULL, provider_id text NULL, model_id text NULL, evidence_json jsonb NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.execution_jobs(id text PRIMARY KEY, title text NOT NULL, job_type text NOT NULL, project_id text NULL, topic_id text NULL, status text NOT NULL, current_step integer NOT NULL DEFAULT 0, total_steps integer NOT NULL DEFAULT 0, cancel_requested boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.execution_steps(id text PRIMARY KEY, job_id text NOT NULL REFERENCES acpos_runtime.execution_jobs(id), step_no integer NOT NULL, name text NOT NULL, status text NOT NULL, result_json jsonb NULL, started_at timestamptz NULL, completed_at timestamptz NULL);
CREATE TABLE IF NOT EXISTS acpos_runtime.execution_logs(id text PRIMARY KEY, job_id text NOT NULL REFERENCES acpos_runtime.execution_jobs(id), page_no integer NOT NULL, content text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(job_id,page_no));
CREATE TABLE IF NOT EXISTS acpos_runtime.todos(id text PRIMARY KEY, project_id text NOT NULL, topic_id text NULL, task_id text NULL, title text NOT NULL, description text NULL, priority text NULL, due_at timestamptz NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.provider_groups(id text PRIMARY KEY, name text NOT NULL, use_case text NOT NULL, data_classification text NULL, quality_tiers jsonb NULL, enabled boolean NOT NULL DEFAULT true, limits_json jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.provider_members(id text PRIMARY KEY, group_id text NOT NULL REFERENCES acpos_runtime.provider_groups(id), provider_id text NOT NULL, model_id text NOT NULL, capability_id text NULL, priority integer NOT NULL, enabled boolean NOT NULL DEFAULT true, health_status text NOT NULL DEFAULT 'UNKNOWN', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.provider_profiles(id text PRIMARY KEY, provider_id text NOT NULL, model_id text NOT NULL, capability_type text NOT NULL, adapter_type text NOT NULL, base_url text NOT NULL, endpoint_path text NOT NULL, http_method text NOT NULL, secret_env_ref text NOT NULL, preferred_language text NULL, max_context integer NULL, timeout_seconds integer NOT NULL, request_template jsonb NOT NULL, response_text_path text NOT NULL, enabled boolean NOT NULL DEFAULT true, health_status text NOT NULL DEFAULT 'UNKNOWN', version integer NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(provider_id,model_id));
CREATE TABLE IF NOT EXISTS acpos_runtime.provider_quarantine(id text PRIMARY KEY, member_id text NOT NULL REFERENCES acpos_runtime.provider_members(id), reason text NOT NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), restored_at timestamptz NULL);
CREATE TABLE IF NOT EXISTS acpos_runtime.layer_documents(id text PRIMARY KEY, project_id text NULL, topic_id text NULL, asset_version_id text NULL, name text NOT NULL, width integer NULL, height integer NULL, version integer NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.layers(id text PRIMARY KEY, document_id text NOT NULL REFERENCES acpos_runtime.layer_documents(id), layer_type text NOT NULL, layer_name text NOT NULL, semantic_target text NULL, parent_layer_id text NULL REFERENCES acpos_runtime.layers(id), z_index integer NOT NULL, visible boolean NOT NULL DEFAULT true, locked boolean NOT NULL DEFAULT false, opacity numeric(5,4) NOT NULL DEFAULT 1.0, blend_mode text NOT NULL DEFAULT 'NORMAL', transform_json jsonb NULL, mask_ref text NULL, source_ref text NULL, version integer NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.patches(id text PRIMARY KEY, patch_type text NOT NULL, source_ref text NOT NULL, target_ref text NULL, instruction text NULL, payload jsonb NOT NULL, status text NOT NULL, preview_json jsonb NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.correction_requests_runtime(id text PRIMARY KEY, finding_id text NOT NULL, source_output_version_id text NOT NULL, source_instruction_package_id text NOT NULL, source_scorecard_id text NULL, original_owner_task_id text NOT NULL, blueprint_version_id text NOT NULL, department text NOT NULL CHECK(department IN ('ASSET','VIDEO','EDITING','VOICE')), provider_id text NULL, root_cause text NOT NULL, affected_scope_json jsonb NOT NULL, revalidation_requirements_json jsonb NOT NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.correction_script_versions_runtime(id text PRIMARY KEY, correction_request_id text NOT NULL REFERENCES acpos_runtime.correction_requests_runtime(id), version_no integer NOT NULL CHECK(version_no > 0), finding_id text NOT NULL, failed_output_version_id text NOT NULL, blueprint_version_id text NOT NULL, original_instruction_package_id text NOT NULL, department text NOT NULL CHECK(department IN ('ASSET','VIDEO','EDITING','VOICE')), provider_id text NULL, root_cause_snapshot text NOT NULL, correction_instruction_json jsonb NOT NULL, status text NOT NULL, decision_reason text NULL, decided_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(correction_request_id,version_no));
CREATE TABLE IF NOT EXISTS acpos_runtime.correction_runs(id text PRIMARY KEY, correction_script_id text NOT NULL REFERENCES acpos_runtime.correction_script_versions_runtime(id), task_id text NOT NULL, provider_candidate_group_id text NOT NULL REFERENCES acpos_runtime.provider_groups(id), source_output_version_id text NOT NULL, new_output_version_id text NULL, route_decision_id text NULL, provider_id text NULL, model_id text NULL, execution_mode text NOT NULL, status text NOT NULL, evidence_json jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz NULL);
CREATE TABLE IF NOT EXISTS acpos_runtime.correction_rescores(id text PRIMARY KEY, correction_run_id text NOT NULL REFERENCES acpos_runtime.correction_runs(id), correction_script_id text NOT NULL REFERENCES acpos_runtime.correction_script_versions_runtime(id), output_version_id text NOT NULL, scorecard_profile_id text NOT NULL, finding_id text NULL, total_score numeric(5,2) NULL CHECK(total_score IS NULL OR (total_score >= 0 AND total_score <= 100)), gate_status text NOT NULL, evaluation_mode text NOT NULL, evidence_json jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.voice_runtime_profiles_runtime(id text PRIMARY KEY, profile_key text NOT NULL, version_no integer NOT NULL CHECK(version_no > 0), dna_version_id text NOT NULL, character_id text NULL, profile_json jsonb NOT NULL, content_hash char(64) NOT NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(profile_key,version_no));
CREATE TABLE IF NOT EXISTS acpos_runtime.editing_runtime_runs_runtime(id text PRIMARY KEY, task_id text NOT NULL, timeline_version_id text NOT NULL, approved_video_output_version_ids_json jsonb NOT NULL, voice_runtime_profile_id text NOT NULL REFERENCES acpos_runtime.voice_runtime_profiles_runtime(id), subtitle_language text NOT NULL, subtitle_format text NOT NULL CHECK(subtitle_format IN ('SRT','VTT','ASS','BURN_IN')), current_state text NOT NULL CHECK(current_state IN ('ASSEMBLY','AUDIO_MIX','LIP_SYNC','SUBTITLE','QA_READY','FAILED','SUPERSEDED')), status text NOT NULL, current_output_version_id text NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.editing_runtime_steps_runtime(id text PRIMARY KEY, run_id text NOT NULL REFERENCES acpos_runtime.editing_runtime_runs_runtime(id), step_no integer NOT NULL CHECK(step_no BETWEEN 1 AND 4), step_name text NOT NULL CHECK(step_name IN ('ASSEMBLY','AUDIO_MIX','LIP_SYNC','SUBTITLE')), from_state text NOT NULL, to_state text NOT NULL, evidence_ref text NOT NULL, output_version_id text NOT NULL, payload_json jsonb NOT NULL, status text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(run_id,step_name));
CREATE TABLE IF NOT EXISTS acpos_runtime.account_permissions(id text PRIMARY KEY, account_id text NOT NULL, resource_key text NOT NULL, actions jsonb NOT NULL, scope_json jsonb NOT NULL, condition_json jsonb NULL, expires_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(account_id,resource_key));
CREATE TABLE IF NOT EXISTS acpos_runtime.accounts(id text PRIMARY KEY, email text NOT NULL UNIQUE, password_hash text NOT NULL, status text NOT NULL, bootstrap_admin boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.sessions(token_hash text PRIMARY KEY, account_id text NOT NULL REFERENCES acpos_runtime.accounts(id), expires_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

-- Deployment-ready canonical alignment for lineage and Multi-AI naming.
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_version integer NOT NULL DEFAULT 1;
ALTER TABLE meeting_participants ADD COLUMN IF NOT EXISTS participant_perspective text NULL;
ALTER TABLE work_packages ADD COLUMN IF NOT EXISTS production_contract_id uuid NULL;
ALTER TABLE department_tasks ADD COLUMN IF NOT EXISTS production_contract_id uuid NULL;
ALTER TABLE provider_jobs ADD COLUMN IF NOT EXISTS production_contract_id uuid NULL;
ALTER TABLE task_outputs ADD COLUMN IF NOT EXISTS production_contract_id uuid NULL;
ALTER TABLE scorecards ADD COLUMN IF NOT EXISTS production_contract_id uuid NULL;
ALTER TABLE handoffs ADD COLUMN IF NOT EXISTS production_contract_id uuid NULL;
ALTER TABLE qa_review_runs ADD COLUMN IF NOT EXISTS production_contract_id uuid NULL;
ALTER TABLE release_packages ADD COLUMN IF NOT EXISTS production_contract_id uuid NULL;
ALTER TABLE publish_requests ADD COLUMN IF NOT EXISTS production_contract_id uuid NULL;

-- Persistent user UI preference (navigation behavior is account-scoped, never role-derived).
CREATE TABLE IF NOT EXISTS user_ui_preferences (user_id uuid PRIMARY KEY REFERENCES app_users(user_id), sidebar_mode text NOT NULL DEFAULT 'MANUAL' CHECK(sidebar_mode IN ('MANUAL','AUTO','PINNED')), auto_collapse_large_workspace boolean NOT NULL DEFAULT true, updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS acpos_runtime.ui_preferences(account_id text PRIMARY KEY, sidebar_mode text NOT NULL DEFAULT 'MANUAL' CHECK(sidebar_mode IN ('MANUAL','AUTO','PINNED')), auto_collapse_large_workspace boolean NOT NULL DEFAULT true, updated_at timestamptz NOT NULL DEFAULT now());

-- FINAL_TARGET_LINEAGE_AND_MEETING_COLUMN_CLOSURE
-- These ALTERs are part of the canonical final target. They deliberately mirror
-- post-bootstrap lineage/meeting migrations so clean install and upgrade paths converge.
ALTER TABLE work_packages ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS output_contract_hash char(64), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE department_tasks ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS output_contract_hash char(64), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE provider_jobs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS output_contract_hash char(64), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE task_outputs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE scorecards ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE handoffs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE qa_review_runs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE release_packages ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE publish_requests ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id), ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id), ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id), ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id), ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id);
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_version integer NOT NULL DEFAULT 1, ADD COLUMN IF NOT EXISTS agenda jsonb NOT NULL DEFAULT '{}'::jsonb, ADD COLUMN IF NOT EXISTS context_snapshot_id uuid NULL, ADD COLUMN IF NOT EXISTS candidate_group_ref text NULL, ADD COLUMN IF NOT EXISTS route_mode text NOT NULL DEFAULT 'SINGLE' CHECK(route_mode IN ('SINGLE','MULTI_AI'));
ALTER TABLE meeting_participants ADD COLUMN IF NOT EXISTS participant_perspective text NULL, ADD COLUMN IF NOT EXISTS requested_provider text NULL, ADD COLUMN IF NOT EXISTS requested_model text NULL, ADD COLUMN IF NOT EXISTS actual_provider text NULL, ADD COLUMN IF NOT EXISTS actual_model text NULL, ADD COLUMN IF NOT EXISTS allow_substitution boolean NOT NULL DEFAULT false, ADD COLUMN IF NOT EXISTS substitution_trace jsonb NOT NULL DEFAULT '{}'::jsonb;

-- FINAL_TARGET_DASHBOARD_TODO
CREATE TABLE IF NOT EXISTS dashboard_todos (
  todo_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_users(user_id),
  scope_type text NOT NULL CHECK(scope_type IN ('PERSONAL','PROJECT','TOPIC','TASK')),
  project_id uuid NULL REFERENCES projects(project_id),
  topic_id uuid NULL REFERENCES topics(topic_id),
  task_id uuid NULL REFERENCES department_tasks(task_id),
  title text NOT NULL,
  deadline_at timestamptz NULL,
  priority text NOT NULL CHECK(priority IN ('LOW','MEDIUM','HIGH','URGENT')),
  status text NOT NULL CHECK(status IN ('OPEN','IN_PROGRESS','DONE','CANCELLED')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- AUTO_FINAL_TARGET_ADD_COLUMN_CLOSURE_BEGIN
-- Generated from every ADD COLUMN in migrations 0002-0007 so canonical final target and clean-install converge.
ALTER TABLE access_reviews ADD COLUMN IF NOT EXISTS assignment_scope jsonb NOT NULL DEFAULT '{}'::jsonb; -- source 0003_account_permission_authorization.sql
ALTER TABLE access_reviews ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES users(user_id); -- source 0003_account_permission_authorization.sql
ALTER TABLE account_permission_assignments ADD COLUMN IF NOT EXISTS approval_required boolean NOT NULL DEFAULT false; -- source 0003_account_permission_authorization.sql
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS continuity_validation jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS mask_ref jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS preserve_regions jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS provider_compiled_prompt_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS resulting_asset_version_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS revision_instruction jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS rights_validation jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE asset_patches ADD COLUMN IF NOT EXISTS semantic_region text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE candidate_blocks ADD COLUMN IF NOT EXISTS block_type text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE candidate_blocks ADD COLUMN IF NOT EXISTS ordinal integer NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE candidate_blocks ADD COLUMN IF NOT EXISTS parent_block_id text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE candidate_patch_sets ADD COLUMN IF NOT EXISTS resulting_candidate_version_ref text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE candidate_patch_sets ADD COLUMN IF NOT EXISTS selected_patch_ids jsonb NOT NULL DEFAULT '[]'::jsonb; -- source 0006_deployment_ready_closure.sql
ALTER TABLE candidate_patches ADD COLUMN IF NOT EXISTS created_by_subject_type text NOT NULL CHECK(created_by_subject_type IN ('USER','SERVICE_IDENTITY')); -- source 0006_deployment_ready_closure.sql
ALTER TABLE candidate_patches ADD COLUMN IF NOT EXISTS preserve_other_blocks boolean NOT NULL DEFAULT true; -- source 0006_deployment_ready_closure.sql
ALTER TABLE chapter_versions ADD COLUMN IF NOT EXISTS estimated_duration_seconds integer NULL CHECK(estimated_duration_seconds > 0); -- source 0006_deployment_ready_closure.sql
ALTER TABLE chapter_versions ADD COLUMN IF NOT EXISTS production_complexity text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_ledger_entries ADD COLUMN IF NOT EXISTS effective_from_ref text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_ledger_entries ADD COLUMN IF NOT EXISTS source_episode_chapter_scene_ref text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_ledger_entries ADD COLUMN IF NOT EXISTS subject_ref text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_ledger_entries ADD COLUMN IF NOT EXISTS superseded_by_ref text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS candidate_state jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS canon_refs jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS confirmed_items jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS decision_refs jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS forbidden_changes jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS message_range jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS reference_refs jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS revision_requirements jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS todo_refs jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE continuity_snapshots ADD COLUMN IF NOT EXISTS unresolved_issues jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS blueprint_version_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS decision_request_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(); -- source 0006_deployment_ready_closure.sql
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS created_by_subject_type text NOT NULL CHECK(created_by_subject_type IN ('USER','SERVICE_IDENTITY')); -- source 0006_deployment_ready_closure.sql
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS provider_job_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS root_cause jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS source_blueprint_version_id uuid NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS source_instruction_package_id uuid NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE correction_script_versions ADD COLUMN IF NOT EXISTS target_department text NOT NULL CHECK(target_department IN ('ASSET','VIDEO','EDITING','VOICE')); -- source 0006_deployment_ready_closure.sql
ALTER TABLE department_tasks ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id); -- source 0004_r9_finalization.sql
ALTER TABLE department_tasks ADD COLUMN IF NOT EXISTS output_contract_hash char(64); -- source 0004_r9_finalization.sql
ALTER TABLE department_tasks ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id); -- source 0004_r9_finalization.sql
ALTER TABLE department_tasks ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id); -- source 0004_r9_finalization.sql
ALTER TABLE department_tasks ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id); -- source 0004_r9_finalization.sql
ALTER TABLE dna_version_references ADD COLUMN IF NOT EXISTS checksum char(64) NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE dna_versions ADD COLUMN IF NOT EXISTS lock_decision_request_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE dna_versions ADD COLUMN IF NOT EXISTS parent_dna_version_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS blend_mode text NOT NULL DEFAULT 'NORMAL'; -- source 0006_deployment_ready_closure.sql
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS locked boolean NOT NULL DEFAULT false; -- source 0006_deployment_ready_closure.sql
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS mask_ref jsonb NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS opacity numeric(5,2) NOT NULL DEFAULT 100 CHECK(opacity BETWEEN 0 AND 100); -- source 0006_deployment_ready_closure.sql
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS parent_layer_id text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS source_ref jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS transform jsonb NOT NULL DEFAULT '{}'::jsonb; -- source 0006_deployment_ready_closure.sql
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS visible boolean NOT NULL DEFAULT true; -- source 0006_deployment_ready_closure.sql
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS z_index integer NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE editing_runtime_runs ADD COLUMN IF NOT EXISTS timeline_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE execution_bundle_steps ADD COLUMN IF NOT EXISTS completed_at timestamptz NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE execution_bundle_steps ADD COLUMN IF NOT EXISTS result_ref text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE execution_bundle_steps ADD COLUMN IF NOT EXISTS started_at timestamptz NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE execution_bundles ADD COLUMN IF NOT EXISTS completed_at timestamptz NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE handoffs ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id); -- source 0004_r9_finalization.sql
ALTER TABLE handoffs ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id); -- source 0004_r9_finalization.sql
ALTER TABLE handoffs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id); -- source 0004_r9_finalization.sql
ALTER TABLE handoffs ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id); -- source 0004_r9_finalization.sql
ALTER TABLE handoffs ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id); -- source 0004_r9_finalization.sql
ALTER TABLE meeting_participants ADD COLUMN IF NOT EXISTS actual_model text NULL; -- source 0005_r9_final_correction.sql
ALTER TABLE meeting_participants ADD COLUMN IF NOT EXISTS actual_provider text NULL; -- source 0005_r9_final_correction.sql
ALTER TABLE meeting_participants ADD COLUMN IF NOT EXISTS allow_substitution boolean NOT NULL DEFAULT false; -- source 0005_r9_final_correction.sql
ALTER TABLE meeting_participants ADD COLUMN IF NOT EXISTS participant_perspective text NULL; -- source 0005_r9_final_correction.sql
ALTER TABLE meeting_participants ADD COLUMN IF NOT EXISTS requested_model text NULL; -- source 0005_r9_final_correction.sql
ALTER TABLE meeting_participants ADD COLUMN IF NOT EXISTS requested_provider text NULL; -- source 0005_r9_final_correction.sql
ALTER TABLE meeting_participants ADD COLUMN IF NOT EXISTS substitution_trace jsonb NOT NULL DEFAULT '{}'::jsonb; -- source 0005_r9_final_correction.sql
ALTER TABLE meeting_rounds ADD COLUMN IF NOT EXISTS peer_visibility_allowed boolean NOT NULL DEFAULT false; -- source 0006_deployment_ready_closure.sql
ALTER TABLE meeting_summaries ADD COLUMN IF NOT EXISTS decision_links jsonb NOT NULL DEFAULT '[]'::jsonb; -- source 0006_deployment_ready_closure.sql
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS agenda jsonb NOT NULL DEFAULT '{}'::jsonb; -- source 0005_r9_final_correction.sql
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS candidate_group_ref text NULL; -- source 0005_r9_final_correction.sql
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS context_snapshot_id uuid NULL; -- source 0005_r9_final_correction.sql
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_version integer NOT NULL DEFAULT 1; -- source 0005_r9_final_correction.sql
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS route_mode text NOT NULL DEFAULT 'SINGLE' CHECK(route_mode IN ('SINGLE','MULTI_AI')); -- source 0005_r9_final_correction.sql
ALTER TABLE memberships ADD COLUMN IF NOT EXISTS position_label text NULL; -- source 0003_account_permission_authorization.sql
ALTER TABLE multi_ai_context_snapshots ADD COLUMN IF NOT EXISTS immutable boolean NOT NULL DEFAULT true; -- source 0006_deployment_ready_closure.sql
ALTER TABLE notebook_entries ADD COLUMN IF NOT EXISTS blueprint_version_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE notebook_entries ADD COLUMN IF NOT EXISTS decision_request_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE notebooks ADD COLUMN IF NOT EXISTS project_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE notebooks ADD COLUMN IF NOT EXISTS topic_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE permission_resources ADD COLUMN IF NOT EXISTS active boolean NOT NULL DEFAULT true; -- source 0003_account_permission_authorization.sql
ALTER TABLE permission_resources ADD COLUMN IF NOT EXISTS allowed_actions jsonb NOT NULL DEFAULT '[]'::jsonb; -- source 0003_account_permission_authorization.sql
ALTER TABLE permission_resources ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(); -- source 0003_account_permission_authorization.sql
ALTER TABLE permission_resources ADD COLUMN IF NOT EXISTS risk_tier text NOT NULL DEFAULT 'STANDARD' CHECK(risk_tier IN ('STANDARD','HIGH')); -- source 0003_account_permission_authorization.sql
ALTER TABLE provider_candidate_groups ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(); -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS api_request_hash char(64) NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS canonical_instruction_id uuid NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS model_id text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS provider_compiler_version text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS provider_id text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS source_script_version text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_compiled_prompts ADD COLUMN IF NOT EXISTS status text NOT NULL CHECK(status IN ('CANDIDATE','APPROVED_FOR_EXECUTION','SUPERSEDED','REJECTED')); -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_jobs ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id); -- source 0004_r9_finalization.sql
ALTER TABLE provider_jobs ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id); -- source 0004_r9_finalization.sql
ALTER TABLE provider_jobs ADD COLUMN IF NOT EXISTS output_contract_hash char(64); -- source 0004_r9_finalization.sql
ALTER TABLE provider_jobs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id); -- source 0004_r9_finalization.sql
ALTER TABLE provider_jobs ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id); -- source 0004_r9_finalization.sql
ALTER TABLE provider_jobs ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id); -- source 0004_r9_finalization.sql
ALTER TABLE provider_prompt_profiles ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now(); -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_prompt_profiles ADD COLUMN IF NOT EXISTS forbidden_fields jsonb NOT NULL DEFAULT '[]'::jsonb; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_quarantines ADD COLUMN IF NOT EXISTS cleared_at timestamptz NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_route_preflights ADD COLUMN IF NOT EXISTS actual_model text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_route_preflights ADD COLUMN IF NOT EXISTS actual_provider text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_route_preflights ADD COLUMN IF NOT EXISTS requested_model text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE provider_route_preflights ADD COLUMN IF NOT EXISTS requested_provider text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE publish_requests ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id); -- source 0004_r9_finalization.sql
ALTER TABLE publish_requests ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id); -- source 0004_r9_finalization.sql
ALTER TABLE publish_requests ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id); -- source 0004_r9_finalization.sql
ALTER TABLE publish_requests ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id); -- source 0004_r9_finalization.sql
ALTER TABLE publish_requests ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id); -- source 0004_r9_finalization.sql
ALTER TABLE qa_review_runs ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id); -- source 0004_r9_finalization.sql
ALTER TABLE qa_review_runs ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id); -- source 0004_r9_finalization.sql
ALTER TABLE qa_review_runs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id); -- source 0004_r9_finalization.sql
ALTER TABLE qa_review_runs ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id); -- source 0004_r9_finalization.sql
ALTER TABLE qa_review_runs ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id); -- source 0004_r9_finalization.sql
ALTER TABLE release_packages ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id); -- source 0004_r9_finalization.sql
ALTER TABLE release_packages ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id); -- source 0004_r9_finalization.sql
ALTER TABLE release_packages ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id); -- source 0004_r9_finalization.sql
ALTER TABLE release_packages ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id); -- source 0004_r9_finalization.sql
ALTER TABLE release_packages ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id); -- source 0004_r9_finalization.sql
ALTER TABLE scorecards ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id); -- source 0004_r9_finalization.sql
ALTER TABLE scorecards ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id); -- source 0004_r9_finalization.sql
ALTER TABLE scorecards ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id); -- source 0004_r9_finalization.sql
ALTER TABLE scorecards ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id); -- source 0004_r9_finalization.sql
ALTER TABLE scorecards ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id); -- source 0004_r9_finalization.sql
ALTER TABLE story_candidate_comparisons ADD COLUMN IF NOT EXISTS audit_event_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidate_comparisons ADD COLUMN IF NOT EXISTS decided_at timestamptz NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidate_comparisons ADD COLUMN IF NOT EXISTS decided_by uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidate_comparisons ADD COLUMN IF NOT EXISTS human_decision text NULL CHECK(human_decision IN ('ADOPT','MERGE','REQUEST_REVISION','REJECT')); -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS character_space text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS foreshadowing_capacity text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS generated_by_subject_type text NOT NULL CHECK(generated_by_subject_type IN ('USER','SERVICE_IDENTITY')); -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS long_form_extension text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS market_positioning text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS production_cost text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS production_risk text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS recommendation text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS strengths jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS weaknesses jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_candidates ADD COLUMN IF NOT EXISTS wizard_session_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS audience_promise text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS core_conflict text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS emotional_core text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS ending_direction text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS forbidden_direction text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS genre text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS logline text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS main_hook text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS narrative_style text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS premise text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS source_candidate_id uuid NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS story_goal text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS theme text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS title text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE story_core_versions ADD COLUMN IF NOT EXISTS tone text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE task_outputs ADD COLUMN IF NOT EXISTS blueprint_version_id uuid REFERENCES blueprint_versions(blueprint_version_id); -- source 0004_r9_finalization.sql
ALTER TABLE task_outputs ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id); -- source 0004_r9_finalization.sql
ALTER TABLE task_outputs ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id); -- source 0004_r9_finalization.sql
ALTER TABLE task_outputs ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id); -- source 0004_r9_finalization.sql
ALTER TABLE task_outputs ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id); -- source 0004_r9_finalization.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS blueprint_validation jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS clip_id text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS continuity_validation jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS dna_validation jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS end_timecode text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS fps numeric(8,3) NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS frame_end integer NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS frame_start integer NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS layer_id text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS minimum_impact_plan jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS region_mask_ref jsonb NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS rights_validation jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS scope_type text NOT NULL CHECK(scope_type IN ('SINGLE_FRAME','FRAME_RANGE','SHOT_RANGE','CLIP_RANGE')); -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS shot_id text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS start_timecode text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE video_timecode_patches ADD COLUMN IF NOT EXISTS track_id text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS accent text NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS emotion text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS emotion_ratio numeric(5,2) NOT NULL CHECK(emotion_ratio BETWEEN 0 AND 100); -- source 0006_deployment_ready_closure.sql
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS intensity numeric(6,3) NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS pause_profile jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS pitch numeric(6,3) NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS sentence_alignment jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS speed numeric(6,3) NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE voice_runtime_profiles ADD COLUMN IF NOT EXISTS timing jsonb NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE work_packages ADD COLUMN IF NOT EXISTS goal_id uuid REFERENCES topic_production_goals(production_goal_id); -- source 0004_r9_finalization.sql
ALTER TABLE work_packages ADD COLUMN IF NOT EXISTS output_contract_hash char(64); -- source 0004_r9_finalization.sql
ALTER TABLE work_packages ADD COLUMN IF NOT EXISTS production_contract_id uuid REFERENCES topic_production_contracts(topic_production_contract_id); -- source 0004_r9_finalization.sql
ALTER TABLE work_packages ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES projects(project_id); -- source 0004_r9_finalization.sql
ALTER TABLE work_packages ADD COLUMN IF NOT EXISTS topic_id uuid REFERENCES topics(topic_id); -- source 0004_r9_finalization.sql
ALTER TABLE world_bible_versions ADD COLUMN IF NOT EXISTS world_name text NOT NULL; -- source 0006_deployment_ready_closure.sql
ALTER TABLE world_canon_rules ADD COLUMN IF NOT EXISTS enforcement text NOT NULL CHECK(enforcement IN ('INSTRUCTION_PACKAGE_REQUIRED','VARIATION_RATIONALE_REQUIRED')); -- source 0006_deployment_ready_closure.sql
-- AUTO_FINAL_TARGET_ADD_COLUMN_CLOSURE_END

-- ACPOS Unit 8 dedicated Provider Router runtime persistence (R9).
-- Unit 8 Provider Router / Prompt Adapter / Waste Guard dedicated runtime persistence.
CREATE TABLE IF NOT EXISTS acpos_runtime.provider_compiled_prompts(
  id text PRIMARY KEY,
  canonical_instruction_id text NOT NULL,
  provider_profile_id text NOT NULL REFERENCES acpos_runtime.provider_profiles(id),
  provider_id text NOT NULL,
  model_id text NOT NULL,
  profile_version integer NOT NULL,
  adapter_type text NOT NULL,
  compiled_prompt text NOT NULL,
  compiled_prompt_hash char(64) NOT NULL,
  api_request_payload jsonb NOT NULL,
  api_request_hash char(64) NOT NULL,
  scoped_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  blueprint_version_id text NULL,
  dna_version_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  source_compiled_prompt_id text NULL REFERENCES acpos_runtime.provider_compiled_prompts(id),
  fallback_recompiled boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS acpos_runtime.provider_route_preflights(
  id text PRIMARY KEY,
  candidate_group_id text NOT NULL REFERENCES acpos_runtime.provider_groups(id),
  use_case text NOT NULL,
  status text NOT NULL CHECK(status IN ('READY','BLOCKED')),
  eligible_members jsonb NOT NULL DEFAULT '[]'::jsonb,
  rejected_members jsonb NOT NULL DEFAULT '[]'::jsonb,
  checks_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  reason text NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS acpos_runtime.provider_quality_observations(
  id text PRIMARY KEY,
  member_id text NOT NULL REFERENCES acpos_runtime.provider_members(id),
  use_case text NOT NULL,
  attempts integer NOT NULL DEFAULT 0,
  valid_results integer NOT NULL DEFAULT 0,
  invalid_results integer NOT NULL DEFAULT 0,
  errors integer NOT NULL DEFAULT 0,
  success_rate numeric(10,6) NOT NULL DEFAULT 1,
  valid_result_rate numeric(10,6) NOT NULL DEFAULT 1,
  error_rate numeric(10,6) NOT NULL DEFAULT 0,
  last_latency_ms integer NULL,
  last_error_code text NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(member_id,use_case)
);
CREATE TABLE IF NOT EXISTS acpos_runtime.provider_route_decisions(
  id text PRIMARY KEY,
  candidate_group_id text NOT NULL REFERENCES acpos_runtime.provider_groups(id),
  preflight_id text NOT NULL REFERENCES acpos_runtime.provider_route_preflights(id),
  status text NOT NULL,
  reason text NULL,
  selected_member_id text NULL REFERENCES acpos_runtime.provider_members(id),
  provider_id text NULL,
  model_id text NULL,
  attempt_count integer NOT NULL DEFAULT 0,
  fallback_count integer NOT NULL DEFAULT 0,
  estimated_cost_waste numeric(20,8) NOT NULL DEFAULT 0,
  payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS acpos_runtime.provider_route_attempts(
  id text PRIMARY KEY,
  route_decision_id text NOT NULL REFERENCES acpos_runtime.provider_route_decisions(id),
  preflight_id text NOT NULL REFERENCES acpos_runtime.provider_route_preflights(id),
  candidate_group_id text NOT NULL REFERENCES acpos_runtime.provider_groups(id),
  member_id text NOT NULL REFERENCES acpos_runtime.provider_members(id),
  provider_profile_id text NOT NULL REFERENCES acpos_runtime.provider_profiles(id),
  compiled_prompt_id text NOT NULL REFERENCES acpos_runtime.provider_compiled_prompts(id),
  provider_id text NOT NULL,
  model_id text NOT NULL,
  attempt_no integer NOT NULL,
  same_provider_attempt_no integer NOT NULL,
  fallback_no integer NOT NULL DEFAULT 0,
  status text NOT NULL,
  latency_ms integer NULL,
  estimated_cost numeric(20,8) NOT NULL DEFAULT 0,
  result_hash char(64) NULL,
  error_code text NULL,
  evidence_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(route_decision_id,attempt_no)
);
CREATE TABLE IF NOT EXISTS acpos_runtime.provider_profile_tests(
  id text PRIMARY KEY,
  profile_id text NOT NULL REFERENCES acpos_runtime.provider_profiles(id),
  status text NOT NULL,
  dry_run boolean NOT NULL DEFAULT false,
  compiled_payload_hash char(64) NULL,
  result_hash char(64) NULL,
  error_code text NULL,
  evidence_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_provider_route_preflights_group ON acpos_runtime.provider_route_preflights(candidate_group_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_provider_route_attempts_decision ON acpos_runtime.provider_route_attempts(route_decision_id,attempt_no);
CREATE INDEX IF NOT EXISTS idx_provider_profile_tests_profile ON acpos_runtime.provider_profile_tests(profile_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_provider_quality_member_usecase ON acpos_runtime.provider_quality_observations(member_id,use_case);



-- R9 Enterprise/Social/Outreach canonical closure 0015
CREATE TABLE IF NOT EXISTS outreach_discovery_jobs (
  discovery_job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), job_name text NOT NULL, mode text NOT NULL CHECK(mode IN ('CONTINUOUS','SINGLE_RUN')), search_scope jsonb NOT NULL, allowed_sources jsonb NOT NULL, interval_seconds integer NOT NULL DEFAULT 3600 CHECK(interval_seconds >= 60), result_limit integer NULL CHECK(result_limit IS NULL OR result_limit > 0), status text NOT NULL CHECK(status IN ('DRAFT','RUNNING','PAUSED','STOPPED','COMPLETED','FAILED','WAITING_CONNECTOR')), stats jsonb NOT NULL DEFAULT '{}'::jsonb, started_at timestamptz NULL, stopped_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS company_master_entities (
  company_master_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), jurisdiction text NULL, registration_id text NULL, current_name text NOT NULL, aliases jsonb NOT NULL DEFAULT '[]'::jsonb, classification jsonb NOT NULL DEFAULT '{}'::jsonb, status text NOT NULL DEFAULT 'ACTIVE', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(jurisdiction,registration_id)
);
CREATE TABLE IF NOT EXISTS company_contact_points (
  contact_point_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_master_id uuid NOT NULL REFERENCES company_master_entities(company_master_id), contact_type text NOT NULL CHECK(contact_type IN ('PHONE','EMAIL','ADDRESS','DOMAIN','WEBSITE','SOCIAL')), value text NOT NULL, normalized_value text NOT NULL, source_evidence jsonb NOT NULL, is_primary boolean NOT NULL DEFAULT false, verification_status text NOT NULL DEFAULT 'UNVERIFIED', first_seen_at timestamptz NOT NULL DEFAULT now(), last_seen_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_master_id,contact_type,normalized_value)
);
CREATE TABLE IF NOT EXISTS outreach_campaigns (
  campaign_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), campaign_name text NOT NULL, message_version_id text NOT NULL, sender_account_id text NOT NULL, status text NOT NULL CHECK(status IN ('DRAFT','REVIEW','APPROVED','QUEUED','SENDING','COMPLETED','STOPPED','FAILED')), schedule_policy jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now(), approved_at timestamptz NULL
);
CREATE TABLE IF NOT EXISTS outreach_email_deliveries (
  delivery_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), campaign_id uuid NOT NULL REFERENCES outreach_campaigns(campaign_id), company_master_id uuid NULL REFERENCES company_master_entities(company_master_id), recipient_contact_id uuid NULL REFERENCES company_contact_points(contact_point_id), recipient_email text NOT NULL, message_id text NOT NULL UNIQUE, to_count integer NOT NULL DEFAULT 1 CHECK(to_count=1), cc jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_array_length(cc)=0), bcc jsonb NOT NULL DEFAULT '[]'::jsonb CHECK(jsonb_array_length(bcc)=0), status text NOT NULL DEFAULT 'QUEUED', delivery_status text NULL, bounce_status text NULL, reply_status text NULL, suppression_status text NULL, created_at timestamptz NOT NULL DEFAULT now(), sent_at timestamptz NULL, UNIQUE(campaign_id,recipient_email)
);
CREATE TABLE IF NOT EXISTS social_account_bindings (
  social_account_binding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), platform_key text NOT NULL, display_name text NOT NULL, login_identifier_masked text NOT NULL, auth_mode text NOT NULL CHECK(auth_mode IN ('OFFICIAL_OAUTH_OR_TOKEN','MANUAL_BROWSER_CREDENTIAL','CUSTOM_SECRET')), secret_reference_id uuid NULL REFERENCES secret_references(secret_reference_id), external_account_ref text NULL, status text NOT NULL CHECK(status IN ('UNBOUND','CONFIGURED','BOUND_LOCKED','HEALTHY','REAUTH_REQUIRED','DISABLED','REVOKED')), locked_at timestamptz NULL, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS social_target_discovery_jobs (
  discovery_job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), platform_key text NOT NULL, target_types jsonb NOT NULL, categories jsonb NOT NULL, keywords jsonb NOT NULL, filters jsonb NOT NULL DEFAULT '{}'::jsonb, mode text NOT NULL CHECK(mode IN ('CONTINUOUS','SINGLE_RUN')), status text NOT NULL DEFAULT 'RUNNING', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS social_market_targets (
  social_target_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), platform_key text NOT NULL, target_type text NOT NULL CHECK(target_type IN ('OWN_MANAGED_PAGE','MARKET_PAGE','MARKET_GROUP','ACCOUNT','CHANNEL','OTHER')), target_name text NOT NULL, target_url text NOT NULL, category text NULL, scale bigint NULL, capability jsonb NOT NULL DEFAULT '{}'::jsonb, join_status text NOT NULL DEFAULT 'DISCOVERED', posting_policy jsonb NOT NULL DEFAULT '{}'::jsonb, last_posted_at timestamptz NULL, next_eligible_at timestamptz NULL, status text NOT NULL DEFAULT 'ACTIVE', UNIQUE(platform_key,target_url)
);
CREATE TABLE IF NOT EXISTS social_manual_actions (
  manual_action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), social_target_id uuid NULL REFERENCES social_market_targets(social_target_id), social_account_binding_id uuid NULL REFERENCES social_account_bindings(social_account_binding_id), action_type text NOT NULL, reason text NOT NULL, target_url text NULL, status text NOT NULL CHECK(status IN ('OPEN','PENDING_ADMIN_APPROVAL','COMPLETED','FAILED')), completion_note text NULL, created_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz NULL
);

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0001_canonical_schema', '77754f170df227354c86083085256c62f6696c6153ec4399cca1f92819766ee1', 'migration-runner', 'CR-SCHEMA-0001')
ON CONFLICT (migration_id) DO NOTHING;
