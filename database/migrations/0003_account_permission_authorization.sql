-- ACPOS migration 0003: replace Role-based Authorization Source with Account Permission Assignments.
-- Preconditions: approved CR-AUTH-0003, backup_ref, validated Account Permission Catalog import, and an explicit user-by-user migration decision.
ALTER TYPE actor_type ADD VALUE IF NOT EXISTS 'SERVICE_IDENTITY';
ALTER TYPE classification_level ADD VALUE IF NOT EXISTS 'RESTRICTED_FINANCE';

ALTER TABLE permission_resources DROP CONSTRAINT IF EXISTS permission_resources_resource_type_check;
ALTER TABLE permission_resources ADD CONSTRAINT permission_resources_resource_type_check CHECK(resource_type IN ('SURFACE','L1','L2','L3','PAGE','SECTION','CONTROL','ACTION','FIELD','API','DECISION'));
ALTER TABLE permission_resources ADD COLUMN IF NOT EXISTS allowed_actions jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE permission_resources ADD COLUMN IF NOT EXISTS active boolean NOT NULL DEFAULT true;
ALTER TABLE permission_resources ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE permission_resources ADD COLUMN IF NOT EXISTS risk_tier text NOT NULL DEFAULT 'STANDARD' CHECK(risk_tier IN ('STANDARD','HIGH'));

CREATE TABLE IF NOT EXISTS account_permission_assignments (
  account_permission_assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES app_users(user_id), resource_id uuid NOT NULL REFERENCES permission_resources(resource_id), action text NOT NULL,
  effect text NOT NULL CHECK(effect IN ('ALLOW','DENY')), scope jsonb NOT NULL, condition jsonb NOT NULL DEFAULT '{}'::jsonb, gate_profile jsonb NOT NULL,
  status acpos_status NOT NULL DEFAULT 'DRAFT', granted_by_user_id uuid NOT NULL REFERENCES app_users(user_id), approval_ref text NOT NULL, version_no integer NOT NULL CHECK(version_no > 0),
  audit_event_id uuid NULL REFERENCES audit_events(audit_event_id), effective_from timestamptz NOT NULL DEFAULT now(), effective_to timestamptz NULL, UNIQUE(user_id, resource_id, action, version_no)
);
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
CREATE TABLE IF NOT EXISTS service_identities (
  service_identity_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), service_identity_key text NOT NULL UNIQUE, owner_service text NOT NULL, status acpos_status NOT NULL DEFAULT 'DRAFT', created_at timestamptz NOT NULL DEFAULT now(), disabled_at timestamptz NULL
);
CREATE TABLE IF NOT EXISTS service_identity_capability_assignments (
  service_capability_assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), service_identity_id uuid NOT NULL REFERENCES service_identities(service_identity_id), capability_key text NOT NULL,
  scope jsonb NOT NULL, condition jsonb NOT NULL DEFAULT '{}'::jsonb, gate_profile jsonb NOT NULL, status acpos_status NOT NULL DEFAULT 'DRAFT', approval_ref text NOT NULL,
  audit_event_id uuid NULL REFERENCES audit_events(audit_event_id), UNIQUE(service_identity_id, capability_key, status)
);
CREATE TABLE IF NOT EXISTS decision_requests (
  decision_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workspace_id uuid NOT NULL REFERENCES workspaces(workspace_id), required_resource_id uuid NOT NULL REFERENCES permission_resources(resource_id), required_action text NOT NULL,
  required_scope jsonb NOT NULL, condition_snapshot jsonb NOT NULL, reason text NOT NULL, evidence_refs jsonb NOT NULL, impact_scope jsonb NOT NULL,
  state text NOT NULL CHECK(state IN ('OPEN','NOTIFIED','APPROVED','REJECTED','MODIFICATION_REQUESTED','CANCELLED')), correlation_id uuid NOT NULL, created_by_actor_type actor_type NOT NULL,
  created_by_user_id uuid NULL REFERENCES app_users(user_id), created_by_service_identity_id uuid NULL REFERENCES service_identities(service_identity_id), decided_by_user_id uuid NULL REFERENCES app_users(user_id), decision_reason text NULL,
  audit_event_id uuid NULL REFERENCES audit_events(audit_event_id), created_at timestamptz NOT NULL DEFAULT now(), decided_at timestamptz NULL,
  CHECK ((created_by_user_id IS NOT NULL) <> (created_by_service_identity_id IS NOT NULL))
);

ALTER TABLE memberships DROP CONSTRAINT IF EXISTS memberships_user_id_department_id_role_bundle_id_key;
ALTER TABLE memberships DROP COLUMN IF EXISTS role_bundle_id;
ALTER TABLE memberships ADD COLUMN IF NOT EXISTS position_label text NULL;
ALTER TABLE memberships ADD CONSTRAINT memberships_user_department_unique UNIQUE(user_id, department_id);
ALTER TABLE access_reviews DROP CONSTRAINT IF EXISTS access_reviews_membership_id_fkey;
ALTER TABLE access_reviews DROP COLUMN IF EXISTS membership_id;
ALTER TABLE access_reviews ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES users(user_id);
ALTER TABLE access_reviews ADD COLUMN IF NOT EXISTS assignment_scope jsonb NOT NULL DEFAULT '{}'::jsonb;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'project_memberships' AND column_name = 'collaboration_role') THEN
    ALTER TABLE project_memberships RENAME COLUMN collaboration_role TO collaboration_label;
  END IF;
END $$;
COMMENT ON COLUMN project_memberships.collaboration_label IS 'NON_AUTHORIZATION_METADATA: collaboration label only; never an Authorization Source.';

-- No AI or migration default may map a Role Bundle to a human account permission assignment.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM user_role_assignments) OR EXISTS (SELECT 1 FROM permission_policies) THEN
    RAISE EXCEPTION 'ACCOUNT_PERMISSION_MIGRATION_MAPPING_REQUIRED';
  END IF;
END $$;
DROP TABLE IF EXISTS user_role_assignments;
DROP TABLE IF EXISTS permission_policies;
DROP TABLE IF EXISTS role_bundles;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0003_account_permission_authorization', '14dbb9540b01ccb33e2f6be3a1e8eac3c8fde5b0216604c86be25ef57dbd6471', 'migration-runner', 'CR-AUTH-0003')
ON CONFLICT (migration_id) DO NOTHING;
