-- ACPOS migration 0037: CORE current governed runtime permission/RLS closure.
-- Extends 0016/0021/0028 without replacing Current Authority or importing legacy story-candidate mutation.
-- Production apply remains pending final release sequence.

DO $$
DECLARE
  bootstrap_user_id uuid;
  resource_count integer;
BEGIN
  SELECT u.user_id INTO bootstrap_user_id
  FROM public.app_users u
  JOIN acpos_runtime.accounts a ON lower(a.email)=lower(u.email::text)
  WHERE a.id='runtime-admin' AND a.status='READY' AND u.disabled_at IS NULL
  LIMIT 1;
  IF bootstrap_user_id IS NULL THEN
    RAISE EXCEPTION 'CORE0037_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*) INTO resource_count
  FROM public.permission_resources
  WHERE active=true
    AND resource_type='API'
    AND 'EXECUTE'=ANY(
      SELECT jsonb_array_elements_text(
        CASE WHEN jsonb_typeof(allowed_actions)='array' THEN allowed_actions ELSE '[]'::jsonb END
      )
    )
    AND resource_key IN(
      'api:createCandidate','api:compareCandidates','api:decideCandidate','api:requestDNALock','api:submitCoreReview',
      'api:createBlueprint','api:validateBlueprint','api:approveBlueprint','api:requestChildLock','api:getCanonicalScript'
    );
  IF resource_count<>10 THEN
    RAISE EXCEPTION 'CORE0037_API_RESOURCE_COUNT_MISMATCH:%',resource_count;
  END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,granted_by_user_id,
    approval_ref,version_no,effective_from,effective_to,approval_required
  )
  SELECT
    bootstrap_user_id,r.resource_id,'EXECUTE','ALLOW','{}'::jsonb,'{}'::jsonb,
    jsonb_build_object(
      'page_uid','CORE-01',
      'runtime_owner','ProductionCoreGovernedRuntime',
      'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'
    ),
    'APPROVED',bootstrap_user_id,'CR-CORE-0037-PENDING-PRODUCTION-APPLY',1,now(),NULL,false
  FROM public.permission_resources r
  WHERE r.active=true
    AND r.resource_key IN(
      'api:createCandidate','api:compareCandidates','api:decideCandidate','api:requestDNALock','api:submitCoreReview',
      'api:createBlueprint','api:validateBlueprint','api:approveBlueprint','api:requestChildLock','api:getCanonicalScript'
    )
  ON CONFLICT(user_id,resource_id,action,version_no) DO NOTHING;
END
$$;

GRANT SELECT ON
  public.topic_versions,
  public.topic_production_contracts,
  public.master_blueprints,
  public.topic_blueprints,
  public.blueprint_versions,
  public.lock_reviews,
  public.dna_versions,
  public.canonical_script_versions
TO acpos_app_runtime;

GRANT INSERT,UPDATE ON public.topic_blueprints TO acpos_app_runtime;
GRANT INSERT ON public.blueprint_versions TO acpos_app_runtime;
GRANT UPDATE(status,validation_result,frozen_at) ON public.blueprint_versions TO acpos_app_runtime;
GRANT UPDATE(lock_decision_request_id) ON public.dna_versions TO acpos_app_runtime;
GRANT INSERT ON public.lock_reviews TO acpos_app_runtime;
GRANT SELECT,INSERT ON public.decision_requests TO acpos_app_runtime;

ALTER TABLE public.topic_versions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_core_topic_versions_select ON public.topic_versions;
CREATE POLICY acpos_core_topic_versions_select ON public.topic_versions
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1 FROM public.topics t
    WHERE t.topic_id=topic_versions.topic_id
      AND acpos_runtime.can_access_project(t.project_id)
  )
);

ALTER TABLE public.topic_production_contracts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_core_topic_contract_select ON public.topic_production_contracts;
CREATE POLICY acpos_core_topic_contract_select ON public.topic_production_contracts
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1
    FROM public.topic_versions tv
    JOIN public.topics t ON t.topic_id=tv.topic_id
    WHERE tv.topic_version_id=topic_production_contracts.topic_version_id
      AND acpos_runtime.can_access_project(t.project_id)
  )
);

ALTER TABLE public.master_blueprints ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_core_master_blueprint_select ON public.master_blueprints;
CREATE POLICY acpos_core_master_blueprint_select ON public.master_blueprints
FOR SELECT TO acpos_app_runtime
USING (status='APPROVED');

ALTER TABLE public.topic_blueprints ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_core_topic_blueprint_select ON public.topic_blueprints;
DROP POLICY IF EXISTS acpos_core_topic_blueprint_insert ON public.topic_blueprints;
DROP POLICY IF EXISTS acpos_core_topic_blueprint_update ON public.topic_blueprints;
CREATE POLICY acpos_core_topic_blueprint_select ON public.topic_blueprints
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1
    FROM public.topic_production_contracts pc
    JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
    JOIN public.topics t ON t.topic_id=tv.topic_id
    WHERE pc.topic_production_contract_id=topic_blueprints.topic_production_contract_id
      AND acpos_runtime.can_access_project(t.project_id)
  )
);
CREATE POLICY acpos_core_topic_blueprint_insert ON public.topic_blueprints
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  EXISTS(
    SELECT 1
    FROM public.topic_production_contracts pc
    JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
    JOIN public.topics t ON t.topic_id=tv.topic_id
    WHERE pc.topic_production_contract_id=topic_blueprints.topic_production_contract_id
      AND acpos_runtime.can_manage_project(t.project_id)
  )
);
CREATE POLICY acpos_core_topic_blueprint_update ON public.topic_blueprints
FOR UPDATE TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1
    FROM public.topic_production_contracts pc
    JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
    JOIN public.topics t ON t.topic_id=tv.topic_id
    WHERE pc.topic_production_contract_id=topic_blueprints.topic_production_contract_id
      AND acpos_runtime.can_manage_project(t.project_id)
  )
)
WITH CHECK (
  EXISTS(
    SELECT 1
    FROM public.topic_production_contracts pc
    JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
    JOIN public.topics t ON t.topic_id=tv.topic_id
    WHERE pc.topic_production_contract_id=topic_blueprints.topic_production_contract_id
      AND acpos_runtime.can_manage_project(t.project_id)
  )
);

ALTER TABLE public.blueprint_versions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_core_blueprint_version_select ON public.blueprint_versions;
DROP POLICY IF EXISTS acpos_core_blueprint_version_insert ON public.blueprint_versions;
DROP POLICY IF EXISTS acpos_core_blueprint_version_update ON public.blueprint_versions;
CREATE POLICY acpos_core_blueprint_version_select ON public.blueprint_versions
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1
    FROM public.topic_blueprints tb
    JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
    JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
    JOIN public.topics t ON t.topic_id=tv.topic_id
    WHERE tb.topic_blueprint_id=blueprint_versions.topic_blueprint_id
      AND acpos_runtime.can_access_project(t.project_id)
  )
);
CREATE POLICY acpos_core_blueprint_version_insert ON public.blueprint_versions
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  created_by=acpos_runtime.current_actor_user_id()
  AND EXISTS(
    SELECT 1
    FROM public.topic_blueprints tb
    JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
    JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
    JOIN public.topics t ON t.topic_id=tv.topic_id
    WHERE tb.topic_blueprint_id=blueprint_versions.topic_blueprint_id
      AND acpos_runtime.can_manage_project(t.project_id)
  )
);
CREATE POLICY acpos_core_blueprint_version_update ON public.blueprint_versions
FOR UPDATE TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1
    FROM public.topic_blueprints tb
    JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
    JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
    JOIN public.topics t ON t.topic_id=tv.topic_id
    WHERE tb.topic_blueprint_id=blueprint_versions.topic_blueprint_id
      AND acpos_runtime.can_manage_project(t.project_id)
  )
)
WITH CHECK (
  EXISTS(
    SELECT 1
    FROM public.topic_blueprints tb
    JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
    JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
    JOIN public.topics t ON t.topic_id=tv.topic_id
    WHERE tb.topic_blueprint_id=blueprint_versions.topic_blueprint_id
      AND acpos_runtime.can_manage_project(t.project_id)
  )
);

ALTER TABLE public.dna_versions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_core_dna_version_select ON public.dna_versions;
DROP POLICY IF EXISTS acpos_core_dna_version_update ON public.dna_versions;
CREATE POLICY acpos_core_dna_version_select ON public.dna_versions
FOR SELECT TO acpos_app_runtime
USING (acpos_runtime.can_access_project(project_id));
CREATE POLICY acpos_core_dna_version_update ON public.dna_versions
FOR UPDATE TO acpos_app_runtime
USING (acpos_runtime.can_manage_project(project_id))
WITH CHECK (acpos_runtime.can_manage_project(project_id));

ALTER TABLE public.lock_reviews ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_core_lock_review_select ON public.lock_reviews;
DROP POLICY IF EXISTS acpos_core_lock_review_insert ON public.lock_reviews;
CREATE POLICY acpos_core_lock_review_select ON public.lock_reviews
FOR SELECT TO acpos_app_runtime
USING (
  (
    target_type='PROJECT_VERSION'
    AND EXISTS(
      SELECT 1 FROM public.project_versions pv
      WHERE pv.project_version_id=lock_reviews.target_version_id
        AND acpos_runtime.can_access_project(pv.project_id)
    )
  )
  OR
  (
    target_type='BLUEPRINT_VERSION'
    AND EXISTS(
      SELECT 1
      FROM public.blueprint_versions bv
      JOIN public.topic_blueprints tb ON tb.topic_blueprint_id=bv.topic_blueprint_id
      JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
      JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
      JOIN public.topics t ON t.topic_id=tv.topic_id
      WHERE bv.blueprint_version_id=lock_reviews.target_version_id
        AND acpos_runtime.can_access_project(t.project_id)
    )
  )
);
CREATE POLICY acpos_core_lock_review_insert ON public.lock_reviews
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  requested_by=acpos_runtime.current_actor_user_id()
  AND (
    (
      target_type='PROJECT_VERSION'
      AND EXISTS(
        SELECT 1 FROM public.project_versions pv
        WHERE pv.project_version_id=lock_reviews.target_version_id
          AND acpos_runtime.can_manage_project(pv.project_id)
      )
    )
    OR
    (
      target_type='BLUEPRINT_VERSION'
      AND EXISTS(
        SELECT 1
        FROM public.blueprint_versions bv
        JOIN public.topic_blueprints tb ON tb.topic_blueprint_id=bv.topic_blueprint_id
        JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
        JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
        JOIN public.topics t ON t.topic_id=tv.topic_id
        WHERE bv.blueprint_version_id=lock_reviews.target_version_id
          AND acpos_runtime.can_manage_project(t.project_id)
      )
    )
  )
);

-- 0028 enables decision_requests for Strategy. Add only the CORE DNA request policies.
ALTER TABLE public.decision_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_core_dna_decision_request_select ON public.decision_requests;
DROP POLICY IF EXISTS acpos_core_dna_decision_request_insert ON public.decision_requests;
CREATE POLICY acpos_core_dna_decision_request_select ON public.decision_requests
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1 FROM public.permission_resources r
    WHERE r.resource_id=decision_requests.required_resource_id
      AND r.resource_key='api:requestDNALock'
      AND r.active=true
  )
  AND required_action='EXECUTE'
  AND required_scope ? 'project_id'
  AND required_scope->>'project_id' ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
  AND acpos_runtime.can_access_project((required_scope->>'project_id')::uuid)
);
CREATE POLICY acpos_core_dna_decision_request_insert ON public.decision_requests
FOR INSERT TO acpos_app_runtime
WITH CHECK (
  created_by_user_id=acpos_runtime.current_actor_user_id()
  AND created_by_actor_type='USER'
  AND EXISTS(
    SELECT 1 FROM public.permission_resources r
    WHERE r.resource_id=decision_requests.required_resource_id
      AND r.resource_key='api:requestDNALock'
      AND r.active=true
  )
  AND required_action='EXECUTE'
  AND required_scope ? 'project_id'
  AND required_scope->>'project_id' ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
  AND acpos_runtime.can_manage_project((required_scope->>'project_id')::uuid)
);

ALTER TABLE public.canonical_script_versions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_core_canonical_script_select ON public.canonical_script_versions;
CREATE POLICY acpos_core_canonical_script_select ON public.canonical_script_versions
FOR SELECT TO acpos_app_runtime
USING (
  EXISTS(
    SELECT 1 FROM public.topics t
    WHERE t.topic_id=canonical_script_versions.topic_id
      AND acpos_runtime.can_access_project(t.project_id)
  )
);

DO $$
DECLARE assignment_count integer;
BEGIN
  SELECT count(DISTINCT r.resource_key) INTO assignment_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  JOIN public.app_users u ON u.user_id=a.user_id
  JOIN acpos_runtime.accounts ac ON lower(ac.email)=lower(u.email::text)
  WHERE ac.id='runtime-admin'
    AND r.resource_key IN(
      'api:createCandidate','api:compareCandidates','api:decideCandidate','api:requestDNALock','api:submitCoreReview',
      'api:createBlueprint','api:validateBlueprint','api:approveBlueprint','api:requestChildLock','api:getCanonicalScript'
    )
    AND a.action='EXECUTE' AND a.effect='ALLOW' AND a.status='APPROVED';
  IF assignment_count<>10 THEN
    RAISE EXCEPTION 'CORE0037_ASSIGNMENT_COUNT_MISMATCH:%',assignment_count;
  END IF;

  IF NOT has_table_privilege('acpos_app_runtime','public.candidate_versions','SELECT')
     OR NOT has_table_privilege('acpos_app_runtime','public.candidate_decisions','SELECT,INSERT')
     OR NOT has_table_privilege('acpos_app_runtime','public.blueprint_versions','SELECT')
     OR NOT has_column_privilege('acpos_app_runtime','public.blueprint_versions','status','UPDATE')
     OR NOT has_column_privilege('acpos_app_runtime','public.dna_versions','lock_decision_request_id','UPDATE')
     OR NOT has_table_privilege('acpos_app_runtime','public.canonical_script_versions','SELECT') THEN
    RAISE EXCEPTION 'CORE0037_RUNTIME_GRANT_MISSING';
  END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0037_core_governed_runtime_permission_rls_closure',
  '42253b9c137e299f482d0f35d2132a32bfa45204e32074ed83bbae0768822ec7',
  'migration-runner',
  'CR-CORE-0037-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT(migration_id) DO NOTHING;
