import { createControlledTestMetadata, createControlledTestRef, isControlledTestMode } from "@/domain/testing/controlledTestData";
import type { AssetClientState } from "./assetClientState";
import type { AssetNormalizedProjection, AssetProjectionCandidateVersion } from "./assetProjectionPort";
import type { AssetInvokeInput, AssetInvokeResult } from "./assetClientPort";
import type { AssetActionUid } from "./assetRuntimeContract";

let lastProjection:AssetNormalizedProjection|null=null;
let correctionCandidateRef:string|null=null;
let approvedCorrectionRef:string|null=null;

export function isControlledAssetClientTestMode(){return isControlledTestMode();}
export function rememberControlledAssetProjection(p:AssetNormalizedProjection|null){if(p)lastProjection=p;}
function meta(){return createControlledTestMetadata("ASSET-01");}
function exactProjection(input:{projection:AssetNormalizedProjection|null}){const p=input.projection??lastProjection;if(!p)throw new Error("ASSET_TEST_PROJECTION_REQUIRED");return p;}
function clone(p:AssetNormalizedProjection):AssetNormalizedProjection{return{...p,values:{...p.values},lists:Object.fromEntries(Object.entries(p.lists).map(([k,v])=>[k,[...v]])),filters:Object.fromEntries(Object.entries(p.filters).map(([k,v])=>[k,[...v]])),gate_state:{...p.gate_state},candidate_versions:p.candidate_versions.map(v=>({...v}))};}

export function buildControlledAssetRequest(input:{action_uid:AssetActionUid;control_uid:string;control_value?:unknown;state:Readonly<AssetClientState>;projection:AssetNormalizedProjection|null;correction_request:string}){
 const p=exactProjection(input),taskId=p.task_id,outputVersionId=p.output_version_id,layerDocumentId=p.layer_document_id,layerId=p.layer_id,patchId=p.patch_id;
 const common={test_metadata:meta(),project_ref:input.state.project_ref,topic_ref:input.state.topic_ref,asset_ref:input.state.asset_ref};
 switch(input.action_uid){
  case"ASSET-01-ACT-FLOW-START":case"ASSET-01-ACT-TASK-RETRY":if(!taskId)throw new Error("TASK_ID_REQUIRED");return{path_params:{taskId},payload:{...common,mode:input.state.mode}};
  case"ASSET-01-ACT-CANDIDATE-CONFIRM":if(!taskId||!outputVersionId)throw new Error("OUTPUT_VERSION_REQUIRED");return{path_params:{taskId,outputVersionId},payload:{...common,decision:"CONFIRM"}};
  case"ASSET-01-ACT-FINDING-CREATE":return{payload:{...common,target_output_version_id:outputVersionId,issue_summary:"TEST_ONLY finding"}};
  case"ASSET-01-ACT-HANDOFF":if(!outputVersionId)throw new Error("OUTPUT_VERSION_REQUIRED");return{payload:{...common,locked_version_ref:p.values["ASSET-01-TEST-LOCK-REF"],asset_version_id:outputVersionId,blueprint_ref:p.values["ASSET-01-FLD-HANDOFF-BLUEPRINT"],script_hash:p.values["ASSET-01-FLD-HANDOFF-SCRIPT-HASH"],dna_ref:p.values["ASSET-01-FLD-HANDOFF-DNA"],manifest_ref:p.values["ASSET-01-FLD-HANDOFF-MANIFEST-ITEMS"],canonical_filename:p.values["ASSET-01-FLD-HANDOFF-CANONICAL-FILENAME"],checksum:p.values["ASSET-01-FLD-HANDOFF-CHECKSUM"],scorecard_ref:p.values["ASSET-01-FLD-HANDOFF-SCORECARD"],rights_ref:p.values["ASSET-01-FLD-HANDOFF-RIGHTS"],contract_hash:p.values["ASSET-01-FLD-HANDOFF-CONTRACT-HASH"]}};
  case"ASSET-01-ACT-LAYER-DOC-CREATE":if(!outputVersionId)throw new Error("OUTPUT_VERSION_REQUIRED");return{payload:{...common,asset_version_id:outputVersionId}};
  case"ASSET-01-ACT-LAYER-DOC-UPDATE":if(!layerDocumentId)throw new Error("LAYER_DOCUMENT_REQUIRED");return{path_params:{layerDocumentId},payload:{...common,operation:"UPDATE_DOCUMENT"}};
  case"ASSET-01-ACT-LAYER-ADD":if(!layerDocumentId)throw new Error("LAYER_DOCUMENT_REQUIRED");return{path_params:{layerDocumentId},payload:{...common,layer_type:"CHARACTER_BODY"}};
  case"ASSET-01-ACT-LAYER-DELETE":case"ASSET-01-ACT-LAYER-DUPLICATE":case"ASSET-01-ACT-LAYER-REORDER":case"ASSET-01-ACT-LAYER-PROPERTIES":case"ASSET-01-ACT-LAYER-MASK":if(!layerDocumentId||!layerId)throw new Error("LAYER_REFERENCE_REQUIRED");return{path_params:{layerDocumentId,layerId},payload:{...common,value:input.control_value??null}};
  case"ASSET-01-ACT-PATCH-CREATE":if(!outputVersionId)throw new Error("OUTPUT_VERSION_REQUIRED");return{payload:{...common,source_asset_version_id:outputVersionId,layer_document_id:layerDocumentId,preserve_constraints:true}};
  case"ASSET-01-ACT-PATCH-PREVIEW":if(!patchId)throw new Error("PATCH_REQUIRED");return{path_params:{patchId},payload:{...common}};
  case"ASSET-01-ACT-PATCH-ACCEPT":case"ASSET-01-ACT-PATCH-REJECT":if(!patchId)throw new Error("PATCH_REQUIRED");return{path_params:{patchId},payload:{...common,decision:input.action_uid.endsWith("ACCEPT")?"ACCEPT":"REJECT"}};
  default:return{payload:common};
 }
}

export function prepareControlledAssetEvaluation(input:AssetInvokeInput){const p=lastProjection;if(!p?.task_id||!p.output_version_id)throw new Error("EVALUATION_CONTEXT_REQUIRED");return{test_metadata:meta(),target_output_version_id:p.output_version_id,criteria_version_id:p.values["ASSET-01-FLD-CRITERIA"],dimensions:[{dimension_uid:"identity",score:98},{dimension_uid:"continuity",score:97},{dimension_uid:"technical",score:99}],overall_score:98,hard_block:false,evidence_refs:[p.output_version_id]};}
export function prepareControlledCorrectionExecution(input:AssetInvokeInput){const p=lastProjection;if(!p?.task_id||!p.output_version_id||!approvedCorrectionRef)throw new Error("APPROVED_CORRECTION_REQUIRED");return{test_metadata:meta(),mode:"CORRECTION",source_asset_version_id:p.output_version_id,approved_candidate_ref:approvedCorrectionRef,translated_instruction_ref:createControlledTestRef("ASSET-CORRECTION-INSTRUCTION"),affected_scope:"CURRENT_ASSET_ONLY"};}

export async function controlledAssetSharedInvoke(operation_id:string,input:AssetInvokeInput):Promise<AssetInvokeResult>{
 if(!isControlledAssetClientTestMode())return{ok:false,error_uid:"ASSET-01-ERR-CONTEXT-001",reason_code:"ASSET_TEST_RUNTIME_DISABLED",correlation_id:"unresolved"};
 const correlation_id=createControlledTestRef("ASSET-SHARED-CORRELATION");
 if(operation_id==="generateCorrectionScriptCandidate"){correctionCandidateRef=createControlledTestRef("ASSET-CORRECTION-CANDIDATE");approvedCorrectionRef=null;return{ok:true,value:{candidate_ref:correctionCandidateRef,test_metadata:meta()},correlation_id};}
 if(operation_id==="approveCorrectionScriptCandidate"){if(!correctionCandidateRef)return{ok:false,error_uid:"ASSET-01-ERR-CORRECTION-001",reason_code:"CORRECTION_CANDIDATE_REQUIRED",correlation_id};approvedCorrectionRef=createControlledTestRef("ASSET-CORRECTION-APPROVED");return{ok:true,value:{approved_candidate_ref:approvedCorrectionRef,test_metadata:meta()},correlation_id};}
 const p=lastProjection;if(!p)return{ok:false,error_uid:"ASSET-01-ERR-CONTEXT-001",reason_code:"ASSET_TEST_PROJECTION_REQUIRED",correlation_id};
 if(operation_id==="restoreAssetVersionAsNewDraft"){
  if(!p.output_version_id)return{ok:false,error_uid:"ASSET-01-ERR-VERSION-001",reason_code:"ASSET_VERSION_REQUIRED",correlation_id};
  const next=clone(p),ref=createControlledTestRef("ASSET-RESTORED-VERSION");
  const current=p.candidate_versions[0];const candidate:AssetProjectionCandidateVersion={ref,label:"[TEST] Restored as new draft",uri:current?.uri??p.candidate_uri??"",media_kind:current?.media_kind??p.candidate_media_kind??"IMAGE"};
  next.output_version_id=ref;next.page_state="CANDIDATE_OUTPUT";next.candidate_uri=candidate.uri;next.candidate_media_kind=candidate.media_kind;next.candidate_versions=[candidate,...p.candidate_versions].slice(0,3);next.values["ASSET-01-FLD-OUTPUT-ID"]=ref;next.values["ASSET-01-FLD-TASK-STATUS"]="CANDIDATE_OUTPUT";next.gate_state["ASSET-01-GATE-CANDIDATE"]=true;next.gate_state["ASSET-01-GATE-EVALUATION"]=true;next.gate_state["ASSET-01-GATE-LOCK"]=false;rememberControlledAssetProjection(next);return{ok:true,value:{projection:next,restored_version_ref:ref,test_metadata:meta()},correlation_id};
 }
 if(operation_id==="lockAssetVersion"){
  if(p.page_state!=="CONFIRMED"||!p.output_version_id)return{ok:false,error_uid:"ASSET-01-ERR-VERSION-001",reason_code:"CONFIRMED_EXACT_VERSION_REQUIRED",correlation_id};
  const next=clone(p),lockRef=`TEST-ASSET-LOCK-${p.output_version_id}`;next.page_state="LOCKED";next.values["ASSET-01-FLD-TASK-STATUS"]="LOCKED";next.values["ASSET-01-TEST-LOCK-REF"]=lockRef;next.gate_state["ASSET-01-GATE-LOCK"]=false;next.gate_state["ASSET-01-GATE-HANDOFF"]=true;rememberControlledAssetProjection(next);return{ok:true,value:{projection:next,locked_version_ref:lockRef,test_metadata:meta()},correlation_id};
 }
 return{ok:false,error_uid:"ASSET-01-ERR-CONTEXT-001",reason_code:"CONTROLLED_SHARED_OPERATION_NOT_IMPLEMENTED",correlation_id};
}
