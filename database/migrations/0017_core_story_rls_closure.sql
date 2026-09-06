-- ACPOS migration 0017: Core story project-scope RLS closure.
-- Change ref: CR-RLS-0017
-- Scope: mother lock and story candidate rows are isolated by the existing session-bound project authority.

GRANT SELECT, INSERT, UPDATE, DELETE ON public.mother_locks, public.story_candidates TO acpos_app_runtime;

ALTER TABLE public.mother_locks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_mother_locks_select ON public.mother_locks;
DROP POLICY IF EXISTS acpos_mother_locks_write ON public.mother_locks;
CREATE POLICY acpos_mother_locks_select ON public.mother_locks
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_project(project_id));
CREATE POLICY acpos_mother_locks_write ON public.mother_locks
FOR ALL TO acpos_app_runtime
USING (acpos_runtime.can_manage_project(project_id))
WITH CHECK (acpos_runtime.can_manage_project(project_id));

ALTER TABLE public.story_candidates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_story_candidates_select ON public.story_candidates;
DROP POLICY IF EXISTS acpos_story_candidates_write ON public.story_candidates;
CREATE POLICY acpos_story_candidates_select ON public.story_candidates
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_project(project_id));
CREATE POLICY acpos_story_candidates_write ON public.story_candidates
FOR ALL TO acpos_app_runtime
USING (acpos_runtime.can_manage_project(project_id))
WITH CHECK (acpos_runtime.can_manage_project(project_id));

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES (
  '0017_core_story_rls_closure',
  '7530585a9c2b6c2a3e1890fb858d4f24d5c838a52cbd556f9b64427d6f5382ba',
  'migration-runner',
  'CR-RLS-0017'
)
ON CONFLICT (migration_id) DO NOTHING;
