import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { EDIT_CONTROL_BINDINGS } from "./editControlBindings";
import { configureEditActionInvoker, type EditActionInvokeInput } from "./editActionPort";
import { invokeEditIntegrationPort, type EditPortInvokeResult } from "./editClientPort";
import type { EditResolvedContext } from "./editClientState";

let lastProjection: EditResolvedContext | null = null;
let correctionCandidateRef: string | null = null;
let correctionApprovedRef: string | null = null;
let internalCounter = 0;

function ref(prefix:string){internalCounter+=1;return `TEST-${prefix}-${String(internalCounter).padStart(3,"0")}`;}
function meta(){return{data_classification:"TEST_ONLY",synthetic:true,test_dataset_id:"TEST-EDIT-01",test_run_id:"TEST-RUN-EDIT-01-CONTROLLED",created_for_validation:true,production_eligible:false};}
function cloneProjection(source:EditResolvedContext):EditResolvedContext{return{...source,values:{...source.values},lists:Object.fromEntries(Object.entries(source.lists).map(([key,items])=>[key,items.map(item=>({...item}))])),gate_state:{...source.gate_state}};}
function current(input:EditActionInvokeInput){return lastProjection??input.state.resolved;}
export function rememberControlledEditProjection(projection:EditResolvedContext|null){if(projection)lastProjection=projection;}
export function isControlledEditClientTestMode(){return isControlledTestMode();}
function ok(projection:EditResolvedContext,action_uid:string,value:Record<string,unknown>={}){lastProjection=projection;return{ok:true as const,value:{...value,projection,test_metadata:meta(),action_uid},correlation_id:ref("EDIT-CORRELATION")};}
function fail(reason_code:string,error_uid="EDIT-01-ERR-CONTEXT-001"){return{ok:false as const,error_uid,reason_code,correlation_id:ref("EDIT-CORRELATION")};}
function projectionFrom(value:unknown){if(!value||typeof value!=="object")return null;const p=(value as{projection?:unknown}).projection;return p&&typeof p==="object"?p as EditResolvedContext:null;}
async function invokePort(input:EditActionInvokeInput,port_uid:Parameters<typeof invokeEditIntegrationPort>[0]["port_uid"],path_params:Record<string,string>={},payload:Record<string,unknown>={}){
  const result:EditPortInvokeResult=await invokeEditIntegrationPort({port_uid,action_uid:input.action_uid,path_params,payload:{...payload,test_metadata:meta()}});
  if(!result.ok)return result;
  const p=projectionFrom(result.value);if(p)lastProjection=p;
  return result;
}
function stagePortScore(stage:string|null){return stage==="EDIT-01-STAGE-01-ASSEMBLY"?"EDIT-01-PORT-ASSEMBLY-SCORECARD" as const:"EDIT-01-PORT-VOICE-SCORECARD" as const;}
function setGate(next:EditResolvedContext,uid:string,value:boolean){next.gate_state={...next.gate_state,[uid]:value};}
function internalAction(input:EditActionInvokeInput){
  const base=current(input);if(!base)return fail("EDIT_TEST_PROJECTION_REQUIRED");const next=cloneProjection(base);const binding=Object.values(EDIT_CONTROL_BINDINGS).find(item=>item.action_uid===input.action_uid);if(!binding)return fail("CONTROLLED_EDIT_ACTION_UNREGISTERED");
  const effect=binding.effect_type;
  next.values={...next.values,"EDIT-01-TEST-LAST-ACTION":input.action_uid};
  if(input.action_uid==="EDIT-01-ACT-CORRECTION-CANDIDATE-GENERATE"){correctionCandidateRef=ref("EDIT-CORRECTION-CANDIDATE");correctionApprovedRef=null;next.values={...next.values,"EDIT-01-LBL-API-JOB":correctionCandidateRef,"EDIT-01-TEST-INTERNAL-CORRECTION-ACTION":"EDIT-01-ACT-CORRECTION-TRANSLATE"};return ok(next,input.action_uid,{candidate_ref:correctionCandidateRef,internal_action_uid:"EDIT-01-ACT-CORRECTION-TRANSLATE"});}
  if(input.action_uid==="EDIT-01-ACT-CORRECTION-CANDIDATE-APPROVE"){if(!correctionCandidateRef)return fail("CORRECTION_CANDIDATE_REQUIRED","EDIT-01-ERR-CORRECTION-001");correctionApprovedRef=ref("EDIT-CORRECTION-APPROVED");return ok(next,input.action_uid,{approved_candidate_ref:correctionApprovedRef});}
  if(input.action_uid==="EDIT-01-ACT-CORRECTION-EXECUTE"||input.action_uid==="EDIT-01-ACT-API-APPLY"){if(input.action_uid==="EDIT-01-ACT-CORRECTION-EXECUTE"&&!correctionApprovedRef)return fail("APPROVED_CORRECTION_REQUIRED","EDIT-01-ERR-CORRECTION-001");next.page_state_uid="EDIT-01-ST-PAGE-EVAL_REQUIRED";next.current_stage_phase="EVALUATING";setGate(next,"EDIT-01-GATE-EVALUATION",true);setGate(next,"EDIT-01-GATE-STAGE-PASS",false);return ok(next,input.action_uid,{working_draft_mutated:true});}
  if(input.action_uid==="EDIT-01-ACT-VERSION-SAVE"){if(next.page_state_uid!=="EDIT-01-ST-PAGE-EVAL_PASS")return fail("EVALUATION_PASS_REQUIRED","EDIT-01-ERR-VERSION-001");const version=ref("EDIT-VERSION");next.saved_edit_version_id=version;next.page_state_uid="EDIT-01-ST-PAGE-VERSION_SAVED";next.current_stage_uid="EDIT-01-STAGE-04-FINALIZE";next.current_stage_phase="READY";next.lists={...next.lists,"EDIT-01-LST-VERSION-HISTORY":[{ref:version,label:"[TEST] Immutable Edit Version"}]};setGate(next,"EDIT-01-GATE-VERSION",true);setGate(next,"EDIT-01-GATE-RENDER",true);return ok(next,input.action_uid,{edit_version_id:version});}
  if(input.action_uid==="EDIT-01-ACT-RENDER-START"){if(!next.saved_edit_version_id)return fail("SAVED_EDIT_VERSION_REQUIRED","EDIT-01-ERR-RENDER-001");const job=ref("EDIT-RENDER-JOB"),output=ref("EDIT-OUTPUT");next.page_state_uid="EDIT-01-ST-PAGE-OUTPUT_READY";next.output_version_id=output;next.final_preview_uri=output;next.values={...next.values,"EDIT-01-LBL-RENDER-JOB":`${job}:COMPLETED`};next.lists={...next.lists,"EDIT-01-LST-JOB-STATUS":[{ref:job,label:"COMPLETED"}]};setGate(next,"EDIT-01-GATE-RENDER",true);return ok(next,input.action_uid,{render_job_ref:job,output_version_id:output,provider_execution:"SIMULATED_EXTERNAL"});}
  if(input.action_uid==="EDIT-01-ACT-RENDER-CANCEL"){next.page_state_uid="EDIT-01-ST-PAGE-VERSION_SAVED";next.output_version_id=null;next.final_preview_uri=null;next.values={...next.values,"EDIT-01-LBL-RENDER-JOB":"CANCELLED"};return ok(next,input.action_uid,{cancelled:true});}
  if(input.action_uid==="EDIT-01-ACT-OUTPUT-VERSION-SAVE"){if(!next.output_version_id)return fail("OUTPUT_REFERENCE_REQUIRED","EDIT-01-ERR-RENDER-001");return ok(next,input.action_uid,{output_version_id:next.output_version_id,checksum:"TEST-EDIT-OUTPUT-CHECKSUM-001"});}
  if(input.action_uid==="EDIT-01-ACT-VERSION-LOCK"){if(next.page_state_uid!=="EDIT-01-ST-PAGE-OUTPUT_READY"||!next.saved_edit_version_id||!next.output_version_id)return fail("OUTPUT_READY_EXACT_VERSION_REQUIRED","EDIT-01-ERR-VERSION-001");next.page_state_uid="EDIT-01-ST-PAGE-LOCKED";next.current_stage_uid="EDIT-01-STAGE-05-QA-HANDOFF";next.current_stage_phase="READY";setGate(next,"EDIT-01-GATE-CONTEXT-MUTABLE",false);setGate(next,"EDIT-01-GATE-HANDOFF",true);return ok(next,input.action_uid,{locked_version_ref:`TEST-LOCK-${next.saved_edit_version_id}`});}
  if(input.action_uid==="EDIT-01-ACT-VERSION-RESTORE-AS-DRAFT"){const draft=ref("EDIT-WORKING-DRAFT");next.working_draft_ref=draft;next.page_state_uid="EDIT-01-ST-PAGE-EVAL_REQUIRED";next.current_stage_uid="EDIT-01-STAGE-04-FINALIZE";next.current_stage_phase="EVALUATING";setGate(next,"EDIT-01-GATE-CONTEXT-MUTABLE",true);setGate(next,"EDIT-01-GATE-EVALUATION",true);return ok(next,input.action_uid,{working_draft_ref:draft});}
  if(input.action_uid==="EDIT-01-ACT-OUTPUT-DOWNLOAD"){if(!next.output_version_id)return fail("OUTPUT_REFERENCE_REQUIRED","EDIT-01-ERR-RENDER-001");return ok(next,input.action_uid,{download_ref:`TEST-DOWNLOAD-${next.output_version_id}`});}
  if(effect==="JOB_START"){const job=ref("EDIT-INTERNAL-JOB");next.values={...next.values,"EDIT-01-LBL-API-JOB":job};return ok(next,input.action_uid,{job_ref:job});}
  if(effect==="JOB_CANCEL")return ok(next,input.action_uid,{cancelled:true});
  if(effect==="VERSION_CREATE"||effect==="VERSION_LOCK"||effect==="OUTPUT_CREATE"||effect==="READ_OUTPUT")return fail("CONTROLLED_EDIT_SPECIALIZED_ACTION_REQUIRED");
  return ok(next,input.action_uid,{effect_type:effect});
}

async function controlledInvoke(input:EditActionInvokeInput){
  if(!isControlledEditClientTestMode())return fail("EDIT_TEST_RUNTIME_DISABLED");const p=current(input);const stage=p.current_stage_uid;const taskId=p.task_id??"TEST-EDIT-TASK-001";const runId=p.editing_run_id??"TEST-EDIT-RUN-001";const voiceRunId=p.voice_run_id??"TEST-VOICE-RUN-001";const outputVersionId=p.output_version_id??"TEST-EDIT-STAGE-CANDIDATE-001";
  if(input.action_uid==="EDIT-01-ACT-FLOW-START-CONTINUE"){
    if(stage==="EDIT-01-STAGE-01-ASSEMBLY"){let r=await invokePort(input,"EDIT-01-PORT-EDIT-RUN-CREATE",{}, {task_id:taskId,input_fingerprint:p.input_fingerprint});if(!r.ok)return r;const q=projectionFrom(r.value);const exactRun=q?.editing_run_id??runId;return invokePort(input,"EDIT-01-PORT-ASSEMBLY-COMPLETE",{runId:exactRun},{working_draft_ref:q?.working_draft_ref});}
    if(stage==="EDIT-01-STAGE-02-AUDIO"){let r=await invokePort(input,"EDIT-01-PORT-EDIT-VOICE-HANDOFF",{runId},{task_id:taskId});if(!r.ok)return r;const q=projectionFrom(r.value);const exactVoice=q?.voice_run_id??voiceRunId;r=await invokePort(input,"EDIT-01-PORT-VOICE-RUNTIME-START",{runId:exactVoice},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});if(!r.ok)return r;return invokePort(input,"EDIT-01-PORT-AUDIO-MIX-COMPLETE",{runId:exactVoice},{mix_manifest_ref:"TEST-MIX-MANIFEST-001"});}
    if(stage==="EDIT-01-STAGE-03-SYNC"){let r=await invokePort(input,"EDIT-01-PORT-LIPSYNC-COMPLETE",{runId:voiceRunId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});if(!r.ok)return r;return invokePort(input,"EDIT-01-PORT-SUBTITLE-COMPLETE",{runId:voiceRunId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});}
    return internalAction(input);
  }
  if(input.action_uid==="EDIT-01-ACT-STAGE-CONFIRM")return invokePort(input,stage==="EDIT-01-STAGE-01-ASSEMBLY"?"EDIT-01-PORT-ASSEMBLY-DECISION":"EDIT-01-PORT-VOICE-DECISION",{taskId,outputVersionId},{decision:"CONFIRM"});
  if(input.action_uid==="EDIT-01-ACT-EVAL-RECHECK-FULL"||input.action_uid==="EDIT-01-ACT-EVAL-RECHECK-SELECTED")return invokePort(input,stagePortScore(stage),{}, {target_ref:p.working_draft_ref,criteria_ref:"TEST-EDIT-CRITERIA-001"});
  if(input.action_uid==="EDIT-01-ACT-RETURN-BLUEPRINT")return invokePort(input,"EDIT-01-PORT-IN-VIDEO-HANDOFF",{}, {direction:"RETURN_BLUEPRINT_CORRECTION",task_id:taskId});
  if(input.action_uid==="EDIT-01-ACT-VOICE-GENERATE")return invokePort(input,"EDIT-01-PORT-VOICE-RUNTIME-START",{runId:voiceRunId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});
  if(input.action_uid==="EDIT-01-ACT-MIX-EXECUTE")return invokePort(input,"EDIT-01-PORT-AUDIO-MIX-COMPLETE",{runId:voiceRunId},{mix_manifest_ref:"TEST-MIX-MANIFEST-001"});
  if(input.action_uid==="EDIT-01-ACT-LIPSYNC-EXECUTE")return invokePort(input,"EDIT-01-PORT-LIPSYNC-COMPLETE",{runId:voiceRunId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});
  if(input.action_uid==="EDIT-01-ACT-SUB-API-SYNC")return invokePort(input,"EDIT-01-PORT-SUBTITLE-COMPLETE",{runId:voiceRunId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});
  if(input.action_uid==="EDIT-01-ACT-HANDOFF")return invokePort(input,"EDIT-01-PORT-VOICE-QA-HANDOFF",{runId:voiceRunId},{task_id:taskId,saved_edit_version_id:p.saved_edit_version_id,output_version_id:p.output_version_id,locked_version_ref:p.values["EDIT-01-TEST-LOCK-REF"]??`TEST-LOCK-${p.saved_edit_version_id??"MISSING"}`});
  return internalAction(input);
}

let configured=false;
export function ensureControlledEditClientTestRuntime(){if(configured||!isControlledEditClientTestMode())return false;configureEditActionInvoker({invoke:controlledInvoke});configured=true;return true;}
