-- R9 Unit 41 Production Goal governance and DAG routing schema closure.
-- Strengthens the existing canonical topic_production_goals table; no parallel goal table is created.
ALTER TABLE topic_production_goals ADD COLUMN IF NOT EXISTS asset_strategy jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE topic_production_goals ADD COLUMN IF NOT EXISTS acceptance_criteria_refs jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE topic_production_goals DROP CONSTRAINT IF EXISTS topic_production_goals_production_type_check;
ALTER TABLE topic_production_goals ADD CONSTRAINT topic_production_goals_production_type_check CHECK(production_type IN ('COMIC','VIDEO','ASSET','AD_VIDEO','AD_ASSET','OTHER'));

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES ('0014_production_goal_routing_closure', 'f6ece41036e85611231688cda4d1106cf7b2a29086dea1a173ea42fed9abcea8', 'migration-runner', 'CR-R9-0014')
ON CONFLICT (migration_id) DO NOTHING;
