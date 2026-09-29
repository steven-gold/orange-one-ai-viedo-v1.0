import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import type { InfoNormalizedProjection } from "@/domain/info/infoProjectionPort";
import type { InfoRequest } from "@/server/info/infoCommandRuntime";
import type { CandidateDecisionRequest } from "@/server/shared/candidateDecisionRuntime";

const TEST_METADATA={data_classification:"TEST_ONLY",synthetic:true,test_dataset_id:"TEST-INFO-01",test_run_id:"TEST-RUN-INFO-CONTROLLED-01",created_for_validation:true,production_eligible:false}as const;
const CANDIDATE_REF="TEST-INFO-CONTEXT-CANDIDATE-001";
let projectionVersion=1;
let candidateState="CONTEXT_CANDIDATE";
let lastCorrelation="TEST-INFO-CORRELATION-INITIAL";

function record(v:unknown):Record<string,unknown>{return v&&typeof v==="object"&&!Array.isArray(v)?v as Record<string,unknown>:{};}
function text(v:unknown){return typeof v==="string"&&v.trim()?v.trim():null;}
export function isControlledInfoServerTestMode(){return isControlledTestMode();}

function gates(){return{
  "INFO-01-GATE-PAGE":true,
  "INFO-01-GATE-READ":true,
  "INFO-01-GATE-FACTPACK":true,
  "INFO-01-GATE-EVIDENCE":true,
  "INFO-01-GATE-REFRESH":true,
  "INFO-01-GATE-SEARCH":true,
  "INFO-01-GATE-EXPORT":true,
  "INFO-01-GATE-CANDIDATE":true,
  "INFO-01-GATE-ADOPT":candidateState==="CONTEXT_CANDIDATE",
  "INFO-01-GATE-DECIDE":candidateState==="CONTEXT_CANDIDATE"||candidateState==="ADOPTED",
};}

export function readControlledInfoTestProjection():InfoNormalizedProjection&{test_metadata:typeof TEST_METADATA}{
  const values:Record<string,string>={
    "INFO-01-FLD-SOURCE-HEALTH":"READY",
    "INFO-01-FLD-SOURCE-TIME":"2026-09-01T08:00:00Z",
    "INFO-01-FLD-SOURCE-CLASS":"REGISTERED_SOURCE",
    "INFO-01-FLD-ALERT-SCOPE":"TEST-PROJECT-001",
    "INFO-01-FLD-ALERT-SOURCE":"TEST-INFO-SOURCE-001",
    "INFO-01-FLD-ALERT-STATUS":"OPEN",
    "INFO-01-FLD-FACTPACK-SCOPE":"TEST-PROJECT-001",
    "INFO-01-FLD-FACTPACK-STATE":"REGISTERED",
    "INFO-01-FLD-FACTPACK-SOURCE-COUNT":"1",
    "INFO-01-FLD-ITEM-CLASS":"FACT",
    "INFO-01-FLD-ITEM-SCOPE":"TEST-PROJECT-001",
    "INFO-01-FLD-ITEM-SOURCE-TIME":"2026-09-01T08:00:00Z",
    "INFO-01-FLD-ITEM-EVIDENCE":"TEST-INFO-EVIDENCE-001",
    "INFO-01-FLD-EVIDENCE-SOURCE":"TEST-INFO-SOURCE-001",
    "INFO-01-FLD-EVIDENCE-TIME":"2026-09-01T08:00:00Z",
    "INFO-01-FLD-EVIDENCE-SCOPE":"TEST-PROJECT-001",
    "INFO-01-FLD-EVIDENCE-CLASS":"REGISTERED_EVIDENCE",
    "INFO-01-FLD-FRESHNESS":"STALE",
    "INFO-01-FLD-COMPLETENESS":"INCOMPLETE — source coverage pending",
    "INFO-01-FLD-CONFIDENCE":"0.82 · SOURCE_OWNED",
    "INFO-01-FLD-VERIFICATION-TIME":"2026-09-01T08:15:00Z",
    "INFO-01-FLD-RESEARCH-STATE":"RUNNING · READ_ONLY",
    "INFO-01-FLD-RESEARCH-SCOPE":"TEST-PROJECT-001",
    "INFO-01-FLD-RESEARCH-RESULT":"—",
    "INFO-01-FLD-CANDIDATE-SCOPE":"TEST-PROJECT-001",
    "INFO-01-FLD-CANDIDATE-FACTS":"TEST-INFO-FACT-001",
    "INFO-01-FLD-CANDIDATE-CITATIONS":"TEST-INFO-CITATION-001",
    "INFO-01-FLD-CANDIDATE-PREVIEW":"[TEST] Context candidate preview; no Canon/Lock/Task/Publish mutation",
    "INFO-01-FLD-ADOPTION-REVIEW":"Evidence-backed governed review",
    "INFO-01-FLD-CANDIDATE-STATE":candidateState,
    "INFO-01-FLD-CITATION-REF":"TEST-INFO-CITATION-001",
    "INFO-01-FLD-CITATION-SOURCE":"TEST-INFO-SOURCE-001",
    "INFO-01-FLD-CITATION-EVIDENCE":"TEST-INFO-EVIDENCE-001",
    "INFO-01-FLD-CITATION-TIME":"2026-09-01T08:00:00Z",
    "INFO-01-FLD-SOURCE-SYNC":"STALE · governed freshness data",
    "INFO-01-FLD-DISABLED":"Research queue/runs are read-only; direct Canon/Lock/Priority/Budget/Task/Release/Publish mutation forbidden",
    "INFO-01-FLD-FIREWALL":"OWNER_BOUNDARY_ENFORCED",
  };
  const lists={
    "INFO-01-LST-SOURCES":[{ref:"TEST-INFO-SOURCE-001",label:"[TEST] Registered source · STALE"}],
    "INFO-01-LST-ALERTS":[{ref:"TEST-INFO-ALERT-001",label:"[TEST] Information alert"}],
    "INFO-01-LST-FACTPACKS":[{ref:"TEST-INFO-FACTPACK-001",label:"[TEST] Fact Pack v1"}],
    "INFO-01-LST-FACTS":[{ref:"TEST-INFO-FACT-001",label:"[TEST] FACT · evidence-backed"}],
    "INFO-01-LST-INFERENCES":[{ref:"TEST-INFO-INFERENCE-001",label:"[TEST] INFERENCE · explicitly classified"}],
    "INFO-01-LST-EVIDENCE":[{ref:"TEST-INFO-EVIDENCE-001",label:"[TEST] Evidence ref"}],
    "INFO-01-LST-RESEARCH":[{ref:"TEST-INFO-RESEARCH-001",label:"[TEST] Research Run · RUNNING · READ_ONLY"}],
    "INFO-01-LST-CANDIDATES":[{ref:CANDIDATE_REF,label:`[TEST] Context Candidate · ${candidateState}`}],
  };
  const filters={"INFO-01-SEL-SCOPE":[{ref:"TEST-PROJECT-001",label:"[TEST] Authorized Project Scope"}]};
  return{page_state:"STALE",projection_version:`TEST-INFO-PROJECTION-v${projectionVersion}`,authorized_scope:"TEST-PROJECT-001",last_refresh:"2026-09-01T08:15:00Z",values,lists,filters,gate_state:gates(),test_metadata:TEST_METADATA};
}

export async function executeControlledInfoCommand(r:InfoRequest){
  if(!isControlledInfoServerTestMode())return null;
  const p=record(r.payload);lastCorrelation=r.correlation_id;
  if(text(p.page_uid)!=="workspace:INFO-01")return null;
  if(r.operation_id==="refreshProjection"){
    projectionVersion+=1;
    return{ok:true as const,value:{operation:"refreshProjection",projection_version:`TEST-INFO-PROJECTION-v${projectionVersion}`,mutation_scope:"PROJECTION_ONLY",test_metadata:TEST_METADATA},correlation_id:r.correlation_id};
  }
  if(r.operation_id==="searchProjection"){
    return{ok:true as const,value:{operation:"searchProjection",results:[{ref:"TEST-INFO-FACTPACK-001",classification:"FACT_PACK"}],authorized_scope:"TEST-PROJECT-001",test_metadata:TEST_METADATA},correlation_id:r.correlation_id};
  }
  if(r.operation_id==="exportProjection"){
    return{ok:true as const,value:{operation:"exportProjection",export_ref:"TEST-INFO-EXPORT-001",fabricated_file:false,test_metadata:TEST_METADATA},correlation_id:r.correlation_id};
  }
  if(r.operation_id==="adoptContextCandidate"){
    if(r.path_params.id!==CANDIDATE_REF)return{ok:false as const,status:409,reason_code:"INFO01_EXACT_CONTEXT_CANDIDATE_REQUIRED",correlation_id:r.correlation_id};
    if(!text(p.decision_reason))return{ok:false as const,status:400,reason_code:"INFO01_DECISION_REASON_REQUIRED",correlation_id:r.correlation_id};
    candidateState="ADOPTED";
    return{ok:true as const,value:{operation:"adoptContextCandidate",context_candidate_id:CANDIDATE_REF,state:candidateState,direct_owner_mutation:false,test_metadata:TEST_METADATA},correlation_id:r.correlation_id};
  }
  return null;
}

export async function executeControlledInfoCandidateDecision(r:CandidateDecisionRequest){
  if(!isControlledInfoServerTestMode()||r.candidate_id!==CANDIDATE_REF)return null;
  const p=record(r.payload);if(text(p.page_uid)!=="workspace:INFO-01")return null;
  const decision=text(p.decision);if(decision!=="ACCEPTED"&&decision!=="REJECTED")return{ok:false as const,status:400,reason_code:"INFO01_REGISTERED_DECISION_REQUIRED",correlation_id:r.correlation_id};
  lastCorrelation=r.correlation_id;
  return{ok:true as const,value:{operation:"decideCandidate",candidate_id:CANDIDATE_REF,decision,direct_owner_mutation:false,test_metadata:TEST_METADATA},correlation_id:r.correlation_id};
}

export function controlledInfoLastCorrelation(){return lastCorrelation;}
