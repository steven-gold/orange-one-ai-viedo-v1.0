-- R9 Runtime Layer closure upgrade for already-created runtime stores.
ALTER TABLE acpos_runtime.layers ADD COLUMN IF NOT EXISTS layer_name text;
UPDATE acpos_runtime.layers SET layer_name=COALESCE(NULLIF(layer_name,''),NULLIF(semantic_target,''),layer_type,id) WHERE layer_name IS NULL OR layer_name='';
ALTER TABLE acpos_runtime.layers ALTER COLUMN layer_name SET NOT NULL;

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0009_layer_runtime_closure', '4813cb8b052898e66e6d0d2090dead04785f7f264f97c799614cf4751cb00746', 'migration-runner', 'CR-R9-0009')
ON CONFLICT (migration_id) DO NOTHING;
