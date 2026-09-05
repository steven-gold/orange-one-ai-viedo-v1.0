-- R9 Unit 17 ERP canonical runtime hardening. No parallel ERP tables are created.
-- Raw credentials remain forbidden; connectors retain only secret_reference_id.
ALTER TABLE erp_sync_jobs ADD COLUMN IF NOT EXISTS data_classification text NOT NULL DEFAULT 'INTERNAL';
ALTER TABLE erp_sync_jobs ADD COLUMN IF NOT EXISTS snapshot_type text NOT NULL DEFAULT 'GENERAL';
ALTER TABLE erp_sync_jobs ADD COLUMN IF NOT EXISTS attempt_no integer NOT NULL DEFAULT 1 CHECK(attempt_no > 0);
ALTER TABLE erp_sync_jobs ADD COLUMN IF NOT EXISTS external_evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE erp_sync_jobs DROP CONSTRAINT IF EXISTS erp_sync_jobs_status_check;
ALTER TABLE erp_sync_jobs ADD CONSTRAINT erp_sync_jobs_status_check CHECK(status IN ('NOT_REQUESTED','QUEUED','RUNNING','COMPLETED','PARTIAL','FAILED','RETRY_PENDING','CANCELLED','PENDING_EXTERNAL'));
ALTER TABLE erp_snapshots ADD COLUMN IF NOT EXISTS external_result_verified boolean NOT NULL DEFAULT false;
ALTER TABLE erp_snapshots ADD COLUMN IF NOT EXISTS external_evidence_refs jsonb NOT NULL DEFAULT '[]'::jsonb;
CREATE INDEX IF NOT EXISTS idx_erp_sync_jobs_connector_status ON erp_sync_jobs(erp_connector_id,status,requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_erp_snapshots_connector_created ON erp_snapshots(erp_connector_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_erp_failures_job ON erp_failures(erp_sync_job_id,occurred_at DESC);

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0013_erp_runtime_closure', '013a0c7e815b0efd398dfe60869d03cc4abeb3afd045bc3f8325d3c5bb04a100', 'migration-runner', 'CR-R9-0013')
ON CONFLICT (migration_id) DO NOTHING;
