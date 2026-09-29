import { createHash, randomUUID } from "node:crypto";
import { cookies } from "next/headers";
import { ensureProductionNeonRuntime,getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import { hashSessionToken,IDENTITY_COOKIE_NAME,resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { executeProductionAiApiCommand } from "@/server/aiApi/productionAiApiCommandRuntime";
import { NamedRuntimeError,namedReason } from "@/server/shared/namedRuntimeError";
import type { EditVoiceRequest } from "@/server/edit/editVoiceRuntime";

type Sql=NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row=Record<string,unknown>;
function rec(v:unknown):Row{return v&&typeof v==="object"&&!Array.isArray(v)?v as Row:{};}
function rows(v:unknown):Row[]{return Array.isArray(v)?v.filter((x):x is Row=>Boolean(x)&&typeof x==="object"&&!Array.isArray(x)):[];}
function first(v:unknown):Row|null{return rows(v)[0]??null;}
function text(v:unknown):string|null{if(typeof v!=="string")return null;const x=v.trim();return x||null;}
function uuid(v:unknown):string|null{const x=text(v);return x&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(x)?x:null;}
function requireUuid(v:unknown,r:string){const x=uuid(v);if(!x)throw new NamedRuntimeError(r);return x;}
function obj(v:unknown):Row|null{return v&&typeof v==="object"&&!Array.isArray(v)?v as Row:null;}
function sha(v:string){return createHash("sha256").update(v).digest("hex");}
async function context(){
  await ensureProductionNeonRuntime();const sql=getProductionNeonSql();if(!sql)throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const token=(await cookies()).get(IDENTITY_COOKIE_NAME)?.value?.trim();if(!token)throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity=await resolveIdentityFromCookie(token);if(!identity.ok)throw new NamedRuntimeError(identity.reason_code);
  return{sql,actor_user_id:identity.actor.user_id,session_token_hash:hashSessionToken(token)};
}
async function runRow(sql:Sql,session:string,runId:string){
  const r=first(await runRlsActorQuery(sql,session,sql`
    SELECT id,task_id,timeline_version_id,current_state,status,current_output_version_id,updated_at::text
    FROM acpos_runtime.editing_runtime_runs_runtime WHERE id=${runId} LIMIT 1
  `));if(!r)throw new NamedRuntimeError("EDIT_RUNTIME_RUN_NOT_FOUND");return r;
}
async function exactTask(sql:Sql,session:string,taskId:string){
  const t=first(await runRlsActorQuery(sql,session,sql`
    SELECT t.task_id::text,t.status::text,t.production_goal_id::text,t.production_contract_id::text,t.goal_id::text,
           t.topic_id::text,t.project_id::text,cl.blueprint_version_id::text,btrim(t.output_contract_hash::text) AS output_contract_hash
    FROM public.department_tasks t
    JOIN public.child_locks cl ON cl.child_lock_id=t.child_lock_id AND cl.status='LOCKED'
    WHERE t.task_id=${taskId}::uuid AND t.department::text='EDITING' LIMIT 1
  `));if(!t)throw new NamedRuntimeError("EDIT_TASK_NOT_FOUND");return t;
}
async function saveVersion(request:EditVoiceRequest){
  const runId=requireUuid(request.path_params.runId,"EDIT_RUNTIME_RUN_ID_REQUIRED");const {sql,actor_user_id,session_token_hash}=await context();
  const run=await runRow(sql,session_token_hash,runId),taskId=requireUuid(run.task_id,"EDIT_TASK_ID_REQUIRED"),task=await exactTask(sql,session_token_hash,taskId);
  if(text(run.current_state)!=="FINALIZE"||!["READY","EVAL_PASS","EVAL_REQUIRED"].includes(text(run.status)??""))throw new NamedRuntimeError("EDIT_FINALIZE_STATE_NOT_READY");
  if(text(task.status)!=="HANDOFF_READY")throw new NamedRuntimeError("EDIT_STAGE_CONFIRMATION_REQUIRED");
  const draftId=requireUuid(run.timeline_version_id,"EDIT_WORKING_DRAFT_REQUIRED");
  const draft=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT editing_timeline_id::text,timeline_document,btrim(timing_hash::text) AS timing_hash,source_video_output_version_id::text,status::text
    FROM public.editing_timelines WHERE editing_timeline_id=${draftId}::uuid AND task_id=${taskId}::uuid AND status='DRAFT' LIMIT 1
  `));
  if(!draft)throw new NamedRuntimeError("EDIT_EXACT_WORKING_DRAFT_REQUIRED");
  const score=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT s.scorecard_id::text,s.output_version_id::text,s.gate_status::text,s.total_score::text
    FROM public.scorecards s JOIN public.task_outputs o ON o.output_version_id=s.output_version_id AND o.task_id=s.task_id
    WHERE s.task_id=${taskId}::uuid AND s.gate_status='PASS'
    ORDER BY s.created_at DESC,s.scorecard_id DESC LIMIT 1
  `));
  if(!score)throw new NamedRuntimeError("EDIT_FINALIZE_PASS_SCORECARD_REQUIRED");
  const sourceHash=sha(JSON.stringify({timeline_document:draft.timeline_document,timing_hash:text(draft.timing_hash)}));
  const next=first(await runRlsActorQuery(sql,session_token_hash,sql`SELECT COALESCE(max(timeline_version),0)+1 AS n FROM public.editing_timelines WHERE task_id=${taskId}::uuid`));
  const versionNo=Number(next?.n);if(!Number.isSafeInteger(versionNo)||versionNo<1)throw new NamedRuntimeError("EDIT_VERSION_NUMBER_INVALID");
  const versionId=randomUUID(),contentHash=sha(JSON.stringify({task_id:taskId,timeline_version:versionNo,timeline_document:draft.timeline_document,timing_hash:text(draft.timing_hash),source_draft_hash:sourceHash}));
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.editing_timelines(
      editing_timeline_id,task_id,timeline_version,source_video_output_version_id,timeline_document,timing_hash,status,
      source_timeline_id,source_draft_hash,version_content_hash,source_scorecard_id,saved_by,saved_at
    ) VALUES(
      ${versionId}::uuid,${taskId}::uuid,${versionNo},${text(draft.source_video_output_version_id)}::uuid,${JSON.stringify(draft.timeline_document)}::jsonb,
      ${text(draft.timing_hash)}::char(64),'APPROVED',${draftId}::uuid,${sourceHash}::char(64),${contentHash}::char(64),
      ${text(score.scorecard_id)}::uuid,${actor_user_id}::uuid,now()
    )
  `);
  await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE acpos_runtime.editing_runtime_runs_runtime SET timeline_version_id=${versionId},current_state='FINALIZE',status='VERSION_SAVED',updated_at=now()
    WHERE id=${runId} RETURNING id
  `);
  return{edit_version_id:versionId,source_draft_ref:draftId,source_draft_hash:sourceHash,content_hash:contentHash,scorecard_ref:text(score.scorecard_id)};
}
async function renderRoute(sql:Sql,session:string){
  const candidates=rows(await runRlsActorQuery(sql,session,sql`
    SELECT rp.route_policy_id::text,rp.fallback_policy,btrim(rp.policy_hash::text) AS policy_hash,
           pc.provider_capability_id::text,pc.provider_key,pc.model_key,pc.limits
    FROM public.route_policies rp JOIN public.provider_capabilities pc ON pc.provider_capability_id=rp.provider_capability_id
    WHERE rp.department::text='EDITING' AND rp.status='APPROVED' AND pc.status='APPROVED'
      AND upper(COALESCE(pc.limits->>'capability','')) IN('EDIT_RENDER','MEDIA_RENDER','VIDEO_RENDER')
    ORDER BY rp.route_policy_id LIMIT 2
  `));
  if(candidates.length===0)throw new NamedRuntimeError("EDIT_RENDER_PROVIDER_ROUTE_NOT_READY");
  if(candidates.length>1)throw new NamedRuntimeError("EDIT_RENDER_PROVIDER_ROUTE_AMBIGUOUS");
  const route=candidates[0]!,groupId=text(obj(route.fallback_policy)?.candidate_group_id),cap=text(obj(route.limits)?.capability);
  if(!groupId||!cap)throw new NamedRuntimeError("EDIT_RENDER_PROVIDER_BINDING_INCOMPLETE");
  return{route,groupId,cap};
}
async function startRender(request:EditVoiceRequest){
  const runId=requireUuid(request.path_params.runId,"EDIT_RUNTIME_RUN_ID_REQUIRED"),p=rec(request.payload),editVersionId=requireUuid(p.edit_version_id,"EDIT_VERSION_ID_REQUIRED");
  const settings=obj(p.settings)??{};const {sql,session_token_hash}=await context();const run=await runRow(sql,session_token_hash,runId),taskId=requireUuid(run.task_id,"EDIT_TASK_ID_REQUIRED");
  if(text(run.current_state)!=="FINALIZE"||text(run.status)!=="VERSION_SAVED"||text(run.timeline_version_id)!==editVersionId)throw new NamedRuntimeError("EDIT_SAVED_VERSION_NOT_CURRENT");
  const version=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT editing_timeline_id::text,timeline_document,btrim(timing_hash::text) AS timing_hash,btrim(version_content_hash::text) AS version_content_hash,source_video_output_version_id::text
    FROM public.editing_timelines WHERE editing_timeline_id=${editVersionId}::uuid AND task_id=${taskId}::uuid AND status='APPROVED' AND saved_at IS NOT NULL LIMIT 1
  `));if(!version)throw new NamedRuntimeError("EDIT_IMMUTABLE_VERSION_REQUIRED");
  const {route,groupId,cap}=await renderRoute(sql,session_token_hash);
  const settingsHash=sha(JSON.stringify(settings)),key=sha([runId,editVersionId,text(route.route_policy_id),text(route.policy_hash),settingsHash].join("|"));
  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`SELECT edit_render_job_id::text,status,output_version_id::text FROM public.edit_render_jobs WHERE idempotency_key=${key} LIMIT 1`));
  if(existing)return{render_job_id:text(existing.edit_render_job_id),status:text(existing.status),output_version_id:text(existing.output_version_id),idempotent_replay:true};
  const jobId=randomUUID();
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.edit_render_jobs(edit_render_job_id,run_id,task_id,input_edit_version_id,route_policy_id,idempotency_key,settings,settings_hash,status)
    VALUES(${jobId}::uuid,${runId},${taskId}::uuid,${editVersionId}::uuid,${text(route.route_policy_id)}::uuid,${key}::char(64),${JSON.stringify(settings)}::jsonb,${settingsHash}::char(64),'QUEUED')
  `);
  try{
    await runRlsActorQuery(sql,session_token_hash,sql`UPDATE public.edit_render_jobs SET status='RUNNING',started_at=now(),updated_at=now() WHERE edit_render_job_id=${jobId}::uuid RETURNING edit_render_job_id`);
    const routed=rec(await executeProductionAiApiCommand({operation_id:"executeProviderRoute",correlation_id:request.correlation_id,path_params:{},payload:{
      candidate_group_id:groupId,required_capability:cap,data_classification:"INTERNAL",use_case:"ACPOS_EDIT_RENDER",
      canonical_instruction:JSON.stringify({operation:"RENDER_EDIT_VERSION",edit_version_id:editVersionId,timeline_document:version.timeline_document,timing_hash:text(version.timing_hash),settings}),
      canonical_instruction_id:`EDIT_RENDER:${editVersionId}:${settingsHash}`,
      scoped_context:{task_id:taskId,run_id:runId,input_edit_version_id:editVersionId,version_content_hash:text(version.version_content_hash),route_policy_id:text(route.route_policy_id)}
    }}));
    const decisionId=requireUuid(routed.route_decision_id,"EDIT_RENDER_ROUTE_DECISION_REQUIRED");
    if(text(routed.status)!=="SUCCESS"||routed.external_request_sent!==true)throw new NamedRuntimeError("EDIT_RENDER_PROVIDER_EXECUTION_NOT_SUCCESS");
    const d=first(await sql`SELECT provider_id,model_id,payload FROM acpos_runtime.provider_route_decisions WHERE id=${decisionId} LIMIT 1`);
    const dp=obj(d?.payload),uri=text(dp?.normalized_result),checksum=text(dp?.result_hash);
    if(!uri||!/^(https?|s3|gs):\/\//i.test(uri)||!checksum)throw new NamedRuntimeError("EDIT_RENDER_OUTPUT_MATERIALIZATION_REQUIRED");
    const manifest={run_id:runId,input_edit_version_id:editVersionId,version_content_hash:text(version.version_content_hash),source_video_output_version_id:text(version.source_video_output_version_id),route_policy_id:text(route.route_policy_id),route_decision_id:decisionId,provider_id:text(d?.provider_id),model_id:text(d?.model_id),settings_hash:settingsHash};
    await runRlsActorQuery(sql,session_token_hash,sql`
      UPDATE public.edit_render_jobs SET status='COMPLETED',route_decision_id=${decisionId},output_uri=${uri},artifact_checksum=${checksum}::char(64),
        manifest=${JSON.stringify(manifest)}::jsonb,completed_at=now(),updated_at=now()
      WHERE edit_render_job_id=${jobId}::uuid RETURNING edit_render_job_id
    `);
    return{render_job_id:jobId,status:"COMPLETED",output_uri:uri,artifact_checksum:checksum,manifest};
  }catch(error){
    const reason=namedReason(error,"EDIT_RENDER_PROVIDER_EXECUTION_FAILED");
    await runRlsActorQuery(sql,session_token_hash,sql`UPDATE public.edit_render_jobs SET status='BLOCKED',failure_reason=${reason},completed_at=now(),updated_at=now() WHERE edit_render_job_id=${jobId}::uuid RETURNING edit_render_job_id`).catch(()=>[]);
    throw new NamedRuntimeError(reason);
  }
}
async function cancelRender(request:EditVoiceRequest){
  const runId=requireUuid(request.path_params.runId,"EDIT_RUNTIME_RUN_ID_REQUIRED"),jobId=requireUuid(request.path_params.renderJobId,"EDIT_RENDER_JOB_ID_REQUIRED");
  const {sql,session_token_hash}=await context();const row=first(await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE public.edit_render_jobs SET status='CANCELLED',cancelled_at=now(),updated_at=now()
    WHERE edit_render_job_id=${jobId}::uuid AND run_id=${runId} AND status IN('QUEUED','RUNNING')
    RETURNING edit_render_job_id::text,status
  `));if(!row)throw new NamedRuntimeError("EDIT_RENDER_CANCEL_STATE_CONFLICT");return row;
}
async function saveOutput(request:EditVoiceRequest){
  const runId=requireUuid(request.path_params.runId,"EDIT_RUNTIME_RUN_ID_REQUIRED"),jobId=requireUuid(request.path_params.renderJobId,"EDIT_RENDER_JOB_ID_REQUIRED");
  const {sql,session_token_hash}=await context();const run=await runRow(sql,session_token_hash,runId),taskId=requireUuid(run.task_id,"EDIT_TASK_ID_REQUIRED"),task=await exactTask(sql,session_token_hash,taskId);
  const job=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT edit_render_job_id::text,input_edit_version_id::text,output_uri,btrim(artifact_checksum::text) AS artifact_checksum,manifest,output_version_id::text,status
    FROM public.edit_render_jobs WHERE edit_render_job_id=${jobId}::uuid AND run_id=${runId} LIMIT 1
  `));if(!job||text(job.status)!=="COMPLETED"||!text(job.output_uri)||!text(job.artifact_checksum)||!obj(job.manifest))throw new NamedRuntimeError("EDIT_COMPLETED_RENDER_REQUIRED");
  if(text(job.output_version_id))return{output_version_id:text(job.output_version_id),render_job_id:jobId,idempotent_replay:true};
  const output=first(await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.task_outputs(task_id,production_goal_id,output_contract_hash,output_uri,artifact_checksum,provenance,status,immutable_at,production_contract_id,goal_id,blueprint_version_id,topic_id,project_id)
    VALUES(${taskId}::uuid,${text(task.production_goal_id)}::uuid,${text(task.output_contract_hash)}::char(64),${text(job.output_uri)},${text(job.artifact_checksum)}::char(64),
      ${JSON.stringify({source:"ACPOS_EDIT_RENDER",render_job_id:jobId,input_edit_version_id:text(job.input_edit_version_id),manifest:job.manifest})}::jsonb,
      'ACCEPTED',now(),${uuid(task.production_contract_id)}::uuid,${uuid(task.goal_id)??uuid(task.production_goal_id)}::uuid,${uuid(task.blueprint_version_id)}::uuid,${uuid(task.topic_id)}::uuid,${uuid(task.project_id)}::uuid)
    ON CONFLICT(task_id,artifact_checksum) DO NOTHING
    RETURNING output_version_id::text
  `))??first(await runRlsActorQuery(sql,session_token_hash,sql`SELECT output_version_id::text FROM public.task_outputs WHERE task_id=${taskId}::uuid AND btrim(artifact_checksum::text)=${text(job.artifact_checksum)} LIMIT 1`));
  const outputId=requireUuid(output?.output_version_id,"EDIT_OUTPUT_PERSIST_FAILED");
  await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE public.edit_render_jobs SET output_version_id=${outputId}::uuid,updated_at=now() WHERE edit_render_job_id=${jobId}::uuid RETURNING edit_render_job_id
  `);
  await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE acpos_runtime.editing_runtime_runs_runtime SET current_output_version_id=${outputId},status='OUTPUT_READY',updated_at=now() WHERE id=${runId} RETURNING id
  `);
  return{output_version_id:outputId,render_job_id:jobId,manifest:job.manifest,artifact_checksum:text(job.artifact_checksum)};
}
async function lockVersion(request:EditVoiceRequest){
  const runId=requireUuid(request.path_params.runId,"EDIT_RUNTIME_RUN_ID_REQUIRED"),versionId=requireUuid(request.path_params.editVersionId,"EDIT_VERSION_ID_REQUIRED"),p=rec(request.payload);
  const outputId=requireUuid(p.output_version_id,"EDIT_OUTPUT_VERSION_ID_REQUIRED"),reason=text(p.reason)??"EDIT-01-ACT-VERSION-LOCK";
  const {sql,actor_user_id,session_token_hash}=await context();const run=await runRow(sql,session_token_hash,runId),taskId=requireUuid(run.task_id,"EDIT_TASK_ID_REQUIRED");
  if(text(run.current_state)!=="FINALIZE"||text(run.status)!=="OUTPUT_READY"||text(run.timeline_version_id)!==versionId||text(run.current_output_version_id)!==outputId)throw new NamedRuntimeError("EDIT_OUTPUT_READY_EXACT_VERSION_REQUIRED");
  const exact=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT v.editing_timeline_id::text,v.source_scorecard_id::text,v.version_content_hash::text,o.output_version_id::text,btrim(o.artifact_checksum::text) AS artifact_checksum,btrim(o.output_contract_hash::text) AS output_contract_hash,
           j.edit_render_job_id::text,j.manifest
    FROM public.editing_timelines v JOIN public.edit_render_jobs j ON j.input_edit_version_id=v.editing_timeline_id AND j.output_version_id=${outputId}::uuid AND j.status='COMPLETED'
    JOIN public.task_outputs o ON o.output_version_id=j.output_version_id AND o.task_id=v.task_id AND o.status='ACCEPTED' AND o.immutable_at IS NOT NULL
    WHERE v.editing_timeline_id=${versionId}::uuid AND v.task_id=${taskId}::uuid AND v.status='APPROVED' AND v.saved_at IS NOT NULL LIMIT 1
  `));if(!exact||!obj(exact.manifest))throw new NamedRuntimeError("EDIT_VERSION_OUTPUT_MANIFEST_BINDING_REQUIRED");
  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`SELECT production_output_version_lock_id::text AS lock_id FROM public.production_output_version_locks WHERE edit_version_id=${versionId}::uuid AND output_version_id=${outputId}::uuid AND task_id=${taskId}::uuid AND department='EDITING' AND status='LOCKED' LIMIT 1`));
  if(existing)return{locked_version_ref:text(existing.lock_id),edit_version_id:versionId,output_version_id:outputId,already_locked:true};
  const lockId=randomUUID();
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.production_output_version_locks(production_output_version_lock_id,output_version_id,task_id,department,scorecard_id,artifact_checksum,output_contract_hash,manifest_hash,locked_by,status,edit_version_id,render_job_id,reason)
    VALUES(${lockId}::uuid,${outputId}::uuid,${taskId}::uuid,'EDITING',${text(exact.source_scorecard_id)}::uuid,${text(exact.artifact_checksum)}::char(64),${text(exact.output_contract_hash)}::char(64),${sha(JSON.stringify(exact.manifest))}::char(64),${actor_user_id}::uuid,'LOCKED',${versionId}::uuid,${text(exact.edit_render_job_id)}::uuid,${reason})
  `);
  await runRlsActorQuery(sql,session_token_hash,sql`UPDATE acpos_runtime.editing_runtime_runs_runtime SET status='LOCKED',updated_at=now() WHERE id=${runId} RETURNING id`);
  return{locked_version_ref:lockId,edit_version_id:versionId,output_version_id:outputId,already_locked:false};
}
async function restoreVersion(request:EditVoiceRequest){
  const runId=requireUuid(request.path_params.runId,"EDIT_RUNTIME_RUN_ID_REQUIRED"),versionId=requireUuid(request.path_params.editVersionId,"EDIT_VERSION_ID_REQUIRED");
  const {sql,session_token_hash}=await context();const run=await runRow(sql,session_token_hash,runId),taskId=requireUuid(run.task_id,"EDIT_TASK_ID_REQUIRED");
  const source=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT editing_timeline_id::text,timeline_document,btrim(timing_hash::text) AS timing_hash,source_video_output_version_id::text
    FROM public.editing_timelines WHERE editing_timeline_id=${versionId}::uuid AND task_id=${taskId}::uuid AND status='APPROVED' LIMIT 1
  `));if(!source)throw new NamedRuntimeError("EDIT_SAVED_VERSION_REQUIRED");
  const next=first(await runRlsActorQuery(sql,session_token_hash,sql`SELECT COALESCE(max(timeline_version),0)+1 AS n FROM public.editing_timelines WHERE task_id=${taskId}::uuid`));
  const n=Number(next?.n);if(!Number.isSafeInteger(n)||n<1)throw new NamedRuntimeError("EDIT_VERSION_NUMBER_INVALID");
  const draftId=randomUUID();
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.editing_timelines(editing_timeline_id,task_id,timeline_version,source_video_output_version_id,timeline_document,timing_hash,status,source_timeline_id)
    VALUES(${draftId}::uuid,${taskId}::uuid,${n},${text(source.source_video_output_version_id)}::uuid,${JSON.stringify(source.timeline_document)}::jsonb,${text(source.timing_hash)}::char(64),'DRAFT',${versionId}::uuid)
  `);
  await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE acpos_runtime.editing_runtime_runs_runtime SET timeline_version_id=${draftId},current_state='FINALIZE',status='EVAL_REQUIRED',current_output_version_id=NULL,updated_at=now()
    WHERE id=${runId} RETURNING id
  `);
  return{working_draft_ref:draftId,source_edit_version_id:versionId,state:"EVAL_REQUIRED"};
}
async function download(request:EditVoiceRequest){
  const runId=requireUuid(request.path_params.runId,"EDIT_RUNTIME_RUN_ID_REQUIRED"),outputId=requireUuid(request.path_params.outputVersionId,"EDIT_OUTPUT_VERSION_ID_REQUIRED");
  const {sql,session_token_hash}=await context();const run=await runRow(sql,session_token_hash,runId),taskId=requireUuid(run.task_id,"EDIT_TASK_ID_REQUIRED");
  const row=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT o.output_version_id::text,o.output_uri,btrim(o.artifact_checksum::text) AS artifact_checksum,j.manifest
    FROM public.task_outputs o JOIN public.edit_render_jobs j ON j.output_version_id=o.output_version_id AND j.run_id=${runId} AND j.status='COMPLETED'
    WHERE o.output_version_id=${outputId}::uuid AND o.task_id=${taskId}::uuid AND o.status='ACCEPTED' AND o.immutable_at IS NOT NULL LIMIT 1
  `));if(!row)throw new NamedRuntimeError("EDIT_OUTPUT_REFERENCE_NOT_FOUND");
  return{output_version_id:outputId,download_ref:text(row.output_uri),artifact_checksum:text(row.artifact_checksum),manifest:row.manifest};
}
export async function executeProductionEditFinalizeOperation(request:EditVoiceRequest){
  switch(request.operation_id){
    case"saveEditVersion":return saveVersion(request);
    case"startEditRender":return startRender(request);
    case"cancelEditRender":return cancelRender(request);
    case"saveEditOutputVersion":return saveOutput(request);
    case"lockEditVersion":return lockVersion(request);
    case"restoreEditVersionAsDraft":return restoreVersion(request);
    case"getEditOutputDownload":return download(request);
    default:throw new NamedRuntimeError("EDIT_FINALIZE_OPERATION_NOT_MATERIALIZED");
  }
}
