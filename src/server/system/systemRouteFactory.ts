import { NextRequest, NextResponse } from "next/server";
import { executeSystemLifecycleOperation } from "@/server/system/systemLifecycleRuntime";
import type { SysServiceOperation } from "@/domain/system/systemRuntimeContract";

type RouteOptions={system_change_id_from:"BODY_OPTIONAL"|"PATH_ID"};

function responseHeaders(correlation_id:string){return{"x-correlation-id":correlation_id,"cache-control":"no-store"};}
function statusFor(reason_code:string){
  if(/PERMISSION|AUTHORIZATION|DENIED/.test(reason_code))return 403;
  if(/NOT_FOUND/.test(reason_code))return 404;
  if(/REQUIRED|INVALID|FIELD_/.test(reason_code))return 400;
  if(/RUNTIME_NOT_BOUND|DATABASE_RUNTIME_NOT_BOUND|CONTINUITY_CONTEXT_UNRESOLVED/.test(reason_code))return 503;
  return 409;
}

export function createSystemRoute(operation_id:SysServiceOperation,options:RouteOptions){
  return async(req:NextRequest,ctx?:{params:Promise<Record<string,string>>})=>{
    const supplied=req.headers.get("x-correlation-id");
    const correlation_id=supplied?.trim()||crypto.randomUUID();
    let payload:Record<string,unknown>={};
    try{
      const raw:unknown=await req.json();
      if(raw&&typeof raw==="object"&&!Array.isArray(raw))payload=raw as Record<string,unknown>;
    }catch{}
    const params=ctx?(await ctx.params)??{}:{};
    const bodyId=typeof payload.system_change_id==="string"?payload.system_change_id:null;
    const system_change_id=options.system_change_id_from==="PATH_ID"?params.id??null:bodyId;
    const result=await executeSystemLifecycleOperation({operation_id,correlation_id,system_change_id,payload});
    if(!result.ok)return NextResponse.json(
      {ok:false,reason_code:result.reason_code,correlation_id},
      {status:statusFor(result.reason_code),headers:responseHeaders(correlation_id)},
    );
    return NextResponse.json({ok:true,value:result.value,correlation_id},{status:200,headers:responseHeaders(correlation_id)});
  };
}
