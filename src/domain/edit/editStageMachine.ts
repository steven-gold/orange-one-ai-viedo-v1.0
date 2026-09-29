export const EDIT_STAGE_UIDS=["EDIT-01-STAGE-01-ASSEMBLY","EDIT-01-STAGE-02-AUDIO","EDIT-01-STAGE-03-SYNC","EDIT-01-STAGE-04-FINALIZE","EDIT-01-STAGE-05-QA-HANDOFF"]as const;export type EditStageUid=typeof EDIT_STAGE_UIDS[number];
export type EditStagePhase="READY"|"RUNNING"|"EVALUATING"|"WAIT_CONFIRMATION"|"CORRECTION"|"CONFIRMED"|"COMPLETED"|"BLOCKED";
export type EditStageState={stage_uid:EditStageUid;phase:EditStagePhase;latest_evaluation_ref:string|null;latest_result:"PASS"|"FAIL"|null;hard_block:boolean;checkpoint_ref:string|null};
export const INITIAL_EDIT_STAGE_STATE:EditStageState={stage_uid:"EDIT-01-STAGE-01-ASSEMBLY",phase:"READY",latest_evaluation_ref:null,latest_result:null,hard_block:false,checkpoint_ref:null};
export type EditStageEvent=
|{type:"START"}|{type:"EXECUTION_COMPLETE"}|{type:"EVALUATION_COMPLETE";evaluation_ref:string;result:"PASS"|"FAIL";hard_block:boolean}|{type:"MODIFY"}|{type:"CORRECTION_COMPLETE"}|{type:"CONFIRM";checkpoint_ref:string}|{type:"FINALIZE_COMPLETE"}|{type:"HANDOFF_COMPLETE"}|{type:"BLOCK"};
function nextConfirmedStage(stage:EditStageUid):EditStageUid|null{if(stage==="EDIT-01-STAGE-01-ASSEMBLY")return"EDIT-01-STAGE-02-AUDIO";if(stage==="EDIT-01-STAGE-02-AUDIO")return"EDIT-01-STAGE-03-SYNC";if(stage==="EDIT-01-STAGE-03-SYNC")return"EDIT-01-STAGE-04-FINALIZE";return null;}
export function reduceEditStageState(s:EditStageState,e:EditStageEvent):EditStageState{switch(e.type){
case"START":return s.phase==="READY"?{...s,phase:"RUNNING"}:s;
case"EXECUTION_COMPLETE":return s.phase==="RUNNING"&&s.stage_uid!=="EDIT-01-STAGE-04-FINALIZE"&&s.stage_uid!=="EDIT-01-STAGE-05-QA-HANDOFF"?{...s,phase:"EVALUATING"}:s;
case"EVALUATION_COMPLETE":return s.phase==="EVALUATING"||s.phase==="CORRECTION"?{...s,phase:"WAIT_CONFIRMATION",latest_evaluation_ref:e.evaluation_ref,latest_result:e.result,hard_block:e.hard_block}:s;
case"MODIFY":return s.phase==="WAIT_CONFIRMATION"?{...s,phase:"CORRECTION"}:s;
case"CORRECTION_COMPLETE":return s.phase==="CORRECTION"?{...s,phase:"EVALUATING"}:s;
case"CONFIRM":{if(s.phase!=="WAIT_CONFIRMATION"||s.latest_result!=="PASS"||s.hard_block)return s;const n=nextConfirmedStage(s.stage_uid);return n?{stage_uid:n,phase:"READY",latest_evaluation_ref:null,latest_result:null,hard_block:false,checkpoint_ref:e.checkpoint_ref}:s;}
case"FINALIZE_COMPLETE":return s.stage_uid==="EDIT-01-STAGE-04-FINALIZE"&&s.phase==="RUNNING"?{stage_uid:"EDIT-01-STAGE-05-QA-HANDOFF",phase:"READY",latest_evaluation_ref:null,latest_result:null,hard_block:false,checkpoint_ref:s.checkpoint_ref}:s;
case"HANDOFF_COMPLETE":return s.stage_uid==="EDIT-01-STAGE-05-QA-HANDOFF"&&s.phase==="RUNNING"?{...s,phase:"COMPLETED"}:s;
case"BLOCK":return{...s,phase:"BLOCKED"};}}
export function canConfirmEditStage(s:EditStageState){return(s.stage_uid==="EDIT-01-STAGE-01-ASSEMBLY"||s.stage_uid==="EDIT-01-STAGE-02-AUDIO"||s.stage_uid==="EDIT-01-STAGE-03-SYNC")&&s.phase==="WAIT_CONFIRMATION"&&s.latest_result==="PASS"&&!s.hard_block;}
