import { NextRequest,NextResponse } from "next/server";
import type { AssetPortUid } from "@/domain/asset/assetRuntimeContract";
import { executeAssetPort } from "@/server/asset/assetRuntime";
type Ctx={params:Promise<Record<string,string>>};
function cid(r:NextRequest){const v=r.headers.get("x-correlation-id");return v&&v.trim()?v:crypto.randomUUID();}
async function run(port_uid:AssetPortUid,r:NextRequest,c:Ctx,payload?:unknown){const correlation_id=cid(r);const path_params=await c.params;const result=await executeAssetPort({port_uid,correlation_id,path_params,payload});if(!result.ok)return NextResponse.json({error_uid:result.error_uid,reason_code:result.reason_code,correlation_id},{status:result.status,headers:{"x-correlation-id":correlation_id,"cache-control":"no-store"}});return NextResponse.json(result.value,{status:200,headers:{"x-correlation-id":correlation_id,"cache-control":"no-store"}});}
export function assetPost(port:AssetPortUid){return async(r:NextRequest,c:Ctx)=>run(port,r,c,await r.json().catch(()=>null));}
export function assetPatch(port:AssetPortUid){return async(r:NextRequest,c:Ctx)=>run(port,r,c,await r.json().catch(()=>null));}
export function assetDelete(port:AssetPortUid){return async(r:NextRequest,c:Ctx)=>run(port,r,c,await r.json().catch(()=>null));}
