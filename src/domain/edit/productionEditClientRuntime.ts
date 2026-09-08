import type { EditActionInvokeInput, EditActionInvoker } from "./editActionPort";
import { invokeEditIntegrationPort } from "./editClientPort";
import type { EditIntegrationPortUid } from "./editRuntimeContract";

function fail(reason_code:string,error_uid="EDIT-01-ERR-CONTEXT-001"){
  return{ok:false as const,error_uid,reason_code,correlation_id:"unresolved"};
}
function firstRef(input:EditActionInvokeInput,key:string){return input.state.resolved.lists[key]?.[0]?.ref??null;}
async function port(input:EditActionInvokeInput,port_uid:EditIntegrationPortUid,path_params:Record<string,string>={},payload:Record<string,unknown>={}){
  return invokeEditIntegrationPort({port_uid,action_uid:input.action_uid,path_params,payload});
}
function exactRun(input:EditActionInvokeInput){return input.state.resolved.editing_run_id??input.state.resolved.voice_run_id;}
function exactTask(input:EditActionInvokeInput){return input.state.resolved.task_id;}
function exactOutput(input:EditActionInvokeInput){return input.state.resolved.output_version_id;}

export const productionEditActionInvoker:EditActionInvoker={
  async invoke(input){
    if(input.source_mode!=="PROJECT_TASK")return fail("EDIT_STANDALONE_PRODUCTION_RUNTIME_NOT_MATERIALIZED");
    const p=input.state.resolved,taskId=exactTask(input),runId=exactRun(input),outputId=exactOutput(input);
    const stage=p.current_stage_uid;

    if(input.action_uid==="EDIT-01-ACT-FLOW-START-CONTINUE"){
      if(stage==="EDIT-01-STAGE-01-ASSEMBLY"||(!stage&&taskId)){
        if(!taskId||!p.input_fingerprint)return fail("EDIT_EXACT_TASK_CONTEXT_REQUIRED");
        const subtitle_language=firstRef(input,"EDIT-01-FLD-SUB-LANG");
        const subtitle_format=firstRef(input,"EDIT-01-FLD-SUB-FORMAT");
        let result=await port(input,"EDIT-01-PORT-EDIT-RUN-CREATE",{}, {
          task_id:taskId,input_fingerprint:p.input_fingerprint,subtitle_language,subtitle_format,
        });
        if(!result.ok)return result;
        const value=result.value&&typeof result.value==="object"?result.value as Record<string,unknown>:{};
        const createdRun=typeof value.id==="string"?value.id:runId;
        if(!createdRun)return fail("EDIT_RUNTIME_RUN_ID_REQUIRED");
        if(!p.working_draft_ref)return fail("EDIT_WORKING_DRAFT_REF_REQUIRED");
        return port(input,"EDIT-01-PORT-ASSEMBLY-COMPLETE",{runId:createdRun},{working_draft_ref:p.working_draft_ref});
      }
      if(stage==="EDIT-01-STAGE-02-AUDIO"){
        if(!runId||!taskId)return fail("EDIT_RUNTIME_CONTEXT_REQUIRED");
        const transition=await port(input,"EDIT-01-PORT-EDIT-VOICE-HANDOFF",{runId},{task_id:taskId});
        if(!transition.ok)return transition;
        const value=transition.value&&typeof transition.value==="object"?transition.value as Record<string,unknown>:{};
        const voiceRunId=typeof value.voice_run_id==="string"?value.voice_run_id:runId;
        return port(input,"EDIT-01-PORT-VOICE-RUNTIME-START",{runId:voiceRunId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});
      }
      if(stage==="EDIT-01-STAGE-03-SYNC"){
        if(!runId||!p.dialogue_timing_binding_ref)return fail("EDIT_SYNC_CONTEXT_REQUIRED");
        const lip=await port(input,"EDIT-01-PORT-LIPSYNC-COMPLETE",{runId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});
        if(!lip.ok)return lip;
        return port(input,"EDIT-01-PORT-SUBTITLE-COMPLETE",{runId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});
      }
      return fail("EDIT_FLOW_STAGE_RUNTIME_NOT_MATERIALIZED");
    }

    if(input.action_uid==="EDIT-01-ACT-VOICE-GENERATE"){
      if(!runId)return fail("EDIT_VOICE_RUN_ID_REQUIRED");
      return port(input,"EDIT-01-PORT-VOICE-RUNTIME-START",{runId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});
    }
    if(input.action_uid==="EDIT-01-ACT-MIX-EXECUTE"){
      if(!runId)return fail("EDIT_VOICE_RUN_ID_REQUIRED");
      const mix_manifest_ref=p.values["EDIT-01-FLD-MIX-MANIFEST"]??null;
      if(!mix_manifest_ref||mix_manifest_ref==="—")return fail("EDIT_MIX_MANIFEST_REF_REQUIRED","EDIT-01-ERR-MIX-001");
      return port(input,"EDIT-01-PORT-AUDIO-MIX-COMPLETE",{runId},{mix_manifest_ref});
    }
    if(input.action_uid==="EDIT-01-ACT-LIPSYNC-EXECUTE"){
      if(!runId||!p.dialogue_timing_binding_ref)return fail("EDIT_LIPSYNC_CONTEXT_REQUIRED","EDIT-01-ERR-LIPSYNC-001");
      return port(input,"EDIT-01-PORT-LIPSYNC-COMPLETE",{runId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});
    }
    if(input.action_uid==="EDIT-01-ACT-SUB-API-SYNC"){
      if(!runId||!p.dialogue_timing_binding_ref)return fail("EDIT_SUBTITLE_SYNC_CONTEXT_REQUIRED","EDIT-01-ERR-SUB-001");
      return port(input,"EDIT-01-PORT-SUBTITLE-COMPLETE",{runId},{dialogue_timing_binding_ref:p.dialogue_timing_binding_ref});
    }
    if(input.action_uid==="EDIT-01-ACT-HANDOFF"){
      if(!runId||!taskId||!outputId||!p.saved_edit_version_id)return fail("EDIT_QA_HANDOFF_CONTEXT_REQUIRED","EDIT-01-ERR-HANDOFF-001");
      const locked_version_ref=p.values["EDIT-01-FLD-LOCKED-VERSION-REF"]??p.values["EDIT-01-LBL-LOCKED-VERSION"]??null;
      if(!locked_version_ref||locked_version_ref==="—")return fail("EDIT_LOCKED_VERSION_REF_REQUIRED","EDIT-01-ERR-VERSION-001");
      return port(input,"EDIT-01-PORT-VOICE-QA-HANDOFF",{runId},{task_id:taskId,saved_edit_version_id:p.saved_edit_version_id,output_version_id:outputId,locked_version_ref});
    }
    if(input.action_uid==="EDIT-01-ACT-EVAL-RECHECK-FULL"||input.action_uid==="EDIT-01-ACT-EVAL-RECHECK-SELECTED"){
      const target_ref=p.working_draft_ref??outputId;
      const criteria_ref=p.values["EDIT-01-FLD-CRITERIA-VERSION"]??null;
      if(!target_ref||!criteria_ref||criteria_ref==="—")return fail("EDIT_EVALUATION_CONTEXT_REQUIRED","EDIT-01-ERR-EVALUATION-001");
      const scorePort:EditIntegrationPortUid=stage==="EDIT-01-STAGE-01-ASSEMBLY"?"EDIT-01-PORT-ASSEMBLY-SCORECARD":"EDIT-01-PORT-VOICE-SCORECARD";
      return port(input,scorePort,{}, {target_ref,criteria_ref});
    }
    if(input.action_uid==="EDIT-01-ACT-STAGE-CONFIRM"){
      if(!taskId||!outputId)return fail("EDIT_DECISION_EXACT_OUTPUT_REQUIRED","EDIT-01-ERR-STAGE-001");
      const decisionPort:EditIntegrationPortUid=stage==="EDIT-01-STAGE-01-ASSEMBLY"?"EDIT-01-PORT-ASSEMBLY-DECISION":"EDIT-01-PORT-VOICE-DECISION";
      return port(input,decisionPort,{taskId,outputVersionId:outputId},{decision:"CONFIRM"});
    }
    return fail(`EDIT_ACTION_RUNTIME_NOT_MATERIALIZED:${input.action_uid}`);
  },
};
