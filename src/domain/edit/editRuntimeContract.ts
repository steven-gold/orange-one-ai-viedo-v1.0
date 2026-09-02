export const EDIT_INTEGRATION_PORT_UIDS = [
  "EDIT-01-PORT-IN-VIDEO-HANDOFF","EDIT-01-PORT-EDIT-RUN-CREATE","EDIT-01-PORT-EDIT-RUN-READ","EDIT-01-PORT-ASSEMBLY-COMPLETE",
  "EDIT-01-PORT-ASSEMBLY-DECISION","EDIT-01-PORT-ASSEMBLY-SCORECARD","EDIT-01-PORT-EDIT-VOICE-HANDOFF","EDIT-01-PORT-VOICE-RUNTIME-START",
  "EDIT-01-PORT-VOICE-RUNTIME-READ","EDIT-01-PORT-AUDIO-MIX-COMPLETE","EDIT-01-PORT-LIPSYNC-COMPLETE","EDIT-01-PORT-SUBTITLE-COMPLETE",
  "EDIT-01-PORT-VOICE-DECISION","EDIT-01-PORT-VOICE-SCORECARD","EDIT-01-PORT-VOICE-QA-HANDOFF"
] as const;
export type EditIntegrationPortUid = typeof EDIT_INTEGRATION_PORT_UIDS[number];

export const EDIT_GATE_UIDS = [
  "EDIT-01-GATE-SOURCE","EDIT-01-GATE-DRAFT","EDIT-01-GATE-AUDIO","EDIT-01-GATE-LIPSYNC","EDIT-01-GATE-SUBTITLE",
  "EDIT-01-GATE-EVALUATION","EDIT-01-GATE-VERSION","EDIT-01-GATE-RENDER","EDIT-01-GATE-HANDOFF","EDIT-01-GATE-CONTEXT-INTEGRITY",
  "EDIT-01-GATE-BINDING-INTEGRITY","EDIT-01-GATE-STAGE-PASS","EDIT-01-GATE-PROJECT-SOURCE-MUTATION","EDIT-01-GATE-DIALOGUE-SYNC",
  "EDIT-01-GATE-CONTEXT-MUTABLE","EDIT-01-GATE-PREVIEW","EDIT-01-GATE-TRACK-SELECTION","EDIT-01-GATE-CORRECTION",
  "EDIT-01-GATE-CORRECTION-CANDIDATE","EDIT-01-GATE-CORRECTION-TRANSLATED","EDIT-01-GATE-EVALUATION-RUN","EDIT-01-GATE-FINALIZE",
  "EDIT-01-GATE-BLUEPRINT-RETURN","EDIT-01-GATE-STANDALONE","EDIT-01-GATE-SYNC-POLICY"
] as const;
export type EditGateUid = typeof EDIT_GATE_UIDS[number];

export const EDIT_PERMISSION_UIDS = [
  "EDITING_USE","EDITING_VIEW","EDITING_UPLOAD","EDITING_EDIT","EDITING_API_EXECUTE","EDITING_VOICE_EXECUTE","EDITING_STAGE_EVALUATION","EDITING_RENDER","EDITING_HANDOFF"
] as const;
export type EditPermissionUid = typeof EDIT_PERMISSION_UIDS[number];

export const EDIT_ERROR_UIDS = [
  "EDIT-01-ERR-SOURCE-001","EDIT-01-ERR-UPLOAD-001","EDIT-01-ERR-MEDIA-001","EDIT-01-ERR-TIME-001","EDIT-01-ERR-TRACK-001",
  "EDIT-01-ERR-API-001","EDIT-01-ERR-API-002","EDIT-01-ERR-API-003","EDIT-01-ERR-VOICE-001","EDIT-01-ERR-MIX-001",
  "EDIT-01-ERR-LIPSYNC-001","EDIT-01-ERR-SUB-001","EDIT-01-ERR-EVALUATION-001","EDIT-01-ERR-VERSION-001","EDIT-01-ERR-RENDER-001",
  "EDIT-01-ERR-PERM-001","EDIT-01-ERR-BLUEPRINT-001","EDIT-01-ERR-PACKAGE-001","EDIT-01-ERR-SCRIPT-001","EDIT-01-ERR-ASSET-BINDING-001",
  "EDIT-01-ERR-FILENAME-001","EDIT-01-ERR-CHECKSUM-001","EDIT-01-ERR-STAGE-001","EDIT-01-ERR-BLUEPRINT-UPDATE-REQUIRED","EDIT-01-ERR-SYNC-BINDING-001",
  "EDIT-01-ERR-CORRECTION-001","EDIT-01-ERR-CORRECTION-002","EDIT-01-ERR-CORRECTION-003","EDIT-01-ERR-CORRECTION-004","EDIT-01-ERR-SCRIPTROLE-001",
  "EDIT-01-ERR-PLACEMENT-001","EDIT-01-ERR-SYNC-POLICY-001","EDIT-01-ERR-CONTEXT-001","EDIT-01-ERR-VOICE-PROFILE-001"
] as const;
export type EditErrorUid = typeof EDIT_ERROR_UIDS[number];

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
export const EDIT_EXPECTED_GATE_COUNT = EDIT_GATE_UIDS.length;
export const EDIT_EXPECTED_PERMISSION_COUNT = EDIT_PERMISSION_UIDS.length;
export const EDIT_EXPECTED_ERROR_COUNT = EDIT_ERROR_UIDS.length;
export type EditActionRequest={action_uid:string;correlation_id:string;source_mode:"PROJECT_TASK"|"STANDALONE_UPLOAD";context?:unknown;payload?:unknown};
export type EditActionResult={ok:true;value:unknown;correlation_id:string}|{ok:false;error_uid:string;reason_code:string;correlation_id:string};
