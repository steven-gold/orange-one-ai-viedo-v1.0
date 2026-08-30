export const EDIT_INTEGRATION_PORT_UIDS = [
  "EDIT-01-PORT-IN-VIDEO-HANDOFF","EDIT-01-PORT-EDIT-RUN-CREATE","EDIT-01-PORT-EDIT-RUN-READ","EDIT-01-PORT-ASSEMBLY-COMPLETE",
  "EDIT-01-PORT-ASSEMBLY-DECISION","EDIT-01-PORT-ASSEMBLY-SCORECARD","EDIT-01-PORT-EDIT-VOICE-HANDOFF","EDIT-01-PORT-VOICE-RUNTIME-START",
  "EDIT-01-PORT-VOICE-RUNTIME-READ","EDIT-01-PORT-AUDIO-MIX-COMPLETE","EDIT-01-PORT-LIPSYNC-COMPLETE","EDIT-01-PORT-SUBTITLE-COMPLETE",
  "EDIT-01-PORT-VOICE-DECISION","EDIT-01-PORT-VOICE-SCORECARD","EDIT-01-PORT-VOICE-QA-HANDOFF"
] as const;
export type EditIntegrationPortUid = typeof EDIT_INTEGRATION_PORT_UIDS[number];
export type EditVoiceOperationId =
  | "createEditingRuntimeRun" | "getEditingRuntimeRun" | "completeAssembly" | "transitionEditingToVoiceStage"
  | "startVoiceRuntime" | "getVoiceRuntimeRun" | "completeAudioMix" | "completeLipSync" | "completeSubtitle" | "handoffVoiceToQA";
export const EDIT_PORT_METHOD_PATH: Record<EditIntegrationPortUid,{operation:string;method:"GET"|"POST";path:string}> = {
  "EDIT-01-PORT-IN-VIDEO-HANDOFF":{operation:"createDepartmentHandoff",method:"POST",path:"/v1/handoffs"},
  "EDIT-01-PORT-EDIT-RUN-CREATE":{operation:"createEditingRuntimeRun",method:"POST",path:"/v1/editing-runtime-runs"},
  "EDIT-01-PORT-EDIT-RUN-READ":{operation:"getEditingRuntimeRun",method:"GET",path:"/v1/editing-runtime-runs/{runId}"},
  "EDIT-01-PORT-ASSEMBLY-COMPLETE":{operation:"completeAssembly",method:"POST",path:"/v1/editing-runtime-runs/{runId}/assembly"},
  "EDIT-01-PORT-ASSEMBLY-DECISION":{operation:"decideOutputCandidate",method:"POST",path:"/v1/tasks/{taskId}/outputs/{outputVersionId}/decision"},
  "EDIT-01-PORT-ASSEMBLY-SCORECARD":{operation:"submitScorecard",method:"POST",path:"/v1/scorecards"},
  "EDIT-01-PORT-EDIT-VOICE-HANDOFF":{operation:"transitionEditingToVoiceStage",method:"POST",path:"/v1/editing-runtime-runs/{runId}/voice-handoff"},
  "EDIT-01-PORT-VOICE-RUNTIME-START":{operation:"startVoiceRuntime",method:"POST",path:"/v1/voice-runtime-runs/{runId}/start"},
  "EDIT-01-PORT-VOICE-RUNTIME-READ":{operation:"getVoiceRuntimeRun",method:"GET",path:"/v1/voice-runtime-runs/{runId}"},
  "EDIT-01-PORT-AUDIO-MIX-COMPLETE":{operation:"completeAudioMix",method:"POST",path:"/v1/voice-runtime-runs/{runId}/audio-mix"},
  "EDIT-01-PORT-LIPSYNC-COMPLETE":{operation:"completeLipSync",method:"POST",path:"/v1/voice-runtime-runs/{runId}/lip-sync"},
  "EDIT-01-PORT-SUBTITLE-COMPLETE":{operation:"completeSubtitle",method:"POST",path:"/v1/voice-runtime-runs/{runId}/subtitle"},
  "EDIT-01-PORT-VOICE-DECISION":{operation:"decideOutputCandidate",method:"POST",path:"/v1/tasks/{taskId}/outputs/{outputVersionId}/decision"},
  "EDIT-01-PORT-VOICE-SCORECARD":{operation:"submitScorecard",method:"POST",path:"/v1/scorecards"},
  "EDIT-01-PORT-VOICE-QA-HANDOFF":{operation:"handoffVoiceToQA",method:"POST",path:"/v1/voice-runtime-runs/{runId}/qa-handoff"},
};
export const EDIT_INTEGRATION_PORT_COUNT = EDIT_INTEGRATION_PORT_UIDS.length;
export const EDIT_EXPECTED_ACTION_COUNT = 124;
export const EDIT_EXPECTED_CONTROL_COUNT = 160;
export type EditActionRequest={action_uid:string;correlation_id:string;source_mode:"PROJECT_TASK"|"STANDALONE_UPLOAD";context?:unknown;payload?:unknown};
export type EditActionResult={ok:true;value:unknown;correlation_id:string}|{ok:false;error_uid:string;reason_code:string;correlation_id:string};
