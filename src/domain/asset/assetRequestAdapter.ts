import{invokeAssetAction,type AssetInvokeResult}from'./assetClientPort';
import type{AssetActionUid}from'./assetRuntimeContract';
import type{AssetClientState}from'./assetClientState';
import type{AssetNormalizedProjection}from'./assetProjectionPort';
export type AssetRequestBuildInput={action_uid:AssetActionUid;control_uid:string;control_value?:unknown;state:Readonly<AssetClientState>;projection:AssetNormalizedProjection|null;correction_request:string};
export type AssetRequestBuilder={build:(input:AssetRequestBuildInput)=>Promise<{path_params?:Record<string,string>;payload?:unknown}>|{path_params?:Record<string,string>;payload?:unknown}};
let builder:AssetRequestBuilder|null=null;
export function configureAssetRequestBuilder(next:AssetRequestBuilder){builder=next;}
export function isAssetRequestBuilderBound(){return builder!==null;}
export async function buildAndInvokeAssetAction(input:AssetRequestBuildInput):Promise<AssetInvokeResult>{if(!builder)return{ok:false,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:'ASSET_REQUEST_ADAPTER_NOT_BOUND',correlation_id:'unresolved'};try{const built=await builder.build(input);return invokeAssetAction({action_uid:input.action_uid,path_params:built.path_params,payload:built.payload});}catch{return{ok:false,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:'ASSET_REQUEST_ADAPTER_FAILED',correlation_id:'unresolved'};}}
