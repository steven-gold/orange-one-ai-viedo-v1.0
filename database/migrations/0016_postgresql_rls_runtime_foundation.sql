-- ACPOS migration 0016: PostgreSQL RLS runtime foundation.
-- Change ref: CR-RLS-0016
-- Scope: non-BYPASSRLS application role, session-bound actor context, and first protected project/permission tables.

DO $
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'acpos_app_runtime') THEN
    CREATE ROLE acpos_app_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
  ELSIF EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = 'acpos_app_runtime'
      AND (rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole OR rolinherit OR rolbypassrls)
  ) THEN
    RAISE EXCEPTION 'ACPOS_RUNTIME_ROLE_SECURITY_MISMATCH';
  END IF;
END
$;
GRANT acpos_app_runtime TO neondb_owner;
GRANT USAGE ON SCHEMA public, acpos_runtime TO acpos_app_runtime;

CREATE OR REPLACE FUNCTION acpos_runtime.current_actor_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT u.user_id
  FROM acpos_runtime.sessions s
  JOIN acpos_runtime.accounts a ON a.id = s.account_id
  JOIN public.app_users u ON lower(u.email::text) = lower(a.email)
  WHERE s.token_hash = NULLIF(current_setting('acpos.session_token_hash', true), '')
    AND s.expires_at > now()
    AND a.status = 'READY'
    AND u.disabled_at IS NULL
  LIMIT 1
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.current_actor_is_bootstrap_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT COALESCE((
    SELECT a.bootstrap_admin
    FROM acpos_runtime.sessions s
    JOIN acpos_runtime.accounts a ON a.id = s.account_id
    JOIN public.app_users u ON lower(u.email::text) = lower(a.email)
    WHERE s.token_hash = NULLIF(current_setting('acpos.session_token_hash', true), '')
      AND s.expires_at > now()
      AND a.status = 'READY'
      AND u.disabled_at IS NULL
    LIMIT 1
  ), false)
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.can_access_project(p_project_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT
    acpos_runtime.current_actor_is_bootstrap_admin()
    OR EXISTS (
      SELECT 1
      FROM public.projects p
      WHERE p.project_id = p_project_id
        AND p.owner_id = acpos_runtime.current_actor_user_id()
    )
    OR EXISTS (
      SELECT 1
      FROM public.project_memberships pm
      WHERE pm.project_id = p_project_id
        AND pm.user_id = acpos_runtime.current_actor_user_id()
        AND pm.status = 'APPROVED'
    )
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.can_manage_project(p_project_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT
    acpos_runtime.current_actor_is_bootstrap_admin()
    OR EXISTS (
      SELECT 1
      FROM public.projects p
      WHERE p.project_id = p_project_id
        AND p.owner_id = acpos_runtime.current_actor_user_id()
    )
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.can_access_conversation(p_conversation_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.conversations c
    WHERE c.conversation_id = p_conversation_id
      AND (
        acpos_runtime.current_actor_is_bootstrap_admin()
        OR c.created_by = acpos_runtime.current_actor_user_id()
        OR acpos_runtime.can_access_project(c.project_id)
      )
  )
$$;

REVOKE ALL ON FUNCTION acpos_runtime.current_actor_user_id() FROM PUBLIC;
REVOKE ALL ON FUNCTION acpos_runtime.current_actor_is_bootstrap_admin() FROM PUBLIC;
REVOKE ALL ON FUNCTION acpos_runtime.can_access_project(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION acpos_runtime.can_manage_project(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION acpos_runtime.can_access_conversation(uuid) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION
  acpos_runtime.current_actor_user_id(),
  acpos_runtime.current_actor_is_bootstrap_admin(),
  acpos_runtime.can_access_project(uuid),
  acpos_runtime.can_manage_project(uuid),
  acpos_runtime.can_access_conversation(uuid)
TO acpos_app_runtime;

GRANT SELECT ON
  public.schema_migration_history,
  public.app_users,
  public.permission_resources,
  public.workspaces
TO acpos_app_runtime;

GRANT SELECT ON acpos_runtime.accounts TO acpos_app_runtime;
GRANT SELECT, INSERT, DELETE ON acpos_runtime.sessions TO acpos_app_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON
  public.account_permission_assignments,
  public.user_ui_preferences,
  public.project_memberships,
  public.projects,
  public.project_versions,
  public.topics,
  public.conversations
TO acpos_app_runtime;

GRANT SELECT, INSERT ON public.conversation_messages TO acpos_app_runtime;

ALTER TABLE public.account_permission_assignments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_assignment_select ON public.account_permission_assignments;
DROP POLICY IF EXISTS acpos_assignment_admin_write ON public.account_permission_assignments;
CREATE POLICY acpos_assignment_select ON public.account_permission_assignments
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR user_id = acpos_runtime.current_actor_user_id()
);
CREATE POLICY acpos_assignment_admin_write ON public.account_permission_assignments
FOR ALL TO acpos_app_runtime
USING (acpos_runtime.current_actor_is_bootstrap_admin())
WITH CHECK (acpos_runtime.current_actor_is_bootstrap_admin());

ALTER TABLE public.user_ui_preferences ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_user_ui_self ON public.user_ui_preferences;
CREATE POLICY acpos_user_ui_self ON public.user_ui_preferences
FOR ALL TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR user_id = acpos_runtime.current_actor_user_id()
)
WITH CHECK (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR user_id = acpos_runtime.current_actor_user_id()
);

ALTER TABLE public.project_memberships ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_project_membership_select ON public.project_memberships;
DROP POLICY IF EXISTS acpos_project_membership_admin_write ON public.project_memberships;
CREATE POLICY acpos_project_membership_select ON public.project_memberships
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR user_id = acpos_runtime.current_actor_user_id()
  OR acpos_runtime.can_access_project(project_id)
);
CREATE POLICY acpos_project_membership_admin_write ON public.project_memberships
FOR ALL TO acpos_app_runtime
USING (acpos_runtime.current_actor_is_bootstrap_admin())
WITH CHECK (acpos_runtime.current_actor_is_bootstrap_admin());

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_projects_select ON public.projects;
DROP POLICY IF EXISTS acpos_projects_insert ON public.projects;
DROP POLICY IF EXISTS acpos_projects_update ON public.projects;
DROP POLICY IF EXISTS acpos_projects_delete ON public.projects;
CREATE POLICY acpos_projects_select ON public.projects
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_project(project_id));
CREATE POLICY acpos_projects_insert ON public.projects
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR owner_id = acpos_runtime.current_actor_user_id()
);
CREATE POLICY acpos_projects_update ON public.projects
FOR UPDATE TO acpos_app_runtime
USING (acpos_runtime.can_manage_project(project_id))
WITH CHECK (acpos_runtime.can_manage_project(project_id));
CREATE POLICY acpos_projects_delete ON public.projects
FOR DELETE TO acpos_app_runtime
USING (acpos_runtime.can_manage_project(project_id));

ALTER TABLE public.project_versions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_project_versions_select ON public.project_versions;
DROP POLICY IF EXISTS acpos_project_versions_write ON public.project_versions;
CREATE POLICY acpos_project_versions_select ON public.project_versions
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_project(project_id));
CREATE POLICY acpos_project_versions_write ON public.project_versions
FOR ALL TO acpos_app_runtime
USING (acpos_runtime.can_manage_project(project_id))
WITH CHECK (acpos_runtime.can_manage_project(project_id));

ALTER TABLE public.topics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_topics_select ON public.topics;
DROP POLICY IF EXISTS acpos_topics_write ON public.topics;
CREATE POLICY acpos_topics_select ON public.topics
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_project(project_id));
CREATE POLICY acpos_topics_write ON public.topics
FOR ALL TO acpos_app_runtime
USING (acpos_runtime.can_manage_project(project_id))
WITH CHECK (acpos_runtime.can_manage_project(project_id));

ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_conversations_select ON public.conversations;
DROP POLICY IF EXISTS acpos_conversations_write ON public.conversations;
CREATE POLICY acpos_conversations_select ON public.conversations
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR created_by = acpos_runtime.current_actor_user_id()
  OR acpos_runtime.can_access_project(project_id)
);
CREATE POLICY acpos_conversations_write ON public.conversations
FOR ALL TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR created_by = acpos_runtime.current_actor_user_id()
  OR acpos_runtime.can_manage_project(project_id)
)
WITH CHECK (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR created_by = acpos_runtime.current_actor_user_id()
  OR acpos_runtime.can_manage_project(project_id)
);

ALTER TABLE public.conversation_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_conversation_messages_select ON public.conversation_messages;
DROP POLICY IF EXISTS acpos_conversation_messages_insert ON public.conversation_messages;
CREATE POLICY acpos_conversation_messages_select ON public.conversation_messages
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_conversation(conversation_id));
CREATE POLICY acpos_conversation_messages_insert ON public.conversation_messages
FOR INSERT TO acpos_app_runtime
WITH CHECK (acpos_runtime.can_access_conversation(conversation_id));

INSERT INTO schema_migration_history(migration_id, checksum, applied_by, approval_ref)
VALUES (
  '0016_postgresql_rls_runtime_foundation',
  '8c8ca99cbbc171e45940869da014dcbdde7130d2e0dd73d1b2c1cac39e7e3cd4',
  'migration-runner',
  'CR-RLS-0016'
)
ON CONFLICT (migration_id) DO NOTHING;
