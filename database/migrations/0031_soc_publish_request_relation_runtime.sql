-- ACPOS migration 0031: SOC publish request canonical target/content relation + governed local request owner.
-- Change ref: CR-SOC-0031 (PENDING PRODUCTION APPLY).
-- Resolves the target/content relation gap without using metadata as a canonical identity store.
-- Does not call any external social platform and does not claim POSTED success.

DO $$
DECLARE
  target_column_exists boolean;
  content_column_exists boolean;
BEGIN
  SELECT EXISTS(
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='publish_requests' AND column_name='social_target_id'
  ) INTO target_column_exists;
  SELECT EXISTS(
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='publish_requests' AND column_name='content_package_id'
  ) INTO content_column_exists;

  IF (NOT target_column_exists OR NOT content_column_exists)
     AND EXISTS (SELECT 1 FROM public.publish_requests) THEN
    RAISE EXCEPTION 'SOC0031_EXISTING_PUBLISH_REQUEST_BACKFILL_REQUIRED';
  END IF;
END
$$;

DO $$
DECLARE
  bootstrap_user_id uuid;
  resource_count bigint;
  approved_allow_count bigint;
BEGIN
  SELECT u.user_id INTO bootstrap_user_id
  FROM public.app_users u
  JOIN acpos_runtime.accounts a ON lower(a.email)=lower(u.email::text)
  WHERE a.id='runtime-admin' AND a.status='READY' AND u.disabled_at IS NULL
  LIMIT 1;

  IF bootstrap_user_id IS NULL THEN
    RAISE EXCEPTION 'SOC0031_BOOTSTRAP_ADMIN_NOT_READY';
  END IF;

  SELECT count(*) INTO resource_count
  FROM public.permission_resources r
  WHERE (
      (r.resource_key='action:admin:SOC-04:ACT-SOCIAL-TARGET-PUBLISH'
       AND r.resource_type='ACTION'
       AND 'INVOKE'=ANY(SELECT jsonb_array_elements_text(CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END)))
      OR
      (r.resource_key='control:CTRL-ADMIN-SOC-04-ACT-02-ACT-SOCIAL-TARGET-PUBLISH'
       AND r.resource_type='CONTROL'
       AND 'INVOKE'=ANY(SELECT jsonb_array_elements_text(CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END)))
      OR
      (r.resource_key='api:requestSocialTargetPublish'
       AND r.resource_type='API'
       AND 'EXECUTE'=ANY(SELECT jsonb_array_elements_text(CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END)))
    )
    AND r.active=true;

  IF resource_count <> 3 THEN
    RAISE EXCEPTION 'SOC0031_PERMISSION_RESOURCE_COUNT_MISMATCH:%', resource_count;
  END IF;

  INSERT INTO public.account_permission_assignments(
    user_id,resource_id,action,effect,scope,condition,gate_profile,status,
    granted_by_user_id,approval_ref,version_no,effective_from,effective_to,approval_required
  )
  SELECT
    bootstrap_user_id,
    r.resource_id,
    CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END,
    'ALLOW',
    '{}'::jsonb,
    '{}'::jsonb,
    jsonb_build_object(
      'page_uid','admin:SOC-01',
      'runtime_scope','SOC_PUBLISH_REQUEST_LOCAL_PERSISTENCE_ONLY',
      'operation_resource',r.resource_key,
      'production_apply','PENDING_FINAL_RELEASE_SEQUENCE'
    ),
    'APPROVED',
    bootstrap_user_id,
    'CR-SOC-0031-PENDING-PRODUCTION-APPLY',
    1,
    now(),
    NULL,
    false
  FROM public.permission_resources r
  WHERE r.resource_key IN (
    'action:admin:SOC-04:ACT-SOCIAL-TARGET-PUBLISH',
    'control:CTRL-ADMIN-SOC-04-ACT-02-ACT-SOCIAL-TARGET-PUBLISH',
    'api:requestSocialTargetPublish'
  )
    AND r.active=true
  ON CONFLICT (user_id,resource_id,action,version_no) DO NOTHING;

  SELECT count(*) INTO approved_allow_count
  FROM public.account_permission_assignments a
  JOIN public.permission_resources r ON r.resource_id=a.resource_id
  WHERE a.user_id=bootstrap_user_id
    AND r.resource_key IN (
      'action:admin:SOC-04:ACT-SOCIAL-TARGET-PUBLISH',
      'control:CTRL-ADMIN-SOC-04-ACT-02-ACT-SOCIAL-TARGET-PUBLISH',
      'api:requestSocialTargetPublish'
    )
    AND a.action=CASE WHEN r.resource_type='API' THEN 'EXECUTE' ELSE 'INVOKE' END
    AND a.effect='ALLOW'
    AND a.status='APPROVED'
    AND a.scope='{}'::jsonb
    AND a.condition='{}'::jsonb
    AND a.effective_from<=now()
    AND (a.effective_to IS NULL OR a.effective_to>now());

  IF approved_allow_count <> 3 THEN
    RAISE EXCEPTION 'SOC0031_APPROVED_ALLOW_COUNT_MISMATCH:%', approved_allow_count;
  END IF;
END
$$;

ALTER TABLE public.publish_requests
  ADD COLUMN IF NOT EXISTS social_target_id uuid,
  ADD COLUMN IF NOT EXISTS content_package_id uuid;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='publish_requests_social_target_id_fkey'
      AND conrelid='public.publish_requests'::regclass
  ) THEN
    ALTER TABLE public.publish_requests
      ADD CONSTRAINT publish_requests_social_target_id_fkey
      FOREIGN KEY (social_target_id)
      REFERENCES public.social_market_targets(social_target_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='publish_requests_content_package_id_fkey'
      AND conrelid='public.publish_requests'::regclass
  ) THEN
    ALTER TABLE public.publish_requests
      ADD CONSTRAINT publish_requests_content_package_id_fkey
      FOREIGN KEY (content_package_id)
      REFERENCES public.content_packages(content_package_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='publish_requests_metadata_no_canonical_identity'
      AND conrelid='public.publish_requests'::regclass
  ) THEN
    ALTER TABLE public.publish_requests
      ADD CONSTRAINT publish_requests_metadata_no_canonical_identity
      CHECK (
        NOT metadata ?| ARRAY[
          'target_id',
          'social_target_id',
          'content_package_id',
          'channel_account_id',
          'release_package_id'
        ]
      );
  END IF;
END
$$;

ALTER TABLE public.publish_requests
  ALTER COLUMN social_target_id SET NOT NULL,
  ALTER COLUMN content_package_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS publish_requests_social_target_id_idx
  ON public.publish_requests(social_target_id,created_at DESC);

CREATE INDEX IF NOT EXISTS publish_requests_content_package_id_idx
  ON public.publish_requests(content_package_id,created_at DESC);

GRANT SELECT ON public.publish_requests TO acpos_app_runtime;
ALTER TABLE public.publish_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS acpos_publish_requests_soc_select ON public.publish_requests;

CREATE POLICY acpos_publish_requests_soc_select ON public.publish_requests
FOR SELECT TO acpos_app_runtime
USING (
  acpos_runtime.current_actor_is_bootstrap_admin()
  OR acpos_runtime.has_soc_resource_action('page:admin:SOC-01','VIEW')
);

CREATE OR REPLACE FUNCTION acpos_runtime.request_soc_target_publish(
  target_id_input uuid,
  content_package_id_input uuid,
  channel_account_id_input uuid,
  expected_version_input bigint,
  idempotency_key_input text,
  schedule_at_input timestamptz DEFAULT NULL,
  content_hash_input text DEFAULT NULL,
  content_similarity_key_input text DEFAULT NULL,
  correlation_id_input uuid DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, acpos_runtime
AS $$
DECLARE
  actor_user_id uuid;
  target_row record;
  package_row record;
  existing_row record;
  created_row record;
  correlation_id uuid;
  metadata_value jsonb;
BEGIN
  actor_user_id := acpos_runtime.current_actor_user_id();
  IF actor_user_id IS NULL THEN
    RETURN jsonb_build_object('ok',false,'reason_code','SOC01_ACTOR_CONTEXT_REQUIRED');
  END IF;

  IF NOT acpos_runtime.current_actor_is_bootstrap_admin()
     AND NOT (
       acpos_runtime.has_soc_resource_action('action:admin:SOC-04:ACT-SOCIAL-TARGET-PUBLISH','INVOKE')
       AND acpos_runtime.has_soc_resource_action('control:CTRL-ADMIN-SOC-04-ACT-02-ACT-SOCIAL-TARGET-PUBLISH','INVOKE')
       AND acpos_runtime.has_soc_resource_action('api:requestSocialTargetPublish','EXECUTE')
     ) THEN
    RETURN jsonb_build_object('ok',false,'reason_code','SOC01_PUBLISH_PERMISSION_DENIED');
  END IF;

  IF expected_version_input IS NULL OR expected_version_input < 1 THEN
    RETURN jsonb_build_object('ok',false,'reason_code','SOC01_EXPECTED_VERSION_MISSING');
  END IF;

  IF idempotency_key_input IS NULL OR idempotency_key_input !~ '^[0-9a-f]{64}$' THEN
    RETURN jsonb_build_object('ok',false,'reason_code','SOC01_IDEMPOTENCY_KEY_INVALID');
  END IF;

  SELECT p.publish_request_id,p.social_target_id,p.content_package_id,p.channel_account_id,p.status,p.schedule_at
  INTO existing_row
  FROM public.publish_requests p
  WHERE p.idempotency_key=idempotency_key_input::char(64)
  LIMIT 1;

  IF FOUND THEN
    IF existing_row.social_target_id<>target_id_input
       OR existing_row.content_package_id<>content_package_id_input
       OR existing_row.channel_account_id<>channel_account_id_input THEN
      RETURN jsonb_build_object('ok',false,'reason_code','SOC01_IDEMPOTENCY_CONTEXT_CONFLICT');
    END IF;
    RETURN jsonb_build_object(
      'ok',true,'publish_request_id',existing_row.publish_request_id::text,
      'target_id',existing_row.social_target_id::text,'content_package_id',existing_row.content_package_id::text,
      'channel_account_id',existing_row.channel_account_id::text,'state',existing_row.status::text,
      'schedule_at',existing_row.schedule_at,'idempotency_replayed',true,
      'external_request_sent',false,'external_success',false
    );
  END IF;

  SELECT t.social_target_id,t.platform_key,t.join_status,t.status,t.version,t.next_eligible_at
  INTO target_row
  FROM public.social_market_targets t
  WHERE t.social_target_id=target_id_input
  FOR UPDATE;

  IF NOT FOUND THEN RETURN jsonb_build_object('ok',false,'reason_code','SOC01_TARGET_NOT_FOUND'); END IF;
  IF target_row.status<>'ACTIVE' THEN RETURN jsonb_build_object('ok',false,'reason_code','SOC01_TARGET_UNAVAILABLE'); END IF;
  IF target_row.join_status<>'READY_TO_POST' THEN RETURN jsonb_build_object('ok',false,'reason_code','SOC01_TARGET_NOT_PUBLISH_ELIGIBLE'); END IF;
  IF target_row.version<>expected_version_input THEN RETURN jsonb_build_object('ok',false,'reason_code','SOC01_VERSION_CONFLICT'); END IF;
  IF target_row.next_eligible_at IS NOT NULL AND COALESCE(schedule_at_input,now()) < target_row.next_eligible_at THEN
    RETURN jsonb_build_object('ok',false,'reason_code','SOC01_PUBLISH_COOLDOWN_ACTIVE');
  END IF;

  SELECT cp.content_package_id,cp.release_package_id,cp.channel_account_id,btrim(cp.package_hash::text) AS package_hash,
         cp.status::text AS content_package_status,rp.status::text AS release_package_status,
         rp.production_contract_id,rp.goal_id,rp.blueprint_version_id,rp.topic_id,rp.project_id,
         ca.platform_key AS channel_platform_key,ca.status::text AS channel_account_status
  INTO package_row
  FROM public.content_packages cp
  JOIN public.release_packages rp ON rp.release_package_id=cp.release_package_id
  JOIN public.channel_accounts ca ON ca.channel_account_id=cp.channel_account_id
  WHERE cp.content_package_id=content_package_id_input
    AND cp.channel_account_id=channel_account_id_input
  LIMIT 1;

  IF NOT FOUND THEN RETURN jsonb_build_object('ok',false,'reason_code','SOC01_PUBLISH_CONTEXT_INVALID'); END IF;
  IF package_row.content_package_status<>'APPROVED' THEN RETURN jsonb_build_object('ok',false,'reason_code','SOC01_CONTENT_PACKAGE_NOT_APPROVED'); END IF;
  IF package_row.release_package_status<>'APPROVED' THEN RETURN jsonb_build_object('ok',false,'reason_code','SOC01_RELEASE_PACKAGE_NOT_APPROVED'); END IF;
  IF package_row.channel_account_status<>'APPROVED' THEN RETURN jsonb_build_object('ok',false,'reason_code','SOC01_CHANNEL_ACCOUNT_NOT_APPROVED'); END IF;
  IF package_row.channel_platform_key<>target_row.platform_key THEN RETURN jsonb_build_object('ok',false,'reason_code','SOC01_CHANNEL_TARGET_PLATFORM_MISMATCH'); END IF;
  IF content_hash_input IS NOT NULL AND btrim(content_hash_input) <> package_row.package_hash THEN
    RETURN jsonb_build_object('ok',false,'reason_code','SOC01_CONTENT_HASH_MISMATCH');
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM acpos_runtime.entities e
    WHERE e.kind='SOC_CONTENT_DRAFT' AND e.status='APPROVED'
      AND e.payload->>'content_package_id'=content_package_id_input::text
      AND e.payload->>'source_package_hash'=package_row.package_hash
  ) THEN
    RETURN jsonb_build_object('ok',false,'reason_code','SOC01_CONTENT_NOT_APPROVED');
  END IF;

  correlation_id := COALESCE(correlation_id_input,gen_random_uuid());
  metadata_value := jsonb_strip_nulls(jsonb_build_object(
    'content_hash',package_row.package_hash,
    'content_similarity_key',NULLIF(btrim(content_similarity_key_input),'')
  ));

  INSERT INTO public.publish_requests(
    release_package_id,channel_account_id,schedule_at,metadata,idempotency_key,status,
    production_contract_id,goal_id,blueprint_version_id,topic_id,project_id,social_target_id,content_package_id
  )
  VALUES(
    package_row.release_package_id,channel_account_id_input,schedule_at_input,metadata_value,
    idempotency_key_input::char(64),'PENDING_EXTERNAL',
    package_row.production_contract_id,package_row.goal_id,package_row.blueprint_version_id,
    package_row.topic_id,package_row.project_id,target_id_input,content_package_id_input
  )
  RETURNING publish_request_id,status,schedule_at INTO created_row;

  UPDATE public.social_market_targets
  SET join_status='PENDING_EXTERNAL',version=version+1
  WHERE social_target_id=target_id_input AND version=expected_version_input AND join_status='READY_TO_POST';

  IF NOT FOUND THEN RAISE EXCEPTION 'SOC01_PUBLISH_TARGET_TRANSITION_RACE'; END IF;

  INSERT INTO public.audit_events(
    action,entity_type,entity_id,actor_id,actor_type,before_version,after_version,reason,correlation_id,payload_hash
  )
  VALUES(
    'requestSocialTargetPublish','admin:SOC-01',created_row.publish_request_id,actor_user_id,'USER',
    jsonb_build_object('target_id',target_id_input,'target_state','READY_TO_POST','target_version',expected_version_input),
    jsonb_build_object('publish_request_id',created_row.publish_request_id,'target_state','PENDING_EXTERNAL','target_version',expected_version_input+1),
    'SOC publish request created locally; external dispatch not executed',correlation_id,
    encode(digest(jsonb_build_object(
      'target_id',target_id_input,'content_package_id',content_package_id_input,
      'channel_account_id',channel_account_id_input,'schedule_at',schedule_at_input,'metadata',metadata_value
    )::text,'sha256'),'hex')
  );

  RETURN jsonb_build_object(
    'ok',true,'publish_request_id',created_row.publish_request_id::text,'target_id',target_id_input::text,
    'content_package_id',content_package_id_input::text,'channel_account_id',channel_account_id_input::text,
    'state',created_row.status::text,'target_state','PENDING_EXTERNAL','target_version',expected_version_input+1,
    'schedule_at',created_row.schedule_at,'idempotency_replayed',false,
    'external_request_sent',false,'external_success',false
  );
END
$$;

REVOKE ALL ON FUNCTION acpos_runtime.request_soc_target_publish(
  uuid,uuid,uuid,bigint,text,timestamptz,text,text,uuid
) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION acpos_runtime.request_soc_target_publish(
  uuid,uuid,uuid,bigint,text,timestamptz,text,text,uuid
) TO acpos_app_runtime;

DO $$
DECLARE fk_count bigint; policy_count bigint;
BEGIN
  SELECT count(*) INTO fk_count
  FROM pg_constraint
  WHERE conrelid='public.publish_requests'::regclass
    AND conname IN (
      'publish_requests_social_target_id_fkey',
      'publish_requests_content_package_id_fkey',
      'publish_requests_metadata_no_canonical_identity'
    );
  IF fk_count <> 3 THEN RAISE EXCEPTION 'SOC0031_PUBLISH_REQUEST_CONSTRAINT_COUNT_MISMATCH:%', fk_count; END IF;

  SELECT count(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname='public' AND tablename='publish_requests' AND policyname='acpos_publish_requests_soc_select';
  IF policy_count <> 1 THEN RAISE EXCEPTION 'SOC0031_PUBLISH_REQUEST_RLS_POLICY_MISMATCH:%', policy_count; END IF;
END
$$;

INSERT INTO schema_migration_history(migration_id,checksum,applied_by,approval_ref)
VALUES(
  '0031_soc_publish_request_relation_runtime',
  '81f65e614d720ad44b8d8d4b2594f7128caac5af396d16221f15f46a31fc600e',
  'migration-runner',
  'CR-SOC-0031-PENDING-PRODUCTION-APPLY'
)
ON CONFLICT (migration_id) DO NOTHING;
