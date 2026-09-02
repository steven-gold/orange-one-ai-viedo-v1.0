import{isControlledTestMode}from'@/domain/testing/controlledTestData';
export type StrategyListItem={ref:string;label:string};
export type StrategyProjectionTestMetadata={data_classification:"TEST_ONLY";synthetic:true;test_dataset_id:string;test_run_id:string;created_for_validation:true;production_eligible:false};
export type StrategyNormalizedProjection={
  page_state:string|null;
  conversation_id:string|null;
  candidate_ref:string|null;
  candidate_version_ref:string|null;
  values:Readonly<Record<string,string>>;
  lists:Readonly<Record<string,readonly StrategyListItem[]>>;
  blocks:Readonly<Record<string,string>>;
  gate_state:Readonly<Record<string,boolean>>;
  owner_type:string|null;
  owner_context_ref:string|null;
  test_metadata?:StrategyProjectionTestMetadata;
};
export type StrategyProjectionResolver={resolve:(raw:unknown)=>StrategyNormalizedProjection|Promise<StrategyNormalizedProjection>};
let resolver:StrategyProjectionResolver|null=null;
export function configureStrategyProjectionResolver(next:StrategyProjectionResolver){resolver=next;}
function object(value:unknown):value is Record<string,unknown>{return Boolean(value)&&typeof value==='object'&&!Array.isArray(value);}
function nullableString(value:unknown){return value===null||typeof value==='string';}
const STRATEGY_PAGE_STATES=new Set(['EMPTY','READY','RESPONDING','ANALYZING','CANDIDATE_READY','REVIEW_REQUIRED','ADOPTED_CONTEXT','FEEDBACK_AVAILABLE','ERROR/BLOCKED']);
function stringRecord(value:unknown){return object(value)&&Object.values(value).every(item=>typeof item==='string');}
function booleanRecord(value:unknown){return object(value)&&Object.values(value).every(item=>typeof item==='boolean');}
function listRecord(value:unknown){return object(value)&&Object.values(value).every(items=>Array.isArray(items)&&items.every(item=>object(item)&&typeof item.ref==='string'&&item.ref.trim().length>0&&typeof item.label==='string'));}
function testMetadata(value:unknown):StrategyProjectionTestMetadata|undefined{if(value===undefined)return undefined;if(!object(value)||value.data_classification!=="TEST_ONLY"||value.synthetic!==true||typeof value.test_dataset_id!=="string"||typeof value.test_run_id!=="string"||value.created_for_validation!==true||value.production_eligible!==false)return undefined;if(!isControlledTestMode())return undefined;return value as unknown as StrategyProjectionTestMetadata;}
function normalizeStrategyProjection(raw:unknown):StrategyNormalizedProjection|null{
  const candidate=object(raw)&&object(raw.projection)?raw.projection:raw;
  if(!object(candidate))return null;
  if(typeof candidate.page_state!=='string'||!STRATEGY_PAGE_STATES.has(candidate.page_state)||!nullableString(candidate.conversation_id)||!nullableString(candidate.candidate_ref)||!nullableString(candidate.candidate_version_ref)||!nullableString(candidate.owner_type)||!nullableString(candidate.owner_context_ref))return null;
  if(!stringRecord(candidate.values)||!listRecord(candidate.lists)||!stringRecord(candidate.blocks)||!booleanRecord(candidate.gate_state))return null;
  const metadata=testMetadata(candidate.test_metadata);if(candidate.test_metadata!==undefined&&!metadata)return null;
  return{page_state:candidate.page_state,conversation_id:candidate.conversation_id as string|null,candidate_ref:candidate.candidate_ref as string|null,candidate_version_ref:candidate.candidate_version_ref as string|null,values:candidate.values as Record<string,string>,lists:candidate.lists as Record<string,StrategyListItem[]>,blocks:candidate.blocks as Record<string,string>,gate_state:candidate.gate_state as Record<string,boolean>,owner_type:candidate.owner_type as string|null,owner_context_ref:candidate.owner_context_ref as string|null,test_metadata:metadata};
}
export function isStrategyProjectionResolverBound(){return true;}
export async function readStrategyProjection(signal?:AbortSignal){
  let response:Response;
  try{response=await fetch('/v1/ui-projections/workspace%3ASTR-01',{method:'GET',cache:'no-store',signal});}
  catch{return{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:'STRATEGY_PROJECTION_REQUEST_FAILED',correlation_id:'unresolved'};}
  const correlation_id=response.headers.get('x-correlation-id')??'unresolved';
  const raw:unknown=await response.json().catch(()=>null);
  if(!response.ok){const body=typeof raw==='object'&&raw!==null?raw as Record<string,unknown>:null;return{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:typeof body?.reason_code==='string'?body.reason_code:'STRATEGY_PROJECTION_READ_FAILED',correlation_id:typeof body?.correlation_id==='string'?body.correlation_id:correlation_id};}
  if(resolver){try{const projection=await resolver.resolve(raw);if(projection.test_metadata!==undefined&&!isControlledTestMode())throw new Error('STRATEGY_TEST_PROJECTION_FORBIDDEN_IN_PRODUCTION');return{ok:true as const,projection,correlation_id};}catch{return{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:'STRATEGY_PROJECTION_ADAPTER_REJECTED',correlation_id};}}
  const projection=normalizeStrategyProjection(raw);
  return projection?{ok:true as const,projection,correlation_id}:{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:'INVALID_STRATEGY_PROJECTION',correlation_id};
}
