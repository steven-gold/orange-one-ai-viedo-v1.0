import { randomUUID } from "node:crypto";
import { cookies } from "next/headers";
import { ensureProductionNeonRuntime,getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import { hashSessionToken,IDENTITY_COOKIE_NAME,resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { EditVoiceRequest } from "@/server/edit/editVoiceRuntime";

type Sql=NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row=Record<string,unknown>;
function rec(v:unknown):Row{return v&&typeof v==="object"&&!Array.isArray(v)?v as Row:{};}
function rows(v:unknown):Row[]{return Array.isArray(v)?v.filter((x):x is Row=>Boolean(x)&&typeof x==="object"&&!Array.isArray(x)):[];}
function first(v:unknown):Row|null{return rows(v)[0]??null;}
function text(v:unknown):string|null{if(typeof v!=="string")return null;const x=v.trim();return x||null;}
function uuid(v:unknown):string|null{const x=text(v);return x&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(x)?x:null;}
function requireUuid(v:unknown,reason:string){const x=uuid(v);if(!x)throw new NamedRuntimeError(reason);return x;}
async function context():Promise<{sql:Sql;actor_user_id:string;session_token_hash:string}>{
  await ensureProductionNeonRuntime();const sql=getProductionNeonSql();if(!sql)throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const token=(await cookies()).get(IDENTITY_COOKIE_NAME)?.value?.trim();if(!token)throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity=await resolveIdentityFromCookie(token);if(!identity.ok)throw new NamedRuntimeError(identity.reason_code);
  return{sql,actor_user_id:identity.actor.user_id,session_token_hash:hashSessionToken(token)};
}
async function exactRun(sql:Sql,session:string,runId:string){
  const row=first(await runRlsActorQuery(sql,session,sql`
    SELECT id,task_id,timeline_version_id,approved_video_output_version_ids_json,voice_runtime_profile_id,
           subtitle_language,subtitle_format,current_state,status,current_output_version_id,created_at::text,updated_at::text
    FROM acpos_runtime.editing_runtime_runs_runtime WHERE id=${runId} LIMIT 1
  `));
  if(!row)throw new NamedRuntimeError("EDIT_RUNTIME_RUN_NOT_FOUND");return row;
}
async function createRun(request:EditVoiceRequest){
  const payload=rec(request.payload),taskId=requireUuid(payload.task_id,"EDIT_TASK_ID_REQUIRED");
  const suppliedFingerprint=text(payload.input_fingerprint);if(!suppliedFingerprint)throw new NamedRuntimeError("EDIT_INPUT_FINGERPRINT_REQUIRED");
  const {sql,session_token_hash}=await context();
  const task=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT t.task_id::text,t.status::text,btrim(t.input_fingerprint::text) AS input_fingerprint,
           h.source_output_version_id::text AS source_video_output_version_id,
           tl.editing_timeline_id::text AS timeline_version_id,
           vp.id AS voice_runtime_profile_id
    FROM public.department_tasks t
    JOIN LATERAL(
      SELECT h0.source_output_version_id FROM public.handoffs h0
      JOIN public.task_outputs o0 ON o0.output_version_id=h0.source_output_version_id AND o0.status='ACCEPTED'
      WHERE h0.target_task_id=t.task_id AND h0.status IN('HANDOFF_READY','HANDED_OFF')
      ORDER BY h0.created_at DESC,h0.handoff_id DESC LIMIT 1
    ) h ON true
    JOIN LATERAL(
      SELECT tl0.editing_timeline_id FROM public.editing_timelines tl0
      WHERE tl0.task_id=t.task_id ORDER BY tl0.timeline_version DESC,tl0.created_at DESC LIMIT 1
    ) tl ON true
    JOIN LATERAL(
      SELECT vp0.id FROM acpos_runtime.voice_runtime_profiles_runtime vp0
      WHERE vp0.status='APPROVED' ORDER BY vp0.version_no DESC,vp0.created_at DESC LIMIT 1
    ) vp ON true
    WHERE t.task_id=${taskId}::uuid AND t.department::text='EDITING' LIMIT 1
  `));
  if(!task)throw new NamedRuntimeError("EDIT_EXACT_RUNTIME_INPUTS_NOT_READY");
  if(text(task.input_fingerprint)!==suppliedFingerprint)throw new NamedRuntimeError("EDIT_INPUT_FINGERPRINT_MISMATCH");
  const subtitleLanguage=text(payload.subtitle_language),subtitleFormat=text(payload.subtitle_format);
  if(!subtitleLanguage)throw new NamedRuntimeError("EDIT_SUBTITLE_LANGUAGE_REQUIRED");
  if(!subtitleFormat||!["SRT","VTT","ASS","BURN_IN"].includes(subtitleFormat))throw new NamedRuntimeError("EDIT_SUBTITLE_FORMAT_REQUIRED");
  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT id FROM acpos_runtime.editing_runtime_runs_runtime
    WHERE task_id=${taskId} AND status NOT IN('FAILED','SUPERSEDED') ORDER BY created_at DESC LIMIT 1
  `));
  if(existing)return exactRun(sql,session_token_hash,text(existing.id)??"");
  const runId=randomUUID();
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO acpos_runtime.editing_runtime_runs_runtime(
      id,task_id,timeline_version_id,approved_video_output_version_ids_json,voice_runtime_profile_id,
      subtitle_language,subtitle_format,current_state,status
    ) VALUES(
      ${runId},${taskId},${text(task.timeline_version_id)},${JSON.stringify([text(task.source_video_output_version_id)])}::jsonb,
      ${text(task.voice_runtime_profile_id)},${subtitleLanguage},${subtitleFormat},'ASSEMBLY','READY'
    )
  `);
  return exactRun(sql,session_token_hash,runId);
}
async function completeStep(request:EditVoiceRequest,stepNo:number,stepName:"ASSEMBLY"|"AUDIO_MIX"|"LIP_SYNC"|"SUBTITLE"){
  const runId=requireUuid(request.path_params?.runId,"EDIT_RUNTIME_RUN_ID_REQUIRED"),payload=rec(request.payload);
  const {sql,session_token_hash}=await context();const run=await exactRun(sql,session_token_hash,runId);
  const expectedState=stepName==="ASSEMBLY"?"ASSEMBLY":stepName==="AUDIO_MIX"?"AUDIO_MIX":stepName==="LIP_SYNC"?"LIP_SYNC":"SUBTITLE";
  if(text(run.current_state)!==expectedState)throw new NamedRuntimeError(`EDIT_${stepName}_STATE_CONFLICT`);
  const evidence=stepName==="ASSEMBLY"?text(payload.working_draft_ref):stepName==="AUDIO_MIX"?text(payload.mix_manifest_ref):text(payload.dialogue_timing_binding_ref);
  if(!evidence)throw new NamedRuntimeError(`EDIT_${stepName}_EVIDENCE_REQUIRED`);
  const nextState=stepName==="ASSEMBLY"?"ASSEMBLY":stepName==="AUDIO_MIX"?"LIP_SYNC":stepName==="LIP_SYNC"?"SUBTITLE":"QA_READY";
  const nextStatus=stepName==="ASSEMBLY"?"ASSEMBLY_REVIEW_REQUIRED":stepName==="SUBTITLE"?"QA_READY":"READY";
  const stepId=randomUUID(),outputRef=text(payload.output_version_id)??evidence;
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO acpos_runtime.editing_runtime_steps_runtime(
      id,run_id,step_no,step_name,from_state,to_state,evidence_ref,output_version_id,payload_json,status
    ) VALUES(${stepId},${runId},${stepNo},${stepName},${expectedState},${nextState},${evidence},${outputRef},${JSON.stringify(payload)}::jsonb,'COMPLETED')
    ON CONFLICT(run_id,step_name) DO NOTHING
  `);
  await runRlsActorQuery(sql,session_token_hash,sql`
    UPDATE acpos_runtime.editing_runtime_runs_runtime
    SET current_state=${nextState},status=${nextStatus},current_output_version_id=${outputRef},updated_at=now()
    WHERE id=${runId}
  `);
  return exactRun(sql,session_token_hash,runId);
}
async function transitionToVoice(request:EditVoiceRequest){
  const runId=requireUuid(request.path_params?.runId,"EDIT_RUNTIME_RUN_ID_REQUIRED");const {sql,session_token_hash}=await context();const run=await exactRun(sql,session_token_hash,runId);
  if(text(run.current_state)!=="ASSEMBLY"||text(run.status)!=="ASSEMBLY_REVIEW_REQUIRED")throw new NamedRuntimeError("EDIT_ASSEMBLY_REVIEW_REQUIRED");
  await runRlsActorQuery(sql,session_token_hash,sql`UPDATE acpos_runtime.editing_runtime_runs_runtime SET current_state='AUDIO_MIX',status='VOICE_READY',updated_at=now() WHERE id=${runId}`);
  return{...(await exactRun(sql,session_token_hash,runId)),voice_run_id:runId};
}
async function startVoice(request:EditVoiceRequest){
  const runId=requireUuid(request.path_params?.runId,"EDIT_VOICE_RUN_ID_REQUIRED");const {sql,session_token_hash}=await context();const run=await exactRun(sql,session_token_hash,runId);
  if(text(run.current_state)!=="AUDIO_MIX"||text(run.status)!=="VOICE_READY")throw new NamedRuntimeError("EDIT_VOICE_STAGE_NOT_READY");
  throw new NamedRuntimeError("EDIT_VOICE_PROVIDER_OPERATION_NOT_MATERIALIZED");
}
async function handoffToQa(request:EditVoiceRequest){
  const runId=requireUuid(request.path_params?.runId,"EDIT_VOICE_RUN_ID_REQUIRED"),payload=rec(request.payload);
  const taskId=requireUuid(payload.task_id,"EDIT_TASK_ID_REQUIRED"),outputId=requireUuid(payload.output_version_id,"EDIT_OUTPUT_VERSION_ID_REQUIRED");
  if(!text(payload.saved_edit_version_id)||!text(payload.locked_version_ref))throw new NamedRuntimeError("EDIT_LOCKED_OUTPUT_REQUIRED");
  const {sql,session_token_hash}=await context();const run=await exactRun(sql,session_token_hash,runId);
  if(text(run.task_id)!==taskId||text(run.current_state)!=="QA_READY"||text(run.status)!=="QA_READY")throw new NamedRuntimeError("EDIT_QA_HANDOFF_STATE_NOT_READY");
  const target=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT q.task_id::text FROM public.department_tasks q JOIN public.department_tasks e ON e.task_id=${taskId}::uuid
    WHERE q.department::text='QA' AND q.project_id=e.project_id AND q.topic_id=e.topic_id AND q.status='READY'
    ORDER BY q.created_at DESC LIMIT 1
  `));
  const qaTaskId=requireUuid(target?.task_id,"EDIT_QA_TARGET_TASK_REQUIRED");
  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT handoff_id::text FROM public.handoffs WHERE source_task_id=${taskId}::uuid AND target_task_id=${qaTaskId}::uuid AND source_output_version_id=${outputId}::uuid AND status IN('HANDOFF_READY','HANDED_OFF') LIMIT 1
  `));
  if(existing)return{handoff_ref:text(existing.handoff_id),run_id:runId};
  const handoffId=randomUUID();
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.handoffs(handoff_id,source_task_id,target_task_id,source_output_version_id,status)
    VALUES(${handoffId}::uuid,${taskId}::uuid,${qaTaskId}::uuid,${outputId}::uuid,'HANDOFF_READY')
  `);
  await runRlsActorQuery(sql,session_token_hash,sql`UPDATE acpos_runtime.editing_runtime_runs_runtime SET status='HANDED_OFF',updated_at=now() WHERE id=${runId}`);
  return{handoff_ref:handoffId,run_id:runId,target_task_id:qaTaskId};
}
export async function executeProductionEditVoiceOperation(request:EditVoiceRequest):Promise<unknown>{
  switch(request.operation_id){
    case"createEditingRuntimeRun":return createRun(request);
    case"getEditingRuntimeRun":{const runId=requireUuid(request.path_params?.runId,"EDIT_RUNTIME_RUN_ID_REQUIRED");const{sql,session_token_hash}=await context();return exactRun(sql,session_token_hash,runId);}
    case"completeAssembly":return completeStep(request,1,"ASSEMBLY");
    case"transitionEditingToVoiceStage":return transitionToVoice(request);
    case"startVoiceRuntime":return startVoice(request);
    case"getVoiceRuntimeRun":{const runId=requireUuid(request.path_params?.runId,"EDIT_VOICE_RUN_ID_REQUIRED");const{sql,session_token_hash}=await context();return exactRun(sql,session_token_hash,runId);}
    case"completeAudioMix":return completeStep(request,2,"AUDIO_MIX");
    case"completeLipSync":return completeStep(request,3,"LIP_SYNC");
    case"completeSubtitle":return completeStep(request,4,"SUBTITLE");
    case"handoffVoiceToQA":return handoffToQa(request);
  }
}
export async function auditProductionEditVoiceOperation():Promise<void>{return;}
