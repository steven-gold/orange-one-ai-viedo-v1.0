export type AssetListItem={ref:string;label:string};
export type AssetNormalizedProjection={
  page_state:string|null;
  task_id:string|null;
  output_version_id:string|null;
  layer_document_id:string|null;
  layer_id:string|null;
  patch_id:string|null;
  values:Readonly<Record<string,string>>;
  lists:Readonly<Record<string,readonly AssetListItem[]>>;
  filters:Readonly<Record<string,readonly AssetListItem[]>>;
  gate_state:Readonly<Record<string,boolean>>;
};
export type AssetProjectionResolver={resolve:(raw:unknown)=>AssetNormalizedProjection|Promise<AssetNormalizedProjection>};
let resolver:AssetProjectionResolver|null=null;
export function configureAssetProjectionResolver(next:AssetProjectionResolver){resolver=next;}
export function isAssetProjectionResolverBound(){return resolver!==null;}
export async function readAssetProjection(signal?:AbortSignal){
  let response:Response;
  try{response=await fetch('/v1/ui-projections/ASSET-01',{method:'GET',cache:'no-store',signal});}
  catch{return{ok:false as const,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:'ASSET_PROJECTION_REQUEST_FAILED',correlation_id:'unresolved'};}
  const correlation_id=response.headers.get('x-correlation-id')??'unresolved';
  const raw:unknown=await response.json().catch(()=>null);
  if(!response.ok){const body=typeof raw==='object'&&raw!==null?raw as Record<string,unknown>:null;return{ok:false as const,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:typeof body?.reason_code==='string'?body.reason_code:'ASSET_PROJECTION_READ_FAILED',correlation_id:typeof body?.correlation_id==='string'?body.correlation_id:correlation_id};}
  if(!resolver)return{ok:false as const,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:'ASSET_PROJECTION_ADAPTER_NOT_BOUND',correlation_id};
  try{return{ok:true as const,projection:await resolver.resolve(raw),correlation_id};}
  catch{return{ok:false as const,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:'ASSET_PROJECTION_ADAPTER_REJECTED',correlation_id};}
}
