-- ACPOS migration 0040: KB-01 KnowledgeSource retire audit RLS closure.
-- Extends 0036 without bypassing the session-bound acpos_app_runtime role.
-- Current Authority: DRAFT,ACTIVE,PAUSED -> RETIRED via retireKnowledgeSource / SOURCE-RETIRE.
-- Reuses public.knowledge_sources and public.audit_events. No new table, synthetic row, or provider path.

GRANT SELECT, INSERT ON public.audit_events TO acpos_app_runtime;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_audit_events_kb_insert ON public.audit_events;
CREATE POLICY acpos_audit_events_kb_insert ON public.audit_events
FOR INSERT TO acpos_app_runtime
WITH CHECK(
  entity_type='admin:KB-01'
  AND actor_id=acpos_runtime.current_actor_user_id()
  AND action IN(
    'knowledge.source.created',
    'knowledge.source.updated',
    'knowledge.source.paused',
    'knowledge.source.resumed',
    'knowledge.source.retired'
  )
  AND (acpos_runtime.current_actor_is_bootstrap_admin() OR acpos_runtime.can_configure_knowledge_source())
);

DO $$
DECLARE policy_count bigint;
BEGIN
  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public'
    AND (
      (tablename='knowledge_sources' AND policyname IN(
        'acpos_knowledge_sources_configure_select','acpos_knowledge_sources_configure_update','acpos_knowledge_sources_configure_insert'
      ))
      OR (tablename='audit_events' AND policyname IN('acpos_audit_events_kb_select','acpos_audit_events_kb_insert'))
    );
  IF policy_count<>5 THEN RAISE EXCEPTION 'KB0040_RLS_POLICY_COUNT_MISMATCH:%',policy_count; END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES('0040_kb_source_retire_audit_rls_closure','301dbcfd2f65def360d8f6f128f0b4010c390c09155db7bc2a3ec07d4f9e4d50','migration-runner','CR-KB-0040-PENDING-PRODUCTION-APPLY')
ON CONFLICT(migration_id) DO NOTHING;
