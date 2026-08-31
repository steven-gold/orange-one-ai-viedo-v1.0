import { NextRequest,NextResponse } from "next/server";
import { ASSET_ACTION_PORT,ASSET_ACTION_UIDS,type AssetActionUid,type AssetPortUid } from "@/domain/asset/assetRuntimeContract";
import { executeAssetPort } from "@/server/asset/assetRuntime";
type Ctx={params:Promise<Record<string,string>>};
function cid(r:NextRequest){const v=r.headers.get("x-correlation-id");return v&&v.trim()?v:crypto.randomUUID();}
function actionForPort(r:NextRequest,port_uid:AssetPortUid):AssetActionUid|undefined{const raw=r.headers.get("x-asset-action-uid");if(!raw||!ASSET_ACTION_UIDS.includes(raw as AssetActionUid))return undefined;const action_uid=raw as AssetActionUid;return ASSET_ACTION_PORT[action_uid]===port_uid?action_uid:undefined;}
function error(correlation_id:string,status:number,error_uid:string,reason_code:string){return NextResponse.json({error_uid,reason_code,correlation_id},{status,headers:{"x-correlation-id":correlation_id,"cache-control":"no-store"}});}
async function run(port_uid:AssetPortUid,r:NextRequest,c:Ctx,payload?:unknown){const correlation_id=cid(r);const path_params=await c.params;const action_uid=actionForPort(r,port_uid);if(r.headers.has("x-asset-action-uid")&&!action_uid)return error(correlation_id,400,"ASSET-01-ERR-CONTEXT-001","ACTION_PORT_BINDING_MISMATCH");const result=await executeAssetPort({port_uid,action_uid,correlation_id,path_params,payload});if(!result.ok)return error(correlation_id,result.status,result.error_uid,result.reason_code);return NextResponse.json(result.value,{status:200,headers:{"x-correlation-id":correlation_id,"cache-control":"no-store"}});}
async function jsonPayload(r:NextRequest,correlation_id:string){try{return{ok:true as const,value:await r.json()};}catch{return{ok:false as const,response:error(correlation_id,400,"ASSET-01-ERR-CONTEXT-001","INVALID_JSON_PAYLOAD")};}}
export function assetPost(port:AssetPortUid){return async(r:NextRequest,c:Ctx)=>{const correlation_id=cid(r),parsed=await jsonPayload(r,correlation_id);if(!parsed.ok)return parsed.response;return run(port,r,c,parsed.value);};}
export function assetPatch(port:AssetPortUid){return async(r:NextRequest,c:Ctx)=>{const correlation_id=cid(r),parsed=await jsonPayload(r,correlation_id);if(!parsed.ok)return parsed.response;return run(port,r,c,parsed.value);};}
export function assetDelete(port:AssetPortUid){return async(r:NextRequest,c:Ctx)=>run(port,r,c);}
