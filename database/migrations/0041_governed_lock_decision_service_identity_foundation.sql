-- ACPOS migration 0041: governed lock decision + automation identity foundation.
-- Current single-authority closure for VersionLockService, TaskOrchestrator and InstructionCompiler.
-- No historical-source runtime fallback; no human-permission impersonation by service identities.

ALTER TABLE public.lock_reviews
  ADD COLUMN IF NOT EXISTS review_version integer NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS decision_correlation_id uuid NULL,
  ADD COLUMN IF NOT EXISTS decision_idempotency_key_hash char(64) NULL,
  ADD COLUMN IF NOT EXISTS decision_payload_hash char(64) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS lock_reviews_decision_idempotency_key_hash_uq
ON public.lock_reviews(decision_idempotency_key_hash)
WHERE decision_idempotency_key_hash IS NOT NULL;

INSERT INTO public.service_identities(service_identity_key,owner_service,status)
VALUES
  ('task_orchestrator','TaskOrchestrator','APPROVED'),
  ('instruction_compiler','InstructionCompiler','APPROVED')
ON CONFLICT(service_identity_key) DO UPDATE
SET owner_service=EXCLUDED.owner_service,
    status='APPROVED',
    disabled_at=NULL;

INSERT INTO public.service_identity_capability_assignments(
  service_identity_id,capability_key,scope,condition,gate_profile,status,approval_ref
)
SELECT si.service_identity_id,v.capability_key,'{}'::jsonb,'{}'::jsonb,v.gate_profile,'APPROVED','CR-RUNTIME-0041'
FROM public.service_identities si
JOIN (
  VALUES
    ('task_orchestrator','dag.materialize_locked_blueprint',jsonb_build_object('requires',jsonb_build_array('child_lock_current','deterministic_resolution','task_contract_hash','audit'))),
    ('task_orchestrator','task.dispatch_approved_flow',jsonb_build_object('requires',jsonb_build_array('child_lock_current','deterministic_resolution','task_contract_hash','audit'))),
    ('instruction_compiler','service.script_view.compile',jsonb_build_object('requires',jsonb_build_array('child_lock_current','task_input_manifest_explicit','script_view_explicit','audit'))),
    ('instruction_compiler','service.instruction_package.compile',jsonb_build_object('requires',jsonb_build_array('child_lock_current','task_input_manifest_explicit','script_view_explicit','audit')))
) AS v(service_identity_key,capability_key,gate_profile)
  ON si.service_identity_key=v.service_identity_key
WHERE NOT EXISTS (
  SELECT 1
  FROM public.service_identity_capability_assignments a
  WHERE a.service_identity_id=si.service_identity_id
    AND a.capability_key=v.capability_key
    AND a.status='APPROVED'
);

CREATE OR REPLACE FUNCTION acpos_runtime.current_service_identity_id()
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT service_identity_id
  FROM public.service_identities
  WHERE service_identity_key=nullif(current_setting('acpos.service_identity_key',true),'')
    AND status='APPROVED'
    AND disabled_at IS NULL
  LIMIT 1
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.has_service_capability(p_capability_key text)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT EXISTS(
    SELECT 1
    FROM public.service_identity_capability_assignments a
    WHERE a.service_identity_id=acpos_runtime.current_service_identity_id()
      AND a.capability_key=p_capability_key
      AND a.status='APPROVED'
      AND a.scope='{}'::jsonb
      AND a.condition='{}'::jsonb
  )
$$;

CREATE OR REPLACE FUNCTION acpos_runtime.has_account_resource_action(p_resource_key text,p_action text)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
  SELECT EXISTS(
    SELECT 1
    FROM public.account_permission_assignments a
    JOIN public.permission_resources r ON r.resource_id=a.resource_id
    WHERE a.user_id=acpos_runtime.current_actor_user_id()
      AND r.resource_key=p_resource_key
      AND r.active=true
      AND p_action = ANY(
        SELECT jsonb_array_elements_text(
          CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END
        )
      )
      AND a.action=p_action
      AND a.effect='ALLOW'
      AND a.status='APPROVED'
      AND a.scope='{}'::jsonb
      AND a.condition='{}'::jsonb
      AND a.effective_from<=now()
      AND (a.effective_to IS NULL OR a.effective_to>now())
  )
$$;

GRANT EXECUTE ON FUNCTION
  acpos_runtime.current_service_identity_id(),
  acpos_runtime.has_service_capability(text),
  acpos_runtime.has_account_resource_action(text,text)
TO acpos_app_runtime;

ALTER TABLE public.service_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.service_identity_capability_assignments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS acpos_service_identity_self_select ON public.service_identities;
CREATE POLICY acpos_service_identity_self_select ON public.service_identities
FOR SELECT TO acpos_app_runtime
USING (service_identity_id=acpos_runtime.current_service_identity_id());

DROP POLICY IF EXISTS acpos_service_capability_self_select ON public.service_identity_capability_assignments;
CREATE POLICY acpos_service_capability_self_select ON public.service_identity_capability_assignments
FOR SELECT TO acpos_app_runtime
USING (service_identity_id=acpos_runtime.current_service_identity_id());

GRANT SELECT ON public.service_identities,public.service_identity_capability_assignments TO acpos_app_runtime;

ALTER TABLE public.lock_reviews ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_core_lock_review_decide_update ON public.lock_reviews;
CREATE POLICY acpos_core_lock_review_decide_update ON public.lock_reviews
FOR UPDATE TO acpos_app_runtime
USING (
  status='IN_REVIEW'
  AND requested_by<>acpos_runtime.current_actor_user_id()
  AND acpos_runtime.has_account_resource_action('api:decideLockReview','EXECUTE')
)
WITH CHECK (
  decided_by=acpos_runtime.current_actor_user_id()
  AND status IN('APPROVED','REJECTED')
  AND acpos_runtime.has_account_resource_action('api:decideLockReview','EXECUTE')
);

GRANT UPDATE(
  status,decided_by,decision_reason,decided_at,review_version,
  decision_correlation_id,decision_idempotency_key_hash,decision_payload_hash
) ON public.lock_reviews TO acpos_app_runtime;
GRANT SELECT,INSERT ON public.child_locks,public.mother_locks TO acpos_app_runtime;
GRANT UPDATE(status,frozen_at) ON public.blueprint_versions TO acpos_app_runtime;
GRANT UPDATE(status,active_version_id) ON public.topic_blueprints TO acpos_app_runtime;
GRANT UPDATE(status,immutable_at) ON public.topic_production_contracts TO acpos_app_runtime;
GRANT UPDATE(status,immutable_at) ON public.project_versions TO acpos_app_runtime;
GRANT INSERT ON public.audit_events TO acpos_app_runtime;

CREATE OR REPLACE FUNCTION acpos_runtime.decide_lock_review(
  p_lock_review_id uuid,
  p_expected_version text,
  p_scope jsonb,
  p_decision text,
  p_reason text,
  p_correlation_id uuid,
  p_idempotency_key text
)
RETURNS TABLE(
  lock_review_id uuid,
  lock_kind text,
  decision_status text,
  review_version integer,
  lock_ref uuid,
  idempotent_replay boolean
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
DECLARE
  v_actor uuid;
  v_row public.lock_reviews%ROWTYPE;
  v_expected integer;
  v_payload_hash char(64);
  v_idem_hash char(64);
  v_workspace_id uuid;
  v_project_id uuid;
  v_topic_id uuid;
  v_lock_ref uuid;
  v_lock_version integer;
BEGIN
  v_actor:=acpos_runtime.current_actor_user_id();
  IF v_actor IS NULL THEN RAISE EXCEPTION 'IDENTITY_RUNTIME_NOT_BOUND'; END IF;
  IF NOT acpos_runtime.has_account_resource_action('api:decideLockReview','EXECUTE') THEN
    RAISE EXCEPTION 'PERMISSION_OR_SCOPE_DENIED';
  END IF;
  IF p_scope IS NULL OR jsonb_typeof(p_scope)<>'object' THEN RAISE EXCEPTION 'R9_CONTEXT_REQUIRED'; END IF;
  IF p_expected_version IS NULL OR p_expected_version !~ '^v[1-9][0-9]*$' THEN RAISE EXCEPTION 'EXPECTED_VERSION_INVALID'; END IF;
  v_expected:=substring(p_expected_version from 2)::integer;
  IF p_decision NOT IN('APPROVE','REJECT') THEN RAISE EXCEPTION 'DECISION_INVALID'; END IF;
  IF nullif(btrim(p_reason),'') IS NULL THEN RAISE EXCEPTION 'REASON_INVALID'; END IF;
  IF length(coalesce(p_idempotency_key,''))<16 OR length(p_idempotency_key)>128 THEN RAISE EXCEPTION 'IDEMPOTENCY_KEY_INVALID'; END IF;

  v_idem_hash:=encode(digest(p_idempotency_key,'sha256'),'hex');
  v_payload_hash:=encode(digest(
    jsonb_build_object(
      'lock_review_id',p_lock_review_id,
      'expected_version',p_expected_version,
      'scope',p_scope,
      'decision',p_decision,
      'reason',p_reason,
      'correlation_id',p_correlation_id
    )::text,'sha256'),'hex');

  SELECT * INTO v_row
  FROM public.lock_reviews
  WHERE public.lock_reviews.lock_review_id=p_lock_review_id
  FOR UPDATE;

  IF NOT FOUND THEN RAISE EXCEPTION 'LOCK_REVIEW_NOT_FOUND'; END IF;

  IF v_row.decision_idempotency_key_hash=v_idem_hash THEN
    IF v_row.decision_payload_hash<>v_payload_hash THEN RAISE EXCEPTION 'IDEMPOTENCY_CONFLICT'; END IF;
    IF v_row.lock_kind='CHILD' THEN
      SELECT child_lock_id INTO v_lock_ref FROM public.child_locks WHERE child_locks.lock_review_id=p_lock_review_id;
    ELSE
      SELECT mother_lock_id INTO v_lock_ref FROM public.mother_locks WHERE mother_locks.lock_review_id=p_lock_review_id;
    END IF;
    RETURN QUERY SELECT p_lock_review_id,v_row.lock_kind::text,v_row.status::text,v_row.review_version,v_lock_ref,true;
    RETURN;
  END IF;

  IF v_row.status<>'IN_REVIEW' THEN RAISE EXCEPTION 'LOCK_REVIEW_STATE_CONFLICT'; END IF;
  IF v_row.review_version<>v_expected THEN RAISE EXCEPTION 'VERSION_CONFLICT'; END IF;
  IF v_row.requested_by=v_actor THEN RAISE EXCEPTION 'SEPARATION_OF_DUTIES_VIOLATION'; END IF;

  IF v_row.lock_kind='MOTHER' THEN
    SELECT p.workspace_id,pv.project_id,NULL::uuid
      INTO v_workspace_id,v_project_id,v_topic_id
    FROM public.project_versions pv
    JOIN public.projects p ON p.project_id=pv.project_id
    WHERE pv.project_version_id=v_row.target_version_id;
  ELSE
    SELECT p.workspace_id,t.project_id,t.topic_id
      INTO v_workspace_id,v_project_id,v_topic_id
    FROM public.blueprint_versions bv
    JOIN public.topic_blueprints tb ON tb.topic_blueprint_id=bv.topic_blueprint_id
    JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
    JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
    JOIN public.topics t ON t.topic_id=tv.topic_id
    JOIN public.projects p ON p.project_id=t.project_id
    WHERE bv.blueprint_version_id=v_row.target_version_id;
  END IF;

  IF v_workspace_id IS NULL OR v_project_id IS NULL THEN RAISE EXCEPTION 'LOCK_REVIEW_TARGET_LINEAGE_INVALID'; END IF;
  IF nullif(p_scope->>'workspace_id','') IS DISTINCT FROM v_workspace_id::text THEN RAISE EXCEPTION 'SCOPE_WORKSPACE_MISMATCH'; END IF;
  IF nullif(p_scope->>'project_id','') IS DISTINCT FROM v_project_id::text THEN RAISE EXCEPTION 'SCOPE_PROJECT_MISMATCH'; END IF;
  IF v_row.lock_kind='CHILD' AND nullif(p_scope->>'topic_id','') IS DISTINCT FROM v_topic_id::text THEN RAISE EXCEPTION 'SCOPE_TOPIC_MISMATCH'; END IF;

  UPDATE public.lock_reviews
  SET status=CASE WHEN p_decision='APPROVE' THEN 'APPROVED'::public.acpos_status ELSE 'REJECTED'::public.acpos_status END,
      decided_by=v_actor,
      decision_reason=p_reason,
      decided_at=now(),
      review_version=review_version+1,
      decision_correlation_id=p_correlation_id,
      decision_idempotency_key_hash=v_idem_hash,
      decision_payload_hash=v_payload_hash
  WHERE public.lock_reviews.lock_review_id=p_lock_review_id
    AND status='IN_REVIEW'
    AND review_version=v_expected;

  IF NOT FOUND THEN RAISE EXCEPTION 'VERSION_CONFLICT'; END IF;

  IF p_decision='APPROVE' AND v_row.lock_kind='MOTHER' THEN
    SELECT COALESCE(max(lock_version),0)+1 INTO v_lock_version FROM public.mother_locks WHERE project_id=v_project_id;
    INSERT INTO public.mother_locks(
      mother_lock_id,project_id,project_version_id,lock_review_id,lock_version,project_hash,status,locked_at
    ) VALUES(
      gen_random_uuid(),v_project_id,v_row.target_version_id,p_lock_review_id,v_lock_version,v_row.expected_target_hash,'MOTHER_LOCKED',now()
    )
    ON CONFLICT(lock_review_id) DO NOTHING
    RETURNING mother_lock_id INTO v_lock_ref;

    IF v_lock_ref IS NULL THEN
      SELECT mother_lock_id INTO v_lock_ref FROM public.mother_locks WHERE mother_locks.lock_review_id=p_lock_review_id;
    END IF;

    UPDATE public.project_versions
    SET status='MOTHER_LOCKED',immutable_at=COALESCE(immutable_at,now())
    WHERE project_version_id=v_row.target_version_id;
  ELSIF p_decision='APPROVE' AND v_row.lock_kind='CHILD' THEN
    SELECT COALESCE(max(lock_version),0)+1 INTO v_lock_version FROM public.child_locks WHERE topic_id=v_topic_id;
    INSERT INTO public.child_locks(
      child_lock_id,topic_id,topic_production_contract_id,blueprint_version_id,lock_review_id,
      lock_version,contract_hash,blueprint_hash,status,locked_at
    )
    SELECT
      gen_random_uuid(),v_topic_id,pc.topic_production_contract_id,bv.blueprint_version_id,p_lock_review_id,
      v_lock_version,pc.contract_hash,bv.content_hash,'CHILD_LOCKED',now()
    FROM public.blueprint_versions bv
    JOIN public.topic_blueprints tb ON tb.topic_blueprint_id=bv.topic_blueprint_id
    JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
    WHERE bv.blueprint_version_id=v_row.target_version_id
    ON CONFLICT(lock_review_id) DO NOTHING
    RETURNING child_lock_id INTO v_lock_ref;

    IF v_lock_ref IS NULL THEN
      SELECT child_lock_id INTO v_lock_ref FROM public.child_locks WHERE child_locks.lock_review_id=p_lock_review_id;
    END IF;

    UPDATE public.blueprint_versions SET status='CHILD_LOCKED',frozen_at=COALESCE(frozen_at,now())
    WHERE blueprint_version_id=v_row.target_version_id;

    UPDATE public.topic_blueprints tb SET status='CHILD_LOCKED',active_version_id=v_row.target_version_id
    FROM public.blueprint_versions bv
    WHERE bv.blueprint_version_id=v_row.target_version_id AND tb.topic_blueprint_id=bv.topic_blueprint_id;

    UPDATE public.topic_production_contracts pc SET status='CHILD_LOCKED',immutable_at=COALESCE(immutable_at,now())
    FROM public.topic_blueprints tb
    WHERE tb.active_version_id=v_row.target_version_id AND pc.topic_production_contract_id=tb.topic_production_contract_id;
  END IF;

  INSERT INTO public.audit_events(
    action,entity_type,entity_id,actor_id,actor_type,workspace_id,reason,correlation_id,payload_hash,before_version,after_version
  ) VALUES(
    CASE WHEN p_decision='APPROVE' THEN 'lock.review.approved' ELSE 'lock.review.rejected' END,
    'lock_review',p_lock_review_id,v_actor,'USER',v_workspace_id,p_reason,p_correlation_id,v_payload_hash,
    jsonb_build_object('status','IN_REVIEW','review_version',v_expected),
    jsonb_build_object('status',CASE WHEN p_decision='APPROVE' THEN 'APPROVED' ELSE 'REJECTED' END,'review_version',v_expected+1,'lock_ref',v_lock_ref)
  );

  RETURN QUERY SELECT
    p_lock_review_id,
    v_row.lock_kind::text,
    CASE WHEN p_decision='APPROVE' THEN 'APPROVED' ELSE 'REJECTED' END,
    v_expected+1,
    v_lock_ref,
    false;
END
$$;

GRANT EXECUTE ON FUNCTION acpos_runtime.decide_lock_review(uuid,text,jsonb,text,text,uuid,text) TO acpos_app_runtime;

DO $$
DECLARE
  service_count integer;
  capability_count integer;
  lock_api_count integer;
BEGIN
  SELECT count(*) INTO service_count
  FROM public.service_identities
  WHERE service_identity_key IN('task_orchestrator','instruction_compiler')
    AND status='APPROVED';
  IF service_count<>2 THEN RAISE EXCEPTION 'RUNTIME0041_SERVICE_IDENTITY_COUNT_MISMATCH:%',service_count; END IF;

  SELECT count(*) INTO capability_count
  FROM public.service_identity_capability_assignments a
  JOIN public.service_identities s ON s.service_identity_id=a.service_identity_id
  WHERE s.service_identity_key IN('task_orchestrator','instruction_compiler')
    AND a.capability_key IN(
      'dag.materialize_locked_blueprint','task.dispatch_approved_flow',
      'service.script_view.compile','service.instruction_package.compile'
    )
    AND a.status='APPROVED';
  IF capability_count<>4 THEN RAISE EXCEPTION 'RUNTIME0041_SERVICE_CAPABILITY_COUNT_MISMATCH:%',capability_count; END IF;

  SELECT count(*) INTO lock_api_count
  FROM public.permission_resources
  WHERE resource_key='api:decideLockReview' AND active=true AND resource_type='API';
  IF lock_api_count<>1 THEN RAISE EXCEPTION 'RUNTIME0041_LOCK_DECISION_API_RESOURCE_MISMATCH:%',lock_api_count; END IF;
END
$$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0041_governed_lock_decision_service_identity_foundation',
  '0c7da1493827da6d43ea26532ea0d6021c01f62969442637616acb5f130a5d8e',
  'migration-runner',
  'CR-RUNTIME-0041'
)
ON CONFLICT(migration_id) DO NOTHING;
