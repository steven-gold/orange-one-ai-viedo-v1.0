import { isControlledTestMode } from "@/domain/testing/controlledTestData";

export type AssetListItem={ref:string;label:string};
export type AssetProjectionCandidateVersion={ref:string;label:string;uri:string;media_kind:"IMAGE"|"AUDIO"|"REFERENCE"};
export type AssetProjectionTestMetadata={
  data_classification:"TEST_ONLY";
  synthetic:true;
  test_dataset_id:string;
  test_run_id:string;
  created_for_validation:true;
  production_eligible:false;
};
export type AssetNormalizedProjection={
  page_state:string|null;
  task_id:string|null;
  output_version_id:string|null;
  layer_document_id:string|null;
  layer_id:string|null;
  patch_id:string|null;
  current_asset_type_uid:string|null;
  candidate_uri:string|null;
  candidate_media_kind:"IMAGE"|"AUDIO"|"REFERENCE"|null;
  candidate_versions:readonly AssetProjectionCandidateVersion[];
  values:Readonly<Record<string,string>>;
  lists:Readonly<Record<string,readonly AssetListItem[]>>;
  filters:Readonly<Record<string,readonly AssetListItem[]>>;
  gate_state:Readonly<Record<string,boolean>>;
  test_metadata?:AssetProjectionTestMetadata;
};
export type AssetProjectionResolver={resolve:(raw:unknown)=>AssetNormalizedProjection|Promise<AssetNormalizedProjection>};
let resolver:AssetProjectionResolver|null=null;
export function configureAssetProjectionResolver(next:AssetProjectionResolver){resolver=next;}
export function isAssetProjectionResolverBound(){return resolver!==null;}
function textOrNull(v:unknown){return v===null||typeof v==="string";}
function validListMap(v:unknown){
  if(!v||typeof v!=="object")return false;
  return Object.values(v as Record<string,unknown>).every(items=>Array.isArray(items)&&items.every(item=>item&&typeof item==="object"&&typeof (item as AssetListItem).ref==="string"&&typeof (item as AssetListItem).label==="string"));
}
function validTestMetadata(v:unknown){
  if(!v||typeof v!=="object")return false;
  const m=v as Record<string,unknown>;
  return m.data_classification==="TEST_ONLY"&&m.synthetic===true&&typeof m.test_dataset_id==="string"&&typeof m.test_run_id==="string"&&m.created_for_validation===true&&m.production_eligible===false;
}
function validProjection(v:unknown):v is AssetNormalizedProjection{
  if(!v||typeof v!=="object")return false;
  const p=v as Partial<AssetNormalizedProjection>;
  if(!textOrNull(p.page_state)||!textOrNull(p.task_id)||!textOrNull(p.output_version_id)||!textOrNull(p.layer_document_id)||!textOrNull(p.layer_id)||!textOrNull(p.patch_id)||!textOrNull(p.current_asset_type_uid)||!textOrNull(p.candidate_uri)||!textOrNull(p.candidate_media_kind))return false;
  if(!Array.isArray(p.candidate_versions)||p.candidate_versions.some(item=>!item||typeof item.ref!=="string"||typeof item.label!=="string"||typeof item.uri!=="string"||!["IMAGE","AUDIO","REFERENCE"].includes(item.media_kind)))return false;
  if(!p.values||typeof p.values!=="object"||Object.values(p.values).some(item=>typeof item!=="string"))return false;
  if(!validListMap(p.lists)||!validListMap(p.filters))return false;
  if(!p.gate_state||typeof p.gate_state!=="object"||Object.values(p.gate_state).some(item=>typeof item!=="boolean"))return false;
  if(p.test_metadata!==undefined){if(!isControlledTestMode()||!validTestMetadata(p.test_metadata))return false;}
  return true;
}
export async function readAssetProjection(signal?:AbortSignal){
  let response:Response;
  try{response=await fetch('/v1/ui-projections/ASSET-01',{method:'GET',cache:'no-store',signal});}
  catch{return{ok:false as const,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:'ASSET_PROJECTION_REQUEST_FAILED',correlation_id:'unresolved'};}
  const correlation_id=response.headers.get('x-correlation-id')??'unresolved';
  const raw:unknown=await response.json().catch(()=>null);
  if(!response.ok){const body=typeof raw==='object'&&raw!==null?raw as Record<string,unknown>:null;return{ok:false as const,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:typeof body?.reason_code==='string'?body.reason_code:'ASSET_PROJECTION_READ_FAILED',correlation_id:typeof body?.correlation_id==='string'?body.correlation_id:correlation_id};}
  if(!resolver){
    if(isControlledTestMode()&&validProjection(raw)&&raw.test_metadata?.data_classification==="TEST_ONLY"&&raw.test_metadata.production_eligible===false)return{ok:true as const,projection:raw,correlation_id};
    return{ok:false as const,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:'ASSET_PROJECTION_ADAPTER_NOT_BOUND',correlation_id};
  }
  try{const projection=await resolver.resolve(raw);if(!validProjection(projection)||projection.test_metadata!==undefined)throw new Error('ASSET_PROJECTION_SCHEMA_REJECTED');return{ok:true as const,projection,correlation_id};}
  catch{return{ok:false as const,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:'ASSET_PROJECTION_ADAPTER_REJECTED',correlation_id};}
}
