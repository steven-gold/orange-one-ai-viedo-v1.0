-- R9 Canonical Layer closure upgrade for already-created domain stores.
ALTER TABLE document_layers ADD COLUMN IF NOT EXISTS layer_name text;
UPDATE document_layers SET layer_name=COALESCE(NULLIF(layer_name,''),NULLIF(semantic_target,''),layer_id) WHERE layer_name IS NULL OR layer_name='';
ALTER TABLE document_layers ALTER COLUMN layer_name SET NOT NULL;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0010_layer_canonical_closure', 'ec2efe83b42fe135f9dac81f058876c6e90291b760106a2a7e3c08a47ffc267b', 'migration-runner', 'CR-R9-0010')
ON CONFLICT (migration_id) DO NOTHING;
