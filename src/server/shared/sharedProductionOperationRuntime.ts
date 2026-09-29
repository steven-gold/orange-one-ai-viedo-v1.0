import { namedReason } from "@/server/shared/namedRuntimeError";
export type SharedProductionOperationId =
  | "generateCorrectionScriptCandidate"
  | "approveCorrectionScriptCandidate"
  | "restoreAssetVersionAsNewDraft"
  | "lockAssetVersion"
  | "lockVideoVersion";
export type SharedProductionOperationRequest={
  operation_id:SharedProductionOperationId;
  correlation_id:string;
  payload:unknown;
};
export type SharedProductionOperationBindings={
  authorize:(request:SharedProductionOperationRequest)=>Promise<{allowed:true}|{allowed:false;reason_code?:string}>;
  execute:(request:SharedProductionOperationRequest)=>Promise<unknown>;
  audit:(entry:SharedProductionOperationRequest&{outcome:"ALLOWED"|"DENIED"|"SUCCESS"|"ERROR";reason_code?:string})=>Promise<void>;
};
let bindings:SharedProductionOperationBindings|null=null;
export function configureSharedProductionOperationRuntime(next:SharedProductionOperationBindings){bindings=next;}
async function audit(b:SharedProductionOperationBindings,e:Parameters<SharedProductionOperationBindings["audit"]>[0]){try{await b.audit(e);}catch{}}
function statusFor(reason:string){if(reason.includes("CONFLICT")||reason.includes("ALREADY"))return 409;if(reason.includes("REQUIRED")||reason.includes("INVALID")||reason.includes("MISMATCH"))return 400;if(reason.includes("PERMISSION")||reason.includes("AUTHORIZATION")||reason.includes("DENIED"))return 403;return 503;}
export async function executeSharedProductionOperation(request:SharedProductionOperationRequest){
  if(!bindings){const {bindIdentityPageCommandRuntimes}=await import("@/server/shared/identityPageCommandRuntime");bindIdentityPageCommandRuntimes();}
  const b=bindings;
  if(!b)return{ok:false as const,status:503,reason_code:"SHARED_PRODUCTION_OPERATION_RUNTIME_NOT_BOUND",correlation_id:request.correlation_id};
  let d:Awaited<ReturnType<SharedProductionOperationBindings["authorize"]>>;
  try{d=await b.authorize(request);}catch{return{ok:false as const,status:403,reason_code:"AUTHORIZATION_EVALUATION_FAILED",correlation_id:request.correlation_id};}
  if(!d.allowed){const reason_code=d.reason_code??"PERMISSION_OR_SCOPE_DENIED";await audit(b,{...request,outcome:"DENIED",reason_code});return{ok:false as const,status:403,reason_code,correlation_id:request.correlation_id};}
  await audit(b,{...request,outcome:"ALLOWED"});
  try{const value=await b.execute(request);await audit(b,{...request,outcome:"SUCCESS"});return{ok:true as const,value,correlation_id:request.correlation_id};}
  catch(error){const reason_code=namedReason(error,"SHARED_PRODUCTION_OPERATION_FAILED");await audit(b,{...request,outcome:"ERROR",reason_code});return{ok:false as const,status:statusFor(reason_code),reason_code,correlation_id:request.correlation_id};}
}
