import { EDIT_CONTROL_BINDINGS } from "@/domain/edit/editControlBindings";
import type { EditResolvedContext, EditListItem } from "@/domain/edit/editClientState";
import type { EditVoiceRequest } from "@/server/edit/editVoiceRuntime";
import type { DepartmentOperationRequest } from "@/server/shared/departmentOperationRuntime";
import { isControlledTestMode } from "@/domain/testing/controlledTestData";

const TEST_METADATA = {
  data_classification:"TEST_ONLY",synthetic:true,test_dataset_id:"TEST-EDIT-01",test_run_id:"TEST-RUN-EDIT-01-CONTROLLED",created_for_validation:true,production_eligible:false,
} as const;
const PROJECT_ID="TEST-EDIT-PROJECT-001";
const TOPIC_ID="TEST-EDIT-TOPIC-001";
const TASK_ID="TEST-EDIT-TASK-001";
const BLUEPRINT_REF="TEST-LOCKED-BLUEPRINT-001";
const PACKAGE_REF="TEST-EDIT-PRODUCTION-PACKAGE-001";
const MANIFEST_REF="TEST-EDIT-INPUT-MANIFEST-001";
const INPUT_FINGERPRINT="TEST-EDIT-INPUT-FINGERPRINT-001";
const DIALOGUE_BINDING="TEST-DIALOGUE-TIMING-BINDING-001";

type StageUid="EDIT-01-STAGE-01-ASSEMBLY"|"EDIT-01-STAGE-02-AUDIO"|"EDIT-01-STAGE-03-SYNC"|"EDIT-01-STAGE-04-FINALIZE"|"EDIT-01-STAGE-05-QA-HANDOFF";
type State={page_state_uid:string;stage_uid:StageUid;stage_phase:string;stage_score:number|null;editing_run_id:string|null;voice_run_id:string|null;working_draft_ref:string|null;saved_edit_version_id:string|null;output_version_id:string|null;handoff_ref:string|null;job_ref:string|null;voice_started:boolean;audio_complete:boolean;lipsync_complete:boolean;subtitle_complete:boolean;};
const state:State={page_state_uid:"EDIT-01-ST-PAGE-SOURCE_READY",stage_uid:"EDIT-01-STAGE-01-ASSEMBLY",stage_phase:"READY",stage_score:null,editing_run_id:null,voice_run_id:null,working_draft_ref:null,saved_edit_version_id:null,output_version_id:null,handoff_ref:null,job_ref:null,voice_started:false,audio_complete:false,lipsync_complete:false,subtitle_complete:false};

function allGates(){
  const gates:Record<string,boolean>={};
  for(const binding of Object.values(EDIT_CONTROL_BINDINGS)) gates[binding.gate_uid]=true;
  const mutable=state.page_state_uid!=="EDIT-01-ST-PAGE-LOCKED"&&state.page_state_uid!=="EDIT-01-ST-PAGE-HANDED_OFF";
  const working=["EDIT-01-ST-PAGE-WORKING","EDIT-01-ST-PAGE-EVAL_REQUIRED","EDIT-01-ST-PAGE-EVAL_PASS","EDIT-01-ST-PAGE-VERSION_SAVED","EDIT-01-ST-PAGE-OUTPUT_READY"].includes(state.page_state_uid);
  gates["EDIT-01-GATE-CONTEXT-MUTABLE"]=mutable;
  gates["EDIT-01-GATE-SOURCE"]=true;
  gates["EDIT-01-GATE-CONTEXT-INTEGRITY"]=true;
  gates["EDIT-01-GATE-BINDING-INTEGRITY"]=true;
  gates["EDIT-01-GATE-STANDALONE"]=false;
  gates["EDIT-01-GATE-PREVIEW"]=Boolean(state.working_draft_ref||state.editing_run_id);
  gates["EDIT-01-GATE-DRAFT"]=working;
  gates["EDIT-01-GATE-TRACK-SELECTION"]=working;
  gates["EDIT-01-GATE-CORRECTION"]=state.page_state_uid==="EDIT-01-ST-PAGE-EVAL_REQUIRED"||state.page_state_uid==="EDIT-01-ST-PAGE-EVAL_PASS";
  gates["EDIT-01-GATE-EVALUATION"]=state.page_state_uid==="EDIT-01-ST-PAGE-EVAL_REQUIRED"||state.page_state_uid==="EDIT-01-ST-PAGE-EVAL_PASS";
  gates["EDIT-01-GATE-STAGE-PASS"]=state.page_state_uid==="EDIT-01-ST-PAGE-EVAL_PASS"&&state.stage_phase==="WAIT_CONFIRMATION";
  gates["EDIT-01-GATE-VERSION"]=Boolean(state.saved_edit_version_id);
  gates["EDIT-01-GATE-RENDER"]=Boolean(state.saved_edit_version_id)&&state.stage_uid==="EDIT-01-STAGE-04-FINALIZE";
  gates["EDIT-01-GATE-HANDOFF"]=state.page_state_uid==="EDIT-01-ST-PAGE-LOCKED"&&Boolean(state.output_version_id&&state.saved_edit_version_id);
  return gates;
}
function list(ref:string,label:string):EditListItem[]{return[{ref,label}]}
function values(){return{
  "EDIT-01-LBL-PENDING-TASK":TASK_ID,
  "EDIT-01-LBL-CURRENT-STAGE":state.stage_uid,
  "EDIT-01-LBL-STAGE-SCORE":state.stage_score===null?"—":String(state.stage_score),
  "EDIT-01-LBL-CURRENT-SCRIPT-SECTION":"TEST-CANONICAL-SCRIPT-SECTION-001",
  "EDIT-01-LBL-BINDING-FINGERPRINT":INPUT_FINGERPRINT,
  "EDIT-01-FLD-API-PROVIDER":state.editing_run_id?"SIMULATED_EXTERNAL":"—",
  "EDIT-01-FLD-API-MODEL":state.editing_run_id?"TEST_EDIT_MODEL":"—",
  "EDIT-01-LBL-API-JOB":state.job_ref??"—",
  "EDIT-01-FLD-VOICE-SCRIPT":"TEST-VOICE-SCRIPT-001",
  "EDIT-01-FLD-VOICE-ASSET":"TEST-VOICE-ASSET-LOCKED-001",
  "EDIT-01-FLD-VOICE-PROVIDER":state.voice_started?"SIMULATED_EXTERNAL":"—",
  "EDIT-01-FLD-VOICE-MODEL":state.voice_started?"TEST_VOICE_MODEL":"—",
  "EDIT-01-FLD-MUSIC-ASSET":"TEST-MUSIC-ASSET-LOCKED-001",
  "EDIT-01-FLD-SFX-ASSET":"TEST-SFX-ASSET-LOCKED-001",
  "EDIT-01-LBL-LIPSYNC-SYNC-BINDING":DIALOGUE_BINDING,
  "EDIT-01-LBL-SUB-SYNC-BINDING":DIALOGUE_BINDING,
  "EDIT-01-LBL-EVAL-SUMMARY":state.stage_score===null?"—":`PASS ${state.stage_score}`,
  "EDIT-01-LBL-RENDER-JOB":state.job_ref??"—",
  "EDIT-01-LBL-PAGE-STATE":state.page_state_uid,
  "EDIT-01-LBL-ERROR-STATE":"—",
  "EDIT-01-TEST-HANDOFF-REF":state.handoff_ref??"—",
};}
export function isControlledEditServerTestMode(){return isControlledTestMode();}
export function readControlledEditTestProjection():EditResolvedContext{return{
  project_id:PROJECT_ID,topic_id:TOPIC_ID,task_id:TASK_ID,locked_blueprint_ref:BLUEPRINT_REF,production_package_ref:PACKAGE_REF,input_manifest_ref:MANIFEST_REF,input_fingerprint:INPUT_FINGERPRINT,
  working_draft_ref:state.working_draft_ref,editing_run_id:state.editing_run_id,voice_run_id:state.voice_run_id,saved_edit_version_id:state.saved_edit_version_id,output_version_id:state.output_version_id,
  dialogue_timing_binding_ref:DIALOGUE_BINDING,page_state_uid:state.page_state_uid,current_stage_uid:state.stage_uid,current_stage_phase:state.stage_phase,current_stage_score:state.stage_score,current_error_uid:null,
  preview_uri:state.editing_run_id?"TEST-EDIT-PREVIEW-VIDEO-001":null,final_preview_uri:state.output_version_id?"TEST-EDIT-FINAL-OUTPUT-001":null,values:values(),
  lists:{
    "EDIT-01-LST-MEDIA":list("TEST-VIDEO-VERSION-LOCKED-001","[TEST] Locked VIDEO handoff input"),
    "EDIT-01-LST-IMPORT-QUEUE":[],"EDIT-01-LST-VOICE-TAKES":state.voice_started?list("TEST-VOICE-TAKE-001","[TEST] Voice Take 001"):[],
    "EDIT-01-LST-EVAL-ISSUES":state.stage_score!==null&&state.stage_score<95?list("TEST-EDIT-ISSUE-001","Continuity issue"):[],
    "EDIT-01-LST-VERSION-HISTORY":state.saved_edit_version_id?list(state.saved_edit_version_id,"[TEST] Immutable Edit Version"):[],
    "EDIT-01-LST-JOB-STATUS":state.job_ref?list(state.job_ref,state.stage_phase):[],
    "EDIT-01-FLD-PROJECT":list(PROJECT_ID,"[TEST] ORANGE ONE Project"),"EDIT-01-FLD-TOPIC":list(TOPIC_ID,"[TEST] Topic 001"),"EDIT-01-FLD-TASK":list(TASK_ID,"[TEST] EDIT Task 001"),
  },gate_state:allGates(),
};}

function ok(correlation_id:string,value:Record<string,unknown>={}){return{ok:true as const,value:{...value,projection:readControlledEditTestProjection(),test_metadata:TEST_METADATA},correlation_id};}
function fail(correlation_id:string,error_uid:string,reason_code:string,status=409){return{ok:false as const,status,error_uid,reason_code,correlation_id};}

export async function executeControlledEditVoiceTestOperation(request:EditVoiceRequest){
  if(!isControlledEditServerTestMode())return fail(request.correlation_id,"EDIT-01-ERR-CONTEXT-001","EDIT_TEST_RUNTIME_DISABLED",503);
  switch(request.operation_id){
    case"createEditingRuntimeRun":state.editing_run_id="TEST-EDIT-RUN-001";state.working_draft_ref="TEST-EDIT-WORKING-DRAFT-001";state.page_state_uid="EDIT-01-ST-PAGE-WORKING";state.stage_uid="EDIT-01-STAGE-01-ASSEMBLY";state.stage_phase="RUNNING";state.job_ref="TEST-EDIT-ASSEMBLY-JOB-001";return ok(request.correlation_id,{editing_run_id:state.editing_run_id});
    case"getEditingRuntimeRun":return ok(request.correlation_id,{editing_run_id:state.editing_run_id});
    case"completeAssembly":if(!state.editing_run_id)return fail(request.correlation_id,"EDIT-01-ERR-STAGE-001","EDITING_RUN_REQUIRED");state.page_state_uid="EDIT-01-ST-PAGE-EVAL_REQUIRED";state.stage_phase="EVALUATING";return ok(request.correlation_id,{assembly_completed:true});
    case"transitionEditingToVoiceStage":state.voice_run_id="TEST-VOICE-RUN-001";state.stage_uid="EDIT-01-STAGE-02-AUDIO";state.stage_phase="READY";state.page_state_uid="EDIT-01-ST-PAGE-WORKING";return ok(request.correlation_id,{voice_run_id:state.voice_run_id});
    case"startVoiceRuntime":if(!state.voice_run_id)state.voice_run_id="TEST-VOICE-RUN-001";state.voice_started=true;state.stage_uid="EDIT-01-STAGE-02-AUDIO";state.stage_phase="RUNNING";state.page_state_uid="EDIT-01-ST-PAGE-WORKING";state.job_ref="TEST-VOICE-JOB-001";return ok(request.correlation_id,{voice_run_id:state.voice_run_id,provider_execution:"SIMULATED_EXTERNAL"});
    case"getVoiceRuntimeRun":return ok(request.correlation_id,{voice_run_id:state.voice_run_id});
    case"completeAudioMix":if(!state.voice_run_id)return fail(request.correlation_id,"EDIT-01-ERR-MIX-001","VOICE_RUN_REQUIRED");state.audio_complete=true;state.page_state_uid="EDIT-01-ST-PAGE-EVAL_REQUIRED";state.stage_phase="EVALUATING";return ok(request.correlation_id,{audio_mix_completed:true});
    case"completeLipSync":if(!state.voice_run_id)return fail(request.correlation_id,"EDIT-01-ERR-LIPSYNC-001","VOICE_RUN_REQUIRED");state.lipsync_complete=true;state.stage_uid="EDIT-01-STAGE-03-SYNC";state.stage_phase="RUNNING";return ok(request.correlation_id,{lip_sync_completed:true});
    case"completeSubtitle":if(!state.lipsync_complete)return fail(request.correlation_id,"EDIT-01-ERR-SUB-001","LIPSYNC_REQUIRED");state.subtitle_complete=true;state.page_state_uid="EDIT-01-ST-PAGE-EVAL_REQUIRED";state.stage_phase="EVALUATING";return ok(request.correlation_id,{subtitle_completed:true});
    case"handoffVoiceToQA":{const payload=request.payload&&typeof request.payload==="object"?request.payload as Record<string,unknown>:{};const saved=typeof payload.saved_edit_version_id==="string"&&payload.saved_edit_version_id?payload.saved_edit_version_id:null;const output=typeof payload.output_version_id==="string"&&payload.output_version_id?payload.output_version_id:null;const locked=typeof payload.locked_version_ref==="string"&&payload.locked_version_ref?payload.locked_version_ref:null;if(!saved||!output||!locked)return fail(request.correlation_id,"EDIT-01-ERR-STAGE-001","LOCKED_OUTPUT_REQUIRED");state.saved_edit_version_id=saved;state.output_version_id=output;state.handoff_ref="TEST-EDIT-VOICE-QA-HANDOFF-001";state.page_state_uid="EDIT-01-ST-PAGE-HANDED_OFF";state.stage_uid="EDIT-01-STAGE-05-QA-HANDOFF";state.stage_phase="COMPLETED";return ok(request.correlation_id,{handoff_ref:state.handoff_ref,locked_version_ref:locked});}
  }
}

export async function executeControlledEditDepartmentOperation(request:DepartmentOperationRequest){
  if(!isControlledEditServerTestMode())return fail(request.correlation_id,"EDIT-01-ERR-CONTEXT-001","EDIT_TEST_RUNTIME_DISABLED",503);
  if(request.operation_id==="submitScorecard"){
    const score=state.stage_uid==="EDIT-01-STAGE-01-ASSEMBLY"?96:state.stage_uid==="EDIT-01-STAGE-02-AUDIO"?97:98;
    state.stage_score=score;state.page_state_uid="EDIT-01-ST-PAGE-EVAL_PASS";state.stage_phase="WAIT_CONFIRMATION";return ok(request.correlation_id,{scorecard_ref:`TEST-EDIT-SCORECARD-${score}`,overall_score:score,hard_block:false,internal_action_uid:"EDIT-01-ACT-STAGE-EVALUATE"});
  }
  if(request.operation_id==="decideOutputCandidate"){
    if(state.page_state_uid!=="EDIT-01-ST-PAGE-EVAL_PASS"||state.stage_phase!=="WAIT_CONFIRMATION")return fail(request.correlation_id,"EDIT-01-ERR-STAGE-001","STAGE_PASS_REQUIRED");
    if(state.stage_uid==="EDIT-01-STAGE-01-ASSEMBLY"){state.stage_uid="EDIT-01-STAGE-02-AUDIO";state.stage_phase="READY";state.page_state_uid="EDIT-01-ST-PAGE-WORKING";state.stage_score=null;}
    else if(state.stage_uid==="EDIT-01-STAGE-02-AUDIO"){state.stage_uid="EDIT-01-STAGE-03-SYNC";state.stage_phase="READY";state.page_state_uid="EDIT-01-ST-PAGE-WORKING";state.stage_score=null;}
    else if(state.stage_uid==="EDIT-01-STAGE-03-SYNC"){state.stage_uid="EDIT-01-STAGE-04-FINALIZE";state.stage_phase="READY";state.page_state_uid="EDIT-01-ST-PAGE-EVAL_PASS";state.stage_score=98;}
    return ok(request.correlation_id,{decision:"CONFIRM"});
  }
  if(request.operation_id==="createDepartmentHandoff")return ok(request.correlation_id,{accepted:true});
  return fail(request.correlation_id,"EDIT-01-ERR-CONTEXT-001","CONTROLLED_EDIT_DEPARTMENT_OPERATION_UNREGISTERED",400);
}

export function applyControlledEditInternalProjection(next:Partial<Pick<State,"page_state_uid"|"stage_uid"|"stage_phase"|"stage_score"|"saved_edit_version_id"|"output_version_id"|"job_ref">>){Object.assign(state,next);return readControlledEditTestProjection();}
