-- ACPOS migration 0042: canonical lock-request persistence, evidence/reviewer resolution and events.
-- Single active construction authority closure. No implicit latest/default resolution.

ALTER TABLE public.lock_reviews
  ADD COLUMN IF NOT EXISTS request_reason text NULL,
  ADD COLUMN IF NOT EXISTS requested_scope_refs jsonb NULL,
  ADD COLUMN IF NOT EXISTS request_correlation_id uuid NULL,
  ADD COLUMN IF NOT EXISTS request_idempotency_key_hash char(64) NULL,
  ADD COLUMN IF NOT EXISTS request_payload_hash char(64) NULL;

CREATE UNIQUE INDEX IF NOT EXISTS lock_reviews_request_idempotency_key_hash_uq
ON public.lock_reviews(request_idempotency_key_hash)
WHERE request_idempotency_key_hash IS NOT NULL;

REVOKE INSERT ON public.lock_reviews FROM acpos_app_runtime;

CREATE OR REPLACE FUNCTION acpos_runtime.request_lock_review(
  p_lock_kind text,
  p_scope jsonb,
  p_expected_version text,
  p_correlation_id uuid,
  p_idempotency_key text,
  p_target_ref uuid,
  p_request_reason text,
  p_requested_scope_refs jsonb
)
RETURNS TABLE(
  lock_review_id uuid,
  lock_kind text,
  review_status text,
  review_version integer,
  target_ref uuid,
  criteria_version_id uuid,
  reviewer_count integer,
  evidence_count integer,
  idempotent_replay boolean
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
DECLARE
  v_actor uuid;
  v_resource_key text;
  v_expected integer;
  v_workspace_id uuid;
  v_project_id uuid;
  v_topic_id uuid;
  v_target_hash char(64);
  v_target_status public.acpos_status;
  v_target_version integer;
  v_criteria_id uuid;
  v_criteria_count integer;
  v_evidence_refs jsonb := '[]'::jsonb;
  v_evidence_count integer := 0;
  v_reviewer_path jsonb := '[]'::jsonb;
  v_reviewer_count integer := 0;
  v_payload_hash char(64);
  v_idem_hash char(64);
  v_existing public.lock_reviews%ROWTYPE;
  v_review_id uuid;
  v_ref text;
  v_ref_uuid uuid;
  v_event_id uuid;
  v_event_payload jsonb;
  v_event_hash char(64);
BEGIN
  v_actor:=acpos_runtime.current_actor_user_id();
  IF v_actor IS NULL THEN RAISE EXCEPTION 'IDENTITY_RUNTIME_NOT_BOUND'; END IF;

  IF p_lock_kind='MOTHER' THEN
    v_resource_key:='api:requestMotherLock';
  ELSIF p_lock_kind='CHILD' THEN
    v_resource_key:='api:requestChildLock';
  ELSE
    RAISE EXCEPTION 'LOCK_KIND_INVALID';
  END IF;

  IF NOT acpos_runtime.has_account_resource_action(v_resource_key,'EXECUTE') THEN
    RAISE EXCEPTION 'PERMISSION_OR_SCOPE_DENIED';
  END IF;
  IF p_scope IS NULL OR jsonb_typeof(p_scope)<>'object' THEN RAISE EXCEPTION 'R9_CONTEXT_REQUIRED'; END IF;
  IF p_expected_version IS NULL OR p_expected_version !~ '^v[1-9][0-9]*$' THEN RAISE EXCEPTION 'EXPECTED_VERSION_INVALID'; END IF;
  v_expected:=substring(p_expected_version from 2)::integer;
  IF p_correlation_id IS NULL THEN RAISE EXCEPTION 'CORRELATION_ID_INVALID'; END IF;
  IF length(coalesce(p_idempotency_key,''))<16 OR length(p_idempotency_key)>128 THEN RAISE EXCEPTION 'IDEMPOTENCY_KEY_INVALID'; END IF;
  IF p_target_ref IS NULL THEN RAISE EXCEPTION 'TARGET_REF_INVALID'; END IF;
  IF nullif(btrim(p_request_reason),'') IS NULL THEN RAISE EXCEPTION 'REQUEST_REASON_INVALID'; END IF;
  IF p_requested_scope_refs IS NULL OR jsonb_typeof(p_requested_scope_refs)<>'array' THEN
    RAISE EXCEPTION 'REQUESTED_SCOPE_REFS_INVALID';
  END IF;

  v_idem_hash:=encode(digest(p_idempotency_key,'sha256'),'hex');
  v_payload_hash:=encode(digest(
    jsonb_build_object(
      'lock_kind',p_lock_kind,
      'scope',p_scope,
      'expected_version',p_expected_version,
      'correlation_id',p_correlation_id,
      'target_ref',p_target_ref,
      'request_reason',p_request_reason,
      'requested_scope_refs',p_requested_scope_refs
    )::text,'sha256'),'hex');

  SELECT * INTO v_existing
  FROM public.lock_reviews
  WHERE request_idempotency_key_hash=v_idem_hash
  LIMIT 1;

  IF FOUND THEN
    IF v_existing.request_payload_hash<>v_payload_hash THEN RAISE EXCEPTION 'IDEMPOTENCY_CONFLICT'; END IF;
    RETURN QUERY SELECT
      v_existing.lock_review_id,v_existing.lock_kind::text,v_existing.status::text,v_existing.review_version,
      v_existing.target_version_id,v_existing.criteria_version_id,
      jsonb_array_length(v_existing.reviewer_path),
      COALESCE(jsonb_array_length(v_existing.evidence->'evidence_refs'),0),
      true;
    RETURN;
  END IF;

  IF p_lock_kind='MOTHER' THEN
    SELECT p.workspace_id,pv.project_id,pv.content_hash,pv.status,pv.version_no
      INTO v_workspace_id,v_project_id,v_target_hash,v_target_status,v_target_version
    FROM public.project_versions pv
    JOIN public.projects p ON p.project_id=pv.project_id
    WHERE pv.project_version_id=p_target_ref;

    IF v_workspace_id IS NULL THEN RAISE EXCEPTION 'TARGET_REF_INVALID'; END IF;
    IF v_target_status<>'READY_FOR_MOTHER_REVIEW' THEN RAISE EXCEPTION 'LOCK_TARGET_NOT_READY'; END IF;
  ELSE
    SELECT p.workspace_id,t.project_id,t.topic_id,bv.content_hash,bv.status,bv.version_no
      INTO v_workspace_id,v_project_id,v_topic_id,v_target_hash,v_target_status,v_target_version
    FROM public.blueprint_versions bv
    JOIN public.topic_blueprints tb ON tb.topic_blueprint_id=bv.topic_blueprint_id
    JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
    JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
    JOIN public.topics t ON t.topic_id=tv.topic_id
    JOIN public.projects p ON p.project_id=t.project_id
    WHERE bv.blueprint_version_id=p_target_ref;

    IF v_workspace_id IS NULL THEN RAISE EXCEPTION 'TARGET_REF_INVALID'; END IF;
    IF v_target_status<>'READY_FOR_CHILD_REVIEW' THEN RAISE EXCEPTION 'LOCK_TARGET_NOT_READY'; END IF;
  END IF;

  IF v_target_version<>v_expected THEN RAISE EXCEPTION 'VERSION_CONFLICT'; END IF;
  IF nullif(p_scope->>'workspace_id','') IS DISTINCT FROM v_workspace_id::text THEN RAISE EXCEPTION 'SCOPE_WORKSPACE_MISMATCH'; END IF;
  IF nullif(p_scope->>'project_id','') IS DISTINCT FROM v_project_id::text THEN RAISE EXCEPTION 'SCOPE_PROJECT_MISMATCH'; END IF;
  IF p_lock_kind='CHILD' AND nullif(p_scope->>'topic_id','') IS DISTINCT FROM v_topic_id::text THEN RAISE EXCEPTION 'SCOPE_TOPIC_MISMATCH'; END IF;

  FOR v_ref IN SELECT jsonb_array_elements_text(p_requested_scope_refs)
  LOOP
    BEGIN
      v_ref_uuid:=v_ref::uuid;
    EXCEPTION WHEN invalid_text_representation THEN
      RAISE EXCEPTION 'REQUESTED_SCOPE_REFS_INVALID';
    END;

    IF EXISTS(
      SELECT 1 FROM public.quality_criteria_versions q
      WHERE q.criteria_version_id=v_ref_uuid AND q.status='APPROVED'
    ) THEN
      IF v_criteria_id IS NOT NULL AND v_criteria_id<>v_ref_uuid THEN
        RAISE EXCEPTION 'LOCK_CRITERIA_AMBIGUOUS';
      END IF;
      v_criteria_id:=v_ref_uuid;
    ELSIF EXISTS(
      SELECT 1
      FROM public.conversation_messages m
      JOIN public.core_conversation_thread_bindings b ON b.conversation_id=m.conversation_id
      WHERE m.conversation_message_id=v_ref_uuid
        AND b.project_id=v_project_id
        AND (
          p_lock_kind='MOTHER'
          OR b.topic_id=v_topic_id
        )
    ) THEN
      v_evidence_refs:=v_evidence_refs || jsonb_build_array(v_ref_uuid::text);
      v_evidence_count:=v_evidence_count+1;
    ELSE
      RAISE EXCEPTION 'REQUESTED_SCOPE_REF_NOT_RESOLVED:%',v_ref;
    END IF;
  END LOOP;

  IF v_criteria_id IS NULL THEN RAISE EXCEPTION 'LOCK_CRITERIA_VERSION_REQUIRED'; END IF;
  SELECT count(*) INTO v_criteria_count
  FROM public.quality_criteria_versions q
  WHERE q.criteria_version_id=v_criteria_id AND q.status='APPROVED';
  IF v_criteria_count<>1 THEN RAISE EXCEPTION 'LOCK_CRITERIA_VERSION_REQUIRED'; END IF;
  IF v_evidence_count<1 THEN RAISE EXCEPTION 'LOCK_EVIDENCE_REQUIRED'; END IF;

  SELECT COALESCE(jsonb_agg(a.user_id::text ORDER BY a.user_id::text),'[]'::jsonb),count(*)::int
    INTO v_reviewer_path,v_reviewer_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  JOIN public.app_users u ON u.user_id=a.user_id
  WHERE r.resource_key='api:decideLockReview'
    AND r.resource_type='API'
    AND r.active=true
    AND a.action='EXECUTE'
    AND a.effect='ALLOW'
    AND a.status='APPROVED'
    AND a.effective_from<=now()
    AND (a.effective_to IS NULL OR a.effective_to>now())
    AND a.condition='{}'::jsonb
    AND u.disabled_at IS NULL
    AND a.user_id<>v_actor
    AND (
      a.scope='{}'::jsonb
      OR (
        COALESCE(a.scope->>'workspace_id',v_workspace_id::text)=v_workspace_id::text
        AND COALESCE(a.scope->>'project_id',v_project_id::text)=v_project_id::text
        AND (
          p_lock_kind='MOTHER'
          OR COALESCE(a.scope->>'topic_id',v_topic_id::text)=v_topic_id::text
        )
      )
    );

  IF v_reviewer_count<1 THEN RAISE EXCEPTION 'CORE_LOCK_REVIEWER_PATH_UNRESOLVED'; END IF;

  INSERT INTO public.lock_reviews(
    lock_kind,target_type,target_version_id,criteria_version_id,evidence,reviewer_path,status,
    expected_target_hash,requested_by,request_reason,requested_scope_refs,request_correlation_id,
    request_idempotency_key_hash,request_payload_hash,review_version
  ) VALUES(
    p_lock_kind::public.lock_kind,
    CASE WHEN p_lock_kind='MOTHER' THEN 'PROJECT_VERSION' ELSE 'BLUEPRINT_VERSION' END,
    p_target_ref,v_criteria_id,
    jsonb_build_object('evidence_refs',v_evidence_refs,'criteria_version_id',v_criteria_id),
    v_reviewer_path,'IN_REVIEW',v_target_hash,v_actor,p_request_reason,p_requested_scope_refs,p_correlation_id,
    v_idem_hash,v_payload_hash,1
  )
  RETURNING public.lock_reviews.lock_review_id INTO v_review_id;

  IF p_lock_kind='MOTHER' THEN
    UPDATE public.project_versions
    SET status='IN_REVIEW'
    WHERE project_version_id=p_target_ref AND status='READY_FOR_MOTHER_REVIEW';
  ELSE
    UPDATE public.blueprint_versions
    SET status='IN_REVIEW'
    WHERE blueprint_version_id=p_target_ref AND status='READY_FOR_CHILD_REVIEW';
  END IF;

  v_event_id:=gen_random_uuid();
  v_event_payload:=jsonb_build_object(
    'lock_review_id',v_review_id,
    'lock_kind',p_lock_kind,
    'target_ref',p_target_ref,
    'workspace_id',v_workspace_id,
    'project_id',v_project_id,
    'topic_id',v_topic_id,
    'criteria_version_id',v_criteria_id,
    'evidence_refs',v_evidence_refs,
    'reviewer_path',v_reviewer_path,
    'review_version',1
  );
  v_event_hash:=encode(digest(v_event_payload::text,'sha256'),'hex');

  INSERT INTO public.outbox_events(
    event_id,event_type,event_version,aggregate_type,aggregate_id,aggregate_version,
    correlation_id,actor_id,payload,payload_hash,idempotency_key
  ) VALUES(
    v_event_id,'lock.review_requested',1,'LockReview',v_review_id,1,
    p_correlation_id,v_actor,v_event_payload,v_event_hash,v_idem_hash
  );

  INSERT INTO public.audit_events(
    action,entity_type,entity_id,actor_id,actor_type,workspace_id,reason,correlation_id,
    payload_hash,before_version,after_version
  ) VALUES(
    'lock.review_requested','lock_review',v_review_id,v_actor,'USER',v_workspace_id,p_request_reason,p_correlation_id,
    v_payload_hash,
    jsonb_build_object('target_status',v_target_status,'target_version',v_target_version),
    jsonb_build_object('status','IN_REVIEW','review_version',1,'criteria_version_id',v_criteria_id,'reviewer_count',v_reviewer_count,'evidence_count',v_evidence_count)
  );

  RETURN QUERY SELECT
    v_review_id,p_lock_kind,'IN_REVIEW',1,p_target_ref,v_criteria_id,v_reviewer_count,v_evidence_count,false;
END
$$;

GRANT EXECUTE ON FUNCTION
  acpos_runtime.request_lock_review(text,jsonb,text,uuid,text,uuid,text,jsonb)
TO acpos_app_runtime;

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
  v_event_id uuid;
  v_event_type text;
  v_event_payload jsonb;
  v_event_hash char(64);
  v_goal_ids jsonb := '[]'::jsonb;
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
      'lock_review_id',p_lock_review_id,'expected_version',p_expected_version,'scope',p_scope,
      'decision',p_decision,'reason',p_reason,'correlation_id',p_correlation_id
    )::text,'sha256'),'hex');

  SELECT * INTO v_row FROM public.lock_reviews
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
  IF NOT (v_row.reviewer_path ? v_actor::text) THEN RAISE EXCEPTION 'REVIEWER_NOT_ASSIGNED_TO_LOCK_REVIEW'; END IF;

  IF v_row.lock_kind='MOTHER' THEN
    SELECT p.workspace_id,pv.project_id,NULL::uuid
      INTO v_workspace_id,v_project_id,v_topic_id
    FROM public.project_versions pv JOIN public.projects p ON p.project_id=pv.project_id
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
      decided_by=v_actor,decision_reason=p_reason,decided_at=now(),review_version=review_version+1,
      decision_correlation_id=p_correlation_id,decision_idempotency_key_hash=v_idem_hash,decision_payload_hash=v_payload_hash
  WHERE public.lock_reviews.lock_review_id=p_lock_review_id AND status='IN_REVIEW' AND review_version=v_expected;
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
    IF v_lock_ref IS NULL THEN SELECT mother_lock_id INTO v_lock_ref FROM public.mother_locks WHERE lock_review_id=p_lock_review_id; END IF;
    UPDATE public.project_versions SET status='MOTHER_LOCKED',immutable_at=COALESCE(immutable_at,now())
    WHERE project_version_id=v_row.target_version_id;
    v_event_type:='mother_lock.approved';
    v_event_payload:=jsonb_build_object(
      'mother_lock_id',v_lock_ref,'project_id',v_project_id,'project_version_id',v_row.target_version_id,
      'project_hash',v_row.expected_target_hash,'lock_version',v_lock_version,'lock_review_id',p_lock_review_id
    );
  ELSIF p_decision='APPROVE' AND v_row.lock_kind='CHILD' THEN
    SELECT COALESCE(max(lock_version),0)+1 INTO v_lock_version FROM public.child_locks WHERE topic_id=v_topic_id;
    INSERT INTO public.child_locks(
      child_lock_id,topic_id,topic_production_contract_id,blueprint_version_id,lock_review_id,
      lock_version,contract_hash,blueprint_hash,status,locked_at
    )
    SELECT gen_random_uuid(),v_topic_id,pc.topic_production_contract_id,bv.blueprint_version_id,p_lock_review_id,
           v_lock_version,pc.contract_hash,bv.content_hash,'CHILD_LOCKED',now()
    FROM public.blueprint_versions bv
    JOIN public.topic_blueprints tb ON tb.topic_blueprint_id=bv.topic_blueprint_id
    JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
    WHERE bv.blueprint_version_id=v_row.target_version_id
    ON CONFLICT(lock_review_id) DO NOTHING
    RETURNING child_lock_id INTO v_lock_ref;
    IF v_lock_ref IS NULL THEN SELECT child_lock_id INTO v_lock_ref FROM public.child_locks WHERE lock_review_id=p_lock_review_id; END IF;

    UPDATE public.blueprint_versions SET status='CHILD_LOCKED',frozen_at=COALESCE(frozen_at,now())
    WHERE blueprint_version_id=v_row.target_version_id;
    UPDATE public.topic_blueprints tb SET status='CHILD_LOCKED',active_version_id=v_row.target_version_id
    FROM public.blueprint_versions bv
    WHERE bv.blueprint_version_id=v_row.target_version_id AND tb.topic_blueprint_id=bv.topic_blueprint_id;
    UPDATE public.topic_production_contracts pc SET status='CHILD_LOCKED',immutable_at=COALESCE(immutable_at,now())
    FROM public.topic_blueprints tb
    WHERE tb.active_version_id=v_row.target_version_id AND pc.topic_production_contract_id=tb.topic_production_contract_id;

    SELECT COALESCE(jsonb_agg(g.production_goal_id::text ORDER BY g.goal_key),'[]'::jsonb)
      INTO v_goal_ids
    FROM public.topic_production_goals g
    JOIN public.child_locks cl ON cl.topic_production_contract_id=g.topic_production_contract_id
    WHERE cl.child_lock_id=v_lock_ref;

    v_event_type:='child_lock.approved';
    v_event_payload:=jsonb_build_object(
      'child_lock_id',v_lock_ref,'topic_id',v_topic_id,
      'topic_production_contract_id',(SELECT topic_production_contract_id FROM public.child_locks WHERE child_lock_id=v_lock_ref),
      'contract_hash',(SELECT contract_hash FROM public.child_locks WHERE child_lock_id=v_lock_ref),
      'blueprint_version_id',v_row.target_version_id,'blueprint_hash',v_row.expected_target_hash,
      'production_goal_ids',v_goal_ids,'lock_version',v_lock_version,'lock_review_id',p_lock_review_id
    );
  ELSIF p_decision='REJECT' THEN
    IF v_row.lock_kind='MOTHER' THEN
      UPDATE public.project_versions SET status='READY_FOR_MOTHER_REVIEW'
      WHERE project_version_id=v_row.target_version_id AND status='IN_REVIEW';
    ELSE
      UPDATE public.blueprint_versions SET status='READY_FOR_CHILD_REVIEW'
      WHERE blueprint_version_id=v_row.target_version_id AND status='IN_REVIEW';
    END IF;
    v_event_type:='lock.rejected';
    v_event_payload:=jsonb_build_object(
      'lock_review_id',p_lock_review_id,'lock_kind',v_row.lock_kind::text,'target_ref',v_row.target_version_id,
      'project_id',v_project_id,'topic_id',v_topic_id,'reason',p_reason
    );
  END IF;

  v_event_id:=gen_random_uuid();
  v_event_hash:=encode(digest(v_event_payload::text,'sha256'),'hex');
  INSERT INTO public.outbox_events(
    event_id,event_type,event_version,aggregate_type,aggregate_id,aggregate_version,
    correlation_id,actor_id,payload,payload_hash,idempotency_key
  ) VALUES(
    v_event_id,v_event_type,1,'LockReview',p_lock_review_id,v_expected+1,
    p_correlation_id,v_actor,v_event_payload,v_event_hash,v_idem_hash
  );

  INSERT INTO public.audit_events(
    action,entity_type,entity_id,actor_id,actor_type,workspace_id,reason,correlation_id,payload_hash,before_version,after_version
  ) VALUES(
    v_event_type,'lock_review',p_lock_review_id,v_actor,'USER',v_workspace_id,p_reason,p_correlation_id,v_payload_hash,
    jsonb_build_object('status','IN_REVIEW','review_version',v_expected),
    jsonb_build_object('status',CASE WHEN p_decision='APPROVE' THEN 'APPROVED' ELSE 'REJECTED' END,'review_version',v_expected+1,'lock_ref',v_lock_ref)
  );

  RETURN QUERY SELECT
    p_lock_review_id,v_row.lock_kind::text,
    CASE WHEN p_decision='APPROVE' THEN 'APPROVED' ELSE 'REJECTED' END,
    v_expected+1,v_lock_ref,false;
END
$$;

DO $$
DECLARE
  direct_insert_grants integer;
BEGIN
  SELECT count(*) INTO direct_insert_grants
  FROM information_schema.role_table_grants
  WHERE grantee='acpos_app_runtime'
    AND table_schema='public'
    AND table_name='lock_reviews'
    AND privilege_type='INSERT';
  IF direct_insert_grants<>0 THEN RAISE EXCEPTION 'LOCK0042_DIRECT_INSERT_GRANT_STILL_PRESENT'; END IF;
END
$$;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0042_lock_request_canonical_event_closure',
  'd959f5dbb0cd2d9d624528a81d80d93aa87787c7db1bac2fa781c116a64e7518',
  'migration-runner',
  'CR-RUNTIME-0042'
)
ON CONFLICT(migration_id) DO NOTHING;
