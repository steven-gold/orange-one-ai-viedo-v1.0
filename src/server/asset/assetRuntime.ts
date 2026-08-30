import type { AssetRuntimeRequest, AssetRuntimeResult } from "@/domain/asset/assetRuntimeContract";

export type AssetRuntimeBindings={
 authorize:(request:AssetRuntimeRequest)=>Promise<{allowed:true}|{allowed:false;reason_code?:string}>;
 execute:(request:AssetRuntimeRequest)=>Promise<unknown>;
 audit:(entry:AssetRuntimeRequest&{outcome:"ALLOWED"|"DENIED"|"SUCCESS"|"ERROR";reason_code?:string})=>Promise<void>;
};
let bindings:AssetRuntimeBindings|null=null;
export function configureAssetRuntime(next:AssetRuntimeBindings):void{bindings=next;}
async function audit(runtime:AssetRuntimeBindings,entry:Parameters<AssetRuntimeBindings["audit"]>[0]){try{await runtime.audit(entry);}catch{/* never fabricate success */}}
export async function executeAssetPort(request:AssetRuntimeRequest):Promise<AssetRuntimeResult>{
 const runtime=bindings;
 if(!runtime)return{ok:false,error_uid:"ASSET-01-ERR-CONTEXT-001",reason_code:"ASSET_RUNTIME_NOT_BOUND",correlation_id:request.correlation_id,status:503};
 let decision:Awaited<ReturnType<AssetRuntimeBindings["authorize"]>>;
 try{decision=await runtime.authorize(request);}catch{await audit(runtime,{...request,outcome:"DENIED",reason_code:"AUTHORIZATION_EVALUATION_FAILED"});return{ok:false,error_uid:"ASSET-01-ERR-PERM-001",reason_code:"AUTHORIZATION_EVALUATION_FAILED",correlation_id:request.correlation_id,status:403};}
 if(!decision.allowed){const reason_code=decision.reason_code??"PERMISSION_OR_SCOPE_DENIED";await audit(runtime,{...request,outcome:"DENIED",reason_code});return{ok:false,error_uid:"ASSET-01-ERR-PERM-001",reason_code,correlation_id:request.correlation_id,status:403};}
 await audit(runtime,{...request,outcome:"ALLOWED"});
 try{const value=await runtime.execute(request);await audit(runtime,{...request,outcome:"SUCCESS"});return{ok:true,value,correlation_id:request.correlation_id};}
 catch{await audit(runtime,{...request,outcome:"ERROR",reason_code:"ASSET_PORT_EXECUTION_FAILED"});return{ok:false,error_uid:"ASSET-01-ERR-PROVIDER-001",reason_code:"ASSET_PORT_EXECUTION_FAILED",correlation_id:request.correlation_id,status:503};}
}
