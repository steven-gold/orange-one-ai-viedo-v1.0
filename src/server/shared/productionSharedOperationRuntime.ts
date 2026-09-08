import { createHash,randomUUID } from "node:crypto";
import { cookies } from "next/headers";
import { ensureProductionNeonRuntime,getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import { hashSessionToken,IDENTITY_COOKIE_NAME,resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { executeProductionAiApiCommand } from "@/server/aiApi/productionAiApiCommandRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { SharedProductionOperationRequest } from "@/server/shared/sharedProductionOperationRuntime";
type Sql=NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row=Record<string,unknown>;
function rec(v:unknown):Row{return v&&typeof v==="object"&&!Array.isArray(v)?v as Row:{};}
function rows(v:unknown):Row[]{return Array.isArray(v)?v.filter((x):x is Row=>Boolean(x)&&typeof x==="object"&&!Array.isArray(x)):[];}
function first(v:unknown):Row|null{return rows(v)[0]??null;}
function text(v:unknown):string|null{if(typeof v!=="string")return null;const x=v.trim();return x||null;}
function uuid(v:unknown):string|null{const x=text(v);return x&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(x)?x:null;}
function requireUuid(v:unknown,reason:string){const x=uuid(v);if(!x)throw new NamedRuntimeError(reason);return x;}
function object(v:unknown):Row|null{return v&&typeof v==="object"&&!Array.isArray(v)?v as Row:null;}
function hash(v:string){return createHash("sha256").update(v).digest("hex");}
async function ctx():Promise<{sql:Sql;actor_user_id:string;session_token_hash:string}>{
  await ensureProductionNeonRuntime();const sql=getProductionNeonSql();if(!sql)throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const token=(await cookies()).get(IDENTITY_COOKIE_NAME)?.value?.trim();if(!token)throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity=await resolveIdentityFromCookie(token);if(!identity.ok)throw new NamedRuntimeError(identity.reason_code);
  return{sql,actor_user_id:identity.actor.user_id,session_token_hash:hashSessionToken(token)};
}
async function generate(request:SharedProductionOperationRequest){
  const p=rec(request.payload),family=text(p.family);
  if(family!=="ASSET"&&family!=="VIDEO")throw new NamedRuntimeError("SHARED_FAMILY_INVALID");
  const taskId=requireUuid(p.task_id,"CORRECTION_TASK_ID_REQUIRED"),outputId=requireUuid(p.output_version_id,"CORRECTION_OUTPUT_VERSION_ID_REQUIRED"),findingId=requireUuid(p.finding_id,"CORRECTION_FINDING_ID_REQUIRED");
  const humanRequest=text(p.request);if(!humanRequest)throw new NamedRuntimeError("CORRECTION_REQUEST_TEXT_REQUIRED");
  const affectedScope=object(p.affected_scope);if(!affectedScope)throw new NamedRuntimeError("CORRECTION_AFFECTED_SCOPE_REQUIRED");
  const {sql,actor_user_id,session_token_hash}=await ctx();
  const lineage=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT t.task_id::text,t.department::text,t.input_fingerprint::text,t.output_contract_hash::text,
           o.output_version_id::text,o.artifact_checksum::text,o.output_uri,o.status::text AS output_status,
           f.finding_id::text,f.category,f.severity,f.evidence,
           cl.blueprint_version_id::text,
           ip.instruction_package_id::text,ip.provider_neutral_intent,
           sc.scorecard_id::text,sc.criteria_version_id::text
    FROM public.department_tasks t
    JOIN public.task_outputs o ON o.task_id=t.task_id AND o.output_version_id=${outputId}::uuid
    JOIN public.findings f ON f.output_version_id=o.output_version_id AND f.finding_id=${findingId}::uuid AND f.closed_at IS NULL
    JOIN public.child_locks cl ON cl.child_lock_id=t.child_lock_id AND cl.status='CHILD_LOCKED'
    JOIN LATERAL(
      SELECT ip0.* FROM public.instruction_packages ip0
      WHERE ip0.task_id=t.task_id AND ip0.status='APPROVED' AND ip0.approved_by IS NOT NULL AND ip0.approved_at IS NOT NULL
      ORDER BY ip0.approved_at DESC,ip0.instruction_package_id DESC LIMIT 1
    ) ip ON true
    LEFT JOIN LATERAL(
      SELECT s0.scorecard_id,s0.criteria_version_id FROM public.scorecards s0
      WHERE s0.task_id=t.task_id AND s0.output_version_id=o.output_version_id
      ORDER BY s0.created_at DESC,s0.scorecard_id DESC LIMIT 1
    ) sc ON true
    WHERE t.task_id=${taskId}::uuid AND t.department::text=${family}
    LIMIT 1
  `));
  if(!lineage)throw new NamedRuntimeError("CORRECTION_EXACT_LINEAGE_NOT_READY");
  const revalidation={criteria_version_id:text(lineage.criteria_version_id),output_contract_hash:text(lineage.output_contract_hash),input_fingerprint:text(lineage.input_fingerprint)};
  let correction=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT correction_request_id::text FROM public.correction_requests
    WHERE finding_id=${findingId}::uuid AND source_output_version_id=${outputId}::uuid AND original_owner_task_id=${taskId}::uuid
      AND status='CORRECTION_REQUIRED'
    ORDER BY created_at DESC LIMIT 1
  `));
  if(!correction){
    correction=first(await runRlsActorQuery(sql,session_token_hash,sql`
      INSERT INTO public.correction_requests(finding_id,source_output_version_id,source_instruction_package_id,source_scorecard_id,original_owner_task_id,affected_scope,revalidation_requirements,status)
      VALUES(${findingId}::uuid,${outputId}::uuid,${text(lineage.instruction_package_id)}::uuid,${uuid(lineage.scorecard_id)}::uuid,${taskId}::uuid,
             ${JSON.stringify(affectedScope)}::jsonb,${JSON.stringify(revalidation)}::jsonb,'CORRECTION_REQUIRED')
      RETURNING correction_request_id::text
    `));
  }
  const correctionRequestId=requireUuid(correction?.correction_request_id,"CORRECTION_REQUEST_CREATE_FAILED");
  const group=first(await sql`
    SELECT g.id FROM acpos_runtime.provider_groups g
    WHERE g.enabled=true AND g.use_case='ACPOS_TEXT_CHAT'
      AND EXISTS(SELECT 1 FROM acpos_runtime.provider_members m JOIN acpos_runtime.provider_profiles p0 ON p0.provider_id=m.provider_id AND p0.model_id=m.model_id
                 WHERE m.group_id=g.id AND m.enabled=true AND p0.enabled=true AND p0.health_status='HEALTHY')
    ORDER BY g.updated_at DESC,g.id LIMIT 1
  `);
  const groupId=text(group?.id);if(!groupId)throw new NamedRuntimeError("CORRECTION_AI_ROUTE_NOT_READY");
  const canonicalInstruction=[
    "你是 ACPOS 修正腳本產生器。只輸出繁體中文、供下游 Provider-independent 執行的修正指令。",
    "禁止加入特定 Provider 語法，禁止改寫未要求範圍，禁止覆蓋來源版本。",
    `部門：${family}`,`人類修改要求：${humanRequest}`,`受影響範圍：${JSON.stringify(affectedScope)}`,
    `Finding：${findingId} / ${text(lineage.severity)??""} / ${text(lineage.category)??""}`,
    `來源 output：${outputId}`,`Blueprint：${text(lineage.blueprint_version_id)??""}`,`Instruction package：${text(lineage.instruction_package_id)??""}`
  ].join("\n");
  const routed=rec(await executeProductionAiApiCommand({operation_id:"executeProviderRoute",correlation_id:request.correlation_id,path_params:{},payload:{
    candidate_group_id:groupId,required_capability:"TEXT_CHAT",data_classification:"INTERNAL",use_case:"ACPOS_TEXT_CHAT",
    canonical_instruction:canonicalInstruction,canonical_instruction_id:`CORRECTION:${correctionRequestId}`,
    scoped_context:{family,task_id:taskId,output_version_id:outputId,finding_id:findingId,blueprint_version_id:text(lineage.blueprint_version_id),instruction_package_id:text(lineage.instruction_package_id)}
  }}));
  const routeDecisionId=requireUuid(routed.route_decision_id,"CORRECTION_ROUTE_DECISION_ID_REQUIRED");
  if(text(routed.status)!=="SUCCESS"||routed.external_request_sent!==true)throw new NamedRuntimeError("CORRECTION_PROVIDER_ROUTE_NOT_SUCCESS");
  const decision=first(await sql`SELECT provider_id,model_id,payload FROM acpos_runtime.provider_route_decisions WHERE id=${routeDecisionId} LIMIT 1`);
  const decisionPayload=object(decision?.payload);const generated=text(decisionPayload?.normalized_result);if(!generated)throw new NamedRuntimeError("CORRECTION_PROVIDER_RESULT_REQUIRED");
  const next=first(await runRlsActorQuery(sql,session_token_hash,sql`SELECT COALESCE(max(version_no),0)+1 AS version_no FROM public.correction_script_versions WHERE correction_request_id=${correctionRequestId}::uuid`));
  const versionNo=Number(next?.version_no??1);if(!Number.isSafeInteger(versionNo)||versionNo<1)throw new NamedRuntimeError("CORRECTION_VERSION_NUMBER_INVALID");
  const candidateId=randomUUID();
  const instruction={language:"zh-TW",provider_neutral:true,human_request:humanRequest,generated_instruction:generated,affected_scope:affectedScope,source_refs:{task_id:taskId,output_version_id:outputId,finding_id:findingId,blueprint_version_id:text(lineage.blueprint_version_id),instruction_package_id:text(lineage.instruction_package_id)},provider_route_decision_id:routeDecisionId};
  const contentHash=hash(JSON.stringify({correction_request_id:correctionRequestId,version_no:versionNo,instruction}));
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.correction_script_versions(correction_script_version_id,correction_request_id,failed_output_id,correction_instruction,status,target_department,source_blueprint_version_id,source_instruction_package_id,provider_job_id,root_cause,created_by_subject_type,version_no,content_hash)
    VALUES(${candidateId}::uuid,${correctionRequestId}::uuid,${outputId}::uuid,${JSON.stringify(instruction)}::jsonb,'CANDIDATE',${family},${text(lineage.blueprint_version_id)}::uuid,
           ${text(lineage.instruction_package_id)}::uuid,NULL,${JSON.stringify({finding_id:findingId,category:text(lineage.category),severity:text(lineage.severity),evidence:lineage.evidence})}::jsonb,'USER',${versionNo},${contentHash}::char(64))
  `);
  await sql`
    INSERT INTO acpos_runtime.correction_requests_runtime(id,finding_id,source_output_version_id,source_instruction_package_id,source_scorecard_id,original_owner_task_id,blueprint_version_id,department,provider_id,root_cause,affected_scope_json,revalidation_requirements_json,status)
    VALUES(${correctionRequestId},${findingId},${outputId},${text(lineage.instruction_package_id)},${text(lineage.scorecard_id)},${taskId},${text(lineage.blueprint_version_id)},${family},NULL,
           ${text(lineage.category)??"FINDING"},${JSON.stringify(affectedScope)}::jsonb,${JSON.stringify(revalidation)}::jsonb,'CORRECTION_REQUIRED')
    ON CONFLICT(id) DO UPDATE SET affected_scope_json=excluded.affected_scope_json,revalidation_requirements_json=excluded.revalidation_requirements_json,updated_at=now()
  `;
  await sql`
    INSERT INTO acpos_runtime.correction_script_versions_runtime(id,correction_request_id,version_no,finding_id,failed_output_version_id,blueprint_version_id,original_instruction_package_id,department,provider_id,root_cause_snapshot,correction_instruction_json,status)
    VALUES(${candidateId},${correctionRequestId},${versionNo},${findingId},${outputId},${text(lineage.blueprint_version_id)},${text(lineage.instruction_package_id)},${family},${text(decision?.provider_id)},
           ${text(lineage.category)??"FINDING"},${JSON.stringify(instruction)}::jsonb,'CANDIDATE')
  `;
  return{candidate_ref:candidateId,correction_request_ref:correctionRequestId,content_hash:contentHash,provider_route_decision_id:routeDecisionId};
}
async function approve(request:SharedProductionOperationRequest){
  const p=rec(request.payload),family=text(p.family);if(family!=="ASSET"&&family!=="VIDEO")throw new NamedRuntimeError("SHARED_FAMILY_INVALID");
  const candidateId=requireUuid(p.candidate_ref,"CORRECTION_CANDIDATE_REQUIRED"),decisionReason=text(p.decision_reason);if(!decisionReason)throw new NamedRuntimeError("CORRECTION_DECISION_REASON_REQUIRED");
  const expectedHash=text(p.expected_content_hash);const {sql,actor_user_id,session_token_hash}=await ctx();
  const current=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT c.correction_script_version_id::text,c.correction_request_id::text,c.status,c.content_hash::text,cr.original_owner_task_id::text,t.department::text
    FROM public.correction_script_versions c
    JOIN public.correction_requests cr ON cr.correction_request_id=c.correction_request_id
    JOIN public.department_tasks t ON t.task_id=cr.original_owner_task_id
    WHERE c.correction_script_version_id=${candidateId}::uuid LIMIT 1
  `));
  if(!current)throw new NamedRuntimeError("CORRECTION_CANDIDATE_NOT_FOUND");
  if(text(current.department)!==family)throw new NamedRuntimeError("CORRECTION_FAMILY_MISMATCH");
  if(text(current.status)!=="CANDIDATE")throw new NamedRuntimeError("CORRECTION_CANDIDATE_STATE_CONFLICT");
  if(expectedHash&&expectedHash!==text(current.content_hash))throw new NamedRuntimeError("CORRECTION_CANDIDATE_HASH_MISMATCH");
  const changed=first(await runRlsActorQuery(sql,session_token_hash,sql`
    WITH prior AS(
      UPDATE public.correction_script_versions SET status='SUPERSEDED'
      WHERE correction_request_id=${text(current.correction_request_id)}::uuid AND status='APPROVED' AND correction_script_version_id<>${candidateId}::uuid
      RETURNING correction_script_version_id
    )
    UPDATE public.correction_script_versions
    SET status='APPROVED',decision_reason=${decisionReason},decided_by=${actor_user_id}::uuid,decided_at=now()
    WHERE correction_script_version_id=${candidateId}::uuid AND status='CANDIDATE'
    RETURNING correction_script_version_id::text,content_hash::text,decided_at::text
  `));
  if(!changed)throw new NamedRuntimeError("CORRECTION_CANDIDATE_APPROVAL_CONFLICT");
  await sql`UPDATE acpos_runtime.correction_script_versions_runtime SET status='APPROVED',decision_reason=${decisionReason},decided_at=now() WHERE id=${candidateId} AND status='CANDIDATE'`;
  return{approved_candidate_ref:candidateId,content_hash:text(changed.content_hash),decided_at:text(changed.decided_at)};
}
async function restore(request:SharedProductionOperationRequest){
  const p=rec(request.payload);if(text(p.family)!=="ASSET")throw new NamedRuntimeError("RESTORE_ASSET_FAMILY_REQUIRED");
  const outputId=requireUuid(p.output_version_id,"ASSET_VERSION_REQUIRED");const {sql,actor_user_id,session_token_hash}=await ctx();
  const source=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT o.output_version_id::text,o.task_id::text,o.project_id::text,o.topic_id::text,o.output_uri,o.artifact_checksum::text,o.status::text,o.immutable_at::text,t.department::text
    FROM public.task_outputs o JOIN public.department_tasks t ON t.task_id=o.task_id
    WHERE o.output_version_id=${outputId}::uuid AND t.department::text='ASSET' LIMIT 1
  `));
  if(!source)throw new NamedRuntimeError("ASSET_VERSION_NOT_FOUND");
  if(text(source.status)!=="ACCEPTED"||!text(source.immutable_at))throw new NamedRuntimeError("CONFIRMED_EXACT_VERSION_REQUIRED");
  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT asset_version_restore_draft_id::text FROM public.asset_version_restore_drafts
    WHERE source_output_version_id=${outputId}::uuid AND created_by=${actor_user_id}::uuid AND status='DRAFT'
    ORDER BY created_at DESC LIMIT 1
  `));
  if(existing)return{restored_version_ref:text(existing.asset_version_restore_draft_id),source_output_version_id:outputId,reused_existing_draft:true};
  const draftId=randomUUID();
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.asset_version_restore_drafts(asset_version_restore_draft_id,source_output_version_id,task_id,project_id,topic_id,source_output_uri,source_artifact_checksum,reason,status,created_by)
    VALUES(${draftId}::uuid,${outputId}::uuid,${text(source.task_id)}::uuid,${uuid(source.project_id)}::uuid,${uuid(source.topic_id)}::uuid,${text(source.output_uri)},${text(source.artifact_checksum)}::char(64),
           'USER_REQUESTED_RESTORE_AS_NEW_DRAFT','DRAFT',${actor_user_id}::uuid)
  `);
  return{restored_version_ref:draftId,source_output_version_id:outputId,reused_existing_draft:false};
}
async function lock(request:SharedProductionOperationRequest,family:"ASSET"|"VIDEO"){
  const p=rec(request.payload);if(text(p.family)!==family)throw new NamedRuntimeError(`${family}_LOCK_FAMILY_MISMATCH`);
  const outputId=requireUuid(p.output_version_id,`${family}_VERSION_REQUIRED`),manifestHash=text(p.manifest_hash);const {sql,actor_user_id,session_token_hash}=await ctx();
  const source=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT o.output_version_id::text,o.task_id::text,o.artifact_checksum::text,o.output_contract_hash::text,o.status::text,o.immutable_at::text,
           t.department::text,t.status::text AS task_status,
           s.scorecard_id::text,s.total_score::text,s.gate_status::text
    FROM public.task_outputs o JOIN public.department_tasks t ON t.task_id=o.task_id
    JOIN LATERAL(SELECT s0.* FROM public.scorecards s0 WHERE s0.task_id=t.task_id AND s0.output_version_id=o.output_version_id ORDER BY s0.created_at DESC,s0.scorecard_id DESC LIMIT 1)s ON true
    WHERE o.output_version_id=${outputId}::uuid AND t.department::text=${family} LIMIT 1
  `));
  if(!source)throw new NamedRuntimeError(`${family}_VERSION_NOT_FOUND`);
  if(text(source.status)!=="ACCEPTED"||!text(source.immutable_at)||text(source.task_status)!=="HANDOFF_READY"||text(source.gate_status)!=="PASS")throw new NamedRuntimeError(`${family}_CONFIRMED_EXACT_VERSION_REQUIRED`);
  if(family==="VIDEO"&&Number(source.total_score)<95)throw new NamedRuntimeError("VIDEO_SCORE_BELOW_LOCK_THRESHOLD");
  if(manifestHash&&manifestHash!=="—"&&manifestHash!==text(source.output_contract_hash))throw new NamedRuntimeError(`${family}_MANIFEST_HASH_MISMATCH`);
  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`SELECT production_output_version_lock_id::text FROM public.production_output_version_locks WHERE output_version_id=${outputId}::uuid LIMIT 1`));
  if(existing)return{locked_version_ref:text(existing.production_output_version_lock_id),output_version_id:outputId,already_locked:true};
  const lockId=randomUUID();
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.production_output_version_locks(production_output_version_lock_id,output_version_id,task_id,department,scorecard_id,artifact_checksum,output_contract_hash,manifest_hash,locked_by,status)
    VALUES(${lockId}::uuid,${outputId}::uuid,${text(source.task_id)}::uuid,${family},${text(source.scorecard_id)}::uuid,${text(source.artifact_checksum)}::char(64),
           ${text(source.output_contract_hash)}::char(64),${manifestHash&&manifestHash!=="—"?manifestHash:null}::char(64),${actor_user_id}::uuid,'LOCKED')
  `);
  return{locked_version_ref:lockId,output_version_id:outputId,already_locked:false};
}
export async function executeProductionSharedOperation(request:SharedProductionOperationRequest){
  switch(request.operation_id){
    case"generateCorrectionScriptCandidate":return generate(request);
    case"approveCorrectionScriptCandidate":return approve(request);
    case"restoreAssetVersionAsNewDraft":return restore(request);
    case"lockAssetVersion":return lock(request,"ASSET");
    case"lockVideoVersion":return lock(request,"VIDEO");
  }
}
export async function auditProductionSharedOperation(entry:SharedProductionOperationRequest&{outcome:"ALLOWED"|"DENIED"|"SUCCESS"|"ERROR";reason_code?:string}){
  try{const {sql,actor_user_id}=await ctx();const p=rec(entry.payload),entity=uuid(p.candidate_ref)??uuid(p.output_version_id)??uuid(p.task_id)??randomUUID();const correlation=uuid(entry.correlation_id)??randomUUID();
    await sql`INSERT INTO public.audit_events(action,entity_type,entity_id,actor_id,actor_type,reason,correlation_id,payload_hash)
      VALUES(${entry.operation_id},'SHARED_PRODUCTION_RUNTIME',${entity}::uuid,${actor_user_id}::uuid,'USER',${entry.reason_code??entry.outcome},${correlation}::uuid,${hash(JSON.stringify({operation_id:entry.operation_id,outcome:entry.outcome,reason_code:entry.reason_code??null}))}::char(64))`;}catch{}
}
