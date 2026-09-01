export const INFO_PAGE_STATES=['LOADING','READY','EMPTY','STALE','INCOMPLETE','ERROR','POLICY_BLOCKED','CONTEXT_CANDIDATE']as const;
export type InfoPageState=typeof INFO_PAGE_STATES[number];
export function isInfoPageState(value:unknown):value is InfoPageState{return typeof value==='string'&&(INFO_PAGE_STATES as readonly string[]).includes(value);}
export type InfoListItem={ref:string;label:string};
export type InfoNormalizedProjection={
  page_state:InfoPageState|null;
  projection_version:string|null;
  authorized_scope:string|null;
  last_refresh:string|null;
  values:Readonly<Record<string,string>>;
  lists:Readonly<Record<string,readonly InfoListItem[]>>;
  filters:Readonly<Record<string,readonly InfoListItem[]>>;
  gate_state:Readonly<Record<string,boolean>>;
};
export type InfoProjectionResolver={resolve:(raw:unknown)=>InfoNormalizedProjection|Promise<InfoNormalizedProjection>};
let resolver:InfoProjectionResolver|null=null;
export function configureInfoProjectionResolver(next:InfoProjectionResolver){resolver=next;}
export function isInfoProjectionResolverBound(){return resolver!==null;}
export async function readInfoProjection(signal?:AbortSignal){
  let response:Response;
  try{response=await fetch('/v1/ui-projections/workspace%3AINFO-01',{method:'GET',cache:'no-store',signal});}
  catch{return{ok:false as const,error_uid:'INFO-01-ERR-CONTEXT-001',reason_code:'INFO_PROJECTION_REQUEST_FAILED',correlation_id:'unresolved'};}
  const correlation_id=response.headers.get('x-correlation-id')??'unresolved';
  const raw:unknown=await response.json().catch(()=>null);
  if(!response.ok){const body=typeof raw==='object'&&raw!==null?raw as Record<string,unknown>:null;return{ok:false as const,error_uid:'INFO-01-ERR-CONTEXT-001',reason_code:typeof body?.reason_code==='string'?body.reason_code:'INFO_PROJECTION_READ_FAILED',correlation_id:typeof body?.correlation_id==='string'?body.correlation_id:correlation_id};}
  if(!resolver)return{ok:false as const,error_uid:'INFO-01-ERR-CONTEXT-001',reason_code:'INFO_PROJECTION_ADAPTER_NOT_BOUND',correlation_id};
  try{const projection=await resolver.resolve(raw);const pageState=(projection as{page_state?:unknown}).page_state;if(pageState!==null&&!isInfoPageState(pageState))throw new Error('INFO_PROJECTION_PAGE_STATE_UNREGISTERED');return{ok:true as const,projection,correlation_id};}
  catch{return{ok:false as const,error_uid:'INFO-01-ERR-CONTEXT-001',reason_code:'INFO_PROJECTION_ADAPTER_REJECTED',correlation_id};}
}
