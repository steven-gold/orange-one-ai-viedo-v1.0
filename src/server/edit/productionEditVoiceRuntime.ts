import { randomUUID } from "node:crypto";
import { cookies } from "next/headers";
import { ensureProductionNeonRuntime,getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import { hashSessionToken,IDENTITY_COOKIE_NAME,resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { EditVoiceRequest } from "@/server/edit/editVoiceRuntime";
import { executeProductionEditFinalizeOperation } from "@/server/edit/productionEditFinalizeRuntime";

type Sql=NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row=Record<string,unknown>;
type RuntimeContext={sql:Sql;actor_user_id:string;session_token_hash:string};
function rec(v:unknown):Row{return v&&typeof v==="object"&&!Array.isArray(v)?v as Row:{};}
function rows(v:unknown):Row[]{return Array.isArray(v)?v.filter((x):x is Row=>Boolean(x)&&typeof x==="object"&&!Array.isArray(x)):[];}
function first(v:unknown):Row|null{return rows(v)[0]??null;}
function text(v:unknown):string|null{if(typeof v!=="string")return null;const x=v.trim();return x||null;}
function uuid(v:unknown):string|null{const x=text(v);return x&&/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(x)?x:null;}
function requireUuid(v:unknown,reason:string){const x=uuid(v);if(!x)throw new NamedRuntimeError(reason);return x;}
async function context():Promise<RuntimeContext>{
  await ensureProductionNeonRuntime();const sql=getProductionNeonSql();if(!sql)throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const token=(await cookies()).get(IDENTITY_COOKIE_NAME)?.value?.trim();if(!token)throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity=await resolveIdentityFromCookie(token);if(!identity.ok)throw new NamedRuntimeError(identity.reason_code);
  return{sql,actor_user_id:identity.actor.user_id,session_token_hash:hashSessionToken(token)};
}
const API_RESOURCE:Readonly<Record<EditVoiceRequest["operation_id"],string>>={
  createEditingRuntimeRun:"api:createEditingRuntimeRun",
  getEditingRuntimeRun:"api:getEditingRuntimeRun",
  completeAssembly:"api:completeAssembly",
  transitionEditingToVoiceStage:"api:transitionEditingToVoiceStage",
  startVoiceRuntime:"api:startVoiceRuntime",
  getVoiceRuntimeRun:"api:getVoiceRuntimeRun",
  completeAudioMix:"api:completeAudioMix",
  completeLipSync:"api:completeLipSync",
  completeSubtitle:"api:completeSubtitle",
  handoffVoiceToQA:"api:handoffVoiceToQA",
  saveEditVersion:"api:saveEditVersion",
  startEditRender:"api:startEditRender",
  cancelEditRender:"api:cancelEditRender",
  saveEditOutputVersion:"api:saveEditOutputVersion",
  lockEditVersion:"api:lockEditVersion",
  restoreEditVersionAsDraft:"api:restoreEditVersionAsDraft",
  getEditOutputDownload:"api:getEditOutputDownload",
};
const CONTROL_RESOURCE:Partial<Record<EditVoiceRequest["operation_id"],string>>={
  createEditingRuntimeRun:"control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-CREATE-EDITING-RUNTIME-RUN",
  getEditingRuntimeRun:"control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-GET-EDITING-RUNTIME-RUN",
  completeAssembly:"control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-COMPLETE-ASSEMBLY",
  transitionEditingToVoiceStage:"control:CTRL-WORKSPACE-EDIT-01-EDITING-RUNTIME-HANDOFF-EDITING-TO-VOICE",
  saveEditVersion:"control:workspace:EDIT-01:EDIT-01-BTN-VERSION-SAVE",
  startEditRender:"control:workspace:EDIT-01:EDIT-01-BTN-RENDER-EXECUTE",
  cancelEditRender:"control:workspace:EDIT-01:EDIT-01-BTN-RENDER-CANCEL",
  saveEditOutputVersion:"control:workspace:EDIT-01:EDIT-01-BTN-OUTPUT-SAVE",
  lockEditVersion:"control:workspace:EDIT-01:EDIT-01-BTN-VERSION-LOCK",
  restoreEditVersionAsDraft:"control:workspace:EDIT-01:EDIT-01-BTN-VERSION-RESTORE",
  getEditOutputDownload:"control:workspace:EDIT-01:EDIT-01-BTN-DOWNLOAD",
};
const ACTION_RESOURCE:Partial<Record<EditVoiceRequest["operation_id"],string>>={
  saveEditVersion:"action:workspace:EDIT-01:EDIT-01-ACT-VERSION-SAVE",
  startEditRender:"action:workspace:EDIT-01:EDIT-01-ACT-RENDER-START",
  cancelEditRender:"action:workspace:EDIT-01:EDIT-01-ACT-RENDER-CANCEL",
  saveEditOutputVersion:"action:workspace:EDIT-01:EDIT-01-ACT-OUTPUT-VERSION-SAVE",
  lockEditVersion:"action:workspace:EDIT-01:EDIT-01-ACT-VERSION-LOCK",
  restoreEditVersionAsDraft:"action:workspace:EDIT-01:EDIT-01-ACT-VERSION-RESTORE-AS-DRAFT",
  getEditOutputDownload:"action:workspace:EDIT-01:EDIT-01-ACT-OUTPUT-DOWNLOAD",
};
async function permissionEffects(ctx:RuntimeContext,resourceKey:string,action:string,resourceType:string){
  const result=await runRlsActorQuery(ctx.sql,ctx.session_token_hash,ctx.sql`
    SELECT a.effect
    FROM public.account_permission_assignments a
    JOIN public.permission_resources r ON r.resource_id=a.resource_id
    WHERE a.user_id=${ctx.actor_user_id}::uuid
      AND r.resource_key=${resourceKey} AND r.resource_type=${resourceType} AND r.active=true
      AND ${action}=ANY(SELECT jsonb_array_elements_text(CASE WHEN jsonb_typeof(r.allowed_actions)='array' THEN r.allowed_actions ELSE '[]'::jsonb END))
      AND a.action=${action} AND a.status='APPROVED' AND a.scope='{}'::jsonb AND a.condition='{}'::jsonb
      AND a.effective_from<=now() AND (a.effective_to IS NULL OR a.effective_to>now())
  `);
  return rows(result).map((r)=>text(r.effect)).filter((v):v is string=>Boolean(v));
}
async function allowed(ctx:RuntimeContext,resourceKey:string,action:string,resourceType:string){
  const effects=await permissionEffects(ctx,resourceKey,action,resourceType);
  return !effects.includes("DENY")&&effects.includes("ALLOW");
}
export async function authorizeProductionEditVoiceOperation(request:EditVoiceRequest):Promise<{allowed:true}|{allowed:false;reason_code:string}>{
  let ctx:RuntimeContext;try{ctx=await context();}catch(error){return{allowed:false,reason_code:error instanceof Error?error.message:"IDENTITY_RUNTIME_NOT_BOUND"};}
  if(!await allowed(ctx,"page:workspace:EDIT-01","VIEW","PAGE"))return{allowed:false,reason_code:"EDIT_PAGE_PERMISSION_DENIED"};
  const action=ACTION_RESOURCE[request.operation_id];
  if(action){
    if(!request.action_uid||request.action_uid!==action.split(":").slice(3).join(":"))return{allowed:false,reason_code:"EDIT_ACTION_UID_MISMATCH"};
    if(!await allowed(ctx,action,"INVOKE","ACTION"))return{allowed:false,reason_code:"EDIT_ACTION_PERMISSION_DENIED"};
  }
  const control=CONTROL_RESOURCE[request.operation_id];
  if(control&&!await allowed(ctx,control,"INVOKE","CONTROL"))return{allowed:false,reason_code:"EDIT_CONTROL_PERMISSION_DENIED"};
  const api=API_RESOURCE[request.operation_id];
  if(!api||!await allowed(ctx,api,"EXECUTE","API"))return{allowed:false,reason_code:"EDIT_API_PERMISSION_DENIED"};
  return{allowed:true};
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
  const nextState=stepName==="ASSEMBLY"?"ASSEMBLY":stepName==="AUDIO_MIX"?"LIP_SYNC":stepName==="LIP_SYNC"?"SUBTITLE":"FINALIZE";
  const nextStatus=stepName==="ASSEMBLY"?"ASSEMBLY_REVIEW_REQUIRED":stepName==="SUBTITLE"?"READY":"READY";
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
  const savedEditVersionId=requireUuid(payload.saved_edit_version_id,"EDIT_SAVED_VERSION_ID_REQUIRED");
  const lockedVersionRef=requireUuid(payload.locked_version_ref,"EDIT_LOCKED_VERSION_REF_REQUIRED");
  const {sql,session_token_hash}=await context();const run=await exactRun(sql,session_token_hash,runId);
  if(text(run.task_id)!==taskId||text(run.current_state)!=="FINALIZE"||text(run.status)!=="LOCKED")throw new NamedRuntimeError("EDIT_QA_HANDOFF_STATE_NOT_READY");
  const lock=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT l.production_output_version_lock_id::text AS lock_id,l.edit_version_id::text,l.output_version_id::text
    FROM public.production_output_version_locks l
    WHERE l.production_output_version_lock_id=${lockedVersionRef}::uuid
      AND l.edit_version_id=${savedEditVersionId}::uuid
      AND l.output_version_id=${outputId}::uuid
      AND l.task_id=${taskId}::uuid AND l.department='EDITING' AND l.status='LOCKED'
    LIMIT 1
  `));
  if(!lock)throw new NamedRuntimeError("EDIT_QA_HANDOFF_EXACT_VERSION_LOCK_REQUIRED");
  const source=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT t.project_id::text,t.topic_id::text,t.production_contract_id::text,t.topic_production_contract_id::text,
           COALESCE(t.goal_id,t.production_goal_id)::text AS goal_id,t.production_goal_id::text,
           btrim(t.output_contract_hash::text) AS output_contract_hash,
           o.output_version_id::text,o.status::text AS output_status,
           s.scorecard_id::text,s.gate_status::text AS gate_status
    FROM public.department_tasks t
    JOIN public.task_outputs o ON o.task_id=t.task_id AND o.output_version_id=${outputId}::uuid
    JOIN LATERAL(
      SELECT s0.scorecard_id,s0.gate_status FROM public.scorecards s0
      WHERE s0.task_id=t.task_id AND s0.output_version_id=o.output_version_id AND s0.gate_status='PASS'
      ORDER BY s0.created_at DESC,s0.scorecard_id DESC LIMIT 1
    ) s ON true
    WHERE t.task_id=${taskId}::uuid AND t.department::text='EDITING' LIMIT 1
  `));
  if(!source||text(source.output_status)!=="ACCEPTED"||text(source.gate_status)!=="PASS")throw new NamedRuntimeError("EDIT_QA_HANDOFF_CANONICAL_EVIDENCE_REQUIRED");
  const target=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT q.task_id::text FROM public.department_tasks q
    WHERE q.department::text='QA' AND q.project_id=${text(source.project_id)}::uuid AND q.topic_id=${text(source.topic_id)}::uuid AND q.status='READY'
    ORDER BY q.created_at DESC LIMIT 1
  `));
  const qaTaskId=requireUuid(target?.task_id,"EDIT_QA_TARGET_TASK_REQUIRED");
  const existing=first(await runRlsActorQuery(sql,session_token_hash,sql`
    SELECT handoff_id::text FROM public.handoffs WHERE source_task_id=${taskId}::uuid AND target_task_id=${qaTaskId}::uuid AND source_output_version_id=${outputId}::uuid AND status IN('HANDOFF_READY','HANDED_OFF') LIMIT 1
  `));
  if(existing)return{handoff_ref:text(existing.handoff_id),run_id:runId};
  const handoffId=randomUUID();
  await runRlsActorQuery(sql,session_token_hash,sql`
    INSERT INTO public.handoffs(
      handoff_id,source_task_id,target_task_id,source_output_version_id,scorecard_id,
      topic_production_contract_id,production_goal_id,output_contract_hash,status,
      production_contract_id,goal_id,topic_id,project_id
    ) VALUES(
      ${handoffId}::uuid,${taskId}::uuid,${qaTaskId}::uuid,${outputId}::uuid,${text(source.scorecard_id)}::uuid,
      ${text(source.topic_production_contract_id)}::uuid,${text(source.production_goal_id)}::uuid,${text(source.output_contract_hash)}::char(64),'HANDOFF_READY',
      ${uuid(source.production_contract_id)}::uuid,${uuid(source.goal_id)}::uuid,${uuid(source.topic_id)}::uuid,${uuid(source.project_id)}::uuid
    )
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
    case"saveEditVersion":
    case"startEditRender":
    case"cancelEditRender":
    case"saveEditOutputVersion":
    case"lockEditVersion":
    case"restoreEditVersionAsDraft":
    case"getEditOutputDownload":
      return executeProductionEditFinalizeOperation(request);
  }
}
export async function auditProductionEditVoiceOperation():Promise<void>{return;}
