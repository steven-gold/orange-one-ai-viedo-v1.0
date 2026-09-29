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

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0008_provider_router_runtime_closure', '8f02fb981bc99fe89cba00ae0292c7fac8437ea4de812b3ad66967975422fbec', 'migration-runner', 'CR-R9-0008')
ON CONFLICT (migration_id) DO NOTHING;
