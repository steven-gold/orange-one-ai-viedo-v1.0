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
export function isStrategyProjectionResolverBound(){return resolver!==null;}
export async function readStrategyProjection(signal?:AbortSignal){
  let response:Response;
  try{response=await fetch('/v1/ui-projections/workspace%3ASTR-01',{method:'GET',cache:'no-store',signal});}
  catch{return{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:'STRATEGY_PROJECTION_REQUEST_FAILED',correlation_id:'unresolved'};}
  const correlation_id=response.headers.get('x-correlation-id')??'unresolved';
  const raw:unknown=await response.json().catch(()=>null);
  if(!response.ok){const body=typeof raw==='object'&&raw!==null?raw as Record<string,unknown>:null;return{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:typeof body?.reason_code==='string'?body.reason_code:'STRATEGY_PROJECTION_READ_FAILED',correlation_id:typeof body?.correlation_id==='string'?body.correlation_id:correlation_id};}
  if(!resolver)return{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:'STRATEGY_PROJECTION_ADAPTER_NOT_BOUND',correlation_id};
  try{return{ok:true as const,projection:await resolver.resolve(raw),correlation_id};}
  catch{return{ok:false as const,error_uid:'STR-01-ERR-CONTEXT-001',reason_code:'STRATEGY_PROJECTION_ADAPTER_REJECTED',correlation_id};}
}
