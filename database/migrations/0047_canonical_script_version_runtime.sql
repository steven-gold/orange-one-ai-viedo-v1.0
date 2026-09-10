-- ACPOS migration 0047: Current canonical script version materializer.
-- Exact Topic/Blueprint/ProductionContract lineage, explicit vN, idempotency, audit and event.
-- No implicit latest/default/current resolution and no auto-approval.

CREATE OR REPLACE FUNCTION acpos_runtime.create_canonical_script_version(
  p_scope jsonb,
  p_expected_version text,
  p_correlation_id uuid,
  p_idempotency_key text,
  p_project_id uuid,
  p_topic_id uuid,
  p_blueprint_version_id uuid,
  p_content text,
  p_source_script_ref text,
  p_change_summary text
)
RETURNS TABLE(
  canonical_script_version_id uuid,
  topic_id uuid,
  source_topic_version_id uuid,
  blueprint_version_id uuid,
  topic_production_contract_id uuid,
  version_no integer,
  status text,
  content_hash text,
  idempotent_replay boolean
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
DECLARE
  v_actor uuid;
  v_workspace_id uuid;
  v_source_topic_version_id uuid;
  v_contract_id uuid;
  v_blueprint_status public.acpos_status;
  v_expected integer;
  v_idem_hash char(64);
  v_payload_hash char(64);
  v_content_hash char(64);
  v_existing public.canonical_script_versions%ROWTYPE;
  v_script_id uuid;
  v_script_document jsonb;
  v_event_payload jsonb;
  v_event_hash char(64);
BEGIN
  v_actor:=acpos_runtime.current_actor_user_id();
  IF v_actor IS NULL THEN RAISE EXCEPTION 'IDENTITY_RUNTIME_NOT_BOUND'; END IF;
  IF NOT acpos_runtime.has_account_resource_action('api:createCanonicalScriptVersion','EXECUTE') THEN
    RAISE EXCEPTION 'ACCOUNT_PERMISSION_DENIED';
  END IF;

  IF p_scope IS NULL OR jsonb_typeof(p_scope)<>'object' THEN RAISE EXCEPTION 'R9_CONTEXT_REQUIRED'; END IF;
  IF p_expected_version IS NULL OR p_expected_version !~ '^v[1-9][0-9]*$' THEN RAISE EXCEPTION 'VERSION_REQUIRED'; END IF;
  v_expected:=substring(p_expected_version from 2)::integer;
  IF p_correlation_id IS NULL THEN RAISE EXCEPTION 'CORRELATION_ID_INVALID'; END IF;
  IF length(coalesce(p_idempotency_key,''))<16 OR length(p_idempotency_key)>128 THEN RAISE EXCEPTION 'IDEMPOTENCY_KEY_INVALID'; END IF;
  IF p_project_id IS NULL THEN RAISE EXCEPTION 'PROJECT-ID_INVALID'; END IF;
  IF p_topic_id IS NULL THEN RAISE EXCEPTION 'TOPIC-ID_INVALID'; END IF;
  IF p_blueprint_version_id IS NULL THEN RAISE EXCEPTION 'BLUEPRINT-VERSION-ID_INVALID'; END IF;
  IF nullif(btrim(p_content),'') IS NULL THEN RAISE EXCEPTION 'CONTENT_INVALID'; END IF;
  IF p_source_script_ref IS NOT NULL AND nullif(btrim(p_source_script_ref),'') IS NULL THEN RAISE EXCEPTION 'SOURCE-SCRIPT-REF_INVALID'; END IF;
  IF p_change_summary IS NOT NULL AND nullif(btrim(p_change_summary),'') IS NULL THEN RAISE EXCEPTION 'CHANGE-SUMMARY_INVALID'; END IF;

  SELECT p.workspace_id,tv.topic_version_id,pc.topic_production_contract_id,bv.status
    INTO v_workspace_id,v_source_topic_version_id,v_contract_id,v_blueprint_status
  FROM public.blueprint_versions bv
  JOIN public.topic_blueprints tb ON tb.topic_blueprint_id=bv.topic_blueprint_id
  JOIN public.topic_production_contracts pc ON pc.topic_production_contract_id=tb.topic_production_contract_id
  JOIN public.topic_versions tv ON tv.topic_version_id=pc.topic_version_id
  JOIN public.topics t ON t.topic_id=tv.topic_id
  JOIN public.projects p ON p.project_id=t.project_id
  WHERE bv.blueprint_version_id=p_blueprint_version_id
    AND t.topic_id=p_topic_id
    AND t.project_id=p_project_id;

  IF v_workspace_id IS NULL OR v_source_topic_version_id IS NULL OR v_contract_id IS NULL THEN
    RAISE EXCEPTION 'CANONICAL_SCRIPT_LINEAGE_MISMATCH';
  END IF;
  IF v_blueprint_status NOT IN('READY_FOR_CHILD_REVIEW','IN_REVIEW','CHILD_LOCKED') THEN
    RAISE EXCEPTION 'CANONICAL_SCRIPT_BLUEPRINT_NOT_READY';
  END IF;
  IF NOT acpos_runtime.can_manage_project(p_project_id) THEN RAISE EXCEPTION 'ACCOUNT_PERMISSION_DENIED'; END IF;

  IF nullif(p_scope->>'workspace_id','') IS DISTINCT FROM v_workspace_id::text THEN RAISE EXCEPTION 'SCOPE_WORKSPACE_MISMATCH'; END IF;
  IF nullif(p_scope->>'project_id','') IS DISTINCT FROM p_project_id::text THEN RAISE EXCEPTION 'SCOPE_PROJECT_MISMATCH'; END IF;
  IF nullif(p_scope->>'topic_id','') IS DISTINCT FROM p_topic_id::text THEN RAISE EXCEPTION 'SCOPE_TOPIC_MISMATCH'; END IF;

  v_idem_hash:=encode(digest(p_idempotency_key,'sha256'),'hex');
  v_content_hash:=encode(digest(p_content,'sha256'),'hex');
  v_payload_hash:=encode(digest(
    jsonb_build_object(
      'scope',p_scope,
      'expected_version',p_expected_version,
      'correlation_id',p_correlation_id,
      'project_id',p_project_id,
      'topic_id',p_topic_id,
      'blueprint_version_id',p_blueprint_version_id,
      'content',p_content,
      'source_script_ref',p_source_script_ref,
      'change_summary',p_change_summary
    )::text,'sha256'),'hex');

  SELECT * INTO v_existing
  FROM public.canonical_script_versions
  WHERE request_idempotency_key_hash=v_idem_hash
  LIMIT 1;

  IF FOUND THEN
    IF v_existing.request_payload_hash<>v_payload_hash THEN RAISE EXCEPTION 'IDEMPOTENCY_CONFLICT'; END IF;
    RETURN QUERY SELECT
      v_existing.canonical_script_version_id,v_existing.topic_id,v_existing.source_topic_version_id,
      v_existing.blueprint_version_id,v_contract_id,v_existing.version_no,v_existing.status::text,
      v_existing.content_hash::text,true;
    RETURN;
  END IF;

  IF EXISTS(
    SELECT 1 FROM public.canonical_script_versions
    WHERE topic_id=p_topic_id AND version_no=v_expected
  ) THEN RAISE EXCEPTION 'VERSION_CONFLICT'; END IF;

  v_script_id:=gen_random_uuid();
  v_script_document:=jsonb_build_object(
    'content',p_content,
    'identity_and_lineage',jsonb_build_object(
      'project_id',p_project_id,
      'topic_id',p_topic_id,
      'project_blueprint_ref',p_blueprint_version_id,
      'topic_production_scope_ref',v_contract_id,
      'canonical_script_hash',v_content_hash,
      'project_canon_refs','[]'::jsonb,
      'dna_refs','[]'::jsonb
    ),
    'source_script_ref',p_source_script_ref,
    'change_summary',p_change_summary
  );

  INSERT INTO public.canonical_script_versions(
    canonical_script_version_id,topic_id,source_topic_version_id,version_no,script_document,status,content_hash,
    created_by,blueprint_version_id,request_idempotency_key_hash,request_payload_hash,source_script_ref,change_summary
  ) VALUES(
    v_script_id,p_topic_id,v_source_topic_version_id,v_expected,v_script_document,'DRAFT',v_content_hash,
    v_actor,p_blueprint_version_id,v_idem_hash,v_payload_hash,p_source_script_ref,p_change_summary
  );

  v_event_payload:=jsonb_build_object(
    'canonical_script_version_id',v_script_id,
    'project_id',p_project_id,
    'topic_id',p_topic_id,
    'source_topic_version_id',v_source_topic_version_id,
    'blueprint_version_id',p_blueprint_version_id,
    'topic_production_contract_id',v_contract_id,
    'version_no',v_expected,
    'status','DRAFT',
    'content_hash',v_content_hash
  );
  v_event_hash:=encode(digest(v_event_payload::text,'sha256'),'hex');

  INSERT INTO public.outbox_events(
    event_id,event_type,event_version,aggregate_type,aggregate_id,aggregate_version,
    correlation_id,actor_id,payload,payload_hash,idempotency_key
  ) VALUES(
    gen_random_uuid(),'script.version_created',1,'CanonicalScriptVersion',v_script_id,v_expected,
    p_correlation_id,v_actor,v_event_payload,v_event_hash,v_idem_hash
  );

  INSERT INTO public.audit_events(
    action,entity_type,entity_id,actor_id,actor_type,workspace_id,reason,correlation_id,payload_hash,before_version,after_version
  ) VALUES(
    'script.version_created','workspace:CORE-06',v_script_id,v_actor,'USER',v_workspace_id,p_change_summary,
    p_correlation_id,v_payload_hash,NULL,
    jsonb_build_object('version_no',v_expected,'status','DRAFT','content_hash',v_content_hash)
  );

  RETURN QUERY SELECT
    v_script_id,p_topic_id,v_source_topic_version_id,p_blueprint_version_id,v_contract_id,
    v_expected,'DRAFT',v_content_hash::text,false;
END
$$;

GRANT EXECUTE ON FUNCTION acpos_runtime.create_canonical_script_version(
  jsonb,text,uuid,text,uuid,uuid,uuid,text,text,text
) TO acpos_app_runtime;

INSERT INTO public.schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0047_canonical_script_version_runtime',
  '7f9a709236c13482b67deeb63d09085eadcde1a0ae05920d39a31b0e67b8e19f',
  'migration-runner',
  'CR-RUNTIME-0047'
)
ON CONFLICT(migration_id) DO NOTHING;
