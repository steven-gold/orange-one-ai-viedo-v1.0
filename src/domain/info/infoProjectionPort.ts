import{isControlledTestMode}from'@/domain/testing/controlledTestData';
export const INFO_PAGE_STATES=['LOADING','READY','EMPTY','STALE','INCOMPLETE','ERROR','POLICY_BLOCKED','CONTEXT_CANDIDATE']as const;
export type InfoPageState=typeof INFO_PAGE_STATES[number];
export function isInfoPageState(value:unknown):value is InfoPageState{return typeof value==='string'&&(INFO_PAGE_STATES as readonly string[]).includes(value);}
export type InfoListItem={ref:string;label:string};
export type InfoProjectionTestMetadata={data_classification:"TEST_ONLY";synthetic:true;test_dataset_id:string;test_run_id:string;created_for_validation:true;production_eligible:false};
export type InfoNormalizedProjection={
  page_state:InfoPageState|null;
  projection_version:string|null;
  authorized_scope:string|null;
  last_refresh:string|null;
  values:Readonly<Record<string,string>>;
  lists:Readonly<Record<string,readonly InfoListItem[]>>;
  filters:Readonly<Record<string,readonly InfoListItem[]>>;
  gate_state:Readonly<Record<string,boolean>>;
  test_metadata?:InfoProjectionTestMetadata;
};
export type InfoProjectionResolver={resolve:(raw:unknown)=>InfoNormalizedProjection|Promise<InfoNormalizedProjection>};
let resolver:InfoProjectionResolver|null=null;
export function configureInfoProjectionResolver(next:InfoProjectionResolver){resolver=next;}
export function isInfoProjectionResolverBound(){return true;}
function object(value:unknown):value is Record<string,unknown>{return Boolean(value)&&typeof value==='object'&&!Array.isArray(value);}
function nullableString(value:unknown){return value===null||typeof value==='string';}
function stringRecord(value:unknown){return object(value)&&Object.values(value).every(item=>typeof item==='string');}
function booleanRecord(value:unknown){return object(value)&&Object.values(value).every(item=>typeof item==='boolean');}
function listRecord(value:unknown){return object(value)&&Object.values(value).every(items=>Array.isArray(items)&&items.every(item=>object(item)&&typeof item.ref==='string'&&item.ref.trim().length>0&&typeof item.label==='string'));}
function testMetadata(value:unknown):InfoProjectionTestMetadata|undefined{
  if(value===undefined)return undefined;
  if(!object(value)||value.data_classification!=="TEST_ONLY"||value.synthetic!==true||typeof value.test_dataset_id!=="string"||typeof value.test_run_id!=="string"||value.created_for_validation!==true||value.production_eligible!==false)return undefined;
  if(!isControlledTestMode())return undefined;
  return value as unknown as InfoProjectionTestMetadata;
}
function normalizeInfoProjection(raw:unknown):InfoNormalizedProjection|null{
  const candidate=object(raw)&&object(raw.projection)?raw.projection:raw;
  if(!object(candidate))return null;
  if(!nullableString(candidate.page_state)||!nullableString(candidate.projection_version)||!nullableString(candidate.authorized_scope)||!nullableString(candidate.last_refresh))return null;
  if(candidate.page_state!==null&&!isInfoPageState(candidate.page_state))return null;
  if(!stringRecord(candidate.values)||!listRecord(candidate.lists)||!listRecord(candidate.filters)||!booleanRecord(candidate.gate_state))return null;
  const metadata=testMetadata(candidate.test_metadata);if(candidate.test_metadata!==undefined&&!metadata)return null;
  return{
    page_state:candidate.page_state as InfoPageState|null,
    projection_version:candidate.projection_version as string|null,
    authorized_scope:candidate.authorized_scope as string|null,
    last_refresh:candidate.last_refresh as string|null,
    values:candidate.values as Record<string,string>,
    lists:candidate.lists as Record<string,InfoListItem[]>,
    filters:candidate.filters as Record<string,InfoListItem[]>,
    gate_state:candidate.gate_state as Record<string,boolean>,
    test_metadata:metadata,
  };
}
export async function readInfoProjection(signal?:AbortSignal){
  let response:Response;
  try{response=await fetch('/v1/ui-projections/workspace%3AINFO-01',{method:'GET',cache:'no-store',credentials:'include',signal});}
  catch{return{ok:false as const,error_uid:'INFO-01-ERR-CONTEXT-001',reason_code:'INFO_PROJECTION_REQUEST_FAILED',correlation_id:'unresolved'};}
  const correlation_id=response.headers.get('x-correlation-id')??'unresolved';
  const raw:unknown=await response.json().catch(()=>null);
  if(!response.ok){const body=object(raw)?raw:null;return{ok:false as const,error_uid:'INFO-01-ERR-CONTEXT-001',reason_code:typeof body?.reason_code==='string'?body.reason_code:'INFO_PROJECTION_READ_FAILED',correlation_id:typeof body?.correlation_id==='string'?body.correlation_id:correlation_id};}
  try{
    const projection=resolver?await resolver.resolve(raw):normalizeInfoProjection(raw);
    if(!projection)throw new Error('INVALID_INFO_PROJECTION');
    if(projection.page_state!==null&&!isInfoPageState(projection.page_state))throw new Error('INFO_PROJECTION_PAGE_STATE_UNREGISTERED');
    if(projection.test_metadata!==undefined&&!isControlledTestMode())throw new Error('INFO_TEST_PROJECTION_FORBIDDEN_IN_PRODUCTION');
    return{ok:true as const,projection,correlation_id};
  }catch{return{ok:false as const,error_uid:'INFO-01-ERR-CONTEXT-001',reason_code:'INFO_PROJECTION_ADAPTER_REJECTED',correlation_id};}
}
