import{invokeAssetAction,type AssetInvokeResult}from'./assetClientPort';
import type{AssetActionUid}from'./assetRuntimeContract';
import type{AssetClientState}from'./assetClientState';
import type{AssetNormalizedProjection}from'./assetProjectionPort';
import{buildControlledAssetRequest,isControlledAssetClientTestMode,rememberControlledAssetProjection}from'./controlledAssetClientTestRuntime';
export type AssetRequestBuildInput={action_uid:AssetActionUid;control_uid:string;control_value?:unknown;state:Readonly<AssetClientState>;projection:AssetNormalizedProjection|null;correction_request:string};
export type AssetRequestBuilder={build:(input:AssetRequestBuildInput)=>Promise<{path_params?:Record<string,string>;payload?:unknown}>|{path_params?:Record<string,string>;payload?:unknown}};
let builder:AssetRequestBuilder|null=null;
export function configureAssetRequestBuilder(next:AssetRequestBuilder){builder=next;}
export function isAssetRequestBuilderBound(){return builder!==null||isControlledAssetClientTestMode();}
export async function buildAndInvokeAssetAction(input:AssetRequestBuildInput):Promise<AssetInvokeResult>{rememberControlledAssetProjection(input.projection);try{const built=builder?await builder.build(input):isControlledAssetClientTestMode()?buildControlledAssetRequest(input):null;if(!built)return{ok:false,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:'ASSET_REQUEST_ADAPTER_NOT_BOUND',correlation_id:'unresolved'};return invokeAssetAction({action_uid:input.action_uid,path_params:built.path_params,payload:built.payload});}catch{return{ok:false,error_uid:'ASSET-01-ERR-CONTEXT-001',reason_code:builder?'ASSET_REQUEST_ADAPTER_FAILED':'ASSET_CONTROLLED_REQUEST_BUILD_FAILED',correlation_id:'unresolved'};}}
