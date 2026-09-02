export type StrategyListItem={ref:string;label:string};
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
function normalizeStrategyProjection(raw:unknown):StrategyNormalizedProjection|null{
  const candidate=object(raw)&&object(raw.projection)?raw.projection:raw;
  if(!object(candidate))return null;
  if(typeof candidate.page_state!=='string'||!STRATEGY_PAGE_STATES.has(candidate.page_state)||!nullableString(candidate.conversation_id)||!nullableString(candidate.candidate_ref)||!nullableString(candidate.candidate_version_ref)||!nullableString(candidate.owner_type)||!nullableString(candidate.owner_context_ref))return null;
  if(!stringRecord(candidate.values)||!listRecord(candidate.lists)||!stringRecord(candidate.blocks)||!booleanRecord(candidate.gate_state))return null;
  return candidate as StrategyNormalizedProjection;
}
export function isStrategyProjectionResolverBound(){return true;}
export async function readStrategyProjection(signal?:AbortSignal){
  let response:Response;
  try{response=await fetch('/v1/ui-projections/workspace%3ASTR-01',{method:'GET',cache:'no-store',signal});}
  catch{return{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:'STRATEGY_PROJECTION_REQUEST_FAILED',correlation_id:'unresolved'};}
  const correlation_id=response.headers.get('x-correlation-id')??'unresolved';
  const raw:unknown=await response.json().catch(()=>null);
  if(!response.ok){const body=typeof raw==='object'&&raw!==null?raw as Record<string,unknown>:null;return{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:typeof body?.reason_code==='string'?body.reason_code:'STRATEGY_PROJECTION_READ_FAILED',correlation_id:typeof body?.correlation_id==='string'?body.correlation_id:correlation_id};}
  if(resolver){try{return{ok:true as const,projection:await resolver.resolve(raw),correlation_id};}catch{return{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:'STRATEGY_PROJECTION_ADAPTER_REJECTED',correlation_id};}}
  const projection=normalizeStrategyProjection(raw);
  return projection?{ok:true as const,projection,correlation_id}:{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:'INVALID_STRATEGY_PROJECTION',correlation_id};
}
