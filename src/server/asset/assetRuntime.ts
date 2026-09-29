import type { AssetRuntimeRequest, AssetRuntimeResult } from "@/domain/asset/assetRuntimeContract";
import { executeControlledAssetTestPort, isControlledAssetServerTestMode } from "@/server/testing/controlledAssetTestRuntime";
import { namedReason } from "@/server/shared/namedRuntimeError";

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
 if(!runtime){if(isControlledAssetServerTestMode())return executeControlledAssetTestPort(request);return{ok:false,error_uid:"ASSET-01-ERR-CONTEXT-001",reason_code:"ASSET_RUNTIME_NOT_BOUND",correlation_id:request.correlation_id,status:503};}
 let decision:Awaited<ReturnType<AssetRuntimeBindings["authorize"]>>;
 try{decision=await runtime.authorize(request);}catch{await audit(runtime,{...request,outcome:"DENIED",reason_code:"AUTHORIZATION_EVALUATION_FAILED"});return{ok:false,error_uid:"ASSET-01-ERR-PERM-001",reason_code:"AUTHORIZATION_EVALUATION_FAILED",correlation_id:request.correlation_id,status:403};}
 if(!decision.allowed){const reason_code=decision.reason_code??"PERMISSION_OR_SCOPE_DENIED";await audit(runtime,{...request,outcome:"DENIED",reason_code});return{ok:false,error_uid:"ASSET-01-ERR-PERM-001",reason_code,correlation_id:request.correlation_id,status:403};}
 await audit(runtime,{...request,outcome:"ALLOWED"});
 try{const value=await runtime.execute(request);await audit(runtime,{...request,outcome:"SUCCESS"});return{ok:true,value,correlation_id:request.correlation_id};}
 catch(error){const reason_code=namedReason(error,"ASSET_PORT_EXECUTION_FAILED");await audit(runtime,{...request,outcome:"ERROR",reason_code});const error_uid=reason_code.includes("PERMISSION")?"ASSET-01-ERR-PERM-001":reason_code.includes("BLUEPRINT")?"ASSET-01-ERR-BLUEPRINT-001":reason_code.includes("SCRIPT")?"ASSET-01-ERR-SCRIPT-001":reason_code.includes("MANIFEST")?"ASSET-01-ERR-MANIFEST-001":reason_code.includes("ROUTE")||reason_code.includes("INSTRUCTION")?"ASSET-01-ERR-ROUTE-001":reason_code.includes("CRITERIA")||reason_code.includes("EVALUATION")||reason_code.includes("SCORE")?"ASSET-01-ERR-CRITERIA-001":reason_code.includes("HANDOFF")?"ASSET-01-ERR-HANDOFF-001":reason_code.includes("CANDIDATE")||reason_code.includes("OUTPUT")?"ASSET-01-ERR-CANDIDATE-001":"ASSET-01-ERR-PROVIDER-001";const status=reason_code.includes("REQUIRED")||reason_code.includes("INVALID")?400:reason_code.includes("MISMATCH")||reason_code.includes("CONFLICT")||reason_code.includes("NOT_SATISFIED")||reason_code.includes("NOT_ELIGIBLE")?409:reason_code.includes("PERMISSION")||reason_code.includes("AUTHORIZATION")?403:503;return{ok:false,error_uid,reason_code,correlation_id:request.correlation_id,status};}
}
