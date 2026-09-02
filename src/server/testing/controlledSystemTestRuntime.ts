import{isControlledTestMode}from"@/domain/testing/controlledTestData";
import type{SystemNormalizedProjection}from"@/domain/system/systemProjectionPort";
const TEST_METADATA={data_classification:"TEST_ONLY",synthetic:true,test_dataset_id:"TEST-SYS-01",test_run_id:"TEST-RUN-SYS-CONTROLLED-01",created_for_validation:true,production_eligible:false}as const;
export function isControlledSystemServerTestMode(){return isControlledTestMode();}
export function readControlledSystemTestProjection():SystemNormalizedProjection{
 return{page_state:"READY",system_change_id:"TEST-SYS-CHANGE-001",conversation_id:"TEST-SYS-CONVERSATION-001",thread_id:"TEST-SYS-THREAD-001",branch_id:"TEST-SYS-BRANCH-001",multi_ai_route_available:true,values:{current_system_version:"ACPOS_v1.0.x · TEST_ONLY",current_goal:"Validate SYS-01 controlled presentation",scope:"admin:SYS-01",candidate_ref:"—",context_snapshot_ref:"TEST-SYS-CONTEXT-SNAPSHOT-001",dependency_graph_ref:"TEST-SYS-DEPENDENCY-GRAPH-001",latest_context_fingerprint:"TEST-SHA256-SYS-CONTEXT-001"},test_metadata:TEST_METADATA};
}
