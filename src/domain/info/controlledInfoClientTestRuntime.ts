import { isControlledTestMode } from "@/domain/testing/controlledTestData";
import { configureInfoProjectionResolver, isInfoPageState, type InfoNormalizedProjection } from "./infoProjectionPort";
import { configureInfoCommandPayloadBuilder, type InfoCommandAction } from "./infoCommandPort";

const TEST_METADATA={data_classification:"TEST_ONLY",synthetic:true,test_dataset_id:"TEST-INFO-01",test_run_id:"TEST-RUN-INFO-CONTROLLED-01",created_for_validation:true,production_eligible:false}as const;
let configured=false;
function rec(v:unknown):Record<string,unknown>{return v&&typeof v==="object"&&!Array.isArray(v)?v as Record<string,unknown>:{};}
function text(v:unknown){return typeof v==="string"?v:null;}
function listMap(v:unknown){const out:Record<string,{ref:string;label:string}[]>={};for(const[key,value]of Object.entries(rec(v))){if(!Array.isArray(value))continue;out[key]=value.flatMap(item=>{const r=rec(item),ref=text(r.ref),label=text(r.label);return ref&&label?[{ref,label}]:[];});}return out;}
function boolMap(v:unknown){const out:Record<string,boolean>={};for(const[key,value]of Object.entries(rec(v)))if(typeof value==="boolean")out[key]=value;return out;}
function stringMap(v:unknown){const out:Record<string,string>={};for(const[key,value]of Object.entries(rec(v)))if(typeof value==="string")out[key]=value;return out;}
function resolveControlled(raw:unknown):InfoNormalizedProjection{
  const r=rec(raw),metadata=rec(r.test_metadata);
  if(metadata.data_classification!=="TEST_ONLY"||metadata.synthetic!==true||metadata.production_eligible!==false)throw new Error("INFO_CONTROLLED_TEST_METADATA_REQUIRED");
  const pageState=r.page_state;if(!isInfoPageState(pageState))throw new Error("INFO_CONTROLLED_PAGE_STATE_INVALID");
  return{page_state:pageState,projection_version:text(r.projection_version),authorized_scope:text(r.authorized_scope),last_refresh:text(r.last_refresh),values:stringMap(r.values),lists:listMap(r.lists),filters:listMap(r.filters),gate_state:boolMap(r.gate_state)};
}
function payload(action_uid:InfoCommandAction,input:{candidate_ref:string|null;scope_filter:string|null;projection_version:string|null;authorized_scope:string|null}){
  const base={page_uid:"workspace:INFO-01",projection_version:input.projection_version,authorized_scope:input.authorized_scope,scope_filter:input.scope_filter,test_metadata:TEST_METADATA};
  if(action_uid==="INFO-01-ACT-REFRESH")return{payload:{...base,request:"REFRESH_REGISTERED_PROJECTION"}};
  if(action_uid==="INFO-01-ACT-SEARCH")return{payload:{...base,query:"TEST controlled registered projection"}};
  if(action_uid==="INFO-01-ACT-EXPORT")return{payload:{...base,export_scope:"CURRENT_AUTHORIZED_PROJECTION"}};
  if(action_uid==="INFO-01-ACT-ADOPT-CONTEXT"){if(!input.candidate_ref)throw new Error("INFO_CONTEXT_CANDIDATE_REQUIRED");return{path_params:{id:input.candidate_ref},payload:{...base,context_candidate_id:input.candidate_ref,decision_reason:"TEST_ONLY governed context adoption validation"}};}
  if(action_uid==="INFO-01-ACT-CANDIDATE-DECIDE"){if(!input.candidate_ref)throw new Error("INFO_CANDIDATE_REQUIRED");return{path_params:{id:input.candidate_ref},payload:{...base,candidate_id:input.candidate_ref,decision:"ACCEPTED",decision_reason:"TEST_ONLY registered candidate decision validation"}};}
  throw new Error("INFO_CONTROLLED_ACTION_UNREGISTERED");
}
export function ensureControlledInfoClientTestRuntime(){if(configured||!isControlledTestMode())return false;configureInfoProjectionResolver({resolve:resolveControlled});configureInfoCommandPayloadBuilder({build:input=>payload(input.action_uid,input)});configured=true;return true;}
