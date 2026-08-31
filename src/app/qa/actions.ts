"use server";
import{runQaAutoTopic}from"@/server/qa/qaAutoOrchestrator";
import{executeQaManualReview,type QaManualAction}from"@/server/qa/qaManualReviewRuntime";
import{ensureControlledQaAuxBindings,isControlledQaServerTestMode}from"@/server/testing/controlledQaTestRuntime";
export async function runQaAutoTopicServerAction(topic_ref:string){if(isControlledQaServerTestMode())ensureControlledQaAuxBindings();return runQaAutoTopic(topic_ref);}
export async function runQaManualReviewServerAction(operation_id:QaManualAction,manual_review_case_ref:string,payload?:unknown){if(isControlledQaServerTestMode())ensureControlledQaAuxBindings();return executeQaManualReview({operation_id,manual_review_case_ref,payload,correlation_id:crypto.randomUUID()});}
