-- ACPOS migration 0002: Phase B contract hardening.
-- Preconditions: migration 0001 applied, orphan scan is zero, approved CR-SCHEMA-0002, restore point recorded.
ALTER TABLE topics ALTER COLUMN mother_lock_id SET NOT NULL;
ALTER TABLE department_tasks ALTER COLUMN child_lock_id SET NOT NULL;
ALTER TABLE department_tasks ALTER COLUMN topic_production_contract_id SET NOT NULL;
ALTER TABLE department_tasks ALTER COLUMN production_goal_id SET NOT NULL;
ALTER TABLE department_tasks ALTER COLUMN output_contract_hash SET NOT NULL;
ALTER TABLE task_input_manifests ALTER COLUMN department_script_view_id SET NOT NULL;
ALTER TABLE instruction_packages ALTER COLUMN task_input_manifest_id SET NOT NULL;
ALTER TABLE task_outputs ALTER COLUMN production_goal_id SET NOT NULL;
ALTER TABLE task_outputs ALTER COLUMN output_contract_hash SET NOT NULL;
ALTER TABLE scorecards ALTER COLUMN production_goal_id SET NOT NULL;
ALTER TABLE scorecards ALTER COLUMN output_contract_hash SET NOT NULL;
ALTER TABLE handoffs ALTER COLUMN topic_production_contract_id SET NOT NULL;
ALTER TABLE handoffs ALTER COLUMN production_goal_id SET NOT NULL;
ALTER TABLE handoffs ALTER COLUMN output_contract_hash SET NOT NULL;

CREATE OR REPLACE FUNCTION acpos_prevent_immutable_version_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.immutable_at IS NOT NULL AND (NEW.content_hash IS DISTINCT FROM OLD.content_hash OR NEW.status IS DISTINCT FROM OLD.status) THEN
    RAISE EXCEPTION 'LOCKED_VERSION_IMMUTABLE';
  END IF;
  RETURN NEW;
END;
$$;
CREATE OR REPLACE FUNCTION acpos_prevent_approved_package_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.status = 'APPROVED' AND (NEW.package_hash IS DISTINCT FROM OLD.package_hash OR NEW.compiled_instruction IS DISTINCT FROM OLD.compiled_instruction) THEN
    RAISE EXCEPTION 'INSTRUCTION_PACKAGE_IMMUTABLE';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS trg_project_version_immutable ON project_versions;
CREATE TRIGGER trg_project_version_immutable BEFORE UPDATE ON project_versions FOR EACH ROW EXECUTE FUNCTION acpos_prevent_immutable_version_mutation();
DROP TRIGGER IF EXISTS trg_topic_version_immutable ON topic_versions;
CREATE TRIGGER trg_topic_version_immutable BEFORE UPDATE ON topic_versions FOR EACH ROW EXECUTE FUNCTION acpos_prevent_immutable_version_mutation();
DROP TRIGGER IF EXISTS trg_script_version_immutable ON canonical_script_versions;
CREATE TRIGGER trg_script_version_immutable BEFORE UPDATE ON canonical_script_versions FOR EACH ROW EXECUTE FUNCTION acpos_prevent_immutable_version_mutation();
DROP TRIGGER IF EXISTS trg_instruction_package_immutable ON instruction_packages;
CREATE TRIGGER trg_instruction_package_immutable BEFORE UPDATE ON instruction_packages FOR EACH ROW EXECUTE FUNCTION acpos_prevent_approved_package_mutation();

CREATE OR REPLACE FUNCTION acpos_prevent_task_without_dag() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM dag_nodes WHERE dag_node_id = NEW.dag_node_id) THEN
    RAISE EXCEPTION 'AD_HOC_TASK_FORBIDDEN';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS trg_task_requires_dag ON department_tasks;
CREATE TRIGGER trg_task_requires_dag BEFORE INSERT ON department_tasks FOR EACH ROW EXECUTE FUNCTION acpos_prevent_task_without_dag();

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0002_topic_contract_constraints', '207230ffb9962fc18c3028c2306bf28192c8fa48ff3c50ce72bb58137266adf6', 'migration-runner', 'CR-SCHEMA-0002')
ON CONFLICT (migration_id) DO NOTHING;
