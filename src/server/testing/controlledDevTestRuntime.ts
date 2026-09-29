import{isControlledTestMode}from"@/domain/testing/controlledTestData";
import type{DevGateUid,DevRuntimeState}from"@/domain/dev/devRuntimeContract";
import type{DevNormalizedProjection}from"@/domain/dev/devProjectionPort";

export const DEV_TEST_METADATA={data_classification:"TEST_ONLY",synthetic:true,test_dataset_id:"TEST-DEV-01",test_run_id:"TEST-RUN-DEV-CONTROLLED-01",created_for_validation:true,production_eligible:false}as const;

type ControlledState={run_status:DevRuntimeState|null;merge_preview:boolean;candidate_ready:boolean;campaign_ready:boolean;campaign_approved:boolean;dispatched:boolean;killed:boolean;};
const state:ControlledState={run_status:"STOPPED",merge_preview:false,candidate_ready:false,campaign_ready:false,campaign_approved:false,dispatched:false,killed:false};

export function isControlledDevServerTestMode(){return isControlledTestMode();}
function gates():Partial<Record<DevGateUid,boolean>>{return{
"DEV-01-GATE-PAGE":true,
"DEV-01-GATE-DISCOVERY-START":state.run_status!=="RUNNING"&&state.run_status!=="PAUSED",
"DEV-01-GATE-DISCOVERY-RUNNING":state.run_status==="RUNNING",
"DEV-01-GATE-DISCOVERY-PAUSED":state.run_status==="PAUSED",
"DEV-01-GATE-DIRECTORY-READ":true,
"DEV-01-GATE-MERGE":true,
"DEV-01-GATE-MERGE-CONFIRM":state.merge_preview,
"DEV-01-GATE-EXPORT":true,
"DEV-01-GATE-MESSAGE-WRITE":true,
"DEV-01-GATE-MESSAGE-REVIEW":state.candidate_ready,
"DEV-01-GATE-CAMPAIGN":true,
"DEV-01-GATE-CAMPAIGN-APPROVAL":state.campaign_ready,
"DEV-01-GATE-DELIVERY-READ":true,
"DEV-01-GATE-DISPATCH":state.campaign_approved&&!state.dispatched,
"DEV-01-GATE-KILL-SWITCH":state.dispatched&&!state.killed,
};}
export function readControlledDevTestProjection():DevNormalizedProjection{
return{page_state:"READY",authorized_scope:"TEST-ORG-SCOPE-001",run_status:state.run_status,values:{
"current_stage":"DISCOVERY",
"discovery_mode":"CONTINUOUS · TEST_ONLY",
"search_scope":"Taiwan B2B · TEST_ONLY",
"allowed_sources":"TEST-SOURCE-REGISTRY-001 / TEST-SOURCE-REGISTRY-002",
"discovery_job_ref":"TEST-DEV-DISCOVERY-JOB-001",
"company_ref":"TEST-DEV-COMPANY-001",
"merge_candidate_ref":"TEST-DEV-MERGE-001",
"message_candidate_ref":"TEST-DEV-MESSAGE-CANDIDATE-001",
"campaign_ref":"TEST-DEV-CAMPAIGN-001",
"delivery_ref":"TEST-DEV-DELIVERY-001",
"recipient_ref":"TEST-DEV-RECIPIENT-001",
"recipient_count":"1",
"delivery_to_count":"1",
"connector_health":"TEST_ONLY READY",
"suppression_state":"CLEAR · TEST_ONLY",
"audit_ref":"TEST-DEV-AUDIT-001",
},gate_state:gates(),test_metadata:DEV_TEST_METADATA};}
export function executeControlledDevAction(action_uid:string):DevNormalizedProjection|null{
if(!isControlledDevServerTestMode())return null;
switch(action_uid){
case"DEV-01-ACT-DISCOVERY-START":state.run_status="RUNNING";break;
case"DEV-01-ACT-DISCOVERY-PAUSE":if(state.run_status!=="RUNNING")return null;state.run_status="PAUSED";break;
case"DEV-01-ACT-DISCOVERY-RESUME":if(state.run_status!=="PAUSED")return null;state.run_status="RUNNING";break;
case"DEV-01-ACT-DISCOVERY-STOP":if(state.run_status!=="RUNNING")return null;state.run_status="STOPPED";break;
case"DEV-01-ACT-MERGE-PREVIEW":state.merge_preview=true;break;
case"DEV-01-ACT-MERGE":if(!state.merge_preview)return null;state.merge_preview=false;break;
case"DEV-01-ACT-CANDIDATE-CREATE":state.candidate_ready=true;break;
case"DEV-01-ACT-CANDIDATE-DECIDE":if(!state.candidate_ready)return null;state.candidate_ready=false;break;
case"DEV-01-ACT-CR-CREATE":if(!state.candidate_ready)return null;break;
case"DEV-01-ACT-CAMPAIGN-CREATE":state.campaign_ready=true;break;
case"DEV-01-ACT-CAMPAIGN-APPROVE":if(!state.campaign_ready)return null;state.campaign_ready=false;state.campaign_approved=true;break;
case"DEV-01-ACT-EMAIL-DISPATCH":if(!state.campaign_approved||state.dispatched)return null;state.dispatched=true;break;
case"DEV-01-ACT-KILL-SWITCH":if(!state.dispatched||state.killed)return null;state.killed=true;break;
case"DEV-01-ACT-DIRECTORY-SEARCH":case"DEV-01-ACT-EXPORT":case"DEV-01-ACT-CAMPAIGN-SEARCH":case"DEV-01-ACT-REFRESH":break;
default:return null;
}
return readControlledDevTestProjection();}
