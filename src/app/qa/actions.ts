"use server";
import{runQaAutoTopic}from"@/server/qa/qaAutoOrchestrator";
import{executeQaManualReview,type QaManualAction}from"@/server/qa/qaManualReviewRuntime";
import{executeQaOperation}from"@/server/qa/qaRuntime";
import{ensureControlledQaAuxBindings,isControlledQaServerTestMode,readControlledQaTestProjection}from"@/server/testing/controlledQaTestRuntime";

export async function runQaAutoTopicServerAction(topic_ref:string){
 const controlled=isControlledQaServerTestMode();
 if(controlled)ensureControlledQaAuxBindings();
 const result=await runQaAutoTopic(topic_ref);
 if(!result.ok||!controlled)return result;
 return{...result,projection:readControlledQaTestProjection()};
}

export async function runQaManualReviewServerAction(operation_id:QaManualAction,manual_review_case_ref:string,payload?:unknown){
 const controlled=isControlledQaServerTestMode();
 if(controlled)ensureControlledQaAuxBindings();
 const result=await executeQaManualReview({operation_id,manual_review_case_ref,payload,correlation_id:crypto.randomUUID()});
 if(!result.ok||!controlled||operation_id!=="manualReview.pass")return result;
 const projection=result.value&&typeof result.value==="object"?((result.value as{projection?:unknown}).projection):undefined;
 if(!projection||typeof projection!=="object"||!(projection as{gate_state?:Record<string,boolean>}).gate_state?.["QA-01-GATE-PASS"])return result;
 return executeQaOperation({operation_id:"decidePass",correlation_id:crypto.randomUUID(),path_params:{},payload:{manual_review_case_ref,system_re_evaluation:true}});
}
